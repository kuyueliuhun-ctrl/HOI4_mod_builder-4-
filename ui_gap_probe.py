#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI 缺口探针：检测“树形编辑器中有、专用 UI 中无展示/编辑”的内容。

用途
----
PROJECT_DOC.md §4.2 要求 UI 能展示并编辑文件中的 100% 内容。本程序以「通用树形编辑器」
（generic_tree_editor / TreeNode 解析）为基准，对已有专用/部分专用 UI 的内容类型，
扫描 mod/游戏真实文件，找出：

  1. 顶层内容：文件里有、专用 UI 未处理的顶层块/键；
  2. 嵌套词条：专用 UI 已处理顶层，但其子级仍存在未展示/未编辑的字段/块。

程序只调用项目自身函数（content_types、tree_node、project_paths），不修改任何文件。

用法
----
python ui_gap_probe.py [--types character,focus,tech] [--max-files 5] [--root PATH ...] [--output 报告.md]

无参数时默认扫描 settings.json 的 mod_path 与 HOI4_path，每类型最多 5 个文件，
报告输出到 docs/UI树形缺口检测报告.md。

扩展
----
在 UI_COVERAGE_SPECS 中为每个类型维护“UI 已覆盖路径模式”：
  top:         顶层键集合，或 "*" 表示任意顶层实体块都由 UI 作为实体容器处理
  covered:     已覆盖路径模式列表；"." 分隔层级，"*" 匹配一整段键
  note:        说明

新增/修改专用 UI 后，应同步更新对应 spec，并运行本程序验证缺口收敛。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import sys
import tempfile

# 让脚本可直接从仓库根运行
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from project_paths import PROJECT_ROOT, project_path
from content_types import CONTENT_TYPES
from tree_node import parse_pdx_text_to_nodes, _strip_comments, COMPARE_OPERATORS

# ---------------------------------------------------------------------------
# UI 覆盖规格
# ---------------------------------------------------------------------------

# 常用角色职责类型字段（供 character spec 生成）
_ROLE_FIELD_KEYS = (
    "ideology", "expire", "id",
    "slot", "idea_token", "cost",
    "skill", "attack_skill", "defense_skill", "logistics_skill",
    "planning_skill", "coordination_skill", "bombing_skill",
    "traits", "desc",
)
_ROLE_TYPES = (
    "country_leader", "advisor", "political_advisor", "corps_commander",
    "field_marshal", "navy_leader", "army_leader", "air_leader",
    "unit_leader", "area_defense_leader", "governor",
)

