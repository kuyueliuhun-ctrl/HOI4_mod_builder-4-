"""OOB 统计/装备估算层（F5 拆分自 oob_loader.py）。

包含 load_equipment_stats / division_stats 及所需公共助手；
营定义加载 load_sub_units 仍在 oob_loader.py。
"""

from __future__ import annotations

import os
import re

from tree_node import parse_pdx_text_to_nodes

# 营/装备属性字段（基础值估算用；字段缺失时值为 None）
_STAT_FIELDS = (
    "combat_width", "max_strength", "max_organisation", "maximum_speed",
    "manpower", "training_time", "suppression", "weight", "supply_consumption",
    "fuel_consumption", "reliability", "soft_attack", "hard_attack",
    "air_attack", "defense", "breakthrough", "armor", "piercing",
    "initiative", "recon", "org_regain", "experience_loss_factor",
)
_EQUIP_STAT_FIELDS = (
    "soft_attack", "hard_attack", "air_attack", "defense", "breakthrough",
    "armor", "piercing", "reliability",
    # 装备 IC 花费（P2.5：装备 IC 估算）
    "build_cost_ic", "convert_cost_ic",
)
# 地形适应性徽章使用的地形键（与游戏 terrain 块一致）
TERRAIN_KEYS = ("desert", "forest", "hills", "jungle", "marsh",
                "mountain", "plains", "urban")

_SUB_KNOWN_SCALARS = frozenset((
    "abbreviation", "sprite", "group", "parent",
) + _STAT_FIELDS)

_EQUIP_STATS_CACHE = {}


def clear_equip_stats_cache():
    """清空装备统计缓存（OOB/兵种写后调用，防旧值残留）。"""
    _EQUIP_STATS_CACHE.clear()

def _node_field_value(node, key):
    """块节点的直接子 value 字段值。"""
    for c in node.children:
        if c.node_type == "value" and c.key == key:
            return c.value
    return None



def _num(v):
    """宽松数值转换：None/非数值 → None，其余 → float。"""
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None



def _node_block(node, key):
    """块节点的直接子块。"""
    if node is None:
        return None
    for c in node.children:
        if c.node_type == "block" and c.key == key:
            return c
    return None



def _parse_need(node):
    """解析 need = { 装备 = 数量 } → {装备: 数量}。"""
    out = {}
    blk = _node_block(node, "need")
    if blk is None:
        return out
    for c in blk.children:
        if c.node_type == "value":
            n = _num(c.value)
            if n is not None:
                out[c.key] = n
    return out



def _parse_terrain(node):
    """解析 terrain 子块 → {地形键: {"movement","attack","defence"}}。

    注意 HOI4 使用英式拼写 defence。
    """
    out = {}
    for c in node.children:
        if c.node_type == "block" and c.key in TERRAIN_KEYS:
            item = {
                "movement": _num(_node_field_value(c, "movement")),
                "attack": _num(_node_field_value(c, "attack")),
                "defence": _num(_node_field_value(c, "defence")),
            }
            out[c.key] = item
    return out



def _parse_terrain_movement(node):
    """解析 terrain 子块 → {地形键: movement 修正}（兼容旧调用方）。"""
    return {k: v.get("movement") for k, v in _parse_terrain(node).items()}


_SUB_KNOWN_SCALARS = frozenset((
    "abbreviation", "sprite", "group", "parent",
) + _STAT_FIELDS)



def _collect_equip_blocks(node, result, seen):
    """递归收集装备块（equipments = { ... } 包裹一层，部分 mod 直接顶层）。

    node 自身先作为候选（直接顶层写法），再递归子块。
    """
    info = {}
    for cc in node.children:
        if cc.node_type == "value" and cc.key in _EQUIP_STAT_FIELDS:
            v = _num(cc.value)
            if v is not None:
                info[cc.key] = v
    if info and node.key not in seen:
        seen.add(node.key)
        result[node.key] = info  # 首个变体（通常为基础变体 _0）
    for c in node.children:
        if c.node_type == "block":
            _collect_equip_blocks(c, result, seen)



