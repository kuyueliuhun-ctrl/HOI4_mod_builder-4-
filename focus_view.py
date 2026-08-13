import os
import re
import json
from PyQt6.QtWidgets import QGraphicsView, QMenu, QDialog, QInputDialog, QMessageBox, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsSimpleTextItem, QGraphicsRectItem
from PyQt6.QtGui import QPainter, QAction, QFont, QColor, QPixmap, QBrush, QPen, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QPoint
from focus_parser import parse_focus_file
from gui_translator import GuiTranslator
from focus_base_builder import FocusTreeEditor
from localization_mgr import get_localization_manager
import icon_ops


CUSTOM_STATEMENT_PATH = os.path.join(os.path.dirname(__file__), "custom_statements.json")

_translator = None
_loc_manager = None


def _get_settings():
    """读取最新的 settings.json 配置。

    不缓存，确保打开/切换 mod 后能读到最新的 mod_path / HOI4_path，
    使树形编辑器能正确加载 mod 文件夹中的翻译文件。
    """
    settings = {}
    settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
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


class FocusView(QGraphicsView):
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

        # Ctrl+F：实体画廊中按英文 id / 中文名查找并定位实体
        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self._open_entity_find_dialog)
        self.find_shortcut.setEnabled(False)

        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def _scene_to_grid(self, scene_pos):
        """将场景坐标转换为国策网格坐标 (x, y)。

        渲染时国策 (x,y) 绘制在场景 ((x+0.5)*90, (y+0.5)*130)，
        因此反算应为 round(px/90 - 0.5)。旧实现 round(px/90)-1 会偏差一整格。
        """
        return (round(scene_pos.x() / self.GRID_X - 0.5),
                round(scene_pos.y() / self.GRID_Y - 0.5))

    def _grid_to_scene(self, gx, gy):
        """国策网格坐标 (x,y) 转场景坐标（单元格中心，即渲染时图标中心）。"""
        return (gx + 0.5) * self.GRID_X, (gy + 0.5) * self.GRID_Y

    def _snap_to_grid_center(self, scene_pos):
        """将场景坐标吸附到最近单元格中心，返回 (吸附后的场景坐标, 网格坐标)。"""
        gx = round(scene_pos.x() / self.GRID_X - 0.5)
        gy = round(scene_pos.y() / self.GRID_Y - 0.5)
        return self._grid_to_scene(gx, gy), (gx, gy)

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

    def _get_current_file_path(self):
        if self._current_file_path:
            return self._current_file_path
        for item in self.scene().items():
            if item.data(1):
                self._current_file_path = item.data(1)
                return item.data(1)
        return None

    def contextMenuEvent(self, event):
        if self._view_mode == "entities":
            self._show_entity_context_menu(event)
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
        file_path = self._get_current_file_path()
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
        file_path = self._get_current_file_path()
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
        """根据模板生成新国策的文本块，可选写入母国策 prerequisite 关系。

        国策使用绝对 x/y 定位，故不再写入 relative_position_id
        （否则会与绝对坐标叠加，导致渲染/游戏内位置偏移）。
        """
        template_path = os.path.join(os.path.dirname(__file__), "templates", "focus.txt")
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8-sig', newline='') as f:
                template_content = f.read()
            template_content = template_content.replace('\r\n', '\n').replace('\r', '\n')
            new_focus_text = template_content.replace("id = ", f"id = {focus_id}", 1)
            new_focus_text = new_focus_text.replace("x = ", f"x = {x}", 1)
            new_focus_text = new_focus_text.replace("y = ", f"y = {y}", 1)
            if parent_id:
                new_focus_text = re.sub(
                    r'prerequisite\s*=\s*\{\s*\}',
                    f'prerequisite = {{ focus = {parent_id} }}',
                    new_focus_text,
                    count=1,
                )
        else:
            new_focus_text = (
                f"focus = {{\n"
                f"\tid = {focus_id}\n"
                f"\ticone = unknown\n"
                f"\tx = {x}\n"
                f"\ty = {y}\n"
                f"\tcost = 70\n"
            )
            if parent_id:
                new_focus_text += f"\tprerequisite = {{\n\t\tfocus = {parent_id}\n\t}}\n"
            new_focus_text += "}"
        return new_focus_text

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
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write('\n'.join(lines))

            self._current_file_path = file_path
            self.redraw()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建国策失败: {e}")

    def _open_focus_editor(self, focus_id):
        file_path = self._get_current_file_path()
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
        """在文件内容中定位包含指定 id 的国策块，返回 (起始字符, 结束字符)，未找到返回 (-1, -1)。"""
        token_pattern = r'("[^"]*"|#.*|\{|\}|=|[\w\.\-]+)'
        raw_matches = list(re.finditer(token_pattern, content))
        tokens = [m.group(0) for m in raw_matches if not m.group(0).startswith('#')]

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in ('focus', 'shared_focus', 'joint_focus'):
                if i + 2 < len(tokens) and tokens[i + 1] == '=' and tokens[i + 2] == '{':
                    block_start = raw_matches[i].start()
                    depth = 1
                    j = i + 3
                    while j < len(tokens) and depth > 0:
                        if tokens[j] == '{':
                            depth += 1
                        elif tokens[j] == '}':
                            depth -= 1
                        j += 1
                    block_end_idx = j - 1

                    # 检查块内是否包含目标 id
                    block_tokens = tokens[i + 3:block_end_idx]
                    has_id = False
                    for k, t in enumerate(block_tokens):
                        if t == 'id' and k + 2 < len(block_tokens) and block_tokens[k + 1] == '=':
                            id_val = block_tokens[k + 2].strip('"')
                            if id_val == focus_id:
                                has_id = True
                                break

                    if has_id:
                        return block_start, raw_matches[block_end_idx].end()
                    i = j
                    continue
            i += 1
        return -1, -1

    def _move_focus(self, focus_id, new_x, new_y):
        """更新国策的 x/y 坐标并重绘。"""
        file_path = self._get_current_file_path()
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

            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(content[:start] + new_block + content[end:])

            self._current_file_path = file_path
            self.redraw()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"移动国策失败: {e}")

    def _delete_focus(self, focus_id):
        file_path = self._get_current_file_path()
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

            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(new_content)

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

    def show_entity_gallery(self, content_type, file_path):
        """在右侧国策组件中展示指定文件的实体图标画廊。

        每个实体显示 图标缩略图 + 名称（中文名）。双击实体打开树形编辑器，
        右键提供 编辑/选择图标/上传图标/删除 等操作。
        """
        from workbench import WorkbenchDock, ICON_RULES
        cfg = ICON_RULES.get(content_type)
        if not cfg:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read()
        except Exception:
            QMessageBox.critical(self, "错误", f"无法读取文件: {file_path}")
            return
        entities = WorkbenchDock._extract_entities(content_type, content)
        self._nofile_entity_list = None
        self._nofile_files = []
        self._render_entity_gallery(content_type, cfg, entities, file_path)

    def show_entity_gallery_nofile(self, content_type, entities):
        """无文件模式：在右侧国策组件中展示跨文件收集的全部实体。

        每个实体字典需携带 file（源文件路径，用于编辑/删除/打开树编辑器）与
        可选的 country（国家标签，用于提示）。双击实体打开其源文件的树形编辑器。
        """
        from workbench import ICON_RULES
        cfg = ICON_RULES.get(content_type) or {}
        cleaned = [dict(e) for e in entities]
        self._nofile_entity_list = cleaned
        self._nofile_files = sorted({
            e.get("file", "") for e in cleaned if e.get("file")})
        self._render_entity_gallery(content_type, cfg, cleaned, None)

    def _render_entity_gallery(self, content_type, cfg, entities, file_path):
        """实体画廊统一渲染；file_path 为 None 表示无文件模式（实体携带 file 键）。"""
        self._view_mode = "entities"
        self._entity_type = content_type
        self._entity_cfg = cfg
        self._current_file_path = file_path
        self._entity_items = {}
        self._pending_entity_icon = None
        self._cancel_pending_modes()
        self.find_shortcut.setEnabled(True)

        scene = self.scene()
        scene.clear()
        self.resetTransform()
        self._entity_highlight = None

        from icon_resolver import resolve_pixmap
        from localization_mgr import get_localization_manager
        loc = get_localization_manager()
        loc.reload(game_path=_get_hoi4_path(), mod_path=_get_mod_path())
        gfx_map = self._gallery_gfx_map()
        nofile = file_path is None
        cols = self.NOFILE_GALLERY_COLS if nofile else self.GALLERY_COLS

        # 无文件模式：按国家分组（有国家标签的组 + 未分国家组），组前绘制标题行
        groups = {}
        rows = []
        if nofile:
            for ent in entities:
                groups.setdefault((ent.get("tags") or [""])[0], []).append(ent)
            order = sorted(groups)
            if "" in order:
                order = [c for c in order if c != ""] + [""]
            for c in order:
                if c:
                    rows.append(("header", c))
                for ent in groups[c]:
                    rows.append(("entity", ent))
        else:
            rows = [("entity", e) for e in entities]

        cur_row = 0
        cur_col = 0
        for kind, payload in rows:
            if kind == "header":
                cur_col = 0
                cur_row += 1
                y = cur_row * self.GALLERY_CELL_H + 30
                hfont = QFont(self._gallery_font())
                hfont.setBold(True)
                hfont.setPointSize(hfont.pointSize() + 1)
                head = QGraphicsSimpleTextItem(f"🏷 {payload}（{len(groups[payload])}）")
                head.setFont(hfont)
                head.setBrush(QBrush(QColor(255, 200, 90)))
                head.setPos(14, y)
                head.setData(0, "__header__")
                scene.addItem(head)
                cur_row += 1
                continue
            if cur_col >= cols:
                cur_col = 0
                cur_row += 1
            ent = payload
            col = cur_col
            row = cur_row
            x = col * self.GALLERY_CELL_W + self.GALLERY_CELL_W // 2
            y = row * self.GALLERY_CELL_H + self.GALLERY_CELL_H // 2

            ent_file = ent.get("file") or file_path or ""

            pm = resolve_pixmap(ent.get("icon", ""), dirs=cfg.get("dirs"),
                                gfx_map=gfx_map, mod_path=_get_mod_path(),
                                hoi4_path=_get_hoi4_path())
            if pm is not None and not pm.isNull():
                thumb = pm.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            else:
                thumb = QPixmap(64, 64)
                thumb.fill(QColor(70, 70, 74))
            pix_item = QGraphicsPixmapItem(thumb)
            pix_item.setPos(x - thumb.width() / 2, y - thumb.height() / 2 - 18)
            pix_item.setData(0, ent["name"])
            pix_item.setData(1, ent_file)
            pix_item.setData(2, ent)
            scene.addItem(pix_item)

            display = ent["name"]
            cn = loc.get_name(ent["name"])
            if cn:
                display = cn
            text_item = QGraphicsSimpleTextItem()
            text_item.setBrush(QBrush(Qt.GlobalColor.white))
            text_item.setFont(self._gallery_font())
            from PyQt6.QtGui import QFontMetrics
            fm = QFontMetrics(self._gallery_font())
            elided = fm.elidedText(display, Qt.TextElideMode.ElideRight,
                                   self.GALLERY_CELL_W - 12)
            text_item.setText(elided)
            tw = text_item.boundingRect().width()
            text_item.setPos(x - tw / 2, y + 20)
            text_item.setData(0, ent["name"])
            text_item.setData(1, ent_file)
            text_item.setData(2, ent)
            scene.addItem(text_item)

            if nofile:
                tags = "、".join(ent.get("tags") or [])
                tooltip = f"{ent['name']}\n国家: {tags or '—'}\n文件: {ent_file}"
                pix_item.setToolTip(tooltip)
                text_item.setToolTip(tooltip)

            self._entity_items[ent["name"]] = (pix_item, text_item, x, y)
            cur_col += 1

        # 新建实体按钮：位于实体网格下方
        self._add_entity_button_proxy = None
        show_add = bool(entities) or (nofile and bool(self._nofile_files))
        if show_add:
            from PyQt6.QtWidgets import QPushButton, QGraphicsProxyWidget
            btn = QPushButton(self._entity_add_button_text())
            btn.setFixedSize(140, 34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._add_new_entity)
            proxy = QGraphicsProxyWidget()
            proxy.setWidget(btn)
            btn_row = cur_row + 1
            proxy.setPos(self.GALLERY_CELL_W // 2 - 70, btn_row * self.GALLERY_CELL_H + 30)
            scene.addItem(proxy)
            self._add_entity_button_proxy = proxy
        elif not entities:
            empty_text = QGraphicsSimpleTextItem("（无实体）")
            empty_text.setBrush(QBrush(QColor(160, 160, 160)))
            empty_text.setFont(self._gallery_font())
            empty_text.setPos(30, 30)
            scene.addItem(empty_text)

        scene.setSceneRect(scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))

    def _reload_nofile_gallery(self):
        """重新从各源文件提取实体并刷新无文件画廊（删除/修改后调用）。"""
        from workbench import WorkbenchDock
        entities = []
        for fp in self._nofile_files:
            content = WorkbenchDock._read_file(fp)
            if not content.strip():
                continue
            entities.extend(WorkbenchDock._collect_file_entities(
                self._entity_type, content, fp))
        self.show_entity_gallery_nofile(self._entity_type, entities)

    def _open_entity_find_dialog(self):
        """Ctrl+F：打开实体查找定位对话框（英文 id / 中文名）。"""
        if self._view_mode != "entities" or not self._entity_items:
            return
        if self._entity_find_dialog is None:
            from entity_find_dialog import EntityFindDialog
            loc = _get_loc_manager()

            def get_cn(name):
                try:
                    return (loc.get_name(name) or "") if loc is not None else ""
                except Exception:
                    return ""

            self._entity_find_dialog = EntityFindDialog(
                sorted(self._entity_items), get_cn, parent=self)
            self._entity_find_dialog.locate_requested.connect(self._locate_gallery_entity)
        self._entity_find_dialog.refresh_entities(sorted(self._entity_items))
        self._entity_find_dialog.focus_search()

    def _locate_gallery_entity(self, name):
        """定位画廊实体：视图居中并绘制高亮边框。"""
        if name not in self._entity_items:
            return
        _pix, _text, x, y = self._entity_items[name]
        if self._entity_highlight is not None:
            try:
                self.scene().removeItem(self._entity_highlight)
            except Exception:
                pass
            self._entity_highlight = None
        half_w, half_h = self.GALLERY_CELL_W / 2, self.GALLERY_CELL_H / 2
        rect = QGraphicsRectItem(x - half_w, y - half_h,
                                 self.GALLERY_CELL_W, self.GALLERY_CELL_H)
        pen = QPen(QColor(255, 170, 0), 2.5)
        pen.setCosmetic(True)
        rect.setPen(pen)
        rect.setBrush(Qt.GlobalColor.transparent)
        rect.setZValue(50)
        self.scene().addItem(rect)
        self._entity_highlight = rect
        self.centerOn(x, y)

    def _entity_add_button_text(self):
        """新建实体按钮文案。"""
        try:
            from workbench import CONTENT_TYPES
            for key, name, *_ in CONTENT_TYPES:
                if key == self._entity_type:
                    return f"＋ 新建{name if key != 'character' else '人物'}"
        except Exception:
            pass
        return "＋ 新建实体"

    def _unique_entity_key(self, base, entities):
        """生成不与现有实体冲突的键。"""
        existing = {e["name"] for e in entities}
        key = base
        n = 1
        while key in existing:
            key = f"{base}_{n}"
            n += 1
        return key

    def _add_new_entity(self):
        """在当前文件（或无文件模式所选文件）中追加一个新实体块并打开编辑。"""
        if self._nofile_entity_list is not None:
            self._add_new_entity_nofile()
            return
        file_path = self._current_file_path
        if not file_path or not self._entity_type:
            return
        self._add_new_entity_to(file_path)

    def _add_new_entity_nofile(self):
        """无文件模式：新建弹窗选择目标文件后创建实体。"""
        if not self._nofile_files:
            QMessageBox.information(self, "提示", "当前类型没有可写入的文件")
            return
        target = self._choose_nofile_target_file()
        if not target:
            return
        self._add_new_entity_to(target)

    def _choose_nofile_target_file(self):
        """弹窗：选择无文件模式下新建实体的目标文件（按国家分组列出）。"""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget,
                                     QListWidgetItem, QDialogButtonBox)
        from workbench import WorkbenchDock

        dlg = QDialog(self)
        dlg.setWindowTitle("选择目标文件")
        dlg.resize(440, 440)
        lay = QVBoxLayout(dlg)
        btn_text = self._entity_add_button_text().lstrip("＋ ").strip() or "实体"
        lay.addWidget(QLabel(f"将新建「{btn_text}」，请选择写入的文件："))
        lst = QListWidget()
        groups = {}
        for fp in self._nofile_files:
            tags = WorkbenchDock._detect_country_tags(fp, WorkbenchDock._read_file(fp))
            groups.setdefault(tags[0] if tags else "", []).append(fp)
        for c in sorted(groups, key=lambda k: (k == "", k)):
            for fp in groups[c]:
                label = f"{c} · {os.path.basename(fp)}" if c else os.path.basename(fp)
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, fp)
                lst.addItem(item)
        lay.addWidget(lst)
        btnbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btnbox.accepted.connect(dlg.accept)
        btnbox.rejected.connect(dlg.reject)
        lay.addWidget(btnbox)
        if lst.count():
            lst.setCurrentRow(0)
        if dlg.exec() == QDialog.DialogCode.Accepted and lst.currentItem():
            return lst.currentItem().data(Qt.ItemDataRole.UserRole)
        return None

    def _add_new_entity_to(self, file_path):
        """在指定文件中追加一个新实体块，写入并打开树形编辑器定位。

        优先使用系统模板的「项目模板」（节点级骨架）生成块，
        无模板时回退到内置最小块。
        """
        from workbench import WorkbenchDock
        if not file_path or not self._entity_type:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            entities = WorkbenchDock._extract_entities(self._entity_type, content)
            base = f"NEW_{self._entity_type.upper()}"
            key = self._unique_entity_key(base, entities)

            block = self._build_entity_block(self._entity_type, key)

            start, end = icon_ops.find_block_range(content, {"characters"} if self._entity_type == "character" else {key})
            if self._entity_type == "character" and start >= 0:
                insert_pos = end - 1  # 包装块闭合 } 前
                new_content = content[:insert_pos] + block + content[insert_pos:]
            else:
                # 无包装块或非角色类型：追加到文件末尾
                rstripped = content.rstrip()
                new_content = rstripped + "\n" + block
            icon_ops.write_file_utf8(file_path, new_content)

            # 刷新画廊并打开树形编辑器定位到新实体
            if self._nofile_entity_list is not None:
                self._reload_nofile_gallery()
            else:
                self.show_entity_gallery(self._entity_type, file_path)
            new_ent = None
            for e in WorkbenchDock._extract_entities(self._entity_type, new_content):
                if e["name"] == key:
                    new_ent = e
                    break
            if new_ent:
                self._open_entity_tree_editor(file_path, new_ent)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"新建实体失败: {e}")

    @staticmethod
    def _build_entity_block(content_type, key):
        """按内容类型生成实体块文本（优先系统「项目模板」，否则内置最小块）。

        - character：内置带 portraits 的最小角色块
        - 其余类型：尝试 系统模板/<类型>/项目模板.txt 的节点骨架
        """
        from template_scheduler import get_template_scheduler
        if content_type == "character":
            return (
                f"\t{key} = {{\n"
                f"\t\tname = {key}\n"
                f"\t\tportraits = {{\n"
                f"\t\t\tcivilian = {{\n"
                f"\t\t\t\tlarge = \"gfx/Leaders/{key}.png\"\n"
                f"\t\t\t}}\n"
                f"\t\t}}\n"
                f"\t}}\n"
            )
        try:
            scheduler = get_template_scheduler()
            # 系统模板类型键：优先英文模板类型，否则用内容类型中文名
            tkey = None
            for c in __import__("workbench", fromlist=["CONTENT_TYPES"]).CONTENT_TYPES:
                if c[0] == content_type:
                    tkey = c[4] or c[1]
                    break
            if tkey:
                matches = scheduler.search_templates(
                    template_type=tkey, usage="node")
                if matches:
                    with open(matches[0]["filepath"], "r",
                              encoding="utf-8-sig", errors="ignore") as f:
                        tpl_text = f.read()
                    # 把模板第一行键名替换为新实体 key
                    lines = tpl_text.splitlines()
                    if lines:
                        m = re.match(r'^(\s*)(\S+)(\s*=\s*\{.*)$', lines[0])
                        if m:
                            lines[0] = f"{m.group(1)}{key}{m.group(3)}"
                    body = "\n".join("\t" + ln if ln.strip() else ln
                                     for ln in lines)
                    return body.rstrip() + "\n"
        except Exception:
            pass
        return f"\t{key} = {{\n\t\t# 新实体\n\t}}\n"

    def _get_entity_under(self, pos):
        """返回点击位置对应的实体字典，未命中返回 None。"""
        item = self.itemAt(pos)
        if item is not None and item.data(2):
            return item.data(2)
        return None

    def _show_entity_context_menu(self, event):
        menu = QMenu(self)
        entity = self._get_entity_under(event.pos())

        if entity is not None:
            label = entity["name"]
            cn = ""
            loc = _get_loc_manager()
            if loc:
                cn = loc.get_name(entity["name"])
            label = cn or entity["name"]

            edit_action = menu.addAction(f"✎ 编辑: {label}")
            edit_action.triggered.connect(
                lambda: self._open_entity_tree_editor(self._current_file_path, entity))
            menu.addSeparator()
            pick_action = menu.addAction("🎨 选择图标…")
            pick_action.triggered.connect(lambda: self._pick_entity_icon(entity))

            slots_cfg = (self._entity_cfg or {}).get("slots")
            if slots_cfg:
                for skey, sdata in slots_cfg.items():
                    label = sdata.get("label", skey)
                    ul = menu.addAction(f"📤 上传{label}…")
                    ul.triggered.connect(
                        lambda checked=False, sk=skey: self._upload_entity_icon_dialog(entity, sk))
                    dl = menu.addAction(f"🖼 上传{label}（拖拽）")
                    dl.triggered.connect(
                        lambda checked=False, sk=skey: self._begin_entity_icon_upload(entity, sk))
            else:
                field = (self._entity_cfg or {}).get("field", "icon")
                if isinstance(field, list):
                    has_large = any(f.endswith(">large") for f in field)
                    has_small = any(f.endswith(">small") for f in field)
                else:
                    has_large = has_small = False
                if has_large or has_small:
                    if has_large:
                        ul = menu.addAction("📤 上传大图…")
                        ul.triggered.connect(lambda: self._upload_entity_icon_dialog(entity, "large"))
                        dl = menu.addAction("🖼 上传大图（拖拽）")
                        dl.triggered.connect(lambda: self._begin_entity_icon_upload(entity, "large"))
                    if has_small:
                        us = menu.addAction("📤 上传小图…")
                        us.triggered.connect(lambda: self._upload_entity_icon_dialog(entity, "small"))
                        ds = menu.addAction("🖼 上传小图（拖拽）")
                        ds.triggered.connect(lambda: self._begin_entity_icon_upload(entity, "small"))
                else:
                    upload_action = menu.addAction("📤 上传图标…")
                    upload_action.triggered.connect(lambda: self._upload_entity_icon_dialog(entity))
                    drag_action = menu.addAction("🖼 上传图标（拖拽）")
                    drag_action.triggered.connect(lambda: self._begin_entity_icon_upload(entity))
            menu.addSeparator()
            del_action = menu.addAction("🗑 删除实体")
            del_action.triggered.connect(lambda: self._delete_entity(entity))
            menu.addSeparator()
            ent_file = entity.get("file") or self._current_file_path or ""
            explorer_action = menu.addAction("📂 所在文件在资源管理器中显示")
            explorer_action.triggered.connect(
                lambda: self._show_in_explorer(ent_file))
        else:
            if self._current_file_path:
                explorer_action = menu.addAction("📂 打开文件于资源管理器")
                explorer_action.triggered.connect(
                    lambda: self._show_in_explorer(self._current_file_path))
            refresh_action = menu.addAction("🔄 刷新")
            refresh_action.triggered.connect(self.redraw)

        menu.exec(event.globalPos())

    def _open_entity_tree_editor(self, file_path, entity):
        """打开树形编辑器：仅编辑该实体块（如同国策），无块范围时回退整文件+定位。"""
        from generic_tree_editor import GenericTreeEditor
        from tree_node import TreeNode, tree_from_pdx_text
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            file_lines = content.splitlines()

            root = None
            block_range = None
            whole_file = False
            if isinstance(entity, dict):
                ent_range = entity.get("range")
                if ent_range and len(ent_range) == 2 and ent_range[0] >= 0:
                    start_char = ent_range[0]
                    end_char = self._entity_block_end(content, start_char)
                    if end_char > start_char:
                        entity_text = content[start_char:end_char]
                        parsed = tree_from_pdx_text(entity_text)
                        if len(parsed.children) == 1 and parsed.children[0].node_type == "block":
                            # 根节点使用包装容器，其下唯一的子节点为该实体块（与国策编辑一致）
                            wrapper = TreeNode("block", "(entity)")
                            wrapper.add_child(parsed.children[0])
                            root = wrapper
                            block_range = (
                                content[:start_char].count('\n') + 1,
                                content[:end_char].count('\n') + 1,
                            )
            if root is None or block_range is None:
                # 回退：整文件编辑并定位实体
                root = tree_from_pdx_text(content)
                block_range = (1, len(file_lines) + 1)
                whole_file = True

            editor = GenericTreeEditor(
                root_node=root,
                file_path=file_path,
                file_lines=file_lines,
                block_range=block_range,
                translator=_get_translator(),
                custom_statement_path=CUSTOM_STATEMENT_PATH,
                loc_manager=_get_loc_manager(),
                parent=self,
                title="内容编辑",
                hoi4_path=_get_hoi4_path(),
                mod_path=_get_mod_path(),
            )
            editor.tree_saved.connect(self.redraw)
            editor.show()
            if whole_file and isinstance(entity, dict):
                self._locate_entity(editor, entity.get("name", ""))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开树形编辑器: {e}")

    @staticmethod
    def _entity_block_end(content, start_char):
        """返回实体块起始字符对应的平衡右括号结束位置（含 }），未找到返回 -1。

        扫描时跳过双引号字符串与 # 注释，避免花括号被误配对。
        """
        i = content.find("{", start_char)
        if i < 0:
            return -1
        depth = 0
        in_str = False
        n = len(content)
        while i < n:
            c = content[i]
            if in_str:
                if c == '"':
                    in_str = False
                i += 1
                continue
            if c == '"':
                in_str = True
            elif c == "#":
                while i < n and content[i] != "\n":
                    i += 1
                continue
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return -1

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

    def _pick_entity_icon(self, entity):
        """打开图标选择对话框并应用到指定实体。"""
        from icon_picker_dialog import IconPickerDialog
        gfx_map = self._gallery_gfx_map()
        if not gfx_map:
            QMessageBox.warning(self, "错误", "未找到可用图标（请先配置钢铁雄心4目录或打开 mod 目录）")
            return
        dlg = IconPickerDialog(
            gfx_map, translator=_get_translator(), parent=self,
            prefix=(self._entity_cfg or {}).get("picker_prefix", ""),
            current_icon=entity.get("icon") or "",
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            icon_name = dlg.get_selected_icon()
            if icon_name:
                self._set_entity_icon(entity, icon_name)

    def _entity_field_for_slot(self, slot):
        """返回指定槽位对应的写入字段。

        槽位为 slots 配置键（如 advisor_large / general_small）时返回其单个字段路径；
        slot 为 "large"/"small" 时按字段列表过滤；否则返回完整字段。
        """
        cfg = self._entity_cfg or {}
        if slot:
            slots_cfg = cfg.get("slots") or {}
            if slot in slots_cfg:
                return slots_cfg[slot]["field"]
        field = cfg.get("field", "icon")
        if isinstance(field, list) and slot:
            return [f for f in field if f.endswith(f">{slot}")]
        return field

    def _set_entity_icon(self, entity, icon_value, field=None):
        """将图标值写回实体字段并刷新画廊。field 为空时使用类型默认字段。"""
        file_path = entity.get("file") or self._current_file_path
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            start, end = entity["range"]
            if start < 0:
                QMessageBox.warning(self, "错误", "未找到该实体")
                return
            if field is None:
                field = (self._entity_cfg or {}).get("field", "icon")
            new_content = icon_ops.apply_icon_to_entity(content, start, end, field, icon_value)
            icon_ops.write_file_utf8(file_path, new_content)
            self.redraw()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置图标失败: {e}")

    def _upload_entity_icon_dialog(self, entity, slot=None):
        """打开上传图标对话框并应用到指定实体。slot 为 "large"/"small" 时上传到对应槽位。"""
        from icon_upload_dialog import IconUploadDialog
        dlg = IconUploadDialog(entity["name"], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            image_path, icon_name = dlg.get_selection()
            if image_path:
                self._apply_entity_uploaded_icon(entity, image_path, icon_name, slot=slot)

    def _begin_entity_icon_upload(self, entity, slot=None):
        """进入拖拽上传模式：将图片拖到画布即可应用到指定实体的对应槽位。"""
        self._cancel_pending_modes()
        self._pending_entity_icon = entity
        self._pending_entity_icon_slot = slot
        self.setCursor(Qt.CursorShape.DragCopyCursor)
        suffix = f"（{'大图' if slot == 'large' else '小图'}）" if slot else ""
        QMessageBox.information(
            self, "上传图标",
            f"请将图片文件（png/jpg/bmp/dds 等）拖拽到画布上，将应用到实体 '{entity['name']}'{suffix}。")

    def _apply_entity_uploaded_icon(self, entity, image_path, icon_base=None, slot=None):
        """处理上传：生成资源、更新 .gfx、写回实体字段并刷新画廊。"""
        mod_path = _get_mod_path()
        if not mod_path:
            QMessageBox.warning(self, "错误", "请先在菜单「打开mod文件夹」中打开一个 mod 目录")
            return
        icon_base = (icon_base or entity["name"]).strip()
        # 按槽位后缀命名，避免不同槽位覆盖
        if slot:
            slots_cfg = (self._entity_cfg or {}).get("slots") or {}
            icon_base += slots_cfg.get(slot, {}).get("suffix", "") or \
                ("_small" if "small" in slot else "")
        try:
            upload_cfg = (self._entity_cfg or {}).get("upload") or {}
            ref_value = icon_ops.upload_icon(mod_path, image_path, icon_base, upload_cfg)
            self._set_entity_icon(entity, ref_value, field=self._entity_field_for_slot(slot))
            tag = ""
            if slot:
                slots_cfg = (self._entity_cfg or {}).get("slots") or {}
                tag = slots_cfg.get(slot, {}).get("label", slot)
            tag = tag or ("小图" if slot == "small" else "大图" if slot == "large" else "图标")
            QMessageBox.information(self, "成功", f"{tag}已上传到实体 '{entity['name']}'")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"上传图标失败: {e}")

    def _drop_entity_icon(self, event):
        """实体画廊模式下的图标拖放：应用到目标实体（或待上传实体）。"""
        if event.mimeData().hasUrls():
            images = [u.toLocalFile() for u in event.mimeData().urls()
                      if u.toLocalFile() and u.toLocalFile().lower().endswith(
                          ('.png', '.jpg', '.jpeg', '.bmp', '.dds', '.tga'))]
            if images:
                entity = self._get_entity_under(event.pos())
                slot = getattr(self, "_pending_entity_icon_slot", None)
                if entity is None:
                    entity = self._pending_entity_icon
                if entity is None:
                    QMessageBox.warning(
                        self, "错误",
                        "请将图标拖拽到具体的实体上，或先右键实体选择「上传图标（拖拽）」")
                    event.acceptProposedAction()
                    return
                self._cancel_pending_modes()
                self._apply_entity_uploaded_icon(entity, images[0], slot=slot)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _delete_entity(self, entity):
        """从实体所在文件中删除指定实体块并刷新画廊。"""
        file_path = entity.get("file") or self._current_file_path
        if not file_path:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除实体 '{entity['name']}' 吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            start, end = entity["range"]
            if start < 0:
                return
            new_content = content[:start] + content[end:]
            new_content = re.sub(r'\n{3,}', '\n\n', new_content)
            icon_ops.write_file_utf8(file_path, new_content)
            self.redraw()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除实体失败: {e}")

    @staticmethod
    def _show_in_explorer(file_path):
        import subprocess
        import platform
        abs_path = os.path.abspath(file_path)
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", abs_path], check=False)
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", abs_path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(abs_path)], check=False)
