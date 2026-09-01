from bisect import bisect_right

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
        # 保真保存相关属性一并拷贝（撤销快照恢复后仍能保真序列化）
        for attr in ("_tok_span", "_verbatim_lead", "_verbatim_tail"):
            val = getattr(self, attr, None)
            if val is not None:
                setattr(new_node, attr, list(val))
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

        if known.prerequisite:
            _add_prerequisite_nodes(
                root, known.prerequisite, raw_fields.get("prerequisite", []))

        if known.mutually_exclusive:
            _add_mutex_nodes(
                root, known.mutually_exclusive, raw_fields.get("mutually_exclusive", []))

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
            _add_multi_block_nodes(
                root, field_name, parser_fn,
                getattr(known, field_name, None), raw_fields.get(field_name))

        _add_completion_reward_nodes(
            root, known.completion_reward, raw_fields.get("completion_reward"))

        _add_unknown_fields(root, known.unknown, raw_fields)

        return root



def _normalize_raw_items(raw, count):
    """把原始行字段规范化为与条目数等长的列表（每项可含多行）。"""
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        raw_list = raw
    else:
        raw_list = [raw] * count if raw else [None] * count
    out = []
    for idx in range(count):
        item = raw_list[idx] if idx < len(raw_list) else None
        if isinstance(item, str):
            item = [item]
        out.append(item)
    return out


def _add_prerequisite_nodes(root, prereq, raw_prereqs):
    """把 prerequisite 字段转为 block 节点挂到 root。"""
    prereqs = prereq if isinstance(prereq, list) else [prereq]
    raw_list = _normalize_raw_items(raw_prereqs, len(prereqs))
    for pi, p in enumerate(prereqs):
        node = TreeNode("block", "prerequisite", raw_lines=raw_list[pi])
        block_text = p.strip()
        if block_text.startswith("{") and block_text.endswith("}"):
            inner = block_text[1:-1].strip()
            for fid in re.findall(r'focus\s*=\s*([\w\.\-]+)', inner):
                node.add_child(TreeNode("value", "focus", fid))
        else:
            node.add_child(TreeNode("value", "focus", block_text))
        root.add_child(node)


def _add_mutex_nodes(root, mutex, raw_mutex):
    """把 mutually_exclusive 字段转为 block 节点挂到 root。"""
    mutex_list = mutex if isinstance(mutex, list) else [mutex]
    raw_list = _normalize_raw_items(raw_mutex, len(mutex_list))
    for mi, m in enumerate(mutex_list):
        node = TreeNode("block", "mutually_exclusive", raw_lines=raw_list[mi])
        block_text = m.strip()
        if block_text.startswith("{") and block_text.endswith("}"):
            inner = block_text[1:-1].strip()
            for fid in re.findall(r'focus\s*=\s*([\w\.\-]+)', inner):
                node.add_child(TreeNode("value", "focus", fid))
        else:
            node.add_child(TreeNode("value", "focus", block_text))
        root.add_child(node)


def _add_multi_block_nodes(root, field_name, parser_fn, val, raw):
    """批量解析 ai_will_do/available/allow_branch 等多块字段。"""
    if val is None:
        return
    items = val if isinstance(val, list) else [val]
    raw_list = _normalize_raw_items(raw, len(items))
    for idx, item in enumerate(items):
        node = TreeNode("block", field_name, raw_lines=raw_list[idx])
        if field_name == "ai_will_do":
            parser_fn(node, item)
        else:
            parser_fn(node, field_name, item)
        root.add_child(node)


def _add_completion_reward_nodes(root, val, raw):
    """解析 completion_reward 字段的多个块。"""
    if not val:
        return
    items = val if isinstance(val, list) else [val]
    raw_list = _normalize_raw_items(raw, len(items))
    for idx, item in enumerate(items):
        node = TreeNode("block", "completion_reward", raw_lines=raw_list[idx])
        _parse_completion_reward(node, item)
        root.add_child(node)