UI_COVERAGE_SPECS = {
    # ---------------- 角色编辑器（批 A 单页三栏） ----------------
    "character": {
        "label": "角色编辑器",
        "top": {"characters"},
        "covered": (["characters.*", "characters.*.name", "characters.*.desc",
                    "characters.*.portraits", "characters.*.instance.**",
                    "characters.*.**"]
                    + ["characters.*.%s.%s" % (r, f)
                       for r in _ROLE_TYPES for f in _ROLE_FIELD_KEYS]),
        "note": "portraits 表可编辑任意 scope/size/texture；role 已知字段可编辑；未知行保留原样；未知块（含 instance = { ... }）经 ScriptBlockEditorDialog 结构化编辑并写回（2026-08-23 复核：--max-files 0 缺口=0，无豁免）",
    },

    # ---------------- 国策树画布 ----------------
    "focus": {
        "label": "国策/科技画布（focus）",
        "top": {"focus_tree", "shared_focus", "joint_focus"},
        "covered": [
            "focus_tree", "focus_tree.focus", "focus_tree.shared_focus",
            "focus_tree.joint_focus",
            "focus_tree.focus.id", "focus_tree.focus.icon",
            "focus_tree.focus.x", "focus_tree.focus.y",
            "focus_tree.focus.cost", "focus_tree.focus.relative_position_id",
            "focus_tree.focus.offset.**", "focus_tree.focus.search_filters.**",
            "focus_tree.focus.prerequisite.**", "focus_tree.focus.mutually_exclusive.**",
            "focus_tree.focus.available.**", "focus_tree.focus.cancel_if_invalid",
            "focus_tree.focus.completion_reward.**", "focus_tree.focus.complete_effect.**",
            "focus_tree.focus.continue_effect.**", "focus_tree.focus.ai_will_do.**",
            "focus_tree.focus.bypass.**", "focus_tree.focus.will_claim_areas",
            "focus_tree.focus.select_effect.**",
        ],
        "note": "节点弹窗常用字段已覆盖；文件级其他键（style/search_filter_prios/常量）与 focus 内部未列嵌套字段仍经通用树编辑器兜底，属长期收敛项（挂 docs/整合计划.md 通用类型 F 批）",
        "ci_exempt": True,
    },

    # ---------------- 科技树画布（B2：低分，几乎只画不改） ----------------
    "tech": {
        "label": "科技编辑器",
        "top": "*",
        "covered": ["*", "*.**"],
        "note": "画布只读拓扑，编辑能力由本编辑器承担；technologies 包装与零散 folder 顶层均由编辑器处理；allow/ai_will_do/category_* 走结构化块，其余字段进 OtherFieldsTable",
    },

    # ---------------- 初始部队 / 编制 / 设计器 ----------------
    "initial_oob": {
        "label": "师编制/OOB 地编/设计器",
        "top": {"division_template", "units", "Units", "air_wings", "air_wing",
                "division", "ship", "fleet", "task_force"},
        "covered": [
            "division_template.**",
            "units.**",
            "Units.**",
            "air_wings.**",
            "air_wing.**",
            "division.**",
            "ship.**",
            "fleet.**",
            "task_force.**",
        ],
        "note": "OOB_COVERED_TOP_KEYS 之外的顶层块（如 division_names_group、instant_effect）会报缺失",
    },

    # ---------------- 力量平衡工作台 ----------------
    "bop": {
        "label": "力量平衡工作台",
        "top": "*",
        "covered": ["*", "*.**"],
        "note": "区间/势力/修正/决议表单全覆盖；动作块位于 common/decisions 文件，由 BOP 编辑器写回",
    },

    # ---------------- AI 内容编辑器 ----------------
    "event": {
        "label": "事件编辑器",
        "top": "*",
        "covered": [
            "*",
            "country_event.**",
            "news_event.**",
            "state_event.**",
            "operative_leader_event.**",
            "dynamic_event.**",
            "unit_leader_event.**",
        ],
        "note": "事件块全部子字段经表单+结构化块+其他字段表覆盖；文件级其他字段表覆盖顶层常量/add_namespace 等非事件键；.** 即整子树",
    },
    "ai_strategy_plans": {
        "label": "AI 战略计划编辑器",
        "top": "*",
        "covered": ["*", "*.name", "*.desc", "*.focus", "*.focus_order"],
        "note": "未知字段走 ScriptBlockEditor 原始 PDX 兜底",
    },
    "ai_strategy": {
        "label": "AI 战略倾向编辑器",
        "top": "*",
        "covered": ["*", "*.allowed", "*.enable", "*.abort", "*.abort_when_not_enabled",
                    "*.ai_strategy.**"],
        "note": "allowed/enable/abort 实际为脚本块，UI 可按需扩展",
    },
    "ai_division": {
        "label": "AI 师模板编辑器",
        "top": "*",
        "covered": ["*", "*.role", "*.available_for", "*.blocked_for",
                    "*.upgrade_prio", "*.target_template.**"],
        "note": "target_template 接 DivisionEditor；其余脚本块仍可能缺失",
    },
    "ai_equipment": {
        "label": "AI 装备编辑器",
        "top": "*",
        "covered": ["*", "*.category", "*.available_for", "*.roles", "*.priority",
                    "*.target_variant.**"],
        "note": "target_variant 接设计器；未知脚本块仍可能缺失",
    },
    "ai_navy": {
        "label": "AI 海军编辑器",
        "top": "*",
        "covered": ["*", "*.required_taskforces", "*.optional_taskforces"],
        "note": "复杂块走树编辑器/raw 兜底",
    },
    "ai_faction_theaters": {
        "label": "AI 派系战区编辑器",
        "top": "*",
        "covered": ["*", "*.name", "*.regions"],
        "note": "未知字段走 ScriptBlockEditor",
    },
    "ai_areas": {
        "label": "AI 区域编辑器",
        "top": "*",
        "covered": ["*", "*.strategic_regions", "*.continents", "*.states"],
        "note": "areas 包装块下的区域实体由侧边栏处理",
    },
    "ai_focuses": {
        "label": "AI 科研权重编辑器",
        "top": "*",
        "covered": ["*", "*.research"],
        "note": "research 键值表已覆盖；其余字段缺失",
    },

    # ---------------- 地图/州编辑器 ----------------
    "state": {
        "label": "地图编辑器（州）",
        "top": {"state"},
        "covered": [
            "state", "state.id", "state.provinces", "state.state_category",
            "state.name", "state.manpower", "state.resources.**",
            "state.history.resources.**",
            "state.history.owner", "state.history.buildings.**",
            "state.history.victory_points.**",
        ],
        "note": "resources/victory_points/manpower/州名/州类别由右侧州字段表单覆盖；history.resources 为兼容 mod 写法；其余 state 嵌套字段（天气/历史/高级建筑等）仍可能走树编辑器，属长期收敛项（收敛计划挂 docs/整合计划.md 通用类型 F 批）",
        "ci_exempt": True,
    },
    "strategic_region": {
        "label": "区域编辑器（战略区域）",
        "top": {"strategic_region"},
        "covered": ["strategic_region", "strategic_region.id", "strategic_region.name",
                    "strategic_region.provinces", "strategic_region.weather",
                    "strategic_region.static_modifiers"],
        "note": "区域编辑器主要做框选划分；字段级编辑仍可能缺失",
    },
    "supply_area": {
        "label": "区域编辑器（补给区域）",
        "top": {"supply_area"},
        "covered": ["supply_area", "supply_area.id", "supply_area.name", "supply_area.value",
                    "supply_area.states"],
        "note": "区域编辑器主要做框选划分；字段级编辑仍可能缺失",
    },
    "country_history": {
        "label": "国家历史文件（变体/顾问等）",
        "top": "*",
        "covered": ["create_equipment_variant.**"],
        "note": "变体（模块/升级）由三设计器覆盖；其余块走树编辑器，逐步收敛（收敛计划挂 docs/整合计划.md 通用类型 F 批）",
        "ci_exempt": True,
    },
}


