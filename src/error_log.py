"""错误日志分析（算法层）

解析游戏 error.log / text.log / game.log，按正则分类常见错误。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

_RULES = [
    ("缺本地化键", re.compile(r"(?:not\s*found|missing|loc|localis\w*)[^:\\]*(?:key|loc)[^:]*", re.IGNORECASE)),
    ("着色字符错误", re.compile(r"coloring|color\s*for\s*character", re.IGNORECASE)),
    ("括号/引用不匹配", re.compile(r"(?:unbalanced|unexpected|expected)[^.]*(?:brace|bracket|end|token)|unexpected\s*\}", re.IGNORECASE)),
    ("找不到文件/精灵", re.compile(r"(?:could\s*not\s*find|cannot\s*(?:load|find))[^.]*(?:file|sprite|texture|gfx)", re.IGNORECASE)),
    ("重复定义", re.compile(r"duplicate\s+(?:id|focus|decision|event)", re.IGNORECASE)),
    ("变量/作用域", re.compile(r"(?:variable|scope|scope\s*error|in\s*scope)", re.IGNORECASE)),
]


def analyze(text: str) -> List[dict]:
    """逐行分析日志，返回 [{lineno, category, message}]。"""
    results = []
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        for category, pat in _RULES:
            if pat.search(stripped):
                results.append({"lineno": idx, "category": category,
                                "message": stripped})
                break
    return results


def summarize(results: List[dict]) -> Dict[str, int]:
    """按类别汇总条数。"""
    out: Dict[str, int] = {}
    for r in results:
        cat = r["category"]
        out[cat] = out.get(cat, 0) + 1
    return out


def analyze_file(path: str) -> List[dict]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return []
    return analyze(text)


# 子系统归类关键字（借鉴 RHoiScribe classify_error_log）
_SUBSYSTEM_RULES = [
    ("focus", re.compile(r"focus|national_focus", re.IGNORECASE)),
    ("decision", re.compile(r"decision", re.IGNORECASE)),
    ("event", re.compile(r"event\b|\.t\b|\.d\b|namespace", re.IGNORECASE)),
    ("technology", re.compile(r"tech|technology|research", re.IGNORECASE)),
    ("state", re.compile(r"state\b|province|owner", re.IGNORECASE)),
    ("character", re.compile(r"character|leader|advisor|portrait", re.IGNORECASE)),
    ("localisation", re.compile(r"localis|\.txt|translation|key", re.IGNORECASE)),
    ("gfx/gui", re.compile(r"gfx|sprite|texture|\.gui|\.dds|\.png", re.IGNORECASE)),
    ("map", re.compile(r"map|province|terrain|adjacenc", re.IGNORECASE)),
    ("ai", re.compile(r"ai\b|ai_will", re.IGNORECASE)),
    ("script/scope", re.compile(r"scope|variable|effect|trigger|this|root|from", re.IGNORECASE)),
    ("其他", re.compile(r".*")),
]


def classify_by_subsystem(results: List[dict]) -> Dict[str, int]:
    """把分析结果按 HOI4 子系统归类汇总。"""
    out: Dict[str, int] = {}
    for r in results:
        msg = r.get("message", "")
        sub = "其他"
        for name, pat in _SUBSYSTEM_RULES:
            if name == "其他":
                break
            if pat.search(msg):
                sub = name
                break
        out[sub] = out.get(sub, 0) + 1
    return out