def _add_unknown_fields(root, unknown, raw_fields):
    """把反序列化未识别的字段作为 value 节点挂到 root。"""
    if not unknown:
        return
    for uk, uv in unknown.items():
        v = str(uv).strip('"') if isinstance(uv, str) else str(uv[0]).strip('"')
        root.add_child(TreeNode("value", uk, v, raw_lines=raw_fields.get(uk)))

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
    tokens 为 (token, line_number, char_pos) 三元组；同时为每个节点记录
    ``_tok_span = (起始 token 下标, 结束 token 下标+1)``，供
    :func:`attach_verbatim_lines` 映射回原文行（通用树保真保存用）。

    参数:
        parent: 父 TreeNode 节点
        tokens: (token, line_number, char_pos) 三元组列表
        start: 起始索引（包含）
        end: 结束索引（不包含）
    """
    i = start
    while i < end:
        tok = tokens[i][0]
        line = tokens[i][1]
        # 跳过等号和右大括号 token
        if tok in ("=", "}"):
            i += 1
            continue

        key = tok
        # 检查是否是 key = value 或 key = { ... } 格式
        if i + 1 < end and tokens[i + 1][0] == "=":
            eq_line = tokens[i + 1][1]
            i += 2  # 跳过键和等号
            if i < end:
                next_tok = tokens[i][0]
                next_line = tokens[i][1]
                # 如果 = 和下一个 token 不在同一行，说明是空值
                if next_line != eq_line:
                    node = TreeNode("value", key, "")
                    node._tok_span = (i - 2, i)
                    parent.add_child(node)
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
                    sub._tok_span = (i - 2, block_end)
                    _parse_tokens(sub, tokens, i, block_end - 1)  # 递归解析块内部
                    parent.add_child(sub)
                    i = block_end
                else:
                    # 简单值：去除引号后存储
                    val = next_tok.strip('"')
                    node = TreeNode("value", key, val)
                    node._tok_span = (i - 2, i + 1)
                    parent.add_child(node)
                    i += 1
            else:
                # = 后面没有 token，空值
                node = TreeNode("value", key, "")
                node._tok_span = (i - 2, end)
                parent.add_child(node)
                i += 1
        else:
            # 比较语句：`key >= 100` / `key < value`（无等号，出现在触发/效果块中）
            # 将 key + 运算符 + 值合并为单个语句节点，避免被拆成多个空值节点；
            # 用 raw_lines 保留原样，序列化时不加引号、不加等号。
            if (i + 2 < end and tokens[i + 1][0] in COMPARE_OPERATORS):
                op = tokens[i + 1][0]
                stmt_val = tokens[i + 2][0].strip('"')
                stmt_text = "%s %s %s" % (key, op, stmt_val)
                node = TreeNode("value", "", stmt_text,
                                raw_lines=[stmt_text])
                node._tok_span = (i, i + 3)
                parent.add_child(node)
                i += 3
                continue
            # 独立 token（无等号），作为空值节点
            if key not in ("{", "}"):
                node = TreeNode("value", key, "")
                node._tok_span = (i, i + 1)
                parent.add_child(node)
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
    """PDX 分词器：将 PDX 文本拆分为带行号与字符偏移的 token 列表。

    识别以下 token 类型：
    - 大括号 { }
    - 等号 =
    - 双引号字符串 "..."
    - 比较运算符 >= <= == != > <
    - 标识符（字母、数字、点、连字符、斜杠——斜杠用于 gfx 路径等值）

    返回 (token, line_number, char_pos) 三元组，line_number 为 1-indexed，
    char_pos 为在「去注释后文本」中的偏移（行号与原文一一对应）。

    性能契约：行号采用增量统计（相邻 token 间只 count 新增段落），
    全文件 O(n)；禁止改回逐 token `text[:pos].count('\\n')`（那会退化为 O(n²)，
    实测 1MB 文件解析 36s → 线性化后亚秒级，见 docs/现状评估报告.md P0-1）。
    """
    text = _strip_comments(text)
    tokens = []
    line_no = 1
    prev = 0
    for m in _TOKEN_RE.finditer(text):
        start = m.start()
        if start > prev:
            line_no += text.count("\n", prev, start)
            prev = start
        tokens.append((m.group(0), line_no, start))
    return tokens


_TOKEN_RE = re.compile(r'\{|\}|>=|<=|==|!=|=|>|<|"[^"]*"|[\w\.\-/]+')


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


class LineIndex:
    """字符偏移 → 行号（1-based）查询索引。

    构建 O(n)（str.find 循环，C 速度），查询单次 O(log n)。
    取代「每个 token 都 text[:pos].count(newline)」的 O(n^2) 写法。
    """

    def __init__(self, text):
        self._newlines = []
        find = text.find
        i = find("\n")
        while i != -1:
            self._newlines.append(i)
            i = find("\n", i + 1)

    def line_of(self, pos):
        """返回字符偏移 pos 所在行号（1-based）。"""
        return bisect_right(self._newlines, pos) + 1


def attach_verbatim_lines(root, text):
    """为树节点附加原始文本行（含节点间注释/空行），供通用树编辑器保真保存。

    只应在「整文件树」（tree_from_pdx_text 的结果）上调用；国策路径
    （TreeNode.from_focus_load）自带 raw_fields 原文行，不需要本函数。

    附加规则：
    - 节点自身行：从节点首个 token 行到末个 token 行（rstrip，保留原缩进），
      写入 raw_lines（_serialize_children 原样输出）；
    - 前导注释/空行：上一兄弟结束行到本节点起始行之间的行，
      写入 _verbatim_lead（序列化时先于节点输出）；
    - 块尾注释/空行（最后一个子节点之后、闭括号之前）：
      写入 _verbatim_tail（重建块时插在子节点与闭括号之间）；
    - 根级尾部（最后一个顶层节点之后到文件尾）：写入 root._verbatim_tail；
    - 与父键同行的内联内容（如 key = { a = 1 } 单行块）不附加原文，
      保存时按树重建，避免键行重复。

    Args:
        root: tree_from_pdx_text / parse_pdx_text_to_nodes 产出的树根
        text: 构建该树时使用的原始文本
    """
    lines = text.splitlines()
    if not lines:
        return
    # token 位置基于「去注释后文本」（_tokenize 先 _strip_comments），
    # 但去注释是逐行截断（不改变行数），行号与原文一一对应；
    # 因此索引必须建在去注释后的文本上，行内容仍取自原文。
    idx = LineIndex(_strip_comments(text))
    prev_end = 0  # 上一节点结束行（1-based；0 = 尚未消费任何行）

    # _tok_span 记录的是 token 下标；换算回字符偏移再查行号
    tok_pos = [t[2] for t in _tokenize(_strip_comments(text))]

    def span_of(node):
        span = getattr(node, "_tok_span", None)
        if not span or span[0] >= len(tok_pos):
            return None
        start_line = idx.line_of(tok_pos[span[0]])
        end_idx = min(span[1] - 1, len(tok_pos) - 1)
        end_line = idx.line_of(tok_pos[end_idx])
        return start_line, max(end_line, start_line)

    def rstrip_lines(first, last):
        """闭区间 [first, last]（1-based 行号）→ rstrip 后的行列表。"""
        if last < first:
            return []
        return [lines[k - 1].rstrip() for k in range(first, last + 1)]

    def walk(node, parent_key_line):
        nonlocal prev_end
        sp = span_of(node)
        if sp is None:
            return
        start_line, end_line = sp
        if start_line <= parent_key_line:
            # 内联块/与父键同行：不附加原文（保存时按树重建）
            return
        node._verbatim_lead = rstrip_lines(prev_end + 1, start_line - 1)
        node.raw_lines = rstrip_lines(start_line, end_line)
        prev_end = start_line  # 子节点前导从键行之后开始
        for child in node.children:
            walk(child, start_line)
        tail = rstrip_lines(prev_end + 1, end_line - 1)
        if tail:
            node._verbatim_tail = tail
        prev_end = end_line  # 下一兄弟的前导接在本节点结束行之后

    for child in root.children:
        walk(child, 0)
    tail = rstrip_lines(prev_end + 1, len(lines))
    if tail:
        root._verbatim_tail = tail
