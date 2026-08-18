import re

# 无空格日期字符串字段：裸写会被引擎按数字截断解析（如 1939.1.1 → 1939.1），
# 序列化时强制加双引号
DATE_QUOTED_KEYS = {"expire", "date", "created"}

# 含中文的键：PDX 引擎将裸键按 ASCII 标识符解析，中文键必须用双引号包裹
CJK_KEY_RE = re.compile(r'[\u4e00-\u9fff]')

# 比较运算符（触发/效果语句中的 `key >= 100` 等）。多字符运算符必须排在前面，
# 否则 `>=` 会被 `>` 抢先切成两个 token。
COMPARE_OPERATORS = (">=", "<=", "==", "!=", ">", "<")


def quote_cjk_key(key):
    """若键含中文字符且尚未被引号包裹，则返回双引号包裹后的键，否则原样返回。"""
    if key and not key.startswith('"') and CJK_KEY_RE.search(key):
        return f'"{key}"'
    return key


class TreeNode:
    """递归树节点：用于表示 Paradox 游戏引擎 PDX 脚本结构化数据中的一个节点。

    每个节点可以是两种类型之一：
    - "value"：键值对节点（如 `key = value`）
    - "block"：块节点（如 `key = { ... }`），包含子节点列表
    """

    def __init__(self, node_type="value", key="", value="", parent=None, raw_lines=None):
        """初始化树节点。

        参数:
            node_type: 节点类型，可选 "value" 或 "block"
            key: 节点的键名
            value: 节点的值（值节点存字符串，块节点通常为空）
            parent: 父节点引用
            raw_lines: 原始文本行列表，用于保留原始格式
        """
        self.node_type = node_type
        self.key = key
        self.value = value
        self.children = []
        self.parent = parent
        self.raw_lines = raw_lines if raw_lines is not None else []

    def add_child(self, node, position=-1):
        """向当前节点添加子节点。

        参数:
            node: 要添加的子 TreeNode 对象
            position: 插入位置，-1 表示追加到末尾，>=0 表示插入到指定索引
        """
        node.parent = self  # 设置子节点的父节点引用
        if position < 0:
            self.children.append(node)  # 追加到末尾
        else:
            self.children.insert(position, node)  # 插入到指定位置

    def remove_child(self, node):
        """从子节点列表中移除指定节点。"""
        if node in self.children:
            self.children.remove(node)
            node.parent = None  # 清除被移除节点的父节点引用

    def child_index(self):
        """返回当前节点在父节点子列表中的索引，若没有父节点返回 -1。"""
        if self.parent:
            return self.parent.children.index(self)
        return -1

    def move_up(self):
        """将当前节点在父节点子列表中向上移动一位（与前一节点交换）。"""
        idx = self.child_index()
        if idx > 0 and self.parent:
            # 交换当前节点与前一节点的位置
            self.parent.children[idx], self.parent.children[idx - 1] = \
                self.parent.children[idx - 1], self.parent.children[idx]

    def move_down(self):
        """将当前节点在父节点子列表中向下移动一位（与后一节点交换）。"""
        idx = self.child_index()
        if idx >= 0 and self.parent and idx < len(self.parent.children) - 1:
            # 交换当前节点与后一节点的位置
            self.parent.children[idx], self.parent.children[idx + 1] = \
                self.parent.children[idx + 1], self.parent.children[idx]

    def to_pdx(self, indent=0):
        """将当前节点子树序列化为 PDX 格式文本字符串。

        参数:
            indent: 当前缩进级别（制表符数量）
        返回:
            格式化后的 PDX 文本行
        """
        tabs = "\t" * indent  # 根据缩进级别生成制表符
        if self.node_type == "value":
            # 如果有原始行，优先使用原始文本（保留用户原始格式）
            if self.raw_lines:
                return "\n".join(tabs + line if i == 0 else line for i, line in enumerate(self.raw_lines))
            v = self.value
            # 日期类字段：无空格裸写会被引擎按数字截断解析，强制加双引号
            if self.key in DATE_QUOTED_KEYS and v and not v.startswith('"'):
                v = f'"{v}"'
            # 如果值包含空格且未加引号，自动加双引号
            if " " in v and not v.startswith('"') and not v.startswith("{"):
                v = f'"{v}"'
            # 键名为空时直接输出值
            if not self.key:
                return f"{tabs}{v}"
            return f"{tabs}{quote_cjk_key(self.key)} = {v}"
        else:
            # 块节点：如果有原始行，使用原始文本
            if self.raw_lines:
                return "\n".join(tabs + line for line in self.raw_lines)
            # 空块节点
            if not self.children:
                return f"{tabs}{quote_cjk_key(self.key)} = {{ }}"
            # 递归序列化子节点，用大括号包裹
            inner = "\n".join(c.to_pdx(indent + 1) for c in self.children)
            return f"{tabs}{quote_cjk_key(self.key)} = {{\n{inner}\n{tabs}}}"

    def clone(self):
        """深拷贝当前节点及其所有子节点，返回一个完全独立的副本。"""
        new_node = TreeNode(self.node_type, self.key, self.value, raw_lines=list(self.raw_lines))
        for child in self.children:
            new_node.add_child(child.clone())  # 递归克隆子节点
        return new_node

    def __repr__(self):
        """返回节点的可读字符串表示，用于调试。"""
        if self.node_type == "block":
            return f"Block({self.key}, children={len(self.children)})"
        return f"Value({self.key}={self.value})"

    @staticmethod
    def from_focus_load(focus_load, x_val="", y_val="", raw_fields=None):
        """从 FocusLoad 结构体解析为 TreeNode 树，保留原始 raw_lines。

        将反序列化后的 Python 数据对象（focus_load.known）转换为 TreeNode 树结构，
        同时尽可能保留原始 PDX 文本行的格式信息。

        参数:
            focus_load: 包含 known 属性的反序列化对象
            x_val: x 坐标值（字符串）
            y_val: y 坐标值（字符串）
            raw_fields: 字段名到原始文本行的映射字典
        返回:
            TreeNode 根节点（"focus" 块节点）
        """
        root = TreeNode("block", "focus")
        known = focus_load.known
        raw_fields = raw_fields or {}

        # 解析 id 字段（必选）
        root.add_child(TreeNode("value", "id", focus_load.focus_id,
                                raw_lines=raw_fields.get("id")))

        # 解析 icon 字段（允许空值：模板带 icon 词条的国策保留该条目，供后续编辑）
        if 'icon' in known and known.icon is not None:
            icon_val = known.icon
            if isinstance(icon_val, list):
                icon_val = icon_val[0]  # 列表类型取第一个
            root.add_child(TreeNode("value", "icon", str(icon_val or "").strip('"'),
                                    raw_lines=raw_fields.get("icon")))

        # 解析位置坐标 x
        if x_val:
            root.add_child(TreeNode("value", "x", str(x_val),
                                    raw_lines=raw_fields.get("x")))

        # 解析位置坐标 y
        if y_val:
            root.add_child(TreeNode("value", "y", str(y_val),
                                    raw_lines=raw_fields.get("y")))

        # 解析 cost 字段
        if known.cost is not None:
            root.add_child(TreeNode("value", "cost", str(known.cost),
                                    raw_lines=raw_fields.get("cost")))

        # 解析 relative_position_id 字段
        if known.relative_position_id:
            root.add_child(TreeNode("value", "relative_position_id", known.relative_position_id,
                                    raw_lines=raw_fields.get("relative_position_id")))

        # 解析 offset 块（位置偏移信息）
        if raw_fields.get("offset"):
            for offset_text in raw_fields["offset"]:
                child = TreeNode("block", "offset", raw_lines=offset_text)
                root.add_child(child)

        # 解析 search_filters 字段
        if known.search_filters:
            raw = raw_fields.get("search_filters")
            node = TreeNode("block", "search_filters", raw_lines=raw)
            filters = known.search_filters if isinstance(known.search_filters, list) else [known.search_filters]
            for f in filters:
                node.add_child(TreeNode("value", f.strip("{} ").strip(), ""))
            root.add_child(node)

        # 解析 prerequisite 前置条件
        if known.prerequisite:
            prereqs = known.prerequisite if isinstance(known.prerequisite, list) else [known.prerequisite]
            raw_prereqs = raw_fields.get("prerequisite", [])
            # 规范化原始行数据：确保是列表的列表
            if isinstance(raw_prereqs, list) and raw_prereqs and isinstance(raw_prereqs[0], list):
                pass  # 已是列表的列表格式
            else:
                raw_prereqs = [raw_prereqs] if raw_prereqs else []
            for pi, p in enumerate(prereqs):
                raw = raw_prereqs[pi] if pi < len(raw_prereqs) else None
                if isinstance(raw, str):
                    raw = [raw]
                node = TreeNode("block", "prerequisite", raw_lines=raw)
                block_text = p.strip()
                # 解析大括号内的 focus 引用
                if block_text.startswith("{") and block_text.endswith("}"):
                    inner = block_text[1:-1].strip()
                    focus_ids = re.findall(r'focus\s*=\s*([\w\.\-]+)', inner)
                    for fid in focus_ids:
                        node.add_child(TreeNode("value", "focus", fid))
                else:
                    node.add_child(TreeNode("value", "focus", block_text))
                root.add_child(node)

        # 解析 mutually_exclusive 互斥关系
        if known.mutually_exclusive:
            mutex = known.mutually_exclusive if isinstance(known.mutually_exclusive, list) else [known.mutually_exclusive]
            raw_mutex = raw_fields.get("mutually_exclusive", [])
            # 规范化原始行数据
            if isinstance(raw_mutex, list) and raw_mutex and isinstance(raw_mutex[0], list):
                pass
            else:
                raw_mutex = [raw_mutex] if raw_mutex else []
            for mi, m in enumerate(mutex):
                raw = raw_mutex[mi] if mi < len(raw_mutex) else None
                if isinstance(raw, str):
                    raw = [raw]
                node = TreeNode("block", "mutually_exclusive", raw_lines=raw)
                block_text = m.strip()
                # 解析大括号内的 focus 引用
                if block_text.startswith("{") and block_text.endswith("}"):
                    inner = block_text[1:-1].strip()
                    focus_ids = re.findall(r'focus\s*=\s*([\w\.\-]+)', inner)
                    for fid in focus_ids:
                        node.add_child(TreeNode("value", "focus", fid))
                else:
                    node.add_child(TreeNode("value", "focus", block_text))
                root.add_child(node)

        # 解析 will_lead_to_war_with 字段
        if known.will_lead_to_war_with:
            val = known.will_lead_to_war_with
            if isinstance(val, list):
                val = val[0]
            root.add_child(TreeNode("value", "will_lead_to_war_with", str(val).strip('"'),
                                    raw_lines=raw_fields.get("will_lead_to_war_with")))

        # 批量解析布尔类型字段
        bool_fields = [
            "dynamic", "text_icon", "available_if_capitulated", "cancelable",
            "bypass_if_unavailable", "continue_if_invalid", "cancel_if_invalid",
        ]
        for field_name in bool_fields:
            val = getattr(known, field_name, None)
            if val is not None:
                v = str(val).strip('"')
                root.add_child(TreeNode("value", field_name, v,
                                        raw_lines=raw_fields.get(field_name)))

        # 批量解析多块类型字段（ai_will_do, available, allow_branch 等）
        multi_block_fields = [
            ("ai_will_do", _parse_ai_will_do),       # AI 意愿计算块
            ("available", _parse_block_field),        # 可用条件块
            ("allow_branch", _parse_block_field),     # 允许分支块
            ("select_effect", _parse_block_field),    # 选择效果块
            ("bypass", _parse_block_field),           # 绕过条件块
            ("historical_ai", _parse_block_field),    # 历史 AI 行为块
            ("cancel", _parse_block_field),           # 取消条件块
        ]
        for field_name, parser_fn in multi_block_fields:
            val = getattr(known, field_name, None)
            if val is None:
                continue  # 字段不存在则跳过
            raw = raw_fields.get(field_name)
            items = val if isinstance(val, list) else [val]
            # 规范化原始数据为列表格式
            if isinstance(raw, list) and raw and isinstance(raw[0], list):
                raw_list = raw
            else:
                raw_list = [raw] * len(items) if raw else [None] * len(items)
            for idx, item in enumerate(items):
                raw_item = raw_list[idx] if idx < len(raw_list) else None
                if isinstance(raw_item, str):
                    raw_item = [raw_item]
                node = TreeNode("block", field_name, raw_lines=raw_item)
                if field_name == "ai_will_do":
                    parser_fn(node, item)  # ai_will_do 使用专门的解析器
                else:
                    parser_fn(node, field_name, item)  # 其他使用通用块解析器
                root.add_child(node)

        # 解析 completion_reward 完成奖励
        if known.completion_reward:
            val = known.completion_reward
            raw = raw_fields.get("completion_reward")
            items = val if isinstance(val, list) else [val]
            if isinstance(raw, list) and raw and isinstance(raw[0], list):
                raw_list = raw
            else:
                raw_list = [raw] * len(items) if raw else [None] * len(items)
            for idx, item in enumerate(items):
                raw_item = raw_list[idx] if idx < len(raw_list) else None
                if isinstance(raw_item, str):
                    raw_item = [raw_item]
                node = TreeNode("block", "completion_reward", raw_lines=raw_item)
                _parse_completion_reward(node, item)
                root.add_child(node)

        # 解析未知字段（反序列化中未显式定义的字段）
        if known.unknown:
            for uk, uv in known.unknown.items():
                root.add_child(TreeNode("value", uk, str(uv).strip('"') if isinstance(uv, str) else str(uv[0]).strip('"'),
                                        raw_lines=raw_fields.get(uk)))

        return root


