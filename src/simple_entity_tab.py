"""B3 通用实体页签（simple_entity_tab）。

从 proto_misc_common 沉淀的通用构造器：
- 左侧实体列表（侧栏 + 新建/复制/重命名/删除）
- 右侧按字段定义动态生成表单
- 支持 text / loc / int / select / weight_table / trigger / ref / badge
- 只为 B3 小/中类型提供统一底座；大类型仍可单独建对话框。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_ui_common import EntityListSidebar
from ui_widgets import (
    LocEdit,
    RefPicker,
    TriggerCard,
    WeightCard,
    WeightTable,
    source_badge,
)

FIELD_TYPE_TEXT = "text"
FIELD_TYPE_LOC = "loc"
FIELD_TYPE_INT = "int"
FIELD_TYPE_SELECT = "select"
FIELD_TYPE_WEIGHT_TABLE = "weight_table"
FIELD_TYPE_TRIGGER = "trigger"
FIELD_TYPE_REF = "ref"
FIELD_TYPE_BADGE = "badge"


def _field_value(entity, key, default=""):
    if not entity:
        return default
    val = entity.get(key, entity.get("fields", {}).get(key, default))
    return val if val is not None else default


class SimpleEntityTab(QWidget):
    """通用实体编辑器：侧栏 + 动态表单。"""

    def __init__(self, entities=None, fields=None, mod_path="", hoi4_path="",
                 parent=None, list_title="实体"):
        super().__init__(parent)
        self.entities = list(entities or [])
        self.fields = list(fields or [])
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current = None
        self._widgets = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar(list_title, self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_current_changed)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)
        self.form_host = QVBoxLayout()
        self._build_form()
        right.addLayout(self.form_host, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._emit_save)
        btn_row.addWidget(self.save_btn)
        right.addLayout(btn_row)
        root.addLayout(right, 1)

        self.saved = self.save_btn.clicked
        self._populate()

    # ---------- 表单构建 ----------

    def _build_form(self):
        for fd in self.fields:
            ftype = fd.get("type", FIELD_TYPE_TEXT)
            label = fd.get("label", fd.get("key", ""))
            container = QWidget()
            lay = QVBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)
            title = QLabel(label)
            title.setStyleSheet("color:#162333; font-weight:bold;")
            lay.addWidget(title)

            if ftype == FIELD_TYPE_LOC:
                w = LocEdit(fd.get("key", ""), "")
            elif ftype == FIELD_TYPE_SELECT:
                w = QComboBox()
                w.setEditable(fd.get("editable", False))
                w.addItems(fd.get("options", []))
            elif ftype == FIELD_TYPE_WEIGHT_TABLE:
                w = WeightTable()
            elif ftype == FIELD_TYPE_TRIGGER:
                w = TriggerCard(label, "")
            elif ftype == FIELD_TYPE_REF:
                w = RefPicker(fd.get("options", []))
            elif ftype == FIELD_TYPE_BADGE:
                w = source_badge("")
            else:  # text / int
                w = QLineEdit()
                if ftype == FIELD_TYPE_INT:
                    w.setPlaceholderText("整数")
            lay.addWidget(w)
            self.form_host.addWidget(container)
            self._widgets[fd["key"]] = (fd, w)
        self.form_host.addStretch(1)

    # ---------- 数据流 ----------

    def _populate(self):
        labels = []
        for entity in self.entities:
            eid = entity.get("id", entity.get("name", ""))
            name = entity.get("name", eid)
            labels.append((eid, name))
        self.sidebar.set_entities(labels)
        if self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_current_changed(self, entity_id):
        self._current = None
        self.id_label.setText(entity_id or "—")
        if not entity_id:
            return
        for entity in self.entities:
            if entity.get("id", entity.get("name", "")) == entity_id:
                self._current = entity
                break
        self._load_values()

    def _load_values(self):
        for key, (fd, w) in self._widgets.items():
            val = _field_value(self._current, key, "")
            ftype = fd.get("type", FIELD_TYPE_TEXT)
            if ftype == FIELD_TYPE_LOC and hasattr(w, "setText"):
                w.setText(val)
            elif ftype == FIELD_TYPE_SELECT and hasattr(w, "setCurrentText"):
                w.setCurrentText(str(val))
            elif ftype == FIELD_TYPE_WEIGHT_TABLE and hasattr(w, "set_rows"):
                rows = val if isinstance(val, list) else []
                w.set_rows(rows)
            elif ftype == FIELD_TYPE_TRIGGER and hasattr(w, "setText"):
                w.setText(val)
            elif ftype == FIELD_TYPE_REF and hasattr(w, "setValue"):
                w.setValue(val)
            elif ftype == FIELD_TYPE_BADGE and hasattr(w, "setText"):
                w.setText(val)
            elif hasattr(w, "setText"):
                w.setText(str(val))

    def values(self):
        """返回当前实体字段字典（仅表单值）。"""
        out = {}
        for key, (fd, w) in self._widgets.items():
            ftype = fd.get("type", FIELD_TYPE_TEXT)
            if ftype == FIELD_TYPE_LOC:
                out[key] = w.text()
            elif ftype == FIELD_TYPE_SELECT:
                out[key] = w.currentText()
            elif ftype == FIELD_TYPE_WEIGHT_TABLE:
                out[key] = w.rows()
            elif ftype == FIELD_TYPE_TRIGGER:
                out[key] = w.text()
            elif ftype == FIELD_TYPE_REF:
                out[key] = w.value()
            elif ftype == FIELD_TYPE_BADGE:
                out[key] = w.text()
            else:
                out[key] = w.text()
        return out

    def set_entities(self, entities):
        self.entities = list(entities or [])
        self._populate()

    def _emit_save(self):
        self.saved.emit()