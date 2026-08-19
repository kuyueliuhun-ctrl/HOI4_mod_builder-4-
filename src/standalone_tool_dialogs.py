"""第一批独立工具对话框（PDX 格式化 / DDS 转换 / VP 本地化 / 错误日志）

工具菜单调用的薄对话框：选路径 → 运行 → 结果提示。
"""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHeaderView, QMessageBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
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


def run_error_log(parent=None):
    """选择日志 → 分析 → 结果表。"""
    path, _ = QFileDialog.getOpenFileName(parent, "选择游戏日志", "",
                                          "日志 (*.log);;所有文件 (*)")
    if not path:
        return None
    from error_log import analyze_file, summarize, classify_by_subsystem
    results = analyze_file(path)
    summary = summarize(results)
    subsystems = classify_by_subsystem(results)
    dlg = QDialog(parent)
    dlg.setWindowTitle("错误日志分析 - " + os.path.basename(path))
    dlg.resize(900, 520)
    lay = QVBoxLayout(dlg)
    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["子系统", "类别", "行号", "内容"])
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    table.setRowCount(len(results))
    for i, r in enumerate(results):
        msg = r["message"]
        table.setItem(i, 0, QTableWidgetItem(_subsystem_of(msg)))
        table.setItem(i, 1, QTableWidgetItem(r["category"]))
        table.setItem(i, 2, QTableWidgetItem(str(r["lineno"])))
        table.setItem(i, 3, QTableWidgetItem(msg))
    lay.addWidget(table)
    summary_str = "；".join("{} {}".format(k, v) for k, v in summary.items()) or "无匹配"
    QMessageBox.information(parent, "错误日志分析",
                            "共 {} 条：{}\n子系统：{}".format(
                                len(results), summary_str,
                                "，".join("{}x{}".format(k, v) for k, v in subsystems.items())))
    dlg.exec()
    return results


def _subsystem_of(msg):
    from error_log import _SUBSYSTEM_RULES
    for name, pat in _SUBSYSTEM_RULES:
        if name == "其他":
            return "其他"
        if pat.search(str(msg)):
            return name
    return "其他"