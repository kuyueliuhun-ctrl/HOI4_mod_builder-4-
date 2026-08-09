"""AI 效果提示词对话框模块

提供 AIPromptDialog 类：
1. 生成带格式的 AI 提示词文本（基于效果器/触发器词条）
2. 支持复制提示词到其他 AI 工具
3. 粘贴 AI 回复后自动解析并预览回填内容
4. 确认后通过回调将解析结果应用到程序
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ai_prompt import (
    build_prompt_for_file, build_prompt_for_project, parse_ai_reply,
)
from term_registry import get_term_registry


class AIPromptDialog(QDialog):
    """AI 效果提示词对话框 - 非模态

    使用步骤：
    1. 生成提示词（默认基于当前文件/项目）
    2. 点击「复制提示词」粘贴到其他 AI 创作
    3. AI 回复后粘贴到回复框
    4. 点击「解析并预览」查看回填内容
    5. 点击「填入程序」应用（通过 fill_callback 回调）
    """

    # 信号：解析出的块列表
    blocks_parsed = pyqtSignal(list)

    def __init__(self, file_path="", mod_path="", scope="当前文件",
                 fill_callback=None, parent=None):
        """初始化对话框

        Args:
            file_path (str): 当前文件路径（为当前文件生成时使用）
            mod_path (str): mod 目录（为整个项目生成时使用）
            scope (str): 提示词范围说明
            fill_callback (callable): 回填回调，接收 blocks 列表
            parent (QWidget): 父窗口
        """
        super().__init__(parent)
        self.file_path = file_path
        self.mod_path = mod_path
        self.scope = scope
        self.fill_callback = fill_callback
        self._parsed_blocks = []

        self.setWindowTitle("AI 效果提示词")
        self.setMinimumSize(680, 640)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._generate()

    def _setup_ui(self):
        """构建 UI 布局。"""
        layout = QVBoxLayout(self)

        # ── 词条类型筛选 ──
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("词条类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部（块+值）", "")
        self.type_combo.addItem("仅块", "block")
        self.type_combo.addItem("仅值", "value")
        self.type_combo.currentIndexChanged.connect(self._generate)
        top_row.addWidget(self.type_combo)
        top_row.addStretch()
        layout.addLayout(top_row)

        # ── 提示词预览 ──
        layout.addWidget(QLabel("📋 提示词（复制到其他 AI 使用）:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setReadOnly(True)
        layout.addWidget(self.prompt_edit)

        # ── 提示词操作按钮 ──
        prompt_btns = QHBoxLayout()
        copy_btn = QPushButton("📋 复制提示词")
        copy_btn.clicked.connect(self._copy_prompt)
        regen_btn = QPushButton("🔄 重新生成")
        regen_btn.clicked.connect(self._generate)
        prompt_btns.addWidget(copy_btn)
        prompt_btns.addWidget(regen_btn)
        prompt_btns.addStretch()
        layout.addLayout(prompt_btns)

        # ── AI 回复输入 ──
        layout.addWidget(QLabel("💬 粘贴 AI 回复（按约定格式输出）:"))
        self.reply_edit = QTextEdit()
        self.reply_edit.setPlaceholderText(
            "将其他 AI 的回复粘贴到这里，然后点击「解析并预览」…")
        layout.addWidget(self.reply_edit)

        # ── 解析与回填按钮 ──
        action_btns = QHBoxLayout()
        parse_btn = QPushButton("🔍 解析并预览")
        parse_btn.clicked.connect(self._parse_reply)
        self.fill_btn = QPushButton("✅ 填入程序")
        self.fill_btn.clicked.connect(self._do_fill)
        self.fill_btn.setEnabled(False)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        action_btns.addWidget(parse_btn)
        action_btns.addWidget(self.fill_btn)
        action_btns.addStretch()
        action_btns.addWidget(close_btn)
        layout.addLayout(action_btns)

        # ── 预览区 ──
        layout.addWidget(QLabel("解析结果预览:"))
        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setMaximumHeight(180)
        layout.addWidget(self.preview_edit)

    def _generate(self):
        """根据当前选择重新生成提示词。"""
        term_type = self.type_combo.currentData()
        registry = get_term_registry()
        if self.scope == "整个项目" and self.mod_path:
            prompt = build_prompt_for_project(
                self.mod_path, node_type=term_type, registry=registry)
        else:
            prompt = build_prompt_for_file(
                self.file_path or "", node_type=term_type, registry=registry)
        self.prompt_edit.setPlainText(prompt)

    def _copy_prompt(self):
        """复制提示词到剪贴板。"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.prompt_edit.toPlainText())
        QMessageBox.information(self, "已复制", "提示词已复制到剪贴板，粘贴到其他 AI 使用。")

    def _parse_reply(self):
        """解析 AI 回复并显示预览。"""
        reply = self.reply_edit.toPlainText().strip()
        if not reply:
            QMessageBox.warning(self, "提示", "请先粘贴 AI 回复")
            return
        blocks = parse_ai_reply(reply)
        self._parsed_blocks = blocks

        if not blocks:
            self.preview_edit.setPlainText("未解析到任何内容。")
            self.fill_btn.setEnabled(False)
            return

        lines = [f"共解析到 {len(blocks)} 个块:"]
        for i, b in enumerate(blocks):
            kind_name = {"focus": "国策块", "effect": "效果块",
                         "trigger": "触发块"}.get(b["kind"], b["kind"])
            lines.append(f"{i + 1}. [{kind_name}] 目标: {b['target']}")
            lines.append(f"   内容:\n{self._indent(b['content'])}")
        self.preview_edit.setPlainText("\n".join(lines))
        self.fill_btn.setEnabled(True)
        self.blocks_parsed.emit(blocks)

    @staticmethod
    def _indent(text, prefix="   "):
        """缩进多行文本。"""
        return "\n".join(prefix + line for line in text.splitlines())

    def _do_fill(self):
        """确认回填：调用外部回调。"""
        if not self._parsed_blocks:
            QMessageBox.warning(self, "提示", "请先解析 AI 回复")
            return
        if self.fill_callback:
            try:
                self.fill_callback(self._parsed_blocks)
                QMessageBox.information(
                    self, "已填入",
                    f"已将 {len(self._parsed_blocks)} 个块填入程序。")
            except Exception as e:
                QMessageBox.critical(self, "填入失败", f"填入时出错: {e}")
        else:
            QMessageBox.information(
                self, "提示", "未设置回填目标。请在相应编辑器中打开后使用。")
