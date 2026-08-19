"""本地化编辑器数据层（算法层）

负责扫描 mod / 游戏本地化目录、解析 yml、构建统一词条列表，
并提供按文件 upsert / delete 的写回能力（只写 mod，不写游戏文件）。

支持多语言：
  - 默认简体中文（simp_chinese）
  - 英文（english）作为可选语言
  - 英文模式可同时提供中文参考值

与 translation_editor.py 的分工：
  - translation_editor.py 面向“单文件/单类型”的保存（focus/ideas 等专用文件）
  - 本模块面向“全量本地化词条浏览与编辑”，需要记录每个键所在的来源文件
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from localization_mgr import LOC_PATTERN
from write_utils import atomic_write_text

# 默认语言：简体中文
DEFAULT_LANG = "simp_chinese"

# 可选语言（可按需扩展）
SUPPORTED_LANGS = ("simp_chinese", "english")

# 语言显示名
LANG_LABELS = {
    "simp_chinese": "简体中文",
    "english": "English",
}

# 常见的本地化目录拼写（英式 localisation / 美式 localization）
LOC_DIR_NAMES = ("localisation", "localization")

# 修正类词条快速筛选关键词（大小写不敏感）
MODIFIER_KEY_HINTS = (
    "modifier_",
    "opinion_",
    "dynamic_modifier",
    "resistance_",
    "compliance_",
    "modifier",
)


def default_loc_filename(lang: str = DEFAULT_LANG) -> str:
    """返回指定语言的默认 mod 本地化文件名。"""
    return "generic_mod_l_{}.yml".format(lang)


def _loc_subdir(mod_or_game_path: str, lang: str = DEFAULT_LANG) -> List[str]:
    """返回存在的本地化目录（localisation / localization 两种拼写）。"""
    dirs = []
    if not mod_or_game_path:
        return dirs
    for name in LOC_DIR_NAMES:
        d = os.path.join(mod_or_game_path, name, lang)
        if os.path.isdir(d):
            dirs.append(d)
    return dirs


def list_loc_files(scope_path: str, lang: str = DEFAULT_LANG) -> List[str]:
    """列出路径范围内的指定语言 yml 文件（含两种目录拼写）。"""
    files = []
    for d in _loc_subdir(scope_path, lang):
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for fn in names:
            if fn.endswith("_l_{}.yml".format(lang)):
                files.append(os.path.join(d, fn))
    return files


def _read_yml_lines(filepath: str) -> List[str]:
    """以 UTF-8-SIG 读取 yml 文件行（本地化文件惯例带 BOM）。"""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return f.readlines()


def _parse_yml_into(filepath: str, cache: Dict[str, str],
                    lang: str = DEFAULT_LANG):
    """解析单个 yml 文件中指定语言节，写入 cache（key -> value）。"""
    header = "l_{}:".format(lang)
    try:
        lines = _read_yml_lines(filepath)
    except OSError:
        return
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == header:
            in_section = True
            continue
        if in_section and stripped.startswith("l_") and stripped != header:
            in_section = False
            continue
        if not in_section:
            continue
        if stripped.startswith("#") or not stripped:
            continue
        m = LOC_PATTERN.match(stripped)
        if m:
            key = m.group(1)
            val = m.group(2) or m.group(3) or m.group(4)
            if key and val:
                cache[key] = val


def load_loc_file(filepath: str, lang: str = DEFAULT_LANG) -> Dict[str, str]:
    """解析单个 yml 文件为 key -> value 字典。"""
    cache: Dict[str, str] = {}
    _parse_yml_into(filepath, cache, lang)
    return cache


def load_loc_dir(scope_path: str, lang: str = DEFAULT_LANG) -> Dict[str, str]:
    """加载路径范围内的全部指定语言 yml 文件（mod 或 game）。"""
    cache: Dict[str, str] = {}
    for fp in list_loc_files(scope_path, lang):
        _parse_yml_into(fp, cache, lang)
    return cache


def load_effective_dict(mod_path: str, hoi4_path: str = "",
                        lang: str = DEFAULT_LANG) -> Dict[str, str]:
    """加载指定语言的有效词条字典：先游戏后 mod，mod 覆盖游戏。"""
    cache: Dict[str, str] = {}
    if hoi4_path:
        game = load_loc_dir(hoi4_path, lang)
        cache.update(game)
    mod = load_loc_dir(mod_path, lang)
    cache.update(mod)
    return cache


def build_entries(mod_path: str, hoi4_path: str = "",
                  lang: str = DEFAULT_LANG) -> List[dict]:
    """构建指定语言的全量本地化词条列表。

    返回顺序：先 mod 文件顺序，后仅存在于游戏的词条（按 key 排序）。
    每个词条字段：
        key       本地化键
        value     当前值（mod 优先，无 mod 时为游戏值）
        game_value游戏原文（无则为空）
        source    "mod" / "game"
        file      mod 文件路径（source=mod 时有效），否则 None
    """
    entries: List[dict] = []
    seen_mod_keys = set()

    # 1) mod 词条：记录来源文件
    for fp in list_loc_files(mod_path, lang):
        cache = load_loc_file(fp, lang)
        for key, val in cache.items():
            seen_mod_keys.add(key)
            entries.append({
                "key": key,
                "value": val,
                "game_value": "",
                "source": "mod",
                "file": fp,
            })

    # 2) 游戏词条：补齐 mod 未覆盖的键
    game_cache = load_loc_dir(hoi4_path, lang) if hoi4_path else {}
    for key in sorted(game_cache):
        if key in seen_mod_keys:
            # 补充 mod 词条的 game_value
            for entry in entries:
                if entry["key"] == key:
                    entry["game_value"] = game_cache[key]
                    break
        else:
            entries.append({
                "key": key,
                "value": game_cache[key],
                "game_value": game_cache[key],
                "source": "game",
                "file": None,
            })

    return entries


def default_mod_loc_file(mod_path: str, lang: str = DEFAULT_LANG) -> str:
    """返回默认 mod 本地化文件完整路径（不存在也会返回目标路径）。"""
    d = os.path.join(mod_path, "localisation", lang)
    return os.path.join(d, default_loc_filename(lang))


def _section_header(lang: str = DEFAULT_LANG) -> str:
    return "l_{}:".format(lang)


def _parse_existing_lines(lines: List[str], lang: str = DEFAULT_LANG):
    """解析现有文本行，返回 (section_start_index, key->line_idx)。

    仅处理 lang 对应节；其他语言节保持原样。
    """
    header = _section_header(lang)
    start_idx = -1
    key_map = {}
    in_section = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == header:
            in_section = True
            start_idx = idx
            continue
        if in_section and stripped.startswith("l_") and stripped != header:
            in_section = False
            continue
        if not in_section:
            continue
        if stripped.startswith("#") or not stripped:
            continue
        m = LOC_PATTERN.match(stripped)
        if m:
            key_map[m.group(1)] = idx
    return start_idx, key_map


def upsert_loc_entry(filepath: str, key: str, value: str,
                     lang: str = DEFAULT_LANG) -> bool:
    """向指定 mod 本地化文件写入/更新一个词条。

    保持已有文件顺序；文件不存在或缺少对应语言节时自动创建。
    写入使用 utf-8-sig（HOI4 本地化惯例）。
    """
    if not key or value is None:
        return False
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    header = _section_header(lang)

    lines = []
    if os.path.isfile(filepath):
        try:
            lines = _read_yml_lines(filepath)
        except OSError:
            return False

    start_idx, key_map = _parse_existing_lines(lines, lang)

    if start_idx < 0:
        # 没有对应语言节：追加节头
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(header + "\n")
        start_idx = len(lines) - 1
        key_map = {}

    new_line = ' {}: "{}"\n'.format(
        key, value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))

    if key in key_map:
        lines[key_map[key]] = new_line
    else:
        # 插到当前节末尾（节内最后一个非空行之后，保持注释/空行在节内次序尽量靠前）
        insert_at = len(lines)
        for idx in range(start_idx + 1, len(lines)):
            stripped = lines[idx].strip()
            if stripped.startswith("l_") or (stripped and not stripped.startswith("#")):
                insert_at = idx + 1
        lines.insert(insert_at, new_line)

    try:
        atomic_write_text(filepath, "".join(lines), encoding="utf-8-sig",
                          allow_bom=True)
        return True
    except Exception:
        return False


def delete_loc_entry(filepath: str, key: str,
                     lang: str = DEFAULT_LANG) -> bool:
    """从指定 mod 本地化文件删除一个词条（保留其他内容）。"""
    if not key or not os.path.isfile(filepath):
        return False
    try:
        lines = _read_yml_lines(filepath)
    except OSError:
        return False

    _, key_map = _parse_existing_lines(lines, lang)
    if key not in key_map:
        return True  # 不存在视为成功

    del lines[key_map[key]]
    try:
        atomic_write_text(filepath, "".join(lines), encoding="utf-8-sig",
                          allow_bom=True)
        return True
    except Exception:
        return False


def find_mod_file_for_key(mod_path: str, key: str,
                          lang: str = DEFAULT_LANG) -> Optional[str]:
    """在 mod 本地化文件中查找包含指定 key 的文件；找不到返回 None。"""
    if not key or not mod_path:
        return None
    for fp in list_loc_files(mod_path, lang):
        if key in load_loc_file(fp, lang):
            return fp
    return None


def find_missing_loc_keys(mod_path: str, hoi4_path: str = "",
                          lang: str = DEFAULT_LANG) -> List[dict]:
    """扫描 mod 内容实体，返回当前语言缺失的本地化词条。

    复用 validation.collect_entity_keys 的实体键提取逻辑。
    返回：[{key, type, country, file, loc_keys, missing_keys}]
    """
    from validation import collect_entity_keys
    entities = collect_entity_keys(mod_path)
    if not entities:
        return []
    existing = load_effective_dict(mod_path, hoi4_path, lang)
    out = []
    for e in entities:
        miss = [k for k in (e.get("loc_keys") or [e.get("key")]) if k and k not in existing]
        if miss:
            item = dict(e)
            item["missing_keys"] = miss
            out.append(item)
    return out


def batch_fill_missing_loc(mod_path: str, hoi4_path: str = "",
                           lang: str = DEFAULT_LANG,
                           target_file: Optional[str] = None) -> tuple:
    """批量补写缺失本地化词条到 mod 文件。

    参数：
        mod_path     mod 根目录
        hoi4_path    游戏根目录（用于取英文原文占位）
        lang         目标语言
        target_file  目标文件；None 时使用默认 mod 文件

    返回：
        (写入条数, 目标文件路径)
    """
    missing = find_missing_loc_keys(mod_path, hoi4_path, lang)
    if not missing:
        target = target_file or default_mod_loc_file(mod_path, lang)
        return 0, target

    # 英文原文（用于中文补写占位）
    english = load_effective_dict(mod_path, hoi4_path, "english") if hoi4_path else {}

    target = target_file or default_mod_loc_file(mod_path, lang)
    written = 0
    for m in missing:
        for key in (m.get("missing_keys") or [m.get("key")]):
            if not key:
                continue
            existing = load_loc_file(target, lang)
            if key in existing:
                continue
            # 中文补写优先用游戏/已有英文值，无值用 key 占位
            if lang == "simp_chinese":
                val = english.get(key) or key
            else:
                val = key
            if upsert_loc_entry(target, key, val, lang):
                written += 1
    return written, target


def is_modifier_key(key: str) -> bool:
    """判断一个键是否属于修正类本地化词条（用于快速筛选）。"""
    lower = key.lower()
    return any(hint in lower for hint in MODIFIER_KEY_HINTS)


def categorise_key(key: str) -> str:
    """按本地化键前缀/特征返回分组名。"""
    if not key:
        return "其他"
    lower = key.lower()

    if lower.startswith("focus_") or lower.endswith("_focus"):
        return "国策"
    if lower.startswith("decision_") or lower.endswith("_decision"):
        return "决议"
    if lower.startswith("event_") or ".title" in lower or ".desc" in lower:
        return "事件"
    if lower.startswith("idea_") or lower.endswith("_idea"):
        return "理念"
    if lower.startswith("tech_") or lower.endswith("_tech"):
        return "科技"
    if lower.startswith("modifier_") or lower.startswith("opinion_") \
            or lower.startswith("dynamic_modifier") or lower.startswith("resistance_") \
            or lower.startswith("compliance_"):
        return "修正"
    if lower.startswith("portrait_") or "leader_" in lower \
            or lower.startswith("leader_") or lower.endswith("_leader") \
            or lower.endswith("_general") or lower.endswith("_admiral"):
        return "人物"
    if lower.startswith("gui_") or lower.startswith("tooltip_") \
            or lower.startswith("message_") or lower.startswith("button_"):
        return "界面/辅助"
    return "其他"


# 分组下拉显示顺序
LOC_CATEGORIES = ("全部", "国策", "决议", "事件", "理念", "科技",
                  "修正", "人物", "界面/辅助", "其他")