"""唯一标识符扫描器（RHoiScribe 补全 A-3 / 未完成计划 P2 内部增强）

跨 mod + 游戏本体扫描"可复用标识符"的重复，防止创建意图冲突。
设计原则（AGENTS §4.9 四层分离 / §4.8）：
  - 纯算法层，无 Qt、无 UI、不写文件；
  - 只把"创建意图"当作重复风险（即各类型的块定义），引用已有内容不在此扫描范围；
  - 国策区分节点 ID（focus/shared_focus/joint_focus = { id = ... }）与树 ID（focus_tree = { id = ... }）；
  - 事件用 命名空间.编号 识别并汇总；
  - 决议/角色用项目自带树解析器精确取块键，减少误报。

用法：
  python tools/unique_id_scanner.py [--mod <mod_path>] [--game <game_path>] [--types focus,decision,event,...]

退出码：0 = 无重复；1 = 找到重复；2 = 参数/路径错误。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

# ---- 正则型扫描器（精确 id = X，低误报） ----

_FOCUS_NODE_RE = re.compile(
    r"(?:^|[\s{])(?:focus|shared_focus|joint_focus)[ ]*=[ ]*\{[^}]*?\bid[ ]*=[ ]*(\w+)", re.M)
_FOCUS_TREE_RE = re.compile(
    r"(?:^|[\s{])focus_tree[ ]*=[ ]*\{[^}]*?\bid[ ]*=[ ]*(\w+)", re.M)
_EVENT_RE = re.compile(r"\bid[ ]*=[ ]*([a-z_][\w]*\.[0-9]+)", re.I | re.M)
_DYNAMIC_MOD_RE = re.compile(
    r"(?:^|[\s{])dynamic_modifier[ ]*=[ ]*\{[^}]*?\bid[ ]*=[ ]*(\w+)", re.M)


def _scan_focus(text):
    return _FOCUS_NODE_RE.findall(text)


def _scan_focus_tree(text):
    return _FOCUS_TREE_RE.findall(text)


def _scan_event(text):
    return _EVENT_RE.findall(text)


def _scan_dynamic_modifier(text):
    return _DYNAMIC_MOD_RE.findall(text)


# ---- 树型扫描器（用项目自带解析器精确取块键） ----

def _block_keys(obj, with_children=True):
    """递归收集块节点键。with_children 时只收有子节点的块（块定义），否则收所有块。"""
    out = []
    for node in getattr(obj, "children", []):
        if node.node_type == "block":
            if with_children and node.children:
                out.append(node.key)
            elif not with_children:
                out.append(node.key)
            out.extend(_block_keys(node.children, with_children))
    return out


def _top_block_keys(obj):
    return [n.key for n in getattr(obj, "children", [])
            if n.node_type == "block"]


def _scan_decision(text):
    """决议 ID = 决策分类块下的深度 1 块键。

    常见结构：`XX_decision_category = { my_decision = { ... } }`
    或 `decision_categories = { XX = { my_decision = { ... } } }`。
    直接收集"有子块的块键"（可能含少量嵌套块误报，可接受）。
    """
    from tree_node import parse_pdx_text_to_nodes
    try:
        nodes = parse_pdx_text_to_nodes(text)
    except Exception:
        return []
    out = []
    for top in nodes:
        if top.node_type != "block":
            continue
        # 顶层块即分类：其子块即决议
        out.extend(_top_block_keys(top))
        # 若顶层是 decision_categories 等聚合块，深入一层
        for child in top.children:
            if child.node_type == "block" and child.children:
                out.extend(_top_block_keys(child))
    return out


def _scan_character(text):
    """角色 ID = characters = { ... } 块的顶层块键。"""
    from tree_node import parse_pdx_text_to_nodes
    try:
        nodes = parse_pdx_text_to_nodes(text)
    except Exception:
        return []
    out = []
    for top in nodes:
        if top.node_type == "block" and top.key == "characters":
            out.extend(_top_block_keys(top))
    return out


# type -> (扫描函数, 建议保留的路径子串; 空=不限制)
SCANNERS = {
    "focus": (_scan_focus, ""),
    "focus_tree": (_scan_focus_tree, ""),
    "decision": (_scan_decision, "decisions"),
    "event": (_scan_event, "events"),
    "character": (_scan_character, "characters"),
    "dynamic_modifier": (_scan_dynamic_modifier, ""),
}

_TYPES_HELP = ",".join(sorted(SCANNERS))

# 只扫描这些目录（覆盖 mod 内容文件的常见位置），避免扫二进制/贴图
_SCAN_SUBDIRS = ("common", "events", "history", "interface", "map")


def _iter_script_files(root):
    """遍历 mod 根下常见内容目录中的 .txt。"""
    if not root or not os.path.isdir(root):
        return
    for sub in _SCAN_SUBDIRS:
        base = os.path.join(root, sub)
        if os.path.isdir(base):
            for f in glob.glob(os.path.join(base, "**", "*.txt"), recursive=True):
                yield f


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fp:
            return fp.read()
    except Exception:
        return ""


def scan_duplicates(mod_path, game_path, types):
    """扫描指定类型标识符，返回 {type: {id: [file:line, ...]}}（仅重复项）。"""
    seen = {}
    roots = [(mod_path, "mod"), (game_path, "game")]
    for root, src in roots:
        for path in _iter_script_files(root):
            text = _read_text(path)
            if not text:
                continue
            rel = os.path.relpath(path, root) if root else path
            label = "[%s] %s" % (src, rel.replace(os.sep, "/"))
            for t in types:
                fn, hint = SCANNERS[t]
                if hint and ("/" + hint + "/") not in ("/" + rel.replace(os.sep, "/")):
                    continue
                for ident in set(fn(text)):
                    if not ident:
                        continue
                    idx = text.find(ident)
                    line_no = text.count("\n", 0, idx if idx >= 0 else 0) + 1
                    seen.setdefault(t, {}).setdefault(ident, []).append(
                        "%s:%d" % (label, line_no))

    dups = {}
    for t, table in seen.items():
        for ident, locs in table.items():
            uniq = sorted(set(locs))
            if len(uniq) > 1:
                dups.setdefault(t, {})[ident] = uniq
    return dups


def _default_settings():
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "settings.json"),
                  "r", encoding="utf-8-sig") as fp:
            s = json.load(fp)
        return s.get("mod_path"), s.get("HOI4_path")
    except Exception:
        return None, None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="唯一标识符重复扫描（跨 mod + 游戏）")
    parser.add_argument("--mod", default=None, help="mod 目录（缺省读 settings.json）")
    parser.add_argument("--game", default=None, help="游戏根目录（缺省读 settings.json）")
    parser.add_argument("--types", default="focus,focus_tree,decision,event",
                        help="要扫描的类型，逗号分隔：%s" % _TYPES_HELP)
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON（机器可读）")
    args = parser.parse_args(argv)

    mod = args.mod
    game = args.game
    if not mod or not game:
        dmod, dgame = _default_settings()
        mod = mod or dmod
        game = game or dgame
    if not mod or not game:
        parser.error("需要 --mod/--game，或项目根 settings.json 提供 mod_path/HOI4_path")

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    unknown = [t for t in types if t not in SCANNERS]
    if unknown:
        parser.error("未知类型: %s（可用: %s）" % (", ".join(unknown), _TYPES_HELP))

    dups = scan_duplicates(mod, game, types)

    if args.json:
        print(json.dumps(dups, ensure_ascii=False, indent=2))
    else:
        total = 0
        for t in types:
            table = dups.get(t, {})
            if not table:
                continue
            print("## %s（%d 个重复标识符）" % (t, len(table)))
            for ident, locs in sorted(table.items()):
                total += 1
                print("  %s" % ident)
                for loc in locs:
                    print("      %s" % loc)
        if total == 0:
            print("未发现重复标识符。")
        else:
            print("共 %d 个重复标识符。" % total)

    return 1 if dups else 0


if __name__ == "__main__":
    sys.exit(main())
