"""首次使用配置向导：引导完成游戏目录 / mod 目录 / .mod 文件目录配置。

四个步骤：
1. 钢铁雄心4游戏根目录（读取本地化与图标资源）
2. 默认 mod 目录（存放 mod 内容子文件夹）
3. .mod 文件目录（存放 .mod 描述文件）
4. 打开要编辑的 mod 内容目录

完成后写入 settings.json（与主窗口格式一致），由主窗口应用并刷新界面。
"""
from project_paths import PROJECT_ROOT

import os
import json

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox)


class PathPage(QWizardPage):
    """单一路径选择页。"""

    def __init__(self, title, subtitle, placeholder, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setSubTitle(subtitle)
        self._placeholder = placeholder
        lay = QVBoxLayout(self)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(placeholder)
        lay.addWidget(self.path_edit)
        row = QHBoxLayout()
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._browse)
        row.addStretch()
        row.addWidget(browse_btn)
        lay.addLayout(row)
        self._required = title != "（可选）"

    def _browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", self.path_edit.text() or os.path.expanduser("~"))
        if directory:
            self.path_edit.setText(directory)

    def get_path(self):
        return self.path_edit.text().strip()

    def isComplete(self):
        # 允许为空（跳过该步），但空时显示提示
        return True


class SetupWizard(QWizard):
    """配置向导：收集四个路径后写 settings.json。"""

    def __init__(self, parent=None, current=None):
        super().__init__(parent)
        self.setWindowTitle("首次使用配置向导")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        current = current or {}

        self.page_hoi4 = PathPage(
            "钢铁雄心4目录", "选择游戏根目录（用于读取本地化、图标与数据字典）",
            "例如 E:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV")
        self.page_hoi4.path_edit.setText(current.get("HOI4_path", ""))
        self.addPage(self.page_hoi4)

        self.page_mods = PathPage(
            "默认 mod 目录", "存放 mod 内容子文件夹的目录（可选）",
            "例如 E:\\mods")
        self.page_mods.path_edit.setText(current.get("mod_folder_path", ""))
        self.addPage(self.page_mods)

        self.page_modfile = PathPage(
            ".mod 文件目录", "存放 .mod 描述文件的目录（可选）",
            "例如 C:\\Users\\xxx\\Documents\\Paradox Interactive\\Hearts of Iron IV\\mod")
        self.page_modfile.path_edit.setText(current.get("mod_file_path", ""))
        self.addPage(self.page_modfile)

        self.page_open = PathPage(
            "打开 mod", "选择要编辑的 mod 内容目录（可选，稍后也可在菜单中打开）",
            "例如 E:\\mods\\my_mod")
        self.page_open.path_edit.setText(current.get("mod_path", ""))
        self.addPage(self.page_open)

        self.setButtonText(QWizard.WizardButton.FinishButton, "完成")

    def get_data(self):
        return {
            "HOI4_path": self.page_hoi4.get_path(),
            "mod_folder_path": self.page_mods.get_path(),
            "mod_file_path": self.page_modfile.get_path(),
            "mod_path": self.page_open.get_path(),
        }

    def save_settings(self):
        """写 settings.json（保留原有字段）。"""
        data = self.get_data()
        settings_path = os.path.join(PROJECT_ROOT, "settings.json")
        old = {}
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            pass
        old.update({k: v for k, v in data.items() if v})
        if "ui_mode" not in old:
            old["ui_mode"] = "workbench"
        if "workbench_nofile" not in old:
            old["workbench_nofile"] = False
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(old, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
            return False
        return True
