"""主窗口模块：包含文件浏览、mod 管理、国策树解析与渲染等核心功能。"""
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMenu, QMessageBox, QInputDialog
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QFileInfo, QTimer
from ui_untitled import Ui_MainWindow
import json
import os
from focus_view import FocusView
from focus_view import CUSTOM_STATEMENT_PATH
from pdx_parser import parse_pdx_script
from focus_processor import FocusProcessor
from focus_renderer import FocusRenderer, FocusScene
import os as _os


class MyWindow(QMainWindow):
    """应用主窗口，负责 UI 初始化、设置管理、文件树交互、国策树解析与绘制。"""

    def __init__(self):
        """初始化主窗口：加载 UI、读取/创建配置、初始化子模块、绑定信号与菜单。"""
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ---------- 配置项初始化 ----------
        self.settings ={}
        self.settings["HOI4_path"] = ''              # 钢铁雄心4 游戏根目录
        self.settings["mod_path"] = ''               # 当前打开的 mod 目录
        self.settings["mod_folder_path"] = ''        # 默认 mod 目录（存放 mod 内容子文件夹）
        self.settings["mod_file_path"] = ''          # .mod 文件目录（只存放 .mod 描述文件）
        self.settings["ui_mode"] = 'classic'         # 界面模式：classic 经典文件树 / workbench 工作台
        self.settings["workbench_nofile"] = False    # 工作台无文件模式（实体浏览）

        # 读取持久化配置（如果存在）
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
            # 逐个字段安全读取，避免 KeyError
            try:
                self.settings["HOI4_path"] = data["HOI4_path"]
            except (KeyError, TypeError):
                self.settings["HOI4_path"] = ''
            try:
                self.settings["mod_path"] = data["mod_path"]
            except (KeyError, TypeError):
                self.settings["mod_path"] = ''
            try:
                self.settings["mod_folder_path"] = data["mod_folder_path"]
            except (KeyError, TypeError):
                self.settings["mod_folder_path"] = ''
            try:
                self.settings["mod_file_path"] = data["mod_file_path"]
            except (KeyError, TypeError):
                self.settings["mod_file_path"] = ''
            try:
                self.settings["ui_mode"] = data["ui_mode"]
            except (KeyError, TypeError):
                self.settings["ui_mode"] = 'classic'
            try:
                self.settings["workbench_nofile"] = bool(data.get("workbench_nofile", False))
            except Exception:
                self.settings["workbench_nofile"] = False
        else:
            # 文件不存在则创建默认配置
            data = {}
            data["HOI4_path"] = ''
            data["mod_path"] = ''
            data["mod_folder_path"] = ''
            data["mod_file_path"] = ''
            data["ui_mode"] = 'classic'
            data["workbench_nofile"] = False
            with open('settings.json','w',encoding='utf-8') as f:
                json.dump(data,f,indent=4, ensure_ascii=False)

        # 校验目录字段：配置的目录不存在则清空，避免空界面误导
        _changed = False
        for _key in ("HOI4_path", "mod_path", "mod_folder_path", "mod_file_path"):
            _val = self.settings.get(_key, "")
            if _val and not os.path.isdir(_val):
                self.settings[_key] = ""
                _changed = True
        if _changed:
            try:
                with open('settings.json', 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4, ensure_ascii=False)
            except Exception:
                pass


        # --- 初始化子模块 ---
        self.processor = FocusProcessor()            # 国策数据处理器

        # 换用我们自定义的带网格的 Scene
        self.scene = FocusScene()                    # 自定义场景（含网格背景）
        self.custom_view = FocusView(self.scene, self)  # 自定义视图（支持缩放、拖拽）
        self.renderer = FocusRenderer(self.scene)    # 国策树渲染器

        # 如果布局已存在，隐藏原始 graphicsView 并替换为 custom_view
        if self.ui.centralwidget.layout():
            self.ui.graphicsView.hide()
            self.ui.centralwidget.layout().addWidget(self.custom_view)

        # ---------- 文件系统模型与树形视图 ----------
        self.model = QFileSystemModel(self)          # Qt 文件系统模型
        # 菜单栏信号绑定
        self.ui.mod_opener.triggered.connect(self.on_mod_opener_clicked)
        self.ui.mod_creater.triggered.connect(self.on_mod_creater_clicked)
        self.ui.hoi4_path_choose.triggered.connect(self.on_hoi4_path_choose_clicked)
        self.ui.modfolder_choose.triggered.connect(self.on_modfolder_choose_clicked)
        self.ui.mod_file_choose.triggered.connect(self.on_modfile_choose_clicked)
        # 文件菜单：首次使用配置向导
        self.act_setup_wizard = self.ui.menu.addAction("配置向导…")
        self.act_setup_wizard.triggered.connect(self.on_setup_wizard)

        # ---------- 界面模式（经典文件树 / 工作台） ----------
        self.workbench_dock = None
        self._init_ui_mode()

        # ---------- AI 助手菜单 ----------
        self.ui.action_ai_prompt_file.triggered.connect(self.on_ai_prompt_file)
        self.ui.action_ai_prompt_project.triggered.connect(self.on_ai_prompt_project)
        self.ui.action_manage_terms.triggered.connect(self.on_manage_terms)

        # ---------- 工具工具栏 ----------
        # 工具操作已收拢到菜单：模板/词条管理（配置菜单）、无文件模式（视图菜单）、
        # 校验 mod（工具菜单）。这里仅做菜单动作的信号连接。
        self.act_nofile_mode = self.ui.action_nofile_mode
        self.act_manage_templates = self.ui.action_manage_templates
        self.act_manage_terms = self.ui.action_manage_terms
        self.act_validate_mod = self.ui.action_validate_mod
        self.act_manage_templates.triggered.connect(self.on_manage_templates)
        self.act_manage_terms.triggered.connect(self.on_manage_terms)
        self.act_nofile_mode.toggled.connect(self._on_toolbar_nofile_toggled)
        self.act_validate_mod.triggered.connect(self.on_validate_mod)
        # 工具菜单：动作由 menu_factory 统一构建（UI 层），这里只做信号连接（信号槽层）
        from menu_factory import build_tool_actions
        _tool_actions = build_tool_actions(self.ui.menu_tools)
        self.act_coverage_report = _tool_actions["coverage_report"]
        self.act_coverage_report.triggered.connect(self.on_coverage_report)
        self.act_health_check = _tool_actions["health_check"]
        self.act_health_check.triggered.connect(self.on_health_check)
        self.act_map_editor = _tool_actions["map_editor"]
        self.act_map_editor.triggered.connect(self.on_map_editor)
        self.act_region_editor = _tool_actions["region_editor"]
        self.act_region_editor.triggered.connect(self.on_region_editor)
        self.act_overlay_report = _tool_actions["overlay_report"]
        self.act_overlay_report.triggered.connect(self.on_overlay_report)
        self.act_icon_manifest = _tool_actions["icon_manifest"]
        self.act_icon_manifest.triggered.connect(self.on_icon_manifest)
        self.act_unit_counters = _tool_actions["unit_counters"]
        self.act_unit_counters.triggered.connect(self.on_unit_counters)
        self.act_undo_write = _tool_actions["undo_write"]
        self.act_undo_write.triggered.connect(self.on_undo_last_write)
        self.act_game_reference = _tool_actions["game_reference"]
        self.act_game_reference.triggered.connect(self.on_game_reference)
        self.act_ai_assist = _tool_actions["ai_assist"]
        self.act_ai_assist.triggered.connect(self.on_ai_assist)
        self.act_ai_config = _tool_actions["ai_config"]
        self.act_ai_config.triggered.connect(self.on_ai_config)
        self.act_api_dialog = _tool_actions["api_dialog"]
        self.act_api_dialog.triggered.connect(self.on_api_dialog)
        self.act_division_editor = _tool_actions["division_editor"]
        self.act_division_editor.triggered.connect(self.on_division_editor)
        self.act_ship_designer = _tool_actions["ship_designer"]
        self.act_ship_designer.triggered.connect(self.on_ship_designer)
        self.act_plane_designer = _tool_actions["plane_designer"]
        self.act_plane_designer.triggered.connect(self.on_plane_designer)
        self.act_tank_designer = _tool_actions["tank_designer"]
        self.act_tank_designer.triggered.connect(self.on_tank_designer)
        from PyQt6.QtWidgets import QToolBar
        self.toolbar = QToolBar("反馈", self)
        self.toolbar.setObjectName("toolbar_feedback")
        self.act_feedback = self.toolbar.addAction("💬 问题反馈")
        self.act_feedback.setToolTip("遇到问题可加入 QQ 群反馈")
        self.act_feedback.triggered.connect(self.on_feedback_clicked)
        self.addToolBar(self.toolbar)

        # 如果已配置 HOI4 路径，同步图标映射和本地化管理器
        if self.settings["HOI4_path"]:
            self.renderer.set_hoi4_path(self.settings["HOI4_path"])
            self._sync_gfx_to_renderer()
            self._sync_loc_manager()

        # 文件树右键菜单配置
        self.ui.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.tree.doubleClicked.connect(self.on_tree_doubleClicked)

        # 设置文件树的根路径为当前 mod 目录
        directory = self.settings["mod_path"]
        self.model.setRootPath(directory)
        self.ui.tree.setModel(self.model)
        self.ui.tree.setRootIndex(self.model.index(directory))
        self.ui.tree.setColumnWidth(0, 200)

        # 首次启动（游戏目录与 mod 目录均未配置）：自动弹出配置向导
        if not self.settings.get("HOI4_path") and not self.settings.get("mod_path"):
            QTimer.singleShot(400, self.on_setup_wizard)

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

    def on_mod_opener_clicked(self):
        """菜单"打开 Mod"：选择目录后更新文件树并保存配置。"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录", self.settings["mod_folder_path"])
        if not directory: return
        self.model.setRootPath(directory)
        self.ui.tree.setModel(self.model)
        self.ui.tree.setRootIndex(self.model.index(directory))
        self.ui.tree.setColumnWidth(0, 200)
        self.settings["mod_path"] = directory  # 或 'last_directory'
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)
        # 重新同步图标与本地化（mod 目录的图标/翻译可能变化）
        self._sync_gfx_to_renderer()
        self._sync_loc_manager()
        # 工作台模式下刷新文件列表（mod 目录已更换）
        if self.workbench_dock is not None:
            self.workbench_dock.set_mod_path(directory)

    def on_hoi4_path_choose_clicked(self):
        """菜单"选择 HOI4 目录"：设置游戏路径，同步翻译器和本地化管理器。"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录", self.settings["HOI4_path"])
        if not directory: return
        self.model.setRootPath(directory)
        self.settings["HOI4_path"] = directory
        self.renderer.set_hoi4_path(directory)
        from focus_view import reload_translator
        reload_translator()                          # 重新加载翻译器
        self._sync_gfx_to_renderer()                 # 同步图标映射
        self._sync_loc_manager()                     # 同步本地化管理器
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)
        self._warn_missing_game_folders(directory)

    @staticmethod
    def _warn_missing_game_folders(directory):
        """校验游戏目录关键结构，缺失时提示（避免 MIO/决议目录等版本差异坑）。"""
        from PyQt6.QtWidgets import QMessageBox
        if not directory or not os.path.isdir(directory):
            return
        critical = [
            ("common", "common"),
            ("national_focus", "common/national_focus"),
            ("characters", "common/characters"),
            ("ideas", "common/ideas"),
            ("history", "history"),
            ("localisation", "localisation"),
            ("interface", "interface"),
        ]
        missing = [name for name, rel in critical
                   if not os.path.isdir(os.path.join(directory, rel.replace("/", os.sep)))]
        if missing:
            QMessageBox.warning(
                None, "HOI4 目录校验",
                "所选目录缺少以下关键文件夹，可能不是有效的游戏根目录：\n"
                + "、".join(missing))
        else:
            # 版本相关目录差异提示
            hints = []
            mio_s = os.path.isdir(os.path.join(directory, "common",
                                               "military_industrial_organizations"))
            mio = os.path.isdir(os.path.join(directory, "common",
                                             "military_industrial_organization"))
            if mio_s and not mio:
                hints.append("检测到旧版 MIO 目录名（复数 military_industrial_organizations），"
                             "当前游戏版本应为单数 military_industrial_organization。")
            if hints:
                QMessageBox.information(None, "HOI4 目录校验", "\n".join(hints))

    def on_modfolder_choose_clicked(self):
        """菜单"选择默认 mod 目录"：设置存放 mod 内容子文件夹的目录并保存配置。"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录", self.settings["mod_folder_path"])
        if not directory: return
        self.settings["mod_folder_path"] = directory  # 或 'last_directory'
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def on_modfile_choose_clicked(self):
        """菜单"选择 .mod 文件目录"：设置只存放 .mod 描述文件的目录并保存配置。"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录", self.settings["mod_file_path"])
        if not directory: return
        self.settings["mod_file_path"] = directory  # 或 'last_directory'
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def on_setup_wizard(self):
        """文件菜单：首次使用配置向导（四步路径引导）。"""
        from PyQt6.QtWidgets import QDialog
        from setup_wizard import SetupWizard
        wiz = SetupWizard(parent=self, current=self.settings)
        if wiz.exec() != QDialog.DialogCode.Accepted:
            return
        if not wiz.save_settings():
            return
        data = wiz.get_data()
        self.apply_path_settings(**data)

    def apply_path_settings(self, HOI4_path="", mod_path="",
                            mod_folder_path="", mod_file_path=""):
        """应用向导/外部配置：更新内存配置、刷新文件树/翻译器/本地化并持久化。"""
        if HOI4_path and os.path.isdir(HOI4_path) \
                and HOI4_path != self.settings.get("HOI4_path"):
            self.settings["HOI4_path"] = HOI4_path
            self.renderer.set_hoi4_path(HOI4_path)
            try:
                from focus_view import reload_translator
                reload_translator()
            except Exception:
                pass
            self._sync_gfx_to_renderer()
            self._sync_loc_manager()
        if mod_folder_path:
            self.settings["mod_folder_path"] = mod_folder_path
        if mod_file_path:
            self.settings["mod_file_path"] = mod_file_path
        if mod_path and os.path.isdir(mod_path) \
                and mod_path != self.settings.get("mod_path"):
            self.settings["mod_path"] = mod_path
            self._refresh_tree()
            self._sync_gfx_to_renderer()
            self._sync_loc_manager()
            if self.workbench_dock is not None:
                self.workbench_dock.set_mod_path(mod_path)
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def on_mod_creater_clicked(self):
        """菜单"创建 Mod"：打开 Mod 创建对话框。需先配置 HOI4 路径、默认 mod 目录和 .mod 文件目录。"""
        from mod_creator_dialog import ModCreatorDialog
        if not self.settings.get("HOI4_path") or not self.settings.get("mod_folder_path") \
                or not self.settings.get("mod_file_path"):
            QMessageBox.warning(
                self, "路径未配置",
                "请先配置「钢铁雄心4目录」、「选择默认mod目录」和「选择.mod文件目录」。\n"
                "在菜单栏「文件」中可进行配置。"
            )
            return
        dialog = ModCreatorDialog(self.settings, self)
        dialog.mod_created.connect(lambda path: self._refresh_tree())
        dialog.show()

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
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            raw_data = parse_pdx_script(content)
            from tree_node import TreeNode, tree_from_pdx_text
            from focus_base_builder import FocusTreeEditor
            from generic_tree_editor import GenericTreeEditor
            from gui_translator import get_translator
            from localization_mgr import get_localization_manager

            file_lines = content.splitlines()
            root = tree_from_pdx_text(content)
            translator = get_translator()
            loc_manager = get_localization_manager()
            hoi4 = self.settings.get("HOI4_path", "")
            mod = self.settings.get("mod_path", "")

            # 判断根类型以选择编辑器
            editor_cls = GenericTreeEditor
            title = "内容编辑"
            if raw_data and any(k in raw_data for k in ("focus_tree", "shared_focus", "joint_focus")):
                title = "国策树编辑"
            editor = editor_cls(
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

    def on_coverage_report(self):
        """工具菜单：打开文件类型覆盖检查报告（含仍使用树形编辑器打开的类型清单）。"""
        from coverage_report import CoverageReportDialog
        dlg = CoverageReportDialog(
            parent=self,
            mod_path=self.settings.get("mod_path", ""),
            game_path=self.settings.get("HOI4_path", ""))
        dlg.show()

    def on_health_check(self):
        """工具菜单：导出前健康检查（发布前确定性检查清单）。"""
        mod_path = self.settings.get("mod_path", "")
        if not mod_path or not os.path.isdir(mod_path):
            QMessageBox.information(
                self, "导出前健康检查",
                "请先打开一个 mod 目录（文件菜单 → 打开 Mod）")
            return
        from health_check_dialog import HealthCheckDialog
        dlg = HealthCheckDialog(
            parent=self,
            mod_path=mod_path,
            game_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def on_map_editor(self):
        """工具菜单：地图编辑（点选/涂色/框选/地形演示）。"""
        mod_path = self.settings.get("mod_path", "")
        if not mod_path or not os.path.isdir(mod_path):
            QMessageBox.information(
                self, "地图编辑",
                "请先打开一个 mod 目录（文件菜单 → 打开 Mod）")
            return
        from map_editor_dialog import MapEditorDialog
        dlg = MapEditorDialog(
            parent=self,
            mod_path=mod_path,
            game_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def _require_mod(self, title):
        """工具菜单统一入口：要求已打开 mod 目录，返回 mod_path/hoi4_path。"""
        mod_path = self.settings.get("mod_path", "")
        if not mod_path or not os.path.isdir(mod_path):
            QMessageBox.information(
                self, title,
                "请先打开一个 mod 目录（文件菜单 → 打开 Mod）")
            return None, None
        return mod_path, self.settings.get("HOI4_path", "")

    def on_division_editor(self):
        """工具菜单：师编制编辑器（先选择 OOB 文件；无文件模式同样可用）。"""
        mod_path, hoi4_path = self._require_mod("师编制编辑器")
        if not mod_path:
            return
        from PyQt6.QtWidgets import QInputDialog
        files = []
        for base in (mod_path, hoi4_path):
            if not base:
                continue
            d = os.path.join(base, "history", "units")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(".txt"):
                    files.append(os.path.join(d, fn))
        if not files:
            QMessageBox.information(self, "师编制编辑器",
                                    "未找到 history/units 下的 OOB 文件。")
            return
        names = [os.path.basename(f) for f in files]
        name, ok = QInputDialog.getItem(self, "师编制编辑器", "选择 OOB 文件:",
                                        names, 0, False)
        if not ok:
            return
        file_path = files[names.index(name)]
        from initial_oob_editor import open_oob_designer
        open_oob_designer(file_path, mod_path=mod_path,
                          hoi4_path=hoi4_path, parent=self)

    def on_ship_designer(self):
        """工具菜单：舰艇设计（跨国家浏览，无文件模式可用）。"""
        mod_path, hoi4_path = self._require_mod("舰艇设计")
        if not mod_path:
            return
        from ship_design_dialog import ShipDesignDialog
        dlg = ShipDesignDialog(mod_path, hoi4_path, parent=self)
        dlg.show()

    def on_plane_designer(self):
        """工具菜单：飞机设计（跨国家浏览，无文件模式可用）。"""
        mod_path, hoi4_path = self._require_mod("飞机设计")
        if not mod_path:
            return
        from plane_design_dialog import PlaneDesignDialog
        dlg = PlaneDesignDialog(mod_path, hoi4_path, parent=self)
        dlg.show()

    def on_tank_designer(self):
        """工具菜单：坦克设计（跨国家浏览，无文件模式可用）。"""
        mod_path, hoi4_path = self._require_mod("坦克设计")
        if not mod_path:
            return
        from tank_design_dialog import TankDesignDialog
        dlg = TankDesignDialog(mod_path, hoi4_path, parent=self)
        dlg.show()

    def on_region_editor(self):
        """工具菜单：区域编辑（框选划分战略区域/补给区域/州）。"""
        mod_path = self.settings.get("mod_path", "")
        if not mod_path or not os.path.isdir(mod_path):
            QMessageBox.information(
                self, "区域编辑",
                "请先打开一个 mod 目录（文件菜单 → 打开 Mod）")
            return
        from region_editor_dialog import RegionEditorDialog
        dlg = RegionEditorDialog(
            parent=self,
            mod_path=mod_path,
            game_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def on_overlay_report(self):
        """工具菜单：覆盖规则与增量报告（mod 覆盖原版的显式规则链）。"""
        from overlay_report_dialog import OverlayReportDialog
        dlg = OverlayReportDialog(
            parent=self,
            mod_path=self.settings.get("mod_path", ""),
            hoi4_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def on_icon_manifest(self):
        """工具菜单：图标库 manifest（全部 gfx sprite 清单）。"""
        from icon_manifest_dialog import IconManifestDialog
        dlg = IconManifestDialog(
            parent=self,
            mod_path=self.settings.get("mod_path", ""),
            hoi4_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def on_unit_counters(self):
        """工具菜单：单位标牌库（从游戏导入的兵牌图标库）。"""
        from unit_counter_library_dialog import UnitCounterLibraryDialog
        dlg = UnitCounterLibraryDialog(
            parent=self,
            game_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def on_undo_last_write(self):
        """工具菜单：撤销最近一次文件写入并刷新界面。"""
        from undo_mgr import undo, can_undo
        if not can_undo():
            QMessageBox.information(self, "撤销", "没有可撤销的写入操作")
            return
        path, ok = undo()
        if not ok:
            QMessageBox.warning(self, "撤销", f"撤销失败: {path}")
            return
        self._refresh_tree()
        if self.workbench_dock is not None:
            try:
                self.workbench_dock._refresh()
            except Exception:
                pass
        try:
            self.custom_view.redraw()
        except Exception:
            pass
        QMessageBox.information(
            self, "撤销", f"已恢复文件到上次写入前:\n{os.path.basename(path)}")

    def on_game_reference(self):
        """工具菜单：游戏数据参考面板（国家 tag + 中文名搜索复制）。"""
        from reference_panel import GameReferenceDialog
        dlg = GameReferenceDialog(
            parent=self,
            game_path=self.settings.get("HOI4_path", ""),
            mod_path=self.settings.get("mod_path", ""))
        dlg.exec()

    def on_ai_assist(self):
        """工具菜单：AI 创作助手（需求 → 生成 → 预览 → 写入 mod）。"""
        from ai_assist_dialog import AiAssistDialog
        cur_type = ""
        wb = self.workbench_dock
        if wb is not None:
            cur_type = wb._current_type
        dlg = AiAssistDialog(
            parent=self,
            content_type_key=cur_type,
            mod_path=self.settings.get("mod_path", ""))
        dlg.exec()

    def on_ai_config(self):
        """工具菜单：AI 服务配置。"""
        from ai_assist_dialog import AiConfigDialog
        dlg = AiConfigDialog(self)
        dlg.exec()

    def on_api_dialog(self):
        """工具菜单：外部接口对话框（外置 Agent HTTP API / MCP）。"""
        from api_gui_dialog import ApiDialog
        dlg = ApiDialog(
            parent=self,
            mod_path=self.settings.get("mod_path", ""),
            game_path=self.settings.get("HOI4_path", ""))
        dlg.exec()

    def on_tech_tree_view(self):
        """（已废弃入口）科技树改在国策树画布中绘制：工作台选中「科技」类型，
        双击科技文件或在无文件模式下自动绘制；此处保留空实现避免旧引用报错。"""
        pass

    @staticmethod
    def _locate_entity_in_editor(editor, entity_id):
        """在已打开的树编辑器中定位并选中指定实体节点。"""
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

    # ---------- AI 助手 ----------

    def on_ai_prompt_file(self):
        """为当前文件生成 AI 文本提示词。"""
        from ai_prompt_dialog import AIPromptDialog
        file_path = ""
        view = self.custom_view
        if view is not None and getattr(view, "_current_file_path", None):
            file_path = view._current_file_path
        dlg = AIPromptDialog(
            file_path=file_path,
            mod_path=self.settings.get("mod_path", ""),
            scope="当前文件",
            fill_callback=lambda blocks: self._fill_ai_blocks(blocks, file_path),
            parent=self,
        )
        dlg.show()

    def on_ai_prompt_project(self):
        """为整个项目生成 AI 提示词。"""
        from ai_prompt_dialog import AIPromptDialog
        mod_path = self.settings.get("mod_path", "")
        if not mod_path:
            QMessageBox.warning(self, "提示", "请先打开 mod 文件夹")
            return
        dlg = AIPromptDialog(
            file_path="",
            mod_path=mod_path,
            scope="整个项目",
            fill_callback=lambda blocks: self._fill_ai_blocks(blocks, ""),
            parent=self,
        )
        dlg.show()

    def _fill_ai_blocks(self, blocks, file_path):
        """将 AI 回复解析出的块回填到当前文件。

        规则：
        - focus 块：追加为国策树中的新国策（写入文件末尾的 focus_tree 内）
        - effect/trigger 块：目标为具体国策 id 时，填入该国策对应块；
          目标为「当前」时，写入当前文件对应的国策树文件中该国策（首个匹配）
        """
        import re
        from pdx_parser import parse_pdx_script

        target_file = file_path or (self.custom_view._current_file_path
                                    if getattr(self.custom_view, "_current_file_path", None) else "")
        if not target_file or not os.path.isfile(target_file):
            QMessageBox.warning(
                self, "提示",
                "未找到目标文件。请在国策设计视图中打开文件后重试。")
            return

        try:
            with open(target_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            applied = 0
            skipped = []
            for b in blocks:
                kind = b["kind"]
                target = b["target"]
                body = b["content"].strip()
                if kind == "focus":
                    # 追加新国策块到文件末尾的 focus_tree 内
                    content = self._append_focus_block(content, body)
                    applied += 1
                else:
                    # effect/trigger 填入目标国策
                    new_content, ok = self._merge_into_focus(content, target, body, kind)
                    if ok:
                        content = new_content
                        applied += 1
                    else:
                        skipped.append(f"{kind}:{target}")

            from write_utils import atomic_write_text
            atomic_write_text(target_file, content)

            # 刷新设计视图
            self.load_txt_pdx_to_memory(target_file)
            self._refresh_tree()
            msg = f"已回填 {applied} 个块到 {os.path.basename(target_file)}"
            if skipped:
                msg += f"\n跳过（未找到目标国策）: {', '.join(skipped)}"
            QMessageBox.information(self, "回填完成", msg)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "回填失败", str(e))

    @staticmethod
    def _append_focus_block(content, body):
        """将新国策块追加到 focus_tree 内（文件末尾的右括号前）。"""
        # 找到最后一个 focus_tree 块的结束（去除末尾空白与右括号）
        stripped = content.rstrip()
        if stripped.endswith("}"):
            idx = stripped.rfind("}")
            # 确保内容是块（非单行），简单处理：在最后一个 } 前插入
            new_block = "\n".join(
                "\t" + line if line.strip() else line for line in body.splitlines())
            return stripped[:idx] + "\n\n\t" + new_block + "\n" + stripped[idx:]
        return stripped + "\n\n" + body + "\n"

    def _merge_into_focus(self, content, focus_id, body, kind):
        """将效果/触发代码合并到指定国策块中。

        解析 body 的第一个顶层语句（key = value 或 key = { ... }），
        若目标国策块内已有同名块则把内容合并进去，否则追加新块。

        Returns:
            (str, bool): 合并后的文件内容；是否找到目标国策
        """
        import re
        # 找到目标国策块范围（用括号配对定位真实块边界）
        start = content.find("focus = {")
        found = -1
        while start != -1:
            depth = 0
            j = content.find("{", start)
            if j == -1:
                break
            k = j
            while k < len(content):
                if content[k] == "{":
                    depth += 1
                elif content[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            block_text = content[start:k + 1]
            if re.search(r'\bid\s*=\s*' + re.escape(focus_id) + r'\b', block_text):
                found = start
                end_idx = k
                block = block_text
                break
            start = content.find("focus = {", k)
        if found == -1:
            return content, False

        # 解析 body 顶层语句
        stmt_key, stmt_value, stmt_inner = self._parse_top_statement(body)
        if stmt_key is None:
            # 无法解析为语句，直接追加整段
            inserted_block = "\n\t" + body.strip() + "\n"
            merged = block[:block.rfind("}")] + inserted_block + block[block.rfind("}"):]
            new_content = content[:found] + merged + content[end_idx + 1:]
            return new_content, True

        # 在目标块中查找同名块
        sub = re.search(
            r'\b' + re.escape(stmt_key) + r'\s*=\s*\{', block)
        if sub:
            # 已有同名块：把语句内容并入其内部（括号配对定位）
            inner_start = block.find("{", sub.start())
            d2 = 0
            k2 = inner_start
            while k2 < len(block):
                if block[k2] == "{":
                    d2 += 1
                elif block[k2] == "}":
                    d2 -= 1
                    if d2 == 0:
                        break
                k2 += 1
            # 保留完整语句前缀（key = { ... }）
            stmt_text = block[sub.start():k2 + 1]
            last_brace = stmt_text.rfind("}")
            if stmt_inner:
                inner_text = stmt_inner.strip()
                if inner_text.endswith("}"):
                    inner_text = inner_text[:-1].rstrip()
                merged_stmt = (stmt_text[:last_brace] + "\n\t\t\t" +
                               inner_text + "\n\t\t" + stmt_text[last_brace:])
            else:
                merged_stmt = stmt_text
            new_block = block[:sub.start()] + merged_stmt + block[k2 + 1:]
            new_content = content[:found] + new_block + content[end_idx + 1:]
            return new_content, True

        # 无同名块：在国策块末尾前追加
        last_brace = block.rfind("}")
        new_stmt = "\n\t" + stmt_key + " = {"
        if stmt_inner:
            for line in stmt_inner.strip().splitlines():
                new_stmt += "\n\t\t" + line
        new_stmt += "\n\t}"
        merged = block[:last_brace] + new_stmt + "\n" + block[last_brace:]
        new_content = content[:found] + merged + content[end_idx + 1:]
        return new_content, True

    @staticmethod
    def _parse_top_statement(body):
        """解析一段 PDX 文本的顶层语句，返回 (key, 原始语句文本, 内部内容)。

        内部内容为块内的文本（不含最外层花括号）。
        """
        import re
        body = body.strip()
        m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\{', body)
        if m:
            key = m.group(1)
            inner_start = body.find("{")
            depth = 0
            k = inner_start
            while k < len(body):
                if body[k] == "{":
                    depth += 1
                elif body[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            inner = body[inner_start + 1:k]
            return key, body[:k + 1], inner
        m2 = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^\s{}]+)', body)
        if m2:
            return m2.group(1), body, ""
        return None, None, None

    def on_manage_terms(self):
        """打开词条管理对话框。"""
        from term_dialog import TermDialog
        from term_registry import get_term_registry
        dlg = TermDialog(get_term_registry(), parent=self)
        dlg.show()

    def on_manage_templates(self):
        """打开模板管理对话框（树形编辑 + 变量设置）。"""
        from template_manager_dialog import TemplateManagerDialog
        dlg = TemplateManagerDialog(parent=self)
        dlg.show()

    def on_feedback_clicked(self):
        """问题反馈：显示 QQ 群号（数字部分可复制）。"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QGuiApplication

        dlg = QDialog(self)
        dlg.setWindowTitle("问题反馈")
        dlg.setFixedWidth(360)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("遇到问题欢迎加入 QQ 群反馈："))
        num_label = QLabel("720723415")
        num_label.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #1f4f7e;"
            "border: 1px solid rgba(22, 35, 51, 0.18); border-radius: 8px; padding: 8px; background: #f4f7fa;")
        num_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(num_label)
        hint = QLabel("（可直接选中上面的数字复制）")
        hint.setStyleSheet("color: #5d6b7a;")
        lay.addWidget(hint)
        btn_row = QHBoxLayout()
        copy_btn = QPushButton("复制群号")
        close_btn = QPushButton("关闭")

        def do_copy():
            QGuiApplication.clipboard().setText("720723415")
            copy_btn.setText("已复制 ✓")
        copy_btn.clicked.connect(do_copy)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)
        dlg.exec()

    def on_validate_mod(self):
        """校验当前 mod：对照游戏数据字典检查未知引用。"""
        from PyQt6.QtWidgets import QMessageBox
        from game_data import build_dictionary, validate_directory

        hoi4 = self.settings.get("HOI4_path", "")
        mod = self.settings.get("mod_path", "")
        if not hoi4 or not os.path.isdir(hoi4):
            QMessageBox.information(
                self, "校验 mod", "未配置有效的 HOI4 游戏目录，无法构建数据字典。")
            return
        if not mod or not os.path.isdir(mod):
            QMessageBox.information(self, "校验 mod", "未打开有效的 mod 目录。")
            return

        self.statusBar().showMessage("正在构建游戏数据字典…")
        try:
            dictionary = build_dictionary(hoi4)
        except Exception as e:
            QMessageBox.warning(self, "校验失败", f"构建数据字典失败: {e}")
            return

        self.statusBar().showMessage("正在校验 mod 文件…")
        from game_data import find_duplicate_ids
        results = validate_directory(dictionary, mod)
        duplicates = find_duplicate_ids(mod)
        self.statusBar().clearMessage()

        # ── 校验体系扩展：本地化缺失 + 国策引用悬空 ──
        from validation import (
            check_localisation_coverage, check_focus_references,
            fix_localisation_missing)
        loc_missing = check_localisation_coverage(mod, hoi4)
        focus_refs = check_focus_references(mod)

        lines = []
        total = 0
        for rel in sorted(results):
            issues = results[rel]
            total += len(issues)
            lines.append(f"◆ {rel}")
            for i in issues:
                lines.append(f"    - {i}")
        if duplicates:
            lines.append("")
            lines.append("════ 重复 ID（多个文件定义同一标识） ════")
            for k in sorted(duplicates):
                total += 1
                lines.append(f"◆ {k}:")
                for rel in duplicates[k]:
                    lines.append(f"    - {rel}")
        if loc_missing:
            lines.append("")
            lines.append(f"════ 本地化缺失（{len(loc_missing)} 条，可一键补写） ════")
            total += len(loc_missing)
            for m in sorted(loc_missing, key=lambda x: (x["country"], x["key"]))[:200]:
                tag = f"[{m['country']}] " if m["country"] else ""
                miss = ", ".join(m.get("missing_keys") or [m["key"]])
                lines.append(f"◆ {tag}{m['key']}（{m['type']} · {m['file']}）→ 缺: {miss}")
            if len(loc_missing) > 200:
                lines.append(f"    …（其余 {len(loc_missing) - 200} 条略）")
        if focus_refs:
            lines.append("")
            lines.append(f"════ 国策引用悬空（{len(focus_refs)} 处） ════")
            total += len(focus_refs)
            for r in sorted(focus_refs, key=lambda x: x["file"])[:100]:
                lines.append(f"◆ {r['focus_id']}（{r['file']}）→ 缺少: {', '.join(r['missing'])}")
            if len(focus_refs) > 100:
                lines.append(f"    …（其余 {len(focus_refs) - 100} 处略）")

        if not lines:
            QMessageBox.information(
                self, "校验 mod", "未发现问题：无未知引用、无重复 ID、无本地化缺失、无国策引用悬空。")
            return
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
            QApplication, QMessageBox as _MB)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"校验结果：{total} 个问题")
        dlg.resize(760, 520)
        lay = QVBoxLayout(dlg)
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText("\n".join(lines))
        lay.addWidget(edit)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        if loc_missing:
            fix_btn = QPushButton(f"✅ 一键补写本地化（{len(loc_missing)} 条）")
            fix_btn.clicked.connect(
                lambda: self._fix_missing_localisation(dlg, edit, mod, hoi4, loc_missing))
            btn_row.addWidget(fix_btn)
        copy_btn = QPushButton("📋 复制报告")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText("\n".join(lines)))
        btn_row.addWidget(copy_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)
        dlg.exec()

    def _fix_missing_localisation(self, dlg, edit, mod, hoi4, missing):
        """一键补写本地化缺失词条（写入 mod 翻译文件，不碰游戏文件）。"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "一键补写本地化",
            f"将把 {len(missing)} 个缺失词条写入 mod 的本地化文件\n"
            "（值取游戏英文原文，无原文用实体 id 占位，之后可逐条翻译）。\n"
            "只写入 mod 目录，不会修改游戏文件。继续？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        from validation import fix_localisation_missing
        try:
            n, target = fix_localisation_missing(mod, hoi4, missing)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"补写失败: {e}")
            return
        if n:
            edit.appendPlainText(
                f"\n✅ 已补写 {n} 条本地化词条 → {os.path.basename(target)}")
        else:
            QMessageBox.information(self, "提示", "没有需要补写的词条（可能已被其他文件覆盖）")
        self._sync_loc_manager()
