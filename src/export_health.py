"""导出前健康检查（无 GUI 依赖，GUI / 契约测试共用）

对应 Scenario Forge 的 "Project Health / 导出前检查" 移植：
在把 mod 发布（上传 Workshop / 交给游戏加载）之前，对 mod 目录做确定性检查，
给出 error / warning / info 三级问题清单：

- error   ：会导致游戏加载失败或明显错误（括号不平衡、引用悬空、重复 id、
            定义的贴图缺失、UTF-8 编码损坏、描述文件缺失/路径错误）
- warning ：影响体验或与项目纪律不一致（本地化缺失、悬空前置国策、
            BOM/CRLF 与写入纪律不符、空文件）
- info    ：观察信息（无图标科技、CRLF 提示、大文件跳过等）

运行方式：
    from export_health import run_export_health_check
    report = run_export_health_check(mod_path, hoi4_path)
    report.to_json()   # 可落盘为 JSON 报告

契约测试：tests/test_contracts.py 中的 HealthCheck 测试类。
"""

from __future__ import annotations

import os
import re
import time

from dataclasses import dataclass, field

# 文本类扩展名（参与编码/括号检查）
TEXT_EXTS = {".txt", ".gfx", ".yml", ".mod", ".csv", ".cfg", ".gui", ".asset"}
# 脚本类扩展名（参与括号配对检查）
SCRIPT_EXTS = {".txt", ".gfx", ".mod", ".csv", ".cfg"}
# 单文件括号检查的大小上限（更大文件跳过，报 info）
BRACE_MAX_BYTES = 2 * 1024 * 1024
# 同类问题最大上报条数（避免巨量输出）
MAX_PER_CATEGORY = 200

_SEV = ("error", "warning", "info")


@dataclass
class HealthIssue:
    severity: str          # error / warning / info
    category: str          # descriptor/encoding/syntax/reference/duplicate/locale
    file: str              # 相对 mod 的路径，或 "-"
    message: str
    hint: str = ""

    def to_dict(self):
        return {
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "message": self.message,
            "hint": self.hint,
        }


@dataclass
class HealthReport:
    mod_path: str
    hoi4_path: str
    issues: list = field(default_factory=list)
    started_at: float = field(default_factory=time.time)

    @property
    def duration_ms(self):
        return int((time.time() - self.started_at) * 1000)

    @property
    def counts(self):
        c = {"error": 0, "warning": 0, "info": 0}
        for i in self.issues:
            if i.severity in c:
                c[i.severity] += 1
        return c

    def has_errors(self):
        return self.counts["error"] > 0

    def to_json(self):
        import json
        return json.dumps({
            "mod_path": self.mod_path,
            "hoi4_path": self.hoi4_path or "",
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(self.started_at)),
            "duration_ms": self.duration_ms,
            "counts": self.counts,
            "issues": [i.to_dict() for i in self.issues],
        }, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 工具函数

def _walk_files(mod_path, exts):
    """遍历 mod 目录下指定扩展名的全部文件（相对路径 + 绝对路径）。"""
    for root, _dirs, names in os.walk(mod_path):
        for name in names:
            low = name.lower()
            if not low.endswith(tuple(exts)):
                continue
            fp = os.path.join(root, name)
            rel = os.path.relpath(fp, mod_path).replace(os.sep, "/")
            yield fp, rel


