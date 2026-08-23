"""信号槽层（控制器）Mixin：国策/科技/实体画廊的交互编排。

四层分离规范见 AGENTS.md §4.9：
- 本模块只做「接线与编排」：connect、弹窗、调用算法/写文件、刷新 UI/绘图；
- 绘图细节委托给 focus_render.py；算法细节下沉到 focus_algo.py 或已有数据层；
- 不直接持有/拼装 UI 控件（UI 搭建留在 FocusView/独立 View 类）。
"""
from project_paths import PROJECT_ROOT

import os

from PyQt6.QtWidgets import QFileDialog, QMenu, QMessageBox

from focus_render import render_tech_tree


class TechTreeControllerMixin:
    """科技树控制器：负责科技模式的进入、数据装载、重绘编排与右键动作。

    依赖宿主（FocusView）提供的实例状态：
        _tech_data / _tech_files / _tech_gfx_map / _tech_source_files
        _current_file_path / _view_mode / _nofile_entity_list / _entity_items
        以及 _gallery_font()、_cancel_pending_modes()、find_shortcut 等。
    """

    def _tech_init_mode(self):
        """进入科技模式的公共初始化。"""
        self._view_mode = "tech"
        self._nofile_entity_list = None
        self._entity_items = {}
        self._cancel_pending_modes()
        self._current_file_path = None
        self._entity_highlight = None
        self.find_shortcut.setEnabled(False)
        self._tech_data = {}
        self._tech_files = {}
        self._tech_gfx_map = None

    def _load_tech_gfx_map(self):
        """构建科技图标 sprite 映射（mod 优先，游戏兜底）。"""
        from gui_translator import get_translator, scan_gfx_folder
        try:
            g = dict(get_translator().gfx_map)
        except Exception:
            g = {}
        mod = _get_mod_path()
        if mod:
            try:
                scan_gfx_folder(mod, g)
            except Exception:
                pass
        return g

    def _tech_pixmap(self, tech_id):
        """解析科技图标，fallback 链：

        1. GFX_<id>_medium sprite（官方规则，gfx_map 已注册时）
        2. 裸科技 id → 显式搜索 gfx/interface/technologies 目录
           （mod 作者常自由命名 sprite）
        3. None（画「无图标」占位）
        """
        from dds_loader import DdsLoader
        from icon_resolver import resolve_pixmap
        if self._tech_gfx_map is None:
            self._tech_gfx_map = self._load_tech_gfx_map()
        gfx_map = self._tech_gfx_map
        sprite = "GFX_%s_medium" % tech_id
        if sprite in gfx_map:
            pm = resolve_pixmap(
                sprite,
                dirs=["gfx/interface/technologies"],
                gfx_map=gfx_map,
                mod_path=_get_mod_path(),
                hoi4_path=_get_hoi4_path())
            if pm is not None and not pm.isNull():
                return pm
        for base in (_get_mod_path(), _get_hoi4_path()):
            if not base or not os.path.isdir(base):
                continue
            d = os.path.join(base, "gfx", "interface", "technologies")
            if not os.path.isdir(d):
                continue
            try:
                for name in os.listdir(d):
                    stem, ext = os.path.splitext(name)
                    if ext.lower() not in (".png", ".dds", ".jpg", ".jpeg", ".tga"):
                        continue
                    if stem.lower() == tech_id.lower():
                        pm = DdsLoader.load_as_pixmap(os.path.join(d, name))
                        if pm is not None and not pm.isNull():
                            return pm
            except Exception:
                continue
        return None

    def _tech_loc_label(self, tech_id):
        try:
            return _get_loc_manager().get_name(tech_id) or ""
        except Exception:
            return ""

    def show_tech_tree_file(self, file_path):
        """文件模式：在画布绘制指定科技文件的科技树（像国策树）。"""
        self._tech_init_mode()
        self._current_file_path = file_path
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "错误", "科技文件不存在: %s" % file_path)
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "错误", "无法读取科技文件: %s" % e)
            return
        from workbench import WorkbenchDock
        techs = WorkbenchDock._quick_tech_scan(content)
        for tid in techs:
            techs[tid]["file"] = file_path
            self._tech_files[tid] = file_path
        self._tech_data = techs
        self._redraw_tech_tree()
        self._tech_source_files = [file_path]

    def show_tech_tree_nofile(self, files):
        """无文件模式：跨文件合并绘制全部科技树（无国家概念）。"""
        self._tech_init_mode()
        files = [f for f in files if f and os.path.isfile(f)]
        merged = {}
        from workbench import WorkbenchDock
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    content = f.read()
                data = WorkbenchDock._quick_tech_scan(content)
                for tid, node in data.items():
                    if tid not in merged:
                        node["file"] = fp
                        merged[tid] = node
                        self._tech_files[tid] = fp
            except Exception:
                continue
        self._tech_data = merged
        self._tech_source_files = files
        self._redraw_tech_tree()

    def _tech_file_for(self, tech_id):
        """返回科技所在文件（画布映射优先，其次当前文件）。"""
        if tech_id in self._tech_files:
            return self._tech_files[tech_id]
        return self._current_file_path

    def _redraw_tech_tree(self):
        """重绘科技树（文件模式 / 无文件模式共用）。

        绘图细节委托给 focus_render.render_tech_tree。
        """
        tree_ids, non_tree_ids = render_tech_tree(
            self.scene(),
            self._tech_data or {},
            getattr(self, "_tech_files", {}) or {},
            self._current_file_path,
            getattr(self, "_tech_source_files", None) or [],
            self._tech_pixmap,
            self._tech_loc_label,
            self._gallery_font,
        )
        self._tree_ids = tree_ids
        self._non_tree_ids = non_tree_ids
        rect = self.scene().itemsBoundingRect().adjusted(-100, -60, 100, 100)
        self.scene().setSceneRect(rect)
        self.centerOn(rect.center())

    def _show_tech_context_menu(self, event):
        """科技模式右键菜单：上传图标 / 打开定义文件。"""
        item = self.itemAt(event.pos())
        if item is None or not item.data(0):
            return
        tech_id = item.data(0)
        file_path = item.data(1) or self._tech_file_for(tech_id)
        menu = QMenu(self)
        act_upload = menu.addAction("🖼 上传科技图标…")
        act_open = menu.addAction("✏ 编辑科技词条…")
        act_explorer = menu.addAction("📂 在资源管理器中显示文件")
        act = menu.exec(event.globalPos())
        if act is None:
            return
        if act == act_upload:
            self._upload_tech_icon_for(tech_id)
        elif act == act_open:
            self._open_tech_in_editor(file_path, tech_id)
        elif act == act_explorer:
            self._show_tech_in_explorer(file_path)

    def _upload_tech_icon_for(self, tech_id):
        """上传科技图标：等比缩放存 PNG，自动注册 GFX_<id>_medium（程序写 gfx）。"""
        mod = _get_mod_path()
        if not mod or not os.path.isdir(mod):
            QMessageBox.warning(self, "错误", "请先在菜单「打开mod文件夹」中打开一个 mod 目录")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择科技 '%s' 的图标图片" % tech_id,
            "", "图片 (*.png *.jpg *.jpeg *.bmp *.dds *.tga *.webp)")
        if not path:
            return
        try:
            from tech_icon_ops import upload_tech_icon
            info = upload_tech_icon(mod, tech_id, path)
            self._tech_gfx_map = None  # 强制重建 sprite 映射
            from icon_resolver import clear_cache
            clear_cache()
            self._redraw_tech_tree()
            where = ("更新已注册 sprite" if info["updated_existing"]
                     else "新增 sprite 注册")
            QMessageBox.information(
                self, "上传成功",
                "科技 '%s' 图标已上传\n"
                "图片: %s（%s×%s）\n"
                "sprite: %s\n"
                "gfx 文件: %s（%s）\n"
                "科技定义文件无需修改（引擎按 GFX_<id>_medium 查找）"
                % (tech_id, info['texture_rel'], info['width'], info['height'],
                   info['sprite_name'], info['gfx_file'], where))
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", "上传科技图标失败: %s" % e)

    def _open_tech_in_editor(self, file_path, tech_id):
        """打开科技专用编辑器并定位该科技；保存后回调刷新画布。"""
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "提示", "未找到科技定义文件")
            return
        win = self.window()
        try:
            from tech_editor_dialog import open_tech_editor
            dlg = open_tech_editor(
                _get_mod_path(), _get_hoi4_path(),
                file_path=file_path, tech_id=tech_id, parent=win)
            dlg.saved.connect(lambda: self._refresh_tech_tree_after_save(file_path))
        except Exception as e:
            QMessageBox.critical(self, "错误", "打开科技编辑器失败: %s" % e)

    def _refresh_tech_tree_after_save(self, file_path):
        """科技编辑器保存后：重新读取该文件并重绘科技树画布。"""
        if self._view_mode != "tech":
            return
        try:
            with open(file_path, 'r', encoding='utf-8-sig',
                      errors='ignore') as f:
                content = f.read()
            from workbench import WorkbenchDock
            data = WorkbenchDock._quick_tech_scan(content)
            for tid in data:
                data[tid]["file"] = file_path
                self._tech_files[tid] = file_path
            self._tech_data = data
            self._redraw_tech_tree()
        except Exception:
            import traceback
            traceback.print_exc()

    @staticmethod
    def _show_tech_in_explorer(file_path):
        import subprocess
        if not file_path:
            return
        subprocess.Popen(["explorer", "/select,", os.path.normpath(file_path)])


