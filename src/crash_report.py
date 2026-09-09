"""编辑器自身崩溃报告（6.94 内容补全）

此前 sys.excepthook 只把 traceback 打到 stderr——Windows 双击启动时
stderr 不可见，用户只知道"崩了"，不知道崩在哪、报告在哪。

本模块把未捕获异常完整落盘到 `.runtime/crash/crash_<时间戳>.txt`
（含异常类型/消息 + 带 文件:行号 的完整 traceback——即"指向更明确的
位置"），并返回报告路径供弹窗展示给用户。
"""

from __future__ import annotations

import os
import platform
import sys
import time
import traceback

from project_paths import PROJECT_ROOT


def crash_report_dir() -> str:
    """崩溃报告目录：`<项目根>/.runtime/crash/`（.runtime 已 gitignore）。"""
    return os.path.join(str(PROJECT_ROOT), ".runtime", "crash")


def format_crash_text(exc_type, exc_value, exc_tb) -> str:
    """拼装崩溃报告全文：环境信息 + 带 文件:行号 的完整 traceback。"""
    lines = [
        "HOI4 Mod 编辑器崩溃报告",
        "时间: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "Python: %s (%s)" % (platform.python_version(),
                             sys.platform),
        "异常类型: %s" % getattr(exc_type, "__name__", str(exc_type)),
        "异常消息: %s" % (exc_value,),
        "",
        "traceback（文件:行号 → 函数 → 语句）:",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    ]
    return "\n".join(lines)


def write_crash_report(exc_type, exc_value, exc_tb) -> str:
    """落盘崩溃报告，返回报告文件绝对路径；失败返回空串（不二次抛异常）。"""
    try:
        d = crash_report_dir()
        os.makedirs(d, exist_ok=True)
        name = "crash_%s.txt" % time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(d, name)
        # 原子写：崩溃中途断电/被杀也不会留下半截报告
        from write_utils import atomic_write_text
        atomic_write_text(path, format_crash_text(exc_type, exc_value, exc_tb))
        return path
    except Exception:
        return ""
