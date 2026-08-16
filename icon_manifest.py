"""图标库 manifest（Scenario Forge 移植：unit_counter_libraries 的 manifest 结构）

扫描 mod + 游戏全部 `gfx/**/*.gfx` 的 spriteType 定义，产出图标清单：
sprite 名 → 贴图路径 / 来源（mod|vanilla）/ 尺寸 / md5 / 贴图存在性。
供图标解析（icon_resolver 兜底索引）、外置 Agent（API/MCP）与
导出前检查使用；贴图按 mod → 游戏顺序解析（与游戏资源回退一致）。

- `build_icon_manifest(mod_path, hoi4_path)` → dict（entries + stats）
- `write_icon_manifest(...)` → JSON 导出（原子写）
- `IconManifest`：加载/查询封装
- `tools/build_icon_manifest.py`：命令行导出
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from write_utils import atomic_write_text

# spriteType = { name = "GFX_x" texturefile = "gfx/interface/x.dds" ... }
_SPRITE_BLOCK_RE = re.compile(r"spriteType\s*=\s*\{(.*?)\}", re.S)
_NAME_RE = re.compile(r'name\s*=\s*"([^"]+)"')
_TEXTURE_RE = re.compile(r'texturefile\s*=\s*"([^"]+)"')

# 跳过的大型非图标目录（避免扫到海量皮肤/旗帜等无关资源）
_SKIP_DIR_PARTS = ("event_photos", "flags", "gfx/flags", "portraits_big")


def _iter_gfx_files(mod_path, hoi4_path):
    """按 mod → 游戏顺序产出 (rel_path, abs_path, source)。

    扫描整棵目录树的 *.gfx（部分游戏安装把定义放在 dlc/ 或 interface/，
    仅扫 gfx/ 会漏）；同一相对路径 mod 优先（seen 去重）。
    """
    seen = set()
    for base, source in ((mod_path or "", "mod"), (hoi4_path or "", "vanilla")):
        if not base or not os.path.isdir(base):
            continue
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs
                       if not d.startswith(".") and d != "__pycache__"]
            for name in names:
                if not name.lower().endswith(".gfx"):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, base).replace("\\", "/")
                if rel in seen:
                    continue
                seen.add(rel)
                yield rel, full, source


def _parse_sprites(gfx_path):
    """解析单个 .gfx 文件的 spriteType 定义。"""
    out = []
    try:
        with open(gfx_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return out
    for m in _SPRITE_BLOCK_RE.finditer(text):
        body = m.group(1)
        name_m = _NAME_RE.search(body)
        tex_m = _TEXTURE_RE.search(body)
        if name_m and tex_m:
            out.append((name_m.group(1), tex_m.group(1)))
    return out


def _resolve_texture(mod_path, hoi4_path, texture):
    """贴图路径 → (abs_path, source)（mod 优先，游戏回退）。"""
    tex = texture.strip()
    if tex.startswith("./"):
        tex = tex[2:]
    if not tex or tex.startswith("http"):
        return None, None
    if mod_path:
        p = os.path.join(mod_path, tex.replace("/", os.sep))
        if os.path.isfile(p):
            return p, "mod"
    if hoi4_path:
        p = os.path.join(hoi4_path, tex.replace("/", os.sep))
        if os.path.isfile(p):
            return p, "vanilla"
    return None, None


def _file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build_icon_manifest(mod_path, hoi4_path, compute_md5=True,
                        progress=None):
    """构建图标清单。

    Returns:
        dict: {"entries": [...], "stats": {...}, "mod_path", "game_path"}
        entry: {"name", "texture", "source", "file", "size": [w, h],
                "md5"|None, "missing": bool}
    """
    entries = []
    seen_names = set()
    total_files = sum(1 for _ in _iter_gfx_files(mod_path, hoi4_path))
    for i, (rel, gfx_path, source) in enumerate(
            _iter_gfx_files(mod_path, hoi4_path)):
        for name, texture in _parse_sprites(gfx_path):
            if name in seen_names:
                continue
            seen_names.add(name)
            abs_path, tex_source = _resolve_texture(
                mod_path, hoi4_path, texture)
            entry = {"name": name, "texture": texture,
                     "source": tex_source or source,
                     "file": rel, "size": None, "md5": None,
                     "missing": abs_path is None}
            if abs_path:
                try:
                    from PIL import Image
                    with Image.open(abs_path) as im:
                        entry["size"] = [im.width, im.height]
                except Exception:
                    entry["size"] = None
                if compute_md5:
                    try:
                        entry["md5"] = _file_md5(abs_path)
                    except OSError:
                        entry["md5"] = None
            entries.append(entry)
        if progress and total_files:
            progress(i + 1, total_files)

    stats = {"total": len(entries),
             "missing": sum(1 for e in entries if e["missing"]),
             "sources": {}}
    for e in entries:
        stats["sources"][e["source"]] = \
            stats["sources"].get(e["source"], 0) + 1
    return {"mod_path": mod_path or "", "game_path": hoi4_path or "",
            "entries": entries, "stats": stats}


def write_icon_manifest(mod_path, hoi4_path, out_path):
    """导出图标清单 JSON（原子写）。返回清单 dict。"""
    manifest = build_icon_manifest(mod_path, hoi4_path)
    atomic_write_text(out_path, json.dumps(
        {"stats": manifest["stats"], "entries": manifest["entries"]},
        ensure_ascii=False, indent=1))
    return manifest


class IconManifest:
    """图标清单加载/查询封装。"""

    def __init__(self, entries):
        self._by_name = {e["name"]: e for e in entries}

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data.get("entries", []))

    @property
    def names(self):
        return list(self._by_name)

    def get(self, name):
        return self._by_name.get(name)

    def search(self, kw="", source="", limit=200):
        out = []
        for name, e in self._by_name.items():
            if kw and kw not in name:
                continue
            if source and e.get("source") != source:
                continue
            out.append(e)
            if len(out) >= limit:
                break
        return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python icon_manifest.py <mod目录> [游戏目录] [输出json]")
        sys.exit(1)
    mod = sys.argv[1]
    game = sys.argv[2] if len(sys.argv) > 2 else ""
    out = sys.argv[3] if len(sys.argv) > 3 else ""
    manifest = build_icon_manifest(mod, game)
    s = manifest["stats"]
    print("图标清单: 共 %d 个 sprite | 缺贴图 %d | 来源 %s"
          % (s["total"], s["missing"], s["sources"]))
    if out:
        write_icon_manifest(mod, game, out)
        print("已导出: %s" % out)
