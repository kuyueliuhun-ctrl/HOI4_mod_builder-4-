"""州/基地数据加载模块

解析游戏与 mod 的 history/states/*.txt（mod 覆盖游戏）：
  - 州：id、名称键（STATE_x）、所属地块列表、州类别（state_category）、
    manpower、胜利点、完整建筑列表（顶层键 + 按地块锚定）
  - 海军基地：buildings 块内 `3838 = { naval_base = 3 }`（锚点为具体地块）
  - 空军基地：`air_base = 3`（无地块，取州内首地块作为锚点）
  - 建筑位：common/state_category/*.txt（mod→游戏）的 local_building_slots

名称经 LocalizationManager 解析为简体中文。
"""

import os

from tree_node import parse_pdx_text_to_nodes


def load_state_categories(mod_path, hoi4_path):
    """解析 common/state_category/*.txt（mod 优先，游戏兜底）。

    Returns:
        dict: 类别名 -> 建筑位数量（local_building_slots）
    """
    out = {}
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "state_category")
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(d, name), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in parse_pdx_text_to_nodes(content):
                if node.node_type != "block":
                    continue
                # 包裹层 state_categories = { town = {...} ... }
                blocks = (node.children if node.key == "state_categories"
                          else [node])
                for b in blocks:
                    if b.node_type != "block":
                        continue
                    cat = b.key
                    slots = 0
                    for child in b.children:
                        if (child.node_type == "value"
                                and child.key == "local_building_slots"):
                            try:
                                slots = int(float(child.value))
                            except ValueError:
                                slots = 0
                    if cat not in out or slots:
                        out[cat] = slots
    return out


