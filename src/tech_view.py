"""
科技树工具模块（供国策树画布复用）。

- _scan_mod_techs(): 扫描 mod 全部 common/technologies/*.txt，合并科技数据
- _classify(): 划分 树科技 / 非树科技 / 子科技
- layout_tech_trees(): 树形自动布局（像国策树：锚点=根、path 连线为边、
  BFS 深度分层，兄弟横向铺开、链纵向延伸；忽略 folder.position 坐标）
- _TechNodeItem / _SubTechSlot: 画布节点图形项（图标 + 名称 + 标注）

科技图标规则见 docs/科技图标存储规则.md：GFX_<科技id>_medium sprite 注册在
interface/*.gfx，纹理在 gfx/interface/technologies/。
"""
from project_paths import PROJECT_ROOT

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QPen, QFont
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsPixmapItem, \
    QGraphicsSimpleTextItem

from entity_scanner import EntityScanner as WorkbenchDock

GRID_X = 250
GRID_Y = 150
NODE_ICON_H = 46          # 节点图标显示高度（宽按比例，上限 230）
NODE_W = 250
NODE_H = 112
SUBTECH_W = 46
SUBTECH_H = 30
FOLDER_COLORS = ["#3a5a8c", "#5a7a4a", "#8c6a3a", "#6a4a8c", "#3a7a7a",
                 "#8c4a4a", "#4a6a8c", "#7a7a3a"]
NON_TREE_COLS = 3


