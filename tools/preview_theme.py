# -*- coding: utf-8 -*-
"""主题预览：offscreen 构建控件全景并截图（python tools/preview_theme.py）

展示主题覆盖的全部控件类别：工具栏/按钮（默认/主/危险/成功/勾选态）/
输入框/组合框/旋转框/勾选框/单选/表格（选中+交替色）/树（选中）/选项卡/
滚动条/状态栏/卡片/语义色标签（错误/警告/信息/地图强调色）。
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QRadioButton, QSpinBox, QStatusBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QToolBar, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

app = QApplication([])
from theme import apply_theme
apply_theme(app)

win = QMainWindow()
win.setWindowTitle("主题预览 — Scenario Forge 风格")

toolbar = QToolBar("主工具栏")
toolbar.setMovable(False)
toolbar.addAction("📁 打开 Mod")
toolbar.addAction("🗺 地图")
toolbar.addAction("🔬 科技")
act = toolbar.addAction("🛠 工具")
act.setCheckable(True)
win.addToolBar(toolbar)

central = QWidget()
win.setCentralWidget(central)
layout = QVBoxLayout(central)
layout.setSpacing(12)
layout.setContentsMargins(18, 14, 18, 14)

# ---- 标题区 ----
title = QLabel("Scenario Forge 风格主题预览")
title.setProperty("class", "title")
layout.addWidget(title)
sub = QLabel("背景 #e7edf2 · 主色 #1f4f7e · 地图强调 #b05b2d · 卡片圆角 16px · 按钮 10px")
sub.setProperty("class", "subtitle")
layout.addWidget(sub)

# ---- 按钮行 ----
row = QHBoxLayout()
b1 = QPushButton("默认按钮")
b2 = QPushButton("主操作")
b2.setProperty("class", "primary")
b3 = QPushButton("危险操作")
b3.setProperty("class", "danger")
b4 = QPushButton("成功操作")
b4.setProperty("class", "success")
b5 = QPushButton("切换态(勾选)")
b5.setCheckable(True)
b5.setChecked(True)
b6 = QPushButton("禁用")
b6.setEnabled(False)
for b in (b1, b2, b3, b4, b5, b6):
    row.addWidget(b)
row.addStretch(1)
layout.addLayout(row)

# ---- 输入行 ----
row = QHBoxLayout()
row.addWidget(QLabel("输入框:"))
edit = QLineEdit("输入框内容")
edit.setMinimumWidth(180)
row.addWidget(edit)
row.addWidget(QLabel("下拉:"))
combo = QComboBox()
combo.addItems(["选项 A", "选项 B", "选项 C"])
row.addWidget(combo)
row.addWidget(QLabel("数值:"))
spin = QSpinBox()
spin.setValue(42)
row.addWidget(spin)
cb = QCheckBox("复选框(勾选)")
cb.setChecked(True)
row.addWidget(cb)
rb = QRadioButton("单选(选中)")
rb.setChecked(True)
row.addWidget(rb)
row.addStretch(1)
layout.addLayout(row)

# ---- 卡片（语义色示例） ----
card = QFrame()
card.setProperty("class", "card")
card_l = QHBoxLayout(card)
card_l.setContentsMargins(14, 10, 14, 10)
card_l.addWidget(QLabel("健康检查级别色:"))
for cls, txt in (("sev_error", "错误"), ("sev_warning", "警告"), ("sev_info", "信息")):
    lab = QLabel(txt)
    lab.setProperty("class", cls)
    card_l.addWidget(lab)
card_l.addSpacing(12)
card_l.addWidget(QLabel("地图强调色:"))
ma = QLabel("地图选中/标注")
ma.setProperty("class", "map_accent")
card_l.addWidget(ma)
card_l.addStretch(1)
layout.addWidget(card)

# ---- 选项卡：表格 / 树 ----
tabs = QTabWidget()
page1 = QWidget()
p1 = QVBoxLayout(page1)
table = QTableWidget(4, 4)
table.setAlternatingRowColors(True)
table.setHorizontalHeaderLabels(["类型", "文件", "级别", "状态"])
for r in range(4):
    for c in range(4):
        table.setItem(r, c, QTableWidgetItem("内容 %d-%d" % (r, c)))
table.setCurrentCell(1, 1)
table.setColumnWidth(0, 120)
p1.addWidget(table)
tabs.addTab(page1, "表格（选中行高亮）")

page2 = QWidget()
p2 = QVBoxLayout(page2)
tree = QTreeWidget()
tree.setHeaderLabels(["节点", "值"])
root = QTreeWidgetItem(tree, ["国策树", "3 项"])
child = QTreeWidgetItem(root, ["GER_focus_1", "已选中"])
QTreeWidgetItem(child, ["prerequisite", "[]"])
QTreeWidgetItem(child, ["icon", "GFX_goals_generic"])
QTreeWidgetItem(root, ["GER_focus_2", ""])
tree.expandAll()
tree.setCurrentItem(child)
p2.addWidget(tree)
tabs.addTab(page2, "树（选中项高亮）")
layout.addWidget(tabs, 1)

win.statusBar().showMessage("状态栏 · 就绪 · 语义色与主题令牌对齐 Scenario Forge")

win.resize(1020, 720)
win.show()
for _ in range(3):
    app.processEvents()

out = os.path.join(ROOT, "主题预览.png")
win.grab().save(out)
print("saved:", out)
