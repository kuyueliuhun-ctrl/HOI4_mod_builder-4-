"""项目符号 / 定义 / 引用 / 补全（B3：补充 RHoiScribe 缺失能力）。

基于 mod 工作区（可选并入游戏目录）的文本级扫描，提供：
- list_workspace_symbols：块键 + id/name/token 值
- find_definition / find_references：定义与引用定位（文件 + 行 + 片段）
- suggest_completion：前缀补全候选

纯文本 + 解析，无 Qt。扫描范围默认仅 mod（快）；include_game 才并入游戏。
"""

from __future__ import annotations

import os
import re

_SKIP_DIRS = {".git", "__pycache__", ".runtime", ".idea", ".venv",
              ".jspace", "node_modules", "unit_counter_library"}
_PDX_EXTS = (".txt", ".gfx", ".gui", ".lua")

_BLOCK_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_\-\.]*)\s*=\s*\{")
_IDVAL_RE = re.compile(
    r"\b(id|name|token)\s*=\s*\"?([A-Za-z_][A-Za-z0-9_\-\.]*)\"?")


def _iter_script_files(root):
    if not root or not os.path.isdir(root):
        return
    for dp, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in names:
            if name.lower().endswith(_PDX_EXTS):
                yield os.path.join(dp, name)


def _rel(fp, root):
    return os.path.relpath(fp, root).replace("\\", "/")


def _read(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def scan_workspace(mod_path="", game_path="", keyword="", limit=1000,
                   include_game=False):
    """扫描工作区，收集符号条目 [{name, kind, file, line}]。"""
    entries = []
    roots = [mod_path]
    if include_game and game_path:
        roots.append(game_path)
    seen = set()
    for root in roots:
        for fp in _iter_script_files(root):
            rel = _rel(fp, root)
            text = _read(fp)
            if not text:
                continue
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                for m in _BLOCK_RE.finditer(line):
                    name = m.group(1)
                    if keyword and keyword not in name:
                        continue
                    key = (name, "block", rel, idx)
                    if key in seen:
                        continue
                    seen.add(key)
                    entries.append({"name": name, "kind": "block",
                                    "file": rel, "line": idx})
                for m in _IDVAL_RE.finditer(line):
                    name = m.group(2)
                    if keyword and keyword not in name:
                        continue
                    key = (name, "id", rel, idx)
                    if key in seen:
                        continue
                    seen.add(key)
                    entries.append({"name": name, "kind": "id",
                                    "file": rel, "line": idx})
            if len(entries) >= limit:
                return entries[:limit]
    return entries[:limit]


def _line_snippet(lines, idx, width=60):
    try:
        line = lines[idx - 1]
    except IndexError:
        return ""
    line = line.strip()
    return line[:width] + ("…" if len(line) > width else "")


def find_definition(name, mod_path="", game_path="", include_game=False):
    """查找 name 的定义（优先块键，其次 id/name 值）。"""
    for root in ([mod_path] + ([game_path] if include_game and game_path else [])):
        for fp in _iter_script_files(root):
            text = _read(fp)
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                for m in _BLOCK_RE.finditer(line):
                    if m.group(1) == name:
                        return {"name": name, "kind": "block",
                                "file": _rel(fp, root), "line": idx,
                                "snippet": _line_snippet(lines, idx)}
                for m in _IDVAL_RE.finditer(line):
                    if m.group(2) == name:
                        return {"name": name, "kind": "id",
                                "file": _rel(fp, root), "line": idx,
                                "snippet": _line_snippet(lines, idx)}
    return None


def find_references(name, mod_path="", game_path="", limit=200,
                    include_game=False):
    """查找 name 的引用（按词出现，排除自身定义行）。"""
    refs = []
    pattern = re.compile(r"\b%s\b" % re.escape(name))
    for root in ([mod_path] + ([game_path] if include_game and game_path else [])):
        for fp in _iter_script_files(root):
            text = _read(fp)
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                if not pattern.search(line):
                    continue
                # 排除定义行（块键 或 id/name/token 赋值）
                is_def = bool(_BLOCK_RE.search(line) and re.match(
                    r"\s*%s\s*=\s*\{" % re.escape(name), line))
                is_def = is_def or bool(
                    re.search(r"\b(?:id|name|token)\s*=\s*\"?%s\"?" % re.escape(name),
                              line))
                if is_def:
                    continue
                refs.append({"file": _rel(fp, root), "line": idx,
                             "snippet": _line_snippet(lines, idx)})
                if len(refs) >= limit:
                    return refs
    return refs


def suggest_completion(prefix, mod_path="", game_path="", limit=50,
                       include_game=False):
    """按前缀给出补全候选（块键优先，其次 id/name 值，去重）。"""
    prefix = (prefix or "").strip()
    cands = {}
    for root in ([mod_path] + ([game_path] if include_game and game_path else [])):
        for fp in _iter_script_files(root):
            text = _read(fp)
            for line in text.splitlines():
                for m in _BLOCK_RE.finditer(line):
                    name = m.group(1)
                    if prefix and name.startswith(prefix):
                        cands.setdefault(name, "block")
                for m in _IDVAL_RE.finditer(line):
                    name = m.group(2)
                    if prefix and name.startswith(prefix):
                        cands.setdefault(name, "id")
            if len(cands) >= limit * 4:
                break
    order = sorted(cands.items(), key=lambda kv: (kv[1] != "block", kv[0]))
    return [{"name": n, "kind": k} for n, k in order[:limit]]