def _parse_ai_will_do(parent, data):
    """解析 ai_will_do 数据为树节点，挂载到 parent 节点下。

    支持两种数据格式：
    1. dict 格式：{'base': ..., 'factor': ..., 'modifier': [...]}
    2. 字符串格式：PDX 文本块字符串

    参数:
        parent: 父 TreeNode 节点
        data: 要解析的 ai_will_do 数据（dict 或 str）
    """
    # 处理字典类型的 ai_will_do 数据
    if isinstance(data, dict):
        if "base" in data:
            parent.add_child(TreeNode("value", "base", str(data["base"])))
        if "factor" in data:
            parent.add_child(TreeNode("value", "factor", str(data["factor"])))
        if "modifier" in data:
            mods = data["modifier"] if isinstance(data["modifier"], list) else [data["modifier"]]
            for mod in mods:
                mod_node = TreeNode("block", "modifier")
                if isinstance(mod, dict):
                    for k, v in mod.items():
                        if isinstance(v, dict):
                            # 嵌套字典：创建子块节点
                            sub = TreeNode("block", k)
                            for sk, sv in v.items():
                                sub.add_child(TreeNode("value", sk, str(sv)))
                            mod_node.add_child(sub)
                        elif isinstance(v, list):
                            # 列表值：每条作为独立值节点
                            for item in v:
                                mod_node.add_child(TreeNode("value", k, str(item)))
                        else:
                            # 简单值
                            mod_node.add_child(TreeNode("value", k, str(v)))
                parent.add_child(mod_node)
        return

    # 处理字符串类型的 ai_will_do 数据
    text = str(data).strip()
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()  # 去除外层大括号
    else:
        inner = text

    # 正则提取 base 值
    base_m = re.search(r'base\s*=\s*([\d\.]+)', inner)
    if base_m:
        parent.add_child(TreeNode("value", "base", base_m.group(1)))

    # 正则提取 factor 值
    factor_m = re.search(r'factor\s*=\s*([\d\.]+)', inner)
    if factor_m:
        parent.add_child(TreeNode("value", "factor", factor_m.group(1)))

    # 构建一个包含所有条件修饰器的 true_node
    true_node = TreeNode("block", "ai_will_do")
    if base_m:
        true_node.add_child(TreeNode("value", "factor", base_m.group(1)))

    # 解析 modifier 块（支持嵌套大括号）
    modifier_blocks = re.finditer(r'modifier\s*=\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', inner)
    for m in modifier_blocks:
        mod_text = m.group(1)
        mod_node = TreeNode("block", "modifier")
        _parse_inline_block(mod_node, mod_text)  # 递归解析修饰器内容
        true_node.add_child(mod_node)

    if true_node.children:
        parent.add_child(true_node)


