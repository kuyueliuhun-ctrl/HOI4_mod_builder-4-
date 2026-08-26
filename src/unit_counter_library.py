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

    def search(self, kw="", keyword=None, category=None):
        """按名称子串 / 类别筛选标牌库条目。

        kw 为旧调用；keyword/category 兼容 `list_unit_counters` 的传参。
        """
        q = kw or keyword or ""
        out = []
        for name, e in sorted(self._by_name.items()):
            if q and q not in name:
                continue
            if category and e.get("category") != category:
                continue
            out.append(e)
        return out

    def abs_path(self, entry):
        """条目 → 库内绝对路径。"""
        return os.path.join(self.lib_dir,
                            entry["file"].replace("/", os.sep))


# ---------------------------------------------------------------------------
# 兵种类型 → 标牌库条目 解析（P2：兵牌图标接标牌库）
# ---------------------------------------------------------------------------

# HOI4 sub_units 类型键 → 标牌库名称主干（不含 unit_/onmap_unit_/support_unit_ 前缀、_icon 后缀）
# 覆盖「键名与库内名称不一致」的常见兵种；其余靠精确匹配 + 后缀剥离兜底。
_TYPE_STEM_ALIASES = {
    "mountaineers": "mountain",
    "paratrooper": "paratroop",
    "light_armor": "light_tank",
    "medium_armor": "medium_tank",
    "amphibious_armor": "amphibious_tank",
    "amphibious_light_armor": "light_amphibious_tank",
    "amphibious_medium_armor": "medium_amphibious_tank",
    "amphibious_heavy_armor": "heavy_amphibious_tank",
    "artillery": "art",
    "anti_tank": "at",
    "anti_tank_battery": "at",
    "rocket_artillery": "rocket_art",
    "rocket_artillery_brigade": "rocket_art",
    "rocket_battery": "rocket_art",
    "penal_battalion": "penal_infantry",
    "anti_air_brigade": "anti_air",
    "anti_tank_brigade": "at",
    "artillery_brigade": "art",
    "mot_anti_air_brigade": "mot_anti_air",
    "mot_anti_tank_brigade": "mot_at",
    "mot_artillery_brigade": "mot_art",
    "mot_rocket_artillery_brigade": "mot_rocket_art",
    "motorized_rocket_brigade": "mot_rocket_art",
    "mot_recon": "motorized_recon",
    "light_tank_recon": "armored_car_recon",
    "motorized_military_police": "motorized_military_police",
    "self_propelled_super_heavy_artillery": "self_propelled_super_heavy_artillery",
    "super_heavy_artillery": "super_heavy_artillery",
    "super_heavy_railway_gun": "super_heavy_railway_gun_unit",
    # 自走防空 / 自走火炮 / 坦克歼击车（各吨位）
    "heavy_sp_anti_air_brigade": "heavy_spaa",
    "heavy_sp_anti_air_support": "heavy_spaa",
    "heavy_sp_artillery_brigade": "heavy_spart",
    "heavy_sp_artillery_support": "heavy_spart",
    "light_sp_anti_air_brigade": "light_spaa",
    "light_sp_anti_air_support": "light_spaa",
    "light_sp_artillery_brigade": "light_spart",
    "light_sp_artillery_support": "light_spart",
    "medium_sp_anti_air_brigade": "medium_spaa",
    "medium_sp_anti_air_support": "medium_spaa",
    "medium_sp_artillery_brigade": "medium_spart",
    "medium_sp_artillery_support": "medium_spart",
    "modern_sp_anti_air_brigade": "modern_spaa",
    "modern_sp_anti_air_support": "modern_spaa",
    "modern_sp_artillery_brigade": "modern_spart",
    "modern_sp_artillery_support": "modern_spart",
    "super_heavy_sp_anti_air_brigade": "super_heavy_armor_antiair",
    "super_heavy_sp_artillery_brigade": "super_heavy_armor_artillery",
    "heavy_flame_tank": "heavy_flamethrower_tank",
    "light_flame_tank": "light_flamethrower_tank",
    "medium_flame_tank": "medium_flamethrower_tank",
    "battle_cruiser": "battlecruiser",
    "airborne_light_armor": "light_tank",
    "ballistic_missile": "v2_rocket",
    "nuclear_missile": "v2_rocket",
    "rocket_interceptor": "v2_rocket",
    "sam_missile": "v2_rocket",
    "strat_bomber_intercontinental": "strat_bomber",
    "cv_cas": "cas",
    "cv_fighter": "fighter",
    "cv_nav_bomber": "nav_bomber",
    "cv_suicide_craft": "suicide_craft",
    "pioneer_support": "pioneers_support",
    "heavy_tank_destroyer_brigade": "heavy_tank_destroyer",
    "heavy_tank_destroyer_support": "heavy_tank_destroyer",
    "light_tank_destroyer_brigade": "light_tank_destroyer",
    "light_tank_destroyer_support": "light_tank_destroyer",
    "medium_tank_destroyer_brigade": "medium_tank_destroyer",
    "medium_tank_destroyer_support": "medium_tank_destroyer",
    "modern_tank_destroyer_brigade": "modern_tank_destroyer",
    "modern_tank_destroyer_support": "modern_tank_destroyer",
    "super_heavy_tank_destroyer_brigade": "super_heavy_armor_at",
    # 海军 / 支援舰
    "repair_ship": "repair_support_ship",
    "support_ship": "general_support_ship",
    # HQ（hq_* 优先具体名，未命中回落通用 HQ）
    "hq_air_liaison": "hq_air_liason",
    "hq_naval_liaison": "hq_naval_liason",
    "hq_specops": "hq_specops",
}

