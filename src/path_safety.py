"""路径与文件名字段安全校验（API/MCP 接口层共享）

背景（P0-1）：接口层多个入口直接拿用户输入的 `country/tag/filename/icon_base/path`
拼路径后写入，持 token 的调用方可越过 mod 目录写任意文件、甚至就地改写游戏本体。
本模块提供两类校验：

- ``validate_component``：单段文件名（不允许路径分隔符 / `..` / 盘符等），
  用于 tag、country、filename、icon_base 等拼文件名的字段。
- ``safe_join``：把 mod 内相对路径安全拼到根目录，并防符号链接逃逸，
  用于 OOB path 等「相对路径」字段。

所有校验失败抛 ``ValueError``，由调用方统一转 400。
"""

from __future__ import annotations

import os
import re

# 单段文件名允许的字符：字母/数字/下划线/点/连字符，且不能以数字开头。
# 这是 HOI4 标识符 / sprite 名的常见子集（tag、focus id、idea id 等）。
_SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")


def validate_component(value, label="值", allow_empty=False):
    """校验单段文件名字段（tag/country/filename/icon_base 等）。

    Args:
        value: 待校验值（str 或可 str() 的对象）
        label: 错误提示里的字段名
        allow_empty: True 时允许空串（返回 ""）

    Raises:
        ValueError: 含路径分隔符 / 盘符 / `..` / 非法字符 / 以数字开头
    """
    s = str(value or "").strip()
    if not s:
        if allow_empty:
            return ""
        raise ValueError("%s 不能为空" % label)
    if not _SAFE_COMPONENT_RE.fullmatch(s):
        raise ValueError(
            "%s 只能包含字母/数字/下划线/点/连字符，且不能以数字开头（不允许路径分隔符）" % label)
    return s


def safe_join(root, rel_path):
    """把相对路径安全拼接到根目录下（越界/绝对/盘符/符号链接逃逸均拒绝）。

    Args:
        root: 根目录（mod 或 game 根）
        rel_path: 相对路径（允许子目录，如 history/units/00_test.txt）

    Returns:
        str: 拼接后的绝对路径（已 normpath + realpath 校验）

    Raises:
        ValueError: 路径为空 / 绝对路径 / 含 `..` / 盘符 / 逃逸出 root
    """
    if not root:
        raise ValueError("未配置根目录")
    root_abs = os.path.abspath(os.fspath(root))
    raw = (rel_path or "").replace("\\", "/")
    if raw.startswith("/"):
        raise ValueError("不允许绝对路径")
    if re.match(r"^[A-Za-z]:", raw):
        raise ValueError("不允许盘符")
    rel = raw
    if not rel:
        raise ValueError("路径不能为空")
    if os.path.isabs(rel):
        raise ValueError("不允许绝对路径")
    parts = rel.split("/")
    if any(p == ".." for p in parts):
        raise ValueError("不允许 .. 越界")
    first = parts[0]
    # 额外防御：段首带盘符（如 `C:/x` 已被上面拦截，双保险）。
    if len(first) >= 2 and first[1] == ":":
        raise ValueError("不允许盘符")
    fp = os.path.normpath(os.path.join(root_abs, rel))
    root_real = os.path.realpath(root_abs)
    fp_real = os.path.realpath(fp)
    if fp_real != root_real and not fp_real.startswith(root_real + os.sep):
        raise ValueError("路径越出根目录（含符号链接逃逸）")
    return fp


def is_within(root, abs_path):
    """判断绝对路径是否位于 root 目录内（realpath 比较，防符号链接）。"""
    if not root or not abs_path:
        return False
    root_real = os.path.realpath(os.path.abspath(os.fspath(root)))
    fp_real = os.path.realpath(os.path.abspath(os.fspath(abs_path)))
    return fp_real == root_real or fp_real.startswith(root_real + os.sep)
