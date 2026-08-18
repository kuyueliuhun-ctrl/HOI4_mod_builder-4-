"""导出前健康检查对话框（工具菜单 → 导出前健康检查…）

对当前 mod 目录执行确定性检查（export_health.run_export_health_check），
以 error / warning / info 三级清单展示问题；error 级问题应修复后再发布。
"""

from __future__ import annotations

import os
import subprocess
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHeaderView, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

_SEV_CN = {"error": "错误", "warning": "警告", "info": "信息"}
# 柔和语义色（与主题 theme.COLORS 对齐）
_SEV_COLOR = {"error": "#b94d3f", "warning": "#b7791f", "info": "#1f4f7e"}


class HealthCheckDialog(QDialog):
    """导出前健康检查结果表。"""

    def __init__(self, parent=None, mod_path="", game_path=""):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.game_path = game_path or ""
        self.report = None
        self.setWindowTitle("导出前健康检查")
        self.resize(1000, 580)
        self._build_ui()
        self._run_check()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.summary_label = QLabel("正在检查…")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["级别", "分类", "文件", "问题", "建议"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        self.btn_rerun = QPushButton("↻ 重新检查")
        self.btn_rerun.clicked.connect(self._run_check)
        self.btn_json = QPushButton("💾 导出 JSON 报告…")
        self.btn_json.clicked.connect(self._export_json)
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_rerun)
        btn_row.addWidget(self.btn_json)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------ 检查
    def _run_check(self):
        from export_health import run_export_health_check
        self.summary_label.setText("正在检查 %s …" % self.mod_path)
        self.summary_label.repaint()
        t0 = time.time()
        try:
            self.report = run_export_health_check(self.mod_path, self.game_path)
        except Exception as e:
            self.report = None
            self.summary_label.setText("检查失败: %s" % e)
            return
        self._populate()
        counts = self.report.counts
        verdict = ("✅ 检查通过，可以发布"
                   if counts["error"] == 0
                   else "❌ 发现 %d 个错误，建议修复后再发布" % counts["error"])
        self.summary_label.setText(
            "%s　|　错误 %d / 警告 %d / 信息 %d　|　用时 %.2f 秒\n%s"
            % (os.path.basename(self.mod_path or "") or self.mod_path,
               counts["error"], counts["warning"], counts["info"],
               time.time() - t0, verdict))

    def _populate(self):
        issues = self.report.issues if self.report else []
        self.table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            sev_item = QTableWidgetItem(_SEV_CN.get(issue.severity, issue.severity))
            sev_item.setForeground(Qt.GlobalColor.white)
            sev_item.setBackground(
                self._color(issue.severity))
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, sev_item)
            self.table.setItem(row, 1, QTableWidgetItem(issue.category))
            self.table.setItem(row, 2, QTableWidgetItem(issue.file or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(issue.message))
            self.table.setItem(row, 4, QTableWidgetItem(issue.hint or ""))
        self.table.resizeRowsToContents()

    @staticmethod
    def _color(severity):
        from PyQt6.QtGui import QColor
        return QColor(_SEV_COLOR.get(severity, "#616161"))

    # ------------------------------------------------------------ 交互
    def _on_row_double_clicked(self, index):
        """双击行：在资源管理器中定位问题文件。"""
        row = index.row()
        item = self.table.item(row, 2)
        if item is None:
            return
        rel = (item.text() or "").strip()
        if not rel or rel == "-":
            return
        fp = os.path.join(self.mod_path, rel.replace("/", os.sep))
        if os.path.isfile(fp):
            try:
                subprocess.Popen(["explorer", "/select,",
                                  os.path.normpath(fp)])
            except Exception:
                pass
        elif os.path.isdir(os.path.dirname(fp)):
            try:
                subprocess.Popen(["explorer",
                                  os.path.normpath(os.path.dirname(fp))])
            except Exception:
                pass

    def _export_json(self):
        if self.report is None:
            return
        default_name = os.path.join(
            os.path.expanduser("~"),
            "export_health_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
        path, _ = QFileDialog.getSaveFileName(
            self, "保存健康检查报告", default_name, "JSON 报告 (*.json)")
        if not path:
            return
        try:
            from write_utils import atomic_write_text
            atomic_write_text(path, self.report.to_json(), undo=False)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", "报告已保存到:\n%s" % path)
