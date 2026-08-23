# -*- coding: utf-8 -*-
"""科技（Technology）数据层（算法层，无 Qt）

解析 common/technologies/*.txt：
- 支持 `technologies = { ... }` 包裹与直接顶层科技块两种形态
- 提取 start_year / research_cost / categories / folder{name,position} /
  path / enable_equipments / allow / ai_will_do / sub_technologies /
  special_project_specialization / category_* 装备加成 / priority
- 提供 CRUD 与字段级写回（内容变换，不直接写文件）
"""

from __future__ import annotations

import os
import re

from oob_loader import _block_ranges
from ai_loader import _find_block_bounds, insert_top_block

_TECH_FIELD_RE = re.compile(
    r'\b(start_year|research_cost|folder|priority|special_project_specialization)'
    r'\s*=\s*([^\r\n#]+)')
_CATEGORY_RE = re.compile(r'\bcategories\s*=\s*\{([^}]*)\}')
_PATH_LEADS_RE = re.compile(r'\bleads_to_tech\s*=\s*([\w\.\-]+)')
_SUB_TECH_RE = re.compile(r'\bsub_technologies\s*=\s*\{([^}]*)\}')
_FOLDER_NAME_RE = re.compile(r'\bfolder\s*=\s*\{[^}]*?\bname\s*=\s*([\w\.\-]+)')
_ENABLE_EQUIP_RE = re.compile(r'\benable_equipments\s*=\s*\{([^}]*)\}')

_COVERED_FIELDS = {
    "start_year", "research_cost", "folder", "categories", "path",
    "enable_equipments", "allow", "ai_will_do", "sub_technologies",
}


def _field_value(seg, key):
    m = re.search(r'\b' + re.escape(key) + r'\s*=\s*([^\r\n#]+)', seg)
    if not m:
        return ""
    return m.group(1).strip().strip('"')


def _child_block_text(seg, key):
    for k, depth, start, _end in _block_ranges(seg):
        if depth == 1 and k == key:
            return seg[start:_find_block_bounds(seg, start)[1]]
    return None


def _values_in_block(seg, key):
    bt = _child_block_text(seg, key)
    if not bt:
        return []
    inner = bt[bt.find("{") + 1:bt.rfind("}")]
    clean = re.sub(r"#.*", "", inner)
    return re.findall(r"[\w\.\-]+", clean)


def _parse_folder(seg):
    folder = ""
    x = ""
    y = ""
    m = _FOLDER_NAME_RE.search(seg)
    if m:
        folder = m.group(1)
    fm = re.search(r'\bfolder\s*=\s*\{.*?\bposition\s*=\s*\{', seg, re.S)
    if fm:
        inner = seg[fm.end():]
        bx = re.search(r'\bx\s*=\s*([\w\.\-]+)', inner)
        by = re.search(r'\by\s*=\s*([\w\.\-]+)', inner)
        if bx:
            x = bx.group(1)
        if by:
            y = by.group(1)
    else:
        pm = re.search(r'\bfolder\s*=\s*\{[^}]*?\bposition\s*=\s*([\w\.\-]+)',
                       seg)
        if pm:
            x = pm.group(1)
    return folder, x, y


def _parse_paths(seg):
    """解析 path 块的 leads_to_tech / research_cost_coeff 列表。"""
    bt = _child_block_text(seg, "path")
    if not bt:
        # 兼容无 path 包裹、直接出现在科技块的 leads_to_tech
        leads = re.findall(_PATH_LEADS_RE, seg)
        if leads:
            return [{"leads_to_tech": t, "research_cost_coeff": ""}
                    for t in leads]
        return []
    inner = bt[bt.find("{") + 1:bt.rfind("}")]
    rows = []
    cur = None
    for line in inner.splitlines():
        line = re.sub(r"#.*", "", line).strip()
        if not line:
            continue
        m = re.match(r'leads_to_tech\s*=\s*([\w\.\-]+)', line)
        if m:
            if cur:
                rows.append(cur)
            cur = {"leads_to_tech": m.group(1), "research_cost_coeff": ""}
            continue
        m = re.match(r'research_cost_coeff\s*=\s*([^\s]+)', line)
        if m and cur is not None:
            cur["research_cost_coeff"] = m.group(1)
    if cur:
        rows.append(cur)
    return rows


