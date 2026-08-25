"""Mod 描述（.mod）专用编辑器（B3-P39）。

针对 HOI4 `descriptor.mod` 的扁平 key-value 形态提供表单式编辑：
- 已知标量字段：name / version / supported_version / remote_file_id / path / archive / picture
- 列表字段：tags / replace_path（重复标量）/ dependencies
- 其他未知条目：以原始文本原样保留（解析回条目，不丢数据）
写回统一走 `write_utils.atomic_write_text` 原子写。
"""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from mod_descriptor_loader import (
    SCALAR_FIELDS,
    build_entries,
    extract_fields,
    format_mod_entries,
    parse_mod_entries,
    split_list_text,
)
from write_utils import atomic_write_text


def _read_file(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


class ModDescriptorEditorDialog(QDialog):
    """Mod 描述专用编辑器（单文件表单）。"""

    def __init__(self, file_path="", mod_path="", hoi4_path="",
                 parent=None, entity_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.file_path = file_path or self._find_descriptor()
        self.setWindowTitle("Mod 描述编辑器")
        self.resize(760, 640)

        self._scalar_edits = {}
        self._tags_edit = None
        self._replace_path_edit = None
        self._deps_edit = None
        self._other_edit = None

        self._build_ui()
        self._load()

    # ---------- 查找 / 加载 ----------

    def _find_descriptor(self):
        if not self.mod_path or not os.path.isdir(self.mod_path):
            return ""
        direct = os.path.join(self.mod_path, "descriptor.mod")
        if os.path.isfile(direct):
            return direct
        for name in sorted(os.listdir(self.mod_path)):
            if name.lower().endswith(".mod"):
                return os.path.join(self.mod_path, name)
        return direct

    def _build_ui(self):
        root = QVBoxLayout(self)
        hint = QLabel(
            "编辑 Mod 描述（descriptor.mod）。修改后点「保存」原子写回；"
            "未知字段在「其他条目」中保留。")
        hint.setWordWrap(True)
        root.addWidget(hint)

        form = QFormLayout()
        for key in SCALAR_FIELDS:
            edit = QLineEdit()
            edit.setPlaceholderText(key)
            self._scalar_edits[key] = edit
            label = _field_label(key)
            form.addRow(label, edit)
        root.addLayout(form)

        self._tags_edit = self._make_list_edit(
            root, "tags（每行一个，游戏内模组标签）")
        self._replace_path_edit = self._make_list_edit(
            root, "replace_path（每行一个，覆盖游戏原版目录）")
        self._deps_edit = self._make_list_edit(
            root, "dependencies（每行一个，依赖模组 id）")

        root.addWidget(QLabel("其他条目（原样保留，key = value 或 key = { ... }）"))
        self._other_edit = QPlainTextEdit()
        self._other_edit.setPlaceholderText('例如：\narchive="mod/xxx.zip"\npicture="thumbnail.png"')
        self._other_edit.setFixedHeight(120)
        root.addWidget(self._other_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

    def _make_list_edit(self, root, label):
        root.addWidget(QLabel(label))
        edit = QPlainTextEdit()
        edit.setFixedHeight(70)
        root.addWidget(edit)
        return edit

    def _load(self):
        text = _read_file(self.file_path) if self.file_path else ""
        fields = extract_fields(parse_mod_entries(text))
        for key in SCALAR_FIELDS:
            self._scalar_edits[key].setText(fields.get(key, ""))
        self._tags_edit.setPlainText("\n".join(fields.get("tags", [])))
        self._replace_path_edit.setPlainText("\n".join(fields.get("replace_path", [])))
        self._deps_edit.setPlainText("\n".join(fields.get("dependencies", [])))
        self._other_edit.setPlainText(format_mod_entries(fields.get("other", [])))

    # ---------- 保存 ----------

    def _collect_fields(self):
        fields = {k: edit.text().strip() for k, edit in self._scalar_edits.items()}
        fields["tags"] = split_list_text(self._tags_edit.toPlainText())
        fields["replace_path"] = split_list_text(self._replace_path_edit.toPlainText())
        fields["dependencies"] = split_list_text(self._deps_edit.toPlainText())
        fields["other"] = parse_mod_entries(self._other_edit.toPlainText())
        return fields

    def _on_save(self):
        fields = self._collect_fields()
        entries = build_entries(fields)
        text = format_mod_entries(entries)
        fp = self.file_path
        if not fp:
            fp = os.path.join(self.mod_path or ".", "descriptor.mod")
        try:
            atomic_write_text(fp, text, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "错误", "保存 Mod 描述失败：%s" % e)
            return
        self.file_path = fp
        QMessageBox.information(self, "已保存", "Mod 描述已保存：\n%s" % fp)


def _field_label(key):
    labels = {
        "name": "名称 name",
        "version": "版本 version",
        "supported_version": "支持版本 supported_version",
        "remote_file_id": "工坊 ID remote_file_id",
        "path": "路径 path",
        "archive": "压缩包 archive",
        "picture": "封面图 picture",
    }
    return labels.get(key, key)


def open_mod_descriptor_editor(file_path="", mod_path="", hoi4_path="",
                               entity_id=None, parent=None):
    """入口：打开 Mod 描述专用编辑器（非模态）。"""
    dlg = ModDescriptorEditorDialog(
        file_path=file_path, mod_path=mod_path, hoi4_path=hoi4_path,
        parent=parent, entity_id=entity_id)
    dlg.show()
    return dlg