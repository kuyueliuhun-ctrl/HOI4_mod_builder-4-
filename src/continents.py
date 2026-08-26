"""大洲划分（P1 方案 A）：definition.csv 第 8 列 = 大洲（0=水域，1-7）。

数据源为引擎原生 `map/definition.csv` 第 8 列 + `map/continent.txt` 顺序，
零外部表、零坐标投影，与游戏判定一致（州=省多数表决）。

- ``load_province_continents``：省 → 大洲索引（mod 覆盖游戏）。
- ``load_state_continents``：州 → 大洲名（省多数表决，过滤 0 水域）。
- ``state_continent_overlay``：州 → 省展开（地图叠加层用，pid → 大洲索引）。

纯函数，无 Qt。
"""

from __future__ import annotations

import os

# 与 map/continent.txt 顺序一致（序号+1 = definition.csv 第 8 列值）
CONTINENT_NAMES = [
    "europe", "north_america", "south_america", "australia",
    "africa", "asia", "middle_east",
]

CONTINENT_ZH = {
    "europe": "欧洲", "north_america": "北美洲", "south_america": "南美洲",
    "australia": "大洋洲", "africa": "非洲", "asia": "亚洲",
    "middle_east": "中东",
}


def load_province_continents(mod_path="", hoi4_path=""):
    """读 definition.csv 第 8 列 → {省id: 大洲索引}（先游戏后 mod，mod 覆盖）。"""
    out = {}
    for base in (hoi4_path, mod_path):
        if not base:
            continue
        fp = os.path.join(base, "map", "definition.csv")
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or ";" not in line:
                        continue
                    parts = line.split(";")
                    if len(parts) < 8 or not parts[0].strip().isdigit():
                        continue
                    col = parts[7].strip()
                    if not col.isdigit():
                        continue
                    out[int(parts[0])] = int(col)
        except Exception:
            continue
    return out


def load_state_continents(state_data, mod_path="", hoi4_path=""):
    """州 → 大洲名（省多数表决，过滤 0 水域；无有效省返回 None）。

    state_data: 提供 `.states`（sid -> {"provinces": [...]}）与可选 mod/game 路径。
    """
    mp = mod_path or getattr(state_data, "mod_path", "")
    hp = hoi4_path or getattr(state_data, "hoi4_path", "")
    prov_cont = load_province_continents(mp, hp)
    result = {}
    for sid, info in (state_data.states or {}).items():
        votes = {}
        for pid in info.get("provinces", []):
            c = prov_cont.get(pid, 0)
            if 1 <= c <= len(CONTINENT_NAMES):
                votes[c] = votes.get(c, 0) + 1
        if not votes:
            result[sid] = None
            continue
        top = max(votes, key=votes.get)
        result[sid] = CONTINENT_NAMES[top - 1]
    return result


def state_continent_overlay(state_data, province_continent):
    """州 → 省展开：{省id: 大洲索引}，供 build_categorical_overlay 使用。"""
    out = {}
    for sid, info in (state_data.states or {}).items():
        c = province_continent.get(sid)
        if c is None or c not in CONTINENT_NAMES:
            continue
        idx = CONTINENT_NAMES.index(c) + 1
        for pid in info.get("provinces", []):
            out[pid] = idx
    return out
