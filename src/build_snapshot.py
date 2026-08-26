"""build_snapshot 溯源台账（Scenario Forge 移植：快照清单 + 差异回查）。

每次 build/导出前对 mod 目录生成文件清单快照（相对路径 + 大小 + sha1 + 来源），
落盘为 JSON；支持 load 与 diff，便于回查「某文件在哪个版本之后被改动、
是 mod 新增还是覆盖原版」。纯函数 + JSON，无 Qt。

快照文件默认写到 .runtime/snapshots/（用 write_utils 原子写，遵守写入纪律）。
"""

from __future__ import annotations

import hashlib
import json
import os
import time


def _sha1_file(fp):
    h = hashlib.sha1()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_mod_files(mod_path):
    """产出 (relpath, abs_path)——mod 内全部文件（含子目录）。"""
    for dp, _dirs, fns in os.walk(mod_path):
        for fn in sorted(fns):
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, mod_path).replace("\\", "/")
            yield rel, fp


def build_snapshot(mod_path, game_path=None):
    """生成 mod 文件清单快照。

    Returns:
        {"created_at": epoch, "mod_path": mod_path, "count": N,
         "files": {rel: {"size": int, "sha1": str, "source": "new"|"override"}}}
        source=override 表示 mod 里存在同相对路径的原版文件（会覆盖原版）。
    """
    files = {}
    for rel, fp in _iter_mod_files(mod_path):
        entry = {"size": os.path.getsize(fp), "sha1": _sha1_file(fp)}
        if game_path and os.path.isfile(
                os.path.join(game_path, rel.replace("/", os.sep))):
            entry["source"] = "override"
        else:
            entry["source"] = "new"
        files[rel] = entry
    return {"created_at": time.time(), "mod_path": mod_path,
            "count": len(files), "files": files}


def save_snapshot(snapshot, path):
    """把快照落盘为 JSON（原子写）。"""
    from write_utils import atomic_write_text
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atomic_write_text(path, json.dumps(snapshot, ensure_ascii=False,
                                       indent=1))


def load_snapshot(path):
    """读 JSON 快照。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_snapshots(old, new):
    """对比新旧快照，返回差异清单。

    Returns:
        {"added": [rel], "removed": [rel], "changed": [rel],
         "unchanged": int}
    """
    oldf = old.get("files") or {}
    newf = new.get("files") or {}
    added, removed, changed = [], [], []
    for rel in sorted(newf):
        if rel not in oldf:
            added.append(rel)
        elif oldf[rel].get("sha1") != newf[rel].get("sha1"):
            changed.append(rel)
    for rel in sorted(oldf):
        if rel not in newf:
            removed.append(rel)
    unchanged = len(newf) - len(added) - len(changed)
    return {"added": added, "removed": removed, "changed": changed,
            "unchanged": unchanged}
