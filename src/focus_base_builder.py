"""国策树编辑器模块

提供 FocusTreeEditor 类，是 GenericTreeEditor 的国策树特化子类。
负责将国策（Focus）的加载数据转换为可在通用编辑器中编辑的树结构，
并处理国策树特有的保存逻辑（如包装行的国策类型标识）。
"""

from generic_tree_editor import GenericTreeEditor


class FocusTreeEditor(GenericTreeEditor):
    """国策树编辑器 - 继承通用编辑器，保留 focus 特有逻辑

    在 GenericTreeEditor 的通用能力基础上，增加了国策树特有的功能：
    - 从 FocusLoad 对象构建 TreeNode 根节点
    - 自动检测国策类型（focus / shared_focus / joint_focus）
    - 保存时使用正确的包装格式

    Attributes:
        focus_load: 国策加载数据对象（包含已知字段等）
        raw_fields (dict): 原始字段数据（不被解析器标准化的字段）
    """

    def __init__(self, focus_load, file_path, file_lines, block_range, x_val, y_val,
                 translator=None, custom_statement_path="",
                 raw_fields=None, parent=None, loc_manager=None,
                 hoi4_path="", mod_path=""):
        """初始化国策树编辑器

        Args:
            focus_load: 国策加载数据对象（FocusLoad 实例）
            file_path (str): 编辑的文件路径
            file_lines (list[str]): 文件完整行列表
            block_range (tuple): 编辑块在文件中的 (起始行号, 结束行号)
            x_val: 国策在树形图中的 X 坐标
            y_val: 国策在树形图中的 Y 坐标
            translator (GuiTranslator, optional): 翻译器实例
            custom_statement_path (str, optional): 自定义语句文件路径
            raw_fields (dict, optional): 原始字段数据
            parent (QWidget, optional): 父窗口
            loc_manager (optional): 本地化管理器
            hoi4_path (str): 钢铁雄心4游戏目录路径
            mod_path (str): MOD 目录路径
        """
        self.focus_load = focus_load
        self.raw_fields = raw_fields or {}

        # 根据 FocusLoad 构建根节点
        root_node = self._build_root_node(focus_load, x_val, y_val)

        # 调用父类初始化（复用通用编辑器功能）
        super().__init__(
            root_node=root_node,
            file_path=file_path,
            file_lines=file_lines,
            block_range=block_range,
            translator=translator,
            custom_statement_path=custom_statement_path,
            loc_manager=loc_manager,
            parent=parent,
            title="国策编辑",
            hoi4_path=hoi4_path,
            mod_path=mod_path
        )

    def _build_root_node(self, focus_load, x_val, y_val):
        """从 FocusLoad 构建 TreeNode 根节点

        使用 TreeNode.from_focus_load 工厂方法将国策加载数据
        转换为树结构。该方法会自动处理 focus 的嵌套块结构，
        并将 raw_fields 中的原始字段附加到节点上。

        为了让树编辑器展示国策的上一层（focus 块本身），
        根节点使用一个包装容器，其下唯一的子节点为 focus 块，
        该块允许用户直接查看和编辑。

        Args:
            focus_load: 国策加载数据对象
            x_val: 国策的 X 坐标
            y_val: 国策的 Y 坐标
            raw_fields (dict): 原始字段数据

        Returns:
            TreeNode: 构建完成的根节点
        """
        from tree_node import TreeNode
        focus_block = TreeNode.from_focus_load(focus_load, x_val, y_val, raw_fields=self.raw_fields)
        # 使用实际国策类型作为块键名（focus / shared_focus / joint_focus）
        focus_type = focus_load.known.get('__focus_type__', 'focus')
        focus_block.key = focus_type
        root = TreeNode("block", "(focus)")
        root.add_child(focus_block)
        return root

    def _get_wrapper_start(self, indent):
        """获取保存时的包装起始行

        优先使用树中可编辑的包装块（focus 块）的键名，
        若用户修改了块名则以其为准；否则根据国策类型动态生成包装行。
        例如：
        - 普通国策：focus = {
        - 共享国策：shared_focus = {
        - 联合国策：joint_focus = {

        Args:
            indent (str): 缩进字符串

        Returns:
            str: 包装起始行
        """
        block = self._get_editable_wrapper_block()
        if block is not None:
            return f"{indent}{block.key} = {{"
        # 从 FocusLoad 的 known 字典中获取国策类型标识
        focus_type = self.focus_load.known.get('__focus_type__', 'focus')
        return f"{indent}{focus_type} = {{"
