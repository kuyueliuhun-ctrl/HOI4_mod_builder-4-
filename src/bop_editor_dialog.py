# -*- coding: utf-8 -*-
"""力量平衡（Balance of Power）专用工作台

批次 6：完整行内编辑表单（程序基本亮色风格，废弃深色 QSS）。

功能：
  - 平衡与区间：滑块 + 初始值；每区间卡 min/max SpinBox + modifier 键值表；
    区间增删。
  - 势力与修正：左右势力卡（图标 / 本地化键 / 中文名 / 关联区间勾选）。
  - 决议（动作）：动作列表 + 新建决议（模板：通用/限时/切换类）+ 选中项编辑
    （名称本地化双行 / 花费 / BOP 增量 / 效果结构化块）+ 删除。
  - 保存：BOP 文件与决策文件分别 ensure_file_in_mod + 原子写；本地化沿用
    upsert_loc_entry 链。

兼容旧入口/旧契约测试：保留滑块/状态标签/左右势力/决策分类编辑控件和
「动作 / 势力与修正」两个页签；「平衡与区间」作为顶部页签区展示。
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


class BopEditorDialog(QDialog):
    """力量平衡（Balance of Power）专用编辑器。"""

    def __init__(self, bop, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.bop = bop
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("Balance of Power - %s" % bop.get("tag", ""))
        self.setModal(True)
        self.resize(1040, 820)

        self._loc = self._load_loc_manager()
        self.actions = load_bop_actions(
            self.mod_path, self.hoi4_path,
            bop.get("decision_category", ""), self._loc)
        self._orig_actions = {a["key"]: dict(a) for a in self.actions}
        self._orig_range_ids = {item["rng"].get("id", "")
                                for item in self._flat_ranges()}
        self._action_blocks = {}
        self._dirty = False
        self._loading_action_list = False
        self._loading_detail = False
        self._delta_edited = False
        self._detail_loaded = False

        self._build_ui()
        self._refresh_slider_text()
        self._rebuild_range_cards()
        self._rebuild_side_cards()
        self._populate_action_list()
        self._loading_action_list = True
        try:
            if self.action_list.count() > 0:
                self.action_list.setCurrentRow(0)
                self._load_action_detail(self._current_action())
                self._detail_loaded = True
            else:
                self._load_action_detail(None)
        finally:
            self._loading_action_list = False

    # ------------------------------------------------------------ 本地化
    def _load_loc_manager(self):
        from localization_mgr import get_localization_manager
        try:
            loc = get_localization_manager()
        except Exception:
            return None
        try:
            if self.hoi4_path:
                loc.add_game_path(self.hoi4_path)
            if self.mod_path:
                loc.add_mod_path(self.mod_path)
        except Exception:
            pass
        return loc

    def _modifier_name(self, key):
        """修饰键中文名：MODIFIER_<KEY> / raw key / 英语 yml，逐级回退。"""
        if self._loc is not None:
            for cand in ("MODIFIER_" + key.upper(), key):
                try:
                    raw = self._loc.get_name(cand)
                    if raw:
                        return _strip_icon_token(raw)
                except Exception:
                    pass
        for base in (self.mod_path, self.hoi4_path):
            if not base:
                continue
            fp = os.path.join(base, "localisation", "english",
                              "modifiers_l_english.yml")
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    for line in f:
                        m = re.match(
                            r'\s*(?:MODIFIER_%s|%s)\s*:\s*"(.*)"\s*$'
                            % (re.escape(key.upper()), re.escape(key)),
                            line)
                        if m:
                            return m.group(1)
            except Exception:
                pass
        return key

    # ------------------------------------------------------------ 数据视图
    def _flat_ranges(self):
        """返回 [{rng, side_id}]，含顶层与 side 内嵌区间。"""
        out = []
        for rng in self.bop.get("ranges", []):
            out.append({"rng": rng, "side_id": None})
        for side in self.bop.get("sides", []):
            for rng in side.get("ranges", []):
                out.append({"rng": rng, "side_id": side.get("id", "")})
        return out

    def _flat_range_keys(self):
        keys = set()
        for item in self._flat_ranges():
            keys.add((item["side_id"] or "", item["rng"].get("id", "")))
        return keys

    def _current_range_by_id(self, range_id):
        for item in self._flat_ranges():
            if item["rng"].get("id") == range_id:
                return item
        return None

    # ------------------------------------------------------------ UI 构建
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = self._build_header()
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Vertical)
        top_widget = self._build_balance_page()
        splitter.addWidget(_make_scroll(top_widget))
        splitter.setStretchFactor(0, 1)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_sides_tab(), "势力与修正")
        self.tabs.addTab(self._build_actions_tab(), "决议（动作）")
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        footer = QHBoxLayout()
        edit_btn = QPushButton("✏ 编辑定义")
        edit_btn.setToolTip("打开 BOP 文件树编辑器（可编辑高级块）")
        edit_btn.clicked.connect(self._edit_bop_file)
        footer.addWidget(edit_btn)
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存修改")
        save_btn.setStyleSheet(
            "font-weight:bold; background:%s; color:#fff;"
            % C["accent"])
        save_btn.setToolTip(
            "保存 BOP 文件与决策文件（原版自动复制到 mod）")
        save_btn.clicked.connect(self._save_changes)
        footer.addWidget(save_btn)
        root.addLayout(footer)

    def _build_header(self):
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Balance of Power")
        title.setStyleSheet("font-size:20px; font-weight:bold; color:%s;"
                            % C["accent"])
        loc_name = _loc_text(self._loc, self.bop.get("id", ""))
        if loc_name and loc_name != "国家权力平衡":
            subtitle = QLabel("国家权力平衡 · %s（%s）" % (
                loc_name, self.bop.get("tag", "")))
        else:
            subtitle = QLabel("国家权力平衡 · %s" % self.bop.get("tag", ""))
        subtitle.setStyleSheet("color:%s; font-size:14px;"
                               % C["text_secondary"])
        install_context_menu(
            subtitle, self.mod_path, self.hoi4_path,
            key_provider=lambda: self.bop.get("id", "") or "",
            desc_key_provider=lambda: (
                (self.bop.get("id", "") + "_desc")
                if self.bop.get("id") else ""),
            parent=self)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        return header

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
    def _current_value(self):
        return self.slider.value() / 100.0

    def _on_initial_edit(self, value):
        self.slider.setValue(int(round(value * 100)))

    def _refresh_slider_text(self):
        v = self._current_value()
        self.value_label.setText("当前值：%+.2f" % v)
        self.initial_edit.blockSignals(True)
        self.initial_edit.setValue(round(v, 3))
        self.initial_edit.blockSignals(False)
        state = _state_label(self.bop, v)
        if state:
            self.status_label.setText("当前状态：%s" % _loc_text(self._loc, state))
        else:
            self.status_label.setText("当前状态：—")
        self._refresh_modifiers(v)

    def _refresh_modifiers(self, v=None):
        if v is None:
            v = self._current_value()
        _, rng = find_active_range(self.bop, v)
        mods = (rng or {}).get("modifier") or {}
        if mods:
            text = "当前修正：%s" % "，".join(
                "%s %s" % (self._modifier_name(k), _fmt_modifier_value(v))
                for k, v in mods.items())
        else:
            text = "当前修正：—"
        self.modifiers_label.setText(text)

    # ------------------------------------------------------------ 保存
    def _save_initial_value(self):
        """兼容旧调用：仅保存滑块初始值（实际走 _save_changes）。"""
        self._save_changes()

    def _save_changes(self):
        from bop_loader import (
            delete_bop_decision, delete_bop_range, insert_bop_decision,
            insert_bop_range, set_bop_action_block, set_bop_action_fields,
            set_bop_fields, set_bop_initial_value, set_bop_range,
            set_bop_range_modifiers, set_bop_range_side, set_bop_side_fields,
            upsert_bop_localisation,
        )
        self._sync_action_from_form()
        if not self.mod_path:
            QMessageBox.warning(self, "保存失败", "请先打开 mod 目录")
            return

        # 1) BOP 基础字段
        try:
            set_bop_initial_value(
                self.mod_path, self.hoi4_path,
                self.bop.get("id", ""), self._current_value())
            set_bop_fields(
                self.mod_path, self.hoi4_path, self.bop.get("id", ""),
                left_side=self.left_edit.text().strip(),
                right_side=self.right_edit.text().strip(),
                decision_category=self.decision_edit.text().strip())
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "BOP 基础字段保存失败：%s" % e)
            return

        # 2) side 字段与区间归属
        try:
            self._save_sides_and_ranges()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "势力/区间保存失败：%s" % e)
            return

        # 3) 决议动作
        try:
            self._save_actions()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "决议保存失败：%s" % e)
            return

        self._dirty = False
        self.bop["initial_value"] = self._current_value()
        self.bop["left_side"] = self.left_edit.text().strip()
        self.bop["right_side"] = self.right_edit.text().strip()
        self.bop["decision_category"] = self.decision_edit.text().strip()
        from bop_loader import _clear_cache
        _clear_cache()
        self.actions = load_bop_actions(
            self.mod_path, self.hoi4_path,
            self.bop.get("decision_category", ""), self._loc)
        self._orig_actions = {a["key"]: dict(a) for a in self.actions}
        self._orig_range_ids = {item["rng"].get("id", "")
                                for item in self._flat_ranges()}
        self._populate_action_list()
        self._loading_action_list = True
        try:
            if self.action_list.count() > 0:
                self.action_list.setCurrentRow(0)
                self._load_action_detail(self._current_action())
                self._detail_loaded = True
            else:
                self._load_action_detail(None)
        finally:
            self._loading_action_list = False
        QMessageBox.information(self, "已保存", "BOP 文件与决策文件已保存")

    def _save_sides_and_ranges(self):
        from bop_loader import (
            delete_bop_range, insert_bop_range, set_bop_range,
            set_bop_range_modifiers, set_bop_range_side, set_bop_side_fields,
            upsert_bop_localisation,
        )
        self._collect_range_card_data()
        bop_id = self.bop.get("id", "")
        # side 字段
        loc_entries = {}
        new_side_ids = {}
        for info in getattr(self, "side_cards", []):
            side = info["side"]
            old_id = side.get("id", "")
            new_id = info["loc_key_edit"].text().strip() or old_id
            icon = info["icon_edit"].text().strip()
            if old_id and icon:
                set_bop_side_fields(self.mod_path, self.hoi4_path, bop_id,
                                    old_id, icon=icon, loc_key=new_id)
            elif old_id and new_id != old_id:
                set_bop_side_fields(self.mod_path, self.hoi4_path, bop_id,
                                    old_id, icon=None, loc_key=new_id)
            side["id"] = new_id
            new_side_ids[old_id] = new_id
            cn = info["name_cn_edit"].text().strip()
            if cn:
                loc_entries[new_id] = cn
        # 同步 left/right 内存引用（若 side id 变了）
        for old, new in new_side_ids.items():
            if old != new:
                if self.bop.get("left_side") == old:
                    self.bop["left_side"] = new
                if self.bop.get("right_side") == old:
                    self.bop["right_side"] = new
                if self.left_edit.text().strip() == old:
                    self.left_edit.setText(new)
                if self.right_edit.text().strip() == old:
                    self.right_edit.setText(new)

        # 区间更新/新增/删除（按 range_id 追踪，side 变更走 set_bop_range_side）
        current_rids = set()
        for item in self._flat_ranges():
            rng = item["rng"]
            rid = rng.get("id", "")
            side_id = item["side_id"]
            current_rids.add(rid)
            if rid not in self._orig_range_ids:
                text = ("range = {\n"
                        "\t\tid = %s\n"
                        "\t\tmin = %s\n"
                        "\t\tmax = %s\n"
                        "\t}" % (rid, rng.get("min", -0.1),
                                 rng.get("max", 0.1)))
                insert_bop_range(self.mod_path, self.hoi4_path, bop_id,
                                 text, side_id=side_id)
                if rng.get("modifier"):
                    set_bop_range_modifiers(
                        self.mod_path, self.hoi4_path, bop_id, rid,
                        rng.get("modifier") or {})
            else:
                set_bop_range(
                    self.mod_path, self.hoi4_path, bop_id, rid,
                    min_v=rng.get("min", 0.0), max_v=rng.get("max", 0.0))
                set_bop_range_modifiers(
                    self.mod_path, self.hoi4_path, bop_id, rid,
                    rng.get("modifier") or {})
                set_bop_range_side(self.mod_path, self.hoi4_path, bop_id,
                                   rid, side_id=side_id)
        for old_rid in self._orig_range_ids:
            if old_rid not in current_rids:
                delete_bop_range(self.mod_path, self.hoi4_path, bop_id,
                                 old_rid)
        if loc_entries:
            upsert_bop_localisation(self.mod_path, loc_entries)

    def _save_actions(self):
        from bop_loader import (
            delete_bop_decision, insert_bop_decision, set_bop_action_block,
            set_bop_action_fields, upsert_bop_localisation,
        )
        category = self.decision_edit.text().strip()
        if not category:
            return
        bop_id = self.bop.get("id", "")
        current_keys = set()
        loc_entries = {}
        for action in self.actions:
            key = action.get("key", "")
            current_keys.add(key)
            cn = action.get("name_cn")
            if cn:
                loc_entries[key] = cn
            orig = self._orig_actions.get(key)
            is_new = action.get("new") or orig is None
            if is_new:
                if action.get("raw"):
                    insert_bop_decision(self.mod_path, self.hoi4_path,
                                        category, action["raw"], action_id=key)
                # 新动作也应用表单编辑
                self._apply_action_edits(
                    category, key, action, orig=None, bop_id=bop_id)
            else:
                self._apply_action_edits(
                    category, key, action, orig=orig, bop_id=bop_id)
        for old_key in self._orig_actions:
            if old_key not in current_keys:
                delete_bop_decision(self.mod_path, self.hoi4_path,
                                    category, old_key)
        if loc_entries:
            upsert_bop_localisation(self.mod_path, loc_entries)

    def _apply_action_edits(self, category, action_id, action, orig, bop_id):
        from bop_loader import (
            set_bop_action_block, set_bop_action_fields,
        )
        cost = action.get("cost")
        delta = action.get("delta")
        delta_edited = bool(action.get("delta_edited"))
        cost_changed = orig is None or (
            cost is not None and cost != orig.get("cost"))
        delta_changed = (orig is None and delta_edited) or (
            orig is not None and delta_edited
            and delta is not None and delta != orig.get("delta"))
        if cost_changed or delta_changed:
            set_bop_action_fields(
                self.mod_path, self.hoi4_path, category, action_id,
                cost=cost if cost_changed else None,
                add_power_balance_value=(
                    delta if delta_changed and delta is not None else None),
                bop_id=bop_id)
        blocks = self._action_blocks_for(action)
        if orig is not None:
            orig_blocks = self._action_blocks_for(orig)
        else:
            raw = action.get("raw", "") or ""
            orig_blocks = {
                bk: self._extract_direct_block(raw, bk)
                for bk in ("complete_effect", "visible", "available",
                           "remove_effect", "ai_will_do")
            }
        for bk, text in blocks.items():
            if text is None or text == "":
                continue
            if text != orig_blocks.get(bk, ""):
                set_bop_action_block(self.mod_path, self.hoi4_path,
                                     category, action_id, bk, text)

    # ------------------------------------------------------------ 树编辑器
    def _ensure_writable_file(self, fp):
        """确保编辑目标在 mod 内；原版文件自动复制到 mod。"""
        if not fp:
            return None, False
        fp = os.path.normpath(fp)
        if self.mod_path and os.path.normcase(fp).startswith(
                os.path.normcase(os.path.normpath(self.mod_path))):
            return fp, False
        if not self.mod_path:
            return None, False
        if self.hoi4_path:
            try:
                rel = os.path.relpath(fp, self.hoi4_path)
                if not rel.startswith(".."):
                    from state_build_ops import ensure_file_in_mod
                    mod_fp, copied = ensure_file_in_mod(
                        self.mod_path, self.hoi4_path,
                        rel.replace("\\", "/"))
                    if mod_fp:
                        return mod_fp, copied
            except Exception:
                pass
        return None, False

    def _edit_bop_file(self):
        fp = self.bop.get("file", "")
        if not fp:
            QMessageBox.warning(self, "无法编辑", "未找到 BOP 文件路径")
            return
        self._open_tree_editor_for_file(
            fp, "BOP 定义编辑 - %s" % self.bop.get("tag", ""),
            entity_id=self.bop.get("id", ""))

    def _edit_action(self, action):
        fp = action.get("file", "")
        if not fp:
            QMessageBox.warning(self, "无法编辑", "未找到动作文件路径")
            return
        self._open_tree_editor_for_file(
            fp, "动作编辑 - %s" % action.get("key", ""),
            entity_id=action.get("key", ""))

    def _open_tree_editor_for_file(self, fp, title, entity_id=None):
        """打开通用 PDX 树编辑器；原版文件先复制到 mod。"""
        mod_fp, copied = self._ensure_writable_file(fp)
        if not mod_fp:
            QMessageBox.warning(
                self, "无法编辑",
                "请先打开 mod 目录；原版文件只读，需复制到 mod 后才能编辑")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "无法编辑", "读取文件失败：%s" % e)
            return

        from tree_node import tree_from_pdx_text
        from generic_tree_editor import GenericTreeEditor
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH

        file_lines = content.splitlines()
        root = tree_from_pdx_text(content)
        editor = GenericTreeEditor(
            root_node=root,
            file_path=mod_fp,
            file_lines=file_lines,
            block_range=(1, len(file_lines) + 1),
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            loc_manager=self._loc,
            parent=self,
            title=title,
            hoi4_path=self.hoi4_path,
            mod_path=self.mod_path,
        )
        editor.show()
        if copied:
            # 原版复制到 mod 后，后续保存应指向 mod 文件
            if self.bop.get("file") and os.path.normpath(
                    self.bop["file"]) == os.path.normpath(fp):
                self.bop["file"] = mod_fp
        if entity_id:
            self._locate_entity_in_editor(editor, entity_id)

    def _locate_entity_in_editor(self, editor, entity_id):
        try:
            model = getattr(editor, "model", None)
            if model is None:
                return
            results = model.find_nodes(entity_id)
            if results:
                editor.tree_view.setCurrentIndex(results[0])
                editor.tree_view.scrollTo(results[0])
        except Exception:
            pass


def open_bop_editor(file_path, mod_path="", hoi4_path="", parent=None):
    """按文件路径打开 BOP 编辑器（文件模式/无文件模式共用）。"""
    from bop_loader import load_bop_definitions
    defs = load_bop_definitions(mod_path, hoi4_path)
    # 按文件路径匹配
    norm = os.path.normpath(file_path).replace("\\", "/")
    for bop in defs.values():
        if os.path.normpath(bop["file"]).replace("\\", "/") == norm:
            dlg = BopEditorDialog(bop, mod_path, hoi4_path, parent)
            dlg.exec()
            return True
    # 按 tag 匹配（无文件模式传入实体 key 时也可用）
    tag = os.path.splitext(os.path.basename(file_path))[0]
    bop = defs.get(tag)
    if bop is None:
        return False
    dlg = BopEditorDialog(bop, mod_path, hoi4_path, parent)
    dlg.exec()
    return True