def _type_folders(type_key):
    for row in CONTENT_TYPES:
        if row[0] == type_key:
            return list(row[3])
    return []


# ---------------------------------------------------------------------------
# 文件扫描与路径收集
# ---------------------------------------------------------------------------

_SKIP_DIR_PARTS = {".git", "__pycache__", ".runtime", ".idea", ".venv",
                   ".jspace", ".opensquilla", ".opensquilla-cache",
                   ".agents", ".codex", "node_modules"}
_PDX_EXTS = {".txt", ".gfx", ".gui", ".lua", ".mod", ".csv"}


def _iter_type_files(root, folders, max_files=0):
    """遍历 root 下匹配 folders 前缀的 PDX 文件。"""
    norm_folders = []
    for f in folders:
        f = f.strip("/")
        if f == ".":
            continue
        norm_folders.append(f)
    seen = 0
    for dp, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIR_PARTS]
        rel = os.path.relpath(dp, root).replace("\\", "/")
        rel = "" if rel == "." else rel
        matched = False
        for f in norm_folders:
            if rel == f or rel.startswith(f + "/"):
                matched = True
                break
        if not matched:
            continue
        for name in sorted(names):
            ext = os.path.splitext(name)[1].lower()
            if ext not in _PDX_EXTS:
                continue
            yield os.path.join(dp, name)
            seen += 1
            if max_files and seen >= max_files:
                return


def _iter_nodes(node):
    """递归产出 TreeNode（含自身）。"""
    yield node
    for child in getattr(node, "children", []):
        for n in _iter_nodes(child):
            yield n