def _read_text(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            return f.read()
    except Exception:
        return ""


def _count_braces(text):
    """引号/注释感知的括号计数。

    Returns:
        int: 正数 = 多出的 '{'（缺闭合）；负数 = 多出的 '}'。
    """
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":
            quote = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    break
                i += 1
        elif c == "#":
            while i < n and text[i] not in "\r\n":
                i += 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return depth


def _sprite_map(mod_path):
    """扫描 interface/**/*.gfx，返回 {sprite_name: texture_rel} 与问题列表。"""
    sprites = {}
    issues = []
    interface_dir = os.path.join(mod_path, "interface")
    base = interface_dir if os.path.isdir(interface_dir) else mod_path
    for fp, rel in _walk_files(base, {".gfx"}):
        if base is interface_dir:
            rel = "interface/" + rel
        if not rel.startswith("interface/"):
            continue
        text = _read_text(fp)
        for m in re.finditer(r"SpriteType\s*=\s*\{(.*?)\}", text,
                             re.DOTALL | re.IGNORECASE):
            block = m.group(1)
            nm = re.search(r'\bname\s*=\s*"([^"]+)"', block)
            tx = re.search(r'\btexturefile\s*=\s*"([^"]+)"', block)
            if not nm:
                continue
            name = nm.group(1)
            tex = tx.group(1) if tx else ""
            sprites[name] = tex
            if not tex:
                issues.append(HealthIssue(
                    "warning", "reference", rel,
                    "sprite '%s' 没有 texturefile 字段" % name,
                    "补上 texturefile 指向贴图文件"))
    return sprites, issues


def _resolve_texture_path(mod_path, tex, hoi4_path=None):
    """把 gfx 文件里的 texturefile 值解析为 mod 内路径（不存在返回 None）。

    优先查 mod 内；mod 内缺失时若提供 hoi4_path 再查游戏本体
    （sprite 常引用游戏自带资源，如 gfx/interface/counters/...）。
    """
    t = (tex or "").strip().replace("\\", "/")
    if not t:
        return None
    if t.startswith("/"):
        t = t.lstrip("/")
    candidate = os.path.join(mod_path, t.replace("/", os.sep))
    if os.path.isfile(candidate):
        return candidate
    # 部分 mod 会写相对于 gfx 目录的路径，这里仅尝试常见前缀剥离
    for prefix in ("gfx/", "interface/"):
        if t.startswith(prefix):
            alt = os.path.join(mod_path, t[len(prefix):].replace("/", os.sep))
            if os.path.isfile(alt):
                return alt
    if hoi4_path and os.path.isdir(hoi4_path):
        game = os.path.join(hoi4_path, t.replace("/", os.sep))
        if os.path.isfile(game):
            return game
    return None


# ---------------------------------------------------------------- 检查项

def check_descriptor(mod_path, issues):
    """描述文件（*.mod）与 path 指向目录存在性。"""
    mods = [n for n in os.listdir(mod_path)
            if n.lower().endswith(".mod") and os.path.isfile(os.path.join(mod_path, n))]
    if not mods:
        issues.append(HealthIssue(
            "error", "descriptor", "-",
            "mod 根目录没有 .mod 描述文件",
            "创建 descriptor.mod（name / path / replace_path / supported_version）"))
        return
    for name in mods:
        text = _read_text(os.path.join(mod_path, name))
        if not text.strip():
            issues.append(HealthIssue(
                "error", "descriptor", name, "描述文件为空", "填写 name / path 等字段"))
            continue
        path_m = re.search(r'^\s*path\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if path_m:
            target = path_m.group(1).replace("\\", "/").strip("/")
            if target and not os.path.isdir(os.path.join(mod_path, target.replace("/", os.sep))):
                issues.append(HealthIssue(
                    "error", "descriptor", name,
                    "描述文件 path 指向的目录不存在：%s" % path_m.group(1),
                    "修正 path 或创建目录"))
        name_m = re.search(r'^\s*name\s*=\s*"([^"]*)"', text, re.MULTILINE)
        if not name_m or not name_m.group(1).strip():
            issues.append(HealthIssue(
                "warning", "descriptor", name,
                "描述文件缺少 name 字段", "游戏内显示名需要 name"))


def check_text_encoding(mod_path, issues):
    """UTF-8 合法性 / BOM / CRLF / 空文件。"""
    for fp, rel in _walk_files(mod_path, TEXT_EXTS):
        try:
            with open(fp, "rb") as f:
                raw = f.read()
        except OSError:
            continue
        if not raw:
            issues.append(HealthIssue("warning", "encoding", rel,
                                      "文件为空（可能是误删内容）",
                                      "确认后删除或补内容"))
            continue
        if len(issues) >= MAX_PER_CATEGORY:
            break
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            issues.append(HealthIssue(
                "error", "encoding", rel,
                "不是合法 UTF-8（文件损坏或编码错误，游戏解析将失败）",
                "用编辑器重新保存为 UTF-8"))
            continue
        if raw.startswith(b"\xef\xbb\xbf") and not rel.lower().endswith(".yml"):
            issues.append(HealthIssue(
                "warning", "encoding", rel,
                "文件带 UTF-8 BOM（与写入纪律不一致，个别解析场景会出问题）",
                "建议统一为无 BOM UTF-8"))
        if b"\r\n" in raw:
            issues.append(HealthIssue(
                "info", "encoding", rel, "文件使用 CRLF 行尾（游戏可读，与写入纪律不一致）",
                "建议统一为 LF"))


def check_brace_balance(mod_path, issues):
    """脚本文件括号配对（引号/注释感知）。"""
    for fp, rel in _walk_files(mod_path, SCRIPT_EXTS):
        try:
            size = os.path.getsize(fp)
        except OSError:
            continue
        if size > BRACE_MAX_BYTES:
            issues.append(HealthIssue(
                "info", "syntax", rel, "文件超过 %.1f MB，跳过括号检查" % (BRACE_MAX_BYTES / 1048576.0),
                ""))
            continue
        text = _read_text(fp)
        if not text.strip():
            continue
        depth = _count_braces(text)
        if depth > 0:
            issues.append(HealthIssue(
                "error", "syntax", rel, "缺少 %d 个 '}'（括号未闭合，游戏加载失败）" % depth,
                "补齐闭合花括号"))
        elif depth < 0:
            issues.append(HealthIssue(
                "error", "syntax", rel, "多出 %d 个 '}'" % (-depth),
                "删掉多余闭合花括号"))


def check_gfx_textures(mod_path, issues, hoi4_path=None):
    """interface/*.gfx 中定义的所有 sprite 贴图必须存在（mod 内或游戏本体）。"""
    sprites, sprite_issues = _sprite_map(mod_path)
    issues.extend(sprite_issues)
    for name, tex in sorted(sprites.items()):
        if not tex:
            continue
        if _resolve_texture_path(mod_path, tex, hoi4_path) is None:
            issues.append(HealthIssue(
                "error", "reference", "interface/",
                "sprite '%s' 的贴图不存在：%s" % (name, tex),
                "补上贴图文件或修正 texturefile 路径"))
    return sprites


def check_focus_references(mod_path, issues):
    """悬空前置国策 / mutually_exclusive 引用（复用 validation）。"""
    try:
        from validation import check_focus_references as _chk
        problems = _chk(mod_path)
    except Exception:
        return
    for p in problems[:MAX_PER_CATEGORY]:
        issues.append(HealthIssue(
            "warning", "reference", p.get("file", ""),
            "国策 '%s' 引用了不存在的国策：%s" % (p.get("focus_id", ""),
                                            ", ".join(p.get("missing", []) or [])),
            "修正 prerequisite / mutually_exclusive；若为脚本生成国策可忽略"))


def check_localisation_coverage(mod_path, hoi4_path, issues):
    """本地化缺失（复用 validation）。"""
    try:
        from validation import check_localisation_coverage as _chk
        missing = _chk(mod_path, hoi4_path)
    except Exception:
        return
    for m in missing[:50]:
        issues.append(HealthIssue(
            "warning", "locale", m.get("file", ""),
            "实体 '%s'（%s）缺少本地化词条：%s" % (
                m.get("key", ""), m.get("type", ""),
                ", ".join(m.get("missing_keys", []) or [])),
            "工具菜单「校验 mod」可一键补全"))
    if len(missing) > 50:
        issues.append(HealthIssue(
            "warning", "locale", "-",
            "本地化缺失共 %d 条，仅显示前 50 条" % len(missing),
            "先用「校验 mod」一键补全"))


def _match_block(text, open_index):
    """从 '{' 位置做括号配对，返回包含 '{' 与 '}' 的整块文本。"""
    depth = 0
    i = open_index
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[open_index:i + 1]
        i += 1
    return text[open_index:]


def _focus_ids(text):
    """提取 focus 块 id（每块开头第一个 id 字段，块级精确）。"""
    ids = []
    for m in re.finditer(r"\bfocus\s*=\s*\{", text):
        block = _match_block(text, m.end() - 1)
        idm = re.search(r"^\s*id\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", block, re.MULTILINE)
        if idm:
            ids.append(idm.group(1))
    return ids


def _first_level_keys(block):
    """取块内最小缩进层级的 `key = {` 顶层键（科技/角色等 wrapper 内实体）。"""
    lines = [l for l in block.splitlines() if l.strip()]
    if not lines:
        return []
    min_indent = min(len(l) - len(l.lstrip(" \t")) for l in lines)
    keys = []
    for line in lines:
        if len(line) - len(line.lstrip(" \t")) != min_indent:
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", line.strip())
        if m:
            keys.append(m.group(1))
    return keys


def _tech_ids(text):
    """提取 technologies = { ... } wrapper 内的科技 id。"""
    m = re.search(r"\btechnologies\s*=\s*\{", text)
    if not m:
        return []
    block = _match_block(text, m.end() - 1)
    return _first_level_keys(block[1:-1])


def check_duplicate_ids(mod_path, issues):
    """focus / tech / character 重复 id（后定义会覆盖先定义）。"""

    def _scan_dir(rel_dir, exts, extractor, type_label):
        base = os.path.join(mod_path, rel_dir.replace("/", os.sep))
        if not os.path.isdir(base):
            return
        seen = {}
        for root, _dirs, names in os.walk(base):
            for name in names:
                if not name.lower().endswith(tuple(exts)):
                    continue
                fp = os.path.join(root, name)
                rel = os.path.relpath(fp, mod_path).replace(os.sep, "/")
                try:
                    ids = extractor(_read_text(fp))
                except Exception:
                    ids = []
                for i in ids:
                    if i in seen:
                        issues.append(HealthIssue(
                            "error", "duplicate", rel,
                            "%s '%s' 重复定义（首次见 %s），后定义会覆盖先定义" % (
                                type_label, i, seen[i]),
                            "重命名其中一个 id"))
                    else:
                        seen[i] = rel

    _scan_dir("common/national_focus", {".txt"}, _focus_ids, "国策")
    _scan_dir("common/technologies", {".txt"}, _tech_ids, "科技")
    # character：通用顶层块 key 计数（字段块可能误报，用 warning 级）
    base = os.path.join(mod_path, "common", "characters")
    seen = {}
    if os.path.isdir(base):
        for root, _dirs, names in os.walk(base):
            for name in names:
                if not name.lower().endswith(".txt"):
                    continue
                fp = os.path.join(root, name)
                rel = os.path.relpath(fp, mod_path).replace(os.sep, "/")
                text = _read_text(fp)
                for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{',
                                     text, re.MULTILINE):
                    key = m.group(1)
                    if key in ("characters", "countries", "set_variable",
                               "supported_idea_categories"):
                        continue
                    if key in seen:
                        issues.append(HealthIssue(
                            "warning", "duplicate", rel,
                            "角色块 '%s' 重复出现（首次见 %s）" % (key, seen[key]),
                            "重命名其中一个 id"))
                    else:
                        seen[key] = rel


def check_tech_icons(mod_path, issues, sprites=None, hoi4_path=None):
    """科技图标引用：已注册 sprite 的贴图必须存在；无图标科技为 info。"""
    try:
        from entity_scanner import EntityScanner as WorkbenchDock
    except Exception:
        WorkbenchDock = None
    base = os.path.join(mod_path, "common", "technologies")
    if not os.path.isdir(base):
        return
    if sprites is None:
        sprites, _ = _sprite_map(mod_path)
    tech_ids = set()
    if WorkbenchDock is not None:
        for root, _dirs, names in os.walk(base):
            for name in names:
                if not name.lower().endswith(".txt"):
                    continue
                try:
                    tech_ids.update(
                        (WorkbenchDock._quick_tech_scan(_read_text(
                            os.path.join(root, name))) or {}).keys())
                except Exception:
                    pass
    n_registered = 0
    for tid in sorted(tech_ids):
        sprite = "GFX_%s_medium" % tid
        tex = sprites.get(sprite)
        if tex is None:
            continue
        n_registered += 1
        if _resolve_texture_path(mod_path, tex) is None:
            issues.append(HealthIssue(
                "error", "reference", "common/technologies/",
                "科技 '%s' 的图标 sprite '%s' 贴图不存在：%s" % (tid, sprite, tex),
                "补上 gfx/interface/technologies/ 下的贴图或修正路径"))
    if n_registered == 0 and tech_ids:
        issues.append(HealthIssue(
            "info", "reference", "common/technologies/",
            "共 %d 个科技均未注册图标（游戏将使用占位图标）" % len(tech_ids),
            "画布右键科技节点可上传图标"))


def check_high_risk_ids(mod_path, issues, hoi4_path=None):
    """高危 id 检查：mod 与 vanilla 同名覆盖 / 保留字用作 id → warning。"""
    try:
        from high_risk_ids import high_risk_ids
        for r in high_risk_ids(mod_path, hoi4_path or ""):
            issues.append(HealthIssue(
                "warning", "high_risk", r["mod_file"],
                "%s：%s — %s" % (r["type"], r["id"], r["reason"]),
                r.get("vanilla_file") or r["reason"]))
    except Exception:
        # 高危扫描失败不阻断整体报告
        return


# ---------------------------------------------------------------- 入口

def run_export_health_check(mod_path, hoi4_path=None, max_issues=500):
    """对 mod 目录执行完整健康检查。

    Args:
        mod_path: mod 根目录（绝对路径）
        hoi4_path: 游戏根目录（可选，用于本地化缺失检测）
        max_issues: 结果上限

    Returns:
        HealthReport
    """
    report = HealthReport(mod_path=mod_path, hoi4_path=hoi4_path or "")
    if not mod_path or not os.path.isdir(mod_path):
        report.issues.append(HealthIssue(
            "error", "descriptor", "-",
            "mod 目录不存在：%s" % (mod_path or ""),
            "先打开一个 mod 目录"))
        return report
    steps = [
        ("descriptor", lambda: check_descriptor(mod_path, report.issues)),
        ("encoding", lambda: check_text_encoding(mod_path, report.issues)),
        ("syntax", lambda: check_brace_balance(mod_path, report.issues)),
        ("gfx", lambda: check_gfx_textures(mod_path, report.issues, hoi4_path)),
        ("focus_refs", lambda: check_focus_references(mod_path, report.issues)),
        ("locale", lambda: check_localisation_coverage(mod_path, hoi4_path,
                                                       report.issues)),
        ("duplicate", lambda: check_duplicate_ids(mod_path, report.issues)),
    ]
    sprites = {}
    try:
        sprites, _ = _sprite_map(mod_path)
    except Exception:
        pass
    steps.append(("tech_icons",
                  lambda: check_tech_icons(mod_path, report.issues, sprites,
                                           hoi4_path)))
    steps.append(("high_risk",
                  lambda: check_high_risk_ids(mod_path, report.issues,
                                              hoi4_path)))
    for _name, fn in steps:
        try:
            fn()
        except Exception:
            # 单项检查失败不阻断整体报告（保证 UI 总能出结果）
            continue
    if len(report.issues) > max_issues:
        report.issues = report.issues[:max_issues]
        report.issues.append(HealthIssue(
            "info", "-", "-",
            "问题总数超过 %d 条，已截断显示" % max_issues, ""))
    return report