def _category_bonus_blocks(seg):
    """返回 category_* 直接子块 [(key, raw)]。"""
    out = []
    for k, depth, start, _end in _block_ranges(seg):
        if depth == 1 and k.startswith("category_"):
            raw = seg[start:_find_block_bounds(seg, start)[1]]
            out.append((k, raw))
    return out


def _other_fields(seg):
    """提取科技块内表单未覆盖的直接标量字段。"""
    covered = set(_COVERED_FIELDS)
    out = []
    for m in re.finditer(r'(?m)^\t([\w\.\-]+)\s*=\s*("[^"]*"|[^\s#}{]+)\s*$',
                         seg):
        key = m.group(1)
        if key.startswith("category_") or key in covered:
            continue
        out.append((key, m.group(2)))
    return out


def _parse_tech(seg, fp):
    folder, x, y = _parse_folder(seg)
    cats = re.findall(r"[\w\.\-]+", _CATEGORY_RE.search(seg).group(1)) \
        if _CATEGORY_RE.search(seg) else []
    em = _ENABLE_EQUIP_RE.search(seg)
    enable = re.findall(r"[\w\.\-]+", em.group(1)) if em else []
    allow = _child_block_text(seg, "allow") or ""
    ai = _child_block_text(seg, "ai_will_do") or ""
    sub = _values_in_block(seg, "sub_technologies")
    return {
        "id": "",
        "file": fp,
        "start_year": _field_value(seg, "start_year"),
        "research_cost": _field_value(seg, "research_cost"),
        "folder": folder,
        "folder_position": x,
        "position_x": x,
        "position_y": y,
        "categories": cats,
        "path": _parse_paths(seg),
        "leads_to_tech": [r["leads_to_tech"] for r in _parse_paths(seg)],
        "enable_equipments": enable,
        "allow": allow,
        "ai_will_do": ai,
        "sub_technologies": sub,
        "category_blocks": _category_bonus_blocks(seg),
        "priority": _field_value(seg, "priority"),
        "special_project_specialization": _field_value(
            seg, "special_project_specialization"),
        "other_fields": _other_fields(seg),
        "raw": seg,
    }


def _scan_tech_files(mod_path="", hoi4_path=""):
    files = []
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "technologies")
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.lower().endswith(".txt"):
                fp = os.path.join(d, n)
                if os.path.normcase(fp).startswith(
                        os.path.normcase(mod_path or "")) \
                        and any(os.path.normcase(x) == os.path.normcase(fp)
                                for x in files):
                    continue
                files.append(fp)
    return files


def load_tech_entities(mod_path="", hoi4_path=""):
    """扫描科技文件，返回 {tech_id: info}。"""
    out = {}
    for fp in _scan_tech_files(mod_path, hoi4_path):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        ranges = _block_ranges(content)
        wrappers = [r for r in ranges if r[0] == "technologies" and r[1] == 0]
        if wrappers:
            _wkey, _wdepth, wstart, wend = wrappers[0]
            for key, depth, start, end in ranges:
                if depth != 1 or key == "technologies":
                    continue
                if start < wstart or end > wend:
                    continue
                if key in out:
                    continue
                seg = content[start:end]
                info = _parse_tech(seg, fp)
                info["id"] = key
                out[key] = info
        else:
            for key, depth, start, end in ranges:
                if depth != 0:
                    continue
                seg = content[start:end]
                if not re.search(r'\bstart_year\b|\bresearch_cost\b|\bfolder\b',
                                 seg):
                    continue
                if key in out:
                    continue
                info = _parse_tech(seg, fp)
                info["id"] = key
                out[key] = info
    return out


# ---------- 科技块定位与写回 ----------

def _tech_block(content, tech_id):
    """定位科技块（technologies 包裹内 depth=1 或顶层 depth=0）。"""
    for key, depth, start, _end in _block_ranges(content):
        if key != tech_id or depth not in (0, 1):
            continue
        return _find_block_bounds(content, start)
    return None


