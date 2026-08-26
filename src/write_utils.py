"""写入纪律核心：原子写 + 编码契约 + 撤销快照

所有 mod 内容文件（.txt / .gfx / .yml / .mod / .csv 等）的写入都应经过本模块，
这是「状态写入纪律」的第一道关卡：

1. **原子写**：先写同目录临时文件，再 os.replace 原子替换。
   写入中途失败（磁盘满、编码错误、进程被杀）绝不破坏原文件；
   原文件要么是旧内容，要么是新内容，不存在半截文件。
2. **编码契约**：默认 UTF-8 无 BOM、LF 行尾。
   HOI4 脚本解析器对 BOM 敏感，BOM 会破坏整文件解析，因此默认拒绝 BOM 文本。
   本地化 .yml 走 HOI4 惯例（UTF-8 BOM）时显式传 allow_bom=True。
3. **撤销快照**：写前自动登记到 undo_mgr（画布 Ctrl+Z / 工具菜单可撤销本次写入）。

契约命令：
    python tools/check_write_discipline.py   # 静态扫描绕过本模块的直写点
    python tools/verify_contracts.py         # 全部契约测试
"""

from __future__ import annotations

import os
import tempfile


class WriteContractError(ValueError):
    """写入违反编码/内容契约（BOM、不可编码字符等），原文件不会被触碰。"""


def validate_text_contract(text, *, encoding="utf-8", allow_bom=False):
    """写前契约校验：类型、BOM、可编码性。

    Raises:
        WriteContractError: 违反契约（原文件保持不动）。
    """
    if not isinstance(text, str):
        raise WriteContractError(
            "写入内容必须是 str，收到 %s" % type(text).__name__)
    if not allow_bom and text.startswith("\ufeff"):
        raise WriteContractError(
            "拒绝写入以 BOM（\\ufeff）开头的文本：HOI4 脚本解析器对 BOM 敏感，"
            "会破坏整文件解析。请去掉 BOM 后重试（本地化 .yml 如需 BOM，"
            "请显式传 allow_bom=True）。")
    try:
        text.encode(encoding)
    except UnicodeEncodeError as exc:
        raise WriteContractError(
            "内容无法用 %s 编码（字符 U+%04X 不可表示）"
            % (encoding, ord(exc.object[exc.start]))) from exc
    return True


def atomic_write_text(path, text, *, encoding="utf-8", newline="", undo=True,
                      allow_bom=False):
    """原子写文本文件（默认 UTF-8 无 BOM + LF 行尾）。

    Args:
        path: 目标文件路径（str 或 os.PathLike）
        text: 要写入的完整文本
        encoding: 编码，默认 utf-8；本地化 .yml 用 utf-8-sig（写 BOM）
        newline: open 的 newline 参数，默认 ""（不转换行尾，写入原文的 \\n）
        undo: 写前是否登记撤销快照（undo_mgr），默认 True
        allow_bom: 允许文本以 BOM 字符开头（本地化 .yml 场景），默认 False

    Returns:
        str: 实际写入的路径

    Raises:
        WriteContractError: 内容违反编码契约（原文件不被触碰）
        OSError: 目录不可写 / 磁盘满等（原文件不被触碰，临时文件已清理）
    """
    validate_text_contract(text, encoding=encoding, allow_bom=allow_bom)
    path = os.fspath(path)
    if undo:
        try:
            from undo_mgr import before_write
            before_write(path)
        except Exception:
            pass
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".dsh_write_", suffix=".tmp",
                                    dir=directory)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(text)
        try:
            os.replace(tmp_path, path)
        except PermissionError:
            # 目标被占用/只读时与原实现保持一致：尝试放宽权限后重试一次
            try:
                os.chmod(path, 0o666)
            except OSError:
                pass
            os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return path


def atomic_write_bytes(path, data, *, undo=False):
    """原子写原始字节（无损恢复用：保留 BOM/CRLF/任何编码）。

    撤销管理器用其恢复写前快照，避免 utf-8-sig 读入 + utf-8 写回丢 BOM/CRLF。
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("atomic_write_bytes 需要 bytes，收到 %s" % type(data).__name__)
    path = os.fspath(path)
    if undo:
        try:
            from undo_mgr import before_write
            before_write(path)
        except Exception:
            pass
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".dsh_write_", suffix=".tmp",
                                    dir=directory)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(bytes(data))
        try:
            os.replace(tmp_path, path)
        except PermissionError:
            try:
                os.chmod(path, 0o666)
            except OSError:
                pass
            os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return path


def read_text_contract(path, *, encoding="utf-8", errors="ignore"):
    """读文本文件并做契约校验（供健康检查/扫描使用）。

    Returns:
        (ok, content_or_message): ok=False 表示文件违反编码契约
    """
    try:
        with open(path, "r", encoding=encoding, errors=errors, newline="") as f:
            return True, f.read()
    except (OSError, UnicodeDecodeError) as exc:
        return False, str(exc)
