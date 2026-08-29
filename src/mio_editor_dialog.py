"""MIO 编辑器（主对话框，UI/信号槽层）。

按游戏内 MIO 界面：
- 左栏：MIO 组织列表
- 顶部：MIO 图标选择 + 保存
- 左侧面板：属性 / 装备加成展示（取自 initial_trait）
- 中部：特质树画布（点击选特质）
- 右侧：特质实体 新增/删除/编辑（含图标选择）
- 底部：方针编辑器入口
"""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_ui_common import EntityListSidebar
from mio_loader import (
    delete_trait,
    duplicate_trait,
    insert_trait,
    load_mios,
    rename_trait,
    replace_mio_fields,
    replace_trait_block,
    trait_to_pdx,
)
from mio_trait_tree import MioTraitTreeView
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text


class MioEditorDialog(QDialog):
    """MIO 编辑器。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("MIO 编辑器")
        self.resize(1280, 780)

        self.mios = {}
        self._current_id = None
        self._trait_token = None
        self._orig_parents_text = ""
        self._trait_parent_blocks = {}
        self._trait_extra_blocks = []
        self._loc = self._make_loc()
        self._gfx_map = self._make_gfx_map()

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("MIO 组织", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_mio_changed)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.addLayout(self._build_top_bar())
        split = QHBoxLayout()
        split.addWidget(self._build_info_panel())
        self.tree = MioTraitTreeView(
            name_of=self._loc, gfx_map=self._gfx_map,
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        self.tree.trait_selected.connect(self._on_trait_selected)
        split.addWidget(self.tree, 1)
        split.addWidget(self._build_trait_form())
        right.addLayout(split, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.policy_btn = QPushButton("🎯 方针编辑器…")
        self.policy_btn.clicked.connect(self._open_policies)
        bottom.addWidget(self.policy_btn)
        right.addLayout(bottom)
        root.addLayout(right, 1)

        self._reload(initial_id)

    # ---------- 依赖 ----------

    def _make_loc(self):
        def name_of(key):
            try:
                from localization_mgr import LocalizationManager
                mgr = LocalizationManager()
                mgr.reload(self.hoi4_path, self.mod_path)
                return mgr.get_name(key) or key
            except Exception:
                return key
        return name_of

    def _make_gfx_map(self):
        gfx = {}
        try:
            from gui_translator import get_translator, scan_gfx_folder
            gfx = dict(get_translator().gfx_map)
            if self.mod_path:
                scan_gfx_folder(self.mod_path, gfx)
        except Exception:
            pass
        return gfx

    # ---------- 布局 ----------

    def _build_top_bar(self):
        bar = QHBoxLayout()
        self.title_label = QLabel("—")
        self.title_label.setStyleSheet("font-weight:bold; font-size:16px;")
        bar.addWidget(self.title_label)
        bar.addStretch(1)
        self.mio_icon_label = QLabel("🖼")
        self.mio_icon_label.setFixedSize(48, 48)
        bar.addWidget(self.mio_icon_label)
        self.mio_icon_btn = QPushButton("选择 MIO 图标")
        self.mio_icon_btn.clicked.connect(self._pick_mio_icon)
        bar.addWidget(self.mio_icon_btn)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._on_save_mio)
        bar.addWidget(self.save_btn)
        return bar

    def _build_info_panel(self):
        host = QVBoxLayout()
        host.setContentsMargins(6, 6, 6, 6)
        title = QLabel("属性与装备加成")
        title.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        host.addWidget(title)
        self.info_label = QLabel("—")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setStyleSheet("color:#162333;")
        host.addWidget(self.info_label, 1)
        panel = QWidget()
        panel.setFixedWidth(300)
        panel.setLayout(host)
        return panel

    def _build_trait_form(self):
        form = QVBoxLayout()
        form.setContentsMargins(6, 6, 6, 6)
        title = QLabel("特质编辑")
        title.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        form.addWidget(title)
        self.trait_label = QLabel("—（点击左侧树节点选择）")
        self.trait_label.setStyleSheet("color:#666;")
        form.addWidget(self.trait_label)

        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("token")
        form.addWidget(self._field_row("token", self.token_edit))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("name（本地化键）")
        form.addWidget(self._field_row("名称", self.name_edit))
        self.icon_row = self._field_row("图标", QLineEdit())
        self.icon_edit = self.icon_row._inner_widget
        self.icon_btn = QPushButton("🖼 选图标")
        self.icon_btn.clicked.connect(self._pick_trait_icon)
        self.icon_row._inner_layout.addWidget(self.icon_btn)
        form.addWidget(self.icon_row)
        self.x_edit = QLineEdit()
        self.x_edit.setPlaceholderText("x")
        self.y_edit = QLineEdit()
        self.y_edit.setPlaceholderText("y")
        xy = QHBoxLayout()
        xy.addWidget(QLabel("位置 x"))
        xy.addWidget(self.x_edit)
        xy.addWidget(QLabel("y"))
        xy.addWidget(self.y_edit)
        form.addLayout(xy)
        self.rel_edit = QLineEdit()
        self.rel_edit.setPlaceholderText("父特质 token")
        form.addWidget(self._field_row("相对父", self.rel_edit))
        self.parents_edit = QLineEdit()
        self.parents_edit.setPlaceholderText("空格分隔的父特质列表")
        form.addWidget(self._field_row("父列表", self.parents_edit))
        self.equip_edit = QPlainTextEdit()
        self.equip_edit.setPlaceholderText("equipment_bonus 原始块（含外层）")
        self.equip_edit.setFixedHeight(90)
        form.addWidget(self._field_row("装备加成", self.equip_edit))
        self.prod_edit = QPlainTextEdit()
        self.prod_edit.setPlaceholderText("production_bonus 原始块（含外层）")
        self.prod_edit.setFixedHeight(80)
        form.addWidget(self._field_row("生产加成", self.prod_edit))

        btns = QHBoxLayout()
        for label, fn in (("💾 存特质", self._on_save_trait),
                          ("＋新增", self._on_add_trait),
                          ("⧉复制", self._on_dup_trait),
                          ("🗑删除", self._on_delete_trait)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        form.addLayout(btns)
        form.addStretch(1)
        panel = QWidget()
        panel.setFixedWidth(420)
        panel.setLayout(form)
        return panel

    def _field_row(self, label, widget):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lab = QLabel(label)
        lab.setStyleSheet("color:#162333; font-weight:bold;")
        lay.addWidget(lab)
        lay.addWidget(widget)
        container._inner_widget = widget
        container._inner_layout = lay
        return container

    # ---------- 数据流 ----------

    def _reload(self, select_id=None):
        self.mios = load_mios(self.mod_path, self.hoi4_path)
        labels = [(mid, m.get("name", mid)) for mid, m in self.mios.items()]
        self.sidebar.set_entities(labels)
        if select_id:
            self.sidebar.set_current(select_id)
        elif self.sidebar.list.count():
            self.sidebar.set_current(
                self.sidebar.list.item(0).data(Qt.ItemDataRole.UserRole))

    def _current_mio(self):
        return self.mios.get(self._current_id)

    def _on_mio_changed(self, mio_id):
        self._current_id = mio_id
        mio = self.mios.get(mio_id)
        self.title_label.setText(mio_id or "—")
        self._trait_token = None
        self._clear_trait_form()
        if not mio:
            self.tree.set_mio(None)
            self.info_label.setText("—")
            self.mio_icon_label.setText("🖼")
            return
        self.tree.set_mio(mio)
        self._refresh_info(mio)
        self._refresh_mio_icon(mio)

    def _refresh_info(self, mio):
        init = mio.get("initial_trait") or {}
        lines = []
        if init.get("name"):
            lines.append("初始特质：%s" % self._loc(init["name"]))
        for label, raw in (("装备加成", init.get("equipment_bonus") or ""),
                           ("生产加成", init.get("production_bonus") or "")):
            if not raw:
                continue
            lines.append("· %s：" % label)
            for k, v in _extract_kv(raw):
                lines.append("    %s = %s" % (k, v))
        self.info_label.setText("\n".join(lines) or "（无 initial_trait 加成）")

    def _refresh_mio_icon(self, mio):
        icon = (mio or {}).get("icon", "")
        self.mio_icon_label.setToolTip(icon)
        try:
            from icon_resolver import resolve_pixmap
            pm = resolve_pixmap(icon, gfx_map=self._gfx_map,
                                mod_path=self.mod_path,
                                hoi4_path=self.hoi4_path)
            if not pm.isNull():
                pm = pm.scaledToHeight(44, Qt.TransformationMode.SmoothTransformation)
                self.mio_icon_label.setPixmap(pm)
                return
        except Exception:
            pass
        self.mio_icon_label.setText("🖼")

    # ---------- 特质表单 ----------

    def _clear_trait_form(self):
        for w in (self.token_edit, self.name_edit, self.icon_edit,
                  self.x_edit, self.y_edit, self.rel_edit, self.parents_edit):
            w.setText("")
        self.equip_edit.setPlainText("")
        self.prod_edit.setPlainText("")
        self.trait_label.setText("—（点击左侧树节点选择）")
        self._orig_parents_text = ""
        self._trait_parent_blocks = {}
        self._trait_extra_blocks = []

    def _on_trait_selected(self, token):
        mio = self._current_mio()
        if not mio:
            return
        for t in mio.get("traits", []) or []:
            if t.get("token") == token:
                self._trait_token = token
                self.trait_label.setText("编辑特质：%s" % self._loc(token))
                self.token_edit.setText(t.get("token", ""))
                self.name_edit.setText(t.get("name", ""))
                self.icon_edit.setText(t.get("icon", ""))
                self.x_edit.setText(str(t.get("x", 0)))
                self.y_edit.setText(str(t.get("y", 0)))
                self.rel_edit.setText(t.get("relative_position_id", ""))
                self.parents_edit.setText(" ".join(t.get("parents") or []))
                self.equip_edit.setPlainText(t.get("equipment_bonus", ""))
                self.prod_edit.setPlainText(t.get("production_bonus", ""))
                self._orig_parents_text = " ".join(t.get("parents") or [])
                self._trait_parent_blocks = dict(t.get("parent_blocks") or {})
                self._trait_extra_blocks = list(t.get("extra_blocks") or [])
                break

    def _form_trait(self, token):
        try:
            x = int(self.x_edit.text() or "0")
        except ValueError:
            x = 0
        try:
            y = int(self.y_edit.text() or "0")
        except ValueError:
            y = 0
        current_parents = [p for p in self.parents_edit.text().split() if p]
        current_parents_text = " ".join(current_parents)
        extra_blocks = list(self._trait_extra_blocks or [])
        parents = current_parents
        if current_parents_text == (self._orig_parents_text or ""):
            # 父列表未修改：保留原始 any_parent/all_parents 块，避免类型被改写
            for blocks in (self._trait_parent_blocks or {}).values():
                extra_blocks.extend(blocks)
            parents = []
        return trait_to_pdx(
            token,
            self.name_edit.text().strip() or token,
            self.icon_edit.text().strip(),
            x, y,
            self.rel_edit.text().strip(),
            parents,
            self.equip_edit.toPlainText().strip(),
            self.prod_edit.toPlainText().strip(),
            extra_blocks=extra_blocks,
        )

    # ---------- 写文件 ----------

    def _write_rel(self, rel, transform):
        if not rel:
            return False
        mod_fp, _copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return False
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        new_content = transform(content)
        try:
            atomic_write_text(mod_fp, new_content)
        except Exception as e:
            QMessageBox.warning(self, "写入失败", "写入失败：%s" % e)
            return False
        return True

    # ---------- 保存 / CRUD ----------

    def _on_save_mio(self):
        mio = self._current_mio()
        if not mio:
            return
        icon = self.mio_icon_label.toolTip() or mio.get("icon", "")
        def transform(content):
            return replace_mio_fields(content, mio["id"], {"icon": icon})
        if self._write_rel(mio.get("rel", ""), transform):
            mio["icon"] = icon
            QMessageBox.information(self, "已保存", "已保存 %s" % mio["id"])

    def _on_save_trait(self):
        mio = self._current_mio()
        if not mio or not self._trait_token:
            return
        old_token = self._trait_token
        new_token = self.token_edit.text().strip() or old_token
        existing = {t.get("token") for t in mio.get("traits", []) or []}
        if new_token != old_token and new_token in existing:
            QMessageBox.warning(self, "保存失败", "特质 token 已存在：%s" % new_token)
            return
        new_pdx = self._form_trait(new_token)
        def transform(content):
            if new_token != old_token:
                content = rename_trait(content, mio["id"], old_token, new_token)
            return replace_trait_block(content, mio["id"], new_token, new_pdx)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)
            self._on_trait_selected(new_token)
            QMessageBox.information(self, "已保存", "已保存特质 %s" % new_token)

    def _on_add_trait(self):
        mio = self._current_mio()
        if not mio:
            return
        token, ok = QInputDialog.getText(self, "新增特质", "新特质 token：")
        if not ok or not token.strip():
            return
        token = token.strip()
        if token in {t.get("token") for t in mio.get("traits", []) or []}:
            QMessageBox.warning(self, "新增失败", "特质 token 已存在：%s" % token)
            return
        after = self._trait_token or None
        def transform(content):
            return insert_trait(content, mio["id"], token, after_token=after)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)
            self._on_trait_selected(token)

    def _on_dup_trait(self):
        mio = self._current_mio()
        if not mio or not self._trait_token:
            return
        new_token, ok = QInputDialog.getText(
            self, "复制特质", "新特质 token：", text=self._trait_token + "_copy")
        if not ok or not new_token.strip():
            return
        new_token = new_token.strip()
        if new_token in {t.get("token") for t in mio.get("traits", []) or []}:
            QMessageBox.warning(self, "复制失败", "特质 token 已存在：%s" % new_token)
            return
        def transform(content):
            return duplicate_trait(content, mio["id"], self._trait_token, new_token)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)
            self._on_trait_selected(new_token)

    def _on_delete_trait(self):
        mio = self._current_mio()
        if not mio or not self._trait_token:
            return
        token = self._trait_token
        ret = QMessageBox.question(
            self, "删除特质", "确定删除特质 %s ？" % token,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        def transform(content):
            return delete_trait(content, mio["id"], token)
        if self._write_rel(mio.get("rel", ""), transform):
            self._reload(self._current_id)

    # ---------- 图标选择 ----------

    def _pick_icon(self, current, prefix, target_widget):
        from icon_picker_dialog import IconPickerDialog
        dlg = IconPickerDialog(
            self._gfx_map, parent=self, prefix=prefix,
            current_icon=current)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_selected_icon()
            if name:
                target_widget.setText(name)

    def _pick_mio_icon(self):
        mio = self._current_mio()
        if not mio:
            return
        self._pick_icon(mio.get("icon", ""), "GFX_", self.mio_icon_label)
        if self.mio_icon_label.text():
            mio["icon"] = self.mio_icon_label.text()
        self.mio_icon_label.setToolTip(mio.get("icon", ""))
        self._refresh_mio_icon(mio)

    def _pick_trait_icon(self):
        self._pick_icon(self.icon_edit.text().strip(), "GFX_", self.icon_edit)

    # ---------- 方针入口 ----------

    def _open_policies(self):
        from mio_policy_editor_dialog import MioPolicyEditorDialog
        dlg = MioPolicyEditorDialog(self.mod_path, self.hoi4_path,
                                    parent=self)
        dlg.show()


def _extract_kv(raw):
    """从原始加成块提取 key = value 行（浅层）。"""
    out = []
    for line in raw.splitlines():
        m = re.match(r"^\s*([\w\.\-]+)\s*=\s*([^\s#]+)", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def open_mio_editor(file_path="", mod_path="", hoi4_path="",
                    entity_id=None, parent=None):
    """入口：加载并显示 MIO 编辑器（非模态）。"""
    dlg = MioEditorDialog(mod_path, hoi4_path, parent=parent,
                          initial_id=entity_id)
    dlg.show()
    return dlg