def _replace_scalar_in_seg(seg, key, value, quoted=False):
    val = str(value)
    if quoted:
        val = '"%s"' % val.replace("\\", "\\\\").replace('"', '\\"')
    pat = re.compile(r'(\b%s\s*=\s*)(?:"[^"]*"|[^\r\n#}{]+)' % re.escape(key))
    if pat.search(seg):
        return pat.sub(lambda m: m.group(1) + val, seg, count=1)
    brace = seg.find("{")
    if brace >= 0:
        pos = brace + 1
        return seg[:pos] + "\n\t%s = %s" % (key, val) + seg[pos:]
    return seg


def _replace_list_in_seg(seg, key, values):
    values = [str(v) for v in (values or [])]
    new_block = '%s = { %s }' % (key, " ".join(values)) if values else \
        '%s = { }' % key
    pat = re.compile(r'\b%s\s*=\s*\{[^}]*\}' % re.escape(key))
    if pat.search(seg):
        return pat.sub(new_block, seg, count=1)
    brace = seg.find("{")
    if brace >= 0:
        pos = brace + 1
        return seg[:pos] + "\n\t" + new_block + seg[pos:]
    return seg


def _replace_child_in_seg(seg, key, new_block_text):
    new_text = new_block_text.strip()
    for ck, cd, cs, _ce in _block_ranges(seg):
        if cd == 1 and ck == key:
            child_start, child_end = _find_block_bounds(seg, cs)
            return seg[:child_start] + new_text + seg[child_end:]
    close = seg.rfind("}")
    if close >= 0:
        return seg[:close] + "\n\t" + new_text + "\n" + seg[close:]
    return seg


def _set_folder_position_in_seg(seg, x, y, name=None):
    """设置 folder 块内的 name 与 position { x y }；无 folder 块则补建。"""
    folder = _child_block_text(seg, "folder")
    if folder is None:
        if not (x or y or name):
            return seg
        folder = "folder = {\n\tname = %s\n\tposition = { x = %s y = %s }\n}" \
            % (name or "", x, y)
        return _replace_child_in_seg(seg, "folder", folder)
    if name is not None:
        name_pat = re.compile(r'\bname\s*=\s*(?:"[^"]*"|[^\s#}{]+)')
        if name_pat.search(folder):
            folder = name_pat.sub('name = %s' % name, folder, count=1)
        else:
            brace = folder.find("{")
            if brace >= 0:
                folder = (folder[:brace + 1] + "\n\tname = %s" % name
                          + folder[brace + 1:])
    pos_pat = re.compile(r'\bposition\s*=\s*\{[^}]*\}')
    new_pos = "position = { x = %s y = %s }" % (x, y)
    if pos_pat.search(folder):
        folder = pos_pat.sub(new_pos, folder, count=1)
    else:
        close = folder.rfind("}")
        folder = folder[:close] + "\n\t" + new_pos + "\n" + folder[close:]
    return _replace_child_in_seg(seg, "folder", folder)


def _serialize_paths(rows):
    lines = ["path = {"]
    for r in rows or []:
        lines.append("\tleads_to_tech = %s" % r.get("leads_to_tech", ""))
        coeff = r.get("research_cost_coeff", "")
        if coeff not in (None, ""):
            lines.append("\tresearch_cost_coeff = %s" % coeff)
    lines.append("}")
    return "\n".join(lines)


