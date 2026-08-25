"""军事学说（Doctrine）数据层（算法层，无 Qt）。

解析 common/doctrines/ 下：
  - grand_doctrines/*.txt   主要学说（含 tracks 列表与 milestones 满级奖励）
  - tracks/<folder>_tracks.txt  四种次要学说（track）与陆军精通度 mastery
  - subdoctrines/<folder>/*.txt  各 track 下的子学说（按 xp_cost 排列）

并提供写回辅助（复用 ai_loader_crud / nested_block_crud 的字符级块操作）。
"""

from __future__ import annotations

import os

from oob_loader import _block_ranges
from ai_loader_crud import (
    _child_block_text,
    _child_blocks,
    _fields,
    _find_block_bounds,
    insert_top_block,
    delete_top_block,
    rename_top_block,
    duplicate_top_block,
    replace_top_block_fields,
)

# ---------- 基础 ----------


def _scan_files(mod_path, hoi4_path, rel_dir, ext=".txt"):
    out = []
    seen = set()
    for base in (mod_path, hoi4_path):
        if not base or not os.path.isdir(base):
            continue
        d = os.path.join(base, rel_dir)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(ext):
                continue
            fp = os.path.join(d, name)
            real = os.path.realpath(fp)
            if real in seen:
                continue
            seen.add(real)
            out.append(fp)
    return out


