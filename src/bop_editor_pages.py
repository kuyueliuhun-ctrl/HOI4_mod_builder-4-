# -*- coding: utf-8 -*-
"""BOP 编辑器三页/卡片/决议动作构建层（F5 拆分自 bop_editor_dialog.py）。

仅包含平衡页、势力与修正页、决议动作页的 UI 构建与卡片/动作逻辑；
保存/文件写回仍在 BopEditorDialog。
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSlider,
    QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from ai_loader import _find_block_bounds
from ai_ui_common import KeyValueTableEditor, ScriptBlockEditorDialog
from bop_loader import (
    _parse_decision_action, _state_label, find_active_range, load_bop_actions,
)
from oob_loader import _block_ranges
from theme import COLORS as C

try:
    from quick_loc_menu import install_context_menu
except Exception:  # 测试/无菜单环境兼容
    def install_context_menu(*args, **kwargs):
        return None


_ICON_TOKEN_RE = re.compile(r"^\s*£[^\s]*\s*")
_VAR_REF_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\$")
_CARD_QSS = """
QFrame#BopCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QLabel#BopCardTitle {{
    color: {heading};
    font-weight: bold;
    font-size: 14px;
}}
QLabel#BopSecondary {{
    color: {secondary};
}}
""".format(surface=C["bg_surface"], border=C["border_strong"],
           heading=C["text_heading"], secondary=C["text_secondary"])


class BopEditorPagesMixin:
    """平衡/势力/决议三页的 UI 构建方法集合。"""

    def _build_balance_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        root = QVBoxLayout(page)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(8)

        # 平衡与区间卡片
        head = _card("平衡与区间")
        head_lay = head.layout()

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("初始值"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-100, 100)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(5)
        self.slider.setValue(
            int(round(float(self.bop.get("initial_value", 0.0)) * 100)))
        self.slider.valueChanged.connect(self._refresh_slider_text)
        slider_row.addWidget(self.slider, 1)

        self.initial_edit = QDoubleSpinBox()
        self.initial_edit.setRange(-1.0, 1.0)
        self.initial_edit.setDecimals(3)
        self.initial_edit.setSingleStep(0.01)
        self.initial_edit.setValue(float(self.bop.get("initial_value", 0.0)))
        self.initial_edit.valueChanged.connect(self._on_initial_edit)
        slider_row.addWidget(self.initial_edit)
        head_lay.addLayout(slider_row)

        self.status_label = QLabel("领袖权力巩固")
        self.status_label.setStyleSheet("font-weight:bold; color:%s;"
                                        % C["text_heading"])
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head_lay.addWidget(self.status_label)

        sides = QHBoxLayout()
        left_label = QLabel(_loc_text(self._loc, self.bop.get("left_side", "")))
        right_label = QLabel(_loc_text(self._loc, self.bop.get("right_side", "")))
        right_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        install_context_menu(
            left_label, self.mod_path, self.hoi4_path,
            key_provider=lambda: self.bop.get("left_side", "") or "",
            parent=self)
        install_context_menu(
            right_label, self.mod_path, self.hoi4_path,
            key_provider=lambda: self.bop.get("right_side", "") or "",
            parent=self)
        sides.addWidget(left_label)
        sides.addStretch(1)
        sides.addWidget(right_label)
        head_lay.addLayout(sides)

        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("color:%s; font-weight:bold;"
                                       % C["accent"])
        head_lay.addWidget(self.value_label)

        self.modifiers_label = QLabel("当前修正：—")
        self.modifiers_label.setWordWrap(True)
        self.modifiers_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.modifiers_label.setStyleSheet("color:%s;" % C["text_secondary"])
        head_lay.addWidget(self.modifiers_label)

        # 基础字段（兼容旧测试）
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.addWidget(QLabel("左势力 ID"), 0, 0)
        self.left_edit = QLineEdit(self.bop.get("left_side", ""))
        grid.addWidget(self.left_edit, 0, 1)
        grid.addWidget(QLabel("右势力 ID"), 0, 2)
        self.right_edit = QLineEdit(self.bop.get("right_side", ""))
        grid.addWidget(self.right_edit, 0, 3)
        grid.addWidget(QLabel("决策分类"), 1, 0)
        self.decision_edit = QLineEdit(self.bop.get("decision_category", ""))
        grid.addWidget(self.decision_edit, 1, 1, 1, 3)
        head_lay.addLayout(grid)
        root.addWidget(head)

        # 区间与修正卡片
        zone = _card("区间与修正（行内直接编辑）")
        zone_lay = zone.layout()
        self.ranges_holder = QVBoxLayout()
        self.ranges_holder.setSpacing(6)
        zone_lay.addLayout(self.ranges_holder)
        add_range_btn = QPushButton("＋ 新增区间")
        add_range_btn.clicked.connect(self._add_range)
        zone_lay.addWidget(add_range_btn)
        root.addWidget(zone)
        root.addStretch(1)
        return page


    def _build_sides_tab(self):
        tab = QWidget()
        root = QHBoxLayout(tab)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        self.side_holder = QHBoxLayout()
        root.addLayout(self.side_holder)
        return tab


    def _build_actions_tab(self):
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        bar = QHBoxLayout()
        cat_lab = QLabel("决议分类")
        cat_lab.setStyleSheet("color:%s;" % C["text_secondary"])
        self.action_category_label = QLabel(
            self.bop.get("decision_category", "") or "—")
        self.action_category_label.setStyleSheet("color:%s; font-weight:bold;"
                                                 % C["text_heading"])
        bar.addWidget(cat_lab)
        bar.addWidget(self.action_category_label, 1)
        new_btn = QPushButton("＋ 新建决议")
        new_btn.setStyleSheet("font-weight:bold; color:%s;" % C["warning"])
        new_btn.setToolTip("在决策分类块末尾插入决议（模板：通用/限时/切换类）")
        new_btn.clicked.connect(self._new_decision)
        bar.addWidget(new_btn)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.action_list = QListWidget()
        self.action_list.currentItemChanged.connect(self._on_action_changed)
        split.addWidget(self.action_list)
        split.setStretchFactor(0, 1)

        detail = _card("决议编辑（选中项）")
        detail_lay = detail.layout()
        self.action_key_label = QLabel("—")
        self.action_key_label.setStyleSheet("color:%s;" % C["text_secondary"])
        detail_lay.addWidget(self.action_key_label)

        name_grid = QGridLayout()
        name_grid.addWidget(QLabel("本地化键"), 0, 0)
        self.action_loc_key_edit = QLineEdit()
        self.action_loc_key_edit.setReadOnly(True)
        name_grid.addWidget(self.action_loc_key_edit, 0, 1)
        name_grid.addWidget(QLabel("中文名"), 1, 0)
        self.action_name_cn_edit = QLineEdit()
        name_grid.addWidget(self.action_name_cn_edit, 1, 1)
        detail_lay.addLayout(name_grid)

        num_row = QHBoxLayout()
        num_row.addWidget(QLabel("花费"))
        self.action_cost_edit = QLineEdit()
        self.action_cost_edit.setPlaceholderText("50 / 脚本变量")
        num_row.addWidget(self.action_cost_edit, 1)
        num_row.addWidget(QLabel("BOP 增量"))
        self.action_delta_edit = QDoubleSpinBox()
        self.action_delta_edit.setRange(-1.0, 1.0)
        self.action_delta_edit.setDecimals(3)
        self.action_delta_edit.setSingleStep(0.01)
        self.action_delta_edit.valueChanged.connect(self._on_delta_changed)
        num_row.addWidget(self.action_delta_edit)
        detail_lay.addLayout(num_row)

        block_row = QHBoxLayout()
        self.action_block_selector = QComboBox()
        for key in ("complete_effect", "visible", "available",
                    "remove_effect", "ai_will_do"):
            self.action_block_selector.addItem(key, key)
        edit_block_btn = QPushButton("✎ 效果/触发（结构化块编辑）")
        edit_block_btn.clicked.connect(self._edit_action_block)
        block_row.addWidget(self.action_block_selector, 1)
        block_row.addWidget(edit_block_btn)
        detail_lay.addLayout(block_row)

        del_btn = QPushButton("🗑 删除该决议")
        del_btn.setStyleSheet("color:%s;" % C["danger"])
        del_btn.clicked.connect(self._delete_action)
        detail_lay.addWidget(del_btn)

        split.addWidget(detail)
        split.setStretchFactor(1, 2)
        root.addWidget(split, 1)
        return tab

    # ------------------------------------------------------------ 区间卡片

    def _make_range_card(self, item):
        rng = item["rng"]
        side_id = item["side_id"]
        card = _card("%s（%s）" % (
            _loc_text(self._loc, rng.get("id", "")), rng.get("id", "")))
        card_lay = card.layout()
        card.setStyleSheet(card.styleSheet() +
                           "\nQLabel#BopCardTitle:hover { color:%s; }"
                           % C["accent"])
        if side_id:
            tip = QLabel("所属势力：%s" % side_id)
            tip.setStyleSheet("color:%s; font-size:11px;"
                              % C["text_tertiary"])
            card_lay.addWidget(tip)

        nums = QHBoxLayout()
        min_edit = QDoubleSpinBox()
        min_edit.setRange(-1000, 1000)
        min_edit.setDecimals(3)
        min_edit.setValue(float(rng.get("min", 0.0)))
        max_edit = QDoubleSpinBox()
        max_edit.setRange(-1000, 1000)
        max_edit.setDecimals(3)
        max_edit.setValue(float(rng.get("max", 0.0)))
        min_edit.valueChanged.connect(
            lambda v, r=rng: r.__setitem__("min", v))
        max_edit.valueChanged.connect(
            lambda v, r=rng: r.__setitem__("max", v))
        nums.addWidget(QLabel("min"))
        nums.addWidget(min_edit)
        nums.addWidget(QLabel("max"))
        nums.addWidget(max_edit)
        nums.addStretch(1)
        del_btn = QPushButton("🗑")
        del_btn.setToolTip("删除该区间")
        del_btn.clicked.connect(lambda _=False, c=card: self._delete_range(c))
        nums.addWidget(del_btn)
        card_lay.addLayout(nums)

        mod_table = KeyValueTableEditor("修正（modifier）", "值")
        mod_table.set_data(rng.get("modifier") or {})
        card_lay.addWidget(mod_table)

        info = {
            "rng": rng,
            "side_id": side_id,
            "min_edit": min_edit,
            "max_edit": max_edit,
            "mod_table": mod_table,
            "frame": card,
        }
        return card, info


    def _collect_range_card_data(self):
        """把当前区间卡表单写回内存 rng（modifier 表是独立控件）。"""
        for info in getattr(self, "_range_cards", []):
            info["rng"]["modifier"] = info["mod_table"].data()


    def _rebuild_range_cards(self):
        self._collect_range_card_data()
        self._range_cards = []
        while self.ranges_holder.count():
            item = self.ranges_holder.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for item in self._flat_ranges():
            w, info = self._make_range_card(item)
            self.ranges_holder.addWidget(w)
            self._range_cards.append(info)


    def _add_range(self):
        count = len(self._flat_ranges()) + 1
        rng_id = "%s_range_%d" % (self.bop.get("id", "bop"), count)
        rng = {"id": rng_id, "min": -0.1, "max": 0.1, "modifier": {},
               "on_activate": None, "on_deactivate": None}
        self.bop.setdefault("ranges", []).append(rng)
        self._dirty = True
        self._rebuild_range_cards()
        self._rebuild_side_cards()


    def _delete_range(self, card):
        info = next((x for x in self._range_cards if x["frame"] is card),
                    None)
        if info is None:
            return
        rng = info["rng"]
        reply = QMessageBox.question(
            self, "确认", "确定要删除区间 '%s' 吗？" % rng.get("id", ""))
        if reply != QMessageBox.StandardButton.Yes:
            return
        if info["side_id"]:
            for side in self.bop.get("sides", []):
                if side.get("id") == info["side_id"]:
                    side["ranges"] = [r for r in side.get("ranges", [])
                                      if r is not rng]
                    break
        else:
            self.bop["ranges"] = [r for r in self.bop.get("ranges", [])
                                  if r is not rng]
        self._dirty = True
        self._rebuild_range_cards()
        self._rebuild_side_cards()

    # ------------------------------------------------------------ 势力卡片

    def _make_side_card(self, side):
        card = _card("%s（%s）" % (
            _loc_text(self._loc, side.get("id", "")), side.get("id", "")))
        card_lay = card.layout()

        icon_row = QHBoxLayout()
        icon_row.addWidget(QLabel("图标"))
        icon_edit = QLineEdit(side.get("icon", ""))
        icon_row.addWidget(icon_edit, 1)
        card_lay.addLayout(icon_row)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("本地化键"))
        loc_key_edit = QLineEdit(side.get("id", ""))
        key_row.addWidget(loc_key_edit, 1)
        card_lay.addLayout(key_row)

        cn_row = QHBoxLayout()
        cn_row.addWidget(QLabel("中文名"))
        name_cn_edit = QLineEdit(_loc_text(self._loc, side.get("id", "")))
        cn_row.addWidget(name_cn_edit, 1)
        card_lay.addLayout(cn_row)

        assoc_lab = QLabel("关联区间")
        assoc_lab.setStyleSheet("color:%s; font-weight:bold;"
                                % C["text_secondary"])
        card_lay.addWidget(assoc_lab)
        checks = []
        for item in self._flat_ranges():
            rng = item["rng"]
            cb = QCheckBox("%s（%s）" % (
                _loc_text(self._loc, rng.get("id", "")), rng.get("id", "")))
            cb.setChecked(item["side_id"] == side.get("id"))
            card_lay.addWidget(cb)
            checks.append((cb, rng))
        card_lay.addStretch(1)

        info = {
            "side": side,
            "icon_edit": icon_edit,
            "loc_key_edit": loc_key_edit,
            "name_cn_edit": name_cn_edit,
            "checks": checks,
        }
        return card, info


    def _rebuild_side_cards(self):
        self.side_cards = []
        while self.side_holder.count():
            item = self.side_holder.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for side in self.bop.get("sides", []):
            w, info = self._make_side_card(side)
            self.side_holder.addWidget(w, 1)
            self.side_cards.append(info)

    # ------------------------------------------------------------ 动作

    def _action_blocks_for(self, action):
        key = action.get("key", "")
        if key not in self._action_blocks:
            blocks = {}
            raw = action.get("raw", "") or ""
            for bk in ("complete_effect", "visible", "available",
                       "remove_effect", "ai_will_do"):
                blocks[bk] = self._extract_direct_block(raw, bk)
            self._action_blocks[key] = blocks
        return self._action_blocks[key]


    def _extract_direct_block(self, block_text, key):
        if not block_text:
            return ""
        for k, depth, start, _end in _block_ranges(block_text):
            if depth == 1 and k == key:
                s, e = _find_block_bounds(block_text, start)
                return block_text[s:e]
        return ""


    def _populate_action_list(self):
        self.action_list.blockSignals(True)
        self.action_list.clear()
        for a in self.actions:
            cost = a.get("cost")
            delta = a.get("delta")
            parts = []
            if cost is not None:
                parts.append("费用 %s" % cost)
            if delta is not None:
                if delta == 1:
                    parts.append("↑")
                elif delta == -1:
                    parts.append("↓")
                else:
                    parts.append("%+.2f" % delta)
            value_text = "  ".join(parts) if parts else "—"
            icon = _action_icon(a.get("key", ""))
            label = "%s %s   %s" % (
                icon, _loc_text(self._loc, a.get("key", "")), value_text)
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, a.get("key", ""))
            it.setToolTip(a.get("key", ""))
            self.action_list.addItem(it)
        self.action_list.blockSignals(False)


    def _current_action(self):
        item = self.action_list.currentItem()
        if item is None:
            return None
        key = item.data(Qt.ItemDataRole.UserRole)
        for a in self.actions:
            if a.get("key") == key:
                return a
        return None


    def _on_action_changed(self, _current, _previous):
        if self._loading_action_list:
            return
        # 首次进入/程序化重建时上一个表单尚未绑定到动作，不执行同步
        if self._detail_loaded:
            self._sync_action_from_form()
        self._load_action_detail(self._current_action())
        self._detail_loaded = True


    def _load_action_detail(self, action):
        if action is None:
            self.action_key_label.setText("—")
            self.action_loc_key_edit.setText("")
            self.action_name_cn_edit.setText("")
            self.action_cost_edit.setText("")
            self._loading_detail = True
            try:
                self.action_delta_edit.setValue(0.0)
            finally:
                self._loading_detail = False
            self._delta_edited = False
            return
        self.action_key_label.setText(action.get("key", ""))
        self.action_loc_key_edit.setText(action.get("key", ""))
        self.action_name_cn_edit.setText(
            _loc_text(self._loc, action.get("key", "")))
        cost = action.get("cost")
        self.action_cost_edit.setText("" if cost is None else str(cost))
        delta = action.get("delta")
        self._loading_detail = True
        try:
            self.action_delta_edit.setValue(
                0.0 if delta is None else float(delta))
        finally:
            self._loading_detail = False
        self._delta_edited = False


    def _on_delta_changed(self, _value):
        if not self._loading_detail:
            self._delta_edited = True


    def _sync_action_from_form(self):
        action = self._current_action()
        if action is None:
            return
        cost_text = self.action_cost_edit.text().strip()
        action["cost"] = cost_text if cost_text else None
        action["delta"] = self.action_delta_edit.value()
        action["delta_edited"] = self._delta_edited
        key = action.get("key", "")
        if key:
            cn = self.action_name_cn_edit.text().strip()
            if cn:
                action["name_cn"] = cn
        blocks = self._action_blocks_for(action)
        # 默认把当前选中的块 text 保留在 blocks 字典（由 _edit_action_block 更新）


    def _new_decision(self):
        templates = ["通用（基础模板）", "限时活动（内置）", "切换类（内置）"]
        choice, ok = QInputDialog.getItem(
            self, "新建决议", "模板:", templates, 0, False)
        if not ok:
            return
        count = len(self.actions) + 1
        base = self.bop.get("id", "bop") or "bop"
        action_id = "%s_new_decision_%d" % (base, count)
        block_text = self._build_decision_template(choice, action_id)
        if not block_text:
            QMessageBox.warning(self, "模板错误", "无法生成决议模板")
            return
        parsed = _parse_decision_action(action_id, block_text, self._loc)
        parsed["raw"] = block_text
        parsed["file"] = None
        parsed["new"] = True
        self.actions.append(parsed)
        self._action_blocks[action_id] = {
            bk: self._extract_direct_block(block_text, bk)
            for bk in ("complete_effect", "visible", "available",
                       "remove_effect", "ai_will_do")
        }
        self._dirty = True
        self._loading_action_list = True
        try:
            self._populate_action_list()
            for i in range(self.action_list.count()):
                it = self.action_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == action_id:
                    self.action_list.setCurrentItem(it)
                    break
        finally:
            self._loading_action_list = False
        self._load_action_detail(parsed)
        self._detail_loaded = True


    def _build_decision_template(self, choice, action_id):
        if choice.startswith("限时"):
            return """{key} = {{
\t\tpriority = 100
\t\tdays_remove = 90
\t\tdays_re_enable = 30
\t\tcost = 25
\t\tvisible = {{
\t\t\tNOT = {{ has_country_flag = {key}_available_flag }}
\t\t}}
\t\tcomplete_effect = {{
\t\t\tset_country_flag = {key}_done_flag
\t\t\tadd_power_balance_value = {{ id = {bop_id} value = 0.1 }}
\t\t}}
\t}}""".format(key=action_id, bop_id=self.bop.get("id", ""))
        if choice.startswith("切换"):
            return """{key} = {{
\t\tpriority = 100
\t\tcost = 25
\t\tvisible = {{
\t\t\tNOT = {{ has_country_flag = {key}_toggle_flag }}
\t\t}}
\t\tcomplete_effect = {{
\t\t\tset_country_flag = {key}_toggle_flag
\t\t\tadd_power_balance_value = {{ id = {bop_id} value = -0.1 }}
\t\t}}
\t}}""".format(key=action_id, bop_id=self.bop.get("id", ""))
        # 通用：优先使用 templates/系统模板/决议/项目模板.txt
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tpl = os.path.join(root_dir, "templates", "系统模板", "决议",
                           "项目模板.txt")
        if os.path.isfile(tpl):
            try:
                with open(tpl, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    text = f.read().strip()
                m = re.search(r"^(\t*)([A-Za-z_][A-Za-z0-9_]*)\s*=",
                              text, re.MULTILINE)
                if m:
                    text = (text[:m.start(2)] + action_id + text[m.end(2):])
                return text
            except Exception:
                pass
        return """{key} = {{
\t\tpriority = 100
\t\tcost = 25
\t\tvisible = {{
\t\t}}
\t\tcomplete_effect = {{
\t\t\tadd_power_balance_value = {{ id = {bop_id} value = 0.1 }}
\t\t}}
\t}}""".format(key=action_id, bop_id=self.bop.get("id", ""))


    def _delete_action(self):
        action = self._current_action()
        if action is None:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除决议 '%s' 吗？" % action.get("key", ""))
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.actions = [a for a in self.actions
                        if a.get("key") != action.get("key")]
        self._dirty = True
        self._populate_action_list()


    def _edit_action_block(self):
        action = self._current_action()
        if action is None:
            return
        block_key = self.action_block_selector.currentData()
        if not block_key:
            return
        blocks = self._action_blocks_for(action)
        current = blocks.get(block_key, "") or ""
        if not current:
            current = "%s = {\n}" % block_key
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=current,
            block_key=block_key,
            translator=None,
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="编辑 %s - %s" % (block_key, action.get("key", "")))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            blocks[block_key] = dlg.get_block_text()
            self._dirty = True

    # ------------------------------------------------------------ 滑块



def _card(title, parent=None):
    """返回一张亮色卡片；body layout 通过 card.layout() 取用。"""
    frame = QFrame(parent)
    frame.setObjectName("BopCard")
    frame.setStyleSheet(_CARD_QSS)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(10, 8, 10, 8)
    lay.setSpacing(6)
    if title:
        cap = QLabel(title)
        cap.setObjectName("BopCardTitle")
        lay.addWidget(cap)
    return frame




def _make_scroll(widget):
    """把 widget 包进 QScrollArea。"""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(widget)
    return scroll




def _strip_icon_token(text):
    """去掉本地化文本开头的 HOI4 图标 token（如 £BoP_right_texticon）。"""
    return _ICON_TOKEN_RE.sub("", text or "").strip()




def _loc_text(loc, key):
    """返回本地化名称；无翻译回退 key。支持 $KEY$ 引用替换。"""
    if not key:
        return ""
    if loc is None:
        return key
    raw = loc.get_name(key) or ""
    if not raw:
        return key
    raw = _strip_icon_token(raw)

    def repl(m):
        ref = m.group(1)
        val = loc.get_name(ref) or ""
        return _strip_icon_token(val) if val else m.group(0)

    raw = _VAR_REF_RE.sub(repl, raw)
    return raw or key




def _fmt_modifier_value(v):
    """修正值格式化：小数值显示百分比，整数/大数保留原值。"""
    try:
        fv = float(v)
    except Exception:
        return str(v)
    if fv == 0:
        return "0"
    if abs(fv) < 1:
        return "%+.0f%%" % (fv * 100)
    return "%+.4g" % fv




def _action_icon(key):
    """按决议 key 猜测动作图标（展示用 emoji）。"""
    k = (key or "").lower()
    if "parade" in k:
        return "🎖️"
    if "slander" in k or "criticize" in k or "question" in k:
        return "🗣️"
    if "army" in k:
        return "🎯"
    if "airforce" in k or "air_force" in k:
        return "✈️"
    if "navy" in k:
        return "⚓"
    if "praise" in k:
        return "👍"
    if "ministry" in k or "foreign" in k or "justice" in k:
        return "🏛️"
    return "📜"