def _parse_block_field(parent, key, data):
    """解析一个通用块字段的内容到 parent 节点中（不创建额外的嵌套块）。

    支持递归处理嵌套的字符串、列表和字典数据。

    参数:
        parent: 父 TreeNode 节点（数据将直接添加到其子节点中）
        key: 字段名
        data: 要解析的数据（str, list, 或 dict）
    """
    if isinstance(data, str):
        text = data.strip()
        # 如果是以大括号包裹的块文本，进行内联解析
        if text.startswith("{") and text.endswith("}"):
            _parse_inline_block(parent, text)
        else:
            parent.add_child(TreeNode("value", key, text))
    elif isinstance(data, list):
        # 列表中的每一项递归处理
        for item in data:
            _parse_block_field(parent, key, item)
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                # 复合值创建子块节点
                sub = TreeNode("block", k)
                _parse_block_field(sub, k, v)
                parent.add_child(sub)
            else:
                # 简单值
                parent.add_child(TreeNode("value", k, str(v)))


def _parse_completion_reward(parent, data):
    """解析 completion_reward 字段，将 hidden_effect 子块分离出来。

    hidden_effect 块会被提取为独立的子节点，其余内容直接内联解析
    到 parent 节点的子节点中。

    参数:
        parent: 父 TreeNode 节点
        data: completion_reward 的字符串数据
    """
    text = str(data).strip()
    # 不是大括号块，作为简单值处理
    if not (text.startswith("{") and text.endswith("}")):
        parent.add_child(TreeNode("value", "completion_reward", text))
        return

    inner = text[1:-1].strip()  # 去除外层大括号

    # 正则匹配所有的 hidden_effect 块（支持嵌套大括号）
    hidden_pattern = re.compile(r'hidden_effect\s*=\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})')
    hidden_matches = list(hidden_pattern.finditer(inner))

    remaining = inner
    hidden_texts = []

    # 从后往前移除 hidden_effect 块，避免索引偏移
    for m in reversed(hidden_matches):
        hidden_texts.insert(0, m.group(1))
        remaining = remaining[:m.start()] + remaining[m.end():]

    # 解析剩余的非 hidden_effect 内容
    _parse_inline_block(parent, "{" + remaining.strip() + "}")

    # 将每个 hidden_effect 块作为独立子节点加入
    for ht in hidden_texts:
        he_node = TreeNode("block", "hidden_effect")
        _parse_inline_block(he_node, ht)
        parent.add_child(he_node)


