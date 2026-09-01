from bisect import bisect_right

import re
from dataclasses import dataclass, field
from typing import Dict, Union, List


class _LineIndex:
    """字符偏移 → 行号（1-based）索引：构建 O(n)，查询单次 O(log n)。

    取代「每个 token 都 ``content[:pos].count('\\n')``」的写法
    （大文件 O(n*m) 热点，见 docs/现状评估报告.md P0-1）。
    """

    def __init__(self, text: str):
        self._newlines = []
        find = text.find
        i = find("\\n")
        while i != -1:
            self._newlines.append(i)
            i = find("\\n", i + 1)

    def line_of(self, pos: int) -> int:
        return bisect_right(self._newlines, pos) + 1

# 模板中已知的通用第一层子语句关键字
KNOWN_KEYS = {
    "id", "icon", "dynamic", "text_icon", "relative_position_id", "offset",
    "mutually_exclusive", "prerequisite", "cost", "ai_will_do", "available",
    "allow_branch", "select_effect", "bypass", "historical_ai", "cancel",
    "available_if_capitulated", "cancelable", "bypass_if_unavailable",
    "cancel_if_invalid", "continue_if_invalid", "will_lead_to_war_with",
    "search_filters", "completion_reward"
}


class KnownDataProxy(dict):
    """允许通过属性和键名两种方式访问数据的代理类。支持: data.cost 或 data['cost']。
    如果属性不存在则返回 None 而非抛出异常，方便条件判断。"""

    def __getattr__(self, name):
        if name in self:
            return self[name]
        # 如果未找到该属性，返回 None 而不是报错，方便后续逻辑判断
        return None

    def __setattr__(self, name, value):
        self[name] = value


@dataclass
class FocusLoad:
    """返回的国策数据结构体"""
    focus_id: str
    focus_type: str  # 记录是 focus, shared_focus 还是 joint_focus
    known: KnownDataProxy = field(default_factory=KnownDataProxy)
    unknown: Dict[str, Union[str, List[str]]] = field(default_factory=dict)


