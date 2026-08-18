"""力量平衡（Balance of Power）专用工作台

仿游戏内「Balance of Power」弹窗风格：深色历史政治军事 UI（黑绿配色、
米白文字、金色/棕色描边），中央滑块展示当前权力平衡位置，下方动作列表
展示该 BOP 关联的决议动作。

支持：
  - 文件模式：双击 common/bop/*.txt 打开
  - 无文件模式：力量平衡实体双击打开
  - 本地化：BOP 名称 / 势力 / 区间 / 动作 / 修正名 显示中文（mod 优先）
  - 编辑：滑块 + 基础字段（left/right/decision_category）保存；
    「编辑定义」打开 BOP 文件树编辑器（势力/区间/修正完整编辑）；
    每个动作行「✏」打开对应决策文件树编辑器并定位动作
  - 修正展示：滑块下方实时显示当前区间修正；「势力与修正」页展示全部
  - 保存时原版自动复制到 mod（原子写）
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget,
)

from bop_loader import _state_label, find_active_range, load_bop_actions

_BOP_QSS = """
QDialog {
    background-color: #0a0a0a;
}
#BopTitle {
    color: #f0ebd7;
    font-size: 20px;
    font-weight: bold;
}
#BopSubtitle {
    color: #c8c3af;
    font-size: 15px;
}
#BopStatus {
    color: #f0ebd7;
    font-size: 13px;
    font-weight: bold;
}
#BopValue {
    color: #d2b446;
    font-size: 14px;
    font-weight: bold;
    font-style: italic;
}
#BopSideLabel {
    color: #c8c3af;
    font-size: 12px;
}
#BopSectionTitle {
    color: #f0ebd7;
    font-size: 14px;
    font-weight: bold;
}
#BopActionRow {
    background-color: #24281d;
    border: 1px solid #826e50;
    border-radius: 2px;
}
#BopActionRow:hover {
    background-color: #2f3526;
    border: 1px solid #64a050;
}
#BopActionName {
    color: #f0ebd7;
    font-size: 14px;
}
#BopActionValue {
    color: #d2b446;
    font-size: 14px;
    font-weight: bold;
    font-style: italic;
}
#BopActionWarn {
    color: #be3c3c;
    font-size: 14px;
    font-weight: bold;
    font-style: italic;
}
#BopStatusDot {
    color: #46a050;
    font-size: 16px;
}
#BopStatusDotOff {
    color: #504b41;
    font-size: 16px;
}
#BopCloseBtn {
    color: #ffffff;
    background-color: transparent;
    border: 1px solid #826e50;
    font-size: 14px;
    font-weight: bold;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}