def _parse_inline_block(parent, block_text):
    """解析 PDX 块文本（含嵌套）并将解析结果作为子节点添加到 parent 中。

    这是核心的递归下降解析器，将 token 列表还原为 TreeNode 树结构。

    参数:
        parent: 父 TreeNode 节点
        block_text: 要解析的块文本字符串（可含大括号）
    """
    text = block_text.strip()
    # 去除可选的外层大括号
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1].strip()

    if not text:
        return  # 空块直接返回

    tokens = _tokenize(text)  # 分词（带行号）
    _parse_tokens(parent, tokens, 0, len(tokens))


def _parse_tokens(parent, tokens, start, end):
    """解析 token 列表的指定范围，将结果添加到 parent 节点中。

    直接操作 token 列表和索引，保留行号信息以正确处理空值。

    参数:
        parent: 父 TreeNode 节点
        tokens: (token, line_number) 元组列表
        start: 起始索引（包含）
        end: 结束索引（不包含）
    """
    i = start
    while i < end:
        tok, line = tokens[i]
        # 跳过等号和右大括号 token
        if tok in ("=", "}"):
            i += 1
            continue

        key = tok
        # 检查是否是 key = value 或 key = { ... } 格式
        if i + 1 < end and tokens[i + 1][0] == "=":
            _, eq_line = tokens[i + 1]
            i += 2  # 跳过键和等号
            if i < end:
                next_tok, next_line = tokens[i]
                # 如果 = 和下一个 token 不在同一行，说明是空值
                if next_line != eq_line:
                    parent.add_child(TreeNode("value", key, ""))
                    continue
                if next_tok == "{":
                    # 块值：匹配嵌套大括号的起止位置
                    depth = 1
                    block_end = i + 1
                    while block_end < end and depth > 0:
                        if tokens[block_end][0] == "{":
                            depth += 1
                        elif tokens[block_end][0] == "}":
                            depth -= 1
                        block_end += 1
                    sub = TreeNode("block", key)
                    _parse_tokens(sub, tokens, i, block_end - 1)  # 递归解析块内部
                    parent.add_child(sub)
                    i = block_end
                else:
                    # 简单值：去除引号后存储
                    val = next_tok.strip('"')
                    parent.add_child(TreeNode("value", key, val))
                    i += 1
            else:
                # = 后面没有 token，空值
                parent.add_child(TreeNode("value", key, ""))
                i += 1
        else:
            # 比较语句：`key >= 100` / `key < value`（无等号，出现在触发/效果块中）
            # 将 key + 运算符 + 值合并为单个语句节点，避免被拆成多个空值节点；
            # 用 raw_lines 保留原样，序列化时不加引号、不加等号。
            if (i + 2 < end and tokens[i + 1][0] in COMPARE_OPERATORS):
                op = tokens[i + 1][0]
                stmt_val = tokens[i + 2][0].strip('"')
                stmt_text = "%s %s %s" % (key, op, stmt_val)
                parent.add_child(TreeNode("value", "", stmt_text,
                                          raw_lines=[stmt_text]))
                i += 3
                continue
            # 独立 token（无等号），作为空值节点
            if key not in ("{", "}"):
                parent.add_child(TreeNode("value", key, ""))
            i += 1


