"""师编制编辑器 — 仿游戏内师设计器（Division Designer）

顶部标题栏（模板下拉切换/新建/复制/删除/锁定 + 保存/地图放置），
中部左=编制网格（固定 5x5 团/营网格），右=数据面板（基础数据/战斗数据/
装备花费/地形适应性，基础值估算）：
  - 每列 = 一个团，每格 = 一个营；团内只能放置同一大类型兵种
  - 团级支援连：横向一排，与团（列）对齐；团内营数 >= 3 后解锁（每团最多 1 个）
  - 普通支援连：右侧纵向一列，与营（行）对齐；无放置条件
  - 兵种选择：点击 ＋ 弹出分类面板（步兵部队/机动部队/装甲部队/支援部队…），
    分类取自兵种文件中的 group 字段；先选大类型，再点具体兵种放入
  - 兵种名：优先显示本地化（翻译文件）中文名，无中文时回退兵种 key（英文）
  - 数据面板数值 = oob_loader.division_stats 基础值估算（未含科技/将领修正）

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
    QGridLayout, QScrollArea, QWidget, QFrame, QSplitter, QGroupBox,
    QComboBox, QMenu
)

from oob_loader import DivisionTemplate

SLOT_SIZE = 84
SLOT_ICON = 44
GRID_COLS = 5              # 团（列）数量
GRID_ROWS = 5              # 营（行）数量
SUPPORT_UNLOCK = 3         # 团内营数达到该值后解锁团级支援连
MAX_LINE_BATTALIONS = 25   # 全师战斗营上限（游戏上限）
PANEL_WIDTH = 330          # 右侧数据面板固定宽度

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

# 地形徽章（键 → 中文名）；顺序与游戏内地形徽章矩阵一致
TERRAIN_LABELS = (
    ("desert", "沙漠"), ("forest", "森林"), ("hills", "丘陵"),
    ("jungle", "丛林"), ("marsh", "沼泽"), ("mountain", "山地"),
    ("plains", "平原"), ("urban", "城市"),
)

# 空槽 ＋ 按钮样式（亮色主题适配：主色虚线框 + 主色加号）
_PLUS_STYLE = (
    "QPushButton { border: 1.5px dashed #1f4f7e; background: #ffffff;"
    " color: #1f4f7e; font-size: 22px; font-weight: bold; }"
    "QPushButton:hover { background: rgba(31, 79, 126, 0.10); }")
_OCCUPIED_STYLE = (
    "QPushButton { border: 1px solid #2f7d57; background: #eef6f0;"
    " color: #2f7d57; }"
    "QPushButton:hover { background: #e0efe6; }")
_LOCKED_STYLE = (
    "QPushButton { border: 1px dashed #95a0ab; background: #f4f6f8;"
    " color: #95a0ab; font-size: 18px; }")

# 数据面板样式（亮色主题：标签次级灰、数值主色粗体、分组框圆角）
_STAT_LABEL_STYLE = "color:#5d6b7a; font-size:12px;"
_STAT_VALUE_STYLE = "color:#1f4f7e; font-weight:bold; font-size:12px;"
_STAT_GROUP_STYLE = (
    "QGroupBox { border: 1px solid rgba(22,35,51,0.18); border-radius: 8px;"
    " margin-top: 10px; font-weight: bold; }"
    "QGroupBox::title { subcontrol-origin: margin; left: 10px;"
    " padding: 0 4px; color:#425062; }")
_TERRAIN_CARD_STYLE = (
    "QLabel { border: 1px solid rgba(22,35,51,0.18); border-radius: 6px;"
    " background: #ffffff; padding: 4px; }")


def group_label(g):
    """group 字段 → 中文大类名（未收录的 group 原样显示）。"""
    return GROUP_LABELS.get(g, g or "其他部队")


def _fmt_num(v, nd=1):
    """数值格式化：None → "—"；整数去小数；否则保留 nd 位。"""
    if v is None:
        return "—"
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%." + str(nd) + "f") % f


def _fmt_pct(v, nd=1):
    """比例格式化（0.2 → "+20%"）：None → "—"。"""
    if v is None:
        return "—"
    p = v * 100.0
    sign = "+" if p > 0 else ""
    if abs(p - round(p)) < 1e-9:
        return "%s%d%%" % (sign, int(round(p)))
    return "%s%.*f%%" % (sign, nd, p)


def equip_cn_name(key):
    """装备中文名（本地化），无中文回退装备键。"""
    try:
        from gui_translator import get_translator
        cn = get_translator().translate_value(key)
        if cn and cn != key:
            return cn
    except Exception:
        pass
    return key


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
        hint.setStyleSheet("color:#5d6b7a; padding:2px;")
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
        # 数据面板字段名 → QLabel（_update_stats 更新）
        self._stat_labels = {}

        self.setWindowTitle("师编制编辑器")
        self.resize(1280, 760)
        self._build_ui()
        self._refresh_combo()
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)
            if self.current is None:
                # addItem 在 blockSignals 期间已自动选中第 0 项，
                # 索引未变化 → 信号不触发，手动补一次
                self._on_combo_changed(0)

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 顶部标题栏：标题 + 模板下拉 + 改名 + 锁定 + 模板管理 + 全局按钮
        bar = QHBoxLayout()
        title = QLabel("师编制编辑器")
        title.setStyleSheet("font-size:15px; font-weight:bold; color:#162333;")
        bar.addWidget(title)
        bar.addSpacing(8)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(240)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        bar.addWidget(self.combo)

        self.name_edit = QLineEdit()
        self.name_edit.setFixedWidth(220)
        self.name_edit.setPlaceholderText("模板名（可编辑）")
        self.name_edit.textChanged.connect(self._on_name_changed)
        bar.addWidget(self.name_edit)

        self.locked_check = QCheckBox("🔒 is_locked")
        self.locked_check.toggled.connect(self._on_locked_changed)
        bar.addWidget(self.locked_check)

        self.add_btn = QPushButton("＋ 新建")
        self.add_btn.clicked.connect(self._add_template)
        self.copy_btn = QPushButton("⧉ 复制")
        self.copy_btn.clicked.connect(self._copy_template)
        self.del_btn = QPushButton("🗑 删除")
        self.del_btn.clicked.connect(self._delete_template)
        self.tpl_save_btn = QPushButton("💾 存为模板")
        self.tpl_save_btn.clicked.connect(self._save_as_template)
        self.tpl_load_btn = QPushButton("📥 模板新建")
        self.tpl_load_btn.clicked.connect(self._new_from_template)
        bar.addWidget(self.add_btn)
        bar.addWidget(self.copy_btn)
        bar.addWidget(self.del_btn)
        bar.addWidget(self.tpl_save_btn)
        bar.addWidget(self.tpl_load_btn)

        bar.addStretch(1)

        # 顶部：地编入口 + 其他设计器（舰艇/飞机/坦克）
        self.place_btn = QPushButton("🗺 地编（地图放置）…")
        self.place_btn.setToolTip("打开地图放置窗口，选择当前编制点击地块放置部队")
        self.place_btn.clicked.connect(self._open_map)
        bar.addWidget(self.place_btn)

        self.design_btn = QToolButton()
        self.design_btn.setText("🛠 设计器 ▾")
        self.design_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        design_menu = QMenu(self)
        act_ship = design_menu.addAction("🚢 舰艇设计…")
        act_ship.triggered.connect(self._open_ship_designer)
        act_plane = design_menu.addAction("✈ 飞机设计…")
        act_plane.triggered.connect(self._open_plane_designer)
        act_tank = design_menu.addAction("🛡 坦克设计…")
        act_tank.triggered.connect(self._open_tank_designer)
        self.design_btn.setMenu(design_menu)
        bar.addWidget(self.design_btn)

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)
        bar.addWidget(self.save_btn)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：编制网格区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.grid_host)
        split.addWidget(scroll)

        hint = QLabel(
            "提示: 点击 ＋ 选择兵种（按大类型分类）；每列 = 一个团，每格 = 一个营，"
            "团内只能放置同一大类型兵种；团内营数达到 3 后可加入 1 个团级支援连"
            "（下方横向与团对齐）；普通支援连（右侧纵向与营对齐）随时可加入。"
            "点击已占格子可移除该兵种。右侧数值为基础值估算（未含科技修正）。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5d6b7a")
        # 提示 + 网格容器：网格内容在 _grid_holder 内，_clear_grid 只清容器
        self.grid_layout.addWidget(hint)
        self._grid_holder = QWidget()
        self._grid_holder_layout = QVBoxLayout(self._grid_holder)
        self._grid_holder_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.addWidget(self._grid_holder)
        self.grid_layout.addStretch(1)

        # 右侧：数据面板（固定宽度）
        panel = QWidget()
        panel.setFixedWidth(PANEL_WIDTH)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_scroll = QScrollArea()
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setFrameShape(QFrame.Shape.NoFrame)
        panel_host = QWidget()
        panel_host_layout = QVBoxLayout(panel_host)
        panel_host_layout.setContentsMargins(4, 0, 4, 0)

        # --- 基础数据 ---
        self._build_stat_group(panel_host_layout, "基础数据", (
            ("width", "战斗宽度"), ("manpower", "人力"), ("org", "组织度"),
            ("speed", "最大速度"), ("hp", "HP"), ("org_regain", "恢复速度"),
            ("recon", "侦察"), ("suppression", "镇压能力"),
            ("weight", "重量"), ("supply", "补给使用"),
            ("fuel", "燃油使用"), ("training", "训练时间"),
        ))
        # --- 战斗数据 ---
        self._build_stat_group(panel_host_layout, "战斗数据", (
            ("soft", "对人员杀伤"), ("hard", "对装甲杀伤"),
            ("air", "对空攻击"), ("defense", "防御"),
            ("breakthrough", "突破"), ("armor", "装甲厚度"),
            ("piercing", "穿甲深度"), ("initiative", "主动性"),
        ))
        # --- 装备花费 ---
        self._build_equip_box(panel_host_layout)
        # --- 地形适应性 ---
        self._build_terrain_group(panel_host_layout)

        panel_host_layout.addStretch(1)
        panel_scroll.setWidget(panel_host)
        panel_layout.addWidget(panel_scroll)
        split.addWidget(panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        root.addWidget(split, 1)

        # 底部操作栏：重置 + 装备需求汇总
        bottom = QHBoxLayout()
        self.reset_btn = QPushButton("⟲ 重置")
        self.reset_btn.setToolTip("放弃当前模板未保存的修改，从文件重新载入")
        self.reset_btn.clicked.connect(self._reset_current)
        bottom.addWidget(self.reset_btn)
        bottom.addStretch(1)
        self.equip_summary = QLabel("装备需求: —")
        self.equip_summary.setStyleSheet("color:#5d6b7a;")
        bottom.addWidget(self.equip_summary)
        root.addLayout(bottom)

    def _build_stat_group(self, host_layout, title, fields):
        """数据面板分组框（两列：标签 | 数值右对齐）。"""
        box = QGroupBox(title)
        box.setStyleSheet(_STAT_GROUP_STYLE)
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 12, 10, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        for row, (key, label) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(_STAT_LABEL_STYLE)
            val = QLabel("—")
            val.setStyleSheet(_STAT_VALUE_STYLE)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            self._stat_labels[key] = val
        host_layout.addWidget(box)

    def _build_terrain_group(self, host_layout):
        """地形适应性徽章矩阵（2 列 × 4 行，显示平均移动修正）。"""
        box = QGroupBox("地形适应性")
        box.setStyleSheet(_STAT_GROUP_STYLE)
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 12, 10, 8)
        grid.setSpacing(6)
        self._terrain_labels = {}
        for i, (key, cn) in enumerate(TERRAIN_LABELS):
            card = QLabel("—")
            card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card.setStyleSheet(_TERRAIN_CARD_STYLE)
            card.setToolTip(f"{cn}（平均移动修正，基础值估算）")
            grid.addWidget(card, i // 2, i % 2)
            self._terrain_labels[key] = (card, cn)
        host_layout.addWidget(box)

    # ---------- 数据刷新 ----------

    def _refresh_combo(self):
        """重填模板下拉（保留当前选择）。"""
        cur = self.current.name if self.current is not None else None
        self.combo.blockSignals(True)
        self.combo.clear()
        for t in self.oob_file.templates:
            n = len(self.oob_file.placements_for_template(t.name))
            self.combo.addItem(f"{t.name}   ({n} 个部署)", t)
        if cur is not None:
            for i in range(self.combo.count()):
                t = self.combo.itemData(i)
                if t is not None and t.name == cur:
                    self.combo.setCurrentIndex(i)
                    break
        self.combo.blockSignals(False)

    # ---------- 编辑区 ----------

    def _clear_grid(self):
        """递归清空网格容器（避免重建时控件堆积；提示/拉伸保留）。"""
        DivisionEditor._clear_layout(self._grid_holder_layout)

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

    def _on_combo_changed(self, index):
        tpl = self.combo.itemData(index)
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

        self._grid_holder_layout.addLayout(grid)
        self._grid_holder_layout.addStretch(1)
        self._update_stats(tpl)

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
            # 同步下拉显示文本（不触发切换）
            self.combo.blockSignals(True)
            idx = self.combo.currentIndex()
            if idx >= 0:
                self.combo.setItemText(idx, f"{text}   "
                                           f"({len(self.oob_file.placements_for_template(text))} 个部署)")
            self.combo.blockSignals(False)

    def _on_locked_changed(self, checked):
        if self.current is not None:
            self.current.is_locked = checked
            self.oob_file.mark_template_modified(self.current)

    # ---------- 数据面板（基础值估算） ----------

    def _equip_stats(self):
        """装备攻击属性（惰性加载 + 模块级缓存）。"""
        try:
            from oob_loader import load_equipment_stats
            return load_equipment_stats(self.mod_path, self.hoi4_path)
        except Exception:
            return {}

    def _update_stats(self, tpl):
        """按当前模板刷新右侧数据面板 + 底部装备汇总。"""
        try:
            from oob_loader import division_stats
            st = division_stats(tpl, self.sub_units, self._equip_stats())
        except Exception:
            return
        fmt = {
            "width": lambda v: _fmt_num(v, 1),
            "manpower": lambda v: _fmt_num(v, 0),
            "org": lambda v: _fmt_num(v, 1),
            "speed": lambda v: ("—" if v is None else _fmt_num(v, 1) + " km/h"),
            "hp": lambda v: _fmt_num(v, 1),
            "org_regain": lambda v: _fmt_num(v, 2),
            "recon": lambda v: _fmt_num(v, 1),
            "suppression": lambda v: _fmt_num(v, 1),
            "weight": lambda v: _fmt_num(v, 1),
            "supply": lambda v: _fmt_num(v, 2),
            "fuel": lambda v: _fmt_num(v, 2),
            "training": lambda v: _fmt_num(v, 0),
            "soft": lambda v: _fmt_num(v, 1),
            "hard": lambda v: _fmt_num(v, 1),
            "air": lambda v: _fmt_num(v, 1),
            "defense": lambda v: _fmt_num(v, 1),
            "breakthrough": lambda v: _fmt_num(v, 1),
            "armor": lambda v: _fmt_num(v, 1),
            "piercing": lambda v: _fmt_num(v, 1),
            "initiative": lambda v: _fmt_num(v, 2),
            "reliability": lambda v: _fmt_pct(v, 1),
        }
        for key, val in self._stat_labels.items():
            val.setText(fmt.get(key, _fmt_num)(st.get(key)))
        # 地形徽章：平均移动修正（%）
        terrain = st.get("terrain") or {}
        for key, (card, cn) in self._terrain_labels.items():
            mv = terrain.get(key)
            card.setText(f"{cn}\n{_fmt_pct(mv, 0)}")
        # 装备花费：按数量降序，最多 8 行
        eq = st.get("equipment") or {}
        lines = []
        if eq:
            rows = sorted(eq.items(), key=lambda kv: kv[1], reverse=True)
            for k, cnt in rows[:8]:
                lines.append(f"{equip_cn_name(k)}  {_fmt_num(cnt, 0)}")
            if len(rows) > 8:
                lines.append(f"…等 {len(rows)} 种装备")
        self._equip_text.setText("\n".join(lines) if lines else "（无装备需求）")
        n_total = int(sum(eq.values()))
        self.equip_summary.setText(
            f"装备需求: {len(eq)} 种 · 合计 {n_total} 件")

    def _build_equip_box(self, host_layout):
        """装备花费分组框（多行文本，_update_stats 刷新）。"""
        box = QGroupBox("装备花费")
        box.setStyleSheet(_STAT_GROUP_STYLE)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 12, 10, 8)
        self._equip_text = QLabel("—")
        self._equip_text.setStyleSheet(_STAT_VALUE_STYLE)
        self._equip_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self._equip_text.setWordWrap(True)
        lay.addWidget(self._equip_text)
        host_layout.addWidget(box)
        self._equip_box = box

    # ---------- 设计模板（存为模板 / 从模板新建） ----------

    def _save_as_template(self):
        if self.current is None:
            QMessageBox.information(self, "提示", "没有可保存的编制。")
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "存为模板", "模板名:", text=self.current.name)
        if not ok or not name.strip():
            return
        tpl = DivisionTemplate(
            name.strip(), self.current.is_locked,
            list(self.current.regiments), list(self.current.support),
            list(self.current.extra_lines))
        from design_template import save_design_template
        path = save_design_template("division", name.strip(), tpl.to_pdx())
        if path:
            QMessageBox.information(self, "已保存模板",
                                    f"模板已保存到:\n{path}")
        else:
            QMessageBox.critical(self, "保存失败", "模板保存失败。")

    def _new_from_template(self):
        if self.oob_file is None:
            return
        from PyQt6.QtWidgets import QInputDialog
        from design_template import list_design_templates, load_design_template
        from oob_loader import parse_division_templates
        tpls = list_design_templates("division")
        if not tpls:
            QMessageBox.information(self, "模板", "暂无编制模板。")
            return
        names = [t["name"] for t in tpls]
        name, ok = QInputDialog.getItem(self, "从模板新建", "选择模板:",
                                        names, 0, False)
        if not ok:
            return
        content = load_design_template("division", name)
        if not content:
            return
        parsed = parse_division_templates(content)
        if not parsed:
            QMessageBox.warning(self, "模板无效",
                                "模板内容不是有效的编制模板。")
            return
        src = parsed[0]
        new_name = src.name
        while any(t.name == new_name for t in self.oob_file.templates):
            new_name = src.name + " Copy"
            src.name = new_name
        tpl = DivisionTemplate(
            new_name, src.is_locked,
            list(src.regiments), list(src.support),
            list(src.extra_lines))
        self.oob_file.add_template(tpl)
        self._refresh_combo()
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(self.combo.count() - 1)

    # ---------- 模板管理 ----------

    def _add_template(self):
        tpl = DivisionTemplate("New Division", is_locked=False,
                               regiments=[("infantry", 0, 0)])
        self.oob_file.add_template(tpl)
        self._refresh_combo()
        self.combo.setCurrentIndex(self.combo.count() - 1)

    def _copy_template(self):
        if self.current is None:
            return
        import copy
        tpl = DivisionTemplate(
            self.current.name + " Copy", self.current.is_locked,
            list(self.current.regiments), list(self.current.support),
            list(self.current.extra_lines))
        self.oob_file.add_template(tpl)
        self._refresh_combo()
        self.combo.setCurrentIndex(self.combo.count() - 1)

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
        self._refresh_combo()
        self._clear_grid()
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)

    def _reset_current(self):
        """丢弃当前模板未保存的修改，从文件原始内容重新载入。"""
        if self.current is None:
            return
        name = self.current.name
        try:
            from oob_loader import parse_division_templates
            tpl = next((t for t in parse_division_templates(self.oob_file.content)
                        if t.name == name), None)
        except Exception:
            return
        if tpl is None:
            return
        for i, t in enumerate(self.oob_file.templates):
            if t.name == name:
                self.oob_file.templates[i] = tpl
                break
        self.current = tpl
        self._refresh_combo()
        self._rebuild_editor(tpl)

    # ---------- 地图 ----------

    def _open_map(self):
        from oob_map_editor import OobMapEditor
        from oob_loader import find_oob_country
        tag = find_oob_country(self.mod_path, self.oob_file.file_path)
        dlg = OobMapEditor(self.oob_file, self.sub_units, self.gfx_map,
                           self.mod_path, self.hoi4_path,
                           country_tag=tag, parent=self)
        dlg.map_saved.connect(self._refresh_combo)
        dlg.show()

    def _open_ship_designer(self):
        from ship_design_dialog import ShipDesignDialog
        dlg = ShipDesignDialog(self.mod_path, self.hoi4_path, parent=self)
        dlg.show()

    def _open_plane_designer(self):
        from plane_design_dialog import PlaneDesignDialog
        dlg = PlaneDesignDialog(self.mod_path, self.hoi4_path, parent=self)
        dlg.show()

    def _open_tank_designer(self):
        from tank_design_dialog import TankDesignDialog
        dlg = TankDesignDialog(self.mod_path, self.hoi4_path, parent=self)
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
        self._refresh_combo()
