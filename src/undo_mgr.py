"""文件写入撤销管理器（模块级单例）

对「写文件入口」做写前快照，支持撤销最近 N 次写入，恢复文件到上次写入前的内容。
挂钩点：
  - icon_ops.write_file_utf8（画廊/国策/项目向导等所有走该入口的写入）
  - generic_tree_editor._save（树形编辑器保存）
UI：
  - FocusView 画布 Ctrl+Z（焦点在画布时）
  - 主窗口「工具 → 撤销上次文件写入…」
"""

import os

MAX_ENTRIES = 50


class FileUndoManager:
    def __init__(self, max_entries=MAX_ENTRIES):
        self._stack = []          # [(path, old_content)]
        self._max = max_entries

    def before_write(self, path):
        """写文件前调用：读取旧内容压栈（文件不存在则跳过）。"""
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                old = f.read()
        except Exception:
            return
        self._stack.append((path, old))
        if len(self._stack) > self._max:
            self._stack.pop(0)

    def can_undo(self):
        return bool(self._stack)

    def undo(self):
        """撤销最近一次写入，恢复旧内容。

        Returns:
            (str, bool): (文件路径, 是否成功)
        """
        if not self._stack:
            return "", False
        path, old = self._stack.pop()
        try:
            # 恢复写入同样走原子写（不登记快照，避免把自己压回撤销栈）
            from write_utils import atomic_write_text
            atomic_write_text(path, old, undo=False)
            return path, True
        except Exception:
            return path, False

    def clear(self):
        self._stack.clear()


# 全局单例
_manager = None


def get_undo_manager():
    global _manager
    if _manager is None:
        _manager = FileUndoManager()
    return _manager


def before_write(path):
    """便捷入口：写文件前快照。"""
    get_undo_manager().before_write(path)


def undo():
    """便捷入口：撤销。"""
    return get_undo_manager().undo()


def can_undo():
    return get_undo_manager().can_undo()