def _strip_comments(text):
    """去除 PDX 文本中的 # 注释（引号内的 # 字符保留）。

    逐字符扫描，遇到 # 且不在双引号字符串内时截断该行，
    避免中文注释被分词为垃圾节点。
    """
    out_lines = []
    in_str = False
    for line in text.split("\n"):
        out = []
        for ch in line:
            if ch == '"':
                in_str = not in_str
                out.append(ch)
            elif ch == "#" and not in_str:
                break
            else:
                out.append(ch)
        out_lines.append("".join(out))
    return "\n".join(out_lines)


def _tokenize(text):
    """PDX 分词器：将 PDX 文本拆分为带行号的 token 列表。

    识别以下 token 类型：
    - 大括号 { }
    - 等号 =
    - 双引号字符串 "..."
    - 比较运算符 >= <= == != > <
    - 标识符（字母、数字、点、连字符）

    参数:
        text: 原始 PDX 文本字符串
    返回:
        (token, line_number) 元组列表，line_number 为 1-indexed
    """
    text = _strip_comments(text)
    tokens = []
    for m in re.finditer(r'\{|\}|>=|<=|==|!=|=|>|<|"[^"]*"|[\w\.\-]+', text):
        line_no = text[:m.start()].count('\n') + 1
        tokens.append((m.group(0), line_no))
    return tokens


