"""初始部队编辑器 — 顶层入口

打开 history/units 文件，整合师编制编辑与地图放置两个独立窗口，
两者共享同一 OobFile（保存/刷新联动）。
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)

from oob_loader import OobFile, load_sub_units
from gui_translator import get_translator, scan_gfx_folder


class InitialOobEditor(QDialog):
    """初始部队（编制 + 放置）编辑器。"""

    def __init__(self, file_path, hoi4_path="", mod_path="", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.hoi4_path = hoi4_path
        self.mod_path = mod_path
        self.oob_file = OobFile(file_path)
        self.sub_units = load_sub_units(mod_path, hoi4_path)
        self.gfx_map = dict(get_translator().gfx_map)
        try:
            scan_gfx_folder(mod_path, self.gfx_map)
        except Exception:
            pass

        self.setWindowTitle(f"初始部队编辑 — {os.path.basename(file_path)}")
        self.resize(520, 260)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        info = QLabel(
            f"<b>{os.path.basename(self.file_path)}</b><br>"
            f"编制模板: {len(self.oob_file.templates)} 个"
            f"　|　已部署部队: {len(self.oob_file.placements)} 支<br>"
            f"<span style='color:#5d6b7a'>"
            f"保存后游戏读取 history/units 下的该文件，未修改的内容将原样保留。"
            f"</span>")
        info.setWordWrap(True)
        root.addWidget(info)

        btn = QHBoxLayout()
        self.division_btn = QPushButton("🎖️ 师编制编辑器")
        self.division_btn.setMinimumHeight(64)
        self.division_btn.clicked.connect(self._open_division_editor)
        btn.addWidget(self.division_btn)

        self.map_btn = QPushButton("🗺 地图放置陆军")
        self.map_btn.setMinimumHeight(64)
        self.map_btn.clicked.connect(self._open_map_editor)
        btn.addWidget(self.map_btn)

        self.ship_btn = QPushButton("🚢 舰艇设计")
        self.ship_btn.setMinimumHeight(64)
        self.ship_btn.clicked.connect(self._open_ship_designer)
        btn.addWidget(self.ship_btn)

        self.plane_btn = QPushButton("✈ 飞机设计")
        self.plane_btn.setMinimumHeight(64)
        self.plane_btn.clicked.connect(self._open_plane_designer)
        btn.addWidget(self.plane_btn)

        self.tank_btn = QPushButton("🛡 坦克设计")
        self.tank_btn.setMinimumHeight(64)
        self.tank_btn.clicked.connect(self._open_tank_designer)
        btn.addWidget(self.tank_btn)
        root.addLayout(btn)

        hint = QLabel(
            "提示: 先编辑编制 → 保存后 → 打开地图放置，选择编制点击地块放置部队。"
            "海军/空军基地已在地图中标出（⚓/✈），供后续海军空军放置使用。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5d6b7a")
        root.addWidget(hint)
        root.addStretch(1)

    def _open_division_editor(self):
        from division_editor import DivisionEditor
        dlg = DivisionEditor(
            self.oob_file, self.sub_units, self.gfx_map,
            self.mod_path, self.hoi4_path, parent=self)
        dlg.show()

    def _open_ship_designer(self):
        from ship_design_dialog import ShipDesignDialog
        dlg = ShipDesignDialog(self.mod_path, self.hoi4_path, parent=self)
        dlg.show()

    def _open_plane_designer(self):
        from plane_design_dialog import PlaneDesignDialog
        dlg = PlaneDesignDialog(self.mod_path, self.hoi4_path, parent=self)
        dlg.show()

    def _open_tank_designer(self):
        from tank_design_dialog import TankDesignDialog
        dlg = TankDesignDialog(self.mod_path, self.hoi4_path, parent=self)
        dlg.show()

    def _open_map_editor(self):
        from oob_map_editor import OobMapEditor
        from oob_loader import find_oob_country
        tag = find_oob_country(self.mod_path, self.file_path)
        dlg = OobMapEditor(
            self.oob_file, self.sub_units, self.gfx_map,
            self.mod_path, self.hoi4_path, country_tag=tag, parent=self)
        dlg.show()

    def _save(self):
        try:
            self.oob_file.save()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", f"已保存到:\n{self.file_path}")


def _ask_oob_open_mode(parent, other_keys):
    """用户选择如何处理含其他内容的 OOB 文件。

    Returns:
        "designer" / "tree" / "both" / None（取消）。
    """
    from PyQt6.QtWidgets import QInputDialog
    items = [
        "打开对应设计器（忽略其他内容）",
        "打开完整树编辑器（可查看/编辑全部内容）",
        "两者都打开",
        "取消",
    ]
    text = ("检测到该 OOB 文件包含设计器未覆盖的内容：\n"
            "　" + "、".join(other_keys) +
            "\n\n请选择打开方式：")
    choice, ok = QInputDialog.getItem(
        parent, "OOB 文件包含其他内容", text, items, 0, False)
    if not ok:
        return None
    if choice == items[0]:
        return "designer"
    if choice == items[1]:
        return "tree"
    if choice == items[2]:
        return "both"
    return None


def _open_oob_tree_editor(file_path, mod_path="", hoi4_path="", parent=None):
    """以完整通用树编辑器打开 OOB 文件（可查看/修改全部内容）。"""
    from tree_node import tree_from_pdx_text
    from generic_tree_editor import GenericTreeEditor
    from gui_translator import get_translator
    from localization_mgr import get_localization_manager
    from focus_view import CUSTOM_STATEMENT_PATH
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        content = f.read()
    root = tree_from_pdx_text(content)
    file_lines = content.splitlines()
    editor = GenericTreeEditor(
        root_node=root,
        file_path=file_path,
        file_lines=file_lines,
        block_range=(1, len(file_lines) + 1),
        translator=get_translator(),
        custom_statement_path=CUSTOM_STATEMENT_PATH,
        loc_manager=get_localization_manager(),
        parent=parent,
        title="OOB 完整编辑",
        hoi4_path=hoi4_path,
        mod_path=mod_path,
    )
    editor.show()
    return editor


def open_oob_designer(file_path, mod_path="", hoi4_path="", parent=None):
    """打开 OOB 文件 → 按文件军种自动拉起对应设计面板。

    - 含陆军（division_template/division）→ 师编制设计器（顶部可调地编/其他设计器）
    - 含海军（ship/fleet/task_force）→ 舰艇设计面板
    - 含空军（air_wings/air_wing）→ 飞机设计面板
    多军种混合会同时拉起多个面板（非模态）；无法识别时回退师编制设计器。
    若文件包含设计器未覆盖的其他顶层内容（如 instant_effect），先让用户选择：
    仅打开设计器 / 打开完整树编辑器 / 两者都打开 / 取消。

    Returns:
        打开的设计器/编辑器；多个时返回 list；用户取消返回 None。
    """
    from oob_loader import OobFile, load_sub_units, detect_oob_kinds, \
        detect_oob_other_content, find_oob_country
    from gui_translator import get_translator, scan_gfx_folder
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
    except Exception:
        content = ""
    kinds = detect_oob_kinds(content)
    other_keys = detect_oob_other_content(content)
    tree_editor = None
    if other_keys:
        mode = _ask_oob_open_mode(parent, other_keys)
        if mode is None:
            return None
        if mode in ("tree", "both"):
            tree_editor = _open_oob_tree_editor(
                file_path, mod_path=mod_path, hoi4_path=hoi4_path,
                parent=parent)
            if mode == "tree":
                return tree_editor

    tag = find_oob_country(mod_path, file_path)
    opened = []

    if kinds.get("navy"):
        from ship_design_dialog import ShipDesignDialog
        dlg = ShipDesignDialog(mod_path, hoi4_path, country_tag=tag,
                               parent=parent)
        dlg.show()
        opened.append(dlg)
    if kinds.get("air"):
        from plane_design_dialog import PlaneDesignDialog
        dlg = PlaneDesignDialog(mod_path, hoi4_path, country_tag=tag,
                                parent=parent)
        dlg.show()
        opened.append(dlg)
    if kinds.get("army") or not opened:
        oob_file = OobFile(file_path)
        sub_units = load_sub_units(mod_path, hoi4_path)
        gfx_map = dict(get_translator().gfx_map)
        try:
            scan_gfx_folder(mod_path, gfx_map)
        except Exception:
            pass
        from division_editor import DivisionEditor
        dlg = DivisionEditor(oob_file, sub_units, gfx_map,
                             mod_path, hoi4_path, parent=parent)
        dlg.show()
        opened.append(dlg)
    if tree_editor is not None:
        return [tree_editor] + opened
    return opened[0] if len(opened) == 1 else opened
