"""覆盖规则与增量报告对话框（SF 移植：规则分层 + delta 增量模型）

表格展示 mod 每个内容文件的分类（new/override/identical）、质量分级与
行级增量；选中行预览与游戏原版的差异；可导出 JSON 报告（原子写）。
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QSplitter, QPlainTextEdit, QMessageBox, QFileDialog,
)

_QUALITY_CN = {"direct_copy": "直接拷贝", "manual_reviewed": "人工复核",
               "approx": "近似", "blocker": "阻断审查"}
_KIND_CN = {"new": "新增", "override": "覆盖", "identical": "一致"}


class OverlayReportDialog(QDialog):
    """覆盖增量报告（mod 覆盖原版）。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.report = None
        self.setWindowTitle("覆盖规则与增量报告（mod vs 游戏原版）")
        self.resize(980, 640)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.summary_label = QLabel("构建中…")
        root.addWidget(self.summary_label)

        bar = QHBoxLayout()
        self.export_btn = QPushButton("💾 导出 JSON 报告")
        self.export_btn.clicked.connect(self._export)
        bar.addWidget(self.export_btn)
        bar.addStretch(1)
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        bar.addWidget(self.close_btn)
        root.addLayout(bar)

        split = QSplitter(self)
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(
            ["文件", "类型", "质量", "新增行", "删除行", "修改字节"])
        self.table.setColumnWidth(0, 380)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 80)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.currentCellChanged.connect(self._on_row)
        split.addWidget(self.table)

        self.preview = QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("选中行 → 与游戏原版的差异预览")
        split.addWidget(self.preview)
        split.setSizes([640, 340])
        root.addWidget(split, 1)

    def _load(self):
        try:
            from overlay_rules import build_override_report
            self.report = build_override_report(self.mod_path, self.hoi4_path)
        except Exception as e:
            QMessageBox.critical(self, "构建失败", str(e))
            self.report = None
            return
        s = self.report["stats"]
        self.summary_label.setText(
            f"mod: {self.report['mod_path']}\n"
            f"共 {s['total']} 个内容文件 | 新增 {s.get('new', 0)} | "
            f"覆盖 {s.get('override', 0)} | 与原版一致 {s.get('identical', 0)}")
        self.table.setRowCount(0)
        for e in self.report["files"]:
            if e["kind"] == "identical":
                continue      # 一致文件不占行
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(e["rel"]))
            self.table.setItem(r, 1, QTableWidgetItem(
                _KIND_CN.get(e["kind"], e["kind"])))
            self.table.setItem(r, 2, QTableWidgetItem(
                _QUALITY_CN.get(e["quality"], e["quality"])))
            d = e.get("delta") or {}
            self.table.setItem(r, 3, QTableWidgetItem(str(d.get("added", ""))))
            self.table.setItem(r, 4, QTableWidgetItem(
                str(d.get("removed", ""))))
            self.table.setItem(r, 5, QTableWidgetItem(
                str(e.get("mod_size", ""))))

    def _on_row(self, row, _col, _pr, _pc):
        if self.report is None or row < 0 or row >= len(self.table):
            return
        e = self.report["files"][row]
        if e.get("binary"):
            self.preview.setPlainText(
                f"[二进制文件] mod {e.get('mod_size', 0)} 字节"
                f" vs 游戏 {e.get('game_size', 0)} 字节（不做行级对比）")
            return
        try:
            mod_p = os.path.join(self.report["mod_path"],
                                 e["rel"].replace("/", os.sep))
            game_p = os.path.join(self.report["game_path"],
                                  e["rel"].replace("/", os.sep))
            import difflib
            with open(game_p, "r", encoding="utf-8", errors="replace") as f:
                gl = f.read().replace("\r\n", "\n").split("\n")
            with open(mod_p, "r", encoding="utf-8", errors="replace") as f:
                ml = f.read().replace("\r\n", "\n").split("\n")
            diff = list(difflib.unified_diff(gl, ml, "游戏原版", "mod 当前",
                                             lineterm=""))
            self.preview.setPlainText("\n".join(diff[:400]))
        except Exception as ex:
            self.preview.setPlainText(str(ex))

    def _export(self):
        if self.report is None:
            return
        default = os.path.join(self.mod_path or os.getcwd(),
                               "overlay_report.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出覆盖增量报告", default, "JSON (*.json)")
        if not path:
            return
        try:
            from overlay_rules import write_override_report
            write_override_report(self.mod_path, self.hoi4_path, path)
            QMessageBox.information(self, "已导出", f"已导出到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
