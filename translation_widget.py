"""
翻译树节点和翻译编辑对话框 — UI组件模块
用于在树编辑器中显示和编辑翻译、文本描述。
提供以下组件：
  - TranslationEditDialog: 翻译编辑对话框（独立弹窗）

依赖：
  - translation_editor: 翻译数据管理层
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QFormLayout
)

from translation_editor import get_translation_editor
import os


class TranslationEditDialog(QDialog):
    """
    翻译编辑对话框 — 独立弹窗
    用于编辑指定字段的翻译（名称和描述），支持：
    - 查看游戏原始翻译和mod翻译
    - 编辑后保存到mod翻译文件（mod/localisation/simp_chinese/类型文件）
    - 显示翻译来源信息（游戏/mod/新建）
    """

    def __init__(self, field_id: str, hoi4_path: str = "", mod_path: str = "",
                 mod_file_name: str = "focus_mod_l_simp_chinese.yml", parent=None):
        super().__init__(parent)
        # 要编辑的字段ID（本地化键名）
        self.field_id = field_id
        # 游戏/mod 根目录
        self.hoi4_path = hoi4_path
        self.mod_path = mod_path
        # 保存目标文件名（类型对应，如 focus_mod_l_simp_chinese.yml）
        self.mod_file_name = mod_file_name
        # 定位本地化目录（保存统一使用 HOI4 标准的 localisation 拼写）
        hoi4_loc = os.path.join(hoi4_path, "localisation", "simp_chinese") if hoi4_path else ""
        mod_loc = os.path.join(mod_path, "localisation", "simp_chinese") if mod_path else ""
        # 获取翻译编辑器单例并重新加载
        self.editor = get_translation_editor(hoi4_loc, mod_loc, mod_file_name)
        self.editor.reload()

        self.setWindowTitle(f"翻译编辑器 - {field_id}")
        self.setMinimumSize(500, 400)

        self._setup_ui()
        self._load_translation()

    def _setup_ui(self):
        """构建对话框UI"""
        layout = QVBoxLayout(self)

        # 标题 — 显示正在编辑的键名
        title_label = QLabel(f"<h3>编辑翻译: <code>{self.field_id}</code></h3>")
        layout.addWidget(title_label)

        # 翻译来源信息标签（如：来自mod/游戏/新建）
        self.source_label = QLabel("")
        layout.addWidget(self.source_label)

        # 名称编辑 — 单行文本
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("中文名称")
        form.addRow("名称:", self.name_edit)
        layout.addLayout(form)

        # 描述编辑 — 多行文本
        layout.addWidget(QLabel("描述文本:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("描述文本（如国策效果描述）")
        self.desc_edit.setMaximumHeight(150)
        layout.addWidget(self.desc_edit)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # 保存按钮
        self.save_btn = QPushButton("💾 保存到mod")
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)

        # 取消按钮 — 关闭对话框不保存
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _load_translation(self):
        """
        加载翻译数据并填充到编辑控件
        同时根据翻译来源更新状态标签
        """
        # 从翻译编辑器获取名称和描述
        name = self.editor.get_name(self.field_id)
        desc = self.editor.get_desc(self.field_id)
        in_mod = self.editor.has_in_mod(self.field_id)

        # 填充编辑控件
        self.name_edit.setText(name)
        self.desc_edit.setPlainText(desc)

        # 根据翻译来源显示不同状态信息
        if in_mod:
            # mod中已有翻译 — 绿色
            self.source_label.setText("📦 此条目的翻译来自mod文件")
            self.source_label.setStyleSheet("color: #2e7d32;")
        elif self.editor.has_in_hoi4(self.field_id):
            # 游戏原始有翻译但mod中没有 — 蓝色
            self.source_label.setText("🎮 此条目的翻译来自游戏原始文件（保存后将复制到mod）")
            self.source_label.setStyleSheet("color: #1565c0;")
        else:
            # 完全没有翻译 — 橙色，需要新建
            self.source_label.setText("❓ 此条目无原始翻译（将新建到mod文件）")
            self.source_label.setStyleSheet("color: #e65100;")

    def _save(self):
        """
        保存翻译到mod文件
        验证名称不为空，调用编辑器保存，成功后关闭对话框
        """
        name_val = self.name_edit.text().strip()
        desc_val = self.desc_edit.toPlainText().strip()

        # 验证：名称不能为空
        if not name_val:
            QMessageBox.warning(self, "错误", "名称不能为空")
            return

        # 保存单个条目的翻译
        success = self.editor.save_single_entry(self.field_id, name_val, desc_val)
        if success:
            # 通知父级（树编辑器）刷新本地化缓存并重绘国策节点
            parent = self.parent()
            if parent is not None and hasattr(parent, "translation_saved"):
                parent.translation_saved.emit(self.field_id)
            QMessageBox.information(self, "成功", "翻译已保存到mod翻译文件")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "保存翻译失败")
