"""覆盖规则链与增量报告（Scenario Forge 移植：规则分层 + delta 增量模型）

SF 的「1939 = 1936 的 delta 叠加」与 manual 规则分层，直接对应本项目
「mod 覆盖原版」的场景——把「覆盖」建模成**显式规则链**而不是隐式优先级：

- `RuleLayer`：一层覆盖规则（来源 + include/exclude 模式 + 质量分级）
- `OverlayRules`：规则链；`resolve(rel_path)` → 命中层与质量分级
- `build_override_report(mod, game)`：文件级增量报告——
  每个 mod 文件分类为 new / override / identical，附质量分级与行级增量
  （added/removed 统计，difflib）
- `write_override_report`：JSON 导出（原子写，遵循写入纪律）

质量分级（对应 SF 的 direct/manual_reviewed/approx/blocker）：
    direct_copy      与游戏原版字节一致（纯拷贝/占位）
    manual_reviewed  与游戏原版明显不同（手写覆盖，需人工复核）
    approx           与游戏原版高度相似（疑似模板生成，需复核）
    blocker          与游戏原版几乎无关且体积大（整块替换，审慎对待）
"""

from __future__ import annotations

import difflib
import json
import os

from write_utils import atomic_write_text

# 扫描的顶层内容目录（相对 mod 根）；顶层 *.mod 描述文件也纳入
SCAN_TOPS = ("common", "events", "history", "map", "localisation", "gfx")
# 二进制扩展名：只做字节比对，不做行级增量
BINARY_EXTS = (".dds", ".bmp", ".png", ".jpg", ".jpeg", ".tga", ".npz",
               ".npy", ".wav", ".ogg")

DEFAULT_RULES_JSON = {
    "layers": [
        {
            "source": "vanilla",
            "quality": "blocker",
            "include": ["**"],
            "exclude": [],
            "description": "游戏原版只读层（写入永不落在此层）",
        },
        {
            "source": "mod",
            "quality": "manual_reviewed",
            "include": ["common/**", "events/**", "history/**", "map/**",
                        "localisation/**", "gfx/**", "*.mod"],
            "exclude": ["**/*.bak", "**/~*", "**/*.tmp", "**/.DS_Store"],
            "description": "mod 覆盖层（覆盖原版，写入目标）",
        },
    ]
}


def _matches(rel_path, patterns):
    import fnmatch
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


class RuleLayer:
    """一层覆盖规则。"""

    def __init__(self, source, quality, include, exclude, description=""):
        self.source = source            # "vanilla" / "mod" / 自定义
        self.quality = quality          # direct_copy / manual_reviewed / approx / blocker
        self.include = list(include or [])
        self.exclude = list(exclude or [])
        self.description = description

    def matches(self, rel_path):
        if self.exclude and _matches(rel_path, self.exclude):
            return False
        return _matches(rel_path, self.include)

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("source", ""), d.get("quality", "manual_reviewed"),
                   d.get("include", []), d.get("exclude", []),
                   d.get("description", ""))

    def to_dict(self):
        return {"source": self.source, "quality": self.quality,
                "include": self.include, "exclude": self.exclude,
                "description": self.description}


class OverlayRules:
    """覆盖规则链：后层优先（mod 覆盖 vanilla）。"""

    def __init__(self, layers):
        self.layers = layers

    @classmethod
    def load(cls, path=None):
        """加载规则 JSON；无文件/损坏时回退默认规则链。"""
        data = None
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = None
        if not data or not data.get("layers"):
            data = DEFAULT_RULES_JSON
        return cls([RuleLayer.from_dict(d) for d in data["layers"]])

    def resolve(self, rel_path):
        """返回 (layer, quality)；无命中返回 (None, None)。"""
        hit = None
        for layer in self.layers:
            if layer.matches(rel_path):
                hit = layer
        if hit is None:
            return None, None
        return hit, hit.quality

    def to_dict(self):
        return {"layers": [l.to_dict() for l in self.layers]}


# ---------------------------------------------------------------- 增量报告

