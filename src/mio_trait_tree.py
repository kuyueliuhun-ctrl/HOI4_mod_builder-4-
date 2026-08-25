"""MIO 特质树画布（绘图层/UI，QGraphicsView）。

把 MIO 定义中的 trait 列表按 position{x,y} 网格绘制成树，
并按 relative_position_id / any_parent / all_parents 画连线。
点击节点发出 trait_selected(token)。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
)

NODE_W = 126
NODE_H = 60
CELL_W = 150
CELL_H = 94


class _TraitNode(QGraphicsRectItem):
    """可点击的特质节点卡片。"""

    def __init__(self, x, y, w, h, token, callback):
        super().__init__(x, y, w, h)
        self.token = token
        self._callback = callback
        self.setPen(QPen(QColor("#4a6fa5"), 2))
        self.setBrush(QColor("#ffffff"))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._callback:
            self._callback(self.token)
        super().mousePressEvent(event)


class MioTraitTreeView(QGraphicsView):
    """MIO 特质树画布。"""

    trait_selected = pyqtSignal(str)

    def __init__(self, parent=None, name_of=None, gfx_map=None,
                 mod_path="", hoi4_path=""):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self._name_of = name_of or (lambda k: k)
        self._gfx_map = gfx_map or {}
        self._mod_path = mod_path or ""
        self._hoi4_path = hoi4_path or ""
        self._mio = None
        self._item_to_token = {}

    def set_mio(self, mio):
        self._mio = mio
        self._rebuild()

    def _name(self, token):
        try:
            return self._name_of(token) or token
        except Exception:
            return token

    def _icon_pixmap(self, icon_value):
        try:
            from icon_resolver import resolve_pixmap
            return resolve_pixmap(
                icon_value, gfx_map=self._gfx_map,
                mod_path=self._mod_path, hoi4_path=self._hoi4_path)
        except Exception:
            from PyQt6.QtGui import QPixmap
            return QPixmap()

    def _rebuild(self):
        self._scene.clear()
        self._item_to_token = {}
        mio = self._mio
        if not mio:
            return

        traits = mio.get("traits", []) or []
        positions = {}
        for t in traits:
            token = t.get("token", "")
            if token:
                positions[token] = (t.get("x", 0), t.get("y", 0))

        # 节点
        for t in traits:
            token = t.get("token", "")
            if not token:
                continue
            x, y = positions.get(token, (0, 0))
            px = x * CELL_W + 10
            py = y * CELL_H + 10
            node = _TraitNode(px, py, NODE_W, NODE_H, token,
                              self._on_node_clicked)
            self._item_to_token[id(node)] = token
            self._scene.addItem(node)

            # 图标
            icon = t.get("icon", "")
            pm = self._icon_pixmap(icon)
            if not pm.isNull():
                pm = pm.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                icon_item = self._scene.addPixmap(pm)
                icon_item.setPos(px + 6, py + (NODE_H - 40) // 2)
                icon_item.setZValue(2)
            # 名称
            text = self._name(token)
            txt = QGraphicsTextItem(text)
            txt.setDefaultTextColor(QColor("#162333"))
            f = QFont()
            f.setPointSize(9)
            txt.setFont(f)
            txt.setPos(px + 50, py + (NODE_H - 20) // 2)
            txt.setTextWidth(NODE_W - 54)
            txt.setZValue(2)
            self._scene.addItem(txt)

        # 连线（子 -> 父）
        for t in traits:
            token = t.get("token", "")
            if not token or token not in positions:
                continue
            parents = list(t.get("parents") or [])
            rel = t.get("relative_position_id", "")
            if rel and rel not in parents:
                parents.append(rel)
            cx, cy = positions[token]
            x1 = cx * CELL_W + CELL_W // 2
            y1 = cy * CELL_H + 10
            for p in parents:
                if p not in positions:
                    continue
                px, py = positions[p]
                x2 = px * CELL_W + CELL_W // 2
                y2 = py * CELL_H + CELL_H
                line = QGraphicsLineItem(x1, y1, x2, y2)
                line.setPen(QPen(QColor("#8aa0b8"), 1.5))
                line.setZValue(-1)
                self._scene.addItem(line)

        # 初始特质标记（五角星）
        init = mio.get("initial_trait") or {}
        init_name = init.get("name", "")
        if init_name in positions:
            ix, iy = positions[init_name]
            star = QGraphicsEllipseItem(
                ix * CELL_W + 8, iy * CELL_H + 8, 12, 12)
            star.setBrush(QColor("#e67e22"))
            star.setPen(QPen(QColor("#ffffff"), 1))
            star.setZValue(3)
            self._scene.addItem(star)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-30, -30, 30, 30))

    def _on_node_clicked(self, token):
        self.trait_selected.emit(token)