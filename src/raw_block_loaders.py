"""脚本库原始块 loader（B2-P17）。

对 scripted_effects / scripted_triggers / script_enums 这类
「每个顶层块 = 任意 PDX 脚本体」的文件形态，提取实体 = 块 key + 块内原文，
供 RawBlockEditor 侧栏 + 原始脚本体编辑使用。
"""

from __future__ import annotations

import os

from oob_loader import _block_ranges
from ai_loader_crud import _inner_block_text


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


def _cached(kind, mod_path, hoi4_path, loader):
    import ai_loader as _al
    key = (kind, mod_path or "", hoi4_path or "")
    if key in _al._AI_CACHE:
        return _al._AI_CACHE[key]
    data = loader()
    _al._AI_CACHE[key] = data
    return data


def _make_raw_block_loader(folder, cache_key, file_mode=False):
    """生成 (parse, load) 对：每个顶层块 = {id, name, body(块内原文), raw}。"""

    def _parse(content):
        out = {}
        for key, depth, start, end in _block_ranges(content):
            if depth != 0:
                continue
            bt = content[start:end]
            out[key] = {
                "id": key,
                "name": key,
                "body": _inner_block_text(bt).strip("\n"),
                "raw": bt,
            }
        return out

    def _paths(mod_path, hoi4_path):
        if file_mode:
            out = []
            for base in (mod_path, hoi4_path):
                if not base:
                    continue
                fp = os.path.join(base, folder)
                if os.path.isfile(fp):
                    out.append(fp)
            seen, res = set(), []
            for fp in out:
                real = os.path.realpath(fp)
                if real in seen:
                    continue
                seen.add(real)
                res.append(fp)
            return res
        return _scan_files(mod_path, hoi4_path, folder)

    def _load(mod_path="", hoi4_path=""):
        def loader():
            out = {}
            for fp in _paths(mod_path, hoi4_path):
                for eid, e in _parse(_read(fp)).items():
                    e["file"] = fp
                    e["rel"] = os.path.relpath(
                        fp, hoi4_path or mod_path or os.path.dirname(fp)
                    ).replace("\\", "/")
                    out[eid] = e
            return out
        return _cached(cache_key, mod_path, hoi4_path, loader)

    _parse.__name__ = "parse_" + cache_key
    _load.__name__ = "load_" + cache_key
    return _parse, _load


(parse_scripted_effects, load_scripted_effects) = _make_raw_block_loader(
    "common/scripted_effects", "scripted_effects")
(parse_scripted_triggers, load_scripted_triggers) = _make_raw_block_loader(
    "common/scripted_triggers", "scripted_triggers")
(parse_script_enums, load_script_enums) = _make_raw_block_loader(
    "common/script_enums.txt", "script_enums", file_mode=True)
