"""PDX 脚本格式化（算法层）

按 `{` / `}` 计数用 Tab 缩进重排 PDX 脚本文件。只改缩进，不改内容意义。
参考 Yard1 HoI4 fileformatter：忽略引号内的括号、可选去除行尾空格、忽略注释。
"""

from __future__ import annotations

import os
import re
from typing import List

from write_utils import atomic_write_text

_BRACE_RE = re.compile(r"\".*?\"")


def _count_braces(line: str) -> int:
    """统计一行中引号外的 `{` 数与 `}` 数（差值为净开口数）。"""
    cleaned = _BRACE_RE.sub("", line)
    return cleaned.count("{") - cleaned.count("}")


def format_text(text: str, remove_whitespace: bool = False,
                ignore_comments: bool = False) -> str:
    """把 PDX 文本按括号计数重缩进。

    Args:
        text: 原始内容
        remove_whitespace: 只去除行尾空格，不重缩进
        ignore_comments: 跳过以 # 开头的行（保持原样不缩进）
    Returns:
        格式化后的文本（不含末尾多余空行）
    """
    lines = text.splitlines()
    out_lines: List[str] = []
    open_blocks = 0
    for raw in lines:
        if ignore_comments and re.match(r"^\s*#", raw):
            out_lines.append(raw.rstrip())
            continue
        if remove_whitespace:
            out_lines.append(re.sub(r"\s*$", "", raw))
            continue
        line = raw.strip()
        if line == "}":
            indent = "\t" * (open_blocks - 1) if open_blocks > 0 else ""
            new_line = indent + line
        else:
            new_line = ("\t" * open_blocks) + line
        out_lines.append(re.sub(r"\s*$", "", new_line))
        open_blocks += _count_braces(line)
        if open_blocks < 0:
            open_blocks = 0
    return "\n".join(out_lines)


def is_loc_file(path: str) -> bool:
    """是否本地化 .yml 文件（需 utf-8-sig + BOM）。"""
    return path.lower().endswith((".yml", ".yaml"))


def _read_text(path):
    encoding = "utf-8-sig" if is_loc_file(path) else "utf-8"
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        return f.read()


def format_file(path: str, remove_whitespace: bool = False,
                ignore_comments: bool = False) -> bool:
    """格式化单个文件并原子写回。返回是否成功。"""
    if not os.path.isfile(path):
        return False
    text = _read_text(path)
    formatted = format_text(text, remove_whitespace, ignore_comments)
    if is_loc_file(path):
        atomic_write_text(path, "\n" + formatted + "\n",
                          encoding="utf-8-sig", allow_bom=True)
    else:
        atomic_write_text(path, formatted + "\n", encoding="utf-8")
    return True


def format_paths(paths, extensions=(".txt", ".gfx", ".yml", ".yaml"),
                 recursive: bool = False, remove_whitespace: bool = False,
                 ignore_comments: bool = False) -> int:
    """批量格式化文件或目录，返回处理的文件数。"""
    counter = 0
    for p in paths:
        if os.path.isdir(p):
            files = []
            if recursive:
                for root, _dirs, names in os.walk(p):
                    for n in names:
                        if n.lower().endswith(extensions):
                            files.append(os.path.join(root, n))
            else:
                for n in os.listdir(p):
                    fp = os.path.join(p, n)
                    if os.path.isfile(fp) and n.lower().endswith(extensions):
                        files.append(fp)
            for fp in sorted(files):
                if format_file(fp, remove_whitespace, ignore_comments):
                    counter += 1
        else:
            if format_file(p, remove_whitespace, ignore_comments):
                counter += 1
    return counter