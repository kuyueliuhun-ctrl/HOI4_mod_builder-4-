"""力量平衡（Balance of Power）专用工作台

仿游戏内「Balance of Power」弹窗风格：深色历史政治军事 UI（黑绿配色、
米白文字、金色/棕色描边），中央滑块展示当前权力平衡位置，下方动作列表
展示该 BOP 关联的决议动作。

支持：
  - 文件模式：双击 common/bop/*.txt 打开
  - 无文件模式：力量平衡实体双击打开
  - 滑块可拖动修改 initial_value，保存时原版自动复制到 mod（原子写）
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSlider,
    QVBoxLayout, QWidget,
)

from bop_loader import _state_label, load_bop_actions

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
"""


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


def _side_label(bop, side_id):
    """side id 转展示名（保留 id，后续可接本地化）。"""
    return side_id or "—"


class BopEditorDialog(QDialog):
    """力量平衡（Balance of Power）专用编辑器。"""

    def __init__(self, bop, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.bop = bop
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("Balance of Power - %s" % bop.get("tag", ""))
        self.setModal(True)
        self.resize(720, 720)
        self.setStyleSheet(_BOP_QSS)

        from localization_mgr import get_localization_manager
        try:
            loc = get_localization_manager()
        except Exception:
            loc = None
        self.actions = load_bop_actions(
            self.mod_path, self.hoi4_path,
            bop.get("decision_category", ""), loc)

        self._build_ui()
        self._refresh_slider_text()

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
        subtitle = QLabel("国家权力平衡 - %s" % self.bop.get("tag", ""))
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
        left_label = QLabel(_side_label(self.bop, self.bop.get("left_side", "")))
        left_label.setObjectName("BopSideLabel")
        right_label = QLabel(_side_label(self.bop, self.bop.get("right_side", "")))
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
        root.addLayout(slider_box)

        # 下方动作列表区
        section = QLabel("动作")
        section.setObjectName("BopSectionTitle")
        root.addWidget(section)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(4, 4, 4, 4)
        col.setSpacing(2)
        if self.actions:
            for a in self.actions:
                col.addWidget(self._make_action_row(a))
        else:
            empty = QLabel("未找到关联动作（decision_category 为空或决议文件缺失）")
            empty.setStyleSheet("color:#80756b;")
            col.addWidget(empty)
        col.addStretch(1)
        body.setLayout(col)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # 底部保存
        footer = QHBoxLayout()
        save_btn = QPushButton("💾 保存初始值")
        save_btn.setObjectName("BopSaveBtn")
        save_btn.setToolTip("把滑块当前值写回 BOP 文件（原版自动复制到 mod）")
        save_btn.clicked.connect(self._save_initial_value)
        footer.addStretch(1)
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

        name = QLabel(action.get("name", action.get("key", "")))
        name.setObjectName("BopActionName")
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

        dot = QLabel("●")
        dot.setObjectName("BopStatusDot")
        h.addWidget(dot)
        return row

    # ------------------------------------------------------------ 交互
    def _current_value(self):
        return self.slider.value() / 100.0

    def _refresh_slider_text(self):
        v = self._current_value()
        self.value_label.setText("当前值：%+.2f" % v)
        state = _state_label(self.bop, v)
        if state:
            self.status_label.setText("当前状态：%s" % state)
        else:
            self.status_label.setText("当前状态：—")

    def _save_initial_value(self):
        """保存 initial_value：原版文件自动复制到 mod，然后原子写。"""
        from write_utils import atomic_write_text
        from state_build_ops import ensure_file_in_mod

        rel = self.bop.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "保存失败", "无法定位 mod/游戏中的 BOP 文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig",
                      errors="ignore") as f:
                content = f.read()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return
        new_val = "%.4f" % self._current_value()
        new_content, n = re.subn(
            r"(\binitial_value\s*=\s*)[-0-9.]+",
            lambda m: m.group(1) + new_val,
            content, count=1)
        if n == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "保存失败", "未找到 initial_value 字段")
            return
        try:
            atomic_write_text(mod_fp, new_content)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        self.bop["file"] = mod_fp
        self.bop["initial_value"] = self._current_value()
        from PyQt6.QtWidgets import QMessageBox
        msg = "已保存 initial_value = %s" % new_val
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


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
