"""军事学说（Doctrine）编辑器（UI/信号槽层）。

按识图与用户修正设计：
- 左栏：主要学说列表（grand doctrine）
- 顶部：学说图标选择 + 保存
- 中部：四种次要学说（track）面板，展示 陆军精通度（mastery）与
  满级额外奖励徽章（milestone）；点击面板进入该 track 的子学说编辑
- 下方：子学说（subdoctrine）列表 + 表单（新增/复制/删除/编辑 + 图标选择）
顶部「加成/花费」按要求不制作。
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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ai_ui_common import EntityListSidebar, file_tooltip
from doctrine_loader import (
    delete_subdoctrine,
    duplicate_subdoctrine,
    insert_subdoctrine,
    load_doctrine_tracks,
    load_grand_doctrines,
    load_subdoctrines,
    replace_grand_doctrine_fields,
    replace_subdoctrine_fields,
)
from state_build_ops import ensure_file_in_mod
from structure_view import StructureView
from write_utils import atomic_write_text


def _shared_translator():
    try:
        from gui_translator import get_translator
        return get_translator()
    except Exception:
        return None


def _strip_block_wrapper(raw, name):
    """剥掉 `name = { ... }` 外层，返回花括号内部文本（结构视图只展示内层）。"""
    raw = (raw or "").strip()
    if raw.startswith(name):
        start = raw.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return raw[start + 1:i]
            return raw[start + 1:]
    return raw


def _ensure_wrapped(raw, key):
    """结构视图输出的是内层文本；缺外层时补 `key = { ... }`。"""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith(key + " ="):
        return raw
    return "%s = {\n%s\n}" % (key, raw)


class _TrackCard(QWidget):
    """可点击的次要学说（track）卡片。"""

    def __init__(self, track_id, title, mastery_text, badge_text, on_click):
        super().__init__()
        self.track_id = track_id
        self._on_click = on_click
        self.setFixedWidth(210)
        self.setStyleSheet(
            "QWidget{background:#f5f8fc;border:1px solid #c9d6e3;"
            "border-radius:6px;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight:bold; color:#162333;")
        lay.addWidget(self.title)
        self.icon = QLabel("🖼")
        self.icon.setFixedSize(44, 44)
        lay.addWidget(self.icon)
        self.mastery = QLabel(mastery_text)
        self.mastery.setWordWrap(True)
        self.mastery.setStyleSheet("color:#3a6ea5; font-size:11px;")
        lay.addWidget(self.mastery)
        self.badge = QLabel(badge_text)
        self.badge.setWordWrap(True)
        self.badge.setStyleSheet(
            "color:#b8860b; border-top:1px dashed #d8c48a; font-size:11px;")
        lay.addWidget(self.badge)

    def set_icon(self, pm):
        if pm and not pm.isNull():
            self.icon.setPixmap(pm.scaledToHeight(
                40, Qt.TransformationMode.SmoothTransformation))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click(self.track_id)
        super().mousePressEvent(event)


class DoctrineEditorDialog(QDialog):
    """学说编辑器。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("学说编辑器")
        self.resize(1280, 780)

        self.grand = {}
        self.tracks = {}
        self.subdocs = {}
        self._current_id = None
        self._current_track = None
        self._current_sd = None
        self._gfx_map = self._make_gfx_map()

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("主要学说", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_doctrine_changed)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.addLayout(self._build_top_bar())

        self.tracks_row = QHBoxLayout()
        self.tracks_row.setSpacing(8)
        tracks_host = QWidget()
        tracks_host.setLayout(self.tracks_row)
        right.addWidget(tracks_host)

        split = QHBoxLayout()
        self.sd_list = QListWidget()
        self.sd_list.currentItemChanged.connect(self._on_sd_changed)
        self.sd_list.setFixedWidth(280)
        split.addWidget(self.sd_list)
        split.addWidget(self._build_sd_form(), 1)
        right.addLayout(split, 1)

        root.addLayout(right, 1)

        self._reload(initial_id)

    # ---------- 依赖 ----------

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

    def _loc(self, key):
        try:
            from localization_mgr import LocalizationManager
            mgr = LocalizationManager()
            mgr.reload(self.hoi4_path, self.mod_path)
            return mgr.get_name(key) or key
        except Exception:
            return key

    # ---------- 布局 ----------

    def _build_top_bar(self):
        bar = QHBoxLayout()
        self.title_label = QLabel("—")
        self.title_label.setStyleSheet("font-weight:bold; font-size:16px;")
        bar.addWidget(self.title_label)
        self.gd_icon = QLabel("🖼")
        self.gd_icon.setFixedSize(48, 48)
        bar.addWidget(self.gd_icon)
        self.gd_icon_btn = QPushButton("选图标")
        self.gd_icon_btn.clicked.connect(self._pick_doctrine_icon)
        bar.addWidget(self.gd_icon_btn)
        self.xp_edit = QLineEdit()
        self.xp_edit.setPlaceholderText("xp_cost")
        self.xp_edit.setFixedWidth(80)
        bar.addWidget(self.xp_edit)
        self.save_btn = QPushButton("💾 保存学说")
        self.save_btn.clicked.connect(self._on_save_doctrine)
        bar.addWidget(self.save_btn)
        bar.addStretch(1)
        return bar

    def _build_sd_form(self):
        form = QVBoxLayout()
        form.setContentsMargins(6, 6, 6, 6)
        t = QLabel("子学说编辑")
        t.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        form.addWidget(t)
        self.sd_label = QLabel("—（选择左侧子学说）")
        self.sd_label.setStyleSheet("color:#666;")
        form.addWidget(self.sd_label)

        row = QHBoxLayout()
        row.addWidget(QLabel("标题(name)"))
        self.sd_title = QLineEdit()
        row.addWidget(self.sd_title, 1)
        form.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("xp_cost"))
        self.sd_cost = QLineEdit()
        row2.addWidget(self.sd_cost)
        row2.addWidget(QLabel("图标"))
        self.sd_icon = QLineEdit()
        row2.addWidget(self.sd_icon, 1)
        self.sd_icon_btn = QPushButton("🖼")
        self.sd_icon_btn.clicked.connect(self._pick_subdoctrine_icon)
        row2.addWidget(self.sd_icon_btn)
        form.addLayout(row2)
        form.addWidget(QLabel("rewards（结构编辑）"))
        self.sd_rewards = StructureView(translator=_shared_translator())
        self.sd_rewards.set_compact(True)
        self.sd_rewards.setFixedHeight(140)
        form.addWidget(self.sd_rewards)
        form.addWidget(QLabel("available（结构编辑）"))
        self.sd_available = StructureView(translator=_shared_translator())
        self.sd_available.set_compact(True)
        self.sd_available.setFixedHeight(70)
        form.addWidget(self.sd_available)

        btns = QHBoxLayout()
        for label, fn in (("💾 保存", self._on_save_sd),
                          ("＋新增", self._on_add_sd),
                          ("⧉复制", self._on_dup_sd),
                          ("🗑删除", self._on_delete_sd)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        form.addLayout(btns)
        form.addStretch(1)
        panel = QWidget()
        panel.setLayout(form)
        return panel

    # ---------- 数据流 ----------

    def _reload(self, select_id=None):
        self.grand = load_grand_doctrines(self.mod_path, self.hoi4_path)
        self.tracks = load_doctrine_tracks(self.mod_path, self.hoi4_path)
        self.subdocs = load_subdoctrines(self.mod_path, self.hoi4_path)
        labels = [(gid, g.get("name", gid),
                   file_tooltip(g, self.mod_path, self.hoi4_path)
                   or g.get("name", gid)) for gid, g in self.grand.items()]
        self.sidebar.set_entities(labels)
        if select_id:
            self.sidebar.set_current(select_id)
        elif self.sidebar.list.count():
            self.sidebar.set_current(
                self.sidebar.list.item(0).data(Qt.ItemDataRole.UserRole))

    def _on_doctrine_changed(self, gd_id):
        self._current_id = gd_id
        g = self.grand.get(gd_id)
        self._current_track = None
        self._current_sd = None
        self.title_label.setText(gd_id or "—")
        self._clear_sd_form()
        self._rebuild_tracks(g)
        self.sd_list.clear()

    def _rebuild_tracks(self, g):
        # 清空旧卡片
        while self.tracks_row.count():
            it = self.tracks_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not g:
            return
        for tid in g.get("tracks", []) or []:
            tr = self.tracks.get(tid)
            title = self._loc((tr or {}).get("title", "")) or tid
            mastery = self._mastery_text(tr)
            badge = self._badge_text(g, tid)
            card = _TrackCard(tid, title, mastery, badge,
                              self._on_track_clicked)
            pm = self._resolve_icon((tr or {}).get("icon", ""))
            card.set_icon(pm)
            self.tracks_row.addWidget(card)

    def _mastery_text(self, tr):
        if not tr:
            return "—"
        m = tr.get("mastery") or {}
        cats = "、".join(self._loc(c) for c in m.get("categories", []))
        return "陆军精通度 ×%s\n%s" % (m.get("multiplier", "1"), cats)

    def _badge_text(self, g, track_id):
        """满级额外奖励徽章：按 track 名匹配里程碑，取最后一条。"""
        ms = [m for m in g.get("milestones", []) if track_id.lower() in m.lower()]
        if not ms:
            return "满级奖励：—"
        text = ms[-1].strip()
        text = re.sub(r"^#[^\n]*", "", text).strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "满级奖励：" + "；".join(lines[:4])

    def _on_track_clicked(self, track_id):
        self._current_track = track_id
        self._load_subdoctrines(track_id)

    def _load_subdoctrines(self, track_id):
        self.sd_list.clear()
        self._clear_sd_form()
        items = [s for s in self.subdocs.values() if s.get("track") == track_id]
        items.sort(key=lambda s: (int(s.get("xp_cost") or 0), s["id"]))
        for s in items:
            cost = s.get("xp_cost", "")
            item = QListWidgetItem("%s  [%s]" % (self._loc(s.get("title", "")) or s["id"], cost))
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            self.sd_list.addItem(item)
        if self.sd_list.count():
            self.sd_list.setCurrentRow(0)

    def _on_sd_changed(self, current, _prev):
        self._clear_sd_form()
        if current is None:
            return
        sd_id = current.data(Qt.ItemDataRole.UserRole)
        s = self.subdocs.get(sd_id)
        if not s:
            return
        self._current_sd = sd_id
        self.sd_label.setText("编辑子学说：%s" % (self._loc(s.get("title", "")) or sd_id))
        self.sd_title.setText(s.get("title", ""))
        self.sd_cost.setText(s.get("xp_cost", ""))
        self.sd_icon.setText(s.get("icon", ""))
        self.sd_rewards.load_text(
            _strip_block_wrapper(s.get("rewards", ""), "rewards").strip())
        self.sd_available.load_text(
            _strip_block_wrapper(s.get("available", ""), "available").strip())

    def _clear_sd_form(self):
        self._current_sd = None
        self.sd_title.setText("")
        self.sd_cost.setText("")
        self.sd_icon.setText("")
        self.sd_rewards.load_text("")
        self.sd_available.load_text("")
        self.sd_label.setText("—（选择左侧子学说）")

    # ---------- 图标 ----------

    def _resolve_icon(self, icon_value):
        try:
            from icon_resolver import resolve_pixmap
            return resolve_pixmap(icon_value, gfx_map=self._gfx_map,
                                  mod_path=self.mod_path,
                                  hoi4_path=self.hoi4_path)
        except Exception:
            from PyQt6.QtGui import QPixmap
            return QPixmap()

    def _pick_icon(self, current, prefix, apply):
        from icon_picker_dialog import IconPickerDialog
        dlg = IconPickerDialog(self._gfx_map, parent=self, prefix=prefix,
                               current_icon=current)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_selected_icon()
            if name:
                apply(name)

    def _pick_doctrine_icon(self):
        g = self.grand.get(self._current_id)
        if not g:
            return
        def apply(name):
            g["icon"] = name
            self.gd_icon.setPixmap(self._resolve_icon(name).scaledToHeight(
                44, Qt.TransformationMode.SmoothTransformation))
        self._pick_icon(g.get("icon", ""), "GFX_doctrine_", apply)

    def _pick_subdoctrine_icon(self):
        def apply(name):
            self.sd_icon.setText(name)
        self._pick_icon(self.sd_icon.text().strip(), "GFX_doctrine_", apply)

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
        try:
            atomic_write_text(mod_fp, transform(content))
        except Exception as e:
            QMessageBox.warning(self, "写入失败", "写入失败：%s" % e)
            return False
        return True

    # ---------- 保存 ----------

    def _on_save_doctrine(self):
        g = self.grand.get(self._current_id)
        if not g:
            return
        fields = {"xp_cost": self.xp_edit.text().strip()}
        if g.get("icon"):
            fields["icon"] = g["icon"]
        def transform(content):
            return replace_grand_doctrine_fields(content, g["id"], fields)
        if self._write_rel(g.get("rel", ""), transform):
            g["xp_cost"] = fields.get("xp_cost", g.get("xp_cost", ""))
            QMessageBox.information(self, "已保存", "已保存学说 %s" % g["id"])

    def _on_save_sd(self):
        s = self.subdocs.get(self._current_sd)
        if not s:
            return
        from doctrine_loader import replace_subdoctrine_child
        fields = {"name": self.sd_title.text().strip() or s["id"],
                  "xp_cost": self.sd_cost.text().strip(),
                  "icon": self.sd_icon.text().strip()}
        fields = {k: v for k, v in fields.items() if v}
        rewards = _ensure_wrapped(self.sd_rewards.to_pdx_text(), "rewards")
        available = _ensure_wrapped(self.sd_available.to_pdx_text(), "available")
        def transform(content):
            content = replace_subdoctrine_fields(content, s["id"], fields)
            if rewards:
                content = replace_subdoctrine_child(
                    content, s["id"], "rewards", rewards)
            if available:
                content = replace_subdoctrine_child(
                    content, s["id"], "available", available)
            return content
        if self._write_rel(s.get("rel", ""), transform):
            s["xp_cost"] = fields.get("xp_cost", s.get("xp_cost", ""))
            QMessageBox.information(self, "已保存", "已保存子学说 %s" % s["id"])

    def _on_add_sd(self):
        if not self._current_track:
            QMessageBox.information(self, "提示", "请先点击选择一个次要学说面板")
            return
        sd_id, ok = QInputDialog.getText(self, "新增子学说", "新子学说 id：")
        if not ok or not sd_id.strip():
            return
        sd_id = sd_id.strip()
        after = self._current_sd or None
        def transform(content):
            return insert_subdoctrine(content, sd_id, self._current_track,
                                      after_id=after)
        if self._write_rel(self._sd_rel(), transform):
            self._reload(self._current_id)
            self._on_track_clicked(self._current_track)
            # 选中新项
            for i in range(self.sd_list.count()):
                if self.sd_list.item(i).data(Qt.ItemDataRole.UserRole) == sd_id:
                    self.sd_list.setCurrentRow(i)
                    break

    def _on_dup_sd(self):
        if not self._current_sd:
            return
        new_id, ok = QInputDialog.getText(self, "复制子学说", "新 id：",
                                          text=self._current_sd + "_copy")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        def transform(content):
            return duplicate_subdoctrine(content, self._current_sd, new_id)
        if self._write_rel(self._sd_rel(), transform):
            self._reload(self._current_id)
            self._on_track_clicked(self._current_track)

    def _on_delete_sd(self):
        if not self._current_sd:
            return
        ret = QMessageBox.question(
            self, "删除子学说", "确定删除 %s ？" % self._current_sd,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        def transform(content):
            return delete_subdoctrine(content, self._current_sd)
        if self._write_rel(self._sd_rel(), transform):
            self._reload(self._current_id)
            self._on_track_clicked(self._current_track)

    def _sd_rel(self):
        s = self.subdocs.get(self._current_sd)
        if s and s.get("rel"):
            return s["rel"]
        for s in self.subdocs.values():
            if s.get("rel"):
                return s["rel"]
        return ""


def open_doctrine_editor(file_path="", mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """入口：加载并显示学说编辑器（非模态）。"""
    dlg = DoctrineEditorDialog(mod_path, hoi4_path, parent=parent,
                               initial_id=entity_id)
    dlg.show()
    return dlg