def _norm_lines(text):
    """统一行尾并按行切分（忽略 CRLF 差异）。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _line_delta(game_text, mod_text):
    """行级增量统计：added / removed / diff_lines。"""
    if game_text == mod_text:
        return {"added": 0, "removed": 0, "diff_lines": 0}
    gl = _norm_lines(game_text)
    ml = _norm_lines(mod_text)
    diff = list(difflib.unified_diff(gl, ml, lineterm="", n=0))
    added = removed = 0
    for line in diff[2:]:            # 跳过文件头两行
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return {"added": added, "removed": removed,
            "diff_lines": added + removed}


def _quality_of(kind, mod_size, game_text, mod_text):
    """质量分级：identical → direct_copy；高度相似 → approx；大体积无关 → blocker。"""
    if kind == "identical":
        return "direct_copy"
    if kind == "new":
        return "manual_reviewed"
    if game_text is None:
        return "manual_reviewed"
    ratio = difflib.SequenceMatcher(None, _norm_lines(game_text),
                                    _norm_lines(mod_text)).ratio()
    if ratio >= 0.9:
        return "approx"
    if ratio < 0.3 and mod_size > 100 * 1024:
        return "blocker"
    return "manual_reviewed"


def classify_override(rel_path, mod_abs, game_abs):
    """单文件分类：new / override / identical + 质量 + 增量统计。"""
    mod_size = os.path.getsize(mod_abs)
    ext = os.path.splitext(rel_path)[1].lower()
    binary = ext in BINARY_EXTS
    game_size = os.path.getsize(game_abs) if game_abs else 0

    if not game_abs:
        return {"rel": rel_path, "kind": "new", "quality": "manual_reviewed",
                "mod_size": mod_size, "game_size": 0, "binary": binary,
                "delta": None}

    if mod_size == game_size:
        try:
            same = _same_bytes(mod_abs, game_abs)
        except OSError:
            same = False
        if same:
            return {"rel": rel_path, "kind": "identical",
                    "quality": "direct_copy",
                    "mod_size": mod_size, "game_size": game_size,
                    "binary": binary, "delta": None}

    if binary:
        return {"rel": rel_path, "kind": "override", "quality": "blocker",
                "mod_size": mod_size, "game_size": game_size,
                "binary": True, "delta": None}

    try:
        with open(game_abs, "r", encoding="utf-8", errors="replace") as f:
            game_text = f.read()
        with open(mod_abs, "r", encoding="utf-8", errors="replace") as f:
            mod_text = f.read()
    except OSError:
        game_text = mod_text = ""
    return {"rel": rel_path, "kind": "override",
            "quality": _quality_of("override", mod_size,
                                   game_text, mod_text),
            "mod_size": mod_size, "game_size": game_size,
            "binary": False, "delta": _line_delta(game_text, mod_text)}


def _same_bytes(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            ca = fa.read(1 << 16)
            cb = fb.read(1 << 16)
            if ca != cb:
                return False
            if not ca:
                return True


def build_override_report(mod_path, hoi4_path, rules=None,
                          progress=None):
    """构建文件级覆盖增量报告。

    Args:
        mod_path: mod 目录
        hoi4_path: 游戏目录（可空 → 全部 mod 文件视为 new）
        rules: OverlayRules（默认加载默认规则链）
        progress: 可选 fn(done, total)

    Returns:
        dict: {"mod_path", "game_path", "layers", "files", "stats"}
    """
    rules = rules or OverlayRules.load()
    files = []
    mod_path = os.path.abspath(mod_path or "")
    hoi4_path = os.path.abspath(hoi4_path or "")

    rel_list = []
    for root, dirs, names in os.walk(mod_path):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d != "__pycache__"]
        for name in names:
            if name.startswith(".") or name.endswith((".bak", "~")):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, mod_path).replace("\\", "/")
            top = rel.split("/", 1)[0]
            if top not in SCAN_TOPS and not (top.endswith(".mod")
                                             or rel == "descriptor.mod"):
                continue
            rel_list.append(rel)
    rel_list.sort()

    for i, rel in enumerate(rel_list):
        mod_abs = os.path.join(mod_path, rel)
        game_abs = os.path.join(hoi4_path, rel) if hoi4_path else None
        if game_abs and not os.path.isfile(game_abs):
            game_abs = None
        entry = classify_override(rel, mod_abs, game_abs)
        layer, quality = rules.resolve(rel)
        entry["layer_source"] = layer.source if layer else None
        # 层质量作为"预期"参考单独记录；报告质量保留文件级精确分级
        entry["layer_quality"] = quality if layer else None
        files.append(entry)
        if progress and rel_list:
            progress(i + 1, len(rel_list))

    stats = {"total": len(files), "new": 0, "override": 0, "identical": 0}
    for e in files:
        stats[e["kind"]] = stats.get(e["kind"], 0) + 1
    return {"mod_path": mod_path, "game_path": hoi4_path,
            "layers": rules.to_dict(), "files": files, "stats": stats}


def write_override_report(mod_path, hoi4_path, out_path):
    """导出增量报告 JSON（原子写）。返回报告 dict。"""
    report = build_override_report(mod_path, hoi4_path)
    text = json.dumps(report, ensure_ascii=False, indent=1)
    atomic_write_text(out_path, text)
    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python overlay_rules.py <mod目录> [游戏目录] [输出json]")
        sys.exit(1)
    mod = sys.argv[1]
    game = sys.argv[2] if len(sys.argv) > 2 else ""
    out = sys.argv[3] if len(sys.argv) > 3 else ""
    report = build_override_report(mod, game)
    stats = report["stats"]
    print("覆盖增量报告: 总计 %d 文件 | 新增 %d | 覆盖 %d | 与原版一致 %d"
          % (stats["total"], stats["new"], stats["override"],
             stats["identical"]))
    for e in report["files"]:
        if e["kind"] != "identical":
            delta = e["delta"]
            d = (" +%d/-%d" % (delta["added"], delta["removed"])) \
                if delta else ""
            print("  [%s] %s (%s)%s" % (e["kind"], e["rel"],
                                        e["quality"], d))
    if out:
        write_override_report(mod, game, out)
        print("已导出: %s" % out)
