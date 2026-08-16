"""游戏数据参考面板：浏览游戏原版国家/意识形态数据作为创作参考。

- 列出游戏 common/countries 全部国家 tag
- 合并游戏/mod 本地化显示中文名（词条 key = tag）
- 显示意识形态（history/countries 或 common/countries 中的 ideology 字段）
- 搜索过滤、点击复制 tag
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QApplication, QMessageBox)


def load_game_countries(game_path, mod_path=""):
    """读取游戏（+mod 覆盖）国家列表。

    Returns:
        list[dict]: [{tag, name, file, ideology}]
    """
    rows = []
    seen = set()
    loc = {}
    # 本地化词条（key = tag → 中文名）
    for base in (game_path, mod_path):
        if not base:
            continue
        loc_dir = os.path.join(base, "localisation", "simp_chinese")
        if os.path.isdir(loc_dir):
            try:
                from localization_mgr import load_loc_yml_dir
                cache = {}
                load_loc_yml_dir(loc_dir, cache)
                loc.update(cache)
            except Exception:
                pass
    for base in (game_path, mod_path):
        if not base:
            continue
        cdir = os.path.join(base, "common", "countries")
        if not os.path.isdir(cdir):
            continue
        for fn in sorted(os.listdir(cdir)):
            if not fn.lower().endswith(".txt"):
                continue
            tag = os.path.splitext(fn)[0].upper()
            if not tag or tag in seen:
                continue
            seen.add(tag)
            rows.append({
                "tag": tag,
                "name": loc.get(tag, ""),
                "file": os.path.join(cdir, fn),
                "ideology": "",
            })
    # 意识形态：history/countries 文件内 ideology = X（尽力提取）
    for r in rows:
        try:
            with open(r["file"], "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read(4096)
            import re
            m = re.search(r'\bideology\s*=\s*([a-z_0-9]+)', text)
            if m:
                r["ideology"] = m.group(1)
        except Exception:
            pass
    return rows


class GameReferenceDialog(QDialog):
    """游戏数据参考对话框：国家表 + 搜索 + 复制 tag。"""

    def __init__(self, parent=None, game_path="", mod_path=""):
        super().__init__(parent)
        self.setWindowTitle("游戏数据参考 · 国家")
        self.resize(720, 520)
        self._rows = load_game_countries(game_path, mod_path)
        if not self._rows:
            QMessageBox.information(
                self, "提示", "未找到游戏国家数据，请先配置钢铁雄心4目录")
            self._rows = []

        lay = QVBoxLayout(self)
        if game_path:
            lay.addWidget(QLabel(f"数据来源：{game_path}"))
        else:
            lay.addWidget(QLabel("数据来源：未配置游戏目录"))
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索 tag / 中文名…")
        self.search_edit.textChanged.connect(self._fill)
        search_row.addWidget(self.search_edit)
        copy_btn = QPushButton("📋 复制选中 tag")
        copy_btn.clicked.connect(self._copy_selected)
        search_row.addWidget(copy_btn)
        lay.addLayout(search_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["tag", "中文名", "意识形态"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda _i: self._copy_selected())
        lay.addWidget(self.table)
        self._fill()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

    def _fill(self):
        kw = self.search_edit.text().strip().lower()
        shown = [r for r in self._rows
                 if not kw or kw in r["tag"].lower() or kw in r["name"].lower()]
        self.table.setRowCount(len(shown))
        for i, r in enumerate(shown):
            self.table.setItem(i, 0, QTableWidgetItem(r["tag"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["ideology"]))
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 260)

    def _copy_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个国家")
            return
        tag = self.table.item(row, 0).text()
        QApplication.clipboard().setText(tag)
        QMessageBox.information(self, "已复制", f"已复制国家 tag：{tag}")
