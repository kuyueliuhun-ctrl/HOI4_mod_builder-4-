"""第一批独立工具对话框（PDX 格式化 / DDS 转换 / VP 本地化 / 错误日志）

工具菜单调用的薄对话框：选路径 → 运行 → 结果提示。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QFileDialog, QHeaderView,
    QLabel, QMenu, QMessageBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from write_utils import atomic_write_text


def run_pdx_format(parent=None, mod_path=""):
    """选择文件/目录 → 格式化 → 提示。"""
    start = mod_path or ""
    path, _ = QFileDialog.getOpenFileName(parent, "选择要格式化的 PDX 文件", start,
                                          "PDX 脚本 (*.txt *.gfx *.yml);;所有文件 (*)")
    if not path:
        return None
    from pdx_format import format_file
    ok = format_file(path)
    QMessageBox.information(parent, "PDX 格式化",
                            "已格式化：{} {}".format(os.path.basename(path), "✓" if ok else "失败"))
    return ok


def run_dds_convert(parent=None, mod_path=""):
    """选择目录 → 批量 DDS→PNG → 提示。"""
    start = mod_path or ""
    d = QFileDialog.getExistingDirectory(parent, "选择含 .dds 的目录", start)
    if not d:
        return None
    from dds_convert import convert_dir
    r = convert_dir(d)
    QMessageBox.information(parent, "DDS 转换",
                            "转换 {} 个，失败 {} 个".format(r["count"], r["fail_count"]))
    return r


def run_vp_loc(parent=None, mod_path="", hoi4_path=""):
    """扫描 mod 的 VP → 写本地化 yml。"""
    if not mod_path or not os.path.isdir(mod_path):
        QMessageBox.information(parent, "VP 本地化", "请先打开 mod 目录")
        return None
    from vp_loc import collect_vps, build_vp_loc_text
    vps = collect_vps(mod_path)
    text = build_vp_loc_text(vps, lang="simp_chinese")
    out, _ = QFileDialog.getSaveFileName(parent, "保存 VP 本地化", mod_path, "本地化 (*.yml)")
    if not out:
        return None
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    atomic_write_text(out, text, encoding="utf-8-sig", allow_bom=True)
    QMessageBox.information(parent, "VP 本地化", "已生成 {} 个 VP 词条 → {}".format(len(vps), out))
    return len(vps)


def _editor_roots():
    """读 settings.json → (mod_path, hoi4_path, hoi4用户目录)。"""
    from project_paths import PROJECT_ROOT
    settings = {}
    try:
        with open(os.path.join(str(PROJECT_ROOT), "settings.json"),
                  "r", encoding="utf-8") as f:
            import json
            settings = json.load(f)
    except Exception:
        settings = {}
    user_dir = ""
    try:
        from playset_loader import hoi4_user_dir
        user_dir = hoi4_user_dir(settings)
    except Exception:
        user_dir = ""
    return (settings.get("mod_path", ""), settings.get("HOI4_path", ""),
            user_dir)


def _default_log_dir():
    """游戏日志默认目录：HOI4 用户目录下的 logs/（error.log 所在）。"""
    _mod, _hoi4, user_dir = _editor_roots()
    if user_dir:
        d = os.path.join(user_dir, "logs")
        if os.path.isdir(d):
            return d
    return ""


def run_error_log(parent=None):
    """选择日志 → 分析 → 结果表。默认定位到游戏 logs 目录。"""
    path, _ = QFileDialog.getOpenFileName(parent, "选择游戏日志",
                                          _default_log_dir(),
                                          "日志 (*.log);;所有文件 (*)")
    if not path:
        return None
    mod_path, hoi4_path, user_dir = _editor_roots()
    return show_error_log_report(parent, path, mod_path=mod_path,
                                 hoi4_path=hoi4_path, user_dir=user_dir)


def show_error_log_report(parent, log_path, mod_path="", hoi4_path="",
                          user_dir=""):
    """错误日志分析结果表（可独立测试）。

    6.94 内容补全：每条错误解析出「具体文件:行号」与来源（mod/游戏/
    用户mod目录/未找到），双击直接打开对应文件，右键复制精确位置；
    相同错误去重合并（真实 error.log 数万行），顶部汇总 + 按文件聚合。
    """
    from error_log import (analyze_file, classify_by_subsystem, summarize,
                           summarize_by_file)
    results = analyze_file(log_path, mod_path=mod_path, hoi4_path=hoi4_path,
                           user_dir=user_dir, dedupe=True)
    summary = summarize(results)
    subsystems = classify_by_subsystem(results)
    files = summarize_by_file(results)
    dlg = QDialog(parent)
    dlg.setWindowTitle("错误日志分析 - " + os.path.basename(log_path))
    dlg.resize(1080, 620)
    lay = QVBoxLayout(dlg)
    top_files = sorted(files.items(), key=lambda x: -x[1])[:5]
    summary_str = "；".join("{} {}".format(k, v) for k, v in summary.items()) or "无匹配"
    files_str = "；".join("{}({})".format(k, v) for k, v in top_files) or "—"
    note = QLabel("共 {} 条（去重后 {} 条）\n类别：{}\n错误最多的文件：{}".format(
        sum(r.get("count", 1) for r in results), len(results),
        summary_str, files_str))
    note.setWordWrap(True)
    note.setStyleSheet("color:#5d6b7a;font-size:11px;")
    lay.addWidget(note)
    table = QTableWidget()
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(
        ["子系统", "类别", "位置（文件:行号）", "来源", "内容（双击打开文件）"])
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    table.setColumnWidth(2, 300)
    table.setColumnWidth(3, 90)
    table.setRowCount(len(results))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setWordWrap(False)
    for i, r in enumerate(results):
        loc_text = "%s:%s" % (r.get("rel_path") or "—", r.get("line") or "—") \
            if r.get("rel_path") else "—（引擎内部/未标注）"
        tip_parts = [r["message"]]
        if r.get("token"):
            tip_parts.append("定位对象：%s" % r["token"])
        if r.get("hint"):
            tip_parts.append("建议：%s" % r["hint"])
        if r.get("abs_path"):
            tip_parts.append("文件：%s" % r["abs_path"])
        elif r.get("rel_path"):
            tip_parts.append("未在 mod/游戏目录中找到该文件（可能来自其他 mod）")
        tip = "\n".join(tip_parts)
        cells = [
            QTableWidgetItem(_subsystem_of(r["message"])),
            QTableWidgetItem(r["category"]),
            QTableWidgetItem(loc_text),
            QTableWidgetItem(r.get("source") or "—"),
            QTableWidgetItem(r["message"]),
        ]
        for col, item in enumerate(cells):
            item.setToolTip(tip)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, r)
            table.setItem(i, col, item)
    table.doubleClicked.connect(lambda: _open_error_location(table))
    table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    table.customContextMenuRequested.connect(
        lambda pos: _error_location_menu(table, dlg, pos))
    lay.addWidget(table)
    dlg.exec()
    return results


def _current_error_row(table):
    item = table.item(table.currentRow(), 0)
    return item.data(Qt.ItemDataRole.UserRole) if item else None


def _open_error_location(table):
    """双击：打开错误指向的文件（系统默认编辑器）。"""
    r = _current_error_row(table)
    if not r or not r.get("abs_path"):
        return
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import QUrl
    QDesktopServices.openUrl(QUrl.fromLocalFile(r["abs_path"]))


def _error_location_menu(table, dlg, pos):
    """右键：打开文件 / 在资源管理器中显示 / 复制位置（文件:行号）。"""
    r = _current_error_row(table)
    if not r:
        return
    menu = QMenu(dlg)
    act_open = menu.addAction("📂 打开指向的文件")
    act_explorer = menu.addAction("🗂 在资源管理器中显示")
    act_copy = menu.addAction("⧉ 复制位置（文件:行号）")
    act_copy_msg = menu.addAction("⧉ 复制错误内容")
    act = menu.exec(table.viewport().mapToGlobal(pos))
    if act is act_open and r.get("abs_path"):
        _open_error_location(table)
    elif act is act_explorer and r.get("abs_path"):
        import subprocess
        subprocess.Popen(["explorer", "/select,",
                          os.path.normpath(r["abs_path"])])
    elif act is act_copy:
        loc = "%s:%s" % (r.get("abs_path") or r.get("rel_path") or "",
                         r.get("line") or "")
        QApplication.clipboard().setText(loc)
    elif act is act_copy_msg:
        QApplication.clipboard().setText(r.get("message", ""))


def _subsystem_of(msg):
    from error_log import _SUBSYSTEM_RULES
    for name, pat in _SUBSYSTEM_RULES:
        if name == "其他":
            return "其他"
        if pat.search(str(msg)):
            return name
    return "其他"