def _fast_tokenize(text):
    """带行号的快速 PDX 分词器（避免 tree_node._tokenize 的 O(n^2) 行号计算）。

    用法与结果同 _tokenize：返回 [(token, line_1based), ...]。
    """
    text = _strip_comments(text)
    tokens = []
    line = 1
    prev = 0
    for m in re.finditer(r'\{|\}|>=|<=|==|!=|=|>|<|"[^"]*"|[\w\.\-]+', text):
        line += text.count("\n", prev, m.start())
        prev = m.start()
        tokens.append((m.group(0), line))
    return tokens


def _collect_entries(content):
    """解析 PDX 文本，返回所有节点条目（含块/词条、级别、键、行号、路径）。

    返回 list[dict]：
      type: "块" | "词条"
      level: 1 起，顶层为 1
      key: 节点键名（裸值/比较语句显示原文）
      line: 所在原始行号（1 起）
      path: 点分路径（供 UI 覆盖匹配；比较语句只用首 token 作段）
    """
    entries = []
    try:
        tokens = _fast_tokenize(content)
    except Exception:
        return entries
    _parse_entries(tokens, 0, len(tokens), 1, "", entries)
    return entries


def _parse_entries(tokens, start, end, level, prefix, out):
    """基于带行号 token 的递归解析，生成条目列表。"""
    i = start
    while i < end:
        tok, line = tokens[i]
        if tok in ("=", "}"):
            i += 1
            continue

        key = tok
        # key = value / key = { ... }
        if i + 1 < end and tokens[i + 1][0] == "=":
            eq_line = tokens[i + 1][1]
            i += 2
            if i < end:
                next_tok, next_line = tokens[i]
                if next_line != eq_line:
                    # 空值
                    path = prefix + key if prefix else key
                    out.append({"type": "词条", "level": level, "key": key,
                                "line": line, "path": path})
                    continue
                if next_tok == "{":
                    path = prefix + key if prefix else key
                    out.append({"type": "块", "level": level, "key": key,
                                "line": line, "path": path})
                    depth = 1
                    block_end = i + 1
                    while block_end < end and depth > 0:
                        if tokens[block_end][0] == "{":
                            depth += 1
                        elif tokens[block_end][0] == "}":
                            depth -= 1
                        block_end += 1
                    _parse_entries(tokens, i, block_end - 1, level + 1,
                                   path + ".", out)
                    i = block_end
                else:
                    path = prefix + key if prefix else key
                    out.append({"type": "词条", "level": level, "key": key,
                                "line": line, "path": path})
                    i += 1
            else:
                path = prefix + key if prefix else key
                out.append({"type": "词条", "level": level, "key": key,
                            "line": line, "path": path})
                i += 1
        else:
            # 比较语句：key >= value / key < value
            if i + 2 < end and tokens[i + 1][0] in COMPARE_OPERATORS:
                op = tokens[i + 1][0]
                val = tokens[i + 2][0].strip('"')
                stmt = "%s %s %s" % (key, op, val)
                path = prefix + key if prefix else key
                out.append({"type": "词条", "level": level, "key": stmt,
                            "line": line, "path": path})
                i += 3
                continue
            # 独立 token（裸值/数组元素）
            if key not in ("{", "}"):
                path = prefix + key if prefix else key
                out.append({"type": "词条", "level": level, "key": key,
                            "line": line, "path": path})
            i += 1


def _segments_regex(pattern):
    """把不含 ** 的点分 pattern 转成正则片段（* = 单段）。"""
    parts = pattern.split(".")
    rx_parts = []
    for p in parts:
        if p == "*":
            rx_parts.append(r"[^.]+")
        else:
            rx_parts.append(re.escape(p))
    return r"\.".join(rx_parts)


def _pattern_to_regex(pattern):
    """把 'a.*.b' / 'a.**' 转成正则。

    - `*` 匹配一个路径段（不含点）
    - `**` 匹配零个或多个路径段（含点），用于“整个子树已覆盖”
    """
    # 最常见的“前缀 + 整个子树”写法：a.b.**
    if pattern.endswith(".**"):
        prefix = pattern[:-3]  # 去掉结尾的 .**
        return re.compile(r"^" + _segments_regex(prefix) + r"(?:\..*)?$",
                          re.DOTALL)
    if ".**" in pattern:
        # 中间出现 **：把 ** 当作可含点的任意后缀
        head, _, tail = pattern.partition(".**")
        tail = tail.lstrip(".")
        rx = _segments_regex(head) + r"(?:\..*)?"
        if tail:
            rx += r"\." + _segments_regex(tail)
        return re.compile(r"^" + rx + r"$", re.DOTALL)
    return re.compile(r"^" + _segments_regex(pattern) + r"$", re.DOTALL)


