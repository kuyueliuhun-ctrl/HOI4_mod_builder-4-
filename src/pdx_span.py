"""PDX 块扫描核心（算法层）：单遍正则扫描 + 单调栈求块范围。

从 EntityScanner 抽出的共享底层（P1-4，见 docs/现状评估报告.md）：
- EntityScanner 委托到这里（保持旧静态方法签名不变）；
- icon_ops / focus_algo 的块定位器复用同一套 O(n) 扫描，
  取代旧版「每次调用整文件 token 化」的 O(n) per call / O(n·m) 热点；
- depth_index/children_in 用按深度分桶 + start 有序早退，
  取代旧版「每个块线性扫全部 spans」的 O(m²) 子块筛选。

四层分离规范见 PROJECT_DOC.md §1.4：本模块只依赖标准库。
"""

from __future__ import annotations

import math
import re

_BLOCK_RE = re.compile(r'(\{|\})|([\w\.\-]+)\s*=\s*\{')
_FIELD_TOKEN_RE = re.compile(r'("[^"]*"|#.*|\{|\}|=|[\w\.\-]+)')


def blank_pdx(text):
    """将注释与引号字符串原地替换为空格（保持字符位置不变）。

    用于块扫描定位时保证结果位置与原文一致，且避免引号/注释内的
    花括号被误配对。
    """
    chars = list(text)
    n = len(chars)
    in_str = False
    i = 0
    while i < n:
        c = chars[i]
        if in_str:
            if c == '"':
                in_str = False
            chars[i] = ' '
            i += 1
            continue
        if c == '"':
            in_str = True
            chars[i] = ' '
            i += 1
            continue
        if c == '#':
            while i < n and chars[i] != '\n':
                chars[i] = ' '
                i += 1
            continue
        i += 1
    return ''.join(chars)


def scan_blocks(text):
    """轻量扫描：返回所有 `key = {` 块的 (key, depth, start) 列表。

    单遍正则扫描，同时跟踪括号深度；注释与引号内容已原地替换为空格
    （保持位置不变）。深度为块自身所处的层级（顶层块为 0）。整体 O(n)。
    """
    clean = blank_pdx(text)
    blocks = []
    depth = 0
    for m in _BLOCK_RE.finditer(clean):
        brace = m.group(1)
        if brace == "{":
            depth += 1
        elif brace == "}":
            depth -= 1
        else:
            blocks.append((m.group(2), depth, m.start()))
            depth += 1
    return blocks


def block_spans(blocks):
    """为 blocks 中每个 `key = {` 计算 (key, depth, start, end)。

    块结束位置 = 其后首个深度 <= 当前块深度的块位置；否则取到内容末尾。
    单调栈从右向左 O(n) 求解。
    """
    n = len(blocks)
    ends = [math.inf] * n
    stack = []
    for i in range(n - 1, -1, -1):
        depth = blocks[i][1]
        while stack and blocks[stack[-1]][1] > depth:
            stack.pop()
        if stack:
            ends[i] = blocks[stack[-1]][2]
        stack.append(i)
    return [(blocks[i][0], blocks[i][1], blocks[i][2], ends[i])
            for i in range(n)]


def depth_index(spans):
    """按深度分桶（各桶内保持 start 升序），供子块区间查询。"""
    out = {}
    for s in spans:
        out.setdefault(s[1], []).append(s)
    return out


def children_in(spans_by_depth, bpos, bend, child_depth):
    """取 (bpos, bend) 区间内、深度为 child_depth 的子块列表。

    取代旧版「对每个父块线性扫全部 spans」的 O(m²) 写法：
    桶内按 start 升序，一旦 start 越过区间右端即可早退（P1-4）。
    """
    out = []
    for s in spans_by_depth.get(child_depth, ()):
        if s[2] <= bpos:
            continue
        if s[2] >= bend:
            break
        if s[3] <= bend:
            out.append(s)
    return out


def top_level_fields(body):
    """返回实体块顶层（括号深度 1）的 key=value 映射（首次出现的值）。

    使用词法 token 扫描，忽略嵌套块与注释，仅取块直接层级的键值对。
    """
    toks = list(_FIELD_TOKEN_RE.finditer(body))
    depth = 0
    fields = {}
    i = 0
    while i < len(toks):
        t = toks[i].group(0)
        if t == '{':
            depth += 1
            i += 1
            continue
        if t == '}':
            depth -= 1
            i += 1
            continue
        if t.startswith('#') or t == '=':
            i += 1
            continue
        if depth == 1 and i + 2 < len(toks):
            eq = toks[i + 1].group(0)
            val = toks[i + 2].group(0)
            if (eq == '=' and val not in ('=', '{', '}')
                    and not val.startswith('#') and t not in fields):
                fields[t] = val.strip('"')
        i += 1
    return fields


def find_block_range(content, keys, entity_id=None):
    """在 content 中定位 keys 中某键的块范围，返回 (start, end)。

    Args:
        content: 文件全文
        keys: 可迭代块键名（或单键字符串），如 {"focus", "shared_focus"}
        entity_id: 非空时要求块内首个顶层 id 值与之匹配
            （与旧版逐 token 扫描语义一致；None 时取首个匹配键的块）

    Returns:
        (起始字符, 结束字符)；未找到返回 (-1, -1)。整体单遍 O(n)。
    """
    try:
        spans = block_spans(scan_blocks(content))
    except Exception:
        return -1, -1
    if isinstance(keys, str):
        keyset = {keys}
    else:
        keyset = set(keys)
    n = len(content)
    for key, _d, start, end in spans:
        if key not in keyset:
            continue
        if math.isinf(end):
            end = n
        if entity_id is not None:
            block = content[start:end]
            m = re.search(r'\bid\s*=\s*["\']?([^\s"\'}#]+)', block)
            if not m or m.group(1) != entity_id:
                continue
        return start, end
    return -1, -1
