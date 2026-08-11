"""州/基地数据加载模块

解析游戏与 mod 的 history/states/*.txt（mod 覆盖游戏）：
  - 州：id、名称键（STATE_x）、所属地块列表
  - 海军基地：buildings 块内 `3838 = { naval_base = 3 }`（锚点为具体地块）
  - 空军基地：`air_base = 3`（无地块，取州内首地块作为锚点）

名称经 LocalizationManager 解析为简体中文。
"""

import os

from tree_node import parse_pdx_text_to_nodes


class StateData:
    """州与海军/空军基地数据。"""

    def __init__(self, mod_path="", hoi4_path="", loc_manager=None):
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.loc_manager = loc_manager
        # 州ID -> dict(id, name_key, provinces:[...], naval:{pid:level}, air_level)
        self.states = {}
        # 地块ID -> 州ID 反向索引
        self.province_to_state = {}
        # 海军基地列表 [(地块ID, 等级, 州ID), ...]
        self.naval_bases = []
        # 空军基地列表 [(地块ID, 等级, 州ID), ...]
        self.air_bases = []
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
                    info = self._parse_state(node)
                    if info and info["id"] not in self.states:
                        self._register(info)

    def _parse_state(self, node):
        """解析单个 state = {...} 块。"""
        info = {"id": 0, "name_key": "", "provinces": [], "naval": {},
                "air_level": 0, "owner": ""}
        for child in node.children:
            if child.node_type == "value":
                if child.key == "id":
                    try:
                        info["id"] = int(child.value)
                    except ValueError:
                        return None
                elif child.key == "name":
                    info["name_key"] = child.value
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
        """解析 history 块中的 owner 与 buildings（海军/空军基地）。"""
        for child in history_node.children:
            if child.node_type == "value" and child.key == "owner":
                info["owner"] = child.value.strip().strip('"').upper()
            elif child.node_type == "block" and child.key == "buildings":
                for b in child.children:
                    if b.node_type == "value" and b.key == "air_base":
                        try:
                            info["air_level"] = int(float(b.value))
                        except ValueError:
                            pass
                    elif b.node_type == "block" and b.key.strip().isdigit():
                        pid = int(b.key)
                        for n in b.children:
                            if n.node_type == "value" and n.key == "naval_base":
                                try:
                                    info["naval"][pid] = int(float(n.value))
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
