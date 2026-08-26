"""地图数据层覆盖层生成（从 map_editor_dialog 拆分，控制行数预算）。

按数据层名生成整图 RGBA 覆盖层，供地图编辑「数据层」下拉使用。
- 无 / 地图数据缺失 → (None, 0, 0)
- 核心圈层需要 current_pid 归属国；无归属国抛 ValueError（UI 提示）。

数据层：胜利点 VP / 资源总量 / 补给区 / 铁路 / 河流 / 大洲 / 核心圈层。
"""

from __future__ import annotations

import os

from map_data_layers import (
    build_categorical_overlay,
    build_line_overlay,
    build_river_overlay,
    build_value_overlay,
    load_railways,
    load_supply_areas,
    state_vp_and_resources,
)


def build_layer_overlay(key, map_data, state_data, mod_path="", game_path="",
                        current_pid=0):
    """生成指定数据层覆盖层。返回 (rgba, x0, y0) 或 (None, 0, 0)。"""
    idm = getattr(map_data, "id_map", None)
    if idm is None:
        return None, 0, 0
    if key == "胜利点 VP":
        vp, _ = state_vp_and_resources(state_data.states)
        return build_value_overlay(idm, vp, alpha=150)
    if key == "资源总量":
        _, res = state_vp_and_resources(state_data.states)
        return build_value_overlay(idm, res, alpha=150)
    if key == "补给区":
        areas, _meta = load_supply_areas(mod_path, game_path)
        pid_area = {}
        for sid, aid in areas.items():
            info = state_data.states.get(sid)
            if info:
                for pid in info.get("provinces", []):
                    pid_area[pid] = aid
        return build_categorical_overlay(idm, pid_area, alpha=150)
    if key == "铁路":
        map_data.precompute_centroids()
        segs = load_railways(mod_path, game_path)
        return build_line_overlay(
            int(idm.shape[1]), int(idm.shape[0]), segs,
            map_data.province_centroid, alpha=220)
    if key == "河流":
        rivers_path = ""
        for base in (game_path, mod_path):
            if base and os.path.isfile(
                    os.path.join(base, "map", "rivers.bmp")):
                rivers_path = os.path.join(base, "map", "rivers.bmp")
                break
        return build_river_overlay(rivers_path, alpha=170)
    if key == "大洲":
        from continents import load_state_continents, state_continent_overlay
        scont = load_state_continents(state_data, mod_path, game_path)
        pid_cat = state_continent_overlay(state_data, scont)
        return build_categorical_overlay(idm, pid_cat, alpha=150)
    if key == "核心圈层":
        from core_rings import build_state_adjacency, compute_core_rings, \
            core_ring_overlay
        tag = ""
        if current_pid:
            sid = state_data.province_to_state.get(int(current_pid), 0)
            info = state_data.states.get(sid)
            if info:
                tag = info.get("owner", "")
        if not tag:
            raise ValueError(
                "请先在图上选择一个属于某国的地块（用该地块归属国显示核心圈层）。")
        adj = build_state_adjacency(map_data, state_data)
        rings = compute_core_rings(tag, state_data.cores_by_tag, adj)
        pid_ring = core_ring_overlay(state_data, rings)
        return build_categorical_overlay(idm, pid_ring, alpha=150)
    return None, 0, 0
