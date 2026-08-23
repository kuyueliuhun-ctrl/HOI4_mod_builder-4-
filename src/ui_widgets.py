"""B0 公共 UI 组件（2026-08-23，对话.md B0 首版落地）。

提供 P10~P39 全量工作台复用的基础件：
- BlockTreeList / BlockListCard：块树列表标准形态（双语列 + 行内编辑 + 右键）
- BLOCK_CN：常用块键中文词典
- LocEdit / source_badge / RefPicker / WeightCard / WeightTable /
  TriggerCard / OrderRowList / OtherFieldsTable
- StructuredBlockBrowser：结构化浏览器（作为「高级」入口的轻量实现）

后续迭代：ScriptBlockEditorDialog 重构为 BlockTreeList 封装；BLOCK_CN 接
game loc/QIUQI 词条库扩充。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ai_ui_common import KeyValueTableEditor as _KeyValueTableEditor

# 常用块键中文词典（正式版扩充并接本地化/词条库）
BLOCK_CN = {
    "name": "名称",
    "desc": "描述",
    "type": "类型",
    "icon": "图标",
    "cost": "花费",
    "visible": "可见性",
    "available": "可用条件",
    "enable": "启用条件",
    "remove_trigger": "移除条件",
    "ai_will_do": "AI 意愿",
    "modifier": "修正",
    "country_modifier": "国家修正",
    "state_modifier": "州修正",
    "research": "科研",
    "ideas": "理念",
    "traits": "特质",
    "focus": "国策",
    "regions": "区域",
    "weight": "权重",
    "factor": "系数",
    "base": "基础值",
    "target_template": "目标编制",
    "target_variant": "目标变体",
    "allowed_modules": "允许模块",
    "mission": "任务",
    "min_composition": "最小构成",
    "optimal_composition": "最优构成",
    "objective_type": "目标类型",
    "priority": "优先级",
    "category": "类别",
    "slot": "槽位",
    "id": "ID",
    "value": "值",
    "values": "值组",
    "default": "默认",
}


def _cn(key: str) -> str:
    """键 → 中文（未知键原样返回）。"""
    return BLOCK_CN.get(key, key)


def source_badge(source: str = "") -> QLabel:
    """返回 mod 改写/置空/本体 的状态小标签。"""
    lbl = QLabel()
    if source == "mod":
        lbl.setText("mod 改写")
        lbl.setStyleSheet("color:#2f7d57; font-weight:bold;")
    elif source == "empty":
        lbl.setText("mod 置空")
        lbl.setStyleSheet("color:#b7791f; font-weight:bold;")
    elif source == "game":
        lbl.setText("本体")
        lbl.setStyleSheet("color:#5d6b7a;")
    else:
        lbl.setText("")
    return lbl


class LocEdit(QWidget):
    """本地化双行编辑：键（只读）+ 中文（可编辑）。"""

    textChanged = pyqtSignal(str)

    def __init__(self, key: str = "", value: str = "", parent=None):
        super().__init__(parent)
        self._key = key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.key_label = QLabel(_cn(key) + "  " + key)
        self.key_label.setStyleSheet("color:#5d6b7a; font-size:12px;")
        self.value_edit = QLineEdit(value)
        self.value_edit.setPlaceholderText("中文/本地化内容")
        self.value_edit.textChanged.connect(self.textChanged)
        lay.addWidget(self.key_label)
        lay.addWidget(self.value_edit)

    def key(self) -> str:
        return self._key

    def text(self) -> str:
        return self.value_edit.text()

    def setText(self, text: str) -> None:
        self.value_edit.setText(text)


class BlockTreeList(QTreeWidget):
    """块树列表：键（中文+原键）/值/中文 三列，双击就地编辑，右键通用菜单。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHeaderLabels(["键（中文+原键）", "值", "中文"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

    def add_item(self, key: str, value: str = "", cn: str = ""):
        item = QTreeWidgetItem([f"{_cn(key)}  {key}", value, cn])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setData(0, Qt.ItemDataRole.UserRole, key)
        self.addTopLevelItem(item)
        return item

    def data(self):
        """返回 [{key, value, cn}]；key 从 UserRole 读。"""
        out = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            out.append({
                "key": item.data(0, Qt.ItemDataRole.UserRole) or item.text(0),
                "value": item.text(1),
                "cn": item.text(2),
            })
        return out

    def _show_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self)
        act_add = menu.addAction("添加词条")
        act_add_sub = menu.addAction("添加子块")
        act_del = menu.addAction("删除")
        act_up = menu.addAction("上移")
        act_down = menu.addAction("下移")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen == act_add:
            self.add_item("new_key", "", "")
        elif chosen == act_add_sub:
            self._add_child_item(item)
        elif chosen == act_del and item is not None:
            parent = item.parent()
            (parent or self).removeChild(item)
        elif chosen == act_up and item is not None:
            self._move(item, -1)
        elif chosen == act_down and item is not None:
            self._move(item, 1)

    def _add_child_item(self, parent_item):
        if parent_item is None:
            return
        child = QTreeWidgetItem(["新子块", "", ""])
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
        parent_item.addChild(child)

    def _move(self, item, delta):
        parent = item.parent()
        container = parent if parent is not None else self.invisibleRootItem()
        idx = container.indexOfChild(item)
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= container.childCount():
            return
        taken = container.takeChild(idx)
        container.insertChild(new_idx, taken)
        self.setCurrentItem(taken)


class BlockListCard(QFrame):
    """内联块列表卡 = BlockTreeList + 标题双语 + 收起切换单行摘要。"""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: #f7f9fb; border-radius: 8px; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)
        head = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight:bold; color:#162333;")
        self.toggle_btn = QPushButton("▾ 收起")
        self.toggle_btn.setFlat(True)
        self.toggle_btn.clicked.connect(self._toggle)
        head.addWidget(self.title_label)
        head.addStretch(1)
        head.addWidget(self.toggle_btn)
        lay.addLayout(head)
        self.tree = BlockTreeList(self)
        lay.addWidget(self.tree)
        self._collapsed = False

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.tree.setVisible(not self._collapsed)
        self.toggle_btn.setText("▸ 展开" if self._collapsed else "▾ 收起")


class RefPicker(QWidget):
    """下拉+搜索+「⚠ 未找到」不阻止手输。"""

    def __init__(self, items=None, current="", parent=None):
        super().__init__(parent)
        self._items = list(items or [])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.addItems(self._items)
        if current:
            self.combo.setCurrentText(current)
        self.warn = QLabel("")
        self.warn.setStyleSheet("color:#b7791f;")
        self.combo.currentTextChanged.connect(self._check)
        lay.addWidget(self.combo, 1)
        lay.addWidget(self.warn)

    def _check(self, text):
        if text and self._items and text not in self._items:
            self.warn.setText("⚠ 未找到")
        else:
            self.warn.setText("")

    def value(self) -> str:
        return self.combo.currentText().strip()

    def setValue(self, text: str) -> None:
        self.combo.setCurrentText(text)


class WeightTable(QTableWidget):
    """权重/键值表：两列可编辑（键、值），带增删行。"""

    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["键", "值"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setMinimumHeight(120)

    def set_rows(self, rows):
        self.setRowCount(len(rows))
        for r, (k, v) in enumerate(rows):
            self.setItem(r, 0, QTableWidgetItem(str(k)))
            self.setItem(r, 1, QTableWidgetItem(str(v)))

    def rows(self):
        out = []
        for r in range(self.rowCount()):
            k = self.item(r, 0)
            v = self.item(r, 1)
            if k is not None and k.text().strip():
                out.append((k.text(), v.text() if v else ""))
        return out

    def add_row(self, key="", value=""):
        r = self.rowCount()
        self.insertRow(r)
        self.setItem(r, 0, QTableWidgetItem(key))
        self.setItem(r, 1, QTableWidgetItem(value))


class WeightCard(QGroupBox):
    """加权卡：标题 + WeightTable。"""

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        lay = QVBoxLayout(self)
        self.table = WeightTable()
        lay.addWidget(self.table)
        btn = QPushButton("＋ 添加行")
        btn.clicked.connect(self.table.add_row)
        lay.addWidget(btn)


class TriggerCard(QGroupBox):
    """触发/条件卡：标题 + 可编辑 PDX 块文本（后续接结构化 BlockTreeList）。"""

    def __init__(self, title="", text="", parent=None):
        super().__init__(title, parent)
        lay = QVBoxLayout(self)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("触发块文本（结构化浏览器兜底）")
        self.edit.setText(text)
        lay.addWidget(self.edit)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, text: str) -> None:
        self.edit.setText(text)


class OrderRowList(QListWidget):
    """顺序行列表（上移/下移/删除/添加）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._btn_add = None

    def set_order(self, items):
        self.clear()
        self.addItems(items)

    def order(self):
        return [self.item(i).text() for i in range(self.count())]


class OtherFieldsTable(_KeyValueTableEditor):
    """其他字段表（复用 KeyValueTableEditor）。"""


class StructuredBlockBrowser(QDialog):
    """结构化浏览器：轻量树形查看/编辑 PDX 块（B0 高级入口）。"""

    def __init__(self, block_text="", title="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "结构化浏览器")
        self.resize(640, 480)
        lay = QVBoxLayout(self)
        self.tree = BlockTreeList()
        # 简要把多行块按行填入，真实解析后续接 tree_node
        for line in block_text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                self.tree.add_item(k.strip(), v.strip())
            elif block_text.strip():
                self.tree.add_item(line.strip())
        lay.addWidget(self.tree)
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)

    def block_text(self) -> str:
        rows = []
        for item in self.tree.data():
            rows.append(f"{item['key']} = {item['value']}")
        return "\n".join(rows)