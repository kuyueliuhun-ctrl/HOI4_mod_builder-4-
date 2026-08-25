"""地图编辑界面（工具菜单 → 地图编辑…）

基于 MapCanvas 的可视化地图工具：
- 四种模式：手型平移（单击/悬停查看信息）/ 涂色（改归属，写 mod 州文件）/
  框选 / 多选
- 图层开关：国家色 / 地块边界 / 地形类型（terrain.bmp）/ 地形立体感（heights hillshade）
- 左侧：建筑类型列表（common/buildings 解析，选中后可放置到地块/州）
- 右侧：地块信息面板（地块/州/州类别/建筑位/建筑/归属/国家颜色）+ 操作按钮
  （放置建筑 / 改变归属 / 修改国家颜色）
- 写回纪律：编辑原版内容时自动复制对应文件到 mod 再改（state_build_ops）
- 定位：输入国家 TAG 或地块 id 跳转
"""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from map_canvas import (MapCanvas, MODE_PAN, MODE_POINT, MODE_PAINT,
                        MODE_RECT, MODE_MULTI)
from building_lib import load_building_types, load_country_colors
from ai_loader import load_ai_faction_theaters
from ai_ui_common import KeyValueTableEditor
from map_region_ops import parse_region_file
from map_data_layers import (
    build_categorical_overlay, build_line_overlay, build_river_overlay,
    build_value_overlay, load_railways, load_supply_areas,
    state_vp_and_resources,
)


# 数据层下拉选项（P2 ③：地图数据层色阶）
DATA_LAYERS = ("无", "胜利点 VP", "资源总量", "补给区", "铁路", "河流")


