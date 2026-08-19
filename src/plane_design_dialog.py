"""飞机设计器（Plane Designer）— 仿游戏内飞机设计界面（亮色主题）

顶部标题栏（国家/设计下拉/改名/新建/复制/删除 + 保存），
中部左=机型信息与模块槽位网格（点击槽位选模块），右=数据面板
（基础/战斗/其他三组），底部操作栏（重置 + 生产/改装花费）。

数据流：plane_design.load_plane_airframes/modules/variants 解析，
plane_design_stats 属性估算；保存用 apply/insert/remove/rename_variant
（modules 块）块级写回 history/countries 文件（原子写，原版自动落 mod）。
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QToolButton, QLineEdit, QLabel, QMessageBox,
    QGridLayout, QScrollArea, QWidget, QFrame, QSplitter, QGroupBox,
    QComboBox, QDialogButtonBox,
)

from plane_design import (
    SLOT_LABELS, CATEGORY_LABELS,
    load_plane_airframes, load_plane_modules, load_plane_variants,
    plane_design_stats, plane_type_cn_name, plane_cn_name,
    apply_variant_modules, insert_variant, remove_variant, rename_variant,
)

PANEL_WIDTH = 330
PLANE_SLOT_COLS = 5   # 飞机槽位网格列数（上5下6 布局）

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


def _fmt(v, nd=1):
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


class ModulePickerDialog(_BaseModulePickerDialog):
    """点击槽位弹出的模块选择面板（公共实现见 designer_common）。"""

    def __init__(self, modules, allowed_categories, slot_label,
                 current_module=None, parent=None):
        super().__init__(
            modules, allowed_categories, slot_label,
            current_module=current_module,
            name_func=plane_cn_name,
            category_labels=CATEGORY_LABELS,
            parent=parent)


class PlaneDesignDialog(QDialog):
    """飞机设计器主对话框。"""

    saved = pyqtSignal()

    def __init__(self, mod_path="", hoi4_path="", country_tag="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self._initial_country_tag = (country_tag or "").upper()
        self.airframes = {}
        self.modules = {}
        self.variants = {}
        self.current_tag = ""
        self.current_name = ""
        self.current_variant = None
        self._stat_labels = {}
        self._slot_buttons = {}
        self._empty_hint = None

        self.setWindowTitle("飞机设计")
        self.resize(1280, 780)
        self._build_ui()
        self._load_data()
        self._refresh_countries()

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        bar = QHBoxLayout()
        title = QLabel("✈ 飞机设计")
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
        bar.addWidget(self.add_btn)
        bar.addWidget(self.copy_btn)
        bar.addWidget(self.del_btn)
        self.tpl_save_btn = QPushButton("💾 存为模板")
        self.tpl_save_btn.clicked.connect(self._save_as_template)
        self.tpl_load_btn = QPushButton("📥 模板新建")
        self.tpl_load_btn.clicked.connect(self._new_from_template)
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

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.plane_label = QLabel("未选择设计")
        self.plane_label.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#425062; padding:2px;")
        self.plane_label.setWordWrap(True)
        left_layout.addWidget(self.plane_label)

        self.slot_scroll = QScrollArea()
        self.slot_scroll.setWidgetResizable(True)
        self.slot_host = QWidget()
        self.slot_grid = QGridLayout(self.slot_host)
        self.slot_grid.setSpacing(6)
        self.slot_scroll.setWidget(self.slot_host)
        left_layout.addWidget(self.slot_scroll, 1)

        hint = QLabel(
            "提示: 点击槽位选择模块（按机体允许的类别过滤）；已装模块再次点击"
            "可更换或移除。右侧数值为基础值估算（airframe 基础 + 模块修正，"
            "未含科技/MIO 加成）。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5d6b7a")
        left_layout.addWidget(hint)
        split.addWidget(left)

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
            ("maximum_speed", "最大速度"), ("air_range", "航程"),
            ("supply_consumption", "补给使用"), ("weight", "重量"),
            ("thrust", "推力"), ("air_defence", "空中防御"),
            ("air_attack", "对空攻击"), ("air_agility", "机动"),
            ("air_superiority", "空优"), ("reliability", "可靠性"),
            ("fuel_consumption", "燃油使用"), ("manpower", "人力"),
        ))
        self._build_stat_group(panel_host_layout, "战斗数据", (
            ("naval_strike_attack", "对海攻击"),
            ("naval_strike_targetting", "对海瞄准"),
            ("air_ground_attack", "对地攻击"), ("air_bombing", "战略轰炸"),
            ("surface_detection", "对海探测"), ("sub_detection", "对潜探测"),
            ("night_penalty", "夜间惩罚"), ("mines_planting", "布雷"),
            ("mines_sweeping", "扫雷"),
        ))
        self._build_stat_group(panel_host_layout, "其他数据", (
            ("build_cost_ic", "生产花费"), ("convert_cost_ic", "改装花费"),
        ))

        panel_host_layout.addStretch(1)
        panel_scroll.setWidget(panel_host)
        panel_layout.addWidget(panel_scroll)
        split.addWidget(panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        root.addWidget(split, 1)

        bottom = QHBoxLayout()
        self.reset_btn = QPushButton("⟲ 重置")
        self.reset_btn.setToolTip("放弃当前设计未保存的修改，从文件重新载入")
        self.reset_btn.clicked.connect(self._reset)
        bottom.addWidget(self.reset_btn)
        bottom.addStretch(1)
        self.cost_label = QLabel("生产花费: — · 改装花费: —")
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
        self.airframes = load_plane_airframes(self.mod_path, self.hoi4_path)
        self.modules = load_plane_modules(self.mod_path, self.hoi4_path)
        self.variants = load_plane_variants(self.mod_path, self.hoi4_path)

    def _save_path(self, tag):
        """保存目标：mod 内路径（原版自动复制到 mod）。"""
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
            cn = plane_type_cn_name(v.get("type", ""))
            self.design_combo.addItem(f"{name}  [{cn}]", name)
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

    # ---------- 编辑区 ----------

    def _clear_editor(self):
        self.plane_label.setText("（该国家暂无飞机设计）")
        self.same_name_label.setText("")
        while self.slot_grid.count():
            item = self.slot_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for key in self._stat_labels:
            self._stat_labels[key].setText("—")
        self.cost_label.setText("生产花费: — · 改装花费: —")

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
        af = self.airframes.get(v.get("type", "")) or {}
        cn = plane_type_cn_name(v.get("type", ""))
        year = af.get("year")
        if af:
            self.plane_label.setText(
                f"{cn}  {v.get('type', '')}"
                + (f"  （{int(year)} 年）" if year else ""))
        else:
            self.plane_label.setText(
                f"{cn}  {v.get('type', '')}  （机体定义未找到）")
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.current_name)
        self.name_edit.blockSignals(False)

        modules = v.get("modules") or {}
        slots = af.get("module_slots") or {}
        # 空设计 = 默认配置（游戏使用 default_modules）
        if not modules:
            hint = QLabel("⚠️ 该设计未配置模块，游戏使用默认配置（可点击槽位添加模块后保存）")
            hint.setWordWrap(True)
            hint.setStyleSheet("color:#b7791f;")
            self._empty_hint = hint
            self.slot_grid.addWidget(hint, 0, 0, 1, PLANE_SLOT_COLS)
        # 5 列布局：上排/下排两排（视觉贴近游戏内）
        idx = 0
        for slot_key, slot_info in slots.items():
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
            btn.setFixedSize(150, 40)
            mod_key = modules.get(slot_key)
            locked = (not allowed and not slot_info.get("required"))
            if mod_key and mod_key != "empty":
                mod = self.modules.get(mod_key) or {}
                btn.setText(mod.get("abbreviation") or mod_key)
                btn.setToolTip(
                    f"{plane_cn_name(mod_key)}（{mod_key}）\n"
                    f"类别: {CATEGORY_LABELS.get(mod.get('category', ''), mod.get('category', ''))}\n"
                    + self._module_brief(mod))
                btn.setStyleSheet(_SLOT_OCCUPIED)
                btn.clicked.connect(
                    lambda _=False, s=slot_key: self._open_module_picker(s))
            elif locked:
                btn.setText("🔒")
                btn.setEnabled(False)
                btn.setToolTip(f"{SLOT_LABELS.get(slot_key, slot_key)}"
                               f"（该机体此槽位锁定，无可用模块）")
                btn.setStyleSheet(_SLOT_LOCKED)
            elif slot_info.get("required"):
                btn.setText("🔒")
                btn.setEnabled(False)
                btn.setToolTip(f"{SLOT_LABELS.get(slot_key, slot_key)}"
                               f"（必装槽位，当前为空）")
                btn.setStyleSheet(_SLOT_LOCKED)
            else:
                btn.setText("＋")
                btn.setStyleSheet(_SLOT_EMPTY)
                btn.setToolTip(f"{SLOT_LABELS.get(slot_key, slot_key)}"
                               f"（可选槽位，点击添加模块）")
                btn.clicked.connect(
                    lambda _=False, s=slot_key: self._open_module_picker(s))
            card_layout.addWidget(btn)
            self.slot_grid.addWidget(card, (idx // PLANE_SLOT_COLS) + 1,
                                     idx % PLANE_SLOT_COLS)
            self._slot_buttons[slot_key] = btn
            idx += 1
        self.slot_grid.setColumnStretch(PLANE_SLOT_COLS, 1)
        self._update_same_name_label()
        self._update_stats()

    def _module_brief(self, mod):
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
        af = self.airframes.get(v.get("type", "")) or {}
        st = plane_design_stats(v, af, self.modules)
        fmt = {
            "maximum_speed": lambda x: _fmt(x, 1) + " km/h",
            "air_range": lambda x: _fmt(x, 0) + " km",
            "supply_consumption": lambda x: _fmt(x, 2),
            "weight": lambda x: _fmt(x, 1),
            "thrust": lambda x: _fmt(x, 1),
            "air_defence": lambda x: _fmt(x, 1),
            "air_attack": lambda x: _fmt(x, 1),
            "air_agility": lambda x: _fmt(x, 1),
            "air_superiority": lambda x: _fmt(x, 2),
            "reliability": lambda x: _fmt_pct(x, 1),
            "fuel_consumption": lambda x: _fmt(x, 2),
            "manpower": lambda x: _fmt(x, 0),
            "naval_strike_attack": lambda x: _fmt(x, 2),
            "naval_strike_targetting": lambda x: _fmt(x, 2),
            "air_ground_attack": lambda x: _fmt(x, 1),
            "air_bombing": lambda x: _fmt(x, 1),
            "surface_detection": lambda x: _fmt(x, 1),
            "sub_detection": lambda x: _fmt(x, 1),
            "night_penalty": lambda x: _fmt_pct(x, 1),
            "mines_planting": lambda x: _fmt(x, 2),
            "mines_sweeping": lambda x: _fmt(x, 2),
            "build_cost_ic": lambda x: _fmt(x, 2),
            "convert_cost_ic": lambda x: _fmt(x, 2),
        }
        for key, val in self._stat_labels.items():
            f = fmt.get(key, _fmt)
            val.setText(f(st.get(key)))
        cost = st.get("cost")
        conv = st.get("convert_cost")
        self.cost_label.setText(
            f"生产花费: {_fmt(cost, 2)} · 改装花费: {_fmt(conv, 2)}")

    # ---------- 模块选择 ----------

    def _open_module_picker(self, slot_key):
        if self.current_variant is None:
            return
        af = self.airframes.get(self.current_variant.get("type", "")) or {}
        slot_info = (af.get("module_slots") or {}).get(slot_key) or {}
        allowed = slot_info.get("allowed") or []
        current = (self.current_variant.get("modules") or {}).get(slot_key)
        dlg = ModulePickerDialog(self.modules, allowed,
                                 SLOT_LABELS.get(slot_key, slot_key),
                                 current_module=current, parent=self)
        if not dlg.exec():
            return
        modules = self.current_variant.setdefault("modules", {})
        if dlg.remove_requested:
            modules.pop(slot_key, None)
        elif dlg.picked:
            modules[slot_key] = dlg.picked
        self._rebuild_editor()

    # ---------- 设计管理 ----------

    def _add_design(self):
        if not self.current_tag:
            return
        name = "New Plane Design"
        keys = [k for k in self.airframes if not self.airframes[k].get("is_archetype")]
        if not keys:
            QMessageBox.warning(self, "无法新建", "未找到可用机体。")
            return
        self.variants.setdefault(self.current_tag, {})[name] = {
            "type": keys[0], "modules": {}}
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
        """当前设计 → create_equipment_variant PDX 文本（modules 块）。"""
        if self.current_variant is None:
            return None
        typ = self.current_variant.get("type", "")
        modules = self.current_variant.get("modules") or {}
        lines = ["create_equipment_variant = {",
                 '\tname = "' + name + '"',
                 "\ttype = " + typ,
                 "\tmodules = {"]
        for slot, mod in modules.items():
            lines.append("\t\t" + str(slot) + " = " + str(mod))
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
        path = save_design_template("plane", name.strip(), content)
        if path:
            QMessageBox.information(self, "已保存模板",
                                    "模板已保存到:\n" + path)
        else:
            QMessageBox.critical(self, "保存失败", "模板保存失败。")

    def _new_from_template(self):
        if not self.current_tag:
            return
        from PyQt6.QtWidgets import QInputDialog
        from design_template import list_design_templates, load_design_template
        from plane_design import parse_equipment_variants
        tpls = list_design_templates("plane")
        if not tpls:
            QMessageBox.information(self, "模板", "暂无飞机设计模板。")
            return
        names = [t["name"] for t in tpls]
        name, ok = QInputDialog.getItem(self, "从模板新建", "选择模板:",
                                        names, 0, False)
        if not ok:
            return
        content = load_design_template("plane", name)
        if not content:
            return
        parsed = parse_equipment_variants(content, None, "modules")
        if not parsed:
            QMessageBox.warning(self, "模板无效",
                                "模板内容不是有效的飞机设计。")
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
                    new_content = apply_variant_modules(content, name, modules)
                else:
                    new_content = insert_variant(content, tag, name, typ,
                                                 modules)
                if new_content is None:
                    failed.append(tag)
                    continue
                from write_utils import atomic_write_text
                atomic_write_text(path, new_content)
                # 内存同步
                self.variants.setdefault(tag, {})[name] = {
                    "type": typ, "modules": modules}
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
        modules = self.current_variant.get("modules") or {}
        new_content = None
        if old_name in content:
            new_content = apply_variant_modules(content, old_name, modules)
            if new_content is not None and new_name != old_name:
                new_content = rename_variant(new_content, old_name, new_name)
        else:
            new_content = insert_variant(content, tag, new_name,
                                         self.current_variant.get("type", ""),
                                         modules)
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
        variants = self.variants.setdefault(tag, {})
        if old_name != new_name:
            variants.pop(old_name, None)
        variants[new_name] = {
            "type": self.current_variant.get("type", ""),
            "modules": modules,
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
        from plane_design import _PLANE_VARIANTS_CACHE
        _PLANE_VARIANTS_CACHE.pop((self.mod_path or "", self.hoi4_path or ""),
                                  None)
        self._load_data()
        self._refresh_countries()


def open_plane_designer(mod_path="", hoi4_path="", parent=None):
    """入口：创建并显示飞机设计器（非模态）。"""
    dlg = PlaneDesignDialog(mod_path, hoi4_path, parent=parent)
    dlg.show()
    return dlg
