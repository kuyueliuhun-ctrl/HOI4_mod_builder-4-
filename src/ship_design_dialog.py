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
)

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


class ShipDesignDialog(QDialog):
    """舰艇设计器主对话框。"""

    saved = pyqtSignal()

    def __init__(self, mod_path="", hoi4_path="", country_tag="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self._initial_country_tag = (country_tag or "").upper()
        self.hulls = {}
        self.modules = {}
        self.variants = {}          # tag -> {name: {type, upgrades}}
        self.current_tag = ""
        self.current_name = ""
        self.current_variant = None
        self._stat_labels = {}
        self._slot_buttons = {}
        self._empty_hint = None

        self.setWindowTitle("舰艇设计")
        self.resize(1280, 780)
        self._build_ui()
        self._load_data()
        self._refresh_countries()

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
        self.hull_label = QLabel("未选择设计")
        self.hull_label.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#425062; padding:2px;")
        self.hull_label.setWordWrap(True)
        left_layout.addWidget(self.hull_label)

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

    def _build_stat_group(self, host_layout, title, fields):
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
            val.setAlignment(Qt.AlignmentFlag.AlignRight
                             | Qt.AlignmentFlag.AlignVCenter)
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            self._stat_labels[key] = val
        host_layout.addWidget(box)

    # ---------- 数据加载 ----------

    def _load_data(self):
        self.hulls = load_ship_hulls(self.mod_path, self.hoi4_path)
        self.modules = load_ship_modules(self.mod_path, self.hoi4_path)
        self.variants = load_ship_variants(self.mod_path, self.hoi4_path)

    def _country_file(self, tag):
        """tag → history/countries 文件路径（mod 优先）。"""
        for base in (self.mod_path, self.hoi4_path):
            if not base:
                continue
            d = os.path.join(base, "history", "countries")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                first = fn.split()[0].strip()
                if first.lower().endswith(".txt"):
                    first = first[:-4]
                if first == tag and fn.lower().endswith(".txt"):
                    return os.path.join(d, fn)
        return ""

    def _save_path(self, tag):
        """保存目标：mod 内路径（原版自动复制到 mod）。

        Returns:
            (mod_abs_path, copied)：copied=True 表示本次从游戏复制到 mod；
            找不到文件返回 (None, False)。
        """
        from state_build_ops import ensure_file_in_mod
        for base in (self.mod_path, self.hoi4_path):
            if not base:
                continue
            d = os.path.join(base, "history", "countries")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                first = fn.split()[0].strip()
                if first.lower().endswith(".txt"):
                    first = first[:-4]
                if first == tag and fn.lower().endswith(".txt"):
                    rel = os.path.join("history", "countries", fn)
                    return ensure_file_in_mod(self.mod_path, self.hoi4_path,
                                              rel)
        return None, False

    # ---------- 刷新 ----------

    def _refresh_countries(self):
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        for tag in sorted(self.variants):
            n = len(self.variants[tag])
            self.country_combo.addItem(f"{tag} ({n} 个设计)", tag)
        self.country_combo.blockSignals(False)
        if self.country_combo.count() > 0:
            # 优先选中调用方指定的初始国家（如从 OOB 文件识别出的国家）
            idx = 0
            if self._initial_country_tag:
                fi = self.country_combo.findData(self._initial_country_tag)
                if fi >= 0:
                    idx = fi
            self.country_combo.setCurrentIndex(idx)
            self._on_country_changed(idx)

    def _on_country_changed(self, index):
        tag = self.country_combo.itemData(index)
        self.current_tag = tag or ""
        self._refresh_designs()

    def _refresh_designs(self):
        self.design_combo.blockSignals(True)
        self.design_combo.clear()
        variants = self.variants.get(self.current_tag) or {}
        for name, v in variants.items():
            cn = hull_cn_name(v.get("type", ""))
            disp = ship_cn_name(name)
            self.design_combo.addItem(f"{disp}  [{cn}]", name)
        self.design_combo.blockSignals(False)
        if self.design_combo.count() > 0:
            self.design_combo.setCurrentIndex(0)
            self._on_design_changed(0)
        else:
            self.current_name = ""
            self.current_variant = None
            self._clear_editor()

    def _on_design_changed(self, index):
        name = self.design_combo.itemData(index)
        variants = self.variants.get(self.current_tag) or {}
        self.current_name = name or ""
        self.current_variant = variants.get(self.current_name)
        self._rebuild_editor()


    def _advanced_values(self):
        """收集高级字段表单值；空/默认值保持缺省语义。"""
        design_team = self.design_team_combo.currentText().strip()
        if design_team and not design_team.startswith("mio:"):
            design_team = "mio:" + design_team
        parent_version = self.parent_version_edit.text().strip()
        if parent_version == "":
            parent_version = 0
        return {
            "design_team": design_team,
            "parent_version": parent_version,
            "obsolete": self.obsolete_check.isChecked(),
            "icon": self.icon_edit.text().strip(),
        }

    def _load_advanced_fields(self):
        """把当前变体高级字段回填表单，并收集同国家已有设计团队作为下拉候选。"""
        if self.current_variant is None:
            self.design_team_combo.setCurrentText("")
            self.parent_version_edit.setText("")
            self.obsolete_check.setChecked(False)
            self.icon_edit.setText("")
            return
        v = self.current_variant
        tag_variants = self.variants.get(self.current_tag) or {}
        teams = sorted({(d.get("design_team") or "") for d in tag_variants.values()
                        if d.get("design_team")})
        self.design_team_combo.blockSignals(True)
        self.design_team_combo.clear()
        for team in teams:
            self.design_team_combo.addItem(team)
        self.design_team_combo.setCurrentText(v.get("design_team") or "")
        self.design_team_combo.blockSignals(False)
        pv = v.get("parent_version")
        self.parent_version_edit.setText("" if pv in (None, 0) else str(pv))
        self.obsolete_check.setChecked(bool(v.get("obsolete")))
        self.icon_edit.setText(v.get("icon") or "")

    # ---------- 编辑区 ----------

    def _clear_editor(self):
        self.hull_label.setText("（该国家暂无舰艇设计）")
        self.same_name_label.setText("")
        while self.slot_grid.count():
            item = self.slot_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for key in self._stat_labels:
            self._stat_labels[key].setText("—")
        self.dominance_label.setText("—")
        self.cost_label.setText("生产花费: —")
        self._load_advanced_fields()

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
        hull = self.hulls.get(v.get("type", "")) or {}
        cn = hull_cn_name(v.get("type", ""))
        year = hull.get("year")
        self.hull_label.setText(
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

    def _refresh_upgrade_card(self):
        rows = []
        if self.current_variant is not None:
            v = self.current_variant
            hull = self.hulls.get(v.get("type", "")) or {}
            keys = hull.get("upgrades_decl") or []
            defs = load_upgrade_definitions(self.hoi4_path, self.mod_path)
            cur_u = v.get("upgrades") or {}
            for key in keys:
                info = defs.get(key) or {}
                cur = int(cur_u.get(key, 0) or 0)
                mx = info.get("max_level") or 5
                cn = ship_cn_name(key)
                reqs = info.get("level_requirements") or {}
                remark = ""
                if reqs:
                    remark = "科技解锁: " + "、".join(
                        "Lv%d" % lv for lv in sorted(reqs))
                rows.append((cn, key, cur, mx, remark))
        self.upgrade_card.set_rows(rows)

    def _update_save_validation(self):
        if self.current_variant is None:
            return
        v = self.current_variant
        hull = self.hulls.get(v.get("type", "")) or {}
        slots = hull.get("module_slots") or {}
        modules = v.get("modules") or {}
        missing = sum(
            1 for s, info in slots.items()
            if info.get("required")
            and (not modules.get(s) or modules.get(s) == "empty"))
        if missing:
            self.save_validation_label.setText(
                "⛔ 必装槽未填 %d 个 —— 填满后方可保存" % missing)
            self.save_validation_label.setStyleSheet(
                "color:#b7791f; font-weight:bold;")
            self.save_btn.setEnabled(False)
        else:
            self.save_validation_label.setText("✅ 必装槽已填满，可保存")
            self.save_validation_label.setStyleSheet(
                "color:#2f7d57; font-weight:bold;")
            self.save_btn.setEnabled(True)

    def _module_brief(self, mod):
        """模块效果摘要（add/multiply 前几项）。"""
        parts = []
        for k, v in list((mod.get("add_stats") or {}).items())[:4]:
            parts.append(f"{k} {_fmt(v, 1)}")
        for k, v in list((mod.get("multiply_stats") or {}).items())[:3]:
            parts.append(f"{k} ×{_fmt(1 + v, 3)}")
        return "效果: " + " · ".join(parts) if parts else "（无修正）"

    def _update_stats(self):
        v = self.current_variant
        if v is None:
            return
        hull = self.hulls.get(v.get("type", "")) or {}
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

    def _open_module_picker(self, slot_key):
        if self.current_variant is None:
            return
        hull = self.hulls.get(self.current_variant.get("type", "")) or {}
        slot_info = (hull.get("module_slots") or {}).get(slot_key) or {}
        allowed = slot_info.get("allowed") or []
        current = (self.current_variant.get("modules") or {}).get(slot_key)
        dlg = ModulePickerDialog(self.modules, allowed,
                                 SLOT_LABELS.get(slot_key, slot_key),
                                 current_module=current, parent=self)
        if not dlg.exec():
            return
        upgrades = self.current_variant.setdefault("modules", {})
        if dlg.remove_requested:
            upgrades.pop(slot_key, None)
        elif dlg.picked:
            upgrades[slot_key] = dlg.picked
        self._rebuild_editor()

    # ---------- 模板管理 ----------

    def _add_design(self):
        if not self.current_tag:
            return
        from PyQt6.QtWidgets import QInputDialog
        hull_keys = [k for k in self.hulls
                     if not self.hulls[k].get("is_archetype")]
        if not hull_keys:
            QMessageBox.warning(self, "无法新建", "未找到可用船体。")
            return
        items = []
        for k in sorted(hull_keys, key=lambda x: (self.hulls[x].get("year") or 0, x)):
            cn = hull_cn_name(k)
            yr = self.hulls[k].get("year")
            items.append("%s  %s  [%s]" % (cn, yr if yr else "", k))
        choice, ok = QInputDialog.getItem(
            self, "选择船体", "船体（中文名 + 年份 + 键）:", items, 0, False)
        if not ok:
            return
        hull_key = choice.rsplit("[", 1)[-1].rstrip("]")
        if hull_key not in self.hulls:
            return
        name = "New Ship Design"
        self.variants.setdefault(self.current_tag, {})[name] = {
            "type": hull_key, "modules": {}}
        self._refresh_designs()
        idx = self.design_combo.findData(name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)

    def _copy_design(self):
        if self.current_variant is None:
            return
        import copy
        new_name = self.current_name + " Copy"
        self.variants.setdefault(self.current_tag, {})[new_name] = {
            "type": self.current_variant.get("type", ""),
            "modules": dict(self.current_variant.get("modules") or {}),
            "design_team": self.current_variant.get("design_team", ""),
            "parent_version": self.current_variant.get("parent_version", 0),
            "obsolete": self.current_variant.get("obsolete", False),
            "icon": self.current_variant.get("icon", ""),
        }
        self._refresh_designs()
        idx = self.design_combo.findData(new_name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)

    def _delete_design(self):
        if self.current_variant is None:
            return
        ret = QMessageBox.question(
            self, "删除设计",
            f"删除设计「{self.current_name}」？（写入保存后才生效）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.variants.get(self.current_tag, {}).pop(self.current_name, None)
        self.current_variant = None
        self._refresh_designs()

    # ---------- 设计模板（存为模板 / 从模板新建） ----------

    def _serialize_template(self, name):
        """当前设计 → create_equipment_variant PDX 文本（upgrades 块）。"""
        if self.current_variant is None:
            return None
        typ = self.current_variant.get("type", "")
        modules = self.current_variant.get("modules") or {}
        lines = ["create_equipment_variant = {",
                 f'\tname = "{name}"',
                 f"\ttype = {typ}"]
        adv = self._advanced_values()
        if adv["design_team"]:
            lines.append("\tdesign_team = " + adv["design_team"])
        if adv["parent_version"] not in (None, "", 0) and str(adv["parent_version"]) != "0":
            lines.append("\tparent_version = " + str(adv["parent_version"]))
        if adv["obsolete"]:
            lines.append("\tobsolete = yes")
        if adv["icon"]:
            lines.append('\ticon = "' + adv["icon"] + '"')
        lines.append("\tmodules = {")
        for slot, mod in modules.items():
            lines.append(f"\t\t{slot} = {mod}")
        lines.append("\t}")
        lines.append("}")
        return "\n".join(lines)

    def _save_as_template(self):
        if self.current_variant is None:
            QMessageBox.information(self, "提示", "没有可保存的设计。")
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "存为模板", "模板名:", text=self.current_name)
        if not ok or not name.strip():
            return
        content = self._serialize_template(name.strip())
        if not content:
            return
        from design_template import save_design_template
        path = save_design_template("ship", name.strip(), content)
        if path:
            QMessageBox.information(self, "已保存模板",
                                    f"模板已保存到:\n{path}")
        else:
            QMessageBox.critical(self, "保存失败", "模板保存失败。")

    def _new_from_template(self):
        if not self.current_tag:
            return
        from PyQt6.QtWidgets import QInputDialog
        from design_template import list_design_templates, load_design_template
        from ship_design import parse_equipment_variants
        tpls = list_design_templates("ship")
        if not tpls:
            QMessageBox.information(self, "模板", "暂无舰艇设计模板。")
            return
        names = [t["name"] for t in tpls]
        name, ok = QInputDialog.getItem(self, "从模板新建", "选择模板:",
                                        names, 0, False)
        if not ok:
            return
        content = load_design_template("ship", name)
        if not content:
            return
        parsed = parse_equipment_variants(content, None, "modules")
        if not parsed:
            QMessageBox.warning(self, "模板无效",
                                "模板内容不是有效的舰艇设计。")
            return
        tpl_name, tpl_data = next(iter(parsed.items()))
        variants = self.variants.setdefault(self.current_tag, {})
        new_name = tpl_name
        while new_name in variants:
            new_name = tpl_name + " Copy"
            tpl_name = new_name
        variants[new_name] = {
            "type": tpl_data.get("type", ""),
            "modules": tpl_data.get("modules", {}),
            "design_team": tpl_data.get("design_team", ""),
            "parent_version": tpl_data.get("parent_version", 0),
            "obsolete": tpl_data.get("obsolete", False),
            "icon": tpl_data.get("icon", ""),
        }
        self._refresh_designs()
        idx = self.design_combo.findData(new_name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)

    # ---------- 同款跨国家（按名字匹配） ----------

    def _same_name_tags(self):
        """当前设计名在哪些国家存在（含当前国家）。"""
        if not self.current_name:
            return []
        tags = []
        for tag, ds in self.variants.items():
            if self.current_name in ds:
                tags.append(tag)
        return tags

    def _update_same_name_label(self):
        tags = self._same_name_tags()
        if len(tags) > 1:
            self.same_name_label.setText(
                f"同款 {len(tags)} 国: " + "、".join(sorted(tags)[:8])
                + ("…" if len(tags) > 8 else ""))
        else:
            self.same_name_label.setText("")

    def _sync_to_all_same_name(self):
        """把当前设计配置写回所有使用同名设计的国家（原子写）。"""
        if self.current_variant is None:
            return
        tags = [t for t in self._same_name_tags() if t != self.current_tag]
        if not tags:
            QMessageBox.information(self, "同步",
                                    "当前设计没有其他国家的同款。")
            return
        ret = QMessageBox.question(
            self, "同步到所有同款",
            f"将当前配置写入 {len(tags)} 个国家的同名设计？\n"
            + "、".join(sorted(tags)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        from ship_design import apply_variant_upgrades, insert_variant
        modules = dict(self.current_variant.get("modules") or {})
        typ = self.current_variant.get("type", "")
        name = self.current_name
        ok = 0
        failed = []
        for tag in tags:
            try:
                path, _copied = self._save_path(tag)
                if not path:
                    failed.append(tag)
                    continue
                with open(path, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
                if name in content:
                    new_content = apply_variant_modules(
                        content, name, modules, typ)
                else:
                    new_content = insert_variant(content, tag, name, typ,
                                                 modules)
                if new_content is not None:
                    new_content = apply_variant_upgrades(
                        new_content, name,
                        self.upgrade_card.values(), typ)
                if new_content is not None:
                    new_content = apply_variant_advanced(
                        new_content, name,
                        self._advanced_values(), typ)
                if new_content is None:
                    failed.append(tag)
                    continue
                from write_utils import atomic_write_text
                atomic_write_text(path, new_content)
                adv = self._advanced_values()
                self.variants.setdefault(tag, {})[name] = {
                    "type": typ, "modules": modules,
                    "design_team": adv["design_team"],
                    "parent_version": adv["parent_version"],
                    "obsolete": adv["obsolete"],
                    "icon": adv["icon"],
                }
                ok += 1
            except Exception as e:
                failed.append(f"{tag}({e})")
        msg = f"已同步 {ok} 个国家。"
        if failed:
            msg += "\n失败: " + "、".join(failed)
        QMessageBox.information(self, "同步完成", msg)
        self._update_same_name_label()

    # ---------- 保存 / 重置 ----------

    def _save(self):
        if self.current_variant is None:
            QMessageBox.information(self, "提示", "没有可保存的设计。")
            return
        tag = self.current_tag
        # 保存目标必须落在 mod 内：原版 countries 文件自动复制到 mod 再写
        path, copied = self._save_path(tag)
        if not path:
            QMessageBox.critical(self, "保存失败", f"找不到国家 {tag} 的文件。")
            return
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        new_name = self.name_edit.text().strip() or self.current_name
        old_name = self.current_name
        upgrades = self.current_variant.get("modules") or {}
        new_content = None
        if old_name in content:
            new_content = apply_variant_modules(
                content, old_name, upgrades,
                self.current_variant.get("type", ""))
            if new_content is not None and new_name != old_name:
                new_content = rename_variant(
                    new_content, old_name, new_name,
                    self.current_variant.get("type", ""))
        else:
            hull_key = self.current_variant.get("type", "")
            new_content = insert_variant(content, tag, new_name, hull_key,
                                         upgrades)
        if new_content is not None:
            new_content = apply_variant_upgrades(
                new_content, new_name,
                self.upgrade_card.values(),
                self.current_variant.get("type", ""))
        if new_content is not None:
            new_content = apply_variant_advanced(
                new_content, new_name,
                self._advanced_values(),
                self.current_variant.get("type", ""))
        if new_content is None:
            QMessageBox.critical(self, "保存失败",
                                 "未能定位到设计块，文件可能已被外部修改。")
            return
        try:
            from write_utils import atomic_write_text
            atomic_write_text(path, new_content)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        # 内存同步
        variants = self.variants.setdefault(tag, {})
        if old_name != new_name:
            variants.pop(old_name, None)
        adv = self._advanced_values()
        variants[new_name] = {
            "type": self.current_variant.get("type", ""),
            "modules": upgrades,
            "design_team": adv["design_team"],
            "parent_version": adv["parent_version"],
            "obsolete": adv["obsolete"],
            "icon": adv["icon"],
        }
        self.current_name = new_name
        self._refresh_designs()
        idx = self.design_combo.findData(new_name)
        if idx >= 0:
            self.design_combo.setCurrentIndex(idx)
        QMessageBox.information(self, "已保存",
                                f"已保存到:\n{path}"
                                + ("\n\n（该国家文件原本只在游戏目录，已自动复制到 mod）"
                                   if copied else ""))
        self.saved.emit()

    def _reset(self):
        if not self.current_tag:
            return
        from ship_design import _VARIANTS_CACHE
        _VARIANTS_CACHE.pop((self.mod_path or "", self.hoi4_path or ""), None)
        self._load_data()
        self._refresh_countries()


def open_ship_designer(mod_path="", hoi4_path="", parent=None):
    """入口：创建并显示舰艇设计器（非模态）。"""
    dlg = ShipDesignDialog(mod_path, hoi4_path, parent=parent)
    dlg.show()
    return dlg
