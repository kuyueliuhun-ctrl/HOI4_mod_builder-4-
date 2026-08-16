"""国策顺序点选器

用于 AI 战略计划编辑器：在国策绘图中通过“点点点”确认 `ai_national_focuses`
顺序。支持：

  - 点击未选国策 → 追加/插入顺序
  - 点击已选国策 → 无动作
  - 右键已选国策：
      - 从该国策开始顺序（插入模式）
      - 退出该状态
      - 删除该顺序（含后续依赖国策）
  - 顺序角标：国策图标右下角黑框红底白字数字
  - 工具栏“加载国策树”切换国家
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen, QFont
from PyQt6.QtWidgets import (
    QDialog, QGraphicsScene, QGraphicsView, QGraphicsRectItem,
    QGraphicsSimpleTextItem, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QPushButton, QVBoxLayout,
)

from focus_processor import FocusProcessor
from localization_mgr import get_localization_manager


def dependent_focuses(focus_data, focus_id):
    """返回依赖 focus_id 的国策集合（直接/间接，不含 focus_id 自身）。"""
    dependents = set()
    stack = [focus_id]
    while stack:
        cur = stack.pop()
        for other, node in focus_data.items():
            if other in dependents:
                continue
            prereqs = node.get("draw", {}).get("prerequisite", []) or []
            if cur in prereqs:
                dependents.add(other)
                stack.append(other)
    return dependents


def remove_focus_with_dependents(ordered, focus_data, focus_id):
    """从顺序中删除 focus_id 及其后续依赖国策。

    返回新顺序列表。若 focus_id 不在顺序中，原样返回。
    """
    if focus_id not in ordered:
        return list(ordered)
    deps = dependent_focuses(focus_data, focus_id)
    return [f for f in ordered if f != focus_id and f not in deps]


def insert_after(ordered, anchor, new_id):
    """把 new_id 插入到 anchor 之后；anchor 不在顺序中则追加到末尾。"""
    if anchor not in ordered:
        return list(ordered) + [new_id]
    out = []
    for fid in ordered:
        out.append(fid)
        if fid == anchor:
            out.append(new_id)
    return out


class FocusOrderScene(QGraphicsScene):
    """国策顺序画布场景（仅用于承载绘图）。"""


class FocusOrderPicker(QDialog):
    """国策顺序点选对话框。"""

    def __init__(self, focus_data=None, ordered=None, country="",
                 mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("国策顺序点选")
        self.resize(1100, 760)
        self._mod_path = mod_path or ""
        self._hoi4_path = hoi4_path or ""
        self._focus_data = focus_data or {}
        self._ordered = list(ordered or [])
        self._insert_anchor = None
        self._country = country or ""
        self._loc = None
        try:
            self._loc = get_localization_manager()
        except Exception:
            self._loc = None
        self._build_ui()
        self._redraw()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.country_label = QLabel("国家：%s" % (self._country or "未选择"))
        bar.addWidget(self.country_label)
        bar.addStretch(1)
        load_btn = QPushButton("📂 加载国策树")
        load_btn.clicked.connect(self._load_tree)
        bar.addWidget(load_btn)
        clear_btn = QPushButton("🗑 清空顺序")
        clear_btn.clicked.connect(self._clear_order)
        bar.addWidget(clear_btn)
        self.insert_label = QLabel("")
        bar.addWidget(self.insert_label)
        root.addLayout(bar)

        self.scene = FocusOrderScene(self)
        self.view = _FocusOrderView(self.scene, self)
        root.addWidget(self.view, 1)

        bottom = QHBoxLayout()
        self.order_label = QLabel("")
        bottom.addWidget(self.order_label, 1)
        save_btn = QPushButton("✅ 确认顺序")
        save_btn.clicked.connect(self.accept)
        bottom.addWidget(save_btn)
        root.addLayout(bottom)

    # ---------- 数据操作 ----------
    def ordered_ids(self):
        return list(self._ordered)

    def _redraw(self):
        from focus_renderer import FocusRenderer
        self.scene.clear()
        if not self._focus_data:
            tip = QGraphicsSimpleTextItem("（无国策树，请点击“加载国策树”）")
            tip.setBrush(QBrush(QColor(200, 200, 120)))
            tip.setPos(30, 30)
            self.scene.addItem(tip)
            self.order_label.setText("当前顺序：—")
            return
        renderer = FocusRenderer(self.scene)
        try:
            renderer.set_loc_manager(self._loc)
        except Exception:
            pass
        renderer.draw_graph(self._focus_data, "<AI顺序>")
        self._draw_order_badges()
        self.order_label.setText("当前顺序：%s" % (" → ".join(self._ordered) if self._ordered else "—"))
        self.insert_label.setText(
            "插入状态：从 %s 之后" % self._insert_anchor if self._insert_anchor else "")
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100))

    def _draw_order_badges(self):
        """在已选国策图标右下角绘制黑框红底白字编号。"""
        order_map = {fid: i + 1 for i, fid in enumerate(self._ordered)}
        for item in self.scene.items():
            fid = item.data(0)
            if not fid or fid not in order_map:
                continue
            # 只对图标/圆形节点绘制，不重复绘制文字/连线
            from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem
            if not isinstance(item, (QGraphicsPixmapItem, QGraphicsEllipseItem)):
                continue
            rect = item.sceneBoundingRect()
            num = order_map[fid]
            size = 22
            badge = QGraphicsRectItem(
                rect.right() - size + 4, rect.bottom() - size + 4, size, size)
            badge.setBrush(QBrush(QColor(180, 20, 20)))
            badge.setPen(QPen(QColor(0, 0, 0), 2))
            badge.setZValue(90)
            self.scene.addItem(badge)
            text = QGraphicsSimpleTextItem(str(num))
            text.setBrush(QBrush(QColor(255, 255, 255)))
            f = QFont()
            f.setBold(True)
            f.setPointSize(10)
            text.setFont(f)
            br = text.boundingRect()
            text.setPos(
                rect.right() - size + 4 + (size - br.width()) / 2,
                rect.bottom() - size + 4 + (size - br.height()) / 2)
            text.setZValue(91)
            self.scene.addItem(text)

    # ---------- 交互 ----------
    def _focus_at(self, scene_pos):
        """返回 scene_pos 命中的国策 ID；未命中返回 None。"""
        # QGraphicsView 的 itemAt 是视图坐标，这里通过场景坐标遍历更稳定
        for item in self.scene.items():
            fid = item.data(0)
            if not fid:
                continue
            from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem
            if isinstance(item, (QGraphicsPixmapItem, QGraphicsEllipseItem)):
                if item.sceneBoundingRect().contains(scene_pos):
                    return fid
        return None

    def _on_left_click(self, scene_pos):
        fid = self._focus_at(scene_pos)
        if not fid:
            return
        if fid in self._ordered:
            return  # 已选国策点击无动作
        if self._insert_anchor and self._insert_anchor in self._ordered:
            self._ordered = insert_after(self._ordered, self._insert_anchor, fid)
        else:
            self._ordered.append(fid)
        self._redraw()

    def _on_right_click(self, scene_pos, global_pos):
        fid = self._focus_at(scene_pos)
        if not fid or fid not in self._ordered:
            return
        menu = QMenu(self)
        act_insert = menu.addAction("从该国策开始顺序")
        act_insert.triggered.connect(lambda: self._set_insert_anchor(fid))
        if self._insert_anchor:
            act_exit = menu.addAction("退出该状态")
            act_exit.triggered.connect(self._exit_insert_state)
        act_delete = menu.addAction("删除该顺序")
        act_delete.triggered.connect(lambda: self._delete_order(fid))
        menu.exec(global_pos)

    def _set_insert_anchor(self, fid):
        self._insert_anchor = fid
        self._redraw()

    def _exit_insert_state(self):
        self._insert_anchor = None
        self._redraw()

    def _delete_order(self, fid):
        self._ordered = remove_focus_with_dependents(
            self._ordered, self._focus_data, fid)
        if self._insert_anchor == fid or (
                self._insert_anchor and self._insert_anchor not in self._ordered):
            self._insert_anchor = None
        self._redraw()

    def _clear_order(self):
        self._ordered = []
        self._insert_anchor = None
        self._redraw()

    def _load_tree(self):
        from workbench import WorkbenchDock
        files = self._collect_focus_files()
        if not files:
            QMessageBox.information(self, "加载国策树", "未找到国策文件")
            return
        tags = set()
        for fp in files:
            content = self._read_file(fp)
            tags.update(WorkbenchDock._detect_country_tags(fp, content))
        if not tags:
            QMessageBox.information(self, "加载国策树", "未从国策文件中识别到国家")
            return
        from PyQt6.QtWidgets import QInputDialog
        items = sorted(tags)
        item, ok = QInputDialog.getItem(
            self, "加载国策树", "选择国家：", items, 0, False)
        if not ok or not item:
            return
        self._load_country(item, files)

    def _load_country(self, country, files=None):
        from workbench import WorkbenchDock
        files = files if files is not None else self._collect_focus_files()
        kept = [fp for fp in files
                if country in WorkbenchDock._detect_country_tags(
                    fp, self._read_file(fp))]
        merged = {}
        for fp in kept:
            content = self._read_file(fp)
            try:
                data = WorkbenchDock._quick_focus_scan(content)
                for fid, node in data.items():
                    merged.setdefault(fid, node)
            except Exception:
                continue
        proc = FocusProcessor()
        proc.focus_data = merged
        proc._calculate_absolute_positions()
        self._focus_data = merged
        self._country = country
        self.country_label.setText("国家：%s" % country)
        self._ordered = [f for f in self._ordered if f in merged]
        self._redraw()

    def _collect_focus_files(self):
        mod = getattr(self, "_mod_path", "")
        hoi4 = getattr(self, "_hoi4_path", "")
        files = []
        seen = set()
        for base in (mod, hoi4):
            if not base or not os.path.isdir(base):
                continue
            d = os.path.join(base, "common", "national_focus")
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if not name.lower().endswith(".txt"):
                    continue
                fp = os.path.join(d, name)
                real = os.path.realpath(fp)
                if real in seen:
                    continue
                seen.add(real)
                files.append(fp)
        return files

    @staticmethod
    def _read_file(fp):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""


class _FocusOrderView(QGraphicsView):
    """支持左键点选、右键菜单的国策顺序视图。"""

    def __init__(self, scene, picker):
        super().__init__(scene)
        self._picker = picker
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self._picker._on_left_click(scene_pos)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            scene_pos = self.mapToScene(event.pos())
            self._picker._on_right_click(scene_pos, event.globalPos())
            event.accept()
            return
        super().mousePressEvent(event)
