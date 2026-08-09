"""
新建 mod 项目对话框 — 非模态交互窗口
用于创建 HOI4 模组的基础文件结构，包括：
  - .mod 文件（mod描述文件，写入 .mod 文件目录）
  - descriptor.mod（mod内部描述，写入 mod 内容目录）
  - interface/*.gfx（空白GFX精灵定义）
  - localisation/simp_chinese/*.yml（空白本地化文件）

目录约定：
  - 默认 mod 目录（mod_folder_path）：存放 mod 内容子文件夹，每个子文件夹包含 mod 的所有文件
  - .mod 文件目录（mod_file_path）：只存放 .mod 描述文件

通过 pyqtSignal 通知外部模块 mod 创建成功，传递创建的 mod 路径。
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QMessageBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal


# 可选的mod标签列表（对应Steam Workshop的分类标签）
TAG_OPTIONS = [
    "Alternative History", "Balance", "Events", "Fixes", "Gameplay",
    "Historical", "Graphics", "Map", "Ideologies", "Military",
    "National Focuses", "Sound", "Technologies", "Translation", "Utilities",
]

# 最多可选择的标签数量（HOI4规范限制）
MAX_TAGS = 10
# 文件夹名称正则：仅允许字母、数字、下划线、连字符
FOLDER_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


class ModCreatorDialog(QDialog):
    """
    新建 mod 项目对话框 — 非模态
    非模态窗口意味着用户可以在对话框打开的同时操作主界面。
    通过 mod_created 信号将创建结果传递给外部监听者。
    """

    # 信号：mod创建成功后通知外部 — 传递创建的mod完整路径
    mod_created = pyqtSignal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        # 应用程序设置（含HOI4_path和mod_folder_path）
        self.settings = settings
        self.setWindowTitle("新建 mod 项目")
        self.setMinimumSize(480, 500)
        # 非模态窗口 — 不阻塞主界面
        self.setWindowModality(Qt.WindowModality.NonModal)

        # 存储所有标签勾选框的引用
        self.tag_checkboxes = []
        self._setup_ui()

    def _setup_ui(self):
        """构建对话框UI"""
        layout = QVBoxLayout(self)

        # ========== 路径状态栏 ==========
        # 显示 HOI4 目录和 Mod 目录的配置状态
        path_status = QFrame()
        path_status.setFrameShape(QFrame.Shape.StyledPanel)
        path_layout = QHBoxLayout(path_status)
        path_layout.setContentsMargins(8, 4, 8, 4)

        hoi4_ok = bool(self.settings.get("HOI4_path"))
        modfolder_ok = bool(self.settings.get("mod_folder_path"))
        modfile_ok = bool(self.settings.get("mod_file_path"))
        status_text = []
        status_text.append("HOI4目录: " + ("已配置" if hoi4_ok else "未配置"))
        status_text.append("默认mod目录: " + ("已配置" if modfolder_ok else "未配置"))
        status_text.append(".mod文件目录: " + ("已配置" if modfile_ok else "未配置"))
        label = QLabel("  |  ".join(status_text))
        # 如果路径未配置完全，用红色提醒用户
        if not (hoi4_ok and modfolder_ok and modfile_ok):
            label.setStyleSheet("color: red;")
        path_layout.addWidget(label)
        layout.addWidget(path_status)

        # ========== 表单区域 ==========
        # 包含模组名称、文件夹名称、支持版本三个必填项
        form_layout = QGridLayout()

        # 模组显示名称（可包含中文和空格）
        form_layout.addWidget(QLabel("模组名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入模组显示名称")
        self.name_edit.textChanged.connect(self._on_input_changed)
        form_layout.addWidget(self.name_edit, 0, 1)

        # 文件夹名称（仅英文字母数字下划线连字符，HOI4规范限制）
        form_layout.addWidget(QLabel("文件夹名称:"), 1, 0)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("仅字母、数字、下划线、连字符")
        self.folder_edit.textChanged.connect(self._on_input_changed)
        form_layout.addWidget(self.folder_edit, 1, 1)

        # 支持版本（如 1.14.* 表示适配1.14.x版本）
        form_layout.addWidget(QLabel("支持版本:"), 2, 0)
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("例如: 1.14.*")
        self.version_edit.textChanged.connect(self._on_input_changed)
        form_layout.addWidget(self.version_edit, 2, 1)

        layout.addLayout(form_layout)

        # ========== 标签选择区域 ==========
        # 显示已选标签数量，最多10个
        tag_header = QHBoxLayout()
        tag_header.addWidget(QLabel("Tags:"))
        self.tag_counter = QLabel("已选择 0/10")
        self.tag_counter.setStyleSheet("color: #666;")
        tag_header.addWidget(self.tag_counter)
        tag_header.addStretch()
        layout.addLayout(tag_header)

        # 标签勾选框网格（3列布局）
        tag_grid = QGridLayout()
        for i, tag in enumerate(TAG_OPTIONS):
            cb = QCheckBox(tag)
            cb.toggled.connect(self._on_tag_toggled)
            self.tag_checkboxes.append(cb)
            # 计算网格行列位置（每行3列）
            row = i // 3
            col = i % 3
            tag_grid.addWidget(cb, row, col)
        layout.addLayout(tag_grid)

        layout.addStretch()

        # ========== 底部按钮区 ==========
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # 取消按钮 — 关闭对话框
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)

        # 确定按钮 — 创建mod
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

        # 初始验证输入
        self._validate_inputs()

    def _on_input_changed(self):
        """输入框内容变化时重新验证"""
        self._validate_inputs()

    def _on_tag_toggled(self):
        """
        标签勾选状态变化时的处理逻辑：
        1. 统计已选数量，更新计数器
        2. 超过最大数量时取消本次勾选
        3. 达到上限时禁用未选中的标签
        """
        # 统计已选中的标签数量
        selected = sum(1 for cb in self.tag_checkboxes if cb.isChecked())

        # 超过上限：取消本次勾选
        if selected > MAX_TAGS:
            sender = self.sender()
            if sender and isinstance(sender, QCheckBox):
                # 暂时阻塞信号避免递归触发
                sender.blockSignals(True)
                sender.setChecked(False)
                sender.blockSignals(False)
            selected = MAX_TAGS

        # 更新标签计数器显示
        self.tag_counter.setText(f"已选择 {selected}/{MAX_TAGS}")

        # 达到上限时禁用未选中的标签
        if selected >= MAX_TAGS:
            for cb in self.tag_checkboxes:
                if not cb.isChecked():
                    cb.setEnabled(False)
        else:
            # 恢复所有标签的可选状态
            for cb in self.tag_checkboxes:
                cb.setEnabled(True)

    def _validate_inputs(self):
        """
        验证所有输入是否有效
        启用/禁用确定按钮
        要求：
        - HOI4目录、默认mod目录和.mod文件目录已配置
        - 模组名称不为空
        - 文件夹名称不为空且只含合法字符
        - 支持版本不为空
        """
        hoi4_ok = bool(self.settings.get("HOI4_path"))
        modfolder_ok = bool(self.settings.get("mod_folder_path"))
        modfile_ok = bool(self.settings.get("mod_file_path"))
        paths_ok = hoi4_ok and modfolder_ok and modfile_ok

        # 验证名称、文件夹名、版本
        name_ok = bool(self.name_edit.text().strip())
        folder_ok = bool(self.folder_edit.text().strip()) and FOLDER_NAME_PATTERN.match(self.folder_edit.text().strip())
        version_ok = bool(self.version_edit.text().strip())

        # 所有条件满足才能启用确定按钮
        self.ok_btn.setEnabled(paths_ok and name_ok and folder_ok and version_ok)

    def _on_ok(self):
        """
        确定按钮点击：创建mod项目
        1. 收集表单数据
        2. 检查文件夹是否已存在
        3. 调用创建方法
        4. 成功后发送信号并关闭对话框
        """
        # 收集已选标签
        tags = [cb.text() for cb in self.tag_checkboxes if cb.isChecked()]
        mod_name = self.name_edit.text().strip()
        folder_name = self.folder_edit.text().strip()
        version = self.version_edit.text().strip()
        mod_folder_path = self.settings["mod_folder_path"]
        mod_file_path = self.settings["mod_file_path"]

        # 构建 mod 内容目录完整路径
        full_folder = os.path.join(mod_folder_path, folder_name)
        # 构建 .mod 描述文件完整路径
        mod_descriptor_path = os.path.join(mod_file_path, f"{folder_name}.mod")
        # 检查是否已存在
        if os.path.exists(full_folder):
            QMessageBox.warning(self, "错误", f"文件夹已存在: {full_folder}")
            return
        if os.path.exists(mod_descriptor_path):
            QMessageBox.warning(self, "错误", f".mod 文件已存在: {mod_descriptor_path}")
            return

        try:
            # 创建mod文件结构
            self._create_mod_structure(mod_name, folder_name, version, tags, mod_folder_path, mod_file_path)
            QMessageBox.information(self, "成功", f"模组 '{mod_name}' 创建成功！")
            # 发送创建成功信号（传递路径）
            self.mod_created.emit(full_folder)
            # 关闭对话框
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建模组失败: {e}")

    def _create_mod_structure(self, mod_name, folder_name, version, tags, mod_folder_path, mod_file_path):
        """
        创建mod的完整文件结构：
        1. {mod_file_path}/{folder_name}.mod — mod描述文件（只存放在 .mod 文件目录）
        2. {mod_folder_path}/{folder_name}/descriptor.mod — mod内部描述文件
        3. {mod_folder_path}/{folder_name}/gfx/ — 图标资源目录（空）
        4. {mod_folder_path}/{folder_name}/interface/{folder_name}.gfx — 精灵定义文件
        5. {mod_folder_path}/{folder_name}/localisation/simp_chinese/{folder_name}_l_simp_chinese.yml — 本地化文件
        """
        full_folder = os.path.join(mod_folder_path, folder_name)

        # ====== 创建 .mod 文件（.mod 文件目录，只存放 .mod 文件）======
        mod_file_full_path = os.path.join(mod_file_path, f"{folder_name}.mod")
        # 格式化标签字符串
        tags_str = "\n".join(f'    "{tag}"' for tag in tags)
        mod_content = f'name = "{mod_name}"\npath = "{mod_folder_path}/{folder_name}"\nsupported_version = "{version}"\ntags = {{\n{tags_str}\n}}\n'

        # 写入.mod文件（游戏启动器读取此文件来识别mod）
        with open(mod_file_full_path, 'w', encoding='utf-8-sig') as f:
            f.write(mod_content)

        # ====== 创建mod目录结构 ======
        os.makedirs(full_folder, exist_ok=True)

        # descriptor.mod — mod内部分布式描述文件
        descriptor_path = os.path.join(full_folder, "descriptor.mod")
        with open(descriptor_path, 'w', encoding='utf-8-sig') as f:
            f.write(mod_content)

        # gfx/ — 图标资源目录
        gfx_dir = os.path.join(full_folder, "gfx")
        os.makedirs(gfx_dir, exist_ok=True)

        # interface/*.gfx — 空白GFX精灵定义文件
        interface_dir = os.path.join(full_folder, "interface")
        os.makedirs(interface_dir, exist_ok=True)
        gfx_file_path = os.path.join(interface_dir, f"{folder_name}.gfx")
        gfx_content = "spriteTypes = {\n\n}\n"
        with open(gfx_file_path, 'w', encoding='utf-8-sig') as f:
            f.write(gfx_content)

        # localisation/simp_chinese/*.yml — 空白简体中文本地化文件（HOI4 标准拼写）
        loc_dir = os.path.join(full_folder, "localisation", "simp_chinese")
        os.makedirs(loc_dir, exist_ok=True)
        yml_path = os.path.join(loc_dir, f"{folder_name}_l_simp_chinese.yml")
        with open(yml_path, 'w', encoding='utf-8-sig') as f:
            f.write("l_simp_chinese:\n")
