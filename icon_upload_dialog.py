"""图标上传/新建对话框模块

提供 IconUploadDialog：为指定国策选择本地图片文件并上传为新图标。
上传时生成 mod 的 goals 目录资源（{名称}.dds / {名称}_shine.dds）、
更新 interface/goals_mod.gfx 与 goals_shine_mod.gfx，并设置国策 icon 字段。
"""

import os
import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap


class IconUploadDialog(QDialog):
    """上传/新建国策图标对话框：选择图片文件、指定图标名并预览。"""

    def __init__(self, focus_id, parent=None):
        super().__init__(parent)
        self.focus_id = focus_id
        self.image_path = None
        self.icon_name = focus_id

        self.setWindowTitle(f"上传图标 - {focus_id}")
        self.setMinimumSize(440, 400)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tip = QLabel(
            f"为国策 <b>{self.focus_id}</b> 上传新图标。<br>"
            f"将生成 <code>GFX_goal_{self.focus_id}</code> 及对应的 .dds 资源，并自动更新国策的 icon 字段。"
        )
        tip.setWordWrap(True)
        layout.addWidget(tip)

        form = QFormLayout()

        # 图片文件选择
        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择图片文件（png/jpg/bmp/dds/tga）...")
        self.path_edit.textChanged.connect(self._preview)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(self.path_edit)
        file_row.addWidget(browse_btn)
        form.addRow("图片:", file_row)

        # 图标名（默认使用国策ID）
        self.name_edit = QLineEdit(self.focus_id)
        self.name_edit.setPlaceholderText("图标资源名（默认使用国策ID）")
        form.addRow("图标名:", self.name_edit)
        layout.addLayout(form)

        # 预览
        self.preview_label = QLabel("")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setStyleSheet(
            "QLabel { border: 1px dashed #5d6b7a; color: #5d6b7a; background: #f4f7fa; border-radius: 8px; }"
        )
        layout.addWidget(self.preview_label, 1)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("上传")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.dds *.tga);;所有文件 (*.*)",
        )
        if path:
            self.path_edit.setText(path)

    def _preview(self):
        path = self.path_edit.text().strip()
        if not path or not os.path.isfile(path):
            self.preview_label.setText("选择图片后此处预览")
            return
        pm = None
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".dds":
                from dds_loader import DdsLoader
                pm = DdsLoader.load_as_pixmap(path)
            else:
                pm = QPixmap(path)
        except Exception:
            pm = None
        if pm is None or pm.isNull():
            self.preview_label.setText("无法预览该图片")
            return
        scaled = pm.scaled(
            160, 160,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def _on_ok(self):
        path = self.path_edit.text().strip()
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "错误", "请先选择一张图片文件")
            return
        name = self.name_edit.text().strip()
        if not name:
            name = self.focus_id
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            QMessageBox.warning(self, "错误", "图标名只能包含字母、数字、下划线，且不能以数字开头")
            return
        self.image_path = path
        self.icon_name = name
        self.accept()

    def get_selection(self):
        """返回 (图片文件路径, 图标资源名)；取消返回 (None, None)。"""
        return self.image_path, self.icon_name