def load_equipment_stats(mod_path="", hoi4_path=""):
    """扫描 common/units/equipment/*.txt 的装备块（如 infantry_equipment_1）。

    Returns:
        dict: 装备名 -> {soft_attack/hard_attack/.../reliability}（该装备
        定义中的直接字段；不追踪 parent 继承，基础值估算用）。
        按 (mod_path, hoi4_path) 缓存。
    """
    key = (mod_path or "", hoi4_path or "")
    if key in _EQUIP_STATS_CACHE:
        return _EQUIP_STATS_CACHE[key]
    result = {}
    seen = set()
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "units", "equipment")
        if not os.path.isdir(d):
            continue
        try:
            names = sorted(os.listdir(d))
        except Exception:
            continue
        for fn in names:
            if not fn.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in parse_pdx_text_to_nodes(content):
                if node.node_type == "block":
                    _collect_equip_blocks(node, result, seen)
    _EQUIP_STATS_CACHE[key] = result
    return result


# ---------- 师编制属性汇总（基础值估算） ----------


def _main_need(need):
    """need 中数量最大的装备（主武器）。"""
    if not need:
        return None
    return max(need, key=lambda k: need[k])



def _find_equip(equip_stats, need_key):
    """装备类别键 → 装备定义：精确匹配 → `键_0` → 变体号最小的 `键_N`。"""
    if not need_key:
        return None
    if need_key in equip_stats:
        return equip_stats[need_key]
    base = need_key + "_0"
    if base in equip_stats:
        return equip_stats[base]
    best_key = None
    best_num = None
    for k in equip_stats:
        if k.startswith(need_key + "_"):
            try:
                num = int(k.rsplit("_", 1)[1])
            except (ValueError, IndexError):
                continue
            if best_num is None or num < best_num:
                best_num = num
                best_key = k
    if best_key is not None:
        return equip_stats[best_key]
    return None




def _accumulate_division_item(stats, info, speeds, orgs, rels, trainings,
                              equip_stats):
    """把一个营/支援连属性累加到 stats 中（含装备回退与地形聚合）。"""
    stats["width"] += info.get("combat_width") or 0
    stats["hp"] += info.get("max_strength") or 0
    stats["manpower"] += int(info.get("manpower") or 0)
    stats["org_regain"] += info.get("org_regain") or 0
    stats["recon"] += info.get("recon") or 0
    stats["suppression"] += info.get("suppression") or 0
    stats["weight"] += info.get("weight") or 0
    stats["supply"] += info.get("supply_consumption") or 0
    stats["fuel"] += info.get("fuel_consumption") or 0
    stats["initiative"] += info.get("initiative") or 0
    spd = info.get("maximum_speed")
    if spd:
        speeds.append(spd)
    org = info.get("max_organisation")
    if org:
        orgs.append(org)
    rel = info.get("reliability")
    if rel is not None:
        rels.append(rel)
    tr = info.get("training_time")
    if tr:
        trainings.append(tr)

    main_eq = _find_equip(equip_stats, _main_need(info.get("need") or {})) or {}
    for f, key in (("soft", "soft_attack"), ("hard", "hard_attack"),
                   ("air", "air_attack"), ("defense", "defense"),
                   ("breakthrough", "breakthrough"),
                   ("armor", "armor"), ("piercing", "piercing")):
        v = info.get(key)
        if v is None:
            v = main_eq.get(key) or 0
        stats[f] += v or 0

    for eq, cnt in (info.get("need") or {}).items():
        stats["equipment"][eq] = stats["equipment"].get(eq, 0) + cnt
    for t, mv in (info.get("terrain") or {}).items():
        acc = stats["terrain"].setdefault(t, [0.0, 0])
        acc[0] += mv
        acc[1] += 1
    for t, full in (info.get("terrain_full") or {}).items():
        box = stats.setdefault("terrain_full", {}).setdefault(
            t, {"movement": [0.0, 0], "attack": [0.0, 0],
                "defence": [0.0, 0]})
        box["movement"][0] += full.get("movement") or 0
        box["movement"][1] += 1
        box["attack"][0] += full.get("attack") or 0
        box["attack"][1] += 1
        box["defence"][0] += full.get("defence") or 0
        box["defence"][1] += 1

