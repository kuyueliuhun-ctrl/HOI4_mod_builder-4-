"""state / province 排序与部署（算法层）

基于 `id = <数值>` 对顶层块（state/province 等）排序并重排。
只重排块顺序，不修改块内容。部署 = 按给定顺序重排。
"""

from __future__ import annotations

import re
from typing import List, Optional

_START_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{")
_ID_RE = re.compile(r"\bid\s*=\s*(-?\d+)")


def _split_blocks(text: str) -> tuple:
    """把文本切成 [头部文本, [块(str), ...]]。

    块按顶层 `key = {`（深度 0）用字符级花括号配平定位，支持单行/多行块；
    顶层键前的内容作为头部文本保留（注释/包装等）。
    """
    blocks = []
    header = []
    i = 0
    n = len(text)
    last_block_end = 0
    while i < n:
        # 在深度 0 时寻找顶层 `key = {`
        m = _START_RE.match(text, i)
        if m is None or m.start() != i:
            i += 1
            continue
        brace = text.find("{", m.end() - 1)
        depth = 0
        j = brace
        while j < n:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            i += 1
            continue
        # 块范围 m.start()..j（含闭合 }
        block = text[m.start():j + 1]
        header.append(text[last_block_end:m.start()])
        blocks.append(block)
        last_block_end = j + 1
        i = j + 1
    header.append(text[last_block_end:])
    return "".join(header), blocks


def _block_id(block: str) -> Optional[int]:
    m = _ID_RE.search(block)
    if m:
        return int(m.group(1))
    return None


def sort_blocks_by_id(text: str, default_order: bool = True) -> str:
    """按块内 id 数值升序排序顶层块（id 无法解析的块放在尾部，保持原序）。"""
    header, blocks = _split_blocks(text)
    keyed = []
    for idx, b in enumerate(blocks):
        bid = _block_id(b)
        keyed.append((idx, bid, b))
    # None 排在最后
    keyed.sort(key=lambda t: (t[1] is None, t[1] if t[1] is not None else 0))
    return header + "".join(b for _i, _id, b in keyed)


def deploy_blocks(text: str, order: List[str] = None, key_of=lambda b: b) -> str:
    """按给定 key 顺序重排顶层块；缺失 key 的块保留在末尾原序。"""
    header, blocks = _split_blocks(text)
    if not order:
        return text
    order_set = set(order)
    placed = []
    remaining = []
    for b in blocks:
        k = key_of(b)
        if k in order_set:
            placed.append((order.index(k), k, b))
        else:
            remaining.append(b)
    placed.sort(key=lambda t: t[0])
    return header + "".join(b for _o, _k, b in placed) + "".join(remaining)


def sort_state_file(text: str) -> str:
    """对 state 文件按块 id 排序。"""
    return sort_blocks_by_id(text)