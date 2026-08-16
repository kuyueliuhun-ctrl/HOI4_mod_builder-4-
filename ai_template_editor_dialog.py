"""AI 师模板编辑器（调用师编制编辑器）

- 左侧：角色模板列表（infantry_generic / armor_ENG 等）
- 中间：目标模板列表（infantry_1 / infantry_2 等）
- 「✏ 编辑目标编制」：把 target_template 转成临时 OOB，调用 DivisionEditor
- 保存：把 DivisionEditor 修改后的编制写回 AI 模板的 target_template 块
"""

from __future__ import annotations

import os
import tempfile

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from ai_loader import load_ai_templates, replace_ai_template_target_template
from division_editor import DivisionEditor
from oob_loader import OobFile, load_sub_units
from write_utils import atomic_write_text
from state_build_ops import ensure_file_in_mod


def _target_template_to_division_text(target_template):
    """把 `target_template = { ... }` 转为可被 OobFile 解析的 division_template。"""
    text = (target_template or "").strip()
    if not text:
        text = "target_template = { }"
    if text.startswith("target_template"):
        text = "division_template" + text[len("target_template"):]
    # 在首 `{` 后插入 name
    idx = text.find("{")
    if idx >= 0:
        text = text[:idx + 1] + ' name = "ai_target"' + text[idx + 1:]
    return text


def _division_template_to_target_text(tpl):
    """把 DivisionTemplate 转回 `target_template = { ... }` 文本。"""
    lines = ["target_template = {"]
    if tpl.support:
        lines.append("\tsupport = {")
        for typ, x, y in tpl.support:
            lines.append("\t\t%s = { x = %s y = %s }" % (typ, x, y))
        lines.append("\t}")
    if tpl.regiments:
        lines.append("\tregiments = {")
        for typ, x, y in tpl.regiments:
            lines.append("\t\t%s = { x = %s y = %s }" % (typ, x, y))
        lines.append("\t}")
    lines.append("}")
    return "\n".join(lines)


class AiDivisionTemplateEditor(DivisionEditor):
    """在 DivisionEditor 基础上拦截保存，写回 AI target_template。"""

    def __init__(self, oob_file, sub_units, mod_path, hoi4_path,
                 on_save, parent=None):
        self._ai_on_save = on_save
        super().__init__(oob_file, sub_units=sub_units, mod_path=mod_path,
                         hoi4_path=hoi4_path, parent=parent)

    def _save(self):
        if self.current is None:
            return
        try:
            target_text = _division_template_to_target_text(self.current)
            self._ai_on_save(target_text)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", "AI 目标编制已写回")
        self.accept()