_COVERED_REGEX_CACHE = {}


def _compile_pattern(pattern):
    rx = _COVERED_REGEX_CACHE.get(pattern)
    if rx is None:
        rx = _pattern_to_regex(pattern)
        _COVERED_REGEX_CACHE[pattern] = rx
    return rx


def _is_covered(path, spec):
    for pat in spec.get("covered", []):
        if _compile_pattern(pat).match(path):
            return True
    return False


def _top_allowed(spec):
    top = spec.get("top")
    if top == "*":
        return True
    return top


def _analyze_entries(entries, spec):
    """返回 (missing_top, missing_fields)。

    missing_top / missing_fields 均为 list[dict]，每个元素是一条缺失条目：
      {"type","level","key","line","path","file"}
    """
    top_allowed = _top_allowed(spec)
    missing_top = []
    missing_fields = []
    for e in entries:
        segs = e["path"].split(".")
        if not segs or not segs[0]:
            continue
        top = segs[0]
        if top_allowed is not True and top not in top_allowed:
            missing_top.append(e)
            continue
        # 顶层容器自身（如 characters / focus_tree / state）视为已处理
        if len(segs) == 1:
            continue
        if not _is_covered(e["path"], spec):
            missing_fields.append(e)
    return missing_top, missing_fields


def _to_local_path(path):
    """把 Windows 盘符路径（E:/... 或 E:\\...）转成当前环境可访问路径。

    - Windows 原生运行：原样返回
    - WSL/Linux 运行：E:/... -> /mnt/e/...
    """
    if not path:
        return path
    normalized = path.replace("\\", "/")
    if os.path.isdir(path) or os.path.isfile(path):
        return path
    m = re.match(r"^([A-Za-z]):/(.*)$", normalized)
    if m and sys.platform.startswith("linux") and os.path.isdir("/mnt"):
        drive = m.group(1).lower()
        rest = m.group(2)
        candidate = "/mnt/%s/%s" % (drive, rest)
        if os.path.isdir(candidate) or os.path.isfile(candidate):
            return candidate
    return path


def _default_roots():
    roots = []
    settings_path = project_path("settings.json")
    try:
        with open(settings_path, "r", encoding="utf-8-sig") as f:
            settings = json.load(f)
    except Exception:
        settings = {}
    hoi4 = settings.get("HOI4_path", "")
    mod = settings.get("mod_path", "")
    for p in (hoi4, mod):
        if not p:
            continue
        local = _to_local_path(p)
        if os.path.isdir(local):
            roots.append(local)
    return roots


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def _render_missing(rows, title):
    lines = ["#### " + title, ""]
    if not rows:
        lines.append("（无缺口）")
        return "\n".join(lines) + "\n"
    folder_trees = {}
    for r in rows:
        folder = os.path.dirname(r.get("file", "")).replace("\\", "/")
        if not folder:
            folder = "."
        _tree_add(folder_trees, folder, r["path"], r["type"], 1)
    lines.append("总缺失条数：**%d**" % len(rows))
    lines.append("")
    for folder in sorted(folder_trees):
        lines.append("##### %s" % folder)
        lines.append("")
        lines.append("```text")
        lines.extend(_render_tree_node(folder_trees[folder], folder, 0))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def build_report(results):
    lines = []
    lines.append("# UI 树形缺口检测报告")
    lines.append("")
    lines.append("> 由 `ui_gap_probe.py` 自动生成：以通用树形编辑器内容为基准，"
                 "检测专用 UI 未展示/未编辑的词条。")
    lines.append("")
    total_top = sum(len(r["missing_top"]) for r in results.values())
    total_fields = sum(len(r["missing_fields"]) for r in results.values())
    lines.append("汇总：缺失顶层词条/块 **%d** 条，缺失嵌套词条/块 **%d** 条。" %
                 (total_top, total_fields))
    lines.append("")
    lines.append("| 类型 | 扫描文件 | 缺失顶层条数 | 缺失嵌套条数 |")
    lines.append("| --- | --- | --- | --- |")
    for type_key in sorted(results):
        r = results[type_key]
        spec = UI_COVERAGE_SPECS.get(type_key, {})
        label = spec.get("label", type_key)
        lines.append("| %s | %d | %d | %d |" % (
            label, r["files"], len(r["missing_top"]), len(r["missing_fields"])))
    lines.append("")
    for type_key in sorted(results):
        r = results[type_key]
        spec = UI_COVERAGE_SPECS.get(type_key, {})
        label = spec.get("label", type_key)
        lines.append("## %s（%s）" % (label, type_key))
        lines.append("")
        if spec.get("note"):
            lines.append("> 说明：%s" % spec["note"])
            lines.append("")
        lines.append("扫描文件：%d" % r["files"])
        lines.append("")
        lines.append(_render_missing(
            r["missing_top"],
            "顶层缺口（文件有，专用 UI 未作为顶层处理）"))
        lines.append(_render_missing(
            r["missing_fields"],
            "嵌套词条缺口（在已处理顶层下，仍无展示/编辑）"))
        lines.append("")
    lines.append("---")
    lines.append("生成时间：由运行命令记录")
    return "\n".join(lines)


