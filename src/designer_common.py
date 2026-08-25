"""UI 层：设计器三件套（舰艇/飞机/坦克）公共控件。

四层分离规范见 PROJECT_DOC.md §1.4：
- 本模块只做 UI 控件搭建（ModulePickerDialog）与通用展示格式化；
- 不包含具体设计器业务逻辑；名称/类别标签通过参数注入。
"""

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QSpinBox, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt

from oob_format import fmt_num


class ModulePickerDialog(QDialog):
    """点击槽位弹出的模块选择面板（按允许类别过滤）。

    Args:
        modules: dict[module_key, info]
        allowed_categories: list[str]
        slot_label: str（用于窗口标题）
        current_module: str|None（存在时显示「移除」按钮）
        name_func: callable(key)->str（模块中文名，默认原样）
        category_labels: dict[str,str]（类别中文名，默认原样）
        parent: QWidget|None
    """

    def __init__(self, modules, allowed_categories, slot_label,
                 current_module=None, name_func=None, category_labels=None,
                 parent=None):
        super().__init__(parent)
        self.modules = modules or {}
        self.allowed = allowed_categories or []
        self.name_func = name_func or (lambda k: k)
        self.category_labels = category_labels or {}
        self.picked = None
        self.remove_requested = False

        self.setWindowTitle("选择模块 — " + slot_label)
        self.resize(520, 420)
        root = QVBoxLayout(self)

        if self.allowed:
            hint = QLabel("允许类别: " + "、".join(
                self.category_labels.get(c, c) for c in self.allowed))
        else:
            hint = QLabel("（该槽位不允许任何模块）")
        hint.setStyleSheet("color:#5d6b7a; padding:2px;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_pick)
        root.addWidget(self.list_widget, 1)

        btns = QDialogButtonBox()
        if current_module:
            rm = btns.addButton("🗑 移除该模块",
                                QDialogButtonBox.ButtonRole.ActionRole)
            rm.clicked.connect(self._on_remove)
        ok = btns.addButton("确定",
                            QDialogButtonBox.ButtonRole.AcceptRole)
        ok.clicked.connect(self._on_ok)
        cancel = btns.addButton("取消",
                                QDialogButtonBox.ButtonRole.RejectRole)
        cancel.clicked.connect(self.reject)
        root.addWidget(btns)

        self._fill()

    def _fill(self):
        """列出允许类别下的模块（按类别分组显示）。"""
        self.list_widget.clear()
        items = []
        for key, info in self.modules.items():
            cat = info.get("category") or ""
            if self.allowed and cat not in self.allowed:
                continue
            cn = self.name_func(key)
            abbr = info.get("abbreviation") or ""
            cat_cn = self.category_labels.get(cat, cat)
            label = "%s  (%s) — %s" % (cn, abbr, cat_cn)
            add = info.get("add_stats") or {}
            if add:
                brief = " · ".join(
                    "%s:%s" % (k, fmt_num(v, 1))
                    for k, v in list(add.items())[:3])
                label += "\n  %s" % brief
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(key)
            items.append(item)
        items.sort(key=lambda it: it.text())
        for it in items:
            self.list_widget.addItem(it)
        if not items:
            empty = QListWidgetItem("（无可用模块）")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(empty)

    def _on_pick(self, item):
        self.picked = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_ok(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        self._on_pick(item)

    def _on_remove(self):
        self.remove_requested = True
        self.accept()


class UpgradePointsCard(QFrame):
    """升级加点区（upgrades）：按原型声明的升级键生成 SpinBox 行。"""

    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self.spinboxes = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        title = QLabel("升级加点（upgrades · 用经验强化，独立于模块）")
        title.setStyleSheet("color:#1f4f7e; font-weight:bold;")
        root.addWidget(title)
        note = QLabel("写入变体 upgrades = { 升级键 = 等级 }；等级上限受科技解锁")
        note.setStyleSheet("color:#5d6b7a; font-size:11px;")
        note.setWordWrap(True)
        root.addWidget(note)
        self._body = QVBoxLayout()
        root.addLayout(self._body)
        self.set_rows(rows or [])

    def set_rows(self, rows):
        # 清空旧行
        while self._body.count():
            item = self._body.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.spinboxes = {}
        for cn, key, cur, mx, remark in rows:
            row = QHBoxLayout()
            lab = QLabel("%s（%s）" % (cn, key))
            lab.setMinimumWidth(210)
            row.addWidget(lab)
            sp = QSpinBox()
            sp.setRange(0, mx)
            sp.setValue(cur)
            sp.setFixedWidth(72)
            row.addWidget(sp)
            mx_lab = QLabel("Lv 0~%d" % mx)
            mx_lab.setStyleSheet("color:#5d6b7a;")
            row.addWidget(mx_lab)
            if remark:
                r = QLabel(remark)
                r.setStyleSheet("color:#5d6b7a; font-size:11px;")
                r.setWordWrap(True)
                row.addWidget(r, 1)
            else:
                row.addStretch(1)
            wrap = QWidget()
            wrap.setLayout(row)
            self._body.addWidget(wrap)
            self.spinboxes[key] = sp

    def values(self):
        return {k: sp.value() for k, sp in self.spinboxes.items()}


def zone_summary_text(keys, slot_infos, limits):
    """槽位区摘要：N 槽 · 必装 M · 同类上限 cat≤N。"""
    required = sum(1 for k in keys
                   if (slot_infos.get(k) or {}).get("required"))
    parts = ["%d 槽" % len(keys), "必装 %d" % required]
    if limits:
        parts.append("同类上限 " + "、".join(
            "%s≤%d" % (l.get("category", ""), l.get("count", 0))
            for l in limits))
    return " · ".join(parts)
