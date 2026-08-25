"""契约测试公共设施（F1）。

统一提供：
- get_app(): offscreen QApplication 单例
- make_temp_mod(tmpdir): 构造最小 mod 目录骨架
- _send_move(widget, pos, buttons): 手工构造 QMouseEvent 发送移动事件
  （QTest.mouseMove 在 offscreen 多窗口下不可靠，见 PROJECT_DOC.md §5.4）
"""

from __future__ import annotations

import os


def get_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def make_temp_mod(tmpdir):
    """在 tmpdir 下创建最小 mod 目录骨架，返回 mod 根路径。"""
    mod = os.path.join(tmpdir, "mod")
    for sub in ("common", "history", "map", "localisation"):
        os.makedirs(os.path.join(mod, sub), exist_ok=True)
    return mod


def _send_move(widget, pos, buttons=0):
    """向 widget 发送一个带按键状态的 QMouseEvent.MouseMove 事件。"""
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    ev = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(pos),
        Qt.MouseButton.NoButton,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.sendEvent(widget, ev)
    return ev