def parse_focus_file(file_path: str, focus_id: str) -> tuple:
    """
    读取文件并解析指定 focus_id 的国策数据。

    :param file_path: 文件绝对或相对路径
    :param focus_id: 需要定位的国策 ID
    :return: (FocusLoad, file_lines, block_range, x_val, y_val)
             file_lines: 原始文件行列表
             block_range: (start_line, end_line) 1-indexed
             x_val, y_val: 国策坐标值
    :raises ValueError: 当找不到对应的 focus_id 时抛出异常
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    file_lines = content.splitlines()
    line_index = _LineIndex(content)

    token_pattern = r'("[^"]*"|#.*|\{|\}|=|[\w\.\-]+)'
    raw_matches = [(m.group(0), m.start()) for m in re.finditer(token_pattern, content)]
    raw_tokens = [m[0] for m in raw_matches]
    tokens = [t for t in raw_tokens if not t.startswith('#')]

    token_positions = [pos for tok, pos in raw_matches if not tok.startswith('#')]

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in ['focus', 'shared_focus', 'joint_focus']:
            if i + 2 < len(tokens) and tokens[i + 1] == '=' and tokens[i + 2] == '{':
                focus_type = token
                start_line = line_index.line_of(token_positions[i])
                first_field_idx = i + 3
                i = first_field_idx

                layer_1_data, end_idx = _parse_layer_1(tokens, i, token_positions, content,
                                                       line_index=line_index)

                block_end_char = _find_block_end_char(content, raw_tokens, tokens, i, end_idx, token_positions)
                end_line = line_index.line_of(block_end_char)
                i = end_idx

                current_id = layer_1_data.get('id', [''])[0].strip('"')

                if current_id == focus_id:
                    result = _categorize_data(focus_type, current_id, layer_1_data)
                    x_val = layer_1_data.get('x', ['0'])[0].strip('"')
                    y_val = layer_1_data.get('y', ['0'])[0].strip('"')
                    block_range = (start_line, end_line)
                    result.known['__focus_type__'] = focus_type
                    raw_field_map = _build_raw_field_map(file_lines, content, raw_matches,
                                                          tokens, token_positions,
                                                          start_line, first_field_idx,
                                                          line_index=line_index)
                    return result, file_lines, block_range, x_val, y_val, raw_field_map
        i += 1

    raise ValueError(f"未在文件 '{file_path}' 中找到 focus_id 为 '{focus_id}' 的结构体。")


def _build_raw_field_map(file_lines, content, raw_matches, tokens, token_positions,
                           block_start_line, token_start_idx, line_index=None):
    """构建字段名到原始文本行的映射"""
    field_map = {}

    block_start_char_pos = 0
    lines_before = content.splitlines(True)
    for ln in range(block_start_line - 1):
        if ln < len(lines_before):
            block_start_char_pos += len(lines_before[ln])

    ti = token_start_idx
    while ti < len(tokens):
        if ti >= len(token_positions):
            break
        pos = token_positions[ti]
        if pos < block_start_char_pos:
            ti += 1
            continue

        key = tokens[ti]
        if key == '}':
            break

        if ti + 1 >= len(tokens) or tokens[ti + 1] != '=':
            ti += 1
            continue

        val_start_idx = ti + 2
        key_start_line = (line_index.line_of(pos) if line_index is not None
                          else content[:pos].count('\n') + 1)

        if val_start_idx < len(tokens) and tokens[val_start_idx] == '{':
            depth = 1
            end_idx = val_start_idx + 1
            while end_idx < len(tokens) and depth > 0:
                if tokens[end_idx] == '{':
                    depth += 1
                elif tokens[end_idx] == '}':
                    depth -= 1
                end_idx += 1
            closing_idx = end_idx - 1
            if closing_idx < len(token_positions):
                block_end_pos = token_positions[closing_idx]
                key_end_line = (line_index.line_of(block_end_pos)
                                if line_index is not None
                                else content[:block_end_pos].count('\n') + 1)
            else:
                key_end_line = key_start_line
        else:
            key_end_line = key_start_line

        field_lines = file_lines[key_start_line - 1:key_end_line]
        stripped = [l.rstrip() for l in field_lines if l.strip()]

        if key in field_map:
            existing = field_map[key]
            if existing and isinstance(existing[0], list):
                existing.append(stripped)
            else:
                field_map[key] = [existing, stripped]
        else:
            field_map[key] = stripped

        if val_start_idx < len(tokens) and tokens[val_start_idx] == '{':
            ti = end_idx
        else:
            ti = val_start_idx + 1

    return field_map





def _find_block_end_char(content: str, raw_tokens: list, tokens: list,
                         start_idx: int, end_idx: int, token_positions: list) -> int:
    """找到块的结束字符位置（close brace 之后）"""
    if end_idx < len(token_positions) and token_positions[end_idx] >= 0:
        return token_positions[end_idx]
    for i in range(end_idx, len(token_positions)):
        if token_positions[i] >= 0:
            return token_positions[i]
    return len(content)


def _parse_layer_1(tokens: list, start_idx: int, token_positions: list = None, content: str = "",
                   line_index=None):
    """解析结构体的第一层级

    参数:
        tokens: token 列表
        start_idx: 起始索引
        token_positions: token 在原文中的字符位置列表（可选，用于行号判断）
        content: 原始内容字符串（可选，用于行号判断）
    返回:
        (layer_data, end_idx)
    """
    layer_data = {}
    i = start_idx

    def get_line(idx):
        """获取 token 的行号"""
        if line_index is not None and idx < len(token_positions):
            return line_index.line_of(token_positions[idx])
        if token_positions and content and idx < len(token_positions):
            return content[:token_positions[idx]].count('\n') + 1
        return 0

    while i < len(tokens):
        if tokens[i] == '}':
            return layer_data, i

        key = tokens[i]
        key_line = get_line(i)
        if i + 2 < len(tokens) and tokens[i + 1] == '=':
            eq_line = get_line(i + 1)
            val_start = i + 2

            # 如果值是一个代码块
            if tokens[val_start] == '{':
                depth = 1
                val_end = val_start + 1
                while val_end < len(tokens) and depth > 0:
                    if tokens[val_end] == '{':
                        depth += 1
                    elif tokens[val_end] == '}':
                        depth -= 1
                    val_end += 1
                value = " ".join(tokens[val_start:val_end])
                i = val_end
                # 处理重复出现的键 (例如 prerequisite)
                if key in layer_data:
                    if not isinstance(layer_data[key], list):
                        layer_data[key] = [layer_data[key]]
                    layer_data[key].append(value)
                else:
                    layer_data[key] = [value]
            else:
                # 检查 val_start 是否与 = 在同一行
                val_line = get_line(val_start)
                if token_positions and content and val_line != eq_line:
                    # = 后面没有同行的值，视为空值
                    # 只跳过 key 和 '='，让 val_start 位置的 token 作为下一个 key 处理
                    layer_data.setdefault(key, []).append("")
                    i += 2
                else:
                    value = tokens[val_start]
                    i = val_start + 1
                    # 处理重复出现的键 (例如 prerequisite)
                    if key in layer_data:
                        if not isinstance(layer_data[key], list):
                            layer_data[key] = [layer_data[key]]
                        layer_data[key].append(value)
                    else:
                        layer_data[key] = [value]
        else:
            # 独立 token 无等号，作为空值
            if key not in ('{', '}'):
                layer_data.setdefault(key, []).append("")
            i += 1

    return layer_data, i


def _categorize_data(focus_type: str, focus_id: str, layer_1_data: dict) -> FocusLoad:
    """将提取的数据分类为已知(known)和未知(unknown)"""
    struct = FocusLoad(focus_id=focus_id, focus_type=focus_type)

    for key, value_list in layer_1_data.items():
        clean_value = value_list[0] if len(value_list) == 1 else value_list
        if key.lower() in KNOWN_KEYS:
            struct.known[key] = clean_value
        else:
            struct.unknown[key] = clean_value

    return struct


def parse_tree_header(file_path):
    """解析树形文件的头信息（排除 focus/joint_focus/shared_focus 块）"""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    header_lines = []
    child_blocks = []
    current_block = []
    block_depth = 0
    in_child_block = False
    insert_pos = len(lines)
    header_depth = 0

    block_names = {'focus', 'joint_focus', 'shared_focus'}

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not in_child_block:
            if stripped in ('', 'l_simp_chinese:') or stripped.startswith('#'):
                continue

            is_block_start = False
            for bn in block_names:
                if stripped.startswith(bn + ' ') or stripped.startswith(bn + '='):
                    if '{' in stripped:
                        is_block_start = True
                        break

            if is_block_start:
                in_child_block = True
                current_block = [line.rstrip('\n')]
                block_depth = stripped.count('{') - stripped.count('}')
                if insert_pos > i:
                    insert_pos = i
            else:
                header_lines.append(line.rstrip('\n'))
                header_depth += stripped.count('{') - stripped.count('}')
        else:
            current_block.append(line.rstrip('\n'))
            block_depth += stripped.count('{') - stripped.count('}')
            if block_depth <= 0:
                child_blocks.append(current_block)
                current_block = []
                in_child_block = False

    if current_block:
        child_blocks.append(current_block)

    while header_lines and header_lines[-1].strip() == '}':
        header_lines.pop()

    return {
        'header_lines': header_lines,
        'child_blocks': child_blocks,
        'insert_pos': insert_pos,
    }