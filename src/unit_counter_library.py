"""单位标牌库（Scenario Forge 移植：unit_counter_libraries 提取 + manifest）

从游戏本体 `gfx/interface/counters/` 提取各军种单位标牌（onmap_*.dds，
NATO 风格地图兵牌），转换为 PNG 存入图标库目录并生成 manifest.json：

    <lib_dir>/
        icon/<category>/<name>.png
        manifest.json

`UnitCounterLibrary` 加载器提供名称/类别查询，供浏览对话框、
OOB 编辑器兵牌与模板管理使用。导入工具：
    python tools/import_unit_counter_library.py --game <游戏目录> [--out <库目录>]
"""

from __future__ import annotations
from project_paths import PROJECT_ROOT

import hashlib
import json
import os

from write_utils import atomic_write_text

# 游戏内标牌类别子目录（gfx/interface/counters/<category>/）
COUNTER_SUBDIRS = ("air_small", "divisions_large", "divisions_small",
                   "division_templates_large", "division_templates_small",
                   "ships_small")

MANIFEST_NAME = "manifest.json"


def default_library_dir():
    """默认库目录：项目根 unit_counter_library/。"""
    return os.path.join(PROJECT_ROOT, "unit_counter_library")


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _dds_to_png_bytes(dds_path):
    """DDS → PNG 字节（PIL 解码；失败返回 None）。"""
    from PIL import Image
    import io
    with Image.open(dds_path) as im:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()


def import_unit_counter_library(game_path, out_dir=None, progress=None):
    """从游戏目录提取单位标牌图标库。

    Args:
        game_path: HOI4 游戏根目录
        out_dir: 输出库目录（默认项目根 unit_counter_library/）
        progress: 可选 fn(done, total)

    Returns:
        dict: {"out_dir", "categories", "total", "skipped"}
    """
    out_dir = out_dir or default_library_dir()
    counters_root = os.path.join(game_path, "gfx", "interface", "counters")
    if not os.path.isdir(counters_root):
        raise ValueError(
            "游戏目录中找不到 gfx/interface/counters/：%s" % counters_root)

    icon_dir = os.path.join(out_dir, "icon")
    os.makedirs(icon_dir, exist_ok=True)

    entries = []
    skipped = 0
    files = []
    for root, _dirs, names in os.walk(counters_root):
        for name in sorted(names):
            if name.lower().endswith(".dds"):
                files.append(os.path.join(root, name))
    for i, dds in enumerate(files):
        rel = os.path.relpath(dds, counters_root).replace("\\", "/")
        parts = rel.split("/")
        category = parts[0] if len(parts) > 1 else "misc"
        stem = os.path.splitext(parts[-1])[0]
        png_name = stem + ".png"
        png_rel = os.path.join("icon", category, png_name).replace("\\", "/")
        png_abs = os.path.join(out_dir, png_rel)
        try:
            data = _dds_to_png_bytes(dds)
            if data is None:
                skipped += 1
                continue
            os.makedirs(os.path.dirname(png_abs), exist_ok=True)
            # 二进制图片写入（非文本，不触发写入纪律）
            with open(png_abs, "wb") as f:
                f.write(data)
            from PIL import Image
            import io
            with Image.open(io.BytesIO(data)) as im:
                size = [im.width, im.height]
            entries.append({
                "name": stem, "category": category, "file": png_rel,
                "size": size, "md5": _md5(png_abs),
                "source": "vanilla",
                "source_file": os.path.relpath(
                    dds, game_path).replace("\\", "/"),
            })
        except Exception:
            skipped += 1
        if progress and files:
            progress(i + 1, len(files))

    manifest = {
        "library": "hoi4-unit-counters",
        "categories": sorted({e["category"] for e in entries}),
        "entries": entries,
    }
    atomic_write_text(os.path.join(out_dir, MANIFEST_NAME),
                      json.dumps(manifest, ensure_ascii=False, indent=1))
    return {"out_dir": out_dir, "categories": manifest["categories"],
            "total": len(entries), "skipped": skipped}


class UnitCounterLibrary:
    """单位标牌库加载器（名称/类别查询）。"""

    def __init__(self, lib_dir=None):
        self.lib_dir = lib_dir or default_library_dir()
        self.categories = []
        self._by_name = {}
        self._load()

    def _load(self):
        fp = os.path.join(self.lib_dir, MANIFEST_NAME)
        if not os.path.isfile(fp):
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.categories = list(data.get("categories", []))
            for e in data.get("entries", []):
                self._by_name[e["name"]] = e
        except Exception:
            self.categories = []
            self._by_name = {}

    @property
    def is_ready(self):
        return bool(self._by_name)

    @property
    def names(self):
        return sorted(self._by_name)

    def get(self, name):
        return self._by_name.get(name)

    def entries_in(self, category):
        return [e for e in self._by_name.values()
                if e.get("category") == category]

    def search(self, kw=""):
        out = []
        for name, e in sorted(self._by_name.items()):
            if kw and kw not in name:
                continue
            out.append(e)
        return out

    def abs_path(self, entry):
        """条目 → 库内绝对路径。"""
        return os.path.join(self.lib_dir,
                            entry["file"].replace("/", os.sep))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python unit_counter_library.py <游戏目录> [输出库目录]")
        sys.exit(1)
    game = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else ""
    r = import_unit_counter_library(game, out or None)
    print("已导入 %d 个标牌（%d 个跳过）到 %s"
          % (r["total"], r["skipped"], r["out_dir"]))
    print("类别: %s" % ", ".join(r["categories"]))
