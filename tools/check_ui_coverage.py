# -*- coding: utf-8 -*-
"""临时 UI 覆盖检测程序：调用 PDX 解析器查询“未覆盖词条”。

用途：
  按 PROJECT_DOC.md §4.2，检测当前 UI/工作台设计是否覆盖了参考目录中的全部内容。
  参考目录：
    1. 游戏根目录（settings.json 的 HOI4_path）
    2. mod 目录（settings.json 的 mod_path）
    3. E:\\SteamLibrary\\steamapps\\workshop\\content\\394360

原理：
  - 遍历参考目录下的 PDX 文本文件（.txt/.gui/.lua/.mod/.gfx/.asset/.csv）
  - 使用 src/tree_node.parse_pdx_text_to_nodes 解析顶层词条（key）
  - 按文件路径匹配 CONTENT_TYPES，判断该类型当前是：
      dedicated（专属 UI） / partial（部分 UI） / none（无专属 UI）
  - 对 dedicated/partial 类型，再按已知覆盖键检查是否有未覆盖词条；
  - 对 none 类型，全部顶层词条都视为“未覆盖（无专属 UI）”。

输出为 Markdown 风格的统计与清单，可直接作为 UI 设计覆盖参考。

用法：
  python tools/check_ui_coverage.py [--max-files N] [--root PATH ...]
"""

import os
import sys

# 让脚本可直接从仓库根运行
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from project_paths import PROJECT_ROOT, project_path
from content_types import CONTENT_TYPES, SPECIAL_TYPE_KEYS, ICON_RULES
from tree_node import parse_pdx_text_to_nodes


# 已有部分 UI（图标画廊/辅助对话框）的类型
PARTIAL_TYPES = set(ICON_RULES) - set(SPECIAL_TYPE_KEYS)
PARTIAL_TYPES |= {"advisor_assign", "country_history", "localisation"}

# 专属/部分 UI 已覆盖的顶层词条；None 表示“该类型任意顶层词条都视为已覆盖”
COVERED_KEYS = {
    # 专属 UI
    "focus": {"focus_tree", "shared_focus", "joint_focus"},
    "tech": {"technologies", "technology"},
    "initial_oob": {
        "division_template", "units", "Units",
        "air_wings", "air_wing", "division", "ship", "fleet", "task_force",
    },
    "bop": None,
    "ai_strategy_plans": None,
    "ai_strategy": None,
    "ai_division": None,
    "ai_equipment": None,
    "ai_navy": None,
    "ai_faction_theaters": None,
    "ai_areas": None,
    "ai_focuses": None,
    # 部分 UI
    "character": {"characters"},
    "idea": {"ideas"},
    "event": {
        "country_event", "news_event", "state_event",
        "operative_leader_event", "dynamic_event",
    },
    "super_event": {"country_event", "news_event", "event"},
    "bookmark": {"bookmarks"},
    "special_project": None,
    "advisor_assign": {"every_possible_country", "every_other_country"},
    "country_history": None,
    "localisation": None,  # yml 非 PDX，暂不扫描
}


PDX_EXTS = {".txt", ".gui", ".lua", ".mod", ".gfx", ".asset", ".csv"}
SKIP_DIR_PARTS = {".git", "__pycache__", ".runtime", ".idea", ".venv", ".jspace",
                  ".opensquilla", ".opensquilla-cache", ".agents", ".codex"}


def _default_roots():
    """从 settings.json 读取参考目录，并补充 Workshop 目录。"""
    roots = []
    settings_path = project_path("settings.json")
    settings = {}
    try:
        with open(settings_path, "r", encoding="utf-8-sig") as f:
            import json
            settings = json.load(f)
    except Exception:
        pass
    hoi4 = settings.get("HOI4_path", "")
    mod = settings.get("mod_path", "")
    if hoi4 and os.path.isdir(hoi4):
        roots.append(hoi4)
    if mod and os.path.isdir(mod):
        roots.append(mod)
    workshop = r"E:\SteamLibrary\steamapps\workshop\content\394360"
    if os.path.isdir(workshop):
        roots.append(workshop)
    return roots


def _match_content_type(relpath):
    """按相对路径匹配 CONTENT_TYPES，返回最具体的类型 key（找不到返回 None）。"""
    norm = relpath.replace("\\", "/").lstrip("/")
    best = None
    best_len = -1
    for key, _name, _icon, folders, _tpl, _ext in CONTENT_TYPES:
        for folder in folders:
            f = folder.strip("/")
            if f == ".":
                continue  # generic 兜底最后处理
            if norm == f or norm.startswith(f + "/"):
                if len(f) > best_len:
                    best_len = len(f)
                    best = key
    if best is None:
        # 仅根目录 .mod 描述文件归为 generic；其余无法识别的非内容文件跳过
        if norm.endswith(".mod"):
            return "generic"
        return None
    return best


