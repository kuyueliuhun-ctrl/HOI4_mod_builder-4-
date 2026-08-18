from project_paths import PROJECT_ROOT
import os
import re
import json
from PyQt6.QtWidgets import QGraphicsView, QMenu, QDialog, QInputDialog, QMessageBox, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsSimpleTextItem, QGraphicsRectItem, QGraphicsPathItem, QFileDialog
from PyQt6.QtGui import QPainter, QAction, QFont, QColor, QPixmap, QBrush, QPen, QKeySequence, QShortcut, QPainterPath
from PyQt6.QtCore import Qt, QPoint
from focus_parser import parse_focus_file
from gui_translator import GuiTranslator
from focus_base_builder import FocusTreeEditor
from localization_mgr import get_localization_manager
from focus_view_ctrl import EntityGalleryControllerMixin, TechTreeControllerMixin
import icon_ops


CUSTOM_STATEMENT_PATH = os.path.join(PROJECT_ROOT, "custom_statements.json")

_translator = None
_loc_manager = None


def _get_settings():
    """读取最新的 settings.json 配置。

    不缓存，确保打开/切换 mod 后能读到最新的 mod_path / HOI4_path，
    使树形编辑器能正确加载 mod 文件夹中的翻译文件。
    """
    settings = {}
    settings_path = os.path.join(PROJECT_ROOT, "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            pass
    return settings


def _get_translator():
    global _translator
    if _translator is None:
        hoi4_path = ""
        loc_path = ""
        settings = _get_settings()
        hoi4_path = settings.get("HOI4_path", "")
        if hoi4_path:
            loc_path = os.path.join(hoi4_path, "localisation", "simp_chinese")
        _translator = GuiTranslator(loc_path, CUSTOM_STATEMENT_PATH, hoi4_path,
                                    settings.get("mod_path", ""))
    return _translator


def _get_loc_manager():
    global _loc_manager
    if _loc_manager is None:
        _loc_manager = get_localization_manager()
        settings = _get_settings()
        hoi4_path = settings.get("HOI4_path", "")
        mod_path = settings.get("mod_path", "")
        if hoi4_path:
            _loc_manager.add_game_path(hoi4_path)
        if mod_path:
            _loc_manager.add_mod_path(mod_path)
    return _loc_manager


def _get_hoi4_path():
    return _get_settings().get("HOI4_path", "")


def _get_mod_path():
    return _get_settings().get("mod_path", "")


def reload_translator():
    global _translator, _loc_manager
    _translator = None
    _loc_manager = None
    _get_translator()
    return _get_loc_manager()


class FocusView(QGraphicsView, TechTreeControllerMixin, EntityGalleryControllerMixin):
    """国策树图形视图：处理缩放、拖拽、双击编辑和右键菜单操作

    同时支持「实体画廊」模式（show_entity_gallery）：在右侧国策组件中
    展示图标型内容（决议/事件/理念/角色等）的各实体图标与名称。
    """

    GRID_X = 90
    GRID_Y = 130
    DRAG_THRESHOLD = 6

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._current_file_path = None
        self._pending_move_focus = None        # 待移动的国策 ID（点击确定新位置）
        self._pending_parent_scene_pos = None  # 待选择母国策时，新国策的目标位置
        self._pending_icon_focus = None        # 待上传图标的国策 ID
        self._press_focus_info = None          # 按下国策时的拖动候选 (fid, 视图起点, node_item, text_item, 宽, 高)
        self._drag_focus_id = None             # 正在拖动的国策 ID

        # 实体画廊模式状态
        self._view_mode = "focus"              # "focus" 国策设计 / "entities" 实体画廊
        self._entity_type = ""                 # 当前画廊的内容类型
        self._entity_cfg = None                # 当前画廊的 ICON_RULES 配置
        self._entity_items = {}                # 实体名 -> (图标项, 文本项, x, y)
        self._pending_entity_icon = None       # 待上传图标的实体字典
        self._pending_entity_icon_slot = None  # 待上传图标的目标槽位（large/small/None）
        self._gallery_font_obj = None
        self._entity_find_dialog = None        # Ctrl+F 查找对话框（懒创建）
        self._entity_highlight = None          # 定位高亮边框项

        # 无文件模式画廊状态（跨文件实体；None 表示文件模式画廊）
        self._nofile_entity_list = None
        self._nofile_files = []                # 无文件画廊的源文件列表
        # 无文件模式「当前国家」提示：新建/移动实体时优先选择该国文件（None=不偏好）
        self._country_hint = None

        # 无文件模式国策树状态（跨文件合并绘制）
        self._nofile_focus_data = None         # 合并后的 focus_data（dict）
        self._nofile_focus_files = {}          # focus_id -> 所在文件路径
        self._nofile_focus_title_item = None   # 场景标题（正在设计的国家）
        self._nofile_focus_country = ""        # 当前设计国家（""=全部）

        # Ctrl+F：实体画廊中按英文 id / 中文名查找并定位实体
        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self._open_entity_find_dialog)
        self.find_shortcut.setEnabled(False)

        # Ctrl+Z：撤销最近一次文件写入（焦点在画布时生效，编辑框内不受影响）
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self.undo_shortcut.activated.connect(self._undo_last_write)

        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def _scene_to_grid(self, scene_pos):
        """将场景坐标转换为国策网格坐标（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.scene_to_grid(scene_pos, self.GRID_X, self.GRID_Y)
    def _grid_to_scene(self, gx, gy):
        """国策网格坐标转场景坐标（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.grid_to_scene(gx, gy, self.GRID_X, self.GRID_Y)
    def _snap_to_grid_center(self, scene_pos):
        """吸附到最近单元格中心（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.snap_to_grid_center(scene_pos, self.GRID_X, self.GRID_Y)
    def _get_focus_grid_pos(self, focus_id):
        """从场景中的图标项反算国策的网格坐标 (x, y)，未找到返回 None。"""
        for item in self.scene().items():
            if item.data(0) == focus_id and isinstance(item, (QGraphicsPixmapItem, QGraphicsEllipseItem)):
                center = item.sceneBoundingRect().center()
                return round(center.x() / 90 - 0.5), round(center.y() / 130 - 0.5)
        return None

    def _cancel_pending_modes(self):
        """取消移动/选择母国策/上传图标/拖动等临时模式，恢复光标。"""
        self._pending_move_focus = None
        self._pending_parent_scene_pos = None
        self._pending_icon_focus = None
        self._pending_entity_icon = None
        self._pending_entity_icon_slot = None
        self._drag_focus_id = None
        self._press_focus_info = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        """处理移动国策 / 选择母国策的临时模式单击，以及国策拖拽的开始。"""
        if self._view_mode != "focus":
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._pending_move_focus is not None:
                fid = self._pending_move_focus
                scene_pos = self.mapToScene(event.pos())
                self._cancel_pending_modes()
                x, y = self._scene_to_grid(scene_pos)
                self._move_focus(fid, x, y)
                event.accept()
                return
            if self._pending_parent_scene_pos is not None:
                item = self.itemAt(event.pos())
                if item and item.data(0) and item.data(1):
                    parent_id = item.data(0)
                    scene_pos = self._pending_parent_scene_pos
                    self._cancel_pending_modes()
                    self._create_focus_with_parent(parent_id, scene_pos)
                event.accept()
                return
            # 拖拽移动国策：按下国策图标/文本时记录候选，阻止 ScrollHandDrag 抢占
            item = self.itemAt(event.pos())
            if item is not None and item.data(0) and item.data(1):
                fid = item.data(0)
                node_item = None
                text_item = None
                for it in self.scene().items():
                    if it.data(0) == fid and it.data(1):
                        if (isinstance(it, (QGraphicsPixmapItem, QGraphicsEllipseItem))
                                and node_item is None):
                            node_item = it
                        elif isinstance(it, QGraphicsSimpleTextItem) and text_item is None:
                            text_item = it
                if node_item is not None:
                    sr = node_item.sceneBoundingRect()
                    self._press_focus_info = (fid, event.pos(), node_item, text_item,
                                              sr.width(), sr.height())
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖动国策：超过阈值后进入拖动，吸附到网格跟随鼠标移动。"""
        if self._press_focus_info is not None:
            fid, start_pos, node_item, text_item, w, h = self._press_focus_info
            if self._drag_focus_id is None:
                if (event.pos() - start_pos).manhattanLength() >= self.DRAG_THRESHOLD:
                    self._drag_focus_id = fid
            if self._drag_focus_id == fid:
                self._snap_drag_items(event, node_item, text_item, w, h)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """结束国策拖动：写入新坐标并重绘；纯点击则仅清理。"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_focus_id is not None:
                fid = self._drag_focus_id
                scene_pos = self.mapToScene(event.pos())
                _, (gx, gy) = self._snap_to_grid_center(scene_pos)
                self._drag_focus_id = None
                self._press_focus_info = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self._move_focus(fid, gx, gy)
                event.accept()
                return
            if self._press_focus_info is not None:
                # 纯点击（未拖动）：清理候选，不做移动
                self._press_focus_info = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def _snap_drag_items(self, event, node_item, text_item, w, h):
        """拖动时把国策图标与文字吸附到鼠标所在格子中心。"""
        scene_pos = self.mapToScene(event.pos())
        center, _ = self._snap_to_grid_center(scene_pos)
        node_item.setPos(center[0] - w / 2, center[1] - h / 2)
        if text_item is not None:
            tw = text_item.boundingRect().width()
            text_item.setPos(center[0] - tw / 2, center[1] + h / 2 + 5)

    def keyPressEvent(self, event):
        """按 ESC 取消移动/拖拽/选择母国策/上传图标的临时模式。"""
        if event.key() == Qt.Key.Key_Escape:
            if self._drag_focus_id is not None or self._press_focus_info is not None:
                self._drag_focus_id = None
                self._press_focus_info = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.redraw()  # 还原被拖动移动的图标位置
                event.accept()
                return
            if (self._pending_move_focus is not None or self._pending_parent_scene_pos is not None
                    or self._pending_icon_focus is not None or self._pending_entity_icon is not None):
                self._cancel_pending_modes()
                event.accept()
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

    def redraw(self):
        if self._view_mode == "entities":
            if self._nofile_entity_list is not None:
                self._reload_nofile_gallery()
            elif self._current_file_path:
                self.show_entity_gallery(self._entity_type, self._current_file_path)
            return
        if self._view_mode == "focus" and self._nofile_focus_data is not None:
            # 无文件模式国策树：跨文件合并重绘
            self._redraw_nofile_focus_tree()
            return
        if not self._current_file_path:
            return
        window = self.window()
        if window and hasattr(window, 'load_txt_pdx_to_memory'):
            window.load_txt_pdx_to_memory(self._current_file_path)

    def _on_editor_translation_saved(self, focus_id):
        """树编辑器翻译保存后：刷新本地化缓存并定向重绘该国策节点。

        直接使用翻译编辑器（目标文件优先级）中的最新名称更新节点文本，
        避免因同目录其他翻译文件覆盖导致显示旧值；无需重新解析整个国策文件。
        """
        try:
            from translation_editor import get_translation_editor
            from localization_mgr import get_localization_manager
            # 从翻译编辑器取最新名称（其缓存以目标文件为最高优先级）
            te = get_translation_editor()
            name = te.get_name(focus_id) or focus_id
            lm = get_localization_manager()
            lm.reload(game_path=_get_hoi4_path(), mod_path=_get_mod_path())
            window = self.window()
            if window is not None and hasattr(window, "renderer") and window.renderer is not None:
                window.renderer.set_loc_manager(lm)
                window.renderer.update_focus_text(focus_id, name)
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        if self._view_mode == "entities":
            if event.button() == Qt.MouseButton.LeftButton:
                item = self.itemAt(event.pos())
                if item is not None and item.data(2):
                    file_path = item.data(1)
                    entity = item.data(2)
                    self._open_entity_tree_editor(file_path, entity)
                    event.accept()
                    return
            event.ignore()
            return
        if self._view_mode == "tech":
            # 双击科技节点 → 打开定义文件树编辑器并定位
            if event.button() == Qt.MouseButton.LeftButton:
                item = self.itemAt(event.pos())
                if item is not None and item.data(0):
                    tech_id = item.data(0)
                    file_path = item.data(1) or self._tech_file_for(tech_id)
                    self._open_tech_in_editor(file_path, tech_id)
                    event.accept()
                    return
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())

            if item and item.data(0):
                focus_id = item.data(0)
                file_path = item.data(1)
                if not file_path:
                    event.ignore()
                    return

                try:
                    result = parse_focus_file(file_path, focus_id)
                    focus_load, file_lines, block_range, x_val, y_val, raw_fields = result
                except ValueError as e:
                    event.ignore()
                    return

                translator = _get_translator()
                loc_manager = _get_loc_manager()
                self.current_editor = FocusTreeEditor(
                    focus_load=focus_load,
                    file_path=file_path,
                    file_lines=file_lines,
                    block_range=block_range,
                    x_val=x_val,
                    y_val=y_val,
                    translator=translator,
                    custom_statement_path=CUSTOM_STATEMENT_PATH,
                    raw_fields=raw_fields,
                    loc_manager=loc_manager,
                    parent=self,
                    hoi4_path=_get_hoi4_path(),
                    mod_path=_get_mod_path(),
                )
                self.current_editor.tree_saved.connect(self.redraw)
                self.current_editor.translation_saved.connect(self._on_editor_translation_saved)
                self.current_editor.show()

                event.accept()
                return

        event.ignore()

    def _undo_last_write(self):
        """撤销最近一次文件写入（画布 Ctrl+Z），恢复后刷新当前视图。"""
        from undo_mgr import undo, can_undo
        if not can_undo():
            QMessageBox.information(self, "撤销", "没有可撤销的写入操作")
            return
        path, ok = undo()
        if not ok:
            QMessageBox.warning(self, "撤销", f"撤销失败: {path}")
            return
        # 刷新当前视图：无文件模式国策树重扫文件；其余走 redraw（画廊/文件模式会重读）
        if self._view_mode == "focus" and self._nofile_focus_data is not None:
            self.show_focus_tree_nofile(
                self._nofile_focus_country, list(self._nofile_focus_files.values()))
        else:
            self.redraw()
        window = self.window()
        if window is not None:
            try:
                window._refresh_tree()
            except Exception:
                pass
            wb = getattr(window, "workbench_dock", None)
            if wb is not None:
                try:
                    wb._refresh()
                except Exception:
                    pass
        QMessageBox.information(
            self, "撤销", f"已恢复文件到上次写入前:\n{os.path.basename(path)}")

    def _get_current_file_path(self):
        if self._current_file_path:
            return self._current_file_path
        if self._view_mode == "focus" and self._nofile_focus_files:
            # 无文件模式国策树：返回首个文件（新建国策等操作的默认落点）
            return next(iter(self._nofile_focus_files.values()), None)
        for item in self.scene().items():
            if item.data(1):
                self._current_file_path = item.data(1)
                return item.data(1)
        return None

    def contextMenuEvent(self, event):
        if self._view_mode == "entities":
            self._show_entity_context_menu(event)
            return
        if self._view_mode == "tech":
            self._show_tech_context_menu(event)
            return
        item = self.itemAt(event.pos())
        self._cancel_pending_modes()
        menu = QMenu(self)

        if item and item.data(0):
            focus_id = item.data(0)
            cn_name = ""
            loc = _get_loc_manager()
            if loc:
                cn_name = loc.get_name(focus_id)
            label = f"{focus_id} ({cn_name})" if cn_name else focus_id

            edit_action = QAction(f"编辑国策: {label}", self)
            edit_action.triggered.connect(lambda: self._open_focus_editor(focus_id))
            menu.addAction(edit_action)

            parent_action = QAction("以该国策为母国策新建国策", self)
            parent_action.triggered.connect(lambda: self._create_child_focus(focus_id))
            menu.addAction(parent_action)

            select_icon_action = QAction("选择图标", self)
            select_icon_action.triggered.connect(lambda: self._pick_focus_icon(focus_id))
            menu.addAction(select_icon_action)

            upload_icon_action = QAction("上传图标（新建对话框）", self)
            upload_icon_action.triggered.connect(lambda: self._upload_icon_dialog(focus_id))
            menu.addAction(upload_icon_action)

            upload_drag_action = QAction("上传图标（拖拽）", self)
            upload_drag_action.triggered.connect(lambda: self._begin_icon_upload(focus_id))
            menu.addAction(upload_drag_action)

            move_action = QAction("移动国策（拖拽到目标位置）", self)
            move_action.triggered.connect(lambda: self._begin_move_focus(focus_id))
            menu.addAction(move_action)

            delete_action = QAction(f"删除国策", self)
            delete_action.triggered.connect(lambda: self._delete_focus(focus_id))
            menu.addAction(delete_action)
        else:
            scene_pos = self.mapToScene(event.pos())

            add_action = QAction("在此处新建国策", self)
            add_action.triggered.connect(lambda: self._create_new_focus(scene_pos))
            menu.addAction(add_action)

            project_action = QAction("🧩 新建国策项目（联动生成事件/决议/图标/本地化）…", self)
            project_action.triggered.connect(self._create_focus_project_wizard)
            menu.addAction(project_action)

            select_parent_action = QAction("选择国策为母国策新建国策", self)
            select_parent_action.triggered.connect(lambda: self._begin_parent_selection(scene_pos))
            menu.addAction(select_parent_action)

        menu.exec(event.globalPos())

    def _begin_move_focus(self, focus_id):
        """进入移动模式：下一次单击的位置作为国策的新坐标。"""
        self._cancel_pending_modes()
        self._pending_move_focus = focus_id
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _begin_parent_selection(self, scene_pos):
        """进入选择母国策模式：下一次单击某个国策作为母国策，新国策生成在右键位置。"""
        self._cancel_pending_modes()
        self._pending_parent_scene_pos = scene_pos
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _pick_focus_icon(self, focus_id):
        """打开图标选择对话框，从游戏/mod 图标中选择并应用到国策。

        国策图标只展示以 GFX_focus 开头的图标，并保留该国策当前使用的图标。
        """
        from icon_picker_dialog import IconPickerDialog
        gfx_map = {}
        window = self.window()
        if window is not None and hasattr(window, "renderer") and window.renderer.gfx_map:
            gfx_map = window.renderer.gfx_map
        if not gfx_map:
            trans = _get_translator()
            if trans and trans.gfx_map:
                gfx_map = trans.gfx_map
        if not gfx_map:
            QMessageBox.warning(self, "错误", "未找到可用图标（请先配置钢铁雄心4目录或打开 mod 目录）")
            return
        current_icon = self._get_focus_icon(focus_id)
        dlg = IconPickerDialog(
            gfx_map,
            translator=_get_translator(),
            parent=self,
            prefix="GFX_focus",
            current_icon=current_icon,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            icon_name = dlg.get_selected_icon()
            if icon_name:
                self._set_focus_icon(focus_id, icon_name)

    def _get_focus_icon(self, focus_id):
        """读取国策当前 icon 字段值（用于选择图标时保留当前项）。"""
        file_path = self._file_for_focus(focus_id)
        if not file_path:
            return ""
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            start, end = self._find_focus_block_range(content, focus_id)
            if start < 0:
                return ""
            m = re.search(r'\bicon\s*=\s*([^\s}]+)', content[start:end])
            if m:
                return m.group(1).strip('"')
        except Exception:
            pass
        return ""

    def _begin_icon_upload(self, focus_id):
        """进入上传图标模式：将图片文件拖拽到画布上即可应用到指定国策。"""
        self._cancel_pending_modes()
        self._pending_icon_focus = focus_id
        self.setCursor(Qt.CursorShape.DragCopyCursor)
        QMessageBox.information(
            self, "上传图标",
            f"请将图片文件（png/jpg/bmp/dds 等）拖拽到画布上，将应用到国策 '{focus_id}'。"
        )

    def _upload_icon_dialog(self, focus_id):
        """打开上传图标对话框：选择图片并指定图标名后上传为新图标。"""
        from icon_upload_dialog import IconUploadDialog
        dlg = IconUploadDialog(focus_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            image_path, icon_name = dlg.get_selection()
            if image_path:
                self._apply_uploaded_icon(focus_id, image_path, icon_base=icon_name)

    def dragEnterEvent(self, event):
        """接受图片文件的拖拽进入。"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.dds', '.tga')):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        """处理图标文件拖放：自动归位图片、生成 .gfx 文件并更新实体/国策图标。"""
        if self._view_mode == "entities":
            self._drop_entity_icon(event)
            return
        if event.mimeData().hasUrls():
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            images = [p for p in files if p and p.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.dds', '.tga'))]
            if images:
                focus_id = None
                item = self.itemAt(event.pos())
                if item and item.data(0) and item.data(1):
                    focus_id = item.data(0)
                if focus_id is None:
                    focus_id = self._pending_icon_focus
                if focus_id is None:
                    QMessageBox.warning(self, "错误", "请将图标拖拽到具体的国策上，或先右键国策选择「上传图标」")
                    event.acceptProposedAction()
                    return
                self._cancel_pending_modes()
                self._apply_uploaded_icon(focus_id, images[0])
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _set_focus_icon(self, focus_id, icon_name):
        """更新国策文件中的 icon 字段并重绘；若国策没有 icon 字段则自动插入。"""
        file_path = self._file_for_focus(focus_id)
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            start, end = icon_ops.find_block_range(
                content, ("focus", "shared_focus", "joint_focus"), focus_id)
            if start < 0:
                QMessageBox.warning(self, "错误", f"未找到国策 '{focus_id}'")
                return
            new_content = icon_ops.apply_icon_to_entity(
                content, start, end, "icon", icon_name)
            icon_ops.write_file_utf8(file_path, new_content)
            self._current_file_path = file_path
            self.redraw()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置图标失败: {e}")

    @staticmethod
    def _get_focus_icon_cfg():
        """国策图标的类型配置（上传目录 / gfx 文件 / 精灵名规则）。"""
        return {
            "subdir": "gfx/interface/goals",
            "gfx_file": "goals_mod.gfx",
            "shine_gfx_file": "goals_shine_mod.gfx",
            "gfx_name_pattern": "GFX_goal_{name}",
            "shine_sprite_pattern": "GFX_goal_{name}_shine",
            "shine": True,
            "ref_mode": "sprite",
        }

    def _apply_uploaded_icon(self, focus_id, image_path, icon_base=None):
        """处理上传的图标：复制到 mod 的 goals 目录、生成/更新 .gfx 文件、更新国策 icon。

        Args:
            focus_id (str): 国策ID
            image_path (str): 本地图片文件路径
            icon_base (str, optional): 图标资源基础名，默认使用 focus_id
        """
        mod_path = _get_mod_path()
        if not mod_path:
            QMessageBox.warning(self, "错误", "请先在菜单「打开mod文件夹」中打开一个 mod 目录")
            return
        icon_base = (icon_base or focus_id).strip()
        try:
            # 处理上传：保存 dds、更新 .gfx、返回应写入的精灵名
            sprite_name = icon_ops.upload_icon(
                mod_path, image_path, icon_base, self._get_focus_icon_cfg())

            # 更新国策文件中的 icon 字段
            self._set_focus_icon(focus_id, sprite_name)
            QMessageBox.information(
                self, "成功",
                f"图标已上传到国策 '{focus_id}'（{sprite_name}）"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"上传图标失败: {e}")

    @staticmethod
    def _update_gfx_file(gfx_path, sprite_name, texture_rel):
        """在指定 .gfx 文件中添加或更新一个 SpriteType 精灵定义。"""
        return icon_ops.update_gfx_file(gfx_path, sprite_name, texture_rel)

    def _create_new_focus(self, scene_pos):
        """在指定场景位置新建国策（无母国策）。"""
        focus_id, ok = QInputDialog.getText(self, "新建国策", "输入新国策 ID:")
        if not ok or not focus_id.strip():
            return
        focus_id = focus_id.strip()

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', focus_id):
            QMessageBox.warning(self, "错误", "国策 ID 只能包含字母、数字、下划线，且不能以数字开头")
            return

        x, y = self._scene_to_grid(scene_pos)
        self._insert_focus_into_file(focus_id, x, y)

    def _create_focus_project_wizard(self):
        """项目级联动：向导输入后一键生成国策 + 事件 + 决议 + 图标 + 本地化。"""
        from project_wizard import ContentProjectDialog, generate_project
        mod = _get_mod_path()
        if not mod or not os.path.isdir(mod):
            QMessageBox.warning(self, "错误", "请先在菜单「打开mod文件夹」中打开一个 mod 目录")
            return
        country = self._nofile_focus_country or ""
        dlg = ContentProjectDialog(parent=self, country=country, mod_path=mod)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data:
            return
        # 目标国策文件：无文件模式取该国文件，文件模式取当前打开文件
        target = None
        if self._nofile_focus_files:
            target = next(iter(self._nofile_focus_files.values()), None)
        if not target:
            target = self._get_current_file_path()
        if not target:
            QMessageBox.warning(self, "错误", "未找到可写入的国策文件（请先选择国家或打开国策文件）")
            return
        try:
            summary = generate_project(data, mod, target)
            # 刷新：无文件模式重扫该国国策文件并重绘；文件模式走常规重绘
            if self._nofile_focus_data is not None:
                self.show_focus_tree_nofile(
                    self._nofile_focus_country,
                    list(self._nofile_focus_files.values()))
            else:
                self.redraw()
            QMessageBox.information(self, "项目生成完成", "\n".join(summary))
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"项目生成失败: {e}")

    def _create_focus_with_parent(self, parent_id, scene_pos):
        """以右键位置为新国策位置，选择 parent_id 作为母国策新建国策。"""
        focus_id, ok = QInputDialog.getText(self, "新建国策", f"输入新国策 ID（以 {parent_id} 为母国策）:")
        if not ok or not focus_id.strip():
            return
        focus_id = focus_id.strip()

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', focus_id):
            QMessageBox.warning(self, "错误", "国策 ID 只能包含字母、数字、下划线，且不能以数字开头")
            return

        x, y = self._scene_to_grid(scene_pos)
        self._insert_focus_into_file(focus_id, x, y, parent_id)

    def _create_child_focus(self, parent_id):
        """以 parent_id 为母国策新建国策，默认生成在母国策正下方 (x, y+1)。"""
        pos = self._get_focus_grid_pos(parent_id)
        if pos is None:
            QMessageBox.warning(self, "错误", f"未找到国策 '{parent_id}' 的位置")
            return
        parent_x, parent_y = pos

        focus_id, ok = QInputDialog.getText(
            self, "新建国策",
            f"输入新国策 ID（以 {parent_id} 为母国策，生成于其正下方）:"
        )
        if not ok or not focus_id.strip():
            return
        focus_id = focus_id.strip()

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', focus_id):
            QMessageBox.warning(self, "错误", "国策 ID 只能包含字母、数字、下划线，且不能以数字开头")
            return

        # 以母国策为原点，新国策生成在正下方
        self._insert_focus_into_file(focus_id, parent_x, parent_y + 1, parent_id)

    def _build_focus_text(self, focus_id, x, y, parent_id=None):
        """生成新国策文本块（算法见 focus_algo）。"""
        import focus_algo
        import os as _os
        return focus_algo.build_focus_text(
            focus_id, x, y, parent_id,
            template_dir=PROJECT_ROOT)
    def _insert_focus_into_file(self, focus_id, x, y, parent_id=None):
        """将新国策写入文件末尾，并重绘。"""
        file_path = self._get_current_file_path()
        if not file_path:
            QMessageBox.warning(self, "错误", "请先打开一个国策文件")
            return

        new_focus_text = self._build_focus_text(focus_id, x, y, parent_id)
        new_focus_lines = ["\t" + line if line.strip() else line for line in new_focus_text.split('\n')]
        new_focus_lines.append('')

        try:
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                lines = content.split('\n')
            else:
                lines = ['focus_tree = {', '\tcountry = {', '\t}', '}']

            last_brace = -1
            for i in range(len(lines) - 1, -1, -1):
                stripped = lines[i].strip()
                if stripped == '}':
                    last_brace = i
                    break

            if last_brace <= 0:
                QMessageBox.warning(self, "错误", "无法找到国策树结构的插入位置")
                return

            lines = lines[:last_brace] + new_focus_lines + lines[last_brace:]
            from write_utils import atomic_write_text
            atomic_write_text(file_path, '\n'.join(lines))

            self._current_file_path = file_path
            self.redraw()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建国策失败: {e}")

    def _open_focus_editor(self, focus_id):
        file_path = self._file_for_focus(focus_id)
        if not file_path:
            return
        try:
            result = parse_focus_file(file_path, focus_id)
            focus_load, file_lines, block_range, x_val, y_val, raw_fields = result
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return

        translator = _get_translator()
        loc_manager = _get_loc_manager()
        self.current_editor = FocusTreeEditor(
            focus_load=focus_load,
            file_path=file_path,
            file_lines=file_lines,
            block_range=block_range,
            x_val=x_val,
            y_val=y_val,
            translator=translator,
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            raw_fields=raw_fields,
            loc_manager=loc_manager,
            parent=self,
            hoi4_path=_get_hoi4_path(),
            mod_path=_get_mod_path(),
        )
        self.current_editor.tree_saved.connect(self.redraw)
        self.current_editor.translation_saved.connect(self._on_editor_translation_saved)
        self.current_editor.show()

    def _find_focus_block_range(self, content, focus_id):
        """定位国策块范围（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.find_focus_block_range(content, focus_id)
    def _move_focus(self, focus_id, new_x, new_y):
        """更新国策的 x/y 坐标并重绘。"""
        file_path = self._file_for_focus(focus_id)
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            start, end = self._find_focus_block_range(content, focus_id)
            if start < 0:
                QMessageBox.warning(self, "错误", f"未找到国策 '{focus_id}'")
                return

            block = content[start:end]
            new_block = re.sub(r'\bx\s*=\s*-?\d+(?:\.\d+)?', f'x = {new_x}', block, count=1)
            new_block = re.sub(r'\by\s*=\s*-?\d+(?:\.\d+)?', f'y = {new_y}', new_block, count=1)
            # 国策使用绝对 x/y 定位，移除矛盾的 relative_position_id（否则游戏内位置会二次偏移）
            new_block = re.sub(r'^\s*relative_position_id\s*=\s*[^\r\n]*\r?\n?', '', new_block, count=1, flags=re.M)

            if new_block == block:
                QMessageBox.warning(self, "错误", f"未找到国策 '{focus_id}' 的 x/y 字段")
                return

            from write_utils import atomic_write_text
            atomic_write_text(file_path, content[:start] + new_block + content[end:])

            self._current_file_path = file_path
            self.redraw()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"移动国策失败: {e}")

    def _delete_focus(self, focus_id):
        file_path = self._file_for_focus(focus_id)
        if not file_path:
            return
        reply = QMessageBox.question(self, "确认删除", f"确定要删除国策 '{focus_id}' 吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            start, end = self._find_focus_block_range(content, focus_id)
            if start < 0:
                QMessageBox.warning(self, "错误", f"未找到国策 '{focus_id}'")
                return

            new_content = content[:start] + content[end:]
            new_content = re.sub(r'\n{3,}', '\n\n', new_content)

            from write_utils import atomic_write_text
            atomic_write_text(file_path, new_content)

            self._current_file_path = file_path
            self.redraw()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除国策失败: {e}")

    # ==========================================================
    # 实体画廊模式（图标型内容在右侧国策组件中展示）
    # ==========================================================

    GALLERY_CELL_W = 170
    GALLERY_CELL_H = 190
    GALLERY_COLS = 5
    NOFILE_GALLERY_COLS = 8   # 无文件模式画廊每行实体数量（更多，减少纵向滚动）

    def _gallery_font(self):
        if self._gallery_font_obj is None:
            self._gallery_font_obj = QFont("Microsoft YaHei", 8)
        return self._gallery_font_obj

    def _gallery_gfx_map(self):
        from gui_translator import get_translator, scan_gfx_folder
        g = dict(get_translator().gfx_map)
        mod = _get_mod_path()
        if mod:
            scan_gfx_folder(mod, g)
        return g

    def _unique_entity_key(self, base, entities):
        """生成不冲突实体键（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.unique_entity_key(base, entities)
    def show_focus_tree_nofile(self, country, files):
        """无文件模式：跨文件合并绘制国策树（展示当前设计中的国家）。

        - 必须先选择国家（country 非空），只绘制该国家的合并树
        - 每个节点的文件映射到其来源文件（双击/右键编辑落在正确文件）
        - 场景左上角显示标题（国家 + 文件数 + 国策数）
        """
        from workbench import WorkbenchDock
        from focus_processor import FocusProcessor

        self._view_mode = "focus"
        self._nofile_entity_list = None
        self._entity_items = {}
        self._cancel_pending_modes()
        self._current_file_path = None
        self._entity_highlight = None
        self.find_shortcut.setEnabled(False)

        self._nofile_focus_country = country or ""
        self._nofile_focus_files = {}

        if not country:
            # 未选择国家：不绘制任何国家树，提示先选择
            self._nofile_focus_data = None
            self.scene().clear()
            self._nofile_focus_title_item = None
            tip = QGraphicsSimpleTextItem(
                "🗺 请先在左侧「当前国家」选择要设计的国家\n"
                "（或点击 🌐 国家设置 创建/复制国家）")
            tip.setBrush(QBrush(QColor(200, 200, 120)))
            tip.setFont(self._gallery_font())
            tip.setPos(30, 30)
            self.scene().addItem(tip)
            return

        files = [f for f in files if f and os.path.isfile(f)]
        merged = {}
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                data = WorkbenchDock._quick_focus_scan(content)
                for fid, node in data.items():
                    if fid not in merged:
                        merged[fid] = node
                        self._nofile_focus_files[fid] = fp
            except Exception:
                continue

        proc = FocusProcessor()
        proc.focus_data = merged
        proc._calculate_absolute_positions()
        self._nofile_focus_data = merged
        if not merged:
            # 无可用国策：清空场景并显示提示
            self.scene().clear()
            self._nofile_focus_title_item = None
            tip = QGraphicsSimpleTextItem(
                f"（{country or '全部国家'} 没有可绘制的国策树）")
            tip.setBrush(QBrush(QColor(160, 160, 160)))
            tip.setFont(self._gallery_font())
            tip.setPos(30, 30)
            self.scene().addItem(tip)
            return
        self._redraw_nofile_focus_tree()

    def _redraw_nofile_focus_tree(self):
        """重绘无文件模式合并国策树（编辑/删除/移动后调用）。"""
        window = self.window()
        renderer = getattr(window, "renderer", None) if window is not None else None
        if renderer is None:
            from focus_renderer import FocusRenderer
            renderer = FocusRenderer(self.scene())
        try:
            renderer.set_loc_manager(_get_loc_manager())
        except Exception:
            pass
        renderer.draw_graph(self._nofile_focus_data, "<无文件模式>")
        # 每个节点映射回其来源文件（渲染器只支持单文件标记）
        for item in self.scene().items():
            fid = item.data(0)
            if fid and fid in self._nofile_focus_files:
                item.setData(1, self._nofile_focus_files[fid])

        # 标题：正在设计的国家 + 统计
        if self._nofile_focus_title_item is not None:
            try:
                self.scene().removeItem(self._nofile_focus_title_item)
            except Exception:
                pass
            self._nofile_focus_title_item = None
        country = self._nofile_focus_country
        title_text = (f"🇪🇺 无文件模式 · 正在设计：{country}"
                      if country else "🌍 无文件模式 · 全部国家国策树")
        title_text += (f"（{len(self._nofile_focus_files)} 文件 · "
                       f"{len(self._nofile_focus_data)} 国策）")
        title = QGraphicsSimpleTextItem(title_text)
        tfont = QFont(self._gallery_font())
        tfont.setBold(True)
        tfont.setPointSize(tfont.pointSize() + 2)
        title.setFont(tfont)
        title.setBrush(QBrush(QColor(255, 200, 90)))
        title.setPos(14, 10)
        title.setZValue(100)
        self.scene().addItem(title)
        self._nofile_focus_title_item = title

        rect = self.scene().itemsBoundingRect().adjusted(-100, -60, 100, 100)
        self.scene().setSceneRect(rect)
        self.centerOn(rect.center())

    def _file_for_focus(self, focus_id):
        """返回国策所在文件：无文件模式按映射，文件模式用当前文件。"""
        if self._nofile_focus_files and focus_id in self._nofile_focus_files:
            return self._nofile_focus_files[focus_id]
        return self._get_current_file_path()

    def set_current_country_hint(self, tag):
        """设置无文件模式「当前国家」提示（None=全部）。

        新建/移动/复制实体选择目标文件时，优先推荐该国家对应的文件。
        """
        self._country_hint = (tag or "").strip().upper() or None

    # ══════════════════════════════════════════════════════════
    # 科技树模式：与国策树同一画布绘制（树形自动布局，并行分支铺开）
    # ══════════════════════════════════════════════════════════

    def _choose_nofile_target_file(self, exclude="", action_text="新建实体"):
        """弹窗：选择无文件模式下的目标文件（按国家分组列出）。

        Args:
            exclude: 排除的文件路径（移动/复制时排除源文件）
            action_text: 动作描述（用于标题与提示文案）
        Returns:
            选中的文件路径；取消返回 None
        """
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget,
                                     QListWidgetItem, QDialogButtonBox)
        from workbench import WorkbenchDock

        candidates = [fp for fp in self._nofile_files if fp != exclude]
        if not candidates:
            QMessageBox.information(self, "提示", "没有可用的目标文件")
            return None

        dlg = QDialog(self)
        dlg.setWindowTitle(f"选择目标文件（{action_text}）")
        dlg.resize(460, 460)
        lay = QVBoxLayout(dlg)
        hint = "将「%s」写入哪个文件？" % action_text
        if self._country_hint:
            hint += f"\n当前国家 {self._country_hint} 的文件已置顶（★）。"
        lay.addWidget(QLabel(hint))
        lst = QListWidget()
        groups = {}
        for fp in candidates:
            tags = WorkbenchDock._detect_country_tags(fp, WorkbenchDock._read_file(fp))
            groups.setdefault(tags[0] if tags else "", []).append(fp)

        def group_key(c):
            # 当前国家文件优先；其次有国家分组；最后无国家
            if self._country_hint and c == self._country_hint:
                return (0, c)
            return (1 if c else 2, c)

        prefer_first = None
        for c in sorted(groups, key=group_key):
            for fp in groups[c]:
                mark = "★ " if (self._country_hint and c == self._country_hint) else ""
                label = f"{mark}{c} · {os.path.basename(fp)}" if c else os.path.basename(fp)
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, fp)
                lst.addItem(item)
                if prefer_first is None:
                    prefer_first = item
        lay.addWidget(lst)
        btnbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btnbox.accepted.connect(dlg.accept)
        btnbox.rejected.connect(dlg.reject)
        lay.addWidget(btnbox)
        if prefer_first is not None:
            lst.setCurrentItem(prefer_first)
        if dlg.exec() == QDialog.DialogCode.Accepted and lst.currentItem():
            return lst.currentItem().data(Qt.ItemDataRole.UserRole)
        return None

    def _insert_entity_block(self, file_path, content_type, block):
        """将实体块文本写入指定文件并返回新内容。

        - character：写入 characters = { ... } 包装块的闭合括号前
          （无包装块时创建包装块）
        - 其余类型：追加到文件末尾（保持换行整洁）

        Returns:
            str: 写入后的完整文件内容
        """
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        if content_type == "character":
            start, end = icon_ops.find_block_range(content, {"characters"})
            if start >= 0 and end > start:
                insert_pos = end - 1  # 包装块闭合 } 前
                return content[:insert_pos] + block + content[insert_pos:]
            # 无 characters 包装块：新建包装块包裹
            new_wrap = "\ncharacters = {\n" + block + "}\n"
            return content.rstrip() + "\n" + new_wrap
        # 无包装块或非角色类型：追加到文件末尾
        rstripped = content.rstrip()
        return rstripped + "\n" + block

    def _entity_block_text(self, entity):
        """从源文件提取实体块文本（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.entity_block_text_from_file(
            entity, self._current_file_path)
    def _entity_block_text_source(self, source, entity):
        """从源文件删除实体块后的内容（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.entity_block_text_source(source, entity)
    @staticmethod
    def _build_entity_block(content_type, key):
        """生成实体块文本（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.build_entity_block(content_type, key)

    @staticmethod
    def _entity_block_end(content, start_char):
        """返回实体块平衡右括号位置（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.entity_block_end(content, start_char)

    @staticmethod
    def _locate_entity(editor, entity_id):
        try:
            model = getattr(editor, "model", None)
            if model is None:
                return
            results = model.find_nodes(entity_id)
            if results:
                editor.tree_view.setCurrentIndex(results[0])
                editor.tree_view.scrollTo(results[0])
        except Exception:
            pass

    def _entity_field_for_slot(self, slot):
        """返回槽位对应的写入字段（算法见 focus_algo）。"""
        import focus_algo
        return focus_algo.entity_field_for_slot(self._entity_cfg, slot)
