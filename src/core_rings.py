"""核心圈层（P1 方案 B）：国家核心州集合 → 州邻接 BFS 分层。

- ``build_state_adjacency``：由 provinces.bmp 邻域扫描构建州级邻接（land-land）。
- ``compute_core_rings``：某国从核心州出发 BFS，返回 {state_id: ring}（ring 0=核心）。
- ``core_ring_overlay``：州 → 省展开（pid → ring），供地图叠加层。

数据源：StateData（含 add_core_of 解析出的 cores/cores_by_tag）与
MapData（id_map = provinces.bmp 像素矩阵、province_table 含省 type）。
"""

from __future__ import annotations

import numpy as np


def _is_land(province_table, pid):
    return (province_table.get(int(pid)) or {}).get("type") == "land"


def build_state_adjacency(map_data, state_data):
    """构建州级邻接（仅 land-land 相邻，经州内省聚合）。

    Returns:
        dict: {state_id: set(state_id)}（对称无自环）
    """
    idm = getattr(map_data, "id_map", None)
    ptab = getattr(map_data, "province_table", None) or {}
    p2s = getattr(state_data, "province_to_state", None) or {}
    if idm is None:
        return {}
    idm = np.asarray(idm)
    pairs = set()

    def _add_pairs(a, b):
        m = a != b
        if not np.any(m):
            return
        pa, pb = a[m], b[m]
        # 去重后再处理（同省邻域巨大，避免逐像素查表）
        for p1, p2 in np.unique(np.stack([pa, pb], axis=1), axis=0):
            p1, p2 = int(p1), int(p2)
            s1, s2 = p2s.get(p1), p2s.get(p2)
            if not s1 or not s2 or s1 == s2:
                continue
            if not (_is_land(ptab, p1) and _is_land(ptab, p2)):
                continue
            pairs.add((s1, s2) if s1 < s2 else (s2, s1))

    if idm.ndim == 2:
        _add_pairs(idm[:-1, :], idm[1:, :])   # 上下
        _add_pairs(idm[:, :-1], idm[:, 1:])   # 左右
    adj = {}
    for s1, s2 in pairs:
        adj.setdefault(s1, set()).add(s2)
        adj.setdefault(s2, set()).add(s1)
    return adj


def compute_core_rings(tag, cores_by_tag, state_adjacency, max_ring=6):
    """从某国核心州出发 BFS 分层。

    Returns:
        dict: {state_id: ring}；ring 0 = 核心州；ring k = 到最近核心州最短邻接步数 k；
        超过 max_ring 的并入 max_ring。无核心州返回 {}。
    """
    seeds = set(cores_by_tag.get(tag, ()))
    if not seeds:
        return {}
    rings = {s: 0 for s in seeds}
    frontier = list(seeds)
    while frontier:
        nxt = []
        for s in frontier:
            r = rings[s]
            if r >= max_ring:
                continue
            for n in state_adjacency.get(s, ()):
                if n not in rings:
                    rings[n] = r + 1
                    nxt.append(n)
        frontier = nxt
    return rings


def core_ring_overlay(state_data, rings):
    """州 → 省展开：{省id: ring}，供 build_categorical_overlay 使用。"""
    out = {}
    for sid, ring in (rings or {}).items():
        info = state_data.states.get(sid)
        if not info:
            continue
        for pid in info.get("provinces", []):
            out[pid] = ring
    return out
