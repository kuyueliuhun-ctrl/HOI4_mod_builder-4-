from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, QObject
from tree_node import TreeNode


class FocusTreeModel(QAbstractItemModel):
    """QAbstractItemModel 适配 TreeNode 到 QTreeView"""

    VIRTUAL_TRANSLATION_KEY = "翻译"
    VIRTUAL_DESCRIPTION_KEY = "文本描述"

    def __init__(self, root_node: TreeNode, translator=None, parent=None, loc_manager=None):
        super().__init__(parent)
        self.root_node = root_node
        self.translator = translator
        self.loc_manager = loc_manager
        self.translation_editor = None
        self._fixed_field_ids = []
        self._show_virtual_nodes = True
        self._vrefs = {}
        self._virtual_nodes = {}
        self._virtual_children = {}

    def set_editor_refs(self, translation_editor, fixed_field_ids):
        self.translation_editor = translation_editor
        self._fixed_field_ids = fixed_field_ids or []

    @staticmethod
    def _safe_pointer(index: QModelIndex):
        ptr = index.internalPointer()
        if isinstance(ptr, TreeNode):
            return ptr
        return None

    def node_from_index(self, index: QModelIndex):
        node = self._safe_pointer(index)
        if node is not None:
            return node
        return self.root_node

    def _is_virtual_node(self, node) -> bool:
        if not isinstance(node, TreeNode):
            return False
        return (node.key in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY)
                and node.parent == self.root_node)

    def _get_virtual_children_count(self) -> int:
        if not self._show_virtual_nodes:
            return 0
        if self._fixed_field_ids:
            return 2
        return 0

    def _get_virtual_node(self, row: int):
        if row in self._virtual_nodes:
            return self._virtual_nodes[row]
        if row == 0:
            node = TreeNode("block", self.VIRTUAL_TRANSLATION_KEY, parent=self.root_node)
        elif row == 1:
            node = TreeNode("block", self.VIRTUAL_DESCRIPTION_KEY, parent=self.root_node)
        else:
            return None
        self._virtual_nodes[row] = node
        self._vrefs[id(node)] = node
        return node

    def _get_virtual_child(self, parent_key: str, row: int):
        key = (parent_key, row)
        if key in self._virtual_children:
            return self._virtual_children[key]
        field_id = self._fixed_field_ids[row]
        child = TreeNode("value", field_id, field_id)
        child._virtual_parent_key = parent_key
        self._virtual_children[key] = child
        self._vrefs[id(child)] = child
        return child

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        if not parent.isValid():
            real_count = len(self.root_node.children)
            virtual_count = self._get_virtual_children_count()
            return real_count + virtual_count
        node = self._safe_pointer(parent)
        if node is None:
            return 0
        if self._is_virtual_node(node):
            if node.key == self.VIRTUAL_TRANSLATION_KEY:
                return len(self._fixed_field_ids)
            elif node.key == self.VIRTUAL_DESCRIPTION_KEY:
                return len(self._fixed_field_ids)
        return len(node.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()):
        return 1

    def index(self, row, column, parent: QModelIndex = QModelIndex()):
        if not parent.isValid():
            real_count = len(self.root_node.children)
            if row < real_count:
                return self.createIndex(row, column, self.root_node.children[row])
            else:
                virtual_row = row - real_count
                virtual_node = self._get_virtual_node(virtual_row)
                if virtual_node:
                    return self.createIndex(row, column, virtual_node)
                return QModelIndex()
        else:
            parent_node = self._safe_pointer(parent)
            if parent_node is None:
                return QModelIndex()
            if self._is_virtual_node(parent_node):
                if row < len(self._fixed_field_ids):
                    child = self._get_virtual_child(parent_node.key, row)
                    return self.createIndex(row, column, child)
                return QModelIndex()

            if row < len(parent_node.children):
                return self.createIndex(row, column, parent_node.children[row])
            return QModelIndex()

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        node = self._safe_pointer(index)
        if node is None:
            return QModelIndex()

        vp = getattr(node, "_virtual_parent_key", None)
        if vp in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY):
            real_count = len(self.root_node.children)
            if vp == self.VIRTUAL_TRANSLATION_KEY:
                vrow = 0
            else:
                vrow = 1
            virtual = self._get_virtual_node(vrow)
            if virtual is not None:
                return self.createIndex(real_count + vrow, 0, virtual)
            return QModelIndex()

        if node.parent is None or node.parent == self.root_node:
            return QModelIndex()

        return self.createIndex(node.parent.child_index(), 0, node.parent)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        node = self._safe_pointer(index)
        if node is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if node.key == self.VIRTUAL_TRANSLATION_KEY and node.parent == self.root_node:
                return f"📖 翻译 ({len(self._fixed_field_ids)}个字段)"
            if node.key == self.VIRTUAL_DESCRIPTION_KEY and node.parent == self.root_node:
                return f"📝 文本描述 ({len(self._fixed_field_ids)}个字段)"

            vp = getattr(node, "_virtual_parent_key", None)
            if vp in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY):
                field_id = node.key
                if self.translation_editor:
                    name = self.translation_editor.get_name(field_id)
                    desc = self.translation_editor.get_desc(field_id)
                    if vp == self.VIRTUAL_TRANSLATION_KEY:
                        if name:
                            return f"📄 {name}"
                        return f"📄 {field_id}（无翻译）"
                    else:
                        if desc:
                            return f"📄 {desc}"
                        return f"📄 {field_id}（无描述）"
                return f"📄 {field_id}"

            if self.translator:
                cn_key, cn_val = self.translator.translate_node(node.key, node.value)
            else:
                cn_key, cn_val = node.key, node.value

            if node.node_type == "block":
                if node.key == "focus" and self.loc_manager:
                    cn_name = self.loc_manager.get_name(node.value)
                    if cn_name:
                        return f"📁 {node.value}--{cn_name}"
                if cn_key and cn_key != node.key:
                    return f"📁 {node.key}--{cn_key}"
                return f"📁 {node.key}"
            else:
                # 键名为空：只有值，不显示等号
                if not node.key:
                    if node.value:
                        vtext = node.value
                        if cn_val and cn_val != node.value:
                            vtext += f"--{cn_val}"
                        return f"📄 {vtext}"
                    return f"📄 (值)"
                # 有值的键值对：正常显示等号
                if node.value:
                    vtext = node.value
                    if cn_val and cn_val != node.value:
                        vtext += f"--{cn_val}"
                    key_text = node.key
                    if cn_key and cn_key != node.key:
                        key_text = f"{node.key}--{cn_key}"
                    return f"📄 {key_text} = {vtext}"
                # 只有值而没有等号（裸值）：不显示等号，多个值用换行隔开
                vals = [p for p in node.key.split() if p]
                if not vals:
                    return f"📄 (值)"
                return f"📄 " + "\n".join(vals)

        if role == Qt.ItemDataRole.EditRole:
            vp = getattr(node, "_virtual_parent_key", None)
            if vp in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY):
                if self.translation_editor:
                    field_id = node.key
                    if vp == self.VIRTUAL_TRANSLATION_KEY:
                        return self.translation_editor.get_name(field_id)
                    return self.translation_editor.get_desc(field_id)
            return node.value

        if role == Qt.ItemDataRole.ToolTipRole:
            if node.key in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY) and node.parent == self.root_node:
                return f"点击展开查看{node.key}详情"
            return f"类型: {'块' if node.node_type == 'block' else '值'}\n键: {node.key}\n值: {node.value}"

        if role == Qt.ItemDataRole.UserRole:
            return node

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        node = self._safe_pointer(index)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        # 翻译/描述条目支持直接编辑翻译文本
        if getattr(node, "_virtual_parent_key", None) in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        """编辑翻译/描述条目的翻译文本，并保存到 mod 翻译文件。"""
        if role != Qt.ItemDataRole.EditRole:
            return False
        if not index.isValid():
            return False
        node = self._safe_pointer(index)
        vp = getattr(node, "_virtual_parent_key", None)
        if vp not in (self.VIRTUAL_TRANSLATION_KEY, self.VIRTUAL_DESCRIPTION_KEY):
            return False
        if not self.translation_editor:
            return False
        field_id = node.key
        new_text = str(value)
        try:
            if vp == self.VIRTUAL_TRANSLATION_KEY:
                ok = self.translation_editor.save_name(field_id, new_text)
            else:
                ok = self.translation_editor.save_desc(field_id, new_text)
            if not ok:
                return False
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            # 通知编辑器：翻译已保存，供刷新本地化缓存与重绘国策节点
            editor = QObject.parent(self)  # QAbstractItemModel.parent() 需要 index，此处取 QObject 父级
            if editor is not None and hasattr(editor, "translation_saved"):
                editor.translation_saved.emit(field_id)
            return True
        except Exception:
            return False

    def insert_node(self, parent_index: QModelIndex, node: TreeNode, row=-1):
        parent_node = self.node_from_index(parent_index)
        if parent_node.node_type != "block":
            return
        if row < 0 or row > len(parent_node.children):
            row = len(parent_node.children)
        self.beginInsertRows(parent_index, row, row)
        parent_node.add_child(node, row)
        self.endInsertRows()

    def remove_node(self, index: QModelIndex):
        if not index.isValid():
            return
        node = self._safe_pointer(index)
        if node is None or node == self.root_node or node.parent is None:
            return
        parent_index = self.parent(index)
        parent_node = node.parent
        row = node.child_index()
        if row < 0:
            return
        self.beginRemoveRows(parent_index, row, row)
        parent_node.remove_child(node)
        self.endRemoveRows()

    def add_node(self, node: TreeNode, parent_index: QModelIndex = None):
        """添加节点到指定父节点下（默认根节点）。

        Args:
            node (TreeNode): 新节点
            parent_index (QModelIndex, optional): 父节点索引
        """
        if parent_index is None or not parent_index.isValid():
            parent_node = self.root_node
            parent_index = QModelIndex()
        else:
            parent_node = self._safe_pointer(parent_index)
            if parent_node is None:
                parent_node = self.root_node
                parent_index = QModelIndex()
        row = len(parent_node.children)
        self.beginInsertRows(parent_index, row, row)
        parent_node.add_child(node, row)
        self.endInsertRows()

    def index_from_node(self, node: TreeNode) -> QModelIndex:
        """由节点查找其 QModelIndex（递归）。

        Args:
            node (TreeNode): 目标节点
        Returns:
            QModelIndex: 节点的索引；根节点或未找到时返回 QModelIndex()
        """
        if node is None or node == self.root_node:
            return QModelIndex()
        parent_index = self.index_from_node(node.parent) if node.parent else QModelIndex()
        row = node.child_index()
        if row < 0:
            return QModelIndex()
        return self.index(row, 0, parent_index)

    def find_nodes(self, keyword: str) -> list:
        results = []
        if self.translator:
            kw_lower = keyword.lower()

            def _match(node):
                cn_key, cn_val = self.translator.translate_node(node.key, node.value)
                if kw_lower in cn_key.lower() or kw_lower in node.key.lower():
                    return True
                if cn_val and (kw_lower in cn_val.lower() or kw_lower in node.value.lower()):
                    return True
                return False

            def _search(node, parent_index):
                for i, child in enumerate(node.children):
                    idx = self.createIndex(i, 0, child)
                    if _match(child):
                        results.append(idx)
                    _search(child, idx)

            _search(self.root_node, QModelIndex())
        return results
