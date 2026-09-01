"""多 Mod 冲突检查报告对话框（阶段B UI）。

流程：选择播放集（launcher-v2.sqlite / dlc_load）→ 扫描（分域进度）→
三级树（严重度 → 类型 → 条目）→ 双击跳转文件 / 导出 JSON、HTML。

数据来源：conflict_scan.scan_conflicts（纯算法层，本模块只做展示）。
导出走 write_utils.atomic_write_text（写入纪律：用户另存为显式指定，
非 mod 内容）。
"""
from __future__ import annotations

import os
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout)

from playset_loader import hoi4_user_dir, list_playsets

SHOW_CAP = 12          # HTML 报告单条目最多展示的位置数
_SEV_LABEL = {"error": "⛔ 错误", "warning": "⚠ 警告", "info": "ℹ 提示"}
_SEV_ORDER = ("error", "warning", "info")

_KIND_LABEL = {
    "duplicate_mod": "重复注册",
    "missing_dependency": "缺失依赖",
    "dependency_cycle": "依赖环",
    "version_mismatch": "版本不匹配",
    "file_shadow": "整文件覆盖",
    "replaced_by_replace_path": "replace_path 清空",
    "entity_id": "实体 id 冲突",
    "loc_key": "本地化键冲突",
}


class ConflictReportDialog(QDialog):
    """播放集冲突扫描与报告。"""

    def __init__(self, parent=None, settings=None, open_file_cb=None):
        super().__init__(parent)
        self.setWindowTitle("多 Mod 冲突检查")
        self.resize(980, 640)
        self.settings = settings or {}
        self.open_file_cb = open_file_cb
        self.report = None
        self._playset = None          # 最近一次扫描的 Playset（跳转复用）
        self._user_dir = hoi4_user_dir(self.settings)

        self._build_ui()
        self._reload_playsets()

    # ---------- UI 构建 ----------

    def _build_ui(self):
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("播放集:"))
        self.playset_combo = QComboBox()
        self.playset_combo.setMinimumWidth(280)
        top.addWidget(self.playset_combo)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self._reload_playsets)
        top.addWidget(self.btn_refresh)
        self.chk_vanilla = QCheckBox("含原版层（文件遮蔽）")
        top.addWidget(self.chk_vanilla)
        self.chk_loc = QCheckBox("本地化扫描")
        self.chk_loc.setChecked(True)
        top.addWidget(self.chk_loc)
        self.chk_entities = QCheckBox("实体 id 扫描")
        self.chk_entities.setChecked(True)
        top.addWidget(self.chk_entities)
        top.addStretch()
        self.btn_scan = QPushButton("开始扫描")
        self.btn_scan.clicked.connect(self._on_scan)
        top.addWidget(self.btn_scan)
        lay.addLayout(top)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["冲突条目", "受害方", "胜者", "位置数"])
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(self._on_item_open)
        lay.addWidget(self.tree)

        bottom = QHBoxLayout()
        self.lbl_stats = QLabel("选择播放集后点击「开始扫描」。")
        bottom.addWidget(self.lbl_stats, 1)
        self.btn_export_json = QPushButton("导出 JSON…")
        self.btn_export_json.clicked.connect(self._export_json)
        self.btn_export_json.setEnabled(False)
        bottom.addWidget(self.btn_export_json)
        self.btn_export_html = QPushButton("导出 HTML…")
        self.btn_export_html.clicked.connect(self._export_html)
        self.btn_export_html.setEnabled(False)
        bottom.addWidget(self.btn_export_html)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        lay.addLayout(bottom)

    def _reload_playsets(self):
        self.playset_combo.clear()
        if not self._user_dir:
            self.lbl_stats.setText(
                "未找到 HOI4 用户文档目录（需 settings.json 的 mod_file_path "
                "指向 …/Hearts of Iron IV/mod，或设置 hoi4_user_path）。")
            self.btn_scan.setEnabled(False)
            return
        self.btn_scan.setEnabled(True)
        for entry in list_playsets(self._user_dir):
            label = entry["name"]
            if entry["source"] == "sqlite":
                label += "（播放集）"
            self.playset_combo.addItem(label, entry["id"])

    # ---------- 扫描 ----------

    def _on_scan(self):
        from conflict_scan import scan_conflicts
        from playset_loader import load_playset

        pid = self.playset_combo.currentData()
        if not pid:
            return
        hoi4_path = self.settings.get("HOI4_path", "")
        self.btn_scan.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        QApplication.processEvents()

        def progress(stage, done, total):
            self.progress.setMaximum(max(int(total), 1))
            self.progress.setValue(min(int(done), int(total)))
            self.lbl_stats.setText("扫描中：%s" % stage)
            QApplication.processEvents()

        try:
            self._playset = load_playset(self._user_dir, pid)
            self.report = scan_conflicts(
                self._playset, hoi4_path=hoi4_path,
                include_vanilla=self.chk_vanilla.isChecked(),
                scan_entities=self.chk_entities.isChecked(),
                scan_loc=self.chk_loc.isChecked(), progress=progress)
        except Exception as e:      # 防御：扫描失败不让对话框崩溃
            QMessageBox.critical(self, "扫描失败", str(e))
            self.report = None
        finally:
            self.progress.setVisible(False)
            self.btn_scan.setEnabled(True)

        self._fill_tree()
        self._update_stats(pid)

    def _update_stats(self, pid):
        if self.report is None:
            return
        counts = self.report.counts()
        by_sev = counts["by_severity"]
        note = ""
        if self.report.truncated_kinds:
            note = "（部分类别超过 %d 条已截断：%s）" % (
                500, "、".join(self.report.truncated_kinds))
        self.lbl_stats.setText(
            "「%s」：%d 条冲突（错误 %d / 警告 %d / 提示 %d），"
            "扫描 %d 个文件（跳过 %d），耗时 %d ms%s"
            % (self.playset_combo.currentText(),
               len(self.report.items),
               by_sev.get("error", 0), by_sev.get("warning", 0),
               by_sev.get("info", 0),
               self.report.scanned_files, self.report.skipped_files,
               self.report.duration_ms, note))
        has = bool(self.report.items)
        self.btn_export_json.setEnabled(has)
        self.btn_export_html.setEnabled(has)

    def _fill_tree(self):
        self.tree.clear()
        if self.report is None:
            return
        groups = {}
        for it in self.report.items:
            groups.setdefault(it.severity, {}).setdefault(it.kind, []).append(it)
        for sev in _SEV_ORDER:
            if sev not in groups:
                continue
            sev_item = QTreeWidgetItem([_SEV_LABEL.get(sev, sev)])
            sev_item.setFirstColumnSpanned(True)
            flags = sev_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
            sev_item.setFlags(flags)
            self.tree.addTopLevelItem(sev_item)
            for kind, items in sorted(groups[sev].items(),
                                      key=lambda kv: -len(kv[1])):
                kind_item = QTreeWidgetItem(
                    ["%s（%d）" % (_KIND_LABEL.get(kind, kind), len(items)),
                     "", "", ""])
                kind_item.setFirstColumnSpanned(True)
                flags = kind_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
                kind_item.setFlags(flags)
                sev_item.addChild(kind_item)
                for it in items:
                    leaf = QTreeWidgetItem(
                        [it.title, it.victim, it.winner,
                         str(len(it.locations))])
                    leaf.setData(0, Qt.ItemDataRole.UserRole, it)
                    leaf.setToolTip(0, it.detail)
                    kind_item.addChild(leaf)
        self.tree.expandToDepth(0)

    def _on_item_open(self, item, _col):
        it = item.data(0, Qt.ItemDataRole.UserRole)
        if it is None:
            return
        if not it.locations:
            return
        # 位置格式 "mod名: 相对路径"；结合播放集内容目录解析为绝对路径
        loc = it.locations[0]
        rel = loc.split(": ", 1)[-1]
        playset = self._playset
        if playset is None:
            from playset_loader import load_playset
            playset = load_playset(
                self._user_dir, self.playset_combo.currentData())
        for m in playset.mods:
            cand = os.path.join(m.content_dir, rel.replace("\\", "/"))
            if os.path.isfile(cand):
                if self.open_file_cb:
                    self.open_file_cb(cand)
                else:
                    QMessageBox.information(self, it.title, loc)
                return
        QMessageBox.information(self, it.title,
                                loc + "\n\n（文件不存在或已被删除）")

    # ---------- 导出 ----------

    def _export_json(self):
        if self.report is None:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            "conflict_report_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
        path, _ = QFileDialog.getSaveFileName(
            self, "导出冲突报告", default, "JSON 报告 (*.json)")
        if not path:
            return
        import json
        payload = {
            "playset": self.report.playset_name,
            "include_vanilla": self.report.include_vanilla,
            "duration_ms": self.report.duration_ms,
            "scanned_files": self.report.scanned_files,
            "skipped_files": self.report.skipped_files,
            "truncated_kinds": self.report.truncated_kinds,
            "counts": self.report.counts(),
            "items": self.report.to_dicts(),
        }
        try:
            from write_utils import atomic_write_text
            atomic_write_text(path, json.dumps(payload, ensure_ascii=False,
                                               indent=2), undo=False)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
            return
        QMessageBox.information(self, "已导出", "报告已保存到:\n%s" % path)

    def _export_html(self):
        if self.report is None:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            "conflict_report_%s.html" % time.strftime("%Y%m%d_%H%M%S"))
        path, _ = QFileDialog.getSaveFileName(
            self, "导出冲突报告", default, "HTML 报告 (*.html)")
        if not path:
            return
        try:
            from write_utils import atomic_write_text
            atomic_write_text(path, _render_html(self.report), undo=False)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
            return
        QMessageBox.information(self, "已导出", "报告已保存到:\n%s" % path)