def _read(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _rel(fp, hoi4_path, mod_path):
    base = hoi4_path or mod_path or os.path.dirname(fp)
    return os.path.relpath(fp, base).replace("\\", "/")


def _values(block_text, key):
    return _values_of(block_text, key)


def _values_of(block_text, key):
    try:
        from ai_loader_crud import _values_in_block
        return _values_in_block(block_text, key)
    except Exception:
        return []


# ---------- 解析 ----------


def _parse_mastery(block_text):
    """从 mastery = { multiplier = .. categories = { .. } sub_units = { .. } } 提取。"""
    raw = _child_block_text(block_text, "mastery")
    if not raw:
        return {"multiplier": "", "categories": [], "sub_units": []}
    f = _fields(raw)
    return {
        "multiplier": f.get("multiplier", ""),
        "categories": _values_of(raw, "categories"),
        "sub_units": _values_of(raw, "sub_units"),
    }


def _split_anonymous_blocks(text):
    """提取文本中顶层匿名 `{ ... }` 块的内部文本列表。"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "{":
            depth = 1
            start = i
            i += 1
            while i < n and depth:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            out.append(text[start + 1:i - 1])
        else:
            i += 1
    return out


def _parse_milestones(block_text):
    """从 milestones = { {...} {...} } 提取每个里程碑块内部文本列表。"""
    raw = _child_block_text(block_text, "milestones")
    if not raw:
        return []
    brace = raw.find("{")
    if brace < 0:
        return []
    close = raw.rfind("}")
    inner = raw[brace + 1:close]
    return [x.strip() for x in _split_anonymous_blocks(inner)]


def parse_grand_doctrines(content):
    """解析 grand_doctrines/*.txt，返回 {gd_id: dict}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        out[key] = {
            "id": key,
            "name": key,
            "folder": f.get("folder", ""),
            "title": f.get("name", ""),
            "description": f.get("description", ""),
            "icon": f.get("icon", ""),
            "xp_cost": f.get("xp_cost", ""),
            "xp_type": f.get("xp_type", ""),
            "tracks": _values_of(bt, "tracks"),
            "milestones": _parse_milestones(bt),
            "available": _child_block_text(bt, "available") or "",
            "raw": bt,
        }
    return out


def load_grand_doctrines(mod_path="", hoi4_path=""):
    folder = "common/doctrines/grand_doctrines"
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, folder):
        for gid, g in parse_grand_doctrines(_read(fp)).items():
            g["file"] = fp
            g["rel"] = _rel(fp, hoi4_path, mod_path)
            out[gid] = g
    return out


def parse_doctrine_tracks(content):
    """解析 tracks/*_tracks.txt，返回 {track_id: dict}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        mastery = _parse_mastery(bt)
        out[key] = {
            "id": key,
            "name": key,
            "title": f.get("name", ""),
            "icon": f.get("icon", ""),
            "background": f.get("background", ""),
            "icon_frame": f.get("icon_frame", ""),
            "mastery": mastery,
            "raw": bt,
        }
    return out


def load_doctrine_tracks(mod_path="", hoi4_path=""):
    folder = "common/doctrines/tracks"
    out = {}
    for fp in _scan_files(mod_path, hoi4_path, folder):
        for tid, t in parse_doctrine_tracks(_read(fp)).items():
            t["file"] = fp
            t["rel"] = _rel(fp, hoi4_path, mod_path)
            out[tid] = t
    return out


def parse_subdoctrines(content):
    """解析 subdoctrines/<folder>/*.txt，返回 {sd_id: dict}。"""
    out = {}
    for key, depth, start, end in _block_ranges(content):
        if depth != 0:
            continue
        bt = content[start:end]
        f = _fields(bt)
        out[key] = {
            "id": key,
            "name": key,
            "track": f.get("track", ""),
            "title": f.get("name", ""),
            "description": f.get("description", ""),
            "icon": f.get("icon", ""),
            "xp_cost": f.get("xp_cost", ""),
            "xp_type": f.get("xp_type", ""),
            "available": _child_block_text(bt, "available") or "",
            "ai_will_do": _child_block_text(bt, "ai_will_do") or "",
            "effects": _child_block_text(bt, "effects") or "",
            "rewards": _child_block_text(bt, "rewards") or "",
            "raw": bt,
        }
    return out


def load_subdoctrines(mod_path="", hoi4_path=""):
    folder = "common/doctrines/subdoctrines"
    out = {}
    for root, _dirs, names in os.walk(os.path.join(
            hoi4_path or mod_path or "", folder)):
        for name in sorted(names):
            if not name.lower().endswith(".txt"):
                continue
            fp = os.path.join(root, name)
            for sid, s in parse_subdoctrines(_read(fp)).items():
                s["file"] = fp
                s["rel"] = _rel(fp, hoi4_path, mod_path)
                out[sid] = s
    # mod 优先合并（mod 文件覆盖游戏同名）
    if mod_path and hoi4_path and os.path.isdir(
            os.path.join(mod_path, folder)):
        for root, _dirs, names in os.walk(os.path.join(mod_path, folder)):
            for name in sorted(names):
                if not name.lower().endswith(".txt"):
                    continue
                fp = os.path.join(root, name)
                for sid, s in parse_subdoctrines(_read(fp)).items():
                    s["file"] = fp
                    s["rel"] = _rel(fp, hoi4_path, mod_path)
                    out[sid] = s
    return out


# ---------- 写回 ----------

def replace_grand_doctrine_fields(content, gd_id, fields):
    return replace_top_block_fields(content, gd_id, fields)


def replace_track_fields(content, track_id, fields):
    return replace_top_block_fields(content, track_id, fields)


def replace_subdoctrine_fields(content, sd_id, fields):
    return replace_top_block_fields(content, sd_id, fields)


def insert_subdoctrine(content, sd_id, track_id, after_id=None):
    block_text = ("%s = {\n\ttrack = %s\n\tname = %s\n\txp_cost = 100\n"
                  "\txp_type = army\n}" % (sd_id, track_id, sd_id))
    return insert_top_block(content, block_text, after_id=after_id)


def delete_subdoctrine(content, sd_id):
    return delete_top_block(content, sd_id)


def rename_subdoctrine(content, old_id, new_id):
    return rename_top_block(content, old_id, new_id)


def duplicate_subdoctrine(content, sd_id, new_id):
    return duplicate_top_block(content, sd_id, new_id)


def replace_subdoctrine_child(content, sd_id, key, new_block_text):
    """替换子学说顶层块内指定子块（rewards/available 等），不存在则插入。"""
    for k, d, s, e in _block_ranges(content):
        if d != 0 or k != sd_id:
            continue
        bs, be = _find_block_bounds(content, s)
        bt = content[bs:be]
        for ck, cd, cs, ce in _block_ranges(bt):
            if cd == 1 and ck == key:
                cbs, cbe = _find_block_bounds(content, bs + cs)
                return content[:cbs] + new_block_text.strip() + content[cbe:]
        brace = content.rfind("}", bs, be)
        if brace >= 0:
            return (content[:brace] + "\n\t" + new_block_text.strip()
                    + "\n" + content[brace:])
    return content