def _settings():
    import json
    p = os.path.join(PROJECT_ROOT, "settings.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _scan_mod_techs(mod_path):
    """扫描 mod 全部 common/technologies/*.txt，合并返回 {id: node}。

        node 额外带 file（来源文件路径，供打开定义文件）。
    """
    result = {}
    tech_dir = os.path.join(mod_path, "common", "technologies")
    if not os.path.isdir(tech_dir):
        return result
    for fn in sorted(os.listdir(tech_dir)):
        if not fn.lower().endswith((".txt", ".info")):
            continue
        fp = os.path.join(tech_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        for tid, node in WorkbenchDock._quick_tech_scan(content).items():
            if tid in result:
                continue
            node["file"] = fp
            result[tid] = node
    return result


def _classify(techs):
    """划分树科技 / 非树科技 / 子科技。

    树科技：有 folder 属性，或被其他科技 path 引用（有入边/出边）
    子科技：出现在某个科技的 sub_technologies 列表中
    非树科技：无 folder、无连线、非子科技（由国策/事件/决议等解锁）

    Returns:
        (tree_ids, non_tree_ids, sub_tech_ids)
    """
    sub_ids = set()
    for node in techs.values():
        for s in node.get("sub_techs", []):
            sub_ids.add(s)
    has_in = {}
    has_out = {}
    for tid, node in techs.items():
        outs = [t for t in node.get("leads_to", []) if t in techs]
        has_out[tid] = bool(outs)
        for t in outs:
            has_in[t] = True
    tree_ids = set()
    non_tree_ids = set()
    for tid, node in techs.items():
        if tid in sub_ids:
            continue
        if node.get("folder") or has_in.get(tid) or has_out.get(tid):
            tree_ids.add(tid)
        else:
            non_tree_ids.add(tid)
    return tree_ids, non_tree_ids, sub_ids


def layout_tech_trees(techs, tree_ids):
    """树形自动布局：每个 folder 一棵树（像国策树那样绘制）。

    - 根 = 有 folder 属性的科技（folder 锚点），或无可达根时取无入边科技
    - path 边 A→B（A 前置）作为父子关系，BFS 分层：深度 = y 行
    - 同层兄弟从左到右横向铺开（x 列）；忽略 folder.position 坐标
      （mod 的坐标常与 GUI gridbox 绑定，直接使用会把并行链拉成直线）

    Returns:
        dict: {folder_name: {tech_id: (x_px, y_px)}}
    """
    folders = {}
    for tid in tree_ids:
        folders.setdefault(techs[tid].get("folder") or "未分组", []).append(tid)

    out = {}
    for fname, ids in folders.items():
        id_set = set(ids)
        children = {t: [] for t in id_set}
        parents = {t: [] for t in id_set}
        for tid in id_set:
            for c in techs[tid].get("leads_to", []):
                if c in id_set:
                    children[tid].append(c)
                    parents[c].append(tid)
        # 根 = 无入边的科技（链首；mod 常给每个科技写 folder 属性，
        # 不能以 folder 判定根，否则整棵树被拉成一行）
        roots = [t for t in ids if not parents[t]]
        if not roots:
            roots = [t for t in ids if techs[t].get("folder")]
        if not roots:
            roots = [ids[0]]
        # BFS 深度（seen 防环）
        depth = {}
        seen = set()
        queue = [(r, 0) for r in roots]
        while queue:
            cur, d = queue.pop(0)
            if cur in seen:
                continue
            seen.add(cur)
            depth[cur] = d
            for c in children.get(cur, []):
                if c not in seen:
                    queue.append((c, d + 1))
        for t in id_set:
            if t not in depth:
                depth[t] = 0
        # 同层按 BFS 发现顺序横向排列
        order = []
        q2 = [(r, 0) for r in roots]
        seen2 = set()
        while q2:
            cur, _d = q2.pop(0)
            if cur in seen2:
                continue
            seen2.add(cur)
            order.append(cur)
            for c in children.get(cur, []):
                if c not in seen2:
                    q2.append((c, depth[c]))
        layers = {}
        for t in order:
            layers.setdefault(depth.get(t, 0), []).append(t)
        for t in id_set:
            if t not in layers[depth.get(t, 0)]:
                layers.setdefault(depth.get(t, 0), []).append(t)
        pos = {}
        for layer in sorted(layers):
            for i, t in enumerate(layers[layer]):
                pos[t] = (i * GRID_X, layer * GRID_Y)
        out[fname] = pos
    return out


class _TechNodeItem(QGraphicsRectItem):
    """科技树节点：图标 + 名称 + 标注。"""

    def __init__(self, tech_id, node, icon_pm, label, color, x, y):
        w, h = NODE_W, NODE_H
        super().__init__(0, 0, w, h)
        self.tech_id = tech_id
        self.setData(0, tech_id)
        self.setData(1, node.get("file", ""))
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(color)))
        pen = QPen(QColor(30, 30, 30, 200))
        pen.setWidth(2)
        self.setPen(pen)

        px = 8
        py = 8
        if icon_pm is not None and not icon_pm.isNull():
            ih = NODE_ICON_H
            iw = int(icon_pm.width() * ih / max(1, icon_pm.height()))
            iw = min(iw, 232)
            scaled = icon_pm.scaled(iw, ih, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
            pmi = QGraphicsPixmapItem(scaled, self)
            pmi.setPos(px, py)
        else:
            ph = QGraphicsRectItem(0, 0, 200, NODE_ICON_H, self)
            ph.setBrush(QBrush(QColor(40, 40, 40, 120)))
            ph.setPos(px, py)
            tip = QGraphicsSimpleTextItem("无图标", ph)
            tip.setBrush(QBrush(QColor(160, 160, 160)))
            f = QFont("Microsoft YaHei", 8)
            tip.setFont(f)
            tip.setPos(75, 13)

        name_txt = label or tech_id
        name = QGraphicsSimpleTextItem(name_txt, self)
        name.setBrush(QBrush(QColor(255, 255, 255)))
        f = QFont("Microsoft YaHei", 9)
        f.setBold(True)
        name.setFont(f)
        name.setPos(px, py + NODE_ICON_H + 2)

        id_txt = QGraphicsSimpleTextItem(tech_id, self)
        id_txt.setBrush(QBrush(QColor(200, 200, 200)))
        f2 = QFont("Consolas", 7)
        id_txt.setFont(f2)
        id_txt.setPos(px, py + NODE_ICON_H + 22)

        tags = []
        if node.get("unresearchable"):
            tags.append("不可研究")
        tags.extend(node.get("allow_tags", []))
        if node.get("hidden"):
            tags.append("隐藏")
        if tags:
            tag = QGraphicsSimpleTextItem(" · ".join(tags), self)
            tag.setBrush(QBrush(QColor(255, 220, 130)))
            f3 = QFont("Microsoft YaHei", 7)
            tag.setFont(f3)
            tag.setPos(px, py + NODE_ICON_H + 38)
        else:
            info = []
            if node.get("cost"):
                info.append(f"成本 {node['cost']}")
            if node.get("start_year"):
                info.append(f"{node['start_year']}")
            if info:
                it = QGraphicsSimpleTextItem(" ".join(info), self)
                it.setBrush(QBrush(QColor(190, 210, 230)))
                f4 = QFont("Microsoft YaHei", 7)
                it.setFont(f4)
                it.setPos(px, py + NODE_ICON_H + 38)


class _SubTechSlot(QGraphicsRectItem):
    """子科技槽位：显示在父节点下方（编号 + id）。"""

    def __init__(self, index, sub_id, x, y):
        super().__init__(0, 0, SUBTECH_W, SUBTECH_H)
        self.tech_id = sub_id
        self.setData(0, sub_id)
        self.setData(1, "")
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(40, 50, 40)))
        pen = QPen(QColor(120, 160, 120))
        pen.setWidth(1)
        self.setPen(pen)
        num = QGraphicsSimpleTextItem(str(index), self)
        num.setBrush(QBrush(QColor(160, 220, 160)))
        f = QFont("Consolas", 7)
        f.setBold(True)
        num.setFont(f)
        num.setPos(3, 2)
        nm = QGraphicsSimpleTextItem(sub_id, self)
        nm.setBrush(QBrush(QColor(220, 220, 220)))
        f2 = QFont("Consolas", 6)
        nm.setFont(f2)
        nm.setPos(14, 8)