#BopCloseBtn:hover {
    background-color: #3a3a3a;
}
#BopSaveBtn {
    color: #f0ebd7;
    background-color: #2f3526;
    border: 1px solid #826e50;
    font-size: 13px;
    padding: 4px 12px;
}
#BopSaveBtn:hover {
    background-color: #3d4530;
    border-color: #64a050;
}
#BopEditBtn {
    color: #f0ebd7;
    background-color: #2f3526;
    border: 1px solid #826e50;
    font-size: 13px;
    padding: 4px 12px;
}
#BopEditBtn:hover {
    background-color: #3d4530;
    border-color: #64a050;
}
#BopActionEditBtn {
    color: #f0ebd7;
    background-color: transparent;
    border: 1px solid #826e50;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
}
#BopActionEditBtn:hover {
    background-color: #3d4530;
    border-color: #64a050;
}
#BopSideSection {
    background-color: #1a1a17;
    border: 1px solid #826e50;
    border-radius: 2px;
    margin: 2px;
}
#BopSideTitle {
    color: #f0ebd7;
    font-size: 14px;
    font-weight: bold;
}
#BopRangeRow {
    background-color: #24281d;
    border: 1px solid #4a443a;
    border-radius: 2px;
}
#BopRangeName {
    color: #d2b446;
    font-size: 12px;
    font-weight: bold;
}
#BopModifierText {
    color: #c8c3af;
    font-size: 12px;
}
QScrollArea {
    border: 1px solid #826e50;
    background-color: #141210;
}
QScrollBar:vertical {
    background: #1e1c18;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #4a443a;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1e1c18;
    border: 1px solid #826e50;
}
QSlider::sub-page:horizontal {
    background: #46a050;
}
QSlider::add-page:horizontal {
    background: #1e1c18;
}
QSlider::handle:horizontal {
    width: 18px;
    margin: -7px 0;
    border-radius: 9px;
    background: #64a050;
    border: 2px solid #f0ebd7;
}
QLineEdit {
    background-color: #1e1c18;
    color: #f0ebd7;
    border: 1px solid #826e50;
    padding: 3px 6px;
    selection-background-color: #64a050;
}
QTabWidget::pane {
    border: 1px solid #826e50;
    background-color: #141210;
}
QTabBar::tab {
    background: #1e1c18;
    color: #c8c3af;
    padding: 6px 14px;
    border: 1px solid #826e50;
}
QTabBar::tab:selected {
    background: #2f3526;
    color: #f0ebd7;
}
"""


_ICON_TOKEN_RE = re.compile(r"^\s*£[^\s]*\s*")
_VAR_REF_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\$")


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
        self.resize(780, 760)
        self.setStyleSheet(_BOP_QSS)

        self._loc = self._load_loc_manager()
        self.actions = load_bop_actions(
            self.mod_path, self.hoi4_path,
            bop.get("decision_category", ""), self._loc)

        self._build_ui()
        self._refresh_slider_text()

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

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        # 顶部标题栏
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Balance of Power")
        title.setObjectName("BopTitle")
        loc_name = _loc_text(self._loc, self.bop.get("id", ""))
        if loc_name and loc_name != "国家权力平衡":
            subtitle = QLabel("国家权力平衡 · %s（%s）" % (
                loc_name, self.bop.get("tag", "")))
        else:
            subtitle = QLabel("国家权力平衡 · %s" % self.bop.get("tag", ""))
        subtitle.setObjectName("BopSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("BopCloseBtn")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        root.addLayout(header)

        # 中央滑块指标区
        slider_box = QVBoxLayout()
        self.status_label = QLabel("领袖权力巩固")
        self.status_label.setObjectName("BopStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider_box.addWidget(self.status_label)

        sides = QHBoxLayout()
        left_label = QLabel(_loc_text(self._loc, self.bop.get("left_side", "")))
        left_label.setObjectName("BopSideLabel")
        right_label = QLabel(_loc_text(self._loc, self.bop.get("right_side", "")))
        right_label.setObjectName("BopSideLabel")
        right_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        sides.addWidget(left_label)
        sides.addStretch(1)
        sides.addWidget(right_label)
        slider_box.addLayout(sides)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-100, 100)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(5)
        self.slider.setValue(
            int(round(float(self.bop.get("initial_value", 0.0)) * 100)))
        self.slider.valueChanged.connect(self._refresh_slider_text)
        slider_box.addWidget(self.slider)

        self.value_label = QLabel()
        self.value_label.setObjectName("BopValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider_box.addWidget(self.value_label)

        self.modifiers_label = QLabel("当前修正：—")
        self.modifiers_label.setObjectName("BopModifierText")
        self.modifiers_label.setWordWrap(True)
        self.modifiers_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider_box.addWidget(self.modifiers_label)

        # 基础字段编辑
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        left_cap = QLabel("左势力 ID")
        left_cap.setObjectName("BopSideLabel")
        right_cap = QLabel("右势力 ID")
        right_cap.setObjectName("BopSideLabel")
        cat_cap = QLabel("决策分类")
        cat_cap.setObjectName("BopSideLabel")
        self.left_edit = QLineEdit(self.bop.get("left_side", ""))
        self.right_edit = QLineEdit(self.bop.get("right_side", ""))
        self.decision_edit = QLineEdit(self.bop.get("decision_category", ""))
        grid.addWidget(left_cap, 0, 0)
        grid.addWidget(self.left_edit, 0, 1)
        grid.addWidget(right_cap, 0, 2)
        grid.addWidget(self.right_edit, 0, 3)
        grid.addWidget(cat_cap, 1, 0)
        grid.addWidget(self.decision_edit, 1, 1, 1, 3)
        slider_box.addLayout(grid)
        root.addLayout(slider_box)

        # 下方：动作 / 势力与修正
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # 动作页
        actions_tab = QWidget()
        actions_col = QVBoxLayout(actions_tab)
        actions_col.setContentsMargins(4, 4, 4, 4)
        actions_col.setSpacing(2)
        if self.actions:
            for a in self.actions:
                actions_col.addWidget(self._make_action_row(a))
        else:
            empty = QLabel("未找到关联动作（decision_category 为空或决议文件缺失）")
            empty.setStyleSheet("color:#80756b;")
            actions_col.addWidget(empty)
        actions_col.addStretch(1)
        self.tabs.addTab(actions_tab, "动作")

        # 势力与修正页
        sides_tab = QWidget()
        sides_col = QVBoxLayout(sides_tab)
        sides_col.setContentsMargins(4, 4, 4, 4)
        sides_col.setSpacing(4)
        bop_sides = self.bop.get("sides", [])
        if bop_sides:
            for side in bop_sides:
                sides_col.addWidget(self._make_side_section(side))
        else:
            empty = QLabel("未解析到 side 块")
            empty.setStyleSheet("color:#80756b;")
            sides_col.addWidget(empty)
        sides_col.addStretch(1)
        self.tabs.addTab(sides_tab, "势力与修正")

        # 底部保存
        footer = QHBoxLayout()
        edit_btn = QPushButton("✏ 编辑定义")
        edit_btn.setObjectName("BopEditBtn")
        edit_btn.setToolTip("打开 BOP 文件树编辑器（可编辑势力/区间/修正）")
        edit_btn.clicked.connect(self._edit_bop_file)
        footer.addWidget(edit_btn)
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存修改")
        save_btn.setObjectName("BopSaveBtn")
        save_btn.setToolTip(
            "保存滑块当前值及左/右势力、决策分类（原版自动复制到 mod）")
        save_btn.clicked.connect(self._save_changes)
        footer.addWidget(save_btn)
        root.addLayout(footer)

    def _make_action_row(self, action):
        row = QWidget()
        row.setObjectName("BopActionRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(10)

        icon = QLabel(_action_icon(action.get("key", "")))
        icon.setStyleSheet("font-size:20px; color:#f0ebd7;")
        h.addWidget(icon)

        name = QLabel(_loc_text(self._loc, action.get("key", "")))
        name.setObjectName("BopActionName")
        name.setToolTip(action.get("key", ""))
        h.addWidget(name, 1)

        cost = action.get("cost")
        delta = action.get("delta")
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
        value_text = "  ".join(parts)
        value = QLabel(value_text if value_text else "—")
        value.setObjectName(
            "BopActionWarn" if (delta is not None and delta < 0)
            else "BopActionValue")
        h.addWidget(value)

        edit_btn = QPushButton("✏")
        edit_btn.setObjectName("BopActionEditBtn")
        edit_btn.setToolTip("编辑动作（打开决策文件树编辑器）")
        edit_btn.clicked.connect(
            lambda checked=False, a=action: self._edit_action(a))
        h.addWidget(edit_btn)

        dot = QLabel("●")
        dot.setObjectName("BopStatusDot")
        h.addWidget(dot)
        return row

    def _make_side_section(self, side):
        box = QWidget()
        box.setObjectName("BopSideSection")
        v = QVBoxLayout(box)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        raw_id = side.get("id", "")
        title = QLabel("%s  %s" % (_loc_text(self._loc, raw_id), raw_id))
        title.setObjectName("BopSideTitle")
        v.addWidget(title)
        for rng in side.get("ranges", []):
            v.addWidget(self._make_range_row(rng))
        return box

    def _make_range_row(self, rng):
        row = QWidget()
        row.setObjectName("BopRangeRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(8)
        name = QLabel("%s  [%+.2f ~ %+.2f]" % (
            _loc_text(self._loc, rng.get("id", "")),
            float(rng.get("min", 0.0)), float(rng.get("max", 0.0))))
        name.setObjectName("BopRangeName")
        h.addWidget(name)
        mods = rng.get("modifier") or {}
        if mods:
            mod_text = "，".join(
                "%s %s" % (self._modifier_name(k), _fmt_modifier_value(v))
                for k, v in mods.items())
        else:
            mod_text = "无修正"
        mod_label = QLabel(mod_text)
        mod_label.setObjectName("BopModifierText")
        mod_label.setWordWrap(True)
        h.addWidget(mod_label, 1)
        return row

    # ------------------------------------------------------------ 交互
    def _current_value(self):
        return self.slider.value() / 100.0

    def _refresh_slider_text(self):
        v = self._current_value()
        self.value_label.setText("当前值：%+.2f" % v)
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
        """保存基础字段：initial_value / left_side / right_side / decision_category。"""
        from write_utils import atomic_write_text
        from state_build_ops import ensure_file_in_mod

        rel = self.bop.get("rel", "")
        if not rel:
            QMessageBox.warning(self, "保存失败", "无法定位 BOP 文件相对路径")
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 mod/游戏中的 BOP 文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return

        replacements = {
            "initial_value": "%.4f" % self._current_value(),
            "left_side": self.left_edit.text().strip(),
            "right_side": self.right_edit.text().strip(),
            "decision_category": self.decision_edit.text().strip(),
        }
        new_content = content
        n = 0
        for field, val in replacements.items():
            if field == "initial_value":
                pattern = r"(\binitial_value\s*=\s*)[-0-9.]+"
            else:
                pattern = r"(\b%s\s*=\s*)[^\s#]+" % re.escape(field)
            new_content, cnt = re.subn(
                pattern, lambda m: m.group(1) + val, new_content, count=1)
            n += cnt
        if n == 0:
            QMessageBox.warning(self, "保存失败", "未找到任何可保存的 BOP 字段")
            return
        try:
            atomic_write_text(mod_fp, new_content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return

        self.bop["file"] = mod_fp
        self.bop["initial_value"] = self._current_value()
        self.bop["left_side"] = replacements["left_side"]
        self.bop["right_side"] = replacements["right_side"]
        self.bop["decision_category"] = replacements["decision_category"]

        msg = "已保存 BOP 修改（%d 个字段）" % n
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)

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
            if self.bop.get("file") and os.path.normpath(self.bop["file"]) == os.path.normpath(fp):
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