def _all_content_folders():
    """返回 CONTENT_TYPES 中全部非 "." 目录前缀（去重）。"""
    seen = set()
    out = []
    for row in CONTENT_TYPES:
        for f in row[3]:
            f = f.strip("/")
            if f and f != "." and f not in seen:
                seen.add(f)
                out.append(f)
    return out


def _default_workers():
    try:
        return max(2, min(32, os.cpu_count() or 4))
    except Exception:
        return 4


def _dump_file_task(root, fp):
    """单文件全量条目聚合任务。

    返回 dict：{folder: {path: {"count": int, "type": "块"|"词条"}}}
    不再返回逐行明细，只保留目录 + 路径聚合计数。
    """
    rel = os.path.relpath(fp, root).replace("\\", "/")
    folder = os.path.dirname(rel).replace("\\", "/")
    if not folder:
        folder = "."
    agg = {}
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
    except Exception:
        return agg
    for e in _collect_entries(content):
        key = (folder, e["path"])
        info = agg.get(key)
        if info is None:
            info = {"count": 0, "type": e["type"]}
            agg[key] = info
        info["count"] += 1
        if e["type"] == "块":
            info["type"] = "块"
    return agg


def _gap_file_task(root, fp, spec):
    """单文件缺口分析任务。返回 (rel, missing_top, missing_fields)。"""
    rel = os.path.relpath(fp, root).replace("\\", "/")
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
    except Exception:
        return rel, [], []
    entries = _collect_entries(content)
    for e in entries:
        e["file"] = rel
    mt, mf = _analyze_entries(entries, spec)
    return rel, mt, mf


def _tree_add(folder_trees, folder, path, type_name, count):
    """把一条路径聚合进 folder_trees[folder] 的嵌套树。"""
    node = folder_trees.get(folder)
    if node is None:
        node = {"children": {}, "count": 0, "type": type_name}
        folder_trees[folder] = node
    node["count"] += count
    if type_name == "块":
        node["type"] = "块"
    segs = path.split(".")
    cur = node
    for seg in segs:
        child = cur["children"].get(seg)
        if child is None:
            child = {"children": {}, "count": 0, "type": type_name}
            cur["children"][seg] = child
        child["count"] += count
        if type_name == "块":
            child["type"] = "块"
        cur = child


def _render_tree_node(node, name=None, indent=0):
    """渲染一棵聚合树节点为 { ... } 缩进文本。"""
    pad = "    " * indent
    suffix = ""
    if node["count"]:
        suffix = "  (x%d)" % node["count"]
    if name is None:
        lines = []
    else:
        lines = ["%s%s%s" % (pad, name, suffix)]
    children = node.get("children") or {}
    if children:
        if name is not None:
            lines[-1] += " {"
        for child_name in sorted(children):
            lines.extend(_render_tree_node(
                children[child_name], child_name, indent + 1))
        if name is not None:
            lines.append("%s}" % pad)
    return lines


