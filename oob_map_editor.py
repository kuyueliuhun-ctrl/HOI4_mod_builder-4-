"""初始部队地图放置窗口

加载游戏/mod 地图文件绘制所有地块，显示海军/空军基地锚点，
按游戏兵牌样式展示已放置的陆军部队；选择编制后点击地块放置部队。
"""

import os

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPixmap, QPen
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsSimpleTextItem, QGraphicsItem, QMenu, QInputDialog, QToolTip
)

from map_loader import MapData
from state_loader import StateData
from oob_loader import DivisionPlacement
from localization_mgr import get_localization_manager

# 地图数据缓存（地图文件大，避免重复加载）
_MAP_CACHE = {}
_STATE_CACHE = {}


def get_map_data(mod_path, hoi4_path):
    key = (mod_path, hoi4_path)
    if key not in _MAP_CACHE:
        _MAP_CACHE[key] = MapData(mod_path, hoi4_path)
    return _MAP_CACHE[key]


def get_state_data(mod_path, hoi4_path):
    key = (mod_path, hoi4_path)
    if key not in _STATE_CACHE:
        _STATE_CACHE[key] = StateData(
            mod_path, hoi4_path,
            loc_manager=get_localization_manager())
    return _STATE_CACHE[key]


COUNTER_W = 90
COUNTER_H = 25
# 初始缩放倍数（全景之上再放大，使地块细节清晰）
DEFAULT_ZOOM = 30.0

# 兵牌底层矩形颜色（与兵牌相近的绿色）+ 数量区占矩形比例
COUNTER_BG = QColor(62, 92, 66)
NUM_RATIO = 1.0 / 4

# 小号锚点字体（场景坐标，随地图缩放；放大后无需对基地操作）
ANCHOR_FONT_SIZE = 6.0

# 兵牌底图缓存：兵种类型 -> QPixmap
_COUNTER_CACHE = {}


def _make_anchor_item(char, color):
    """生成锚点文字 item（矢量文本，随缩放重新光栅化，不失真）。"""
    item = QGraphicsSimpleTextItem(char)
    font = item.font()
    font.setPointSizeF(ANCHOR_FONT_SIZE)
    item.setFont(font)
    item.setBrush(QColor(color))
    return item


class MapView(QGraphicsView):
    """地图视图：平移/缩放/点击/悬停 + 兵牌/国家名覆盖绘制。

    兵牌与国家名在 paintEvent 中随每次视图重绘换算场景坐标绘制，
    缩放/平移后位置始终与地块对齐（不依赖独立覆盖层的刷新时机）。
    """

    hover_moved = pyqtSignal(int, int)        # viewport 坐标
    canvas_clicked = pyqtSignal(int, int)     # viewport 坐标
    canvas_context = pyqtSignal(int, int, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHints(QPainter.RenderHint.Antialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        # 完整重绘视图，避免平移/缩放时兵牌残留错位
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._press_pos = None
        self.screen_counters = []   # list[ScreenCounter]
        self.country_labels = []    # [(scene_x, scene_y, 名称), ...]

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self.viewport())
        p.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform |
                         QPainter.RenderHint.Antialiasing |
                         QPainter.RenderHint.TextAntialiasing)
        # 国家名称（恒定屏幕大小，锚定各国领土中心）
        if self.country_labels:
            font = p.font()
            font.setPointSizeF(9.0)
            p.setFont(font)
            for sx, sy, name in self.country_labels:
                vp = self.mapFromScene(QPointF(sx, sy))
                rect = QRectF(vp.x() - 100, vp.y() - 9, 200, 18)
                p.setPen(QPen(QColor(15, 15, 15), 3))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)
                p.setPen(QPen(QColor(255, 255, 255)))
                p.setBrush(QColor(255, 255, 255))
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)
        # 兵牌（恒定屏幕大小，锚定地块中心；聚合：不透明绿底矩形 + 白框黑底兵牌 + 数量）
        for c in self.screen_counters:
            vp = self.mapFromScene(QPointF(*c.scene_point))
            rect = QRectF(vp.x() - COUNTER_W / 2, vp.y() - COUNTER_H / 2,
                          COUNTER_W, COUNTER_H)
            # 底层矩形：不透明绿色 + 黑边（drawRect 会用当前 brush 填充，
            # 必须先清空 brush，否则标签的白色 brush 会把整块刷白）
            p.fillRect(rect, COUNTER_BG)
            p.setPen(QPen(QColor(0, 0, 0), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(rect)
            # 左侧兵牌区：白框黑底
            num_w = rect.width() * NUM_RATIO
            icon_rect = QRectF(rect.x(), rect.y(),
                               rect.width() - num_w, rect.height())
            inner = icon_rect.adjusted(2, 2, -2, -2)
            p.fillRect(inner, QColor(18, 18, 18))
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(inner)
            src = c.pixmap
            scaled = src.scaled(int(inner.width()), int(inner.height()),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            dx = (inner.width() - scaled.width()) / 2
            dy = (inner.height() - scaled.height()) / 2
            p.drawPixmap(inner.x() + dx, inner.y() + dy, scaled)
            # 右侧数量数字（1/4 区）
            num_rect = QRectF(rect.x() + rect.width() - num_w, rect.y(),
                              num_w, rect.height())
            font = p.font()
            font.setPointSizeF(11.0)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(255, 255, 255))
            p.setBrush(QColor(255, 255, 255))
            p.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(c.count))
            if c.selected:
                p.setPen(QPen(QColor(255, 215, 0), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(rect.adjusted(-1, -1, 1, 1))
        p.end()

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 1.0 / 1.25
        self.scale(factor, factor)

    def hit_counter(self, vp_pos):
        """按 viewport 坐标命中兵牌，返回 ScreenCounter 或 None。"""
        for c in self.screen_counters:
            vp = self.mapFromScene(QPointF(*c.scene_point))
            if abs(vp.x() - vp_pos.x()) <= COUNTER_W / 2 + 2 \
                    and abs(vp.y() - vp_pos.y()) <= COUNTER_H / 2 + 2:
                return c
        return None

    def refresh_counters(self):
        self.viewport().update()

    def mousePressEvent(self, event):
        self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        vp = event.position().toPoint()
        self.hover_moved.emit(vp.x(), vp.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 仅当按下与释放位置接近时视为点击（区分拖拽平移）
        if self._press_pos is not None:
            dist = (event.position().toPoint() - self._press_pos).manhattanLength()
            if dist < 5:
                vp = event.position().toPoint()
                if event.button() == Qt.MouseButton.LeftButton:
                    self.canvas_clicked.emit(vp.x(), vp.y())
                elif event.button() == Qt.MouseButton.RightButton:
                    self.canvas_context.emit(vp.x(), vp.y(),
                                             event.globalPosition().toPoint())
        self._press_pos = None
        super().mouseReleaseEvent(event)


class ScreenCounter:
    """屏幕层兵牌：固定屏幕大小的部队图标（同地块部队聚合为一个兵牌）。"""

    def __init__(self, placement, scene_point, pixmap):
        self.placement = placement
        self.scene_point = scene_point   # 地块中心（场景坐标）
        self.pixmap = pixmap
        self.count = 1                   # 该地块部队数量
        self.selected = False

    def info_text(self):
        txt = (f"{self.placement.name}\n模板: {self.placement.division_template}"
               + (f"\n经验: {self.placement.start_experience_factor}"
                  if self.placement.start_experience_factor is not None else "")
               + f"\n地块: {self.placement.location}")
        if self.count > 1:
            txt += f"\n本地块共 {self.count} 支"
        return txt


def _counter_pixmap(typ, sub_units, gfx_map, mod_path, hoi4_path):
    """兵牌底图：GFX_unit_<type>_icon_medium 缩放为兵牌尺寸（按兵种缓存）。"""
    if typ in _COUNTER_CACHE:
        return _COUNTER_CACHE[typ]
    from icon_resolver import resolve_pixmap
    pm = None
    try:
        pm = resolve_pixmap(f"GFX_unit_{typ}_icon_medium", gfx_map=gfx_map,
                            mod_path=mod_path, hoi4_path=hoi4_path)
    except Exception:
        pm = None
    if pm is None or pm.isNull():
        pm = QPixmap(COUNTER_W, COUNTER_H)
        pm.fill(QColor(18, 18, 18))
    pm = pm.scaled(COUNTER_W, COUNTER_H,
                   Qt.AspectRatioMode.KeepAspectRatio,
                   Qt.TransformationMode.SmoothTransformation)
    _COUNTER_CACHE[typ] = pm
    return pm


class OobMapEditor(QDialog):
    """初始部队地图放置编辑器。"""

    map_saved = pyqtSignal()

    def __init__(self, oob_file, sub_units=None, gfx_map=None,
                 mod_path="", hoi4_path="", country_tag="", parent=None):
        super().__init__(parent)
        self.oob_file = oob_file
        self.sub_units = sub_units or {}
        self.gfx_map = gfx_map or {}
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.country_tag = (country_tag or "").upper()

        self.map_data = get_map_data(mod_path, hoi4_path)
        self.state_data = get_state_data(mod_path, hoi4_path)

        self.place_mode = False
        self.counters = []          # list[ArmyCounter]
        self.highlight_item = None  # 悬停地块高亮
        self._current_highlight_pid = 0
        # 地块高亮 LRU 缓存：(pid, 模式) -> (pixmap, x0, y0)
        from collections import OrderedDict
        self._highlight_cache = OrderedDict()

        # 批量预计算全部地块中心（基地/兵牌定位使用）
        self.map_data.precompute_centroids()

        self.setWindowTitle(
            f"初始陆军部队 — 地图放置"
            + (f"（{self.country_tag}）" if self.country_tag else ""))
        self.resize(1200, 800)
        self._build_ui()
        self._draw_bases()
        self._rebuild_counters()

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("选择编制:"))
        self.tpl_combo = QComboBox()
        self.tpl_combo.setMinimumWidth(240)
        for t in self.oob_file.templates:
            self.tpl_combo.addItem(t.name)
        bar.addWidget(self.tpl_combo)

        self.place_btn = QPushButton("放置模式")
        self.place_btn.setCheckable(True)
        self.place_btn.toggled.connect(self._on_place_mode)
        bar.addWidget(self.place_btn)

        self.fit_btn = QPushButton("⌂ 全景")
        self.fit_btn.clicked.connect(lambda: self.view.fitInView(
            self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))
        bar.addWidget(self.fit_btn)

        bar.addStretch(1)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)
        bar.addWidget(self.save_btn)
        root.addLayout(bar)

        self.view = MapView()
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        root.addWidget(self.view, 1)

        self.status_label = QLabel("就绪")
        root.addWidget(self.status_label)

        # 底图（provinces.bmp 平坦地块色，地形不影响地图颜色）
        pm = self.map_data.base_pixmap()
        self.base_item = QGraphicsPixmapItem(pm)
        self.base_item.setCacheMode(
            QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.scene.addItem(self.base_item)
        # 国家着色图层（统一国家色块 + 地块边界线 + 国界线 + 焦点金边）
        self.country_item = None
        owner_by_pid = {}
        try:
            owner_by_pid = {
                pid: tag
                for tag, pids in self.state_data.owner_province_map().items()
                for pid in pids
            }
        except Exception:
            owner_by_pid = {}
        try:
            country_pm = self.map_data.country_overlay_pixmap(
                owner_by_pid, focus_tag=self.country_tag)
            if not country_pm.isNull():
                self.country_item = QGraphicsPixmapItem(country_pm)
                self.country_item.setZValue(2)
                self.country_item.setCacheMode(
                    QGraphicsItem.CacheMode.DeviceCoordinateCache)
                self.scene.addItem(self.country_item)
        except Exception:
            pass
        # 国家名称标签（各国领土中心，屏幕恒定大小绘制）
        try:
            loc = get_localization_manager()
            labels = []
            for tag, (cx, cy) in self.map_data.country_centroids(
                    owner_by_pid).items():
                name = ""
                try:
                    name = loc.get_name(tag) or ""
                except Exception:
                    name = ""
                labels.append((cx, cy, name or tag))
            self.view.country_labels = labels
        except Exception:
            pass
        self.scene.setSceneRect(0, 0, pm.width(), pm.height())

        # 悬停高亮
        self.highlight_item = QGraphicsPixmapItem()
        self.highlight_item.setZValue(5)
        self.scene.addItem(self.highlight_item)
        self.highlight_item.hide()

        # 交互
        self.view.hover_moved.connect(self._on_hover)
        self.view.canvas_clicked.connect(self._on_canvas_clicked)
        self.view.canvas_context.connect(self._on_canvas_context)

        # 初始视野：优先定位到编辑文件对应国家的领土（或文件中已放置部队的区域），
        # 否则全景基础上放大 DEFAULT_ZOOM 倍
        focus = self._focus_region()
        if focus:
            xs = [c[0] for c in focus if c]
            ys = [c[1] for c in focus if c]
            if xs:
                pad = 80
                rect = QRectF(min(xs) - pad, min(ys) - pad,
                              max(xs) - min(xs) + pad * 2,
                              max(ys) - min(ys) + pad * 2)
                self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
                self.view.scale(1.2, 1.2)
                return
        self.view.fitInView(self.scene.sceneRect(),
                            Qt.AspectRatioMode.KeepAspectRatio)
        self.view.scale(DEFAULT_ZOOM, DEFAULT_ZOOM)

    def _focus_region(self):
        """定位区域：国家领土地块中心；无领土则用文件中已放置部队的地块。"""
        if self.country_tag:
            pids = self.state_data.provinces_of_owner(self.country_tag)
            if pids:
                return [self.map_data.province_centroid(pid) for pid in pids]
        pids = [p.location for p in self.oob_file.placements if p.location > 0]
        if pids:
            return [self.map_data.province_centroid(pid) for pid in pids]
        return []

    # ---------- 基地绘制 ----------

    def _draw_bases(self):
        """绘制基地锚点：小号矢量文字模型（随地图缩放不失真）。

        同地块多个锚点（海军+空军）分散排列避免重叠；场景 item
        自带悬停 tooltip。
        """
        from collections import defaultdict
        offsets = [(0, 0), (12, -12), (-12, 12), (12, 12), (-12, -12),
                   (0, 16), (16, 0), (-16, 0), (0, -16)]
        by_pid = defaultdict(list)
        for pid, level, sid in self.state_data.naval_bases:
            by_pid[pid].append(("naval", level, sid))
        for pid, level, sid in self.state_data.air_bases:
            by_pid[pid].append(("air", level, sid))
        for pid, anchors in by_pid.items():
            c = self.map_data.province_centroid(pid)
            if not c:
                continue
            for i, (kind, level, sid) in enumerate(anchors):
                ox, oy = offsets[i % len(offsets)]
                item = _make_anchor_item(
                    "⚓" if kind == "naval" else "✈",
                    "#4fc3f7" if kind == "naval" else "#f4b942")
                br = item.boundingRect()
                item.setPos(c[0] + ox - br.width() / 2,
                            c[1] + oy - br.height() / 2)
                item.setZValue(3)
                state_name = self.state_data.state_name(sid)
                label = "海军基地" if kind == "naval" else "空军基地"
                item.setToolTip(f"{label} 等级 {level}\n{state_name} (州 {sid})")
                self.scene.addItem(item)

    # ---------- 兵牌 ----------

    def _rebuild_counters(self):
        """按地块聚合兵牌：同一地块多支部队合并为一个兵牌（左侧图标+右侧数量）。"""
        self.counters = []
        from collections import OrderedDict
        by_loc = OrderedDict()
        for p in self.oob_file.placements:
            by_loc.setdefault(p.location, []).append(p)
        for loc, group in by_loc.items():
            typ = self._placement_type(group[0])
            pm = _counter_pixmap(typ, self.sub_units, self.gfx_map,
                                 self.mod_path, self.hoi4_path)
            c = self.map_data.province_centroid(loc)
            if not c:
                c = (0, 0)
            counter = ScreenCounter(group[0], c, pm)
            counter.count = len(group)
            self.counters.append(counter)
        self.view.screen_counters = self.counters
        self.view.refresh_counters()

    def _placement_type(self, placement):
        """部队主兵种（用于兵牌图标）：取模板首个战斗连。"""
        tpl = self.oob_file.find_template(placement.division_template)
        if tpl and tpl.regiments:
            return tpl.regiments[0][0]
        return "infantry"

    # ---------- 交互 ----------

    def _on_place_mode(self, checked):
        self.place_mode = checked
        if checked:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.view.setCursor(Qt.CursorShape.CrossCursor)
            self.status_label.setText(
                "放置模式：移动鼠标预览地块，点击陆地放置所选编制；"
                "按住 Ctrl 拖动平移")
        else:
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.view.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_label.setText("就绪")

    def _on_hover(self, x, y):
        # 兵牌优先：悬停已放置部队显示部队信息
        counter = self.view.hit_counter(QPoint(x, y))
        if counter is not None:
            p = counter.placement
            extra = f" | 本地块共 {counter.count} 支" if counter.count > 1 else ""
            self.status_label.setText(
                f"部队: {p.name} | 模板: {p.division_template} | 地块: {p.location}{extra}")
            QToolTip.hideText()
            return
        sp = self.view.mapToScene(QPoint(x, y))
        pid = self.map_data.province_at(int(sp.x()), int(sp.y()))
        if pid <= 0:
            self.highlight_item.hide()
            self.status_label.setText("地图外")
            QToolTip.hideText()
            return
        sid = self.state_data.state_of_province(pid)
        info = self.map_data.province_table.get(pid, {})
        kind = info.get("type", "?")
        state_name = self.state_data.state_name(sid) if sid else ""
        self.status_label.setText(
            f"地块 {pid}  [{kind}]  州: {state_name} ({sid})")
        QToolTip.hideText()
        if pid != self._current_highlight_pid:
            self._current_highlight_pid = pid
            self._update_highlight(pid)

    def _update_highlight(self, pid):
        key = (pid, self.place_mode)
        hit = self._highlight_cache.get(key)
        if hit is not None:
            pm, x0, y0 = hit
            self.highlight_item.setPixmap(pm)
            self.highlight_item.setPos(x0, y0)
            self.highlight_item.setZValue(6)
            self.highlight_item.show()
            return
        mask = self.map_data.province_mask(pid)
        if mask is None or not mask.any():
            self.highlight_item.hide()
            return
        ys, xs = np.nonzero(mask)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        sub = mask[y0:y1 + 1, x0:x1 + 1]
        h, w = sub.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 3] = np.where(sub, 160, 0)
        if self.place_mode:
            # 放置模式：亮黄
            rgba[..., 0] = 255
            rgba[..., 1] = 215
            rgba[..., 2] = 0
        else:
            # 查看模式：淡青
            rgba[..., 0] = 120
            rgba[..., 1] = 220
            rgba[..., 2] = 255
        from PyQt6.QtGui import QImage
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        pm = QPixmap.fromImage(img)
        # LRU 缓存（键含放置模式，两种颜色分别缓存）
        self._highlight_cache[key] = (pm, x0, y0)
        while len(self._highlight_cache) > 64:
            self._highlight_cache.popitem(last=False)
        self.highlight_item.setPixmap(pm)
        self.highlight_item.setPos(x0, y0)
        self.highlight_item.setZValue(6)
        self.highlight_item.show()

    def _on_canvas_clicked(self, x, y):
        vp = QPoint(x, y)
        counter = self.view.hit_counter(vp)
        if counter is not None and not self.place_mode:
            # 点击兵牌：选中并显示详情（聚合兵牌以首支部队为代表）
            for c in self.counters:
                c.selected = c is counter
            self.view.refresh_counters()
            p = counter.placement
            extra = f" | 本地块共 {counter.count} 支" if counter.count > 1 else ""
            self.status_label.setText(
                f"{p.name} | 模板: {p.division_template} | 地块: {p.location}"
                + (f" | 经验: {p.start_experience_factor}"
                   if p.start_experience_factor is not None else "")
                + extra)
            return
        sp = self.view.mapToScene(vp)
        pid = self.map_data.province_at(int(sp.x()), int(sp.y()))
        if pid <= 0:
            return
        if not self.place_mode:
            for c in self.counters:
                c.selected = False
            self.view.refresh_counters()
            return
        if self.map_data.is_sea(pid):
            QMessageBox.information(self, "提示", "陆军部队不能放置在海上。")
            return
        tpl_name = self.tpl_combo.currentText()
        if not tpl_name:
            QMessageBox.information(self, "提示", "请先在编制编辑器中创建编制。")
            return
        name, ok = QInputDialog.getText(
            self, "放置部队", f"部队名称（地块 {pid}，模板 {tpl_name}）:",
            text=f"{tpl_name} {pid}")
        if not ok or not name.strip():
            return
        self.oob_file.add_placement(DivisionPlacement(
            name=name.strip(), location=pid, division_template=tpl_name))
        self._rebuild_counters()
        self.status_label.setText(f"已放置: {name.strip()} @ 地块 {pid}")

    def _on_canvas_context(self, x, y, global_pos):
        vp = QPoint(x, y)
        counter = self.view.hit_counter(vp)
        if counter is None:
            return
        # 该地块全部部队（聚合兵牌覆盖同地块多支部队）
        group = [p for p in self.oob_file.placements
                 if p.location == counter.placement.location]
        menu = QMenu(self)
        for i, p in enumerate(group):
            if i > 0:
                menu.addSeparator()
            menu.addAction(f"🗑 删除「{p.name}」").setData(("del", p))
            menu.addAction(f"✎ 重命名「{p.name}」").setData(("ren", p))
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        action, p = chosen.data()
        if action == "del":
            if self.oob_file.remove_placement(p):
                self._rebuild_counters()
                self.status_label.setText(f"已删除: {p.name}")
        else:
            name, ok = QInputDialog.getText(self, "重命名", "部队名称:",
                                            text=p.name)
            if ok and name.strip():
                p.name = name.strip()
                self.oob_file.mark_units_modified()
                self._rebuild_counters()

    # ---------- 保存 ----------

    def _save(self):
        try:
            self.oob_file.save()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", f"已保存到:\n{self.oob_file.file_path}")
        self.map_saved.emit()