def _render_html(report):
    """独立自包含 HTML 报告（无外部资源）。"""
    counts = report.counts()
    by_sev = counts["by_severity"]
    rows = []
    for it in report.items:
        locs = "<br>".join(
            l.replace("&", "&amp;").replace("<", "&lt;")
            for l in it.locations[:SHOW_CAP])
        more = ("…（另有 %d 个位置）" % (len(it.locations) - SHOW_CAP)
                if len(it.locations) > SHOW_CAP else "")
        rows.append(
            "<tr class='%s'><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
            "<td>%s%s</td></tr>" % (
                it.severity,
                _KIND_LABEL.get(it.kind, it.kind),
                _esc(it.title), _esc(it.victim), _esc(it.winner),
                locs, _esc(more)))
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>多Mod冲突报告 - %s</title><style>"
        "body{font-family:'Microsoft YaHei',sans-serif;margin:24px;"
        "background:#f7f7f7;color:#222}"
        "h1{font-size:20px}table{border-collapse:collapse;width:100%%;"
        "background:#fff;font-size:13px}"
        "th,td{border:1px solid #ddd;padding:6px 8px;vertical-align:top;"
        "text-align:left}"
        "th{background:#eee}tr.error td:first-child{border-left:4px solid #c00}"
        "tr.warning td:first-child{border-left:4px solid #e90}"
        "tr.info td:first-child{border-left:4px solid #06c}"
        "</style></head><body>"
        "<h1>多 Mod 冲突报告 — %s</h1>"
        "<p>生成时间：%s ｜ 冲突 %d 条（错误 %d / 警告 %d / 提示 %d）｜ "
        "扫描 %d 文件（跳过 %d）｜ 耗时 %d ms ｜ 含原版层：%s</p>"
        "<table><tr><th>类型</th><th>条目</th><th>受害方</th><th>胜者</th>"
        "<th>位置</th></tr>%s</table></body></html>"
        % (_esc(report.playset_name), _esc(report.playset_name),
           time.strftime("%Y-%m-%d %H:%M:%S"), len(report.items),
           by_sev.get("error", 0), by_sev.get("warning", 0),
           by_sev.get("info", 0), report.scanned_files,
           report.skipped_files, report.duration_ms,
           "是" if report.include_vanilla else "否",
           "".join(rows)))


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def open_conflict_report(parent=None, settings=None, open_file_cb=None):
    """工具菜单入口：创建并模态显示冲突报告对话框。"""
    dlg = ConflictReportDialog(parent=parent, settings=settings,
                               open_file_cb=open_file_cb)
    dlg.exec()
