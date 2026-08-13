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
            f"<span style='color:#888'>"
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
        root.addLayout(btn)

        hint = QLabel(
            "提示: 先编辑编制 → 保存后 → 打开地图放置，选择编制点击地块放置部队。"
            "海军/空军基地已在地图中标出（⚓/✈），供后续海军空军放置使用。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#888")
        root.addWidget(hint)
        root.addStretch(1)

    def _open_division_editor(self):
        from division_editor import DivisionEditor
        dlg = DivisionEditor(
            self.oob_file, self.sub_units, self.gfx_map,
            self.mod_path, self.hoi4_path, parent=self)
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
