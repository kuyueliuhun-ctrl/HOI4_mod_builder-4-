"""项目路径工具：所有模块统一从这里获取项目根目录。

代码位于 src/ 子目录，项目根目录 = src 的父目录。
移动/归档后，任何 `os.path.dirname(__file__)` 指向根目录资源的代码都应改为
使用 project_path()，避免因 src/ 打包导致资源定位错误。
"""

from __future__ import annotations

import os

# src/ 的父目录 = 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_path(*parts):
    """返回项目根目录下的路径。"""
    return os.path.join(PROJECT_ROOT, *parts)
