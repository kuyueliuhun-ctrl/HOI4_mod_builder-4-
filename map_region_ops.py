"""区域文件操作（无 GUI 依赖，GUI / 契约测试共用）

识别并编辑「定义地块集合」的 mod/游戏文件：
  - strategic_region：map/strategicregions/*.txt
  - supply_area：map/supplyareas/*.txt
  - state：history/states/*.txt（state 块顶层 provinces）

块级写回：只替换目标块的 provinces 内容 / 删除整块 / 追加新块，
保留文件其余内容（注释、其他块、shared_blocks 等）；
写回走 write_utils 原子写（BOM 拒绝 + 撤销快照）。
"""

from __future__ import annotations

import os
import re

REGION_KINDS = {
    "strategic_region": ("map/strategicregions", r"\bstrategic_region\s*=\s*\{"),
    "supply_area": ("map/supplyareas", r"\bsupply_area\s*=\s*\{"),
    "state": ("history/states", r"\bstate\s*=\s*\{"),
}


def _match_block(text, open_index):
    """从 '{' 起做括号配对，返回 (inner_text, end_pos_inclusive)。"""
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
                return text[open_index + 1:i], i
        i += 1
    return text[open_index + 1:], n


def parse_region_file(content, kind):
    """解析单文件 → 区域列表。

    Returns:
        list[dict]: {id, provinces:[int], start, end, inner_start, inner_end}
            start/end 为整块区间（含花括号）；provinces 内容定位见 _provinces_loc
    """
    _dir, pattern = REGION_KINDS.get(kind, (None, None))
    if pattern is None:
        return []
    out = []
    for m in re.finditer(pattern, content):
        start = m.end() - 1
        inner, end = _match_block(content, start)
        if end >= len(content):
            continue
        idm = re.search(r"\bid\s*=\s*(\d+)", inner)
        if not idm:
            continue
        try:
            rid = int(idm.group(1))
        except ValueError:
            continue
        pm = re.search(r"\bprovinces\s*=\s*\{(.*?)\}", inner, re.DOTALL)
        pids = []
        if pm:
            pids = [int(x) for x in re.findall(r"\b(\d+)\b", pm.group(1))]
        out.append({
            "id": rid,
            "provinces": pids,
            "start": start,
            "end": end,
            "inner_start": start + 1,
            "inner_end": end,
        })
    return out


def _provinces_loc(block, block_start):
    """块内 provinces = { ... } 定位。

    Returns:
        (content_start, content_end, indent) 或 None：
        content_start/end 为 provinces 花括号内区间（替换目标），
        indent 为 provinces 行的缩进。
    """
    m = re.search(r"^(\s*)provinces\s*=\s*\{", block, re.MULTILINE)
    if not m:
        return None
    inner, _end = _match_block(block, m.end() - 1)
    return (block_start + m.end(), block_start + m.end() + len(inner),
            m.group(1))


def _format_pids(pids, indent):
    """地块 id 列表 → provinces 块内容（每行 16 个，制表符缩进）。"""
    pids = [int(p) for p in pids if int(p) > 0]
    lines = []
    for i in range(0, len(pids), 16):
        lines.append(indent + " ".join(str(p) for p in pids[i:i + 16]))
    return "\n".join(lines)


def set_region_provinces(content, kind, rid, pids):
    """替换指定区域的 provinces 内容；区域不存在则追加新块。

    Returns:
        str: 新内容（未找到区域且无法追加时返回 None）
    """
    regions = parse_region_file(content, kind)
    for r in regions:
        if r["id"] == rid:
            block = content[r["inner_start"]:r["inner_end"]]
            loc = _provinces_loc(block, r["inner_start"])
            if loc:
                c_start, c_end, indent = loc
                return (content[:c_start] + "\n" + _format_pids(pids, indent)
                        + "\n" + content[c_end:])
            # 块内无 provinces：在块首插入
            idm = re.search(r"^(\s*)id\s*=\s*\d+[^\r\n]*", block,
                            re.MULTILINE)
            base_ind = idm.group(1) if idm else "\t"
            insert = ("\n" + base_ind + "\tprovinces = {\n"
                      + _format_pids(pids, base_ind + "\t") + "\n"
                      + base_ind + "\t}")
            pos = r["inner_start"] + (idm.end() if idm else 0)
            return content[:pos] + insert + content[pos:]
    return append_region(content, kind, rid, pids)


def append_region(content, kind, rid, pids):
    """在文件末尾追加新区域块（kind 名 + id + provinces）。"""
    _dir, pattern = REGION_KINDS.get(kind, (None, None))
    if pattern is None:
        return None
    name = {"strategic_region": "strategic_region",
            "supply_area": "supply_area",
            "state": "state"}.get(kind, kind)
    block = ("\n%s = {\n\tid = %d\n\tprovinces = {\n%s\n\t}\n}\n"
             % (name, int(rid), _format_pids(pids, "\t\t")))
    return content.rstrip() + block


def remove_region(content, kind, rid):
    """删除指定区域整块。返回新内容；未找到返回 None。"""
    regions = parse_region_file(content, kind)
    for r in regions:
        if r["id"] == rid:
            # 连同前导换行一起删除，避免留空行
            start = r["start"]
            if start > 0 and content[start - 1] == "\n":
                start -= 1
            return content[:start] + content[r["end"] + 1:]
    return None


def next_region_id(regions):
    """下一个可用区域 id（现有最大值 + 1）。"""
    max_id = 0
    for r in regions:
        if r["id"] > max_id:
            max_id = r["id"]
    return max_id + 1


def scan_region_files(mod_path, hoi4_path="", kinds=None):
    """扫描 mod+游戏 的区域文件（mod 优先，同相对路径只取 mod）。

    Returns:
        list[dict]: {kind, rel, source, regions:[...]}
    """
    if kinds is None:
        kinds = list(REGION_KINDS)
    out = []
    seen = set()
    for base, source in ((mod_path, "mod"), (hoi4_path, "game")):
        if not base or not os.path.isdir(base):
            continue
        for kind in kinds:
            rel_dir, _pat = REGION_KINDS[kind]
            d = os.path.join(base, rel_dir.replace("/", os.sep))
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if not name.lower().endswith(".txt"):
                    continue
                rel = rel_dir + "/" + name
                if rel in seen:
                    continue
                seen.add(rel)
                try:
                    with open(os.path.join(d, name), "r",
                              encoding="utf-8-sig", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                regions = parse_region_file(content, kind)
                out.append({"kind": kind, "rel": rel, "source": source,
                            "content": content, "regions": regions})
    return out
