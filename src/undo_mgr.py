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
# 撤销栈字节预算：所有快照的原始字节总量上限（超出时从最旧开始淘汰）。
# 修复旧版「50 个文件完整字节无内存上限」的问题（MB 级 mod 文件可占数百 MB）。
MAX_TOTAL_BYTES = 64 * 1024 * 1024


class FileUndoManager:
    def __init__(self, max_entries=MAX_ENTRIES,
                 max_total_bytes=MAX_TOTAL_BYTES):
        self._stack = []          # [(path, old_bytes)]
        self._max = max_entries
        self._max_bytes = max_total_bytes
        self._total_bytes = 0

    def _evict_over_budget(self):
        """快照总字节超预算时从最旧开始淘汰（保证至少保留最新一条）。"""
        while self._stack and len(self._stack) > 1 \
                and self._total_bytes > self._max_bytes:
            _path, old = self._stack.pop(0)
            self._total_bytes -= len(old)

    def before_write(self, path):
        """写文件前调用：读取原始字节压栈（文件不存在则跳过）。

        使用字节快照，撤销时可无损恢复 BOM / CRLF / 任意编码。
        总字节量受 max_total_bytes 预算约束，超限淘汰最旧快照。
        """
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "rb") as f:
                old = f.read()
        except Exception:
            return
        self._stack.append((path, old))
        self._total_bytes += len(old)
        if len(self._stack) > self._max:
            _path, old = self._stack.pop(0)
            self._total_bytes -= len(old)
        self._evict_over_budget()

    def can_undo(self):
        return bool(self._stack)

    def undo(self):
        """撤销最近一次写入，恢复旧内容。

        成功后才弹出栈顶；恢复失败时保留撤销条目，避免永久丢失最后一次可恢复状态。

        Returns:
            (str, bool): (文件路径, 是否成功)
        """
        if not self._stack:
            return "", False
        path, old = self._stack[-1]
        try:
            # 恢复写入同样走原子写（不登记快照，避免把自己压回撤销栈）
            from write_utils import atomic_write_bytes
            atomic_write_bytes(path, old, undo=False)
        except Exception:
            return path, False
        self._stack.pop()
        return path, True

    def clear(self):
        self._stack.clear()
        self._total_bytes = 0


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