def _get_settings():
    """读取最新的 settings.json 配置（与 focus_view 原实现保持一致）。"""
    import json
    settings = {}
    settings_path = os.path.join(PROJECT_ROOT, "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            pass
    return settings


def _get_hoi4_path():
    return _get_settings().get("HOI4_path", "")


def _get_mod_path():
    return _get_settings().get("mod_path", "")


def _get_loc_manager():
    from localization_mgr import get_localization_manager
    return get_localization_manager()


class EntityGalleryControllerMixin:
    """实体画廊控制器：负责画廊进入/重绘/查找/增删改/图标/本地化编排。
    
    绘图细节委托给 focus_render；算法细节下沉到 focus_algo/entity_scanner。
    """

    def show_entity_gallery(self, content_type, file_path):
        """在右侧国策组件中展示指定文件的实体图标画廊。

        每个实体显示 图标缩略图 + 名称（中文名）。双击实体打开树形编辑器，
        右键提供 编辑/选择图标/上传图标/删除 等操作。
        非图标型内容类型（无 ICON_RULES 配置）同样展示实体（占位图标 + 名称，
        图标值经全局 gfx 索引兜底解析）。
        """
        from workbench import WorkbenchDock, ICON_RULES
        cfg = ICON_RULES.get(content_type)
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read()
        except Exception:
            QMessageBox.critical(self, "错误", f"无法读取文件: {file_path}")
            return
        # 用通用提取：图标型取带图标实体，非图标型取通用实体（含 icon/picture 探测）
        entities = WorkbenchDock._collect_file_entities(content_type, content, file_path)
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


    def clear_entity_gallery(self):
        """清空实体画廊，回到空白场景（用于退出无文件模式时避免残留跨文件实体）。"""
        self._nofile_entity_list = None
        self._nofile_files = []
        # 清空无文件模式国策树状态
        self._nofile_focus_data = None
        self._nofile_focus_files = {}
        self._nofile_focus_title_item = None
        self._nofile_focus_country = ""
        self._entity_items = {}
        self._view_mode = "focus"
        self._current_file_path = None
        self._pending_entity_icon = None
        self._entity_highlight = None
        self.find_shortcut.setEnabled(False)
        self.scene().clear()
        self.resetTransform()


    def _render_entity_gallery(self, content_type, cfg, entities, file_path):
        """实体画廊统一渲染；file_path 为 None 表示无文件模式（实体携带 file 键）。

        cfg 可为 None（非图标型内容类型）：使用占位图标渲染，图标字段值
        经全局 gfx 索引兜底解析。
        """
        cfg = cfg or {}
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


    def _add_new_entity_to(self, file_path):
        """在指定文件中追加一个新实体块，写入并打开树形编辑器定位。

        优先使用系统模板的「项目模板」（节点级骨架）生成块，
        无模板时回退到内置最小块；创建成功后自动补充本地化词条。
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
            new_content = self._insert_entity_block(file_path, self._entity_type, block)
            icon_ops.write_file_utf8(file_path, new_content)

            # 刷新画廊并打开树形编辑器定位到新实体
            if self._nofile_entity_list is not None:
                self._reload_nofile_gallery()
            else:
                self.show_entity_gallery(self._entity_type, file_path)
            new_ent = None
            for e in WorkbenchDock._collect_file_entities(
                    self._entity_type, new_content, file_path):
                if e["name"] == key:
                    new_ent = e
                    break
            # 无文件模式：自动为新建实体补充本地化词条（名称=实体id，占位）
            if new_ent is not None and self._nofile_entity_list is not None:
                self._ensure_entity_localization(key)
            if new_ent:
                self._open_entity_tree_editor(file_path, new_ent)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"新建实体失败: {e}")


    def _move_copy_entity_to_file(self, entity, copy_mode=False):
        """移动/复制实体到其他文件（无文件模式）。

        copy_mode=False 为移动（源文件删除该块），True 为复制。
        """
        if self._nofile_entity_list is None:
            return
        source = entity.get("file") or ""
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, "错误", "未找到实体所在文件")
            return
        block = self._entity_block_text(entity)
        if not block:
            QMessageBox.warning(self, "错误", "无法提取实体块文本")
            return
        action = "复制实体" if copy_mode else "移动实体"
        target = self._choose_nofile_target_file(
            exclude=source, action_text=action)
        if not target:
            return
        try:
            # 先写目标，再删源（移动）；复制仅写目标
            new_content = self._insert_entity_block(target, self._entity_type, block)
            icon_ops.write_file_utf8(target, new_content)
            if not copy_mode:
                src_content = self._entity_block_text_source(source, entity)
                icon_ops.write_file_utf8(source, src_content)
            self._reload_nofile_gallery()
            QMessageBox.information(
                self, "成功",
                f"实体 '{entity['name']}' 已{'复制到' if copy_mode else '移动到'}: "
                f"{os.path.basename(target)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"{action}失败: {e}")


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

            # 图标操作仅在配置了图标规则的类型提供
            if self._entity_cfg:
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
            loc_action = menu.addAction("✍ 编辑本地化名称/描述…")
            loc_action.triggered.connect(lambda: self._edit_entity_localization(entity))
            if self._nofile_entity_list is not None:
                copy_action = menu.addAction("⧉ 复制到其他文件…")
                copy_action.triggered.connect(
                    lambda: self._move_copy_entity_to_file(entity, copy_mode=True))
                move_action = menu.addAction("➡ 移动到其他文件…")
                move_action.triggered.connect(
                    lambda: self._move_copy_entity_to_file(entity, copy_mode=False))
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


    def _set_entity_icon(self, entity, icon_value, field=None):
        """将图标值写回实体字段并刷新画廊。field 为空时使用类型默认字段。

        民族精神等 picture 字段按游戏约定存储裸名（游戏加载时自动补 GFX_idea_ 前缀），
        故写回前对带 GFX_idea_ 前缀的值去掉该前缀。
        """
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
            cfg = self._entity_cfg or {}
            write_value = icon_value
            if cfg.get("picture_unprefixed") and write_value.startswith("GFX_idea_"):
                write_value = write_value[len("GFX_idea_"):]
            new_content = icon_ops.apply_icon_to_entity(content, start, end, field, write_value)
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
            if upload_cfg.get("tech_special"):
                # 科技特殊流程：图标不写入科技定义文件（引擎按
                # GFX_<id>_medium 解析），保留原尺寸比例上传并自动注册 gfx
                from tech_icon_ops import upload_tech_icon
                info = upload_tech_icon(mod_path, entity["name"], image_path)
                ref_value = info["sprite_name"]
            else:
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

    # 内容类型 -> 保存本地化词条时写入的 mod 翻译文件名
    _LOC_FILE_FOR_TYPE = {
        "focus": "focus_mod_l_simp_chinese.yml",
        "idea": "ideas_mod_l_simp_chinese.yml",
        "decision": "decision_mod_l_simp_chinese.yml",
        "event": "event_mod_l_simp_chinese.yml",
        "super_event": "event_mod_l_simp_chinese.yml",
        "tech": "tech_mod_l_simp_chinese.yml",
        "character": "character_mod_l_simp_chinese.yml",
        "country_history": "country_history_mod_l_simp_chinese.yml",
    }


    def _loc_file_for_type(self):
        """返回当前类型对应的 mod 翻译文件名（未知类型用通用文件）。"""
        return self._LOC_FILE_FOR_TYPE.get(
            self._entity_type or "", "generic_mod_l_simp_chinese.yml")


    def _loc_save_dir(self):
        """返回 mod 本地化保存目录（mod/localisation/simp_chinese）。"""
        mod = _get_mod_path()
        if not mod:
            return ""
        return os.path.join(mod, "localisation", "simp_chinese")


    def _edit_entity_localization(self, entity):
        """编辑实体本地化名称/描述（写入 mod 翻译文件，不修改游戏文件）。"""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                     QLineEdit, QPushButton)
        from translation_editor import get_translation_editor

        name_key = entity["name"]
        mod_dir = self._loc_save_dir()
        if not mod_dir:
            QMessageBox.warning(self, "错误", "请先在菜单「打开mod文件夹」中打开一个 mod 目录")
            return
        te = get_translation_editor(
            hoi4_loc_path=os.path.join(_get_hoi4_path(), "localisation", "simp_chinese")
            if _get_hoi4_path() else "",
            mod_loc_path=mod_dir,
            mod_file_name=self._loc_file_for_type())
        try:
            te.reload()
        except Exception:
            pass

        dlg = QDialog(self)
        dlg.setWindowTitle(f"本地化：{name_key}")
        dlg.resize(480, 180)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(f"实体：{name_key}（写入 {os.path.basename(self._loc_file_for_type())}）"))
        name_edit = QLineEdit(te.get_name(name_key))
        name_edit.setPlaceholderText("名称（留空则不写入）")
        lay.addWidget(QLabel("名称："))
        lay.addWidget(name_edit)
        desc_edit = QLineEdit(te.get_desc(name_key))
        desc_edit.setPlaceholderText("描述（留空则不写入）")
        lay.addWidget(QLabel("描述："))
        lay.addWidget(desc_edit)
        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存")
        close_btn = QPushButton("关闭")
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        def do_save():
            name_val = name_edit.text().strip()
            desc_val = desc_edit.text().strip()
            if name_val:
                te.save_name(name_key, name_val)
            if desc_val:
                te.save_desc(name_key, desc_val)
            if not name_val and not desc_val:
                QMessageBox.information(self, "提示", "名称与描述均为空，未写入任何内容")
                return
            # 词条已保存到翻译文件，刷新画廊显示的中文名
            try:
                loc = _get_loc_manager()
                if loc is not None:
                    loc.reload(game_path=_get_hoi4_path(), mod_path=_get_mod_path())
            except Exception:
                pass
            self.redraw()
            QMessageBox.information(self, "成功", f"本地化已保存：{name_key}")
            dlg.accept()

        save_btn.clicked.connect(do_save)
        close_btn.clicked.connect(dlg.reject)
        dlg.exec()


    def _ensure_entity_localization(self, key):
        """为新建实体自动补充本地化词条（名称=实体id 占位），无文件模式创建后调用。"""
        mod_dir = self._loc_save_dir()
        if not mod_dir:
            return
        try:
            from translation_editor import get_translation_editor
            te = get_translation_editor(
                hoi4_loc_path=os.path.join(_get_hoi4_path(), "localisation", "simp_chinese")
                if _get_hoi4_path() else "",
                mod_loc_path=mod_dir,
                mod_file_name=self._loc_file_for_type())
            te.reload()
            if not te.get_name(key):
                te.save_name(key, key)
        except Exception:
            pass


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

    def _get_entity_under(self, pos):
        """返回点击位置对应的实体字典，未命中返回 None。"""
        item = self.itemAt(pos)
        if item is not None and item.data(2):
            return item.data(2)
        return None