def apply_tech_edits(content, tech_id, fields=None, blocks=None,
                     categories=None, enable_equipments=None, paths=None,
                     other_fields=None, folder_position=None):
    """对科技块应用一批编辑，返回新内容。"""
    bounds = _tech_block(content, tech_id)
    if bounds is None:
        return content
    start, end = bounds
    seg = content[start:end]

    for key, spec in (fields or {}).items():
        if isinstance(spec, (tuple, list)):
            value, quoted = spec[0], bool(spec[1]) if len(spec) > 1 else False
        else:
            value, quoted = spec, False
        seg = _replace_scalar_in_seg(seg, key, value, quoted=quoted)

    for key, text in (blocks or {}).items():
        changed = _replace_child_in_seg(seg, key, text)
        if changed is not None:
            seg = changed

    if categories is not None:
        seg = _replace_list_in_seg(seg, "categories", categories)
    if enable_equipments is not None:
        seg = _replace_list_in_seg(seg, "enable_equipments", enable_equipments)
    if paths is not None:
        seg = _replace_child_in_seg(seg, "path", _serialize_paths(paths))
    if folder_position is not None:
        x = folder_position.get("x", "")
        y = folder_position.get("y", "")
        name = folder_position.get("name")
        seg = _set_folder_position_in_seg(seg, x, y, name=name)

    for key, raw_value in (other_fields or []):
        if not key:
            continue
        if raw_value == "":
            seg = re.sub(r'(?m)^\t%s\s*=.*$' % re.escape(key), "", seg)
        else:
            pat = re.compile(r'(?m)^(\t%s\s*=).*$' % re.escape(key))
            if pat.search(seg):
                seg = pat.sub(r"\1 " + raw_value, seg)
            else:
                seg = _replace_scalar_in_seg(seg, key, raw_value, quoted=False)

    return content[:start] + seg + content[end:]


# ---------- CRUD ----------

def delete_tech(content, tech_id):
    """删除指定科技块。"""
    bounds = _tech_block(content, tech_id)
    if bounds is None:
        return content
    bs, be = bounds
    before = content[:bs].rstrip()
    after = content[be:].lstrip("\n")
    if before and after:
        return before + "\n\n" + after
    return before + after


def rename_tech(content, old_id, new_id):
    """重命名科技块 key。"""
    bounds = _tech_block(content, old_id)
    if bounds is None:
        return content
    bs, be = bounds
    block_text = content[bs:be]
    eq = block_text.find("=")
    if eq < 0:
        return content
    prefix = block_text[:eq]
    new_prefix = re.sub(
        r"\b%s(\s*)$" % re.escape(old_id), new_id + r"\1", prefix, count=1)
    return content[:bs] + new_prefix + block_text[eq:] + content[be:]


def duplicate_tech(content, tech_id, new_id):
    """复制科技块并重命名（保持 technologies 包裹内/外位置）。"""
    bounds = _tech_block(content, tech_id)
    if bounds is None:
        return content
    bs, be = bounds
    block_text = content[bs:be]
    new_text = rename_tech(block_text, tech_id, new_id)
    # 原科技在 technologies 包裹内：插在原块之后（仍在包裹内）
    for wkey, wdepth, ws, _we in _block_ranges(content):
        if wkey != "technologies" or wdepth != 0:
            continue
        wstart, wend = _find_block_bounds(content, ws)
        if wstart <= bs < wend:
            return (content[:be] + "\n\t" + new_text.strip() + "\n"
                    + content[be:])
    # 顶层科技：插在原块之后
    return insert_top_block(content, new_text, after_id=tech_id)


def _tech_block_at_top(content, tech_id):
    """判断科技块是否在文件顶层（无 technologies 包裹）。"""
    bounds = _tech_block(content, tech_id)
    if bounds is None:
        return False
    for _key, depth, _s, _e in _block_ranges(content):
        pass
    # 找到该科技块对应的 depth
    for key, depth, start, _end in _block_ranges(content):
        if key == tech_id and _find_block_bounds(content, start)[0] == bounds[0]:
            return depth == 0
    return False


def insert_tech(content, tech_id, folder="", start_year="1936",
                research_cost="100"):
    """新建科技块（有 technologies 包裹则插入包裹内）。"""
    lines = ["%s = {" % tech_id, "\tstart_year = %s" % start_year,
             "\tresearch_cost = %s" % research_cost]
    if folder:
        lines.append("\tfolder = { name = %s position = { x = 0 y = 0 } }"
                     % folder)
    lines.append("}")
    block_text = "\n".join(lines)
    for key, depth, start, _end in _block_ranges(content):
        if key == "technologies" and depth == 0:
            wstart, wend = _find_block_bounds(content, start)
            inner = content[wstart:wend]
            close = inner.rfind("}")
            return (content[:wstart + close]
                    + "\n\t" + block_text + "\n"
                    + content[wstart + close:])
    return insert_top_block(content, block_text)