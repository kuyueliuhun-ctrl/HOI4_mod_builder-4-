"""通用 PDX 树编辑器模块

提供 GenericTreeEditor 类，用于可视化编辑 PDX（Paradox Development Language）树结构。
支持节点的增删改查、拖拽排序、搜索过滤、翻译集成、模板导入等功能。
主要用于编辑《钢铁雄心4》（Hearts of Iron IV）国策树、理念树等游戏数据文件。

依赖：
    - PyQt6: GUI 框架
    - GuiTranslator: 提供中英文翻译查询
    - FocusTreeModel: 树模型数据层
    - TreeNode: 树节点数据结构
    - NodeEditDialog: 节点编辑对话框
    - CustomStatementDialog: 自定义语句管理对话框
    - TranslationEditor: 翻译编辑集成
    - FixedFieldRecognizer: 固定字段识别器
"""

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QTreeView, QLineEdit, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu, QMessageBox, QDialog, QAbstractItemView,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QTextEdit
)
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QFontMetrics, QKeySequence, QShortcut

from tree_model import FocusTreeModel
from tree_node import TreeNode, DATE_QUOTED_KEYS, quote_cjk_key
from node_edit_dialog import NodeEditDialog
from custom_statement_dialog import CustomStatementDialog
from translation_editor import get_translation_editor
from fixed_field_recognizer import (
    FixedFieldRecognizer, get_default_recognizer
)


class MultilineItemDelegate(QStyledItemDelegate):
    """支持键值换行显示的树节点委托

    树模型将值节点显示为 "键\n值" 两行文本（不使用等号），
    该委托负责把换行文本按多行渲染并自动计算行高。
    """

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        widget = opt.widget
        style = widget.style() if widget is not None else QtWidgets.QApplication.style()

        # 记录原始文本，交由本委托自行按行绘制
        text = opt.text
        opt.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

        if not text:
            return

        painter.save()
        painter.setFont(opt.font)
        fm = QFontMetrics(opt.font)
        if opt.state & QStyle.StateFlag.State_Selected:
            painter.setPen(opt.palette.highlightedText().color())
        else:
            painter.setPen(opt.palette.text().color())

        margin = 2
        x = opt.rect.left() + 4
        y = opt.rect.top() + margin + fm.ascent()
        line_height = fm.height()
        for line in text.split("\n"):
            painter.drawText(x, y, line)
            y += line_height
        painter.restore()

    def sizeHint(self, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        fm = QFontMetrics(opt.font)
        lines = opt.text.split("\n")
        width = max(fm.horizontalAdvance(line) for line in lines) if lines else 0
        height = fm.height() * len(lines) + 4
        deco = opt.decorationSize
        return QSize(max(deco.width() + width + 16, deco.width() + 40),
                     max(height, deco.height() + 8))

    def _virtual_parent_key(self, index):
        node = index.data(Qt.ItemDataRole.UserRole)
        return getattr(node, "_virtual_parent_key", None)

    def createEditor(self, parent, option, index):
        """翻译条目使用单行编辑框，描述条目使用多行编辑框。"""
        vp = self._virtual_parent_key(index)
        if vp == "文本描述":
            editor = QTextEdit(parent)
            editor.setAcceptRichText(False)
            editor.setMaximumHeight(160)
            # Ctrl+Return 提交多行编辑（Return 用于换行）
            shortcut = QShortcut(QKeySequence("Ctrl+Return"), editor)
            shortcut.activated.connect(lambda: self.commitData.emit(editor))
            editor.installEventFilter(self)
            return editor
        if vp == "翻译":
            editor = QLineEdit(parent)
            editor.returnPressed.connect(lambda: self.commitData.emit(editor))
            editor.installEventFilter(self)
            return editor
        return super().createEditor(parent, option, index)

    def eventFilter(self, obj, event):
        # 编辑器失焦时提交，确保修改被保存而不是被丢弃
        try:
            if event.type() == QEvent.Type.FocusOut:
                if isinstance(obj, (QTextEdit, QLineEdit)):
                    self.commitData.emit(obj)
        except RuntimeError:
            pass  # 编辑器已被销毁
        return super().eventFilter(obj, event)

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.EditRole) or ""
        if isinstance(editor, QTextEdit):
            editor.setPlainText(text)
        else:
            editor.setText(text)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QTextEdit):
            text = editor.toPlainText()
        else:
            text = editor.text()
        if self._virtual_parent_key(index) in ("翻译", "文本描述"):
            model.setData(index, text, Qt.ItemDataRole.EditRole)
        else:
            super().setModelData(editor, model, index)