class StateData:
    """州与海军/空军基地数据。"""

    def __init__(self, mod_path="", hoi4_path="", loc_manager=None):
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.loc_manager = loc_manager
        # 州ID -> dict(id, name_key, provinces:[...], naval:{pid:level},
        #              air_level, state_category, manpower, buildings,
        #              buildings_pid, victory_points, src)
        self.states = {}
        # 地块ID -> 州ID 反向索引
        self.province_to_state = {}
        # 海军基地列表 [(地块ID, 等级, 州ID), ...]
        self.naval_bases = []
        # 空军基地列表 [(地块ID, 等级, 州ID), ...]
        self.air_bases = []
        # 州类别 -> 建筑位（common/state_category）
        self.categories = load_state_categories(mod_path, hoi4_path)
        self._load()

    def reload(self):
        """写回 mod 后重新加载（mod 覆盖游戏后新内容生效）。"""
        self.states = {}
        self.province_to_state = {}
        self.naval_bases = []
        self.air_bases = []
        self.categories = load_state_categories(
            self.mod_path, self.hoi4_path)
        self._load()

    # ---------- 加载 ----------

    def _state_dirs(self):
        dirs = []
        if self.mod_path:
            d = os.path.join(self.mod_path, "history", "states")
            if os.path.isdir(d):
                dirs.append(d)
        if self.hoi4_path:
            d = os.path.join(self.hoi4_path, "history", "states")
            if os.path.isdir(d) and d not in dirs:
                dirs.append(d)
        return dirs

    def _load(self):
        for d in self._state_dirs():
            try:
                names = sorted(os.listdir(d))
            except Exception:
                continue
            for name in names:
                if not name.lower().endswith(".txt"):
                    continue
                path = os.path.join(d, name)
                try:
                    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                for node in parse_pdx_text_to_nodes(content):
                    if node.node_type != "block" or node.key != "state":
                        continue
                    info = self._parse_state(node, path)
                    if info and info["id"] not in self.states:
                        self._register(info)

    def _parse_state(self, node, src=""):
        """解析单个 state = {...} 块。"""
        info = {"id": 0, "name_key": "", "provinces": [], "naval": {},
                "air_level": 0, "owner": "", "state_category": "",
                "manpower": 0, "victory_points": [], "buildings": {},
                "buildings_pid": {}, "src": src}
        for child in node.children:
            if child.node_type == "value":
                if child.key == "id":
                    try:
                        info["id"] = int(child.value)
                    except ValueError:
                        return None
                elif child.key == "name":
                    info["name_key"] = child.value
                elif child.key == "state_category":
                    info["state_category"] = child.value.strip().strip('"')
                elif child.key == "manpower":
                    try:
                        info["manpower"] = int(float(child.value))
                    except ValueError:
                        pass
            else:  # block
                if child.key == "provinces":
                    for p in child.children:
                        if p.node_type == "value" and p.key.strip().isdigit():
                            info["provinces"].append(int(p.key))
                elif child.key == "history":
                    self._parse_history(info, child)
        return info

    @staticmethod
    def _parse_history(info, history_node):
        """解析 history 块中的 owner、胜利点与完整 buildings。"""
        for child in history_node.children:
            if child.node_type == "value" and child.key == "owner":
                info["owner"] = child.value.strip().strip('"').upper()
            elif child.node_type == "block" and child.key == "buildings":
                for b in child.children:
                    if b.node_type == "value":
                        try:
                            lv = int(float(b.value))
                        except ValueError:
                            continue
                        info["buildings"][b.key] = lv
                        if b.key == "air_base":
                            info["air_level"] = lv
                    elif b.node_type == "block" and b.key.strip().isdigit():
                        pid = int(b.key)
                        d = info["buildings_pid"].setdefault(pid, {})
                        for n in b.children:
                            if n.node_type == "value":
                                try:
                                    d[n.key] = int(float(n.value))
                                except ValueError:
                                    pass
                        if "naval_base" in d:
                            info["naval"][pid] = d["naval_base"]
            elif child.node_type == "block" and child.key == "victory_points":
                # 配对序列：pid points pid points ...
                items = [c.key.strip() for c in child.children
                         if c.node_type == "value"]
                for i in range(0, len(items) - 1, 2):
                    try:
                        info["victory_points"].append(
                            (int(float(items[i])), int(float(items[i + 1]))))
                    except ValueError:
                        pass

    def _register(self, info):
        sid = info["id"]
        self.states[sid] = info
        for pid in info["provinces"]:
            self.province_to_state.setdefault(pid, sid)
        for pid, level in info["naval"].items():
            self.naval_bases.append((pid, level, sid))
        if info["air_level"] > 0:
            anchor = info["provinces"][0] if info["provinces"] else 0
            self.air_bases.append((anchor, info["air_level"], sid))

    # ---------- 查询 ----------

    def state_name(self, state_id):
        """州名称：本地化中文，回退名称键。"""
        info = self.states.get(state_id)
        if not info:
            return ""
        key = info["name_key"] or f"STATE_{state_id}"
        if self.loc_manager is not None:
            try:
                cn = self.loc_manager.get_name(key)
                if cn:
                    return cn
            except Exception:
                pass
        return key

    def category_slots(self, category):
        """州类别 -> 建筑位数量（未知类别返回 0）。"""
        if not category:
            return 0
        return int(self.categories.get(category, 0))

    def slots_of(self, state_id):
        """州建筑位数量（state_category 的 local_building_slots）。"""
        info = self.states.get(state_id)
        return self.category_slots(info["state_category"]) if info else 0

    def buildings_of(self, state_id):
        """州建筑汇总：{type: level}（含按地块锚定的防御类）。"""
        info = self.states.get(state_id)
        if not info:
            return {}
        out = dict(info.get("buildings", {}))
        for d in info.get("buildings_pid", {}).values():
            for k, v in d.items():
                out[k] = out.get(k, 0) + v
        return out

    def state_of_province(self, pid):
        """地块所属州ID，未知返回 0。"""
        return self.province_to_state.get(pid, 0)

    # ---------- 国家 ----------

    def owners(self):
        """返回所有有主州的标签集合。"""
        return sorted({info["owner"] for info in self.states.values()
                       if info["owner"]})

    def provinces_of_owner(self, tag):
        """国家标签 -> 拥有的地块ID列表。"""
        tag = tag.upper()
        out = []
        for info in self.states.values():
            if info["owner"] == tag:
                out.extend(info["provinces"])
        return out

    def owner_of_province(self, pid):
        """地块所属国家标签，未知返回 ""。"""
        sid = self.province_to_state.get(pid, 0)
        info = self.states.get(sid)
        return info["owner"] if info else ""

    def owner_province_map(self):
        """国家标签 -> 地块ID列表（所有有主地块）。"""
        by_owner = {}
        for info in self.states.values():
            if not info["owner"]:
                continue
            by_owner.setdefault(info["owner"], []).extend(info["provinces"])
        return by_owner