def division_stats(tpl, sub_units=None, equip_stats=None):
    """按 HOI4 基础规则汇总师编制属性（基础值估算，未含科技/将领修正）。

    Args:
        tpl: DivisionTemplate
        sub_units: load_sub_units() 结果（营属性）
        equip_stats: load_equipment_stats() 结果（装备攻击属性回退）

    Returns:
        dict: width/manpower/speed/org/hp/org_regain/recon/suppression/
              weight/supply/fuel/training/soft/hard/air/defense/breakthrough/
              armor/piercing/initiative/reliability/equipment{装备:数量}/
              terrain{地形:平均movement}/counts{battalions,support}
    """
    sub_units = sub_units or {}
    equip_stats = equip_stats or {}
    stats = {f: 0.0 for f in (
        "width", "hp", "org_regain", "recon", "suppression", "weight",
        "supply", "fuel", "soft", "hard", "air", "defense", "breakthrough",
        "armor", "piercing", "initiative", "reliability_sum")}
    stats["manpower"] = 0
    stats["equipment"] = {}
    stats["terrain"] = {}          # 地形 -> [和, 计数]
    speeds = []
    orgs = []
    rels = []
    trainings = []
    n_items = 0

    items = [(typ, False) for typ, _x, _y in tpl.regiments]
    items += [(typ, True) for typ, _x, _y in tpl.support]

    for typ, _is_sup in items:
        info = sub_units.get(typ) or {}
        n_items += 1
        _accumulate_division_item(
            stats, info, speeds, orgs, rels, trainings, equip_stats)

    stats["speed"] = min(speeds) if speeds else None
    stats["org"] = (sum(orgs) / len(orgs)) if orgs else 0.0
    stats["reliability"] = (sum(rels) / len(rels)) if rels else None
    stats["training"] = max(trainings) if trainings else 0
    stats["terrain"] = {t: (acc[0] / acc[1])
                        for t, acc in stats["terrain"].items()}
    if stats.get("terrain_full"):
        stats["terrain_full"] = {
            t: {k: (v[0] / v[1]) if v[1] else None
                for k, v in box.items()}
            for t, box in stats["terrain_full"].items()
        }
    stats["counts"] = {"battalions": len(tpl.regiments),
                       "support": len(tpl.support)}
    stats["items"] = n_items
    stats["reliability_sum"] = stats["reliability"]
    return stats


def division_ic_cost(tpl, sub_units=None, equip_stats=None):
    """按装备 build_cost_ic 汇总师编制 IC 花费（基础值估算，未含科技/将领修正）。

    每个营/支援连的 `need`（装备需求）逐项乘该装备定义（前缀匹配 _0/_N 变体）
    的 `build_cost_ic` 求和。未找到装备定义时该装备 IC 计 0。

    Returns:
        {"equipment": {装备: {"count": n, "ic": ic}}, "total_ic": X,
         "total_items": N}
    """
    sub_units = sub_units or {}
    equip_stats = equip_stats or {}
    items = [(typ, False) for typ, _x, _y in tpl.regiments]
    items += [(typ, True) for typ, _x, _y in tpl.support]
    acc = {}
    total_ic = 0.0
    total_items = 0
    for typ, _sup in items:
        info = sub_units.get(typ) or {}
        for eq, cnt in (info.get("need") or {}).items():
            cnt = float(cnt or 0)
            if cnt <= 0:
                continue
            equip = _find_equip(equip_stats, eq) or {}
            ic = float(equip.get("build_cost_ic") or 0)
            entry = acc.setdefault(eq, {"count": 0.0, "ic": 0.0})
            entry["count"] += cnt
            entry["ic"] += cnt * ic
            total_ic += cnt * ic
            total_items += cnt
    return {"equipment": acc, "total_ic": total_ic,
            "total_items": total_items}



