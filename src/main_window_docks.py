"""主窗口 Dock/文件树/工作台装配 Mixin（F5 拆分自 main_window.py）。

仅含文件树交互、经典/工作台模式切换、工作台信号接线与通用文件分发；
主窗口仍负责菜单、设置、工具入口与 AI 内容生成。
"""

from __future__ import annotations

import json
import os

from PyQt6.QtCore import Qt, QFileInfo, QTimer
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox

from focus_view import CUSTOM_STATEMENT_PATH, FocusView
from pdx_parser import parse_pdx_script
from ui_untitled import Ui_MainWindow


class MainWindowDocksMixin:
    """文件树 + Dock + 画布装配的公共方法集合。"""

    def _sync_gfx_to_renderer(self):
        """同步图标映射（gfx_map）到渲染器，使其能正确显示科技/国策图标。

        同时合并游戏目录和 mod 目录中的图标定义与 mod 路径。
        """
        from gui_translator import get_translator, _default_translator, scan_gfx_folder
        hoi4 = self.settings.get("HOI4_path", "")
        mod = self.settings.get("mod_path", "")
        loc_path = os.path.join(hoi4, "localisation", "simp_chinese") if hoi4 else ""
        # 复用已有翻译器实例或创建新实例（同时加载游戏与 mod 本地化）
        if _default_translator is not None:
            _default_translator.reload(loc_path, hoi4_path=hoi4, mod_path=mod)
            combined = dict(_default_translator.gfx_map)
        else:
            trans = get_translator(loc_path, hoi4_path=hoi4, mod_path=mod)
            combined = dict(trans.gfx_map)
        # 合并 mod 目录中的图标定义（如上传的自定义图标）
        if mod:
            scan_gfx_folder(mod, combined)
        self.renderer.set_gfx_map(combined)
        self.renderer.set_mod_path(mod)


    def _sync_loc_manager(self):
        """同步本地化管理器：重新加载游戏和 mod 的本地化文本。"""
        from localization_mgr import get_localization_manager, _manager
        hoi4 = self.settings.get("HOI4_path", "")
        mod = self.settings.get("mod_path", "")
        if _manager is not None:
            _manager.reload(game_path=hoi4, mod_path=mod)
        else:
            mgr = get_localization_manager()
            if hoi4:
                mgr.add_game_path(hoi4)
            if mod:
                mgr.add_mod_path(mod)
        # 确保渲染器持有最新的本地化管理器引用
        self.renderer.set_loc_manager(get_localization_manager())


    def show_context_menu(self, pos):
        """在文件树指定位置弹出右键菜单，提供新建、解析、删除等操作。"""
        index = self.ui.tree.indexAt(pos)
        menu = QMenu(self)

        if index.isValid():
            # 已选中文件或文件夹
            file_path = self.model.filePath(index)
            file_info = QFileInfo(file_path)
            is_dir = file_info.isDir()
            is_txt = file_info.suffix().lower() == 'txt'

            if is_dir:
                # --- 文件夹右键菜单 ---
                new_file_action = menu.addAction("新建文件")
                new_file_action.triggered.connect(lambda: self._create_new_file(file_path))
                new_template_file_action = menu.addAction("从模板新建文件")
                new_template_file_action.triggered.connect(lambda: self._create_new_file_from_template(file_path))
                new_dir_action = menu.addAction("新建文件夹")
                new_dir_action.triggered.connect(lambda: self._create_new_folder(file_path))
            else:
                # --- 文件右键菜单 ---
                new_file_action = menu.addAction("新建文件")
                new_file_action.triggered.connect(lambda: self._create_new_file(
                    file_info.absolutePath()))
                new_template_file_action = menu.addAction("从模板新建文件")
                new_template_file_action.triggered.connect(lambda: self._create_new_file_from_template(
                    file_info.absolutePath()))
                new_dir_action = menu.addAction("新建文件夹")
                new_dir_action.triggered.connect(lambda: self._create_new_folder(
                    file_info.absolutePath()))
                menu.addSeparator()
                if is_txt:
                    info_action = menu.addAction("编辑树基本信息")
                    info_action.triggered.connect(lambda: self._edit_tree_info(file_path))

            menu.addSeparator()
            # 删除文件
            if not is_dir:
                delete_action = menu.addAction("🗑 删除文件")
                delete_action.triggered.connect(lambda: self._delete_file(file_path))
            else:
                delete_action = menu.addAction("🗑 删除文件夹")
                delete_action.triggered.connect(lambda: self._delete_folder(file_path))

            # 在资源管理器中显示
            menu.addSeparator()
            show_in_explorer_action = menu.addAction("📂 在资源管理器中显示")
            show_in_explorer_action.triggered.connect(lambda: self._show_in_explorer(file_path))

            menu.addSeparator()
            menu.addAction(f"名称: {self.model.fileName(index)}")
        else:
            # 空白区域右键菜单
            new_file_action = menu.addAction("新建文件")
            new_file_action.triggered.connect(lambda: self._create_new_file(self.settings["mod_path"]))
            new_template_file_action = menu.addAction("从模板新建文件")
            new_template_file_action.triggered.connect(lambda: self._create_new_file_from_template(self.settings["mod_path"]))
            new_dir_action = menu.addAction("新建文件夹")
            new_dir_action.triggered.connect(lambda: self._create_new_folder(self.settings["mod_path"]))
            menu.addSeparator()
            refresh_action = menu.addAction("刷新目录")
            refresh_action.triggered.connect(self._refresh_tree)

        # 将菜单位置从控件坐标转换为全局坐标后弹出
        global_pos = self.ui.tree.viewport().mapToGlobal(pos)
        menu.exec(global_pos)


    def _create_new_file_from_template(self, directory):
        """从模板新建文件：打开模板对话框选择模板，输入文件名后创建到指定目录。"""
        from template_scheduler import get_template_scheduler
        from template_dialog import TemplateDialog

        scheduler = get_template_scheduler()
        dlg = TemplateDialog(scheduler, parent=self)
        dlg.setWindowTitle("从模板新建文件")

        def on_template_ok():
            template_data = dlg.get_template_data()
            if not template_data:
                dlg.deleteLater()
                return
            # 输入新文件名（不含扩展名，扩展名取自模板）
            name, ok = QInputDialog.getText(self, "新建文件", "输入文件名（不含扩展名）:")
            if not ok or not name.strip():
                dlg.deleteLater()
                return
            ext = os.path.splitext(template_data["filename"])[1] or ".txt"
            new_path = os.path.join(directory, f"{name.strip()}{ext}")
            if os.path.exists(new_path):
                QMessageBox.warning(self, "错误", f"文件已存在: {new_path}")
                dlg.deleteLater()
                return
            # 模板变量已在模板对话框内填写，优先使用替换后的内容
            applied = dlg.get_applied_content()
            if applied is not None:
                success = scheduler.apply_template(template_data["filepath"], new_path)
                if success:
                    try:
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        from write_utils import atomic_write_text
                        atomic_write_text(new_path, applied, undo=False)
                    except Exception:
                        success = False
            else:
                success = scheduler.apply_template(template_data["filepath"], new_path)
            dlg.deleteLater()
            if success:
                self._refresh_tree()
            else:
                QMessageBox.critical(self, "错误", "从模板创建文件失败")

        dlg.accepted.connect(on_template_ok)
        dlg.show()


    def _delete_file(self, file_path):
        """删除指定文件（含确认对话框）。"""
        reply = QMessageBox.question(self, "确认删除", f"确定要删除文件 '{os.path.basename(file_path)}' 吗？\n此操作不可撤销。")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(file_path)
                self._refresh_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除文件失败: {e}")


    def _delete_folder(self, folder_path):
        """递归删除指定文件夹（含确认对话框）。"""
        import shutil
        reply = QMessageBox.question(self, "确认删除", f"确定要删除文件夹 '{os.path.basename(folder_path)}' 及其所有内容吗？\n此操作不可撤销。")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(folder_path)
                self._refresh_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除文件夹失败: {e}")


    def _show_in_explorer(self, file_path):
        """在系统文件资源管理器中定位并显示指定文件/文件夹。"""
        import subprocess
        import platform
        abs_path = os.path.abspath(file_path)
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", abs_path], check=False)
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", abs_path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(abs_path)], check=False)


    def _edit_tree_info(self, file_path):
        """打开国策树基本信息编辑对话框（树标题、备注等）。"""
        from tree_info_dialog import TreeHeaderEditor
        from gui_translator import get_translator
        from localization_mgr import get_localization_manager
        translator = get_translator()
        loc_manager = get_localization_manager()
        dialog = TreeHeaderEditor(file_path, translator=translator, loc_manager=loc_manager, parent=self)
        dialog.tree_saved.connect(self._refresh_tree)
        dialog.show()


    def _create_new_file(self, directory):
        """在指定目录下创建空白 .txt 文件（弹出输入对话框）。"""
        name, ok = QInputDialog.getText(self, "新建文件", "输入文件名:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if not os.path.splitext(name)[1]:
            name += ".txt"                           # 无扩展名时默认补 .txt
        file_path = os.path.join(directory, name)
        if os.path.exists(file_path):
            QMessageBox.warning(self, "错误", f"文件已存在: {file_path}")
            return
        try:
            from write_utils import atomic_write_text
            atomic_write_text(file_path, "", undo=False)   # 创建空文件
            self._refresh_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建文件失败: {e}")


    def _create_new_folder(self, directory):
        """在指定目录下创建新文件夹（弹出输入对话框）。"""
        name, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名:")
        if not ok or not name.strip():
            return
        name = name.strip()
        folder_path = os.path.join(directory, name)
        if os.path.exists(folder_path):
            QMessageBox.warning(self, "错误", f"文件夹已存在: {folder_path}")
            return
        try:
            os.makedirs(folder_path)
            self._refresh_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建文件夹失败: {e}")


    def _refresh_tree(self):
        """刷新文件树视图，使其重新加载当前 mod 目录。"""
        directory = self.settings["mod_path"]
        if directory:
            self.model.setRootPath(directory)
            self.ui.tree.setRootIndex(self.model.index(directory))


    def on_tree_doubleClicked(self, index):
        """文件树双击事件：文本类文件解析打开（国策→设计视图，其余→树形编辑器）。"""
        if not index.isValid(): return
        file_path = self.model.filePath(index)
        file_info = QFileInfo(file_path)
        if not file_info.isFile():
            return
        suffix = file_info.suffix().lower()
        if suffix in ("txt", "gui", "lua", "mod", "yml", "yaml", "gfx", "asset", "csv"):
            self.load_txt_pdx_to_memory(file_path)


    def load_txt_pdx_to_memory(self, file_path):
        """读取并解析 PDX 脚本文件，若为国策树则渲染到图形场景，否则打开树形编辑器。"""
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            raw_data = parse_pdx_script(content)     # 使用 PDX 解析器解析文本

            # 判断文件是否包含国策树定义
            if 'focus_tree' in raw_data or 'shared_focus' in raw_data or 'joint_focus' in raw_data:
                self.custom_view._view_mode = "focus"
                focus_data = self.processor.process(raw_data)  # 将原始数据转换为统一国策格式
                self.renderer.draw_graph(focus_data, file_path)  # 在场景中绘制国策树
                self.custom_view._current_file_path = file_path
            else:
                # 初始部队文件（history/units）→ 直接打开师编制设计器（顶部可调地编）
                norm = os.path.normpath(file_path).replace("\\", "/")
                if "/history/units/" in norm or norm.endswith("/history/units"):
                    from initial_oob_editor import open_oob_designer
                    open_oob_designer(
                        file_path,
                        mod_path=self.settings.get("mod_path", ""),
                        hoi4_path=self.settings.get("HOI4_path", ""),
                        parent=self)
                else:
                    # 其余文本文件 → 树形编辑器（覆盖国策以外的全部类型）
                    self._open_tree_editor(file_path, None)

        except Exception as e:
            print(f"读取或解析文件时发生错误: {e}")

    # ---------- 界面模式（经典文件树 / 工作台） ----------


    def _init_ui_mode(self):
        """初始化界面模式：经典文件树 / 工作台（无文件模式由工具栏切换），持久化到 settings.json。"""
        self.ui.action_mode_classic.setChecked(False)
        self.ui.action_mode_workbench.setChecked(False)
        saved_mode = self.settings.get("ui_mode", "classic")
        if saved_mode == "nofile":
            # 旧版本「无文件模式」菜单项已移除，迁移为工作台模式（默认不启用无文件模式）
            self.ui.action_mode_workbench.setChecked(True)
            self._show_workbench_mode(nofile=False)
        elif saved_mode == "workbench":
            self.ui.action_mode_workbench.setChecked(True)
            self._show_workbench_mode(
                nofile=bool(self.settings.get("workbench_nofile", False)))
        else:
            self.ui.action_mode_classic.setChecked(True)
            self._show_classic_mode()

        self.ui.action_mode_classic.triggered.connect(
            lambda: self._set_ui_mode("classic"))
        self.ui.action_mode_workbench.triggered.connect(
            lambda: self._set_ui_mode("workbench"))


    def _set_ui_mode(self, mode):
        """切换界面模式并持久化。"""
        if mode == "workbench":
            self.ui.action_mode_classic.setChecked(False)
            self.ui.action_mode_workbench.setChecked(True)
            self._show_workbench_mode(nofile=bool(self.settings.get("workbench_nofile", False)))
        else:
            self.ui.action_mode_classic.setChecked(True)
            self.ui.action_mode_workbench.setChecked(False)
            self._show_classic_mode()
        self.settings["ui_mode"] = mode
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass


    def _show_classic_mode(self):
        """显示经典文件树模式。"""
        if self.workbench_dock is not None:
            self.removeDockWidget(self.workbench_dock)
            self.workbench_dock.hide()
        self.ui.dockWidget.show()


    def _show_workbench_mode(self, nofile=False):
        """显示工作台模式（隐藏经典文件树，显示工作台）；nofile 为无文件模式。"""
        self.ui.dockWidget.hide()
        if self.workbench_dock is None:
            from workbench import WorkbenchDock
            self.workbench_dock = WorkbenchDock(self.settings.get("mod_path", ""), parent=self)
            self.workbench_dock.focus_file_selected.connect(self._on_workbench_focus_file)
            self.workbench_dock.generic_file_selected.connect(self._on_workbench_generic_file)
            self.workbench_dock.force_tree_file_selected.connect(
                self._on_workbench_force_tree_file)
            self.workbench_dock.entity_gallery_requested.connect(self._on_workbench_entity_gallery)
            self.workbench_dock.entity_gallery_nofile_requested.connect(
                self._on_workbench_nofile_gallery)
            self.workbench_dock.nofile_mode_changed.connect(self._on_workbench_nofile_changed)
            self.workbench_dock.country_changed.connect(self._on_workbench_country_changed)
            self.workbench_dock.focus_tree_nofile_requested.connect(
                self._on_workbench_focus_tree_nofile)
            self.workbench_dock.tech_file_selected.connect(
                self._on_workbench_tech_file)
            self.workbench_dock.tech_tree_nofile_requested.connect(
                self._on_workbench_tech_tree_nofile)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.workbench_dock)
        self.workbench_dock.set_mod_path(self.settings.get("mod_path", ""))
        self.workbench_dock.set_nofile_mode(nofile)
        self.workbench_dock.show()


    def _on_workbench_focus_file(self, file_path):
        """工作台：打开国策树文件（复用设计视图）。"""
        self.load_txt_pdx_to_memory(file_path)


    def _on_workbench_entity_gallery(self, content_type, file_path):
        """工作台：在右侧国策组件中展示图标型文件的实体图标画廊。"""
        self.custom_view.show_entity_gallery(content_type, file_path)


    def _on_workbench_nofile_gallery(self, content_type, entities):
        """工作台无文件模式：在右侧国策组件中展示跨文件收集的实体画廊。"""
        self.custom_view.show_entity_gallery_nofile(content_type, entities)


    def _on_toolbar_nofile_toggled(self, checked):
        """无文件模式切换（视图菜单）：同步工作台并持久化。"""
        if self.workbench_dock is not None:
            self.workbench_dock.set_nofile_mode(checked)
        elif checked and self.settings.get("ui_mode") != "workbench":
            # 经典文件树模式下开启无文件模式：先切到工作台
            self._set_ui_mode("workbench")
            if self.workbench_dock is not None:
                self.workbench_dock.set_nofile_mode(True)
        self.settings["workbench_nofile"] = bool(checked)
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass


    def _on_workbench_nofile_changed(self, nofile):
        """工作台无文件模式变化：同步工具栏动作并持久化。"""
        act = getattr(self, "act_nofile_mode", None)
        if act is not None and act.isChecked() != nofile:
            act.setChecked(nofile)
        if not nofile:
            # 退出无文件模式：清空右侧跨文件实体画廊，回到空白场景
            self.custom_view.clear_entity_gallery()
        self.settings["workbench_nofile"] = bool(nofile)
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass


    def _on_workbench_country_changed(self, tag):
        """工作台「当前国家」变化：同步到右侧画廊（新建实体时优先写入该国文件）。"""
        try:
            self.custom_view.set_current_country_hint(tag or None)
        except Exception:
            pass


    def _on_workbench_focus_tree_nofile(self, country, files):
        """无文件模式：在右侧绘制国策树（当前设计中的国家），跨文件合并。"""
        try:
            self.custom_view.show_focus_tree_nofile(country, files)
        except Exception:
            import traceback
            traceback.print_exc()


    def _on_workbench_tech_file(self, file_path):
        """工作台：科技文件 → 在右侧画布绘制科技树（与国策树同一画布）。"""
        try:
            self.custom_view.show_tech_tree_file(file_path)
        except Exception:
            import traceback
            traceback.print_exc()


    def _on_workbench_tech_tree_nofile(self, files):
        """无文件模式：在右侧画布绘制全部科技（跨文件合并）。"""
        try:
            self.custom_view.show_tech_tree_nofile(files)
        except Exception:
            import traceback
            traceback.print_exc()


    def _on_workbench_generic_file(self, file_path, entity_id=None):
        """工作台：打开其他内容文件（复用树形编辑器），可选定位实体。"""
        self._open_tree_editor(file_path, entity_id)


    def _on_workbench_force_tree_file(self, file_path, entity_id=None):
        """工作台右键「打开（树形编辑器）」：强制用通用树形编辑器打开，跳过专用路由。"""
        self._open_generic_tree_editor(file_path, entity_id)


    def _open_tree_editor(self, file_path, entity_id=None):
        """打开指定文件到合适的编辑器：

        - history/units → 初始部队编辑器（编制 + 地图放置）
        - 其余文本文件 → 通用 PDX 树形编辑器（可选定位实体）
        经典文件树双击与工作台双击共用此分发逻辑。
        """
        # 专用编辑器路由：路径子串 → 打开函数（app_routes.py）
        from app_routes import RouteContext, find_route
        mod = self.settings.get("mod_path", "")
        norm, route = find_route(file_path)
        if route is not None:
            try:
                ctx = RouteContext(
                    file_path,
                    mod_path=mod,
                    hoi4_path=self.settings.get("HOI4_path", ""),
                    entity_id=entity_id,
                    parent=self)
                route[1](ctx)
                return
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "错误", "专用编辑器打开失败: %s" % e)
                return
        # 其余文本文件 → 通用 PDX 树形编辑器（可选定位实体）
        self._open_generic_tree_editor(file_path, entity_id)

    def _open_generic_tree_editor(self, file_path, entity_id=None):
        """用通用 PDX 树形编辑器打开文件（跳过专用编辑器路由）。

        供右键「打开（树形编辑器）」强制使用，也作为普通分发无专用路由时的兜底。
        """
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            raw_data = parse_pdx_script(content)
            from tree_node import tree_from_pdx_text
            from generic_tree_editor import GenericTreeEditor
            from gui_translator import get_translator
            from localization_mgr import get_localization_manager

            file_lines = content.splitlines()
            root = tree_from_pdx_text(content)
            from tree_node import attach_verbatim_lines
            attach_verbatim_lines(root, content)  # 保真：原文行（注释/空行/缩进）
            translator = get_translator()
            loc_manager = get_localization_manager()
            hoi4 = self.settings.get("HOI4_path", "")
            mod = self.settings.get("mod_path", "")

            title = "内容编辑"
            if raw_data and any(k in raw_data for k in ("focus_tree", "shared_focus", "joint_focus")):
                title = "国策树编辑"
            editor = GenericTreeEditor(
                root_node=root,
                file_path=file_path,
                file_lines=file_lines,
                block_range=(1, len(file_lines) + 1),
                translator=translator,
                custom_statement_path=CUSTOM_STATEMENT_PATH,
                loc_manager=loc_manager,
                parent=self,
                title=title,
                hoi4_path=hoi4,
                mod_path=mod,
            )
            editor.tree_saved.connect(self._refresh_tree)
            editor.show()
            if entity_id:
                self._locate_entity_in_editor(editor, entity_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"无法打开文件: {e}")


