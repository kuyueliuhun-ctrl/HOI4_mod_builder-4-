"""MIO 特质树画布（绘图层/UI，QGraphicsView）。

把 MIO 定义中的 trait 列表按 position{x,y} 网格绘制成树，
并按 relative_position_id / any_parent / all_parents 画连线。
点击节点发出 trait_selected(token)。

配色与编辑器全局主题一致（theme.py）；
特质名单行省略（tooltip 看全名），无特质时画布给出占位提示。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsView,
)

from theme import COLORS as C

NODE_W = 126
NODE_H = 60
CELL_W = 150
CELL_H = 94


class _TraitNode(QGraphicsRectItem):
    """可点击的特质节点卡片（主题白卡 + 主色描边，选中转主色软底）。"""

    def __init__(self, x, y, w, h, token, callback):
        super().__init__(x, y, w, h)
        self.token = token
        self._callback = callback
        self._apply_look(False)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def _apply_look(self, selected):
        if selected:
            self.setPen(QPen(QColor(C["accent"]), 2))
            self.setBrush(QColor("#d9e5f2"))  # accent_soft 等效实色
        else:
            self.setPen(QPen(QColor("#b9c5d1"), 1))
            self.setBrush(QColor(C["bg_surface"]))

    def paint(self, painter, option, widget=None):
        self._apply_look(self.isSelected())
        super().paint(painter, option, widget)

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
        self.setBackgroundBrush(QColor(C["bg_surface_subtle"]))
        self.setStyleSheet(
            "QGraphicsView { border: 1px solid #d9e0e7; background: %s; }"
            % C["bg_surface_subtle"])
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

    def _resolve_positions(self, traits):
        """按游戏规则解析绝对网格坐标。

        position 的 x/y 在带 relative_position_id 时是相对另一特质的偏移：
        abs(t) = abs(relative_position_id) + (x, y)。递归解析 + 环防护；
        引用缺失/成环时退化为把 x/y 当绝对坐标。解析后若仍同格叠加，
        向右顺序找空位（数据本身错误时的兜底）。
        """
        raw, rel = {}, {}
        for t in traits:
            tok = t.get("token", "")
            if not tok:
                continue
            try:
                raw[tok] = (int(t.get("x", 0) or 0), int(t.get("y", 0) or 0))
            except (TypeError, ValueError):
                raw[tok] = (0, 0)
            rel[tok] = t.get("relative_position_id", "")
        resolved = {}

        def resolve(tok, stack):
            if tok in resolved:
                return resolved[tok]
            bx, by = raw.get(tok, (0, 0))
            base = rel.get(tok, "")
            if base and base != tok and base in raw and base not in stack:
                px, py = resolve(base, stack | {tok})
                pos = (px + bx, py + by)
            else:
                pos = (bx, by)
            resolved[tok] = pos
            return pos

        for tok in raw:
            resolve(tok, set())
        # 同格叠加兜底：按出现顺序向右找空位
        used = set()
        for tok in raw:
            x, y = resolved.get(tok, (0, 0))
            while (x, y) in used:
                x += 1
            resolved[tok] = (x, y)
            used.add((x, y))
        return resolved

    def _rebuild(self):
        self._scene.clear()
        self._item_to_token = {}
        mio = self._mio
        if not mio:
            return

        traits = mio.get("traits", []) or []
        if not traits:
            self._draw_placeholder("（该组织未定义特质树）")
            return
        positions = self._resolve_positions(traits)

        # 连线（子 -> 父，先画线再画节点，节点覆盖线头）
        # 注意：relative_position_id 只用于定位，游戏不为其画线
        drawn = set()
        for t in traits:
            token = t.get("token", "")
            if not token or token not in positions:
                continue
            cx, cy = positions[token]
            x1 = cx * CELL_W + 10 + NODE_W // 2
            y1 = cy * CELL_H + 10
            for p in t.get("parents") or []:
                if p not in positions or (p, token) in drawn:
                    continue
                drawn.add((p, token))
                px, py = positions[p]
                x2 = px * CELL_W + 10 + NODE_W // 2
                y2 = py * CELL_H + 10 + NODE_H
                line = QGraphicsLineItem(x1, y1, x2, y2)
                line.setPen(QPen(QColor("#b3bec9"), 1.4))
                line.setZValue(-1)
                self._scene.addItem(line)

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
            node.setToolTip(token)
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
            # 名称（单行省略，tooltip 看全名，杜绝溢出节点）
            label = self._name(token)
            f = QFont()
            f.setPointSize(9)
            fm = self.fontMetrics()
            shown = fm.elidedText(label, Qt.TextElideMode.ElideRight,
                                  NODE_W - 58)
            txt = QGraphicsSimpleTextItem(shown)
            txt.setFont(f)
            txt.setBrush(QColor(C["text_primary"]))
            txt.setToolTip("%s\n%s" % (label, token))
            txt.setPos(px + 50, py + (NODE_H - 16) // 2)
            txt.setZValue(2)
            self._scene.addItem(txt)

        # 初始特质标记（★ 画在节点右上角，避免与图标重叠）
        init = mio.get("initial_trait") or {}
        init_name = init.get("name", "")
        if init_name in positions:
            ix, iy = positions[init_name]
            star = QGraphicsTextItem("★")
            f = QFont()
            f.setPointSize(11)
            star.setFont(f)
            star.setDefaultTextColor(QColor(C["map_accent"]))
            star.setToolTip("初始特质：%s" % self._name(init_name))
            star.setPos(ix * CELL_W + 10 + NODE_W - 18, iy * CELL_H + 8)
            star.setZValue(3)
            self._scene.addItem(star)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-30, -30, 30, 30))

    def _draw_placeholder(self, text):
        """空画布占位提示（居中、次级文字色）。"""
        txt = QGraphicsTextItem(text)
        f = QFont()
        f.setPointSize(12)
        txt.setFont(f)
        txt.setDefaultTextColor(QColor(C["text_tertiary"]))
        self._scene.addItem(txt)
        self._scene.setSceneRect(txt.boundingRect().adjusted(-40, -40, 40, 40))
        self.centerOn(txt)

    def _on_node_clicked(self, token):
        self.trait_selected.emit(token)
