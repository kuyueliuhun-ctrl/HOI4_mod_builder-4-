"""胜利点(VP)本地化生成（算法层）

从 history/states/*.txt 提取 victory_points 的 pid + 点值，
为每个 pid 生成本地化词条 `VICTORY_POINTS_<pid>`。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

# 形如 victory_points = { 10 2 11 1 }
_VP_RE = re.compile(r"victory_points\s*=\s*\{([^}]*)\}", re.DOTALL | re.IGNORECASE)


def _read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read()


def extract_vp_from_file(path: str) -> List[dict]:
    """解析单个 state 文件中的 VP：[{pid, points, state_file}]。"""
    out = []
    if not os.path.isfile(path):
        return out
    try:
        content = _read_text(path)
    except OSError:
        return out
    tokens = re.findall(r"-?\d+", content[:0])  # 占位
    for m in _VP_RE.finditer(content):
        body = m.group(1)
        nums = re.findall(r"-?\d+", body)
        # 成对解析 pid, points
        for i in range(0, len(nums) - 1, 2):
            pid = nums[i]
            points = nums[i + 1]
            out.append({"pid": pid, "points": points,
                        "state_file": os.path.basename(path)})
    return out


def collect_vps(mod_path: str) -> List[dict]:
    """扫描 history/states 全部 state 文件的 VP。"""
    vps = []
    base = os.path.join(mod_path, "history", "states")
    if not os.path.isdir(base):
        return vps
    for root, _dirs, names in os.walk(base):
        for name in names:
            if not name.lower().endswith(".txt"):
                continue
            vps.extend(extract_vp_from_file(os.path.join(root, name)))
    # 去重 + 排序
    seen = set()
    dedup = []
    for v in vps:
        if v["pid"] in seen:
            continue
        seen.add(v["pid"])
        dedup.append(v)
    dedup.sort(key=lambda v: int(v["pid"]))
    return dedup


def build_vp_loc(vps: List[dict], values: Dict[str, str] = None) -> List[dict]:
    """生成 VP 本地化词条列表。values 可选 pid→名称；缺省用 pid。"""
    values = values or {}
    return [{"key": "VICTORY_POINTS_" + v["pid"],
             "value": values.get(v["pid"], "") or ""} for v in vps]


def build_vp_loc_text(vps: List[dict], lang: str = "english",
                      values: Dict[str, str] = None) -> str:
    """生成含语言节的本地化 yml 文本（lang: simp_chinese / english 等）。"""
    entries = build_vp_loc(vps, values)
    lines = ["l_{}:".format(lang)]
    for e in entries:
        lines.append(' {}: "{}"'.format(e["key"], e["value"]))
    return "\n".join(lines) + "\n"