def _iter_pdx_files(root, max_files=0):
    """遍历 root 下 PDX 文本文件；max_files>0 时最多产出该数量。"""
    count = 0
    for dp, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_PARTS]
        for name in names:
            ext = os.path.splitext(name)[1].lower()
            if ext not in PDX_EXTS:
                continue
            yield os.path.join(dp, name)
            count += 1
            if max_files and count >= max_files:
                return


def _top_keys(content):
    """调用 PDX 解析器，返回文件顶层词条 key 列表。"""
    try:
        nodes = parse_pdx_text_to_nodes(content)
    except Exception:
        return []
    keys = []
    for node in nodes:
        if getattr(node, "key", ""):
            keys.append(node.key)
    return keys


def _record(agg, status, type_key, key, relpath):
    bucket = agg.setdefault(status, {})
    by_type = bucket.setdefault(type_key, {})
    info = by_type.setdefault(key, {"count": 0, "examples": []})
    info["count"] += 1
    if len(info["examples"]) < 3 and relpath not in info["examples"]:
        info["examples"].append(relpath)


def scan_roots(roots, max_files=0):
    """扫描所有 root，返回聚合结果。"""
    agg = {
        "dedicated_uncovered": {},   # 专属 UI 内未覆盖
        "partial_missing": {},       # 部分 UI 内未覆盖
        "none_type": {},             # 无专属 UI 类型的全部词条
    }
    stats = {"files": 0, "parsed": 0, "failed": 0}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for fp in _iter_pdx_files(root, max_files=max_files):
            stats["files"] += 1
            try:
                with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read()
            except Exception:
                stats["failed"] += 1
                continue
            rel = os.path.relpath(fp, root).replace("\\", "/")
            type_key = _match_content_type(rel)
            if type_key is None:
                continue
            stats["parsed"] += 1
            keys = _top_keys(content)
            if type_key in SPECIAL_TYPE_KEYS:
                covered = COVERED_KEYS.get(type_key)
                if covered is None:
                    continue
                for k in keys:
                    if k not in covered:
                        _record(agg, "dedicated_uncovered", type_key, k, rel)
            elif type_key in PARTIAL_TYPES:
                covered = COVERED_KEYS.get(type_key)
                if covered is None:
                    continue
                for k in keys:
                    if k not in covered:
                        _record(agg, "partial_missing", type_key, k, rel)
            else:
                for k in keys:
                    _record(agg, "none_type", type_key, k, rel)
    return agg, stats


def _render_bucket(bucket, title):
    lines = []
    lines.append("### " + title)
    lines.append("")
    total = sum(info["count"] for by_type in bucket.values()
                for info in by_type.values())
    lines.append(f"未覆盖词条总数（含重复出现）：**{total}**")
    lines.append("")
    for type_key in sorted(bucket):
        by_key = bucket[type_key]
        lines.append(f"#### 类型 `{type_key}`")
        lines.append("")
        lines.append("| 词条 | 出现次数 | 示例文件 |")
        lines.append("| --- | --- | --- |")
        for key in sorted(by_key, key=lambda k: (-by_key[k]["count"], k)):
            info = by_key[key]
            ex = info["examples"][0] if info["examples"] else ""
            lines.append(f"| `{key}` | {info['count']} | `{ex}` |")
        lines.append("")
    if not bucket:
        lines.append("（无）")
        lines.append("")
    return "\n".join(lines)


def build_report(agg, stats, roots):
    lines = []
    lines.append("# UI 覆盖检测报告（未覆盖词条）")
    lines.append("")
    lines.append("- 扫描目录：")
    for r in roots:
        lines.append(f"  - `{r}`")
    lines.append(f"- 文件数：{stats['files']}；成功解析：{stats['parsed']}；失败：{stats['failed']}")
    lines.append("")
    lines.append(_render_bucket(agg["dedicated_uncovered"],
                                "一、专属 UI 内未覆盖词条（已有设计器，但文件里还有未展示内容）"))
    lines.append(_render_bucket(agg["partial_missing"],
                                "二、部分 UI 内未覆盖词条（有画廊/辅助，但缺少完整专属设计）"))
    lines.append(_render_bucket(agg["none_type"],
                                "三、无专属 UI 类型（全部顶层词条均视为待设计）"))
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="UI 覆盖检测（未覆盖词条查询）")
    parser.add_argument("--max-files", type=int, default=0,
                        help="每个目录最多扫描文件数（0=不限制）")
    parser.add_argument("--root", action="append", default=[],
                        help="额外参考目录，可多次指定；不指定时使用 settings + Workshop")
    args = parser.parse_args()

    roots = list(args.root) or _default_roots()
    if not roots:
        print("未找到任何参考目录，请通过 --root 指定，或检查 settings.json。")
        return 1
    agg, stats = scan_roots(roots, max_files=args.max_files)
    report = build_report(agg, stats, roots)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
