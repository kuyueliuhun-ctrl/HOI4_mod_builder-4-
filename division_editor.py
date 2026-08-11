"""师编制编辑器 — 仿游戏内师设计器（Division Designer）

左侧模板列表（新建/复制/删除），右侧编辑区：
  - 模板名、is_locked
  - regiments 网格（5 列 x 动态行）+ support 横栏（5 槽）
  - 兵种面板（战斗连 / 支援连分组），点击兵种 → 点空槽放置，点已占槽移除
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QCheckBox, QLabel, QMessageBox, QGridLayout,
    QScrollArea, QWidget, QFrame, QSplitter, QGroupBox
)

from oob_loader import DivisionTemplate

SLOT_SIZE = 92
SLOT_ICON = 48


def unit_icon(name, sub_units, gfx_map, mod_path, hoi4_path):
    """兵种图标 QIcon（GFX_unit_<type>_icon_medium），失败回退缩写文本占位。"""
    from icon_resolver import resolve_pixmap
    try:
        pm = resolve_pixmap(f"GFX_unit_{name}_icon_medium", gfx_map=gfx_map,
                            mod_path=mod_path, hoi4_path=hoi4_path)
        if pm is not None and not pm.isNull():
            return QIcon(pm)
    except Exception:
        pass
    return None


class DivisionEditor(QDialog):
    """师编制编辑器。"""

    tree_saved = pyqtSignal()   # 保存成功信号

    def __init__(self, oob_file, sub_units=None, gfx_map=None,
                 mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.oob_file = oob_file
        self.sub_units = sub_units or {}
        self.gfx_map = gfx_map or {}
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        # 当前选中要放入格子的兵种类型（None = 未选，点击已占槽为移除）
        self.picked_type = None
        # 当前编辑中的模板
        self.current = None

        self.setWindowTitle("师编制编辑器")
        self.resize(980, 620)
        self._build_ui()
        self._refresh_template_list()
        self._refresh_palette()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 工具栏
        bar = QHBoxLayout()
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)
        bar.addWidget(self.save_btn)
        bar.addStretch(1)
        self.place_btn = QPushButton("🗺 地图放置陆军…")
        self.place_btn.clicked.connect(self._open_map)
        bar.addWidget(self.place_btn)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：模板列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("师编制模板:"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_template_selected)
        left_layout.addWidget(self.list_widget)
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("＋ 新建")
        self.add_btn.clicked.connect(self._add_template)
        self.copy_btn = QPushButton("⧉ 复制")
        self.copy_btn.clicked.connect(self._copy_template)
        self.del_btn = QPushButton("🗑 删除")
        self.del_btn.clicked.connect(self._delete_template)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.del_btn)
        left_layout.addLayout(btn_row)
        split.addWidget(left)

        # 右侧：编辑区 + 兵种面板
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 模板属性
        prop = QHBoxLayout()
        prop.addWidget(QLabel("模板名:"))
        self.name_edit = QLineEdit()
        self.name_edit.setFixedWidth(260)
        self.name_edit.textChanged.connect(self._on_name_changed)
        prop.addWidget(self.name_edit)
        self.locked_check = QCheckBox("is_locked（锁模板）")
        self.locked_check.toggled.connect(self._on_locked_changed)
        prop.addWidget(self.locked_check)
        prop.addStretch(1)
        right_layout.addLayout(prop)

        # 编制网格区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.grid_host)
        right_layout.addWidget(scroll, 1)

        # 兵种面板
        pal_box = QGroupBox("兵种面板（先选兵种，再点击格子放置；点击已占格子移除）")
        pal_layout = QVBoxLayout(pal_box)
        self.palette_list = QListWidget()
        self.palette_list.setIconSize(QSize(40, 40))
        self.palette_list.currentItemChanged.connect(self._on_palette_changed)
        self.palette_list.setFixedHeight(190)
        pal_layout.addWidget(self.palette_list)
        right_layout.addWidget(pal_box)

        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        root.addWidget(split, 1)

    # ---------- 数据刷新 ----------

    def _refresh_template_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for t in self.oob_file.templates:
            n = len(self.oob_file.placements_for_template(t.name))
            item = QListWidgetItem(f"{t.name}   ({n} 个部署)")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

    def _refresh_palette(self):
        """兵种面板：战斗连分组 + 支援连分组。"""
        self.palette_list.blockSignals(True)
        self.palette_list.clear()
        for group, is_support in (("战斗兵种", False), ("支援连", True)):
            header = QListWidgetItem(f"— {group} —")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setForeground(QColor(150, 150, 150))
            self.palette_list.addItem(header)
            types = sorted(k for k, v in self.sub_units.items() if v["support"] == is_support)
            for name in types:
                info = self.sub_units[name]
                label = f"{name}  ({info['abbreviation']})"
                item = QListWidgetItem(label)
                icon = unit_icon(name, self.sub_units, self.gfx_map,
                                 self.mod_path, self.hoi4_path)
                if icon is not None:
                    item.setIcon(icon)
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.palette_list.addItem(item)
            if not types:
                empty = QListWidgetItem("（无）")
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                empty.setForeground(QColor(120, 120, 120))
                self.palette_list.addItem(empty)
        self.palette_list.blockSignals(False)

    def _on_palette_changed(self, current, _prev):
        self.picked_type = current.data(Qt.ItemDataRole.UserRole) if current else None

    # ---------- 编辑区 ----------

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_template_selected(self, row):
        item = self.list_widget.item(row)
        if item is None:
            return
        tpl = item.data(Qt.ItemDataRole.UserRole)
        if tpl is None:
            return
        self.current = tpl
        self._rebuild_editor(tpl)

    def _rebuild_editor(self, tpl):
        self._clear_grid()
        self.name_edit.blockSignals(True)
        self.locked_check.blockSignals(True)
        self.name_edit.setText(tpl.name)
        self.locked_check.setChecked(bool(tpl.is_locked))
        self.name_edit.blockSignals(False)
        self.locked_check.blockSignals(False)

        rows = max((y for _t, _x, y in tpl.regiments), default=0) + 1
        cols = 5
        # 网格（regiments）
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.addWidget(QLabel("战斗兵种:"), 0, 0, 1, cols)
        for y in range(rows):
            for x in range(cols):
                slot = self._make_slot(tpl, is_support=False, x=x, y=y)
                grid.addWidget(slot, y + 1, x)
        self.grid_layout.addLayout(grid)

        # 支援横栏（support）
        sup = QGridLayout()
        sup.setSpacing(6)
        sup.addWidget(QLabel("支援连:"), 0, 0, 1, cols)
        for x in range(cols):
            slot = self._make_slot(tpl, is_support=True, x=x, y=0)
            sup.addWidget(slot, 1, x)
        self.grid_layout.addLayout(sup)
        self.grid_layout.addStretch(1)

    def _make_slot(self, tpl, is_support, x, y):
        """创建单个格子按钮。"""
        lst = tpl.support if is_support else tpl.regiments
        typ = next((t for t, tx, ty in lst if tx == x and ty == y), None)
        btn = QPushButton()
        btn.setFixedSize(SLOT_SIZE, SLOT_SIZE)
        btn.setStyleSheet(
            "QPushButton { border: 1px dashed #555; background: #2b2b30; }"
            "QPushButton:hover { background: #35353c; }")
        if typ:
            info = self.sub_units.get(typ, {})
            abbr = info.get("abbreviation") or typ.upper()
            icon = unit_icon(typ, self.sub_units, self.gfx_map,
                             self.mod_path, self.hoi4_path)
            text = f"{abbr}\n{typ}"
            if icon is not None:
                btn.setIcon(icon)
                btn.setIconSize(QSize(SLOT_ICON, SLOT_ICON))
            else:
                text = abbr
            btn.setText(text)
            btn.setStyleSheet(
                "QPushButton { border: 1px solid #7a8; background: #2f3a32; }"
                "QPushButton:hover { background: #3a463c; }")
            btn.setToolTip(f"{typ} ({abbr})  x={x} y={y}  — 点击移除")
            btn.clicked.connect(lambda _=False, t=typ: self._remove_unit(t))
        else:
            btn.setText("＋")
            btn.setToolTip(f"空槽 x={x} y={y}（{tpl.name}）")
            btn.clicked.connect(lambda _=False, sx=x, sy=y: self._place_unit(sx, sy))
        return btn

    def _place_unit(self, x, y):
        if self.current is None:
            return
        typ = self.picked_type
        if not typ:
            QMessageBox.information(self, "提示", "请先在兵种面板中选择一个兵种。")
            return
        # 从支援面板选的放 support，否则放 regiments
        info = self.sub_units.get(typ, {})
        is_support = bool(info.get("support"))
        if is_support:
            self.current.support = [(t, tx, ty) for t, tx, ty in self.current.support
                                    if not (tx == x and ty == 0)]
            self.current.support.append((typ, x, 0))
        else:
            self.current.regiments = [(t, tx, ty) for t, tx, ty in self.current.regiments
                                      if not (tx == x and ty == y)]
            self.current.regiments.append((typ, x, y))
        self.current.regiments.sort(key=lambda r: (r[2], r[1]))
        self.current.support.sort(key=lambda r: (r[2], r[1]))
        self.oob_file.mark_template_modified(self.current)
        self._rebuild_editor(self.current)

    def _remove_unit(self, typ):
        if self.current is None:
            return
        self.current.regiments = [(t, x, y) for t, x, y in self.current.regiments
                                  if t != typ]
        self.current.support = [(t, x, y) for t, x, y in self.current.support
                                if t != typ]
        self.oob_file.mark_template_modified(self.current)
        self._rebuild_editor(self.current)

    def _on_name_changed(self, text):
        if self.current is not None and text != self.current.name:
            self.current.name = text
            self.oob_file.mark_template_modified(self.current)

    def _on_locked_changed(self, checked):
        if self.current is not None:
            self.current.is_locked = checked
            self.oob_file.mark_template_modified(self.current)

    # ---------- 模板管理 ----------

    def _add_template(self):
        tpl = DivisionTemplate("New Division", is_locked=False,
                               regiments=[("infantry", 0, 0)])
        self.oob_file.add_template(tpl)
        self._refresh_template_list()
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _copy_template(self):
        if self.current is None:
            return
        import copy
        tpl = DivisionTemplate(
            self.current.name + " Copy", self.current.is_locked,
            list(self.current.regiments), list(self.current.support),
            list(self.current.extra_lines))
        self.oob_file.add_template(tpl)
        self._refresh_template_list()
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _delete_template(self):
        if self.current is None:
            return
        used = self.oob_file.placements_for_template(self.current.name)
        if used:
            QMessageBox.warning(
                self, "无法删除",
                f"模板「{self.current.name}」已被 {len(used)} 支部队引用，"
                f"请先在地图放置中移除这些部队。")
            return
        self.oob_file.remove_template(self.current.name)
        self.current = None
        self._refresh_template_list()
        self._clear_grid()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    # ---------- 地图 ----------

    def _open_map(self):
        from oob_map_editor import OobMapEditor
        from oob_loader import find_oob_country
        tag = find_oob_country(self.mod_path, self.oob_file.file_path)
        dlg = OobMapEditor(self.oob_file, self.sub_units, self.gfx_map,
                           self.mod_path, self.hoi4_path,
                           country_tag=tag, parent=self)
        dlg.map_saved.connect(self._refresh_template_list)
        dlg.show()

    # ---------- 保存 ----------

    def _save(self):
        try:
            self.oob_file.save()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", f"已保存到:\n{self.oob_file.file_path}")
        self.tree_saved.emit()
        self._refresh_template_list()