def parse_pdx_block_to_tree(text, key="(root)"):
    """将 PDX 块文本解析为 TreeNode 树结构。

    这是一个便捷入口函数，用于将原始 PDX 文本字符串转换为
    程序可操作的树形数据结构。

    参数:
        text: PDX 块文本字符串
        key: 根节点的键名，默认为 "(root)"
    返回:
        TreeNode 根节点
    """
    root = TreeNode("block", key)
    _parse_inline_block(root, text)
    return root


def parse_pdx_text_to_nodes(text):
    """将多行 PDX 文本解析为子节点的列表（与 parse_pdx_block_to_tree 类似但不创建根节点）。

    适用于需要直接将多个顶级条目解析为独立节点的场景。

    参数:
        text: 多行 PDX 文本字符串
    返回:
        TreeNode 节点列表
    """
    nodes = []
    text = text.strip()
    if not text:
        return nodes

    tokens = _tokenize(text)  # 分词（带行号）
    # 使用一个临时根节点来解析，然后取其子节点
    temp_root = TreeNode("block", "__temp__")
    _parse_tokens(temp_root, tokens, 0, len(tokens))
    return temp_root.children


def tree_from_pdx_text(text):
    """解析 PDX 多行文本为完整 TreeNode 树（用于粘贴 PDX 内容）。

    与 parse_pdx_block_to_tree 的区别在于此函数假设文本是多行格式，
    每一行可能是一个独立的顶级条目。

    参数:
        text: 多行 PDX 文本字符串
    返回:
        TreeNode 根节点（类型为 "(paste_root)"）
    """
    root = TreeNode("block", "(paste_root)")
    children = parse_pdx_text_to_nodes(text)
    for child in children:
        root.add_child(child)
    return root