class MapEditorDialog(QDialog):
    """地图编辑界面。"""

    def __init__(self, parent=None, mod_path="", game_path=""):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.game_path = game_path or ""
        from oob_map_editor import get_map_data, get_state_data
        self.map_data = get_map_data(self.mod_path, self.game_path)
        self.state_data = get_state_data(self.mod_path, self.game_path)
        self._last_pids = []
        # 建筑类型 / 国家文件颜色（写回后刷新）
        self.building_types = load_building_types(self.mod_path,
                                                  self.game_path)
        self.country_colors = load_country_colors(self.mod_path,
                                                  self.game_path)
        self._building_icons = {}
        self._building_btn_map = {}
        self._current_pid = 0
        from localization_mgr import get_localization_manager
        self._loc_manager = get_localization_manager()
        try:
            self._loc_manager.reload(game_path=self.game_path,
                                     mod_path=self.mod_path)
        except Exception:
            pass
        self._load_building_icons()

        self.setWindowTitle("地图编辑")
        self.resize(1600, 900)   # 左右面板加宽后默认尺寸
        self._build_ui()
        self._rebuild_layers()
        self._setup_vector_borders()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        bar = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        for mode, label, tip in (
            (MODE_PAN, "✋ 手型", "拖拽平移；单击/悬停查看地块信息"),
            (MODE_PAINT, "🖌 涂色", "点击地块修改归属（写 mod 州文件）"),
            (MODE_RECT, "▭ 框选", "拖拽框选地块集合"),
            (MODE_MULTI, "☑ 多选", "逐个点选地块加入/移出选区"),
        ):
            btn = QToolButton()
            btn.setText(label)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _c, m=mode: self._set_mode(m))
            self.mode_group.addButton(btn)
            bar.addWidget(btn)
        self.mode_group.buttons()[0].setChecked(True)
        bar.addSpacing(16)

        self.chk_country = QCheckBox("国家色")
        self.chk_country.setChecked(True)
        self.chk_border = QCheckBox("地块边界")
        self.chk_border.setChecked(True)
        self.chk_terrain = QCheckBox("地形类型")
        self.chk_hillshade = QCheckBox("地形立体感")
        self.chk_ai_theaters = QCheckBox("AI派系战区")
        for chk, slot in ((self.chk_country, self._rebuild_layers),
                          (self.chk_border, self._rebuild_layers),
                          (self.chk_terrain, self._rebuild_layers),
                          (self.chk_hillshade, self._rebuild_layers),
                          (self.chk_ai_theaters, self._rebuild_layers)):
            chk.toggled.connect(slot)
            bar.addWidget(chk)
        theater_btn = QPushButton("战区列表")
        theater_btn.clicked.connect(self._open_theater_list)
        bar.addWidget(theater_btn)
        bar.addSpacing(10)
        bar.addWidget(QLabel("数据层"))
        self.data_layer_combo = QComboBox()
        self.data_layer_combo.addItems(DATA_LAYERS)
        self.data_layer_combo.setMaximumWidth(140)
        self.data_layer_combo.currentTextChanged.connect(
            self._on_data_layer_changed)
        bar.addWidget(self.data_layer_combo)
        bar.addStretch(1)

        self.loc_edit = QLineEdit()
        self.loc_edit.setPlaceholderText("定位国家 TAG 或地块 id")
        self.loc_edit.setMaximumWidth(170)
        bar.addWidget(self.loc_edit)
        self.loc_btn = QPushButton("定位")
        self.loc_btn.clicked.connect(self._on_locate)
        bar.addWidget(self.loc_btn)
        self.fit_btn = QPushButton("⌂ 全景")
        bar.addWidget(self.fit_btn)
        layout.addLayout(bar)

        # 三栏：左（建筑类型）｜中（画布）｜右（地块信息）
        mid = QHBoxLayout()
        mid.addWidget(self._build_left_panel())

        # 画布
        self.canvas = MapCanvas(self.map_data)
        self.canvas.province_clicked.connect(self._on_province_clicked)
        self.canvas.paint_province.connect(self._on_paint)
        self.canvas.rect_selected.connect(self._on_rect_selected)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        # 悬停不再刷新信息（信息只在点选后展示）；悬停仅做目标省份高亮
        self.canvas.set_hover_highlight_enabled(True)
        self.fit_btn.clicked.connect(self.canvas.fit_map)
        mid.addWidget(self.canvas, 1)

        mid.addWidget(self._build_right_panel())
        layout.addLayout(mid, 1)

        # 状态栏
        self.status_label = QLabel(
            "手型：拖拽平移；单击/悬停查看地块信息；滚轮缩放（预览）")
        layout.addWidget(self.status_label)

        # 初始视野：全景基础上放大（map_initial_zoom，默认 1.3，减少留白）
        from map_canvas import read_map_settings
        self.canvas.fit_map(factor=read_map_settings()["initial_zoom"])

    def _build_left_panel(self):
        """左侧：建筑类型按钮。

        可建造（is_buildable 非 no）→ 上方 5 列纯图标网格（悬停显示
        中文名+描述）；不可建造（地标/水坝等）→ 下方文本按钮一行一个。
        图标放大、面板加宽；隐藏水平滚动条（底部不出滚动条），垂直滚动条
        按需出现并保留在内容区右侧（不压缩按钮，加宽面板补偿）。
        """
        panel = QGroupBox("建筑类型")
        vl = QVBoxLayout(panel)
        vl.addWidget(QLabel("选中建筑后，点选地块并在右侧点「放置」"))
        self.building_scroll = QScrollArea()
        self.building_scroll.setWidgetResizable(True)
        self.building_scroll.setMinimumWidth(320)
        self.building_scroll.setMaximumWidth(360)
        # 底部不出现水平滚动条；垂直滚动条按需显示
        self.building_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.building_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(6, 6, 6, 6)
        col.setSpacing(4)
        self.building_group = QButtonGroup(self)
        self.building_group.setExclusive(True)

        buildable = [b for b in self.building_types if b.get("buildable", True)]
        not_buildable = [b for b in self.building_types
                         if not b.get("buildable", True)]
        if buildable:
            grid = QGridLayout()
            grid.setSpacing(4)
            for i, b in enumerate(buildable):
                btn = self._make_building_button(b, icon_only=True)
                grid.addWidget(btn, i // 5, i % 5)
            col.addLayout(grid)
        if not_buildable:
            col.addWidget(QLabel("不可建造（地标/设施）"))
            for b in not_buildable:
                btn = self._make_building_button(b)
                btn.setMinimumHeight(44)
                col.addWidget(btn)
        col.addStretch(1)
        body.setLayout(col)
        self.building_scroll.setWidget(body)
        vl.addWidget(self.building_scroll)
        return panel

    def _make_building_button(self, b, icon_only=False):
        """单个建筑按钮：icon_only=纯图标（4 列网格用），否则图标+中文名。"""
        btn = QToolButton()
        btn.setCheckable(True)
        icon = self._building_icons.get(b["key"])
        if icon is not None:
            btn.setIcon(QIcon(icon))
        if icon_only:
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setFixedSize(56, 56)
            # 图标尽量充满按钮（Qt 默认 iconSize 偏小，会留大量白边）
            btn.setIconSize(QSize(52, 52))
            btn.setStyleSheet("QToolButton { padding: 0px; }")
        else:
            btn.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setIconSize(QSize(32, 32))
            btn.setText(self._building_name(b["key"]))
        tip = "%s（%s级）" % (self._building_name(b["key"]),
                             "省" if b["provincial"] else "州")
        desc = self._building_desc(b["key"])
        if desc:
            tip += "\n\n" + desc
        eff = self._building_effects(b)
        if eff:
            tip += "\n\n" + eff
        btn.setToolTip(tip)
        self.building_group.addButton(btn)
        self._building_btn_map[btn] = b
        return btn

    def _build_right_panel(self):
        """右侧：地块信息 + 操作按钮（固定宽度，信息变化不影响布局）。"""
        panel = QGroupBox("地块信息")
        panel.setFixedWidth(330)
        vl = QVBoxLayout(panel)
        self.info_label = QLabel("点选地块查看详细信息")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        vl.addWidget(self.info_label)

        self.state_group = QGroupBox("州信息（可编辑）")
        svl = QVBoxLayout(self.state_group)
        fid = QHBoxLayout()
        fid.addWidget(QLabel("州 id"))
        self.state_id_label = QLabel("-")
        self.state_id_label.setStyleSheet(
            "color:%s;" % "#6b7686")
        fid.addWidget(self.state_id_label, 1)
        svl.addLayout(fid)

        fkey = QHBoxLayout()
        fkey.addWidget(QLabel("州名键"))
        self.state_name_edit = QLineEdit()
        self.state_name_edit.setToolTip("state.name 的本地化键，如 STATE_124")
        fkey.addWidget(self.state_name_edit, 1)
        svl.addLayout(fkey)
        fcn = QHBoxLayout()
        fcn.addWidget(QLabel("中文名"))
        self.state_name_cn_edit = QLineEdit()
        self.state_name_cn_edit.setToolTip(
            "保存时写入 mod 本地化（simp_chinese）")
        fcn.addWidget(self.state_name_cn_edit, 1)
        svl.addLayout(fcn)

        fcat = QHBoxLayout()
        fcat.addWidget(QLabel("州类别"))
        self.state_category_combo = QComboBox()
        self._populate_state_categories()
        fcat.addWidget(self.state_category_combo, 1)
        svl.addLayout(fcat)

        fmp = QHBoxLayout()
        fmp.addWidget(QLabel("人力"))
        self.state_manpower_spin = QSpinBox()
        self.state_manpower_spin.setRange(0, 100_000_000)
        fmp.addWidget(self.state_manpower_spin, 1)
        svl.addLayout(fmp)

        svl.addWidget(QLabel("资源（resources）"))
        self.state_resources_table = KeyValueTableEditor("资源键", "产量")
        svl.addWidget(self.state_resources_table)
        rescand = QHBoxLayout()
        self.resource_candidate_combo = QComboBox()
        for key, zh in (("steel", "钢"), ("aluminium", "铝"), ("chromium", "铬"),
                        ("oil", "油"), ("rubber", "橡胶"), ("tungsten", "钨")):
            self.resource_candidate_combo.addItem("%s（%s）" % (zh, key), key)
        add_res_btn = QPushButton("＋ 添加候选")
        add_res_btn.clicked.connect(self._add_resource_candidate)
        rescand.addWidget(QLabel("快速添加"))
        rescand.addWidget(self.resource_candidate_combo, 1)
        rescand.addWidget(add_res_btn)
        svl.addLayout(rescand)

        svl.addWidget(QLabel("胜利点（victory_points）"))
        self.state_vp_table = KeyValueTableEditor("地块 pid", "点数")
        svl.addWidget(self.state_vp_table)

        self.state_save_btn = QPushButton("💾 保存州文件")
        self.state_save_btn.clicked.connect(self._save_state_fields)
        svl.addWidget(self.state_save_btn)
        self.state_group.setEnabled(False)
        vl.addWidget(self.state_group)

        self.place_btn = QPushButton("🏗 放置选中建筑")
        self.place_btn.setEnabled(False)
        self.place_btn.setToolTip("把左侧选中的建筑写入当前地块所属州（省级锚定地块，州级写州顶层）")
        self.place_btn.clicked.connect(self._place_building)
        vl.addWidget(self.place_btn)

        self.owner_btn = QPushButton("🔄 改变归属（写 mod 州文件）")
        self.owner_btn.setEnabled(False)
        self.owner_btn.clicked.connect(self._change_owner)
        vl.addWidget(self.owner_btn)

        self.color_btn = QPushButton("🎨 修改国家颜色")
        self.color_btn.setEnabled(False)
        self.color_btn.setToolTip("修改所属国在 common/countries 中的 color（原版自动复制到 mod）")
        self.color_btn.clicked.connect(self._change_country_color)
        vl.addWidget(self.color_btn)

        self.clear_sel_btn = QPushButton("✕ 清空选区")
        self.clear_sel_btn.setVisible(False)
        self.clear_sel_btn.clicked.connect(self.canvas.clear_selection)
        vl.addWidget(self.clear_sel_btn)
        self.copy_btn = QPushButton("📋 复制选区 id 列表")
        self.copy_btn.setVisible(False)
        self.copy_btn.clicked.connect(self._copy_pids)
        vl.addWidget(self.copy_btn)
        vl.addStretch(1)
        return panel

    # ------------------------------------------------------------ 图层
    def _rebuild_layers(self):
        self.canvas.clear_overlays()
        if self.chk_country.isChecked():
            try:
                by_owner = self.state_data.owner_province_map()
                owner_by_pid = {
                    pid: tag
                    for tag, pids in by_owner.items()
                    for pid in pids
                }
                pm = self.map_data.country_overlay_pixmap(
                    owner_by_pid, tag_colors=self.country_colors)
                self.canvas.set_overlay("country", pm, z=10)
            except Exception:
                pass
        if self.chk_border.isChecked():
            self.canvas.set_overlay("border",
                                    self.map_data.edge_overlay_pixmap(), z=11)
        if self.chk_terrain.isChecked():
            pm = self.map_data.terrain_pixmap()
            if pm is not None:
                self.canvas.set_overlay("terrain", pm, z=12)
            else:
                QMessageBox.information(
                    self, "地形类型", "mod 与游戏中都没有 map/terrain.bmp")
                self.chk_terrain.blockSignals(True)
                self.chk_terrain.setChecked(False)
                self.chk_terrain.blockSignals(False)
        if self.chk_hillshade.isChecked():
            pm = self.map_data.hillshade_pixmap()
            if pm is not None:
                self.canvas.set_overlay("hillshade", pm, z=13)
            else:
                QMessageBox.information(
                    self, "地形立体感", "mod 与游戏中都没有 map/heights.bmp")
                self.chk_hillshade.blockSignals(True)
                self.chk_hillshade.setChecked(False)
                self.chk_hillshade.blockSignals(False)
        if self.chk_ai_theaters.isChecked():
            pids = self._ai_theater_province_ids()
            if pids:
                pm = self.map_data.theater_outline_pixmap(pids)
                self.canvas.set_overlay("ai_theaters", pm, z=14)
        # 数据层覆盖层跟随刷新
        self._apply_data_layer()

    # ------------------------------------------------------------ 数据层

    def _on_data_layer_changed(self, _text):
        self._apply_data_layer()

    @staticmethod
    def _rgba_to_pixmap(rgba):
        """numpy HxWx4 RGBA -> QPixmap（UI 层）。"""
        from PyQt6.QtGui import QImage, QPixmap
        h, w = rgba.shape[0], rgba.shape[1]
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(img)

    def _apply_data_layer(self):
        self.canvas.remove_overlay("data_layer")
        key = self.data_layer_combo.currentText()
        if key == "无":
            return
        idm = self.map_data.id_map
        if idm is None:
            return
        try:
            if key == "胜利点 VP":
                vp, _ = state_vp_and_resources(self.state_data.states)
                rgba, x0, y0 = build_value_overlay(idm, vp, alpha=150)
            elif key == "资源总量":
                _, res = state_vp_and_resources(self.state_data.states)
                rgba, x0, y0 = build_value_overlay(idm, res, alpha=150)
            elif key == "补给区":
                areas, _meta = load_supply_areas(self.mod_path,
                                                 self.game_path)
                pid_area = {}
                for sid, aid in areas.items():
                    info = self.state_data.states.get(sid)
                    if info:
                        for pid in info.get("provinces", []):
                            pid_area[pid] = aid
                rgba, x0, y0 = build_categorical_overlay(
                    idm, pid_area, alpha=150)
            elif key == "铁路":
                self.map_data.precompute_centroids()
                segs = load_railways(self.mod_path, self.game_path)
                rgba, x0, y0 = build_line_overlay(
                    int(idm.shape[1]), int(idm.shape[0]), segs,
                    self.map_data.province_centroid, alpha=220)
            elif key == "河流":
                rivers_path = ""
                for base in (self.game_path, self.mod_path):
                    if base and os.path.isfile(
                            os.path.join(base, "map", "rivers.bmp")):
                        rivers_path = os.path.join(base, "map", "rivers.bmp")
                        break
                rgba, x0, y0 = build_river_overlay(rivers_path, alpha=170)
            else:
                return
        except Exception as e:
            QMessageBox.information(self, "数据层", "生成失败：%s" % e)
            return
        if rgba is None:
            return
        pm = self._rgba_to_pixmap(rgba)
        if pm is not None and not pm.isNull():
            self.canvas.set_overlay_pos("data_layer", pm, x0, y0, z=15)

    def _ai_theater_province_ids(self):
        """返回所有 AI 派系战区覆盖的地块 ID 集合。"""
        theaters = load_ai_faction_theaters(self.mod_path, self.game_path)
        if not theaters:
            return set()
        # 战略区域 ID -> 地块 ID
        region_pids = {}
        for base in (self.mod_path, self.game_path):
            if not base:
                continue
            d = os.path.join(base, "map", "strategicregions")
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if not name.lower().endswith(".txt"):
                    continue
                try:
                    with open(os.path.join(d, name), "r", encoding="utf-8-sig",
                              errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                for r in parse_region_file(content, "strategic_region"):
                    region_pids.setdefault(r["id"], set()).update(r["provinces"])
        out = set()
        for t in theaters.values():
            for rid in t.get("regions", []):
                try:
                    out.update(region_pids.get(int(rid), set()))
                except Exception:
                    continue
        return out

    def _open_theater_list(self):
        from ai_faction_theater_editor_dialog import open_ai_faction_theater_list
        open_ai_faction_theater_list(
            None, mod_path=self.mod_path, hoi4_path=self.game_path,
            parent=self)

    def _setup_vector_borders(self):
        """构建矢量层（放大不模糊；带磁盘缓存，首次构建后秒开）。

        矢量边界线 v1 + 矢量多边形填充 v2（省内部也矢量渲染）。
        """
        self.status_label.setText("正在构建矢量层（边界线 + 多边形填充）…")
        self.status_label.repaint()
        try:
            from map_vector import get_edge_segments
            segs = get_edge_segments(self.map_data)
            self.canvas.enable_vector_borders(segs)
            nseg = segs.shape[0] if segs is not None else 0
            extra = ""
            try:
                from map_fill import get_province_polygons
                fill = get_province_polygons(self.map_data)
                if fill is not None:
                    self.canvas.enable_vector_fill(fill)
                    extra = "，多边形填充 %d 环" % fill.n_loops
            except Exception:
                pass
            self.status_label.setText(
                "矢量层就绪（%d 条线段%s，放大 2.5 倍以上自动启用）"
                % (nseg, extra))
        except Exception as e:
            self.status_label.setText("矢量层构建失败：%s" % e)

    # ------------------------------------------------------------ 模式
    def _set_mode(self, mode):
        self.canvas.set_mode(mode)
        tips = {MODE_PAN: "手型：拖拽平移；单击/悬停查看地块信息；滚轮缩放",
                MODE_POINT: "点选：点击地块查看信息",
                MODE_PAINT: "涂色：点击地块修改归属（写入 mod 州文件，可撤销）",
                MODE_RECT: "框选：拖拽矩形，释放后加入选区",
                MODE_MULTI: "多选：逐个点选地块加入/移出选区"}
        self.status_label.setText(tips.get(mode, ""))

    # ------------------------------------------------------------ 信息
    def _state_category_name(self, cat):
        """州类别中文名：STATE_CATEGORY_<cat> 优先，raw key 兜底。"""
        for key in ("STATE_CATEGORY_" + cat, cat):
            try:
                cn = self._loc_manager.get_name(key)
                if cn:
                    return "%s（%s）" % (cn, cat)
            except Exception:
                pass
        return cat

    def _populate_state_categories(self):
        """填充州类别下拉（中文名 + 原始键存 UserRole）。"""
        self.state_category_combo.clear()
        for cat in sorted(self.state_data.categories.keys()):
            self.state_category_combo.addItem(
                self._state_category_name(cat), cat)

    def _add_resource_candidate(self):
        """把候选资源键加入资源表（值为 0，用户再改产量）。"""
        key = self.resource_candidate_combo.currentData()
        if key:
            self.state_resources_table.add_row(key, "0")

    def _load_state_edit_form(self, sid):
        st = self.state_data.states.get(sid)
        if st is None:
            self.state_group.setEnabled(False)
            return
        self.state_group.setEnabled(True)
        self.state_id_label.setText(str(sid))
        name_key = st.get("name_key", "")
        self.state_name_edit.setText(name_key)
        try:
            cn = self._loc_manager.get_name(name_key) if name_key else ""
        except Exception:
            cn = ""
        self.state_name_cn_edit.setText(cn or "")

        cat = st.get("state_category", "")
        idx = self.state_category_combo.findData(cat)
        if idx >= 0:
            self.state_category_combo.setCurrentIndex(idx)
        else:
            self.state_category_combo.addItem(self._state_category_name(cat), cat)
            self.state_category_combo.setCurrentIndex(
                self.state_category_combo.count() - 1)

        self.state_manpower_spin.setValue(int(st.get("manpower", 0) or 0))
        res = st.get("resources") or {}
        self.state_resources_table.set_data(
            [(k, str(v)) for k, v in res.items()])
        vp = st.get("victory_points") or []
        self.state_vp_table.set_data(
            [(str(pid), str(pts)) for pid, pts in vp])

    def _save_state_fields(self):
        if self._current_pid <= 0:
            return
        sid = self.state_data.state_of_province(self._current_pid)
        if not sid:
            QMessageBox.information(self, "保存", "当前地块不属于任何州。")
            return
        # 确保 state_data 有该州源文件
        st = self.state_data.states.get(sid)
        if not st or not st.get("src"):
            QMessageBox.critical(self, "保存失败", "找不到州文件。")
            return
        from state_build_ops import (
            set_state_category_in_content,
            set_state_resources_in_content,
            set_state_victory_points_in_content,
            set_state_manpower_in_content,
            set_state_name_in_content,
            ensure_file_in_mod,
        )
        from localisation_editor_data import (
            default_mod_loc_file, find_mod_file_for_key, upsert_loc_entry,
        )
        from write_utils import atomic_write_text
        try:
            src = st["src"]
            if src.startswith(self.mod_path or ""):
                fp = src
            elif self.game_path and src.startswith(self.game_path):
                rel = os.path.relpath(src, self.game_path).replace("\\", "/")
                fp, _ = ensure_file_in_mod(self.mod_path, self.game_path, rel)
            else:
                fp = src
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()

            resources = {}
            for k, v in self.state_resources_table.rows():
                k = k.strip()
                if not k:
                    continue
                try:
                    resources[k] = int(float(v))
                except ValueError:
                    resources[k] = 0
            vp_pairs = []
            for pid, pts in self.state_vp_table.rows():
                if not pid.strip() and not pts.strip():
                    continue
                try:
                    vp_pairs.append((int(float(pid)), int(float(pts))))
                except ValueError:
                    continue

            category = self.state_category_combo.currentData()
            if category:
                content = (set_state_category_in_content(
                    content, sid, category) or content)
            content = (set_state_resources_in_content(
                content, sid, resources) or content)
            content = (set_state_victory_points_in_content(
                content, sid, vp_pairs) or content)
            content = (set_state_manpower_in_content(
                content, sid, self.state_manpower_spin.value()) or content)
            name_key = self.state_name_edit.text().strip()
            if name_key:
                content = (set_state_name_in_content(
                    content, sid, name_key) or content)
            atomic_write_text(fp, content)

            name_cn = self.state_name_cn_edit.text().strip()
            if name_key and name_cn:
                loc_fp = (find_mod_file_for_key(
                    self.mod_path, name_key, "simp_chinese")
                    or default_mod_loc_file(self.mod_path, "simp_chinese"))
                if loc_fp:
                    upsert_loc_entry(loc_fp, name_key, name_cn, "simp_chinese")

            self.state_data.reload()
            self.info_label.setText(self._province_desc(self._current_pid))
            self._load_state_edit_form(sid)
            QMessageBox.information(self, "已保存", "州文件已保存。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _province_desc(self, pid):
        """地块完整信息（地块/州/类别/建筑位/建筑/归属/国家颜色）。"""
        md = self.map_data
        info = md.province_table.get(pid, {})
        typ = info.get("type", "?")
        coastal = "是" if info.get("coastal") else "否"
        terrain = info.get("terrain", "?")
        lines = ["地块 %d" % pid,
                 "类型 %s ｜ 海岸 %s ｜ 地形 %s" % (typ, coastal, terrain)]
        sid = self.state_data.state_of_province(pid)
        if sid:
            sname = self.state_data.state_name(sid)
            cat = self.state_data.states.get(sid, {}).get(
                "state_category", "")
            slots = self.state_data.slots_of(sid)
            manpower = self.state_data.states.get(sid, {}).get(
                "manpower", 0)
            lines.append("州 %d%s ｜ 类别 %s ｜ 建筑位 %d"
                         % (sid, "（%s）" % sname if sname else "",
                            cat or "?", slots))
            if manpower:
                lines.append("人力 %s" % format(manpower, ","))
            bd = self.state_data.buildings_of(sid)
            if bd:
                btext = "  ".join(
                    "%s %d" % (self._building_name(k), v)
                    for k, v in sorted(bd.items()))
                lines.append("建筑: %s" % btext)
            else:
                lines.append("建筑: 无")
        owner = self.state_data.owner_of_province(pid)
        if owner:
            color = self.country_colors.get(owner)
            color_txt = ""
            if color:
                color_txt = " 颜色 #%02X%02X%02X" % color
            lines.append("所属国 %s%s" % (owner, color_txt))
        else:
            lines.append("所属国 无主")
        return "\n".join(lines)

    def _on_province_clicked(self, pid, x, y):
        """点选地块：进入选中（黄色层）+ 右侧信息面板完整刷新。"""
        self._current_pid = pid
        # 点选 = 单选（替换选中集；多选/框选流程不受影响）
        if pid > 0:
            self.canvas.set_selection([pid])
        self.info_label.setText(self._province_desc(pid))
        sid = self.state_data.state_of_province(pid)
        self._load_state_edit_form(sid or 0)
        self.place_btn.setEnabled(pid > 0)
        self.owner_btn.setEnabled(pid > 0)
        self.color_btn.setEnabled(
            pid > 0 and bool(self.state_data.owner_of_province(pid)))

    def _selected_building(self):
        btn = self.building_group.checkedButton()
        if btn is None:
            return None
        return self._building_btn_map.get(btn)

    # ------------------------------------------------------------ 建筑图标/名称
    def _load_building_icons(self):
        """按建筑定义来源加载对应图集并裁剪（mod/游戏帧布局可能不同）。

        帧宽 = strip 宽 / GFX_buildings_strip 的 noOfFrames（mod 3350890356
        为 26 帧 45px，游戏为 31 帧 46px）；frame 超界或无定义跳过。
        """
        from building_lib import strip_frame_count
        self._building_icons = {}
        # 按来源缓存 (strip_path, 帧宽, 帧高)
        strip_cache = {}
        for b in self.building_types:
            frame = b.get("icon_frame")
            if frame is None:
                continue
            src = b.get("src", "game")
            base = self.mod_path if src == "mod" else self.game_path
            if not base:
                continue
            info = strip_cache.get(src)
            if info is None:
                strip_path = os.path.join(base, "gfx", "interface",
                                          "buildings",
                                          "building_icon_strip.dds")
                if not os.path.isfile(strip_path):
                    strip_cache[src] = (None, 0, 0)
                    continue
                n = strip_frame_count(base)
                if n <= 0:
                    strip_cache[src] = (None, 0, 0)
                    continue
                try:
                    from dds_loader import DdsLoader
                    pm = DdsLoader.load_as_pixmap(strip_path)
                except Exception:
                    pm = None
                if pm is None or pm.isNull():
                    strip_cache[src] = (None, 0, 0)
                    continue
                fw = pm.width() / float(n)
                info = (pm, fw, pm.height())
                strip_cache[src] = info
            pm, fw, fh = info
            if pm is None:
                continue
            x = int(round(frame * fw))
            w = max(2, int(fw) - 2)          # 内部内容宽（留 1px 边距）
            if x + 2 > pm.width():
                continue
            icon = pm.copy(x, 0, min(w, pm.width() - x), fh)
            self._building_icons[b["key"]] = icon.scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)

    def _building_name(self, key):
        """建筑中文名（buildings_l_english.yml 的键 = 建筑键），回退 key。"""
        try:
            name = self._loc_manager.get_name(key)
            if name:
                return name
        except Exception:
            pass
        return key

    def _building_desc(self, key):
        """建筑描述（<key>_desc）：中文优先，回退英语 yml，再回退空。"""
        try:
            d = self._loc_manager.get_name(key + "_desc")
            if d:
                return d
        except Exception:
            pass
        for base in (self.mod_path, self.game_path):
            if not base:
                continue
            fp = os.path.join(base, "localisation", "english",
                              "buildings_l_english.yml")
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    for line in f:
                        m = re.match(
                            r'\s*%s_desc\s*:\s*"(.*)"\s*$'
                            % re.escape(key), line)
                        if m:
                            return m.group(1)
            except Exception:
                pass
        return ""

    def _building_effects(self, b):
        """建筑在游戏内的效果（state/country_modifiers，中文修饰名）。"""
        mods = b.get("modifiers") or []
        if not mods:
            return ""
        lines = []
        for scope, label in (("state", "州"), ("country", "国")):
            sel = [m for m in mods if m["scope"] == scope]
            if not sel:
                continue
            parts = ["%s %s" % (self._modifier_name(m["key"]),
                                _fmt_modifier_value(m["value"]))
                     for m in sel]
            lines.append("效果（%s）: %s" % (label, "，".join(parts)))
        return "\n".join(lines)

    def _modifier_name(self, key):
        """修饰键中文名：MODIFIER_<KEY> / raw key / 英语 yml，逐级回退。"""
        for cand in ("MODIFIER_" + key.upper(), key):
            try:
                name = self._loc_manager.get_name(cand)
                if name:
                    return name
            except Exception:
                pass
        for base in (self.mod_path, self.game_path):
            if not base:
                continue
            fp = os.path.join(base, "localisation", "english",
                              "modifiers_l_english.yml")
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    for line in f:
                        m = re.match(
                            r'\s*(?:MODIFIER_%s|%s)\s*:\s*"(.*)"\s*$'
                            % (re.escape(key.upper()), re.escape(key)),
                            line)
                        if m:
                            return m.group(1)
            except Exception:
                pass
        return key

    def _place_building(self):
        """放置选中建筑到当前地块所属州（省级锚定地块，州级写州顶层）。"""
        pid = self._current_pid
        if pid <= 0:
            return
        b = self._selected_building()
        if b is None:
            QMessageBox.information(self, "放置建筑", "请先在左侧选择建筑类型")
            return
        sid = self.state_data.state_of_province(pid)
        if not sid:
            QMessageBox.information(self, "放置建筑",
                                    "地块 %d 不属于任何州（可能是海/湖）" % pid)
            return
        btype = b["key"]
        anchor_pid = pid if b["provincial"] else None
        level, ok = QInputDialog.getInt(
            self, "放置建筑",
            "建筑 %s（%s级）\n写入州 %d%s\n等级（0 = 移除）："
            % (btype, "省" if anchor_pid else "州", sid,
               "，锚定地块 %d" % anchor_pid if anchor_pid else ""),
            1, 0, 99)
        if not ok:
            return
        from state_build_ops import set_state_building
        ok_w, message, rel = set_state_building(
            self.mod_path, self.game_path, sid, btype, level,
            pid=anchor_pid, state_data=self.state_data)
        if not ok_w:
            QMessageBox.warning(self, "放置建筑",
                                "写入失败：%s" % message)
            return
        self.state_data.reload()
        self.map_data.invalidate_country_overlays()
        self._rebuild_layers()
        self.info_label.setText(
            "已写入 %s = %d → %s%s"
            % (btype, level, rel,
               "（原版已复制到 mod）" if message == "copied_written" else ""))
        self._on_province_clicked(pid, 0, 0)

    def _change_owner(self):
        """改变当前地块所属州归属（写 mod 州文件，可撤销）。"""
        pid = self._current_pid
        if pid <= 0:
            return
        sid = self.state_data.state_of_province(pid)
        if not sid:
            QMessageBox.information(
                self, "改变归属", "地块 %d 不属于任何州（可能是海/湖）" % pid)
            return
        current = self.state_data.owner_of_province(pid)
        owners = self.state_data.owners()
        tag, ok = QInputDialog.getItem(
            self, "改变归属", "地块 %d 的新归属国家（州 %d，当前 %s）："
            % (pid, sid, current or "无主"),
            owners + ["（清除 owner）"], 0, True)
        if not ok:
            return
        tag = (tag or "").strip().upper()
        if tag in ("（清除 OWNER）", "（清除owner）"):
            tag = ""
        from state_edit_ops import set_state_owner
        ok_written, message, rel = set_state_owner(
            self.mod_path, sid, tag, self.state_data)
        if not ok_written:
            if message == "not_in_mod":
                QMessageBox.warning(
                    self, "改变归属",
                    "州 %d 定义在游戏本体中（mod 未覆盖）。\n"
                    "请在 mod 的 history/states/ 下覆盖该州后再编辑归属。"
                    % sid)
            else:
                QMessageBox.warning(self, "改变归属",
                                    "未能写回州 %d：%s" % (sid, message))
            return
        if sid in self.state_data.states:
            self.state_data.states[sid]["owner"] = tag
        self.map_data.invalidate_country_overlays()
        self._rebuild_layers()
        self.info_label.setText(
            "已把州 %d 归属改为 %s（%s）" % (sid, tag or "无主", rel))
        self._on_province_clicked(pid, 0, 0)

    def _change_country_color(self):
        """修改当前地块所属国的国家颜色（原版自动复制到 mod）。"""
        pid = self._current_pid
        if pid <= 0:
            return
        tag = self.state_data.owner_of_province(pid)
        if not tag:
            QMessageBox.information(self, "修改国家颜色", "该地块无主")
            return
        current = self.country_colors.get(tag, (128, 128, 128))
        from PyQt6.QtGui import QColor
        color = QColorDialog.getColor(
            QColor(*current), self, "修改 %s 的国家颜色" % tag)
        if not color.isValid():
            return
        rgb = (color.red(), color.green(), color.blue())
        from state_build_ops import set_country_color
        ok_w, message, rel = set_country_color(
            self.mod_path, self.game_path, tag, rgb)
        if not ok_w:
            QMessageBox.warning(self, "修改国家颜色",
                                "写入失败：%s" % message)
            return
        self.country_colors = load_country_colors(self.mod_path,
                                                  self.game_path)
        self.map_data.invalidate_country_overlays()
        self._rebuild_layers()
        self.info_label.setText(
            "已把 %s 颜色改为 #%02X%02X%02X → %s%s"
            % (tag, rgb[0], rgb[1], rgb[2], rel,
               "（原版已复制到 mod）" if message == "copied_written" else ""))
        self._on_province_clicked(pid, 0, 0)

    # ------------------------------------------------------------ 涂色
    def _on_paint(self, pid):
        """涂色模式点击：复用右侧「改变归属」流程。"""
        self._current_pid = pid
        self._change_owner()

    # ------------------------------------------------------------ 框选/选区
    def _on_rect_selected(self, pids, x0, y0, x1, y1):
        self._last_pids = list(pids)
        states = []
        for p in pids:
            sid = self.state_data.state_of_province(p)
            if sid and sid not in states:
                states.append(sid)
        self.info_label.setText(
            "框选 %d 个地块（%d,%d → %d,%d）｜涉及 %d 个州%s"
            % (len(pids), x0, y0, x1, y1, len(states),
               "：%s" % ", ".join(str(s) for s in states[:12])
               if states else ""))

    def _update_state_outline(self, pids):
        """根据选中地块更新州轮廓高亮（黄色描边圈出涉及的州）。"""
        states_pids = []
        seen = set()
        for p in pids:
            sid = self.state_data.state_of_province(p)
            if sid and sid not in seen:
                seen.add(sid)
                info = self.state_data.states.get(sid)
                if info and info.get("provinces"):
                    states_pids.append(info["provinces"])
        if states_pids:
            self.canvas.set_state_outlines(states_pids)
        else:
            self.canvas.clear_state_outlines()

    def _on_selection_changed(self, pids):
        """选区变化（框选/多选）：更新反馈按钮、提示与州轮廓高亮。"""
        self._last_pids = list(pids)
        self._update_state_outline(pids)
        has = bool(pids)
        self.copy_btn.setVisible(has)
        self.clear_sel_btn.setVisible(has)
        if has and not self.info_label.text().startswith("框选"):
            states = []
            for p in pids:
                sid = self.state_data.state_of_province(p)
                if sid and sid not in states:
                    states.append(sid)
            self.info_label.setText(
                "已选 %d 个地块｜涉及 %d 个州%s"
                % (len(pids), len(states),
                   "：%s" % ", ".join(str(s) for s in states[:12])
                   if states else ""))

    def _copy_pids(self):
        if not self._last_pids:
            return
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(
            " ".join(str(p) for p in self._last_pids))
        QMessageBox.information(
            self, "已复制",
            "已复制 %d 个地块 id 到剪贴板（空格分隔）" % len(self._last_pids))

    # ------------------------------------------------------------ 定位
    def _on_locate(self):
        text = (self.loc_edit.text() or "").strip()
        if not text:
            return
        if text.isdigit():
            pid = int(text)
            md = self.map_data
            if not (0 <= pid < (md.id_map.max() + 1 if md.id_map is not None else 0)):
                QMessageBox.information(self, "定位", "地块 %d 不存在" % pid)
                return
            c = md.province_centroid(pid)
            if c:
                self.canvas.center_on_pixel(c[0], c[1])
                self.canvas.highlight_pids([pid])
                self._update_state_outline([pid])
                self.info_label.setText(self._province_desc(pid))
            return
        tag = text.upper()
        owner = self.state_data.owner_province_map()
        centroids = self.map_data.country_centroids(owner)
        if tag not in centroids:
            QMessageBox.information(self, "定位", "国家 %s 没有领土" % tag)
            return
        cx, cy = centroids[tag]
        self.canvas.center_on_pixel(cx, cy)
        self.canvas.highlight_pids(owner.get(tag, []))
        self._update_state_outline(owner.get(tag, []))
        self.info_label.setText("已定位到 %s 领土（%d 个地块）"
                                % (tag, len(owner.get(tag, []))))


def _fmt_modifier_value(v):
    """修饰值显示：|v|<1 的系数显示为百分比，其余显示原值。"""
    if v == 0:
        return "0"
    if abs(v) < 1:
        return "%+d%%" % round(v * 100)
    if float(v).is_integer():
        return str(int(v))
    return str(v)
