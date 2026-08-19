"""角色（Character）专用编辑器

左侧：文件 + 角色列表；右侧：编辑 名称键 / 中文名 / 肖像，保存写 mod。
不破坏角色内其余角色块（country_leader/advisor/leader 等）。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
    QVBoxLayout, QWidget,
)

from character_data import find_char_file, load_file, render_character_block, save_file
from localisation_editor_data import load_effective_dict, upsert_loc_entry, find_mod_file_for_key


def _char_file_list(mod_path, hoi4_path):
    files = []
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "common", "characters")
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                if n.lower().endswith(".txt"):
                    files.append(os.path.join(d, n))
    return files


class CharacterEditorDialog(QDialog):
    """角色专用编辑器（非模态）。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._metas = []
        self._header = ""
        self._tail = ""
        self._current_file = ""

        self.setWindowTitle("角色（Character）编辑器")
        self.resize(1080, 620)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._build_ui()
        self._load_files()
        if self.file_combo.count():
            self._switch_file(0)

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("文件:"))
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(420)
        self.file_combo.currentIndexChanged.connect(self._on_file_changed)
        top.addWidget(self.file_combo, 1)
        add_btn = QPushButton("＋ 新建角色")
        add_btn.clicked.connect(self._add_char)
        dup_btn = QPushButton("⧉ 复制")
        dup_btn.clicked.connect(self._dup_char)
        del_btn = QPushButton("🗑 删除")
        del_btn.clicked.connect(self._delete_char)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        refresh_btn = QPushButton("⟳ 刷新")
        refresh_btn.clicked.connect(self._reload)
        for b in (add_btn, dup_btn, del_btn, save_btn, refresh_btn):
            top.addWidget(b)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        split.addWidget(self.list)

        right = QWidget()
        rlay = QVBoxLayout(right)
        form = QHBoxLayout()
        form.addWidget(QLabel("ID:"))
        self.id_label = QLabel("—")
        form.addWidget(self.id_label, 1)
        form.addWidget(QLabel("名称键:"))
        self.name_loc_edit = QLineEdit()
        self.name_loc_edit.setPlaceholderText("name = \"...\" 的本地化键")
        form.addWidget(self.name_loc_edit, 1)
        rlay.addLayout(form)

        cn_row = QHBoxLayout()
        cn_row.addWidget(QLabel("中文名:"))
        self.cn_edit = QLineEdit()
        self.cn_edit.setPlaceholderText("该名称键的中文翻译")
        cn_row.addWidget(self.cn_edit, 1)
        rlay.addLayout(cn_row)

        rlay.addWidget(QLabel("肖像 portraits = { ... }（可直接编辑）"))
        self.portraits_edit = QPlainTextEdit()
        self.portraits_edit.setPlaceholderText("civilian = {\n  large = GFX_portrait_xxx\n}\n...")
        rlay.addWidget(self.portraits_edit, 1)

        self.role_info = QLabel("")
        rlay.addWidget(self.role_info)
        split.addWidget(right)
        split.setSizes([280, 800])
        root.addWidget(split, 1)

    # ---------- 数据 ----------
    def _load_files(self):
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self._files = _char_file_list(self.mod_path, self.hoi4_path)
        for fp in self._files:
            rel = os.path.relpath(fp, self.mod_path or os.path.dirname(fp))
            src = "mod" if os.path.normcase(fp).startswith(os.path.normcase(self.mod_path or "")) else "游戏"
            self.file_combo.addItem("{:5s} {}".format(src, rel), fp)
        self.file_combo.blockSignals(False)

    def _on_file_changed(self, idx):
        self._switch_file(idx)

    def _switch_file(self, idx):
        if idx < 0 or idx >= len(self._files):
            return
        fp = self._files[idx]
        self._current_file = fp
        self._reload()

    def _reload(self):
        if not self._current_file or not os.path.isfile(self._current_file):
            return
        try:
            self._header, self._metas, self._tail = load_file(self._current_file)
        except Exception as e:
            QMessageBox.warning(self, "读取失败", str(e))
            return
        self.list.blockSignals(True)
        self.list.clear()
        for m in self._metas:
            item = QListWidgetItem(m["id"])
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            self.list.addItem(item)
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(0)
            self._load_meta(0)

    def _current_meta(self):
        row = self.list.currentRow()
        if 0 <= row < len(self._metas):
            return self._metas[row]
        return None

    def _load_meta(self, row):
        m = self._metas[row]
        self.id_label.setText(m["id"])
        self.name_loc_edit.setText(m["name_loc"])
        self.portraits_edit.setPlainText(m["portraits_inner"])
        self.role_info.setText("角色内其余块：{}（不从此处编辑，保存时保留）".format(len(m["roles"])))
        # 中文名
        if m["name_loc"]:
            d = load_effective_dict(self.mod_path, self.hoi4_path, "simp_chinese")
            self.cn_edit.setText(d.get(m["name_loc"], ""))
        else:
            self.cn_edit.setText("")

    def _on_select(self, current, _prev):
        if current is None:
            return
        # 找到当前 id 对应 index
        cid = current.data(Qt.ItemDataRole.UserRole)
        for i, m in enumerate(self._metas):
            if m["id"] == cid:
                self._load_meta(i)
                return

    # ---------- 操作 ----------
    def _add_char(self):
        from PyQt6.QtWidgets import QInputDialog
        cid, ok = QInputDialog.getText(self, "新建角色", "角色 ID（建议带国家前缀，如 AAA_gen）")
        if not ok or not cid.strip():
            return
        self._metas.append({"id": cid.strip(), "name_loc": cid.strip(),
                            "portraits_inner": "", "roles": [], "others": [], "raw": ""})
        self._reload()

    def _dup_char(self):
        m = self._current_meta()
        if not m:
            QMessageBox.information(self, "提示", "请先选择角色")
            return
        from PyQt6.QtWidgets import QInputDialog
        new_id, ok = QInputDialog.getText(self, "复制角色", "新 ID", text=m["id"] + "_copy")
        if not ok or not new_id.strip():
            return
        meta = dict(m)
        meta["id"] = new_id.strip()
        self._metas.append(meta)
        self._reload()

    def _delete_char(self):
        m = self._current_meta()
        if not m:
            QMessageBox.information(self, "提示", "请先选择角色")
            return
        if QMessageBox.question(self, "确认", "删除角色 {}？".format(m["id"])) != QMessageBox.StandardButton.Yes:
            return
        self._metas = [x for x in self._metas if x["id"] != m["id"]]
        self._reload()

    def _save(self):
        if not self._metas:
            QMessageBox.information(self, "提示", "没有角色可保存")
            return
        # 写回 name / portraits 编辑内容
        row = self.list.currentRow()
        if 0 <= row < len(self._metas):
            self._metas[row]["name_loc"] = self.name_loc_edit.text().strip()
            self._metas[row]["portraits_inner"] = self.portraits_edit.toPlainText()
            # 中文名 → 本地化
            cn = self.cn_edit.text().strip()
            nkey = self._metas[row]["name_loc"]
            if nkey and cn:
                up = find_mod_file_for_key(self.mod_path, nkey, "simp_chinese")
                from localisation_editor_data import default_mod_loc_file
                target = up or default_mod_loc_file(self.mod_path, "simp_chinese")
                upsert_loc_entry(target, nkey, cn, "simp_chinese")
        try:
            n = save_file(self._current_file, self._header, self._metas, self._tail)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", "已保存 {} 个角色 → {}".format(n, os.path.basename(self._current_file)))
        self._reload()


def open_character_editor(mod_path="", hoi4_path="", parent=None):
    dlg = CharacterEditorDialog(mod_path=mod_path, hoi4_path=hoi4_path, parent=parent)
    dlg.show()
    return dlg