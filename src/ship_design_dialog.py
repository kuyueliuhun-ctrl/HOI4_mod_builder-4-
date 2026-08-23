"""舰艇设计器（Ship Designer）— 仿游戏内舰艇设计界面（亮色主题）

顶部标题栏（国家下拉/设计下拉/改名/新建/复制/删除 + 保存），
中部左=船体信息与模块槽位网格（点击槽位选模块），右=数据面板
（基础数据/战斗数据/其他数据 + 制海权徽章），底部操作栏（重置+花费）。

数据流：ship_design.load_ship_hulls/modules/variants 解析，
ship_design_stats 属性估算；保存用 apply/insert/remove/rename_variant
块级写回 history/countries 文件（原子写）。
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QToolButton, QLineEdit, QLabel, QMessageBox,
    QGridLayout, QScrollArea, QWidget, QFrame, QSplitter, QGroupBox,
    QComboBox, QDialogButtonBox, QCheckBox,
)

from ship_design import (
    SLOT_LABELS, CATEGORY_LABELS, HULL_TYPE_LABELS,
    load_ship_hulls, load_ship_modules, load_ship_variants,
    ship_design_stats, hull_cn_name, ship_cn_name,
    apply_variant_upgrades, apply_variant_modules,
    apply_variant_advanced,
    insert_variant, remove_variant, rename_variant,
    parse_equipment_variants, _VARIANTS_CACHE,
)

from designer_base import VariantDesignerBase

PANEL_WIDTH = 330
SHIP_SLOT_COLS = 6   # 舰艇槽位网格列数（上6下6 布局）

_STAT_LABEL_STYLE = "color:#5d6b7a; font-size:12px;"
_STAT_VALUE_STYLE = "color:#1f4f7e; font-weight:bold; font-size:12px;"
_STAT_GROUP_STYLE = (
    "QGroupBox { border: 1px solid rgba(22,35,51,0.18); border-radius: 8px;"
    " margin-top: 10px; font-weight: bold; }"
    "QGroupBox::title { subcontrol-origin: margin; left: 10px;"
    " padding: 0 4px; color:#425062; }")
_SLOT_OCCUPIED = (
    "QToolButton { border: 1px solid #2f7d57; background: #eef6f0;"
    " color: #2f7d57; font-size: 12px; }"
    "QToolButton:hover { background: #e0efe6; }")
_SLOT_EMPTY = (
    "QToolButton { border: 1.5px dashed #1f4f7e; background: #ffffff;"
    " color: #1f4f7e; font-size: 18px; font-weight: bold; }"
    "QToolButton:hover { background: rgba(31, 79, 126, 0.10); }")
_SLOT_LOCKED = (
    "QToolButton { border: 1px dashed #95a0ab; background: #f4f6f8;"
    " color: #95a0ab; font-size: 14px; }")
_SLOT_REQUIRED_EMPTY = (
    "QToolButton { border: 1.5px dashed #b7791f; background: #fff8ee;"
    " color: #b7791f; font-size: 12px; font-weight: bold; }"
    "QToolButton:hover { background: rgba(183, 121, 31, 0.10); }")


def _fmt(v, nd=1):
    """数值格式化：None → "—"；整数去 .0；否则保留 nd 位。"""
    if v is None:
        return "—"
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%." + str(nd) + "f") % f


def _fmt_pct(v, nd=1):
    if v is None:
        return "—"
    p = v * 100.0
    if abs(p - round(p)) < 1e-9:
        return "%d%%" % int(round(p))
    return ("%." + str(nd) + "f%%") % p


from designer_common import ModulePickerDialog as _BaseModulePickerDialog
from designer_common import UpgradePointsCard, zone_summary_text
from designer_slots import load_upgrade_definitions


class ModulePickerDialog(_BaseModulePickerDialog):
    """点击槽位弹出的模块选择面板（公共实现见 designer_common）。"""

    def __init__(self, modules, allowed_categories, slot_label,
                 current_module=None, parent=None):
        super().__init__(
            modules, allowed_categories, slot_label,
            current_module=current_module,
            name_func=ship_cn_name,
            category_labels=CATEGORY_LABELS,
            parent=parent)


class ShipDesignDialog(VariantDesignerBase):
    """舰艇设计器主对话框。"""

    KIND = "ship"
    TITLE = "🚢 舰艇设计"
    HOST_LABEL = "未选择设计"
    SLOT_COLS = SHIP_SLOT_COLS
    HOSTS_LOADER = load_ship_hulls
    MODULES_LOADER = load_ship_modules
    VARIANTS_LOADER = load_ship_variants
    STATS_FN = ship_design_stats
    TYPE_CN = hull_cn_name
    NAME_CN = ship_cn_name
    APPLY_MODULES = apply_variant_modules
    APPLY_UPGRADES = apply_variant_upgrades
    APPLY_ADVANCED = apply_variant_advanced
    INSERT_FN = insert_variant
    REMOVE_FN = remove_variant
    RENAME_FN = rename_variant
    PARSE_VARIANTS_FN = parse_equipment_variants
    VARIANTS_CACHE = _VARIANTS_CACHE
    MODULE_PICKER_CLS = ModulePickerDialog
    SLOT_LABELS = SLOT_LABELS
    CATEGORY_LABELS = CATEGORY_LABELS

    def __init__(self, mod_path="", hoi4_path="", country_tag="", parent=None):
        super().__init__(mod_path, hoi4_path, country_tag, parent)

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 顶部标题栏
        bar = QHBoxLayout()
        title = QLabel("🚢 舰艇设计")
        title.setStyleSheet("font-size:15px; font-weight:bold; color:#162333;")
        bar.addWidget(title)
        bar.addSpacing(8)

        self.country_combo = QComboBox()
        self.country_combo.setMinimumWidth(150)
        self.country_combo.currentIndexChanged.connect(self._on_country_changed)
        bar.addWidget(QLabel("国家:"))
        bar.addWidget(self.country_combo)

        self.design_combo = QComboBox()
        self.design_combo.setMinimumWidth(260)
        self.design_combo.currentIndexChanged.connect(self._on_design_changed)
        bar.addWidget(QLabel("设计:"))
        bar.addWidget(self.design_combo)
        # 右键快速编辑本地化（当前设计名）
        from quick_loc_menu import install_combo_context_menu
        install_combo_context_menu(
            self.design_combo, self.mod_path, self.hoi4_path,
            key_provider=lambda: getattr(self, "current_name", "") or "",
            parent=self)

        self.name_edit = QLineEdit()
        self.name_edit.setFixedWidth(200)
        self.name_edit.setPlaceholderText("设计名（可编辑）")
        bar.addWidget(self.name_edit)

        self.add_btn = QPushButton("＋ 新建")
        self.add_btn.clicked.connect(self._add_design)
        self.copy_btn = QPushButton("⧉ 复制")
        self.copy_btn.clicked.connect(self._copy_design)
        self.del_btn = QPushButton("🗑 删除")
        self.del_btn.clicked.connect(self._delete_design)
        self.tpl_save_btn = QPushButton("💾 存为模板")
        self.tpl_save_btn.clicked.connect(self._save_as_template)
        self.tpl_load_btn = QPushButton("📥 模板新建")
        self.tpl_load_btn.clicked.connect(self._new_from_template)
        bar.addWidget(self.add_btn)
        bar.addWidget(self.copy_btn)
        bar.addWidget(self.del_btn)
        bar.addWidget(self.tpl_save_btn)
        bar.addWidget(self.tpl_load_btn)
        self.same_name_label = QLabel("")
        self.same_name_label.setStyleSheet("color:#5d6b7a;")
        bar.addWidget(self.same_name_label)
        self.sync_btn = QPushButton("🔄 同步到所有同款")
        self.sync_btn.setToolTip("将当前设计配置写回所有使用同名设计的国家")
        self.sync_btn.clicked.connect(self._sync_to_all_same_name)
        bar.addWidget(self.sync_btn)

        bar.addStretch(1)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)
        bar.addWidget(self.save_btn)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：船体信息 + 槽位网格
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.host_label = QLabel("未选择设计")
        self.host_label.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#425062; padding:2px;")
        self.host_label.setWordWrap(True)
        left_layout.addWidget(self.host_label)

        self.slot_scroll = QScrollArea()
        self.slot_scroll.setWidgetResizable(True)
        self.slot_host = QWidget()
        self.slot_grid = QGridLayout(self.slot_host)
        self.slot_grid.setSpacing(6)
        self.slot_scroll.setWidget(self.slot_host)
        left_layout.addWidget(self.slot_scroll, 1)

        self.save_validation_label = QLabel("")
        self.save_validation_label.setWordWrap(True)
        left_layout.addWidget(self.save_validation_label)

        hint = QLabel(
            "提示: 点击槽位选择模块（按船体允许的类别过滤）；已装模块再次点击"
            "可更换或移除。右侧数值为基础值估算（hull 基础 + 模块修正，"
            "未含科技/MIO 加成）。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5d6b7a")
        left_layout.addWidget(hint)

        self.upgrade_card = UpgradePointsCard()
        left_layout.addWidget(self.upgrade_card)

        self.advanced_box = QGroupBox("高级字段")
        self.advanced_box.setStyleSheet(_STAT_GROUP_STYLE)
        adv_lay = QGridLayout(self.advanced_box)
        adv_lay.setContentsMargins(10, 12, 10, 8)
        adv_lay.setHorizontalSpacing(8)
        adv_lay.setVerticalSpacing(4)

        adv_lay.addWidget(QLabel("设计团队"), 0, 0)
        self.design_team_combo = QComboBox()
        self.design_team_combo.setEditable(True)
        self.design_team_combo.setPlaceholderText("mio:<组织>（可自由输入）")
        self.design_team_combo.setMinimumWidth(180)
        adv_lay.addWidget(self.design_team_combo, 0, 1)

        adv_lay.addWidget(QLabel("父版本"), 1, 0)
        self.parent_version_edit = QLineEdit()
        self.parent_version_edit.setPlaceholderText("0")
        adv_lay.addWidget(self.parent_version_edit, 1, 1)

        adv_lay.addWidget(QLabel("已废弃"), 2, 0)
        self.obsolete_check = QCheckBox("obsolete = yes")
        adv_lay.addWidget(self.obsolete_check, 2, 1)

        adv_lay.addWidget(QLabel("图标"), 3, 0)
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("GFX_...（可输入图标键）")
        adv_lay.addWidget(self.icon_edit, 3, 1)

        left_layout.addWidget(self.advanced_box)
        split.addWidget(left)

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

        self._build_stat_group(panel_host_layout, "基础数据", (
            ("naval_speed", "最大速度"), ("naval_range", "最大航程"),
            ("max_organisation", "组织度"), ("max_strength", "HP"),
            ("reliability", "可靠性"), ("supply_consumption", "补给使用"),
            ("manpower", "人力"), ("fuel_consumption", "燃油使用"),
        ))
        self._build_stat_group(panel_host_layout, "战斗数据", (
            ("lg_attack", "轻型火炮攻击"),
            ("lg_armor_piercing", "轻型穿甲深度"),
            ("hg_attack", "重型火炮攻击"),
            ("hg_armor_piercing", "重型穿甲深度"),
            ("torpedo_attack", "鱼雷攻击"), ("sub_attack", "深水炸弹"),
            ("armor_value", "装甲厚度"), ("anti_air_attack", "防空"),
        ))
        self._build_stat_group(panel_host_layout, "其他数据", (
            ("surface_visibility", "水面可见度"),
            ("surface_detection", "对海探测"),
            ("sub_visibility", "水下可见度"),
            ("sub_detection", "对潜探测"),
            ("naval_mine_laying", "布雷"), ("naval_mine_sweeping", "扫雷"),
            ("naval_weather_penalty_factor", "天气惩罚"),
            ("hit_profile_mult", "被弹系数"),
        ))
        # 制海权徽章
        dom_box = QGroupBox("制海权")
        dom_box.setStyleSheet(_STAT_GROUP_STYLE)
        dom_lay = QVBoxLayout(dom_box)
        dom_lay.setContentsMargins(10, 12, 10, 8)
        self.dominance_label = QLabel("—")
        self.dominance_label.setStyleSheet(
            "font-size:20px; font-weight:bold; color:#b05b2d;")
        self.dominance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dom_lay.addWidget(self.dominance_label)
        panel_host_layout.addWidget(dom_box)

        panel_host_layout.addStretch(1)
        panel_scroll.setWidget(panel_host)
        panel_layout.addWidget(panel_scroll)
        split.addWidget(panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        root.addWidget(split, 1)

        # 底部操作栏
        bottom = QHBoxLayout()
        self.reset_btn = QPushButton("⟲ 重置")
        self.reset_btn.setToolTip("放弃当前设计未保存的修改，从文件重新载入")
        self.reset_btn.clicked.connect(self._reset)
        bottom.addWidget(self.reset_btn)
        bottom.addStretch(1)
        self.cost_label = QLabel("生产花费: —")
        self.cost_label.setStyleSheet("color:#5d6b7a;")
        bottom.addWidget(self.cost_label)
        root.addLayout(bottom)

    def _load_data(self):
        self.hosts = load_ship_hulls(self.mod_path, self.hoi4_path)
        self.modules = load_ship_modules(self.mod_path, self.hoi4_path)
        self.variants = load_ship_variants(self.mod_path, self.hoi4_path)

    def _rebuild_editor(self):
        while self.slot_grid.count():
            item = self.slot_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._slot_buttons = {}
        v = self.current_variant
        if v is None:
            self._clear_editor()
            return
        hull = self.hosts.get(v.get("type", "")) or {}
        cn = hull_cn_name(v.get("type", ""))
        year = hull.get("year")
        self.host_label.setText(
            f"{cn}  {v.get('type', '')}"
            + (f"  （{int(year)} 年）" if year else ""))
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.current_name)
        self.name_edit.blockSignals(False)
        self._load_advanced_fields()

        upgrades = v.get("modules") or {}
        slots = hull.get("module_slots") or {}
        # 空设计 = 默认配置（游戏使用 default_modules）
        if not upgrades:
            hint = QLabel("⚠️ 该设计未配置模块，游戏使用默认配置（可点击槽位添加模块后保存）")
            hint.setWordWrap(True)
            hint.setStyleSheet("color:#b7791f;")
            self._empty_hint = hint
            self.slot_grid.addWidget(hint, 0, 0, 1, SHIP_SLOT_COLS)
        # 布局：固定装备区（上）+ 甲板自定义区（下），各 6 列
        fixed_keys = [k for k in slots if "custom_slot" not in k]
        custom_keys = [k for k in slots if k not in fixed_keys]
        row = 1 if not upgrades else 0

        def add_zone(title, keys):
            nonlocal row
            if not keys:
                return
            header = QLabel("%s  [%s]" % (
                title,
                zone_summary_text(keys, slots,
                                  hull.get("module_count_limits") or [])))
            header.setStyleSheet(
                "color:#1f4f7e; font-weight:bold; padding:2px;")
            self.slot_grid.addWidget(header, row, 0, 1, SHIP_SLOT_COLS)
            row += 1
            idx = 0
            for slot_key in keys:
                slot_info = slots[slot_key]
                allowed = slot_info.get("allowed") or []
                card = QWidget()
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(0, 0, 0, 0)
                card_layout.setSpacing(2)
                lbl = QLabel(SLOT_LABELS.get(slot_key, slot_key))
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(_STAT_LABEL_STYLE)
                lbl.setToolTip(
                    "允许类别: " + "、".join(
                        CATEGORY_LABELS.get(c, c) for c in allowed) or "（无）")
                card_layout.addWidget(lbl)
                btn = QToolButton()
                btn.setFixedSize(130, 40)
                mod_key = upgrades.get(slot_key)
                locked = (not allowed and not slot_info.get("required"))
                if mod_key:
                    mod = self.modules.get(mod_key) or {}
                    btn.setText(mod.get("abbreviation") or mod_key)
                    btn.setToolTip(
                        f"{ship_cn_name(mod_key)}（{mod_key}）\n"
                        f"类别: {CATEGORY_LABELS.get(mod.get('category', ''), mod.get('category', ''))}\n"
                        + self._module_brief(mod))
                    btn.setStyleSheet(_SLOT_OCCUPIED)
                    btn.clicked.connect(
                        lambda _=False, s=slot_key: self._open_module_picker(s))
                elif locked:
                    btn.setText("🔒")
                    btn.setEnabled(False)
                    btn.setToolTip(f"{SLOT_LABELS.get(slot_key, slot_key)}"
                                   f"（该船体此槽位锁定，无可用模块）")
                    btn.setStyleSheet(_SLOT_LOCKED)
                elif slot_info.get("required"):
                    btn.setText("必装·待填")
                    btn.setEnabled(True)
                    btn.setToolTip(f"{SLOT_LABELS.get(slot_key, slot_key)}"
                                   f"（必装槽位，当前为空；点击添加模块）")
                    btn.setStyleSheet(_SLOT_REQUIRED_EMPTY)
                    btn.clicked.connect(
                        lambda _=False, s=slot_key: self._open_module_picker(s))
                else:
                    btn.setText("＋")
                    btn.setStyleSheet(_SLOT_EMPTY)
                    btn.setToolTip(f"{SLOT_LABELS.get(slot_key, slot_key)}"
                                   f"（可选槽位，点击添加模块）")
                    btn.clicked.connect(
                        lambda _=False, s=slot_key: self._open_module_picker(s))
                card_layout.addWidget(btn)
                self.slot_grid.addWidget(
                    card, row + idx // SHIP_SLOT_COLS,
                    idx % SHIP_SLOT_COLS)
                self._slot_buttons[slot_key] = btn
                idx += 1
            row += (idx + SHIP_SLOT_COLS - 1) // SHIP_SLOT_COLS

        add_zone("固定装备区（上排）", fixed_keys)
        add_zone("甲板自定义区（下排）", custom_keys)
        self.slot_grid.setColumnStretch(SHIP_SLOT_COLS, 1)
        self._update_same_name_label()
        self._update_stats()
        self._refresh_upgrade_card()
        self._update_save_validation()

    def _update_stats(self):
        v = self.current_variant
        if v is None:
            return
        hull = self.hosts.get(v.get("type", "")) or {}
        st = ship_design_stats(v, hull, self.modules)
        fmt = {
            "naval_speed": lambda x: _fmt(x, 1) + " kn",
            "naval_range": lambda x: _fmt(x, 0) + " km",
            "max_organisation": _fmt,
            "max_strength": _fmt,
            "reliability": lambda x: _fmt_pct(x, 1),
            "supply_consumption": lambda x: _fmt(x, 2),
            "manpower": lambda x: _fmt(x, 0),
            "fuel_consumption": lambda x: _fmt(x, 2),
            "lg_attack": _fmt, "lg_armor_piercing": _fmt,
            "hg_attack": _fmt, "hg_armor_piercing": _fmt,
            "torpedo_attack": _fmt, "sub_attack": _fmt,
            "armor_value": _fmt, "anti_air_attack": _fmt,
            "surface_visibility": _fmt, "surface_detection": _fmt,
            "sub_visibility": _fmt, "sub_detection": _fmt,
            "naval_mine_laying": lambda x: _fmt(x, 2),
            "naval_mine_sweeping": lambda x: _fmt(x, 2),
            "naval_weather_penalty_factor": lambda x: _fmt_pct(x, 0),
            "hit_profile_mult": lambda x: _fmt(x, 1),
        }
        for key, val in self._stat_labels.items():
            f = fmt.get(key, _fmt)
            val.setText(f(st.get(key)))
        dom = hull.get("naval_dominance_factor")
        if dom is None:
            dom = hull.get("stats", {}).get("naval_dominance_factor")
        self.dominance_label.setText(_fmt(dom, 0) if dom else "—")
        cost = st.get("cost")
        self.cost_label.setText(f"生产花费: {_fmt(cost, 0)}" if cost else "生产花费: —")

    # ---------- 模块选择 ----------

def open_ship_designer(mod_path="", hoi4_path="", parent=None):
    """入口：创建并显示舰艇设计器（非模态）。"""
    dlg = ShipDesignDialog(mod_path, hoi4_path, parent=parent)
    dlg.show()
    return dlg