# 可剥离的后缀（先剥后缀再看库）
_TYPE_SUFFIXES = ("_brigade", "_battalion", "_support",
                  "_battery", "_company", "_regiment", "_platoon")

# 带 _icon 后缀的标牌名称前缀（按优先级依次尝试）
_COUNTER_PREFIXES = ("unit", "onmap_unit", "support_unit")

# 无 _icon 后缀的空中/海军标牌前缀（如 onmap_fighter / onmap_battleship）
_COUNTER_RAW_PREFIXES = ("onmap",)

# 通用 HQ 兜底名
_HQ_FALLBACK = "support_unit_hq_icon"


def _candidate_stems(unit_type):
    """生成候选名称主干（去重保序）。"""
    t = str(unit_type or "").strip().replace("-", "_").lower()
    if not t:
        return []
    seen = []

    def _add(x):
        x = x.strip("_")
        if x and x not in seen:
            seen.append(x)

    # 别名（规范大图）优先，其次原始键，最后剥离后缀
    alias = _TYPE_STEM_ALIASES.get(t)
    if alias:
        _add(alias)
    _add(t)
    for suf in _TYPE_SUFFIXES:
        if t.endswith(suf):
            _add(t[: -len(suf)])
            break
    return seen


def find_counter_entry(unit_type, lib=None):
    """兵种类型 → 标牌库条目（dict）或 None。

    按优先级尝试 `unit_<stem>_icon` / `onmap_unit_<stem>_icon` /
    `support_unit_<stem>_icon` / `onmap_<stem>`（空中/海军无 _icon 后缀）；
    hq_* 未命中具体 HQ 图标时回落通用 HQ 图标。lib 可传入已加载的
    UnitCounterLibrary，缺省用进程级缓存实例。
    """
    if lib is None:
        lib = _get_library()
    if not lib.is_ready:
        return None
    stems = _candidate_stems(unit_type)
    for stem in stems:
        for prefix in _COUNTER_PREFIXES:
            entry = lib.get("%s_%s_icon" % (prefix, stem))
            if entry:
                return entry
        for prefix in _COUNTER_RAW_PREFIXES:
            entry = lib.get("%s_%s" % (prefix, stem))
            if entry:
                return entry
        # 库名本身就是主干（如 pioneers_support）
        entry = lib.get(stem)
        if entry:
            return entry
    # HQ 兜底
    t = str(unit_type or "").strip().replace("-", "_").lower()
    if t.startswith("hq_"):
        entry = lib.get(_HQ_FALLBACK)
        if entry:
            return entry
    return None


# 进程级库实例缓存（避免每次查询都读 manifest）
_lib_cache = {}


def _get_library(lib_dir=None):
    lib_dir = lib_dir or default_library_dir()
    lib = _lib_cache.get(lib_dir)
    if lib is None:
        lib = UnitCounterLibrary(lib_dir)
        _lib_cache[lib_dir] = lib
    return lib


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
