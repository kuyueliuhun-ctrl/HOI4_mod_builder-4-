"""师编制编辑器 — 仿游戏内师设计器（Division Designer）

左侧模板列表（新建/复制/删除），右侧编辑区（固定 5x5 团/营网格）：
  - 每列 = 一个团，每格 = 一个营；团内只能放置同一大类型兵种
  - 团级支援连：横向一排，与团（列）对齐；团内营数 >= 3 后解锁（每团最多 1 个）
  - 普通支援连：右侧纵向一列，与营（行）对齐；无放置条件
  - 兵种选择：点击 ＋ 弹出分类面板（步兵部队/机动部队/装甲部队/支援部队…），
    分类取自兵种文件中的 group 字段；先选大类型，再点具体兵种放入
  - 兵种名：优先显示本地化（翻译文件）中文名，无中文时回退兵种 key（英文）

数据编码（support 块内）：
  普通支援连  ->  (type, x=0, y=行)   （与 mod 现有文件写法一致）
  团级支援连  ->  (type, x=团列, y=5)
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QToolButton, QLineEdit, QCheckBox, QLabel, QMessageBox,
    QGridLayout, QScrollArea, QWidget, QFrame, QSplitter, QGroupBox
)

from oob_loader import DivisionTemplate

SLOT_SIZE = 84
SLOT_ICON = 44
GRID_COLS = 5              # 团（列）数量
GRID_ROWS = 5              # 营（行）数量
SUPPORT_UNLOCK = 3         # 团内营数达到该值后解锁团级支援连
MAX_LINE_BATTALIONS = 25   # 全师战斗营上限（游戏上限）

# 大类型（兵种文件 group 字段）→ 中文名
GROUP_LABELS = {
    "infantry": "步兵部队",
    "mobile": "机动部队",
    "armor": "装甲部队",
    "support": "支援部队",
    "combat_support": "炮兵部队",
    "mobile_combat_support": "炮兵部队",
    "armor_combat_support": "装甲炮兵部队",
}
_GROUP_ORDER = ("infantry", "mobile", "armor", "support",
                "combat_support", "mobile_combat_support", "armor_combat_support")

# 空槽 ＋ 按钮样式（亮色加号，便于分辨）
_PLUS_STYLE = (
    "QPushButton { border: 1px dashed #777; background: #2b2b30;"
    " color: #9fe870; font-size: 22px; font-weight: bold; }"
    "QPushButton:hover { background: #3a3a44; }")
_OCCUPIED_STYLE = (
    "QPushButton { border: 1px solid #7a8; background: #2f3a32;"
    " color: #e8f5e9; }"
    "QPushButton:hover { background: #3a463c; }")
_LOCKED_STYLE = (
    "QPushButton { border: 1px dashed #444; background: #242428;"
    " color: #666; font-size: 18px; }")


def group_label(g):
    """group 字段 → 中文大类名（未收录的 group 原样显示）。"""
    return GROUP_LABELS.get(g, g or "其他部队")


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


def unit_cn_name(typ):
    """兵种中文名（翻译文件/本地化缓存），无中文时回退兵种 key（英文）。"""
    try:
        from gui_translator import get_translator
        cn = get_translator().translate_value(typ)
        if cn and cn != typ:
            return cn
    except Exception:
        pass
    return typ


class UnitPickerDialog(QDialog):
    """点击 ＋ 弹出的兵种选择面板。

    先选大类型（步兵部队/机动部队/装甲部队/支援部队…），再点击具体兵种即可放入。
    mode="line"：战斗营选择（排除支援连兵种）；mode="support"：支援连选择。
    allowed_group：限制只能选择该大类型（同一团内只可放入同一大类型兵种）。
    """

    def __init__(self, sub_units, gfx_map=None, mod_path="", hoi4_path="",
                 mode="line", allowed_group=None, title="选择兵种", parent=None):
        super().__init__(parent)
        self.sub_units = sub_units or {}
        self.gfx_map = gfx_map or {}
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.mode = mode
        self.allowed_group = allowed_group
        self.picked = None          # 选中的兵种名
        self._types = []            # 当前大类型下的兵种列表

        self.setWindowTitle(title)
        self.resize(560, 430)
        self._build_ui()
        self._build_groups()

    def _unit_list(self):
        """按模式筛选兵种：line 排除支援连，support 只留支援连。"""
        if self.mode == "support":
            return {k: v for k, v in self.sub_units.items()
                    if v.get("support")}
        units = {k: v for k, v in self.sub_units.items()
                 if not v.get("support")}
        if self.allowed_group:
            units = {k: v for k, v in units.items()
                     if v.get("group") == self.allowed_group}
        return units

    def _build_ui(self):
        root = QVBoxLayout(self)
        if self.mode == "line" and self.allowed_group:
            hint = QLabel(f"该团已放置「{group_label(self.allowed_group)}」兵种，"
                          f"团内只能放置同一大类型兵种。")
        elif self.mode == "support":
            hint = QLabel(f"团级支援连需团内 {SUPPORT_UNLOCK} 个营；普通支援连随时可加入。")
        else:
            hint = QLabel("先选择大类型（步兵部队/机动部队/装甲部队/支援部队…），"
                          "再点击具体兵种放入。")
        hint.setStyleSheet("color:#999; padding:2px;")
        root.addWidget(hint)

        split = QHBoxLayout()
        # 左：大类型列表
        self.group_list = QListWidget()
        self.group_list.setFixedWidth(150)
        self.group_list.currentRowChanged.connect(self._on_group_changed)
        split.addWidget(self.group_list)
        # 右：兵种列表
        self.unit_list = QListWidget()
        self.unit_list.setIconSize(QSize(40, 40))
        self.unit_list.itemClicked.connect(self._on_unit_clicked)
        split.addWidget(self.unit_list, 1)
        root.addLayout(split, 1)

    def _build_groups(self):
        """按兵种文件中的 group 字段分组（无 group 的兵种不展示）。"""
        units = self._unit_list()
        by_group = {}
        for name, info in units.items():
            g = info.get("group") or ""
            if not g:
                continue
            by_group.setdefault(g, []).append(name)

        def sort_key(g):
            return (_GROUP_ORDER.index(g) if g in _GROUP_ORDER else 99, g)

        self._groups = sorted(by_group, key=sort_key)
        self.group_list.blockSignals(True)
        self.group_list.clear()
        for g in self._groups:
            item = QListWidgetItem(f"{group_label(g)} ({len(by_group[g])})")
            item.setData(Qt.ItemDataRole.UserRole, g)
            self.group_list.addItem(item)
        self.group_list.blockSignals(False)
        if self._groups:
            self.group_list.setCurrentRow(0)
        else:
            empty = QListWidgetItem("（无可用兵种）")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.unit_list.addItem(empty)

    def _on_group_changed(self, row):
        if row < 0 or row >= len(self._groups):
            return
        g = self._groups[row]
        self._types = sorted(
            k for k, v in self._unit_list().items() if (v.get("group") or "") == g)
        self.unit_list.blockSignals(True)
        self.unit_list.clear()
        for name in self._types:
            info = self.sub_units.get(name, {})
            cn = unit_cn_name(name)
            label = f"{cn}  ({info.get('abbreviation') or ''})"
            item = QListWidgetItem(label)
            item.setToolTip(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.unit_list.addItem(item)
        self.unit_list.blockSignals(False)

    def _on_unit_clicked(self, item):
        self.picked = item.data(Qt.ItemDataRole.UserRole)
        self.accept()


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
        # 当前编辑中的模板
        self.current = None

        self.setWindowTitle("师编制编辑器")
        self.resize(1120, 660)
        self._build_ui()
        self._refresh_template_list()
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

        # 右侧：编辑区
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

        hint = QLabel(
            "提示: 点击 ＋ 选择兵种（按大类型分类）；每列 = 一个团，每格 = 一个营，"
            "团内只能放置同一大类型兵种；团内营数达到 3 后可加入 1 个团级支援连"
            "（下方横向与团对齐）；普通支援连（右侧纵向与营对齐）随时可加入。"
            "点击已占格子可移除该兵种。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#888")
        right_layout.addWidget(hint)

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

    # ---------- 编辑区 ----------

    def _clear_grid(self):
        """递归清空网格（含嵌套布局与全部子控件），避免重建时控件堆积。"""
        DivisionEditor._clear_layout(self.grid_layout)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
                continue
            child = item.layout()
            if child is not None:
                DivisionEditor._clear_layout(child)
                child.deleteLater()

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
        self._compact(tpl)

        grid = QGridLayout()
        grid.setSpacing(6)

        # 行0：团头（不显示营数）；列5：普通支援连标题
        for c in range(GRID_COLS):
            hdr = QLabel(f"团{c + 1}")
            hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr.setToolTip("每个团为一列；团内只能放置同一大类型兵种。")
            grid.addWidget(hdr, 0, c)
        sup_hdr = QLabel("普通\n支援连")
        sup_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sup_hdr.setToolTip("普通支援连（纵向与营对齐），随时可加入，无放置条件。")
        grid.addWidget(sup_hdr, 0, GRID_COLS)

        # 行1..：战斗营（每列 = 团，每格 = 营）；列5：普通支援连（纵向，与营对齐）
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                grid.addWidget(self._make_slot(tpl, "battalion", x, y), y + 1, x)
            grid.addWidget(self._make_slot(tpl, "normal", 0, y), y + 1, GRID_COLS)

        # 下方：团级支援连（横向，与团对齐）
        for c in range(GRID_COLS):
            lbl = QLabel(f"团支{c + 1}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setToolTip(f"团 {c + 1} 的团级支援连位（需该团有 {SUPPORT_UNLOCK} 个营）")
            grid.addWidget(lbl, GRID_ROWS + 1, c)
            grid.addWidget(self._make_slot(tpl, "regimental", c, 0),
                           GRID_ROWS + 2, c)

        self.grid_layout.addLayout(grid)
        self.grid_layout.addStretch(1)

    def _make_slot(self, tpl, kind, x, y):
        """创建单个格子按钮。

        kind: "battalion" 战斗营 / "regimental" 团级支援连 / "normal" 普通支援连
        """
        if kind == "battalion":
            typ = next((t for t, tx, ty in tpl.regiments
                        if tx == x and ty == y), None)
        elif kind == "regimental":
            typ = next((t for t, tx, ty in tpl.support
                        if tx == x and ty == 5), None)
        else:
            typ = next((t for t, tx, ty in tpl.support
                        if tx == 0 and ty == y), None)

        btn = QToolButton()
        btn.setFixedSize(SLOT_SIZE, SLOT_SIZE)
        if typ:
            info = self.sub_units.get(typ, {})
            abbr = info.get("abbreviation") or typ.upper()
            cn = unit_cn_name(typ)
            icon = unit_icon(typ, self.sub_units, self.gfx_map,
                             self.mod_path, self.hoi4_path)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setText(cn)
            btn.setIconSize(QSize(SLOT_ICON, SLOT_ICON))
            if icon is not None:
                btn.setIcon(icon)
            btn.setStyleSheet(_OCCUPIED_STYLE)
            if kind == "battalion":
                g = info.get("group", "")
                btn.setToolTip(f"{cn} ({abbr}) 团 {x + 1} 第 {y + 1} 营"
                               f" — {group_label(g)} — 点击移除")
                btn.clicked.connect(lambda _=False, sx=x, sy=y:
                                    self._remove_battalion(sx, sy))
            elif kind == "regimental":
                btn.setToolTip(f"团 {x + 1} 的团级支援连: {cn} ({abbr}) — 点击移除")
                btn.clicked.connect(lambda _=False, sx=x:
                                    self._remove_support("regimental", sx))
            else:
                btn.setToolTip(f"第 {y + 1} 排普通支援连: {cn} ({abbr}) — 点击移除")
                btn.clicked.connect(lambda _=False, sy=y:
                                    self._remove_support("normal", sy))
            return btn

        # 空槽
        if kind == "regimental":
            n = self._column_height(tpl, x)
            if n < SUPPORT_UNLOCK:
                btn.setText("🔒")
                btn.setEnabled(False)
                btn.setStyleSheet(_LOCKED_STYLE)
                btn.setToolTip(f"团 {x + 1} 需有 {SUPPORT_UNLOCK} 个营才能加入"
                               f"团级支援连（当前 {n} 营）")
                return btn
            btn.setText("＋")
            btn.setStyleSheet(_PLUS_STYLE)
            btn.setToolTip(f"为团 {x + 1} 添加团级支援连（点击选择支援兵种）")
            btn.clicked.connect(lambda _=False, sx=x:
                                self._open_support_picker("regimental", sx))
            return btn

        if kind == "normal":
            btn.setText("＋")
            btn.setStyleSheet(_PLUS_STYLE)
            btn.setToolTip(f"第 {y + 1} 排添加普通支援连（点击选择支援兵种）")
            btn.clicked.connect(lambda _=False, sy=y:
                                self._open_support_picker("normal", sy))
            return btn

        g = self._column_group(tpl, x)
        btn.setText("＋")
        btn.setStyleSheet(_PLUS_STYLE)
        if g:
            btn.setToolTip(f"团 {x + 1} 第 {y + 1} 营（空）— 团内为「{group_label(g)}」，"
                           f"只能添加同一大类型兵种")
        else:
            btn.setToolTip(f"团 {x + 1} 第 {y + 1} 营（空）— 点击选择兵种")
        btn.clicked.connect(lambda _=False, sx=x, sy=y: self._open_line_picker(sx, sy))
        return btn

    # ---------- 放置 / 移除 ----------

    def _column_height(self, tpl, x):
        return sum(1 for _t, tx, _y in tpl.regiments if tx == x)

    def _column_group(self, tpl, x):
        """团（列）内已有兵种的大类型；空团返回 ""。"""
        for t, tx, _y in tpl.regiments:
            if tx == x:
                g = self.sub_units.get(t, {}).get("group", "")
                if g:
                    return g
        return ""

    def _open_line_picker(self, x, y):
        if self.current is None:
            return
        g = self._column_group(self.current, x)
        dlg = UnitPickerDialog(self.sub_units, self.gfx_map, self.mod_path,
                               self.hoi4_path, mode="line",
                               allowed_group=g or None,
                               title=f"选择兵种 — 团 {x + 1} 第 {y + 1} 营",
                               parent=self)
        if dlg.exec() and dlg.picked:
            self._place_battalion(x, y, dlg.picked)

    def _open_support_picker(self, kind, pos):
        if self.current is None:
            return
        if kind == "regimental":
            title = f"选择团级支援连 — 团 {pos + 1}"
        else:
            title = f"选择普通支援连 — 第 {pos + 1} 排"
        dlg = UnitPickerDialog(self.sub_units, self.gfx_map, self.mod_path,
                               self.hoi4_path, mode="support",
                               title=title, parent=self)
        if dlg.exec() and dlg.picked:
            self._place_support(kind, pos, dlg.picked)

    def _place_battalion(self, x, y, typ):
        tpl = self.current
        if tpl is None:
            return
        if any(tx == x and ty == y for _t, tx, ty in tpl.regiments):
            return
        info = self.sub_units.get(typ, {})
        g = info.get("group", "")
        if g:
            col_g = self._column_group(tpl, x)
            if col_g and col_g != g:
                QMessageBox.warning(
                    self, "不能放置",
                    f"团 {x + 1} 内已放置「{group_label(col_g)}」兵种，"
                    f"团内只能放置同一大类型兵种。")
                return
        if len(tpl.regiments) >= MAX_LINE_BATTALIONS:
            QMessageBox.warning(self, "不能放置",
                                f"全师战斗营已达上限 {MAX_LINE_BATTALIONS} 个。")
            return
        tpl.regiments.append((typ, x, y))
        self._compact(tpl)
        self.oob_file.mark_template_modified(tpl)
        self._rebuild_editor(tpl)

    def _place_support(self, kind, pos, typ):
        """放置支援连。kind: "regimental"（与团对齐，需3营）/"normal"（与营对齐，无限制）。"""
        tpl = self.current
        if tpl is None:
            return
        if kind == "regimental":
            x, y = pos, 5
            if any(tx == x and ty == y for _t, tx, ty in tpl.support):
                QMessageBox.information(self, "提示",
                                        f"团 {x + 1} 已有一个团级支援连。")
                return
            n = self._column_height(tpl, x)
            if n < SUPPORT_UNLOCK:
                QMessageBox.warning(
                    self, "不能放置",
                    f"团 {x + 1} 需有 {SUPPORT_UNLOCK} 个营才能加入团级支援连（当前 {n} 营）。")
                return
        else:
            x, y = 0, pos
            if any(tx == x and ty == y for _t, tx, ty in tpl.support):
                QMessageBox.information(self, "提示",
                                        f"第 {y + 1} 排已有一个普通支援连。")
                return
        tpl.support = [(t, tx, ty) for t, tx, ty in tpl.support
                       if not (tx == x and ty == y)]
        tpl.support.append((typ, x, y))
        self.oob_file.mark_template_modified(tpl)
        self._rebuild_editor(tpl)

    def _remove_battalion(self, x, y):
        tpl = self.current
        if tpl is None:
            return
        tpl.regiments = [(t, tx, ty) for t, tx, ty in tpl.regiments
                         if not (tx == x and ty == y)]
        self._compact(tpl)
        # 团内营数不足 → 该团的团级支援连一并移除（普通支援连不受影响）
        if self._column_height(tpl, x) < SUPPORT_UNLOCK:
            tpl.support = [(t, tx, ty) for t, tx, ty in tpl.support
                           if not (tx == x and ty == 5)]
        self.oob_file.mark_template_modified(tpl)
        self._rebuild_editor(tpl)

    def _remove_support(self, kind, pos):
        tpl = self.current
        if tpl is None:
            return
        if kind == "regimental":
            x, y = pos, 5
        else:
            x, y = 0, pos
        tpl.support = [(t, tx, ty) for t, tx, ty in tpl.support
                       if not (tx == x and ty == y)]
        self.oob_file.mark_template_modified(tpl)
        self._rebuild_editor(tpl)

    def _compact(self, tpl):
        """每列（团）营从第 0 行起紧凑排列（最多 GRID_ROWS 行）。

        支援连按位规范化：普通支援连 (x=0, y=行)，团级支援连 (x=团列, y=5)。
        仅整理内存数据，不标记 modified（未编辑的模板仍按原样写回）。
        """
        by_col = {}
        for t, x, y in tpl.regiments:
            by_col.setdefault(x, []).append((t, x, y))
        out = []
        for x in sorted(by_col):
            items = sorted(by_col[x], key=lambda r: r[2])
            for i, (t, _tx, _ty) in enumerate(items[:GRID_ROWS]):
                out.append((t, x, i))
        tpl.regiments = out
        sup = {}
        for t, x, y in tpl.support:
            if x == 0 and y < 5:
                key = (0, y)          # 普通支援连（与营行对齐）
            else:
                key = (x, 5)          # 团级支援连（与团列对齐）
            sup.setdefault(key, (t, key[0], key[1]))
        tpl.support = list(sup.values())

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
