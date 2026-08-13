"""国策树基本信息编辑对话框模块

提供 TreeInfoDialog 和 TreeHeaderEditor 两个类，
用于编辑国策树文件的头部信息（如 ID、国家条件、连续焦点坐标、共享焦点等）。

TreeInfoDialog: 表单式的基本信息编辑对话框。
TreeHeaderEditor: 基于 GenericTreeEditor 的树状结构编辑器，用于更灵活地编辑头部字段。
"""

import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QGroupBox,
    QListWidget, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from generic_tree_editor import GenericTreeEditor
from tree_node import TreeNode, parse_pdx_block_to_tree


class TreeInfoDialog(QDialog):
    """编辑树基本信息对话框 - 非模态

    提供表单式界面编辑国策树头部信息，包括：
    - 基本标识：ID、默认值
    - 连续焦点坐标：continuous_focus_position
    - 国家条件：country 块
    - 共享焦点引用：shared_focus 列表
    - 其他顶层字段

    保存时会重新构建 focus_tree = { ... } 头部结构并写入文件。

    Attributes:
        file_path (str): 编辑的文件路径
        header_lines (list[str]): 文件头部行（解析后）
        child_blocks (list): 子块数据（国策树的各个 focus 块）
        insert_pos (int): 插入位置
        fields (dict): 解析出的字段数据
    """

    # 信号：保存成功后通知外部刷新
    info_saved = pyqtSignal()

    def __init__(self, file_path, parent=None):
        """初始化基本信息编辑对话框

        Args:
            file_path (str): 要编辑的国策树文件路径
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle("编辑树基本信息")
        self.setMinimumSize(500, 500)
        # 非模态窗口
        self.setWindowModality(Qt.WindowModality.NonModal)

        # 解析后的文件结构数据
        self.header_lines = []   # 头部行列表
        self.child_blocks = []   # 国策子块数据
        self.insert_pos = 0      # 插入位置
        self.fields = {}         # 字段缓存

        self._setup_ui()
        self._load_file()

    def _setup_ui(self):
        """构建 UI 界面

        布局结构：
        1. 基本信息组（ID、默认值、连续焦点坐标）
        2. 国家条件组（QTextEdit 编辑 country 块）
        3. 共享焦点引用组（QListWidget + 增删按钮）
        4. 其他字段组（QTextEdit 自由编辑）
        5. 底部按钮（关闭 / 保存）
        """
        layout = QVBoxLayout(self)

        # ── 基本信息组 ──
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("例如: usa_focus")
        basic_layout.addRow("ID:", self.id_edit)

        self.default_edit = QLineEdit()
        self.default_edit.setPlaceholderText("yes / no")
        basic_layout.addRow("默认:", self.default_edit)

        self.pos_x_edit = QLineEdit()
        self.pos_x_edit.setPlaceholderText("0")
        basic_layout.addRow("连续焦点 X:", self.pos_x_edit)

        self.pos_y_edit = QLineEdit()
        self.pos_y_edit.setPlaceholderText("0")
        basic_layout.addRow("连续焦点 Y:", self.pos_y_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # ── 国家条件组 ──
        country_group = QGroupBox("国家条件")
        country_layout = QVBoxLayout()
        self.country_text = QTextEdit()
        self.country_text.setPlaceholderText("country = {\n    factor = 0\n    modifier = {\n        add = 10\n        tag = USA\n    }\n}")
        self.country_text.setMinimumHeight(120)
        country_layout.addWidget(self.country_text)
        country_group.setLayout(country_layout)
        layout.addWidget(country_group)

        # ── 共享焦点引用组 ──
        shared_group = QGroupBox("共享焦点引用")
        shared_layout = QVBoxLayout()
        self.shared_list = QListWidget()
        shared_layout.addWidget(self.shared_list)

        shared_btn_layout = QHBoxLayout()
        add_shared_btn = QPushButton("添加")
        add_shared_btn.clicked.connect(self._add_shared_focus)
        del_shared_btn = QPushButton("删除")
        del_shared_btn.clicked.connect(self._del_shared_focus)
        shared_btn_layout.addWidget(add_shared_btn)
        shared_btn_layout.addWidget(del_shared_btn)
        shared_layout.addLayout(shared_btn_layout)
        shared_group.setLayout(shared_layout)
        layout.addWidget(shared_group)

        # ── 其他字段组（自由编辑） ──
        other_group = QGroupBox("其他字段")
        other_layout = QVBoxLayout()
        self.other_text = QTextEdit()
        self.other_text.setPlaceholderText("其他顶层字段（每行一个）")
        self.other_text.setMinimumHeight(80)
        other_layout.addWidget(self.other_text)
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)

        # ── 按钮行 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("保存")
        ok_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _load_file(self):
        """加载并解析文件头部信息

        使用 focus_parser.parse_tree_header 解析文件结构，
        将头部行和子块数据分离，然后调用 _parse_header 填充表单字段。
        """
        from focus_parser import parse_tree_header
        try:
            result = parse_tree_header(self.file_path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"解析文件失败: {e}")
            return

        self.header_lines = result['header_lines']
        self.child_blocks = result['child_blocks']
        self.insert_pos = result['insert_pos']

        # 将头部行合并为文本，解析填充到表单
        header_text = '\n'.join(self.header_lines)
        self._parse_header(header_text)

    def _parse_header(self, text):
        """解析头部 PDX 文本并填充表单控件

        从头部文本中提取：
        - id 字段
        - default 字段
        - continuous_focus_position（x, y）
        - country 块（使用花括号匹配）
        - shared_focus 引用
        - 其他未知字段

        Args:
            text (str): 头部 PDX 文本
        """
        # 过滤掉空的块起始行（如 "focus_tree = {" "shared_focus_tree = {"），
        # 因为这些是解析器产生的容器行，不是实际数据
        filtered_lines = []
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped.endswith('{') and '=' in stripped:
                key_name = stripped.split('=')[0].strip()
                # 跳过容器类型的空块
                if key_name in ('focus_tree', 'shared_focus_tree'):
                    continue
            filtered_lines.append(line)
        text = '\n'.join(filtered_lines)

        # ── 提取 id ──
        id_match = re.search(r'^\s*id\s*=\s*(.+)$', text, re.MULTILINE)
        if id_match:
            self.id_edit.setText(id_match.group(1).strip().strip('"'))

        # ── 提取 default ──
        default_match = re.search(r'^\s*default\s*=\s*(.+)$', text, re.MULTILINE)
        if default_match:
            self.default_edit.setText(default_match.group(1).strip().strip('"'))

        # ── 提取 continuous_focus_position ──
        pos_match = re.search(r'continuous_focus_position\s*=\s*\{\s*x\s*=\s*(\d+)\s+y\s*=\s*(\d+)', text)
        if pos_match:
            self.pos_x_edit.setText(pos_match.group(1))
            self.pos_y_edit.setText(pos_match.group(2))

        # ── 提取 country 块（使用花括号深度匹配） ──
        country_ranges = []  # 记录 country 块在文本中的起止位置
        country_match = re.search(r'country\s*=\s*\{', text)
        if country_match:
            start = country_match.start()
            depth = 0
            end = start
            # 花括号深度匹配：找到配对的闭合花括号
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:  # 回到最外层，匹配结束
                        end = i + 1
                        break
            self.country_text.setPlainText(text[start:end])
            country_ranges.append((start, end))

        # 辅助函数：判断某个位置是否在 country 块内
        def in_country(pos):
            for s, e in country_ranges:
                if s <= pos < e:
                    return True
            return False

        # ── 提取 shared_focus ──
        shared_matches = re.findall(r'^\s*shared_focus\s*=\s*(.+)$', text, re.MULTILINE)
        for sm in shared_matches:
            self.shared_list.addItem(sm.strip().strip('"'))

        # ── 提取其他未知字段 ──
        known_keys = {'id', 'default', 'continuous_focus_position', 'country', 'shared_focus'}
        other_lines = []
        for line in text.split('\n'):
            stripped = line.strip()
            # 跳过空行和注释
            if not stripped or stripped.startswith('#'):
                continue
            line_start = text.find(line)
            # 跳过 country 块内的行
            if in_country(line_start):
                continue
            # 检查是否为已知字段
            is_known = False
            for key in known_keys:
                if stripped.startswith(key + ' ') or stripped.startswith(key + '='):
                    is_known = True
                    break
            if not is_known:
                other_lines.append(stripped)
        if other_lines:
            self.other_text.setPlainText('\n'.join(other_lines))

    def _add_shared_focus(self):
        """添加共享焦点引用

        弹出输入对话框让用户输入共享焦点 ID，
        验证非空后添加到列表控件。
        """
        name, ok = QInputDialog.getText(self, "添加共享焦点", "输入共享焦点 ID:")
        if ok and name.strip():
            self.shared_list.addItem(name.strip())

    def _del_shared_focus(self):
        """删除选中的共享焦点引用"""
        row = self.shared_list.currentRow()
        if row >= 0:
            self.shared_list.takeItem(row)

    def _on_save(self):
        """保存基本信息到文件

        流程：
        1. 构建新的头部字段
        2. 拼接子块数据
        3. 添加闭合花括号
        4. 写入文件（UTF-8 with BOM）
        """
        new_header_fields = self._build_header_fields()
        if new_header_fields is None:
            return

        try:
            lines = new_header_fields
            # 追加子块数据（国策树的各个 focus 块）
            for block in self.child_blocks:
                lines.extend(block)
            # 闭合 focus_tree = { 的花括号
            lines.append("}")

            output = '\n'.join(lines) + '\n'
            with open(self.file_path, 'w', encoding='utf-8', newline="") as f:
                f.write(output)

            self.info_saved.emit()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入文件时出错: {e}")

    def _build_header_fields(self):
        """根据表单内容构建新的头部 PDX 文本行列表

        构建顺序：
        1. focus_tree = {
        2. id
        3. country（含缩进）
        4. continuous_focus_position
        5. shared_focus（可多个）
        6. default
        7. 其他字段

        Returns:
            list[str]: PDX 格式的头部行列表
        """
        lines = []

        # 包装起始
        lines.append("focus_tree = {")

        # id 字段
        id_val = self.id_edit.text().strip()
        if id_val:
            lines.append(f"    id = {id_val}")

        # country 块（保持原有缩进格式）
        country_text = self.country_text.toPlainText().strip()
        if country_text:
            for line in country_text.split('\n'):
                lines.append(f"    {line.strip()}")

        # 连续焦点坐标
        pos_x = self.pos_x_edit.text().strip()
        pos_y = self.pos_y_edit.text().strip()
        if pos_x and pos_y:
            lines.append(f"    continuous_focus_position = {{ x = {pos_x} y = {pos_y} }}")

        # 共享焦点引用（可能多个）
        for i in range(self.shared_list.count()):
            sf = self.shared_list.item(i).text().strip()
            if sf:
                lines.append(f"    shared_focus = {sf}")

        # 默认值
        default_val = self.default_edit.text().strip()
        if default_val:
            lines.append(f"    default = {default_val}")

        # 其他顶层字段
        other_text = self.other_text.toPlainText().strip()
        if other_text:
            for line in other_text.split('\n'):
                if line.strip():
                    lines.append(f"    {line.strip()}")

        return lines


class TreeHeaderEditor(GenericTreeEditor):
    """国策树基本信息编辑器 - 非模态

    继承自 GenericTreeEditor，提供一个基于树状结构的头部编辑器。
    相比 TreeInfoDialog 的表单式编辑，这个编辑器更灵活，
    可以以树视图的方式编辑 focus_tree 头部中的所有字段。

    重写了 _get_wrapper_start 和 _save 方法以适配头部编辑的格式需求。
    """

    def __init__(self, file_path, translator=None, parent=None, loc_manager=None):
        """初始化头部树编辑器

        Args:
            file_path (str): 要编辑的国策树文件路径
            translator (GuiTranslator, optional): 翻译器实例
            parent (QWidget, optional): 父窗口
            loc_manager (optional): 本地化管理器
        """
        from focus_parser import parse_tree_header

        # 解析文件头部结构
        result = parse_tree_header(file_path)
        header_lines = result['header_lines']
        self._child_blocks = result['child_blocks']  # 国策子块数据，保存时不修改

        # 读取完整文件内容
        with open(file_path, 'r', encoding="utf-8-sig") as f:
            self._file_lines = f.read().splitlines()

        # 将头部文本解析为树节点结构
        # 去除头尾的 focus_tree = { 和 } 包装层，避免保存时嵌套
        header_lines_clean = list(header_lines)
        if header_lines_clean and re.match(r'^\s*(?:focus_tree|shared_focus_tree)\s*=\s*\{\s*$', header_lines_clean[0]):
            header_lines_clean = header_lines_clean[1:]
        while header_lines_clean and header_lines_clean[-1].strip() == '}':
            header_lines_clean = header_lines_clean[:-1]
        header_text = '\n'.join(header_lines_clean)
        if header_text.strip():
            root_node = parse_pdx_block_to_tree(header_text, "focus_tree")
        else:
            root_node = TreeNode("block", "focus_tree")

        # 调用父类初始化，block_range 设为 (1, 1) 因为我们重写了 _save
        super().__init__(
            root_node=root_node,
            file_path=file_path,
            file_lines=self._file_lines,
            block_range=(1, 1),
            translator=translator,
            loc_manager=loc_manager,
            parent=parent,
            title="编辑树基本信息"
        )

    def _get_wrapper_start(self, indent):
        """获取头部的包装起始行

        重写父类方法，使用 focus_tree = { 作为起始包装。

        Args:
            indent (str): 缩进字符串

        Returns:
            str: 包装起始行
        """
        return "focus_tree = {"

    def _save(self):
        """保存头部编辑结果

        与父类 _save 不同，这里不依赖 block_range，
        而是完全重建整个文件内容：头部 + 子块 + 闭合花括号。
        """
        try:
            # 序列化头部字段
            inner_lines = self._serialize_children(self.root_node, indent=1)
            # 收集所有子块（不修改的内容）
            child_lines = []
            for block in self._child_blocks:
                child_lines.extend(block)

            # 拼接完整文件
            output_lines = ["focus_tree = {"] + inner_lines + child_lines + ["}"]
            output = "\n".join(output_lines) + "\n"
            with open(self.file_path, "w", encoding="utf-8", newline="") as f:
                f.write(output)
            # 发送保存成功信号
            self.tree_saved.emit()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入文件时出错: {e}")
