"""快速本地化编辑小窗口

从编辑器右键菜单弹出，直接编辑某个本地化 key 的翻译。
默认简体中文；可切换 English 编辑英文翻译。
只写 mod 本地化文件，不写游戏文件。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from localisation_editor_data import (
    LANG_LABELS,
    default_mod_loc_file,
    find_mod_file_for_key,
    load_effective_dict,
    list_loc_files,
    upsert_loc_entry,
)


class QuickLocalisationEditDialog(QDialog):
    """快速本地化编辑小窗口（非模态）。"""

    def __init__(self, key: str = "", value: str = "", lang: str = "simp_chinese",
                 mod_path: str = "", hoi4_path: str = "",
                 desc_key: str = "", parent=None):
        super().__init__(parent)
        self.key = key
        self.lang = lang
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.desc_key = desc_key

        self.setWindowTitle("快速本地化编辑")
        self.setMinimumSize(520, 180)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._load_initial(value)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 语言
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(LANG_LABELS["simp_chinese"], "simp_chinese")
        self.lang_combo.addItem(LANG_LABELS["english"], "english")
        idx = self.lang_combo.findData(self.lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        form.addRow("语言:", self.lang_combo)

        # 键
        self.key_edit = QLineEdit(self.key)
        self.key_edit.setPlaceholderText("本地化键，如 focus_xxx / MODIFIER_xxx")
        form.addRow("键:", self.key_edit)

        # 值
        self.value_edit = QLineEdit()
        form.addRow(self._value_label(), self.value_edit)

        # 可选描述（仅 BOP 等需要名称+描述时传入 desc_key）
        self.desc_edit = None
        if self.desc_key:
            self.desc_edit = QLineEdit()
            self.desc_edit.setPlaceholderText("{} 描述文本".format(self.desc_key))
            form.addRow(self._desc_label(), self.desc_edit)

        # 目标文件
        self.target_label = QLabel("")
        self.target_label.setStyleSheet("color: gray;")
        form.addRow("写入:", self.target_label)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        save_btn = QPushButton("保存到 mod")
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        self._update_target_label()

    def _value_label(self):
        return "中文:" if self.lang == "simp_chinese" else "英文:"

    def _desc_label(self):
        return "描述（中文）:" if self.lang == "simp_chinese" else "描述（英文）:"

    def _on_lang_changed(self):
        self.lang = self.lang_combo.currentData() or "simp_chinese"
        # 切换语言时重新填值（mod/游戏已有译名）
        key = self.key_edit.text().strip()
        if key:
            d = load_effective_dict(self.mod_path, self.hoi4_path, self.lang)
            self.value_edit.setText(d.get(key, ""))
        if self.desc_key and self.desc_edit:
            d = load_effective_dict(self.mod_path, self.hoi4_path, self.lang)
            self.desc_edit.setText(d.get(self.desc_key, ""))
        self._update_target_label()

    def _load_initial(self, initial_value):
        key = self.key_edit.text().strip()
        if initial_value:
            self.value_edit.setText(initial_value)
        elif key:
            d = load_effective_dict(self.mod_path, self.hoi4_path, self.lang)
            self.value_edit.setText(d.get(key, ""))
        if self.desc_key and self.desc_edit:
            d = load_effective_dict(self.mod_path, self.hoi4_path, self.lang)
            self.desc_edit.setText(d.get(self.desc_key, ""))

    def _target_filepath(self):
        key = self.key_edit.text().strip()
        found = find_mod_file_for_key(self.mod_path, key, self.lang)
        if found:
            return found
        return default_mod_loc_file(self.mod_path, self.lang)

    def _update_target_label(self):
        target = self._target_filepath()
        self.target_label.setText("{}（{}）".format(
            os.path.relpath(target, self.mod_path) if self.mod_path else target,
            "已有键" if os.path.isfile(target) and
            find_mod_file_for_key(self.mod_path, self.key_edit.text().strip(), self.lang)
            else "默认文件"))

    def _on_save(self):
        key = self.key_edit.text().strip()
        value = self.value_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "错误", "键不能为空")
            return
        target = self._target_filepath()
        ok = upsert_loc_entry(target, key, value, self.lang)
        if not ok:
            QMessageBox.warning(self, "错误", "写入失败，请检查路径与文件权限。")
            return
        if self.desc_key and self.desc_edit:
            desc = self.desc_edit.text().strip()
            if desc or not find_mod_file_for_key(self.mod_path, self.desc_key, self.lang):
                upsert_loc_entry(target, self.desc_key, desc, self.lang)
        self.accept()

    def get_result(self):
        return {
            "key": self.key_edit.text().strip(),
            "value": self.value_edit.text().strip(),
            "lang": self.lang,
            "desc_key": self.desc_key or "",
            "desc_value": (self.desc_edit.text().strip()
                           if self.desc_edit else ""),
        }


def get_quick_localisation_edit_dialog(key="", value="", lang="simp_chinese",
                                       mod_path="", hoi4_path="", parent=None):
    """工厂函数：构造快速本地化编辑窗口。"""
    return QuickLocalisationEditDialog(
        key=key, value=value, lang=lang,
        mod_path=mod_path, hoi4_path=hoi4_path, parent=parent)