"""脚本库结构编辑器（B2-P17，共享编辑器）。

对 scripted_effects / scripted_triggers / script_enums / defines / names
提供统一编辑：
- 左栏 = 函数/枚举名侧栏（搜索 + 新建/复制/改名/删除）
- 右栏 = 结构视图（StructureView）：块内部文本按列表/缩进展示，
  双击改键值、右键添加条目、内联本地化
- 保存 = 只替换被编辑块的内部文本，其余文件内容原样保留，
  原版文件自动复制到 mod + 原子写。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_top_block,
    duplicate_top_block,
    insert_top_block,
    rename_top_block,
)
from ai_loader_crud import replace_block_body
from ai_ui_common import EntityListSidebar, file_tooltip
from state_build_ops import ensure_file_in_mod
from structure_view import StructureView
from write_utils import atomic_write_text


def _shared_translator():
    try:
        from gui_translator import get_translator
        return get_translator()
    except Exception:
        return None


class RawBlockEditorDialog(QDialog):
    """脚本库共享编辑器。"""

    def __init__(self, loader, list_title, window_title, mod_path="",
                 hoi4_path="", parent=None, initial_id=None):
        super().__init__(parent)
        self.loader = loader
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle(window_title)
        self.resize(1080, 680)

        self.entities = {}
        self._current_id = None

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
        self.editor = StructureView(translator=_shared_translator())
        self.editor.set_compact(True)
        self.editor.setMinimumHeight(220)
        right.addWidget(self.editor, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)
        right.addLayout(btn_row)
        root.addLayout(right, 1)

        self._reload()
        self._wire_sidebar()
        if initial_id:
            self.sidebar.set_current(initial_id)

    # ---------- 数据流 ----------

    def _reload(self, select_id=None):
        # 精确失效本编辑器对应类型的缓存（P1-5），不再全量清空 _AI_CACHE
        kind = getattr(self.loader, "__name__", "")
        if kind.startswith("load_"):
            from ai_loader import invalidate_cache
            invalidate_cache(kind=kind[len("load_"):])
        else:
            _AI_CACHE.clear()
        try:
            self.entities = dict(self.loader(self.mod_path, self.hoi4_path))
        except Exception:
            self.entities = {}
        labels = [(eid, e.get("name", eid),
                   file_tooltip(e, getattr(self, "mod_path", ""), getattr(self, "hoi4_path", "")) or e.get("name", eid))
                  for eid, e in self.entities.items()]
        self.sidebar.set_entities(labels)
        if select_id:
            self.sidebar.set_current(select_id)

    def _on_current_changed(self, entity_id):
        self._current_id = entity_id
        self.id_label.setText(entity_id or "—")
        ent = self.entities.get(entity_id)
        self.editor.load_text(ent.get("body", "") if ent else "")

    def _current_entity(self):
        return self.entities.get(self._current_id)

    def _wire_sidebar(self):
        sb = self.sidebar
        if sb.create_btn is None:
            return
        sb.createRequested.connect(self._on_create)
        sb.duplicateRequested.connect(self._on_duplicate)
        sb.renameRequested.connect(self._on_rename)
        sb.deleteRequested.connect(self._on_delete)

    # ---------- 文件读写 ----------

    def _current_rel(self):
        ent = self._current_entity()
        if ent and ent.get("rel"):
            return ent["rel"]
        for ent in self.entities.values():
            if ent.get("rel"):
                return ent["rel"]
        return ""

    def _read_mod_file(self, rel):
        if not rel:
            return None, "", False
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return None, "", False
        from write_utils import read_text_for_write, WriteContractError
        try:
            content = read_text_for_write(mod_fp)  # 严格解码（P1-3）
        except (WriteContractError, OSError) as e:
            QMessageBox.warning(self, "读取失败",
                                "文件解码失败，已取消编辑保存：%s" % e)
            return None, "", False
        return mod_fp, content, copied

    def _write_mod_file(self, mod_fp, content, msg=""):
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "写入失败", "写入失败：%s" % e)
            return False
        if msg:
            QMessageBox.information(self, "已保存", msg)
        return True

    # ---------- 保存 ----------

    def _on_save(self):
        ent = self._current_entity()
        if ent is None:
            return
        rel = ent.get("rel", "")
        if not rel:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return
        mod_fp, content, copied = self._read_mod_file(rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return
        body = self.editor.to_pdx_text().strip("\n")
        content = replace_block_body(content, ent["id"], body)
        if not self._write_mod_file(mod_fp, content):
            return
        ent["body"] = body
        msg = "已保存 %s" % ent["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)

    # ---------- 侧栏 CRUD ----------

    def _on_create(self):
        new_id, ok = QInputDialog.getText(self, "新建脚本", "新脚本名：")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        if new_id in self.entities:
            QMessageBox.warning(self, "新建失败", "名称已存在：%s" % new_id)
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            QMessageBox.warning(self, "新建失败", "无法定位目标文件")
            return
        after_id = self.sidebar.current_id() or None
        content = insert_top_block(
            content, "\n%s = {\n\t\n}\n" % new_id, after_id=after_id)
        if not self._write_mod_file(mod_fp, content, "已创建 %s" % new_id):
            return
        self._reload(select_id=new_id)

    def _on_duplicate(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "复制脚本",
                                          "新脚本名：", text=cur + "_copy")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        if new_id in self.entities:
            QMessageBox.warning(self, "复制失败", "名称已存在：%s" % new_id)
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            return
        content = duplicate_top_block(content, cur, new_id)
        if not self._write_mod_file(mod_fp, content, "已复制为 %s" % new_id):
            return
        self._reload(select_id=new_id)

    def _on_rename(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "重命名脚本",
                                          "新脚本名：", text=cur)
        if not ok or not new_id.strip() or new_id.strip() == cur:
            return
        new_id = new_id.strip()
        if new_id in self.entities:
            QMessageBox.warning(self, "重命名失败", "名称已存在：%s" % new_id)
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            return
        content = rename_top_block(content, cur, new_id)
        if not self._write_mod_file(mod_fp, content,
                                    "已重命名为 %s" % new_id):
            return
        self._reload(select_id=new_id)

    def _on_delete(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        ret = QMessageBox.question(
            self, "删除脚本", "确定删除 %s ？" % cur,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            return
        content = delete_top_block(content, cur)
        if not self._write_mod_file(mod_fp, content, "已删除 %s" % cur):
            return
        self._reload()


def make_raw_block_dialog(loader, list_title, window_title):
    """返回可被路由使用的脚本库编辑器对话框类。"""

    class _Dialog(RawBlockEditorDialog):
        def __init__(self, mod_path="", hoi4_path="", parent=None,
                     initial_id=None):
            super().__init__(loader, list_title, window_title,
                             mod_path, hoi4_path, parent, initial_id)

    return _Dialog