class AiTemplateEditorDialog(QDialog):
    """AI 师模板选择器。"""

    def __init__(self, roles, mod_path="", hoi4_path="", parent=None,
                 initial_role_id=None):
        super().__init__(parent)
        self.roles = roles
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current_role = None
        self._current_target = None
        self.setWindowTitle("AI 师模板编辑器")
        self.resize(900, 560)
        self._build_ui()
        self._populate_roles(initial_role_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("角色模板"))
        self.role_list = QListWidget()
        self.role_list.currentItemChanged.connect(self._on_role_changed)
        left.addWidget(self.role_list, 1)
        root.addLayout(left, 1)

        mid = QVBoxLayout()
        mid.addWidget(QLabel("目标模板"))
        self.target_list = QListWidget()
        self.target_list.currentItemChanged.connect(self._on_target_changed)
        mid.addWidget(self.target_list, 1)
        root.addLayout(mid, 1)

        right = QVBoxLayout()
        self.info_label = QLabel("—")
        self.info_label.setWordWrap(True)
        right.addWidget(self.info_label)
        edit_btn = QPushButton("✏ 编辑目标编制（调用师编制编辑器）")
        edit_btn.clicked.connect(self._edit_target)
        right.addWidget(edit_btn)
        tree_btn = QPushButton("✏ 编辑定义（树编辑器）")
        tree_btn.clicked.connect(self._edit_tree)
        right.addWidget(tree_btn)
        right.addStretch(1)
        root.addLayout(right, 2)

    def _populate_roles(self, initial_role_id=None):
        self.role_list.blockSignals(True)
        self.role_list.clear()
        for rid in sorted(self.roles):
            item = QListWidgetItem(rid)
            item.setData(Qt.ItemDataRole.UserRole, rid)
            self.role_list.addItem(item)
        self.role_list.blockSignals(False)
        if self.role_list.count() > 0:
            target = 0
            if initial_role_id:
                for i in range(self.role_list.count()):
                    if self.role_list.item(i).data(Qt.ItemDataRole.UserRole) == initial_role_id:
                        target = i
                        break
            self.role_list.setCurrentRow(target)
            self._on_role_changed(self.role_list.currentItem())

    def _on_role_changed(self, item):
        if item is None:
            return
        rid = item.data(Qt.ItemDataRole.UserRole)
        role = self.roles.get(rid)
        if not role:
            return
        self._current_role = role
        self.target_list.blockSignals(True)
        self.target_list.clear()
        for t in role.get("targets", []):
            it = QListWidgetItem(t.get("id", ""))
            it.setData(Qt.ItemDataRole.UserRole, t.get("id", ""))
            self.target_list.addItem(it)
        self.target_list.blockSignals(False)
        if self.target_list.count() > 0:
            self.target_list.setCurrentRow(0)
            self._on_target_changed(self.target_list.currentItem())

    def _on_target_changed(self, item):
        if item is None or self._current_role is None:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        self._current_target = tid
        for t in self._current_role.get("targets", []):
            if t.get("id") == tid:
                replace = t.get("replace_with", "")
                self.info_label.setText(
                    "目标：%s\n替换：%s\n匹配：%s / %s" % (
                        tid, replace or "—",
                        t.get("replace_at_match", "—"),
                        t.get("target_min_match", "—")))
                return

    def _edit_target(self):
        if not self._current_role or not self._current_target:
            return
        target = None
        for t in self._current_role.get("targets", []):
            if t.get("id") == self._current_target:
                target = t
                break
        if target is None:
            return
        target_text = target.get("target_template", "")
        tmp_dir = tempfile.mkdtemp(prefix="dsh_ai_tpl_")
        tmp_path = os.path.join(tmp_dir, "ai_target.txt")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(_target_template_to_division_text(target_text))
            oob = OobFile(tmp_path)
        except Exception as e:
            QMessageBox.warning(self, "无法打开", "转换 AI 目标编制失败：%s" % e)
            return
        sub_units = load_sub_units(self.mod_path, self.hoi4_path)
        role_id = self._current_role["id"]
        target_id = self._current_target
        file_path = self._current_role.get("file", "")

        def on_save(new_target_text):
            self._write_target(file_path, role_id, target_id, new_target_text)

        editor = AiDivisionTemplateEditor(
            oob, sub_units, self.mod_path, self.hoi4_path,
            on_save, parent=self)
        editor.exec()
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def _write_target(self, file_path, role_id, target_id, new_target_text):
        if not file_path:
            return
        rel = self._current_role.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 师模板文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return
        content = replace_ai_template_target_template(
            content, role_id, target_id, new_target_text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        # 更新内存
        for t in self._current_role.get("targets", []):
            if t.get("id") == target_id:
                t["target_template"] = new_target_text
                break

    def _edit_tree(self):
        if not self._current_role:
            return
        fp = self._current_role.get("file", "")
        if not fp:
            return
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            QMessageBox.warning(self, "无法编辑", "请先打开 mod 目录")
            return
        from tree_node import tree_from_pdx_text
        from generic_tree_editor import GenericTreeEditor
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "无法编辑", "读取文件失败：%s" % e)
            return
        root = tree_from_pdx_text(content)
        editor = GenericTreeEditor(
            root_node=root,
            file_path=mod_fp,
            file_lines=content.splitlines(),
            block_range=(1, len(content.splitlines()) + 1),
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            loc_manager=None,
            parent=self,
            title="AI 师模板 - %s" % self._current_role["id"],
            hoi4_path=self.hoi4_path,
            mod_path=self.mod_path,
        )
        editor.show()
        try:
            model = getattr(editor, "model", None)
            if model is not None:
                results = model.find_nodes(self._current_role["id"])
                if results:
                    editor.tree_view.setCurrentIndex(results[0])
                    editor.tree_view.scrollTo(results[0])
        except Exception:
            pass

    def _ensure_writable(self, fp):
        if self.mod_path and os.path.normcase(fp).startswith(
                os.path.normcase(os.path.normpath(self.mod_path))):
            return fp, False
        if not self.mod_path or not self.hoi4_path:
            return None, False
        try:
            rel = os.path.relpath(fp, self.hoi4_path).replace("\\", "/")
            if not rel.startswith(".."):
                return ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        except Exception:
            pass
        return None, False


def open_ai_template_editor(file_path, mod_path="", hoi4_path="",
                            entity_id=None, parent=None):
    """按文件/实体打开 AI 师模板编辑器。"""
    roles = load_ai_templates(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_roles = {}
    for rid, role in roles.items():
        if os.path.normpath(role.get("file", "")).replace("\\", "/") == norm:
            file_roles[rid] = role
    if not file_roles:
        return False
    dlg = AiTemplateEditorDialog(
        file_roles, mod_path, hoi4_path, parent,
        initial_role_id=entity_id if entity_id in file_roles else None)
    dlg.exec()
    return True