class GenericTreeEditor(QDialog):
    """通用 PDX 树编辑器 - 非模态

    提供通用的 PDX 树结构可视化编辑界面，支持：
    - 树节点的展开/折叠、搜索过滤
    - 节点的增删改（值节点和块节点）
    - 从 PDX 命令模板添加节点
    - PDX 文本的复制/粘贴
    - 节点的上移/下移排序
    - 自定义语句管理
    - 翻译集成与本地化编辑
    - 文件保存（含缩进保持和原始格式保留）

    Attributes:
        root_node (TreeNode): 树的根节点
        file_path (str): 编辑的文件路径
        file_lines (list[str]): 文件的原始行列表
        block_range (tuple): 编辑块在文件中的起止行号 (start, end)
        translator (GuiTranslator): 翻译器实例，提供中英文对照
        custom_statement_path (str): 自定义语句文件路径
    """

    VIRTUAL_TRANSLATION_KEY = "翻译"
    VIRTUAL_DESCRIPTION_KEY = "文本描述"

    # 信号：保存成功后通知外部（通常用于刷新主界面）
    tree_saved = pyqtSignal()
    # 信号：翻译/描述保存成功后通知外部（携带字段ID，用于刷新国策节点显示）
    translation_saved = pyqtSignal(str)

    def __init__(self, root_node, file_path, file_lines, block_range,
                 translator=None, custom_statement_path="",
                 loc_manager=None, parent=None, title="树编辑器",
                 hoi4_path="", mod_path=""):
        """初始化通用树编辑器

        Args:
            root_node (TreeNode): 树的根节点
            file_path (str): 要编辑的文件路径
            file_lines (list[str]): 文件的完整行列表，用于保存时拼接
            block_range (tuple): 编辑块在文件中的 (起始行号, 结束行号)，1-indexed
            translator (GuiTranslator, optional): 翻译器实例
            custom_statement_path (str, optional): 自定义语句配置文件路径
            loc_manager (optional): 本地化管理器
            parent (QWidget, optional): 父窗口
            title (str): 窗口标题，默认为"树编辑器"
            hoi4_path (str): 钢铁雄心4游戏根目录路径
            mod_path (str): MOD 根目录路径
        """
        super().__init__(parent)

        # 保存核心数据引用
        self.root_node = root_node
        self.file_path = file_path
        self.file_lines = file_lines
        self.block_range = block_range
        self.translator = translator
        self.custom_statement_path = custom_statement_path
        self.loc_manager = loc_manager
        self.hoi4_path = hoi4_path or ""
        self.mod_path = mod_path or ""

        # 翻译编辑器实例（延迟初始化）
        self.translation_editor = None
        # 收集到的固定字段ID列表（如 focus_id 等，用于翻译编辑）
        self._fixed_field_ids = []

        # 设置窗口基本属性
        self.setWindowTitle(title)
        self.resize(750, 600)
        # 非模态窗口：不会阻塞父窗口交互
        self.setWindowModality(Qt.WindowModality.NonModal)

        # 初始化翻译编辑器（加载本地化文件）
        self._init_translation_editor()

        # 从树节点中收集固定字段ID
        self._collect_fixed_fields()

        # 构建 UI 界面布局
        self._setup_ui()
        # 连接信号与槽
        self._connect_signals()
        # 更新状态栏（节点计数等）
        self._update_status()

    def _init_translation_editor(self):
        """初始化翻译编辑器

        根据 hoi4_path 和 mod_path 自动定位本地化文件夹（simp_chinese），
        创建或获取 TranslationEditor 单例并重新加载翻译数据。
        """
        hoi4_loc = ""
        mod_loc = ""

        # 构建游戏本体的本地化路径
        if self.hoi4_path:
            import os
            hoi4_loc = os.path.join(self.hoi4_path, "localisation", "simp_chinese")
        # 构建 MOD 的本地化路径（保存统一使用 HOI4 标准拼写 localisation）
        if self.mod_path:
            import os
            mod_loc = os.path.join(self.mod_path, "localisation", "simp_chinese")

        # 如果至少有一个路径存在，则初始化翻译编辑器
        if hoi4_loc or mod_loc:
            self.translation_editor = get_translation_editor(hoi4_loc, mod_loc)
            # 重新加载以确保数据最新
            self.translation_editor.reload()

    def _collect_fixed_fields(self):
        """从树节点中收集所有固定字段ID（focus_id等）

        固定字段是指在 PDX 结构中具有特定含义的标识符字段，
        例如国策 ID、理念 ID 等。收集它们用于后续的翻译编辑功能。
        使用 FixedFieldRecognizer 进行识别，并对结果去重。
        """
        if not self.root_node:
            return

        # 获取默认的固定字段识别器
        recognizer = get_default_recognizer()
        self._fixed_field_ids = []

        # 从根节点的直接子节点开始递归收集
        self._collect_from_node(self.root_node, recognizer, "")

        # 去重：保持顺序的同时移除重复项
        seen = set()
        unique = []
        for fid in self._fixed_field_ids:
            if fid not in seen:
                seen.add(fid)
                unique.append(fid)
        self._fixed_field_ids = unique

    def _collect_from_node(self, node: TreeNode, recognizer: FixedFieldRecognizer,
                           parent_key: str):
        """递归收集固定字段

        遍历节点的所有子节点，使用 FixedFieldRecognizer 判断是否为固定字段。
        对于 focus_id 类型和 focus_block_id 类型，分别提取对应的 ID 值。
        特殊处理：根级别的 "id" 字段直接收集。

        Args:
            node (TreeNode): 当前遍历的节点
            recognizer (FixedFieldRecognizer): 固定字段识别器
            parent_key (str): 父节点的键名，用于上下文识别
        """
        for child in node.children:
            # 包装块（如 focus = { ... }）：不作为固定字段收集，仅递归其内容
            if (child.node_type == "block"
                    and child.key in ("focus", "shared_focus", "joint_focus")
                    and not child.value):
                self._collect_from_node(child, recognizer, child.key)
                continue

            # 尝试将子节点匹配为固定字段
            result = recognizer.is_fixed_field(
                child.key, child.value, parent_key,
                {"root_type": self._get_root_type()}
            )
            if result:
                # 只收集本结构体自身的可翻译字段，交叉引用（如 prerequisite 中的 focus = X）不收集
                if result["type"] == "focus_block_id":
                    # 国策块ID类型：如果值是字典则取 key，否则直接取值
                    self._fixed_field_ids.append(result["value"]["key"] if isinstance(result["value"], dict) else child.value)

            # 特殊处理：focus 块内部或根级别的 id 字段
            if child.key == "id" and (parent_key == "" or parent_key in ("focus", "shared_focus", "joint_focus")):
                self._fixed_field_ids.append(child.value)

            # 如果是块节点，递归收集其子节点
            if child.node_type == "block":
                self._collect_from_node(child, recognizer, child.key)

    def _get_root_type(self) -> str:
        """获取根节点类型

        通过检查根节点第一个子节点的键名来判断整体结构类型：
        - focus / shared_focus / joint_focus -> "focus_tree"（国策树）
        - country -> "ideas"（理念/修正器）
        - 其他 -> ""（未知类型）

        Returns:
            str: 根节点类型标识符
        """
        if not self.root_node or not self.root_node.children:
            return ""
        # 检查第一个子节点的键名
        first = self.root_node.children[0]
        if first.key == "id" or first.key in ("focus", "shared_focus", "joint_focus"):
            return "focus_tree"
        if first.key == "country":
            return "ideas"
        return ""

    def _setup_ui(self):
        """构建主界面布局

        布局结构（自上而下）：
        1. 工具栏：搜索框 + 展开/折叠按钮
        2. 根节点类型标签（如"🌳 国策树"）
        3. QTreeView 树视图（核心）
        4. 节点详情标签（选中节点时显示翻译信息）
        5. 底部栏：状态标签 + 关闭/保存按钮
        """
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)

        # ── 工具栏 ──
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索节点（中文/英文）...")
        toolbar.addWidget(self.search_edit)

        self.expand_btn = QPushButton("📂 展开")
        self.collapse_btn = QPushButton("📁 折叠")
        toolbar.addWidget(self.expand_btn)
        toolbar.addWidget(self.collapse_btn)
        self.main_layout.addLayout(toolbar)

        # ── 根节点类型显示 ──
        self.root_type_label = QLabel(self._get_root_type_display())
        self.root_type_label.setStyleSheet(
            "QLabel { background: #3c3c3c; color: #ffcc00; padding: 4px 8px; border-radius: 3px; font-weight: bold; }"
        )
        self.main_layout.addWidget(self.root_type_label)

        # ── 树视图 ──
        self.tree_view = QTreeView()
        # 启用右键菜单
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # 单选模式
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_view.setAnimated(True)
        # 双击可编辑节点（翻译/描述条目直接编辑）
        self.tree_view.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        # 使用支持换行显示的委托（键/值分行展示）
        self.tree_view.setItemDelegate(MultilineItemDelegate(self.tree_view))
        self.main_layout.addWidget(self.tree_view)

        # ── 详情标签（默认隐藏，选中国策节点时显示翻译信息） ──
        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("QLabel { background: #2d2d30; color: #d0d0d0; padding: 4px; border-radius: 3px; }")
        self.detail_label.setVisible(False)
        self.main_layout.addWidget(self.detail_label)

        # ── 底部栏 ──
        bottom = QHBoxLayout()
        self.status_label = QLabel("就绪")
        bottom.addWidget(self.status_label)
        # 弹性空间：将按钮推到右侧
        bottom.addStretch()
        self.cancel_btn = QPushButton("关闭")
        self.save_btn = QPushButton("✓ 保存")
        bottom.addWidget(self.cancel_btn)
        bottom.addWidget(self.save_btn)
        self.main_layout.addLayout(bottom)

        # 构建数据模型（包含翻译和文本描述节点）
        self.model = FocusTreeModel(self.root_node, self.translator, parent=self,
                                     loc_manager=self.loc_manager)
        # 设置编辑器引用和固定字段ID（用于翻译节点显示）
        self.model.set_editor_refs(self.translation_editor, self._fixed_field_ids)
        self.tree_view.setModel(self.model)
        # 行数较少（不超过200行）时默认展开所有节点，超过200行时收缩所有节点
        if self.file_lines and len(self.file_lines) > 200:
            self.tree_view.collapseAll()
        else:
            self.tree_view.expandAll()

    def _get_root_type_display(self) -> str:
        """获取根节点类型的友好显示文本

        Returns:
            str: 带 emoji 的类型标签，如 "🌳 国策树"
        """
        root_type = self._get_root_type()
        type_labels = {
            "focus_tree": "🌳 国策树",
            "ideas": "💡 理念/修正器",
            "event": "📜 事件树",
            "decision": "📋 决议",
        }
        return type_labels.get(root_type, f"📂 结构: {root_type or self.root_node.key}")

    def _connect_signals(self):
        """连接 UI 控件的信号与处理槽函数"""
        # 搜索框文本变化时触发搜索
        self.search_edit.textChanged.connect(self._on_search)
        # 展开/折叠全部节点
        self.expand_btn.clicked.connect(self.tree_view.expandAll)
        self.collapse_btn.clicked.connect(self.tree_view.collapseAll)
        # 右键自定义上下文菜单
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        # 保存和关闭
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.close)
        # 节点点击：更新状态和详情
        self.tree_view.clicked.connect(self._on_node_clicked)
        # 翻译保存后：刷新本地化缓存并重绘树中该节点的显示
        self.translation_saved.connect(self._on_translation_saved)
        # Ctrl+F：打开节点查找定位对话框（英文 id / 中文翻译）
        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self._open_find_dialog)
        self._find_dialog = None

    def _open_find_dialog(self):
        """Ctrl+F：打开节点查找定位对话框（英文 id / 中文翻译）。"""
        if self._find_dialog is None:
            from node_find_dialog import NodeFindDialog
            self._find_dialog = NodeFindDialog(self.model, self.translator,
                                               parent=self)
            self._find_dialog.locate_requested.connect(self._locate_node)
        self._find_dialog.focus_search()

    def _locate_node(self, index):
        """定位到树节点：展开祖先并滚动居中选中。"""
        if index is None or not index.isValid():
            return
        chain = []
        p = self.model.parent(index)
        while p.isValid():
            chain.append(p)
            p = self.model.parent(p)
        for pi in reversed(chain):
            self.tree_view.setExpanded(pi, True)
        self.tree_view.setCurrentIndex(index)
        self.tree_view.scrollTo(index,
                                QAbstractItemView.ScrollHint.PositionAtCenter)

    def _reload_loc_manager(self):
        """重新加载本地化管理器缓存并刷新树的显示。

        树编辑器与图形视图共用 LocalizationManager 单例，
        翻译保存后需重新加载才能让界面显示最新译文。
        """
        try:
            from localization_mgr import get_localization_manager
            lm = get_localization_manager()
            lm.reload(game_path=self.hoi4_path, mod_path=self.mod_path)
            self.loc_manager = lm
            if self.model is not None:
                self.model.loc_manager = lm
                self.model.layoutChanged.emit()
        except Exception:
            pass

    def _on_translation_saved(self, field_id):
        """翻译保存后的处理：刷新本地化缓存与树显示。"""
        self._reload_loc_manager()

    def _on_node_clicked(self, index):
        """节点被点击时的处理

        Args:
            index (QModelIndex): 被点击节点的模型索引
        """
        self._update_status()
        self._update_detail(index)

    def _update_detail(self, index):
        """更新节点详情标签

        当选中节点为 focus 节点且存在 loc_manager 时，
        显示该国策的中文名称和描述（从本地化文件中读取）。

        Args:
            index (QModelIndex): 当前选中节点的模型索引
        """
        if not index.isValid():
            self.detail_label.setText("")
            self.detail_label.setVisible(False)
            return
        # 从模型索引获取对应的树节点
        node = self.model.node_from_index(index)
        # 根节点不显示详情
        if node == self.root_node:
            self.detail_label.setText("")
            self.detail_label.setVisible(False)
            return
        # 如果是国策节点且有本地化管理器
        if node.key == "focus" and self.loc_manager:
            focus_id = node.value
            # 若为包装块，从子节点的 id 字段获取国策 ID
            for child in node.children:
                if child.key == "id":
                    focus_id = child.value
                    break
            # 从本地化数据中获取中文名称和描述
            cn_name = self.loc_manager.get_name(focus_id)
            cn_desc = self.loc_manager.get_desc(focus_id)
            parts = [f"ID: {focus_id}"]
            if cn_name:
                parts.append(f"名称: {cn_name}")
            if cn_desc:
                parts.append(f"描述: {cn_desc}")
            self.detail_label.setText("\n".join(parts))
            self.detail_label.setVisible(True)
        else:
            self.detail_label.setText("")
            self.detail_label.setVisible(False)

    def _update_status(self):
        """更新状态栏：显示总节点数和已翻译节点数"""
        count = self._count_nodes(self.root_node)
        cn_count = self._count_translatable(self.root_node)
        if count > 0:
            self.status_label.setText(f"节点数: {count} | 已翻译: {cn_count}/{count}")
        else:
            self.status_label.setText("节点数: 0")

    def _count_nodes(self, node):
        """递归计算树中所有子节点的总数（不含根节点）

        Args:
            node (TreeNode): 起始节点

        Returns:
            int: 子节点总数
        """
        count = len(node.children)
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _count_translatable(self, node):
        """递归计算树中有翻译的节点数量

        通过翻译器检查 key 是否有对应的中文翻译。
        有翻译表示该字段对中文用户更友好。

        Args:
            node (TreeNode): 起始节点

        Returns:
            int: 有翻译的节点数量
        """
        count = 0
        for child in node.children:
            # 检查当前节点的 key 是否可翻译
            cn_key = self.translator.translate_key(child.key) if self.translator else child.key
            if cn_key != child.key:
                count += 1
            # 递归统计子节点
            count += self._count_translatable(child)
        return count

    def _show_context_menu(self, pos: QPoint):
        """显示右键上下文菜单

        根据当前选中节点的类型（根节点/块节点/值节点/翻译节点）动态构建菜单项。
        菜单项包括：添加节点（统一词条/模板搜索）、编辑节点、
        上移/下移、删除、管理自定义语句、管理词条等。

        Args:
            pos (QPoint): 右键点击位置（相对于树视图）
        """
        menu = QMenu(self)
        index = self.tree_view.indexAt(pos)
        self.tree_view.setCurrentIndex(index)
        node = self.model.node_from_index(index)
        is_root = (node == self.root_node)

        # 翻译和文本描述节点只有翻译相关的菜单
        if node.key == "翻译" or node.key == "文本描述":
            edit_translation_action = menu.addAction("✎ 编辑翻译")
            edit_translation_action.triggered.connect(self._edit_translation)
            menu.addSeparator()
            refresh_action = menu.addAction("🔄 刷新翻译")
            refresh_action.triggered.connect(self._refresh_translations)
            global_pos = self.tree_view.viewport().mapToGlobal(pos)
            menu.exec(global_pos)
            return

        # 翻译/描述的具体条目（虚拟子节点）：编辑该字段的翻译
        vp = getattr(node, "_virtual_parent_key", None)
        if vp in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY):
            field_id = node.key
            edit_translation_action = menu.addAction("✎ 编辑翻译/描述")
            edit_translation_action.triggered.connect(
                lambda: self._edit_translation(field_id)
            )
            menu.addSeparator()
            refresh_action = menu.addAction("🔄 刷新翻译")
            refresh_action.triggered.connect(self._refresh_translations)
            global_pos = self.tree_view.viewport().mapToGlobal(pos)
            menu.exec(global_pos)
            return

        # 根节点或块节点：可通过统一搜索添加子节点（词条/模板）
        if is_root or node.node_type == "block":
            add_node_action = menu.addAction("🔍 添加节点（词条/模板）...")
            add_node_action.triggered.connect(self._add_node_search)
            if node.node_type == "block" and node != self.root_node:
                save_tpl_action = menu.addAction("💾 将该块保存为模板…")
                save_tpl_action.triggered.connect(
                    lambda: self._save_block_as_template(node))
            menu.addSeparator()

        # 顾问分配文件（history/general/*advisors*.txt）：提供专门的分配编辑
        if self._is_advisor_assign_file():
            if (node.key == "every_possible_country" or node.key == "every_other_country"
                    or node.key == "generate_character" or is_root):
                assign_action = menu.addAction("🎯 顾问分配编辑…")
                assign_action.triggered.connect(self._open_advisor_assign_dialog)
                menu.addSeparator()

        # 通用菜单项
        edit_action = menu.addAction("✎ 编辑节点")
        edit_action.triggered.connect(self._edit_node)
        # 非根节点：可以移动和删除
        if node != self.root_node:
            menu.addSeparator()
            up_action = menu.addAction("⬆ 上移")
            up_action.triggered.connect(self._move_up)
            down_action = menu.addAction("⬇ 下移")
            down_action.triggered.connect(self._move_down)
            menu.addSeparator()
            del_action = menu.addAction("🗑 删除节点")
            del_action.triggered.connect(self._delete_node)
        menu.addSeparator()
        manage_action = menu.addAction("⚙ 管理自定义语句...")
        manage_action.triggered.connect(self._manage_custom_statements)
        term_action = menu.addAction("📖 管理词条...")
        term_action.triggered.connect(self._manage_terms)

        # 根节点额外显示翻译编辑入口
        if is_root:
            menu.addSeparator()
            edit_trans_action = menu.addAction("📖 编辑翻译/描述...")
            edit_trans_action.triggered.connect(self._edit_translation)

        # 将菜单显示在全局坐标位置
        global_pos = self.tree_view.viewport().mapToGlobal(pos)
        menu.exec(global_pos)

    def _edit_translation(self, field_id=None):
        """打开翻译编辑对话框

        使用固定字段ID（如国策ID）打开翻译编辑对话框，
        允许用户编辑对应的中文名称和描述。保存时写入 mod 目录中
        类型对应的翻译文件（如 focus_mod_l_simp_chinese.yml）。
        """
        from translation_widget import TranslationEditDialog
        from translation_editor import get_mod_loc_file_name
        target = field_id or (self._fixed_field_ids[0] if self._fixed_field_ids else None)
        if target:
            # 编辑指定字段（默认是主要 focus_id）
            file_name = get_mod_loc_file_name(self._get_root_type())
            dlg = TranslationEditDialog(
                target,
                self.hoi4_path,
                self.mod_path,
                file_name,
                self
            )
            # 翻译保存后自动刷新显示
            dlg.accepted.connect(self._refresh_translations)
            dlg.show()
        else:
            QMessageBox.information(
                self, "无固定字段",
                "未检测到可编辑的固定字段（如focus_id、ideas中的country名称等）。\n"
                "请在编辑器中添加对应的字段后再试。"
            )

    def _refresh_translations(self):
        """刷新翻译节点显示

        触发模型的 layoutChanged 信号让视图重新渲染，
        使翻译节点的数据更新后能在界面上反映出来。
        """
        self.model.layoutChanged.emit()
        self._update_status()

    def _edit_node(self):
        """编辑当前选中的节点

        打开 NodeEditDialog 进行节点属性编辑。
        编辑完成后根据子节点数量的变化，使用对应的模型方法
        （insertRows/removeRows/dataChanged）来通知视图更新，
        以保证视图与数据的一致性，避免崩溃。
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return
        node = self.model.node_from_index(index)
        # 禁止编辑根节点
        if node == self.root_node:
            return
        # 记录编辑前的子节点数，用于判断增删
        old_child_count = len(node.children)
        dlg = NodeEditDialog(self.translator, node=node, parent=self)

        def on_edit_ok():
            """对话框确认后的回调"""
            result = dlg.get_node()
            if result:
                new_child_count = len(result.children)
                # 编辑改变了节点内容，需清空其所有祖先节点的 raw_lines，
                # 否则保存时仍会输出旧的原始文本行，导致修改被丢弃。
                if node.parent is not None:
                    p = node.parent
                    while p is not None:
                        p.raw_lines = []
                        p = p.parent
                # 子节点增多 → 通知模型插入行
                if new_child_count > old_child_count:
                    self.model.beginInsertRows(index, old_child_count, new_child_count - 1)
                    self._replace_node(node, result)
                    self.model.endInsertRows()
                    self.model.dataChanged.emit(index, index)
                # 子节点减少 → 通知模型移除行
                elif new_child_count < old_child_count:
                    self.model.beginRemoveRows(index, new_child_count, old_child_count - 1)
                    self._replace_node(node, result)
                    self.model.endRemoveRows()
                    self.model.dataChanged.emit(index, index)
                # 子节点数不变 → 仅标记数据变化
                else:
                    self._replace_node(node, result)
                    self.model.dataChanged.emit(index, index)
                self._update_status()
            # 用完即删，防止内存泄漏
            dlg.deleteLater()

        dlg.accepted.connect(on_edit_ok)
        dlg.show()

    def _replace_node(self, node, result):
        """用新节点数据替换原节点的属性

        注意：这里不改变节点的对象引用，而是原地修改属性，
        以保证模型中的索引仍然有效。

        Args:
            node (TreeNode): 被替换的目标节点
            result (TreeNode): 包含新数据的节点
        """
        node.key = result.key
        node.value = result.value
        node.node_type = result.node_type
        node.children = result.children
        # 清空 raw_lines，后续序列化时会重新生成
        node.raw_lines = []
        # 重新设置子节点的 parent 引用
        for child in node.children:
            child.parent = node

    @staticmethod
    def _invalidate_ancestors(node):
        """清空节点自身及其所有祖先的 raw_lines，确保保存时从树重新序列化。

        若某个节点或其祖先块保留了原始文本行（raw_lines），修改内部后
        保存时仍会输出旧文本，导致修改被丢弃。这里沿节点自身向上清空。
        """
        p = node
        while p is not None:
            p.raw_lines = []
            p = p.parent

    def _add_node_search(self):
        """统一搜索添加子节点（词条 / 模板）

        打开 NodeSearchDialog，合并搜索词条（块/值）与模板：
        - 词条块 → 创建空块节点
        - 词条值 → 预填键名打开节点编辑对话框
        - 模板 → 解析模板内容为块节点
        """
        from node_search_dialog import NodeSearchDialog
        index = self.tree_view.currentIndex()
        parent_node = self.model.node_from_index(index)
        dlg = NodeSearchDialog(self.translator, parent=self)

        def on_add_ok():
            new_node = dlg.get_node()
            if new_node:
                self.model.insert_node(index, new_node)
                self._invalidate_ancestors(parent_node)
                self.tree_view.expand(index)
                self._update_status()
            dlg.deleteLater()

        dlg.accepted.connect(on_add_ok)
        dlg.show()


    def _template_type_for_file(self):
        """根据文件路径推断模板类型（用于保存块为模板）。"""
        fp = (getattr(self, "file_path", "") or "").replace("/", "\\")
        try:
            from workbench import CONTENT_TYPES
            for _key, _name, _icon, folders, tpl_type, _ext in CONTENT_TYPES:
                if not tpl_type:
                    continue
                for folder in (folders or []):
                    if folder and folder != "." and \
                            ("\\" + folder.replace("/", "\\") + "\\") in fp:
                        return tpl_type
        except Exception:
            pass
        return "custom"

    def _is_advisor_assign_file(self) -> bool:
        """判断当前编辑文件是否为顾问分配文件（history/general/*advisors*.txt）。

        同时识别文件内容中是否存在 every_possible_country / generate_character 结构。
        """
        import os
        fp = (getattr(self, "file_path", "") or "").replace("/", "\\")
        if "\\history\\general\\" in fp.lower() and "advis" in os.path.basename(fp).lower():
            return True
        # 内容识别：根节点下存在 every_possible_country 且含 generate_character
        try:
            for child in getattr(self.root_node, "children", []):
                if child.key in ("every_possible_country", "every_other_country"):
                    return True
        except Exception:
            pass
        return False

    def _open_advisor_assign_dialog(self):
        """打开顾问分配编辑对话框（国家条件 + 顾问参数）。"""
        from advisor_assign_dialog import AdvisorAssignDialog
        dlg = AdvisorAssignDialog(
            self.root_node,
            file_path=getattr(self, "file_path", ""),
            mod_path=self.mod_path,
            game_path=self.hoi4_path,
            loc_manager=self.loc_manager,
            parent=self,
        )
        dlg.tree_changed.connect(self._refresh_translations)
        dlg.show()

    def _save_block_as_template(self, node):
        """将选中的块节点保存为模板文件。

        保存后自动扫描内容中的 __变量名__ 占位符，
        弹出变量设置对话框让用户选择哪些变量需要填入。
        """
        from PyQt6.QtWidgets import QInputDialog
        from template_scheduler import get_template_scheduler
        name, ok = QInputDialog.getText(
            self, "将该块保存为模板", "模板名称:", text=node.key)
        if not ok or not (name or "").strip():
            return
        content = node.to_pdx() if node.node_type == "block" else node.key
        ttype = self._template_type_for_file()
        scheduler = get_template_scheduler()
        path = scheduler.create_template(name.strip(), content, ttype)
        if not path:
            QMessageBox.warning(self, "错误", "保存模板失败")
            return
        # 变量选择：扫描占位符并弹出设置对话框（选择需要填入的变量）
        variables = scheduler.get_template_variables(path)
        if variables:
            from template_manager_dialog import TemplateVariableDialog
            vdlg = TemplateVariableDialog(scheduler, path, parent=self)
            vdlg.show()
            vdlg.accepted.connect(lambda: QMessageBox.information(
                self, "成功", f"模板已保存并配置变量：\n{path}"))
            return
        QMessageBox.information(self, "成功", f"模板已保存：\n{path}")


    def _move_up(self):
        """将选中节点上移一个位置

        使用模型的 beginMoveRows/endMoveRows 方法来正确通知视图，
        保证模型索引在移动过程中保持一致，避免崩溃。
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return
        node = self.model.node_from_index(index)
        if node != self.root_node and node.parent:
            # 获取节点在父节点下的索引位置
            idx = node.child_index()
            if idx > 0:  # 不是第一个才能上移
                parent_index = index.parent()
                # 通知模型开始移动行（源行 idx，目标行 idx-1）
                self.model.beginMoveRows(parent_index, idx, idx, parent_index, idx - 1)
                node.move_up()
                self.model.endMoveRows()
                # 清空缓存，保存时重新序列化
                self._invalidate_ancestors(node)

    def _move_down(self):
        """将选中节点下移一个位置

        逻辑与 _move_up 对称，目标位置为 idx+2（因为 endMoveRows 的目标是"插入到该行之前"）。
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return
        node = self.model.node_from_index(index)
        if node != self.root_node and node.parent:
            idx = node.child_index()
            if idx < len(node.parent.children) - 1:  # 不是最后一个才能下移
                parent_index = index.parent()
                # idx+2: 因为目标是在 idx+1 行之前插入（即移动到 idx+1 的位置）
                self.model.beginMoveRows(parent_index, idx, idx, parent_index, idx + 2)
                node.move_down()
                self.model.endMoveRows()
                self._invalidate_ancestors(node)

    def _delete_node(self):
        """删除选中的节点（带确认对话框）

        通过模型删除节点，保持视图与数据的一致性。
        不删除根节点。
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return
        node = self.model.node_from_index(index)
        if node == self.root_node:
            return
        # 禁止删除国策包装块（如 focus 块本身），防止整块被误删
        wrapper = self._get_editable_wrapper_block()
        if node == wrapper and node.key in ("focus", "shared_focus", "joint_focus"):
            QMessageBox.warning(self, "提示", "不能删除该包装节点（如 focus 块本身）。\n你可以编辑它或其子节点。")
            return
        # 二次确认
        reply = QMessageBox.question(self, "确认", f"确定要删除节点 '{node.key}' 吗？")
        if reply == QMessageBox.StandardButton.Yes:
            parent_node = node.parent
            self.model.remove_node(index)
            if parent_node:
                self._invalidate_ancestors(parent_node)
            self._update_status()

    def _manage_custom_statements(self):
        """打开自定义语句管理对话框

        让用户管理自定义的 PDX 命令翻译和定义，
        包括添加、编辑、删除自定义语句。
        """
        dlg = CustomStatementDialog(self.translator, self.custom_statement_path, parent=self)
        # 自定义语句变化后更新状态
        dlg.statements_changed.connect(self._update_status)
        dlg.show()

    def _manage_terms(self):
        """打开词条管理对话框（效果器/触发器词条）。"""
        from term_dialog import TermDialog
        from term_registry import get_term_registry
        dlg = TermDialog(get_term_registry(), parent=self)
        dlg.terms_changed.connect(self._update_status)
        dlg.show()

    def _on_search(self, keyword):
        """搜索节点（根据关键词模糊匹配）

        使用模型的 find_nodes 方法进行节点搜索。
        找到结果后自动滚动并选中第一个匹配项。

        Args:
            keyword (str): 搜索关键词
        """
        if not keyword.strip():
            return
        results = self.model.find_nodes(keyword.strip())
        if results:
            self.tree_view.setCurrentIndex(results[0])
            self.tree_view.scrollTo(results[0])

    def _save(self):
        """保存编辑结果到文件

        保存流程：
        1. 检测原文件的缩进格式（tab 或空格）
        2. 构建外层的包装起始行（如 "focus = {"）
        3. 将树节点序列化为带缩进的 PDX 文本行
        4. 拼接文件头 + 编辑块 + 文件尾
        5. 写入文件（UTF-8 with BOM）

        Returns:
            bool: 保存成功返回 True，失败返回 False
        """
        try:
            start, end = self.block_range
            # 获取编辑块起始行的文本，用于检测缩进
            if start <= 0 or start > len(self.file_lines):
                start_line_text = ""
            else:
                start_line_text = self.file_lines[start - 1]
            # 提取缩进字符（优先使用 tab；否则统计前导空格数量作为缩进单位）
            indent = ""
            unit = "\t"
            for ch in start_line_text:
                if ch in ('\t', ' '):
                    indent += ch
                else:
                    break
            if indent and not indent.startswith("\t"):
                unit = indent

            # 构建编辑块的包装行
            wrapper_start = self._get_wrapper_start(indent)
            wrapper_end = f"{indent}}}"

            # 若根节点下只有唯一的包装块子节点（如 focus 块），序列化该块的子节点
            inner_source = self._get_editable_wrapper_block()
            if inner_source is None:
                inner_source = self.root_node
            inner_lines = self._serialize_children(inner_source, indent=1, unit=unit)

            # 拼接完整文件内容：头 + 包装开始 + 内部内容 + 包装结束 + 尾
            new_lines = (
                self.file_lines[:start - 1] +
                [wrapper_start] +
                inner_lines +
                [wrapper_end] +
                self.file_lines[end:]
            )

            # 写入文件（UTF-8 with BOM）
            output = "\n".join(new_lines) + "\n"
            try:
                with open(self.file_path, "w", encoding="utf-8-sig", newline="") as f:
                    f.write(output)
            except PermissionError:
                # 尝试清除只读属性后重写
                import os
                try:
                    os.chmod(self.file_path, 0o666)
                    with open(self.file_path, "w", encoding="utf-8-sig", newline="") as f:
                        f.write(output)
                except Exception:
                    raise
            # 保存成功后刷新固定字段ID（翻译/描述条目跟随新ID）
            self._collect_fixed_fields()
            self.model.set_editor_refs(self.translation_editor, self._fixed_field_ids)
            # 发送保存成功信号
            self.tree_saved.emit()
            self.close()
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入文件时出错: {e}")
            return False

    def _get_wrapper_start(self, indent):
        """获取编辑块包装的起始行

        子类可以重写此方法以提供不同的包装格式。
        若根节点下只有一个包装块子节点，则使用该块的键名；
        否则默认使用 "focus = {"。

        Args:
            indent (str): 缩进字符串

        Returns:
            str: 包装起始行
        """
        block = self._get_editable_wrapper_block()
        if block is not None:
            return f"{indent}{block.key} = {{"
        return f"{indent}focus = {{"

    def _get_editable_wrapper_block(self):
        """返回可编辑的包装块节点

        当根节点下恰好只有一个块子节点（如 focus 块）时返回该节点，
        此时树编辑器应展示此包装块并允许用户编辑。
        否则返回 None。

        Returns:
            Optional[TreeNode]: 包装块节点，或 None
        """
        if len(self.root_node.children) == 1 and self.root_node.children[0].node_type == "block":
            return self.root_node.children[0]
        return None

    def _serialize_children(self, parent_node, indent=1, unit="\t"):
        """将子节点序列化为 PDX 文本行列表

        递归地将节点树转换为带缩进的 PDX 格式文本。
        处理逻辑：
        - 如果有 raw_lines（原始保留的文本），直接使用
        - 值节点：格式为 "key = value"
        - 块节点：格式为 "key = { ... }"（含递归子节点）

        Args:
            parent_node (TreeNode): 父节点
            indent (int): 缩进级数（unit 的倍数）
            unit (str): 缩进单位（"\\t" 或 "    "），与源文件保持一致

        Returns:
            list[str]: PDX 文本行列表
        """
        lines = []
        tabs = unit * indent
        for child in parent_node.children:
            # 跳过虚拟节点（顾问分配等展示条目，不写入文件）
            if getattr(child, "_virtual_parent_key", None):
                continue
            # 如果有原始行，直接使用（保留格式）
            if child.raw_lines:
                for line in child.raw_lines:
                    lines.append(line)
            elif child.node_type == "value":
                v = child.value if child.value is not None else ""
                # 值中不能包含换行，避免破坏单行键值对结构
                if "\n" in v or "\r" in v:
                    v = " ".join(v.split())
                # 日期类字段：无空格裸写会被引擎按数字截断解析，强制加双引号
                if child.key in DATE_QUOTED_KEYS and v and not v.startswith('"'):
                    v = f'"{v}"'
                # 值中包含空格且未加引号/花括号包围时加引号
                if " " in v and not v.startswith('"') and not v.startswith("{"):
                    v = f'"{v}"'
                # 键名为空时直接输出值
                if child.key:
                    lines.append(f"{tabs}{quote_cjk_key(child.key)} = {v}")
                else:
                    lines.append(f"{tabs}{v}")
            else:  # block 类型
                if not child.children:
                    # 空块节点
                    lines.append(f"{tabs}{quote_cjk_key(child.key)} = {{ }}")
                else:
                    lines.append(f"{tabs}{quote_cjk_key(child.key)} = {{")
                    # 递归序列化子节点
                    lines.extend(self._serialize_children(child, indent + 1, unit))
                    lines.append(f"{tabs}}}")
        return lines