def _render_all_rows(rows, files=0, roots=None):
    lines = ["# 全部词条/块分析", ""]
    lines.append("> 由 `ui_gap_probe.py --dump-all` 自动生成："
                 "扫描全部内容类型目录下的全部文件，列出每个词条/块条目。")
    lines.append("")
    # 数量统计
    block_count = sum(1 for r in rows if r["type"] == "块")
    entry_count = sum(1 for r in rows if r["type"] == "词条")
    level_counts = {}
    for r in rows:
        level_counts[r["level"]] = level_counts.get(r["level"], 0) + 1
    lines.append("## 数量统计")
    lines.append("")
    lines.append("| 统计项 | 数量 |")
    lines.append("| --- | --- |")
    lines.append("| 扫描文件数 | %d |" % files)
    lines.append("| 总条数 | %d |" % len(rows))
    lines.append("| 块数 | %d |" % block_count)
    lines.append("| 词条数 | %d |" % entry_count)
    if roots:
        lines.append("| 扫描根目录数 | %d |" % len(roots))
    lines.append("")
    if level_counts:
        lines.append("### 按层级统计")
        lines.append("")
        lines.append("| 第几级 | 条数 |")
        lines.append("| --- | --- |")
        for lv in sorted(level_counts):
            lines.append("| %d | %d |" % (lv, level_counts[lv]))
        lines.append("")
    lines.append("## 明细")
    lines.append("")
    lines.append("总条数：**%d**" % len(rows))
    lines.append("")
    lines.append("| 类型（块，词条） | 第几级 | 词条/块本身 | 所在文件 | 所在行数 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in rows:
        lines.append("| %s | %d | `%s` | `%s` | %d |" % (
            r["type"], r["level"], r["key"], r.get("file", ""), r["line"]))
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="UI 树形缺口探针 / 全部词条分析")
    parser.add_argument("--dump-all", action="store_true",
                        help="全类型全文件输出全部词条/块到 已分析.md")
    parser.add_argument("--types", default="",
                        help="逗号分隔类型 key；默认全部已配置类型（缺口模式）")
    parser.add_argument("--max-files", type=int, default=None,
                        help="每个类型每个根目录最多扫描文件数；0=不限。"
                             "缺口模式默认 5，--dump-all 默认 0")
    parser.add_argument("--collapse-depth", type=int, default=0,
                        help="（已废弃保留兼容）不再折叠")
    parser.add_argument("--root", action="append", default=[],
                        help="额外扫描根目录（可多次）；默认 settings 的 mod+HOI4")
    parser.add_argument("--output", default="",
                        help="输出路径；缺口模式默认 docs/UI树形缺口检测报告.md，"
                             "--dump-all 默认 已分析.md")
    parser.add_argument("--ci", action="store_true",
                        help="CI/门禁模式：非豁免类型存在缺口时返回非零")
    args = parser.parse_args()

    roots = [_to_local_path(r) for r in args.root] or _default_roots()
    if not roots:
        print("未找到可用根目录（请检查 settings.json 的 mod_path/HOI4_path）")
        return 1

    if args.max_files is None:
        max_files = 0 if args.dump_all else 5
    else:
        max_files = args.max_files

    if args.dump_all:
        all_folders = _all_content_folders()
        tasks = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            tasks.extend((root, fp) for fp in _iter_type_files(
                root, all_folders, max_files=max_files))
        out_path = os.path.join(PROJECT_ROOT, args.output or "已分析.md")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        folder_trees = {}
        total_count = 0
        block_count = 0
        entry_count = 0
        level_counts = {}
        workers = _default_workers()
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=workers) as executor:
            futures = [executor.submit(_dump_file_task, root, fp)
                       for root, fp in tasks]
            for fut in concurrent.futures.as_completed(futures):
                agg = fut.result()
                for (folder, path), info in agg.items():
                    _tree_add(folder_trees, folder, path,
                              info["type"], info["count"])
                    total_count += info["count"]
                    if info["type"] == "块":
                        block_count += info["count"]
                    else:
                        entry_count += info["count"]
                    lv = path.count(".") + 1
                    level_counts[lv] = level_counts.get(lv, 0) + info["count"]

        with open(out_path, "w", encoding="utf-8") as out:
            out.write("# 全部词条/块分析\n\n")
            out.write("> 由 `ui_gap_probe.py --dump-all` 自动生成："
                      "全类型全文件遍历，只输出统计与目录/词条树。\n\n")
            out.write("## 数量统计\n\n")
            out.write("| 统计项 | 数量 |\n")
            out.write("| --- | --- |\n")
            out.write("| 扫描文件数 | %d |\n" % len(tasks))
            out.write("| 总条数 | %d |\n" % total_count)
            out.write("| 块数 | %d |\n" % block_count)
            out.write("| 词条数 | %d |\n" % entry_count)
            out.write("| 扫描根目录数 | %d |\n" % len(roots))
            out.write("\n")
            if level_counts:
                out.write("### 按层级统计\n\n")
                out.write("| 第几级 | 条数 |\n")
                out.write("| --- | --- |\n")
                for lv in sorted(level_counts):
                    out.write("| %d | %d |\n" % (lv, level_counts[lv]))
                out.write("\n")
            out.write("## 目录/词条树\n\n")
            for folder in sorted(folder_trees):
                out.write("### %s\n\n" % folder)
                lines = _render_tree_node(folder_trees[folder], folder, 0)
                out.write("```text\n")
                out.write("\n".join(lines))
                out.write("\n```\n\n")
        print("已分析全部条目：%d 条" % total_count)
        print("已写入：%s" % out_path)
        return 0

    if args.types:
        type_keys = [t.strip() for t in args.types.split(",") if t.strip()]
    else:
        type_keys = list(UI_COVERAGE_SPECS.keys())

    results = {}
    for type_key in type_keys:
        spec = UI_COVERAGE_SPECS.get(type_key)
        if not spec:
            print("跳过未配置类型：%s" % type_key)
            continue
        folders = _type_folders(type_key)
        if not folders:
            print("跳过无目录映射类型：%s" % type_key)
            continue
        tasks = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            tasks.extend((root, fp) for fp in _iter_type_files(
                root, folders, max_files=max_files))
        missing_top = []
        missing_fields = []
        workers = _default_workers()
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=workers) as executor:
            futures = [executor.submit(_gap_file_task, root, fp, spec)
                       for root, fp in tasks]
            for fut in concurrent.futures.as_completed(futures):
                _rel, mt, mf = fut.result()
                missing_top.extend(mt)
                missing_fields.extend(mf)
        results[type_key] = {
            "files": len(tasks),
            "missing_top": missing_top,
            "missing_fields": missing_fields,
        }
        print("[%s] files=%d missing_top=%d missing_fields=%d" % (
            type_key, len(tasks), len(missing_top), len(missing_fields)))

    report = build_report(results)
    out_path = os.path.join(PROJECT_ROOT, args.output or "docs/UI树形缺口检测报告.md")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    from write_utils import atomic_write_text
    atomic_write_text(out_path, report, encoding="utf-8", undo=False)
    print("报告已写入：%s" % out_path)
    print("汇总：缺失顶层词条/块 %d 条，缺失嵌套词条/块 %d 条" % (
        sum(len(r["missing_top"]) for r in results.values()),
        sum(len(r["missing_fields"]) for r in results.values())))

    if args.ci:
        bad = []
        for type_key, r in results.items():
            spec = UI_COVERAGE_SPECS.get(type_key, {})
            if spec.get("ci_exempt"):
                continue
            if r["missing_top"] or r["missing_fields"]:
                bad.append("%s top=%d fields=%d" % (
                    type_key, len(r["missing_top"]), len(r["missing_fields"])))
        if bad:
            print("CI 缺口门禁失败：%s" % "; ".join(bad))
            return 1
        print("CI 缺口门禁通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())