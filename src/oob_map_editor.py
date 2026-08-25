"""初始部队地图放置窗口

加载游戏/mod 地图文件绘制所有地块，显示海军/空军基地锚点，
按游戏兵牌样式展示已放置的陆军部队；选择编制后点击地块放置部队。

基于可复用 MapCanvas（map_canvas.py）：
- 平移/缩放/滚轮防抖/矢量渲染（边界线 + 多边形填充）由画布提供
- 兵牌/国家标签通过前景 painter 钩子绘制（屏幕恒定大小）
- 点击/右键/悬停通过通用信号接入
"""

import os
import re

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPixmap, QPen, QTransform
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QMenu, QInputDialog, QToolTip
)

from map_loader import MapData
from map_canvas import MapCanvas, MODE_PAN
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
    from PyQt6.QtWidgets import QGraphicsSimpleTextItem
    item = QGraphicsSimpleTextItem(char)
    font = item.font()
    font.setPointSizeF(ANCHOR_FONT_SIZE)
    item.setFont(font)
    item.setBrush(QColor(color))
    return item


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
        # 回退：单位标牌库（P2：兵牌图标接标牌库）
        try:
            from unit_counter_icons import counter_pixmap
            pm = counter_pixmap(typ, COUNTER_W, COUNTER_H)
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


def _country_capital_province(mod_path, hoi4_path, tag):
    """从 history/countries 的国家文件解析 capital 地块（mod 优先）。"""
    tag = (tag or "").upper()
    if not tag:
        return None
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "history", "countries")
        if not os.path.isdir(d):
            continue
        try:
            names = sorted(os.listdir(d))
        except Exception:
            continue
        for fn in names:
            if not fn.lower().endswith(".txt"):
                continue
            first = fn.split(" - ")[0].split()[0].strip().upper().rstrip(".TXT")
            if first != tag:
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            m = re.search(r'\bcapital\s*=\s*(\d+)', content)
            if m:
                return int(m.group(1))
    return None


def _province_adjacency(map_data, pids):
    """返回给定地块集合内的 4 邻接关系 {pid: set(pid)}。

    仅记录两个端点都属于 pids 的边，内存控制在布尔掩码 + 行级切片。
    """
    pid_list = list(pids or [])
    if not pid_list or map_data.id_map is None:
        return {p: set() for p in pid_list}
    id_map = map_data.id_map
    mask = np.isin(id_map, pid_list)
    adj = {p: set() for p in pid_list}
    h, w = id_map.shape
    if w > 1:
        m = mask[:, :-1] & mask[:, 1:]
        a = id_map[:, :-1][m]
        b = id_map[:, 1:][m]
        for p, q in zip(a.tolist(), b.tolist()):
            if p != q:
                adj.setdefault(p, set()).add(q)
                adj.setdefault(q, set()).add(p)
    if h > 1:
        m = mask[:-1, :] & mask[1:, :]
        a = id_map[:-1, :][m]
        b = id_map[1:, :][m]
        for p, q in zip(a.tolist(), b.tolist()):
            if p != q:
                adj.setdefault(p, set()).add(q)
                adj.setdefault(q, set()).add(p)
    return adj


def _connected_components(pids, adjacency):
    """按地块邻接图求连通分量，返回按数量降序的 [set(pid), ...]。"""
    pids = list(pids or [])
    if not pids:
        return []
    seen = set()
    comps = []
    for p in pids:
        if p in seen:
            continue
        stack = [p]
        seen.add(p)
        comp = set()
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for nb in (adjacency.get(cur) or ()):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps


def _home_component(map_data, pids, capital_pid=None):
    """选取国家的“本体最大连通区”：首都所在分量优先，否则最大分量。"""
    if not pids:
        return []
    adj = _province_adjacency(map_data, pids)
    comps = _connected_components(pids, adj)
    if capital_pid in pids:
        for comp in comps:
            if capital_pid in comp:
                return sorted(comp)
    if comps:
        return sorted(comps[0])
    return sorted(pids)


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
        self.counters = []          # list[ScreenCounter]
        self.country_labels = []    # [(scene_x, scene_y, 名称), ...]
        self._current_highlight_pid = 0
        self._highlight_color = (120, 220, 255)

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
        self.fit_btn.clicked.connect(self._fit)
        bar.addWidget(self.fit_btn)

        bar.addStretch(1)
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)
        bar.addWidget(self.save_btn)
        root.addLayout(bar)

        # 可复用地图画布（平移/缩放/矢量渲染/信号由画布提供）
        self.canvas = MapCanvas(self.map_data)
        self.canvas.hover_moved.connect(self._on_hover)
        self.canvas.left_clicked.connect(self._on_canvas_clicked)
        self.canvas.right_clicked.connect(self._on_canvas_context)
        self.canvas.add_painter(self._paint_foreground)
        root.addWidget(self.canvas, 1)

        self.status_label = QLabel("就绪")
        root.addWidget(self.status_label)

        # 国家着色图层（统一国家色块 + 地块边界线 + 国界线 + 焦点金边）
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
                self.canvas.set_overlay("country", country_pm, z=2)
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
            self.country_labels = labels
        except Exception:
            pass

        self._initial_focus_done = False

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_initial_focus_done", False):
            self._initial_focus_done = True
            self._apply_initial_focus()

    def _apply_initial_focus(self):
        """初始视野：定位到所选国家领土；无则全景放大 DEFAULT_ZOOM。"""
        focus = self._focus_region()
        if focus:
            xs = [c[0] for c in focus if c]
            ys = [c[1] for c in focus if c]
            if xs:
                pad = 80
                rect = QRectF(min(xs) - pad, min(ys) - pad,
                              max(xs) - min(xs) + pad * 2,
                              max(ys) - min(ys) + pad * 2)
                self.canvas.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
                self.canvas.scale(1.2, 1.2)
                return
        self._fit()
        self.canvas.scale(DEFAULT_ZOOM, DEFAULT_ZOOM)

    def _fit(self):
        self.canvas.fit_map()

    def _focus_region(self):
        """定位区域：国家本体最大连通区（首都所在州优先）。

        若国家不存在/无地块，则回退到文件中已放置部队的地块。
        """
        if self.country_tag:
            pids = self.state_data.provinces_of_owner(self.country_tag)
            if pids:
                capital = _country_capital_province(
                    self.mod_path, self.hoi4_path, self.country_tag)
                home = _home_component(self.map_data, pids, capital)
                return [self.map_data.province_centroid(pid)
                        for pid in home if self.map_data.province_centroid(pid)]
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
        scene = self.canvas.scene()
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
                scene.addItem(item)

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
        self.canvas.viewport().update()

    def _placement_type(self, placement):
        """部队主兵种（用于兵牌图标）：取模板首个战斗连。"""
        tpl = self.oob_file.find_template(placement.division_template)
        if tpl and tpl.regiments:
            return tpl.regiments[0][0]
        return "infantry"

    # ---------- 前景绘制（屏幕恒定大小：国家标签 + 兵牌） ----------

    def _paint_foreground(self, painter, rect, canvas):
        """前景 painter 钩子：切到视口坐标绘制，恒定屏幕大小。"""
        painter.save()
        painter.setWorldTransform(QTransform())
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing)
        # 国家名称（锚定各国领土中心）
        if self.country_labels:
            font = painter.font()
            font.setPointSizeF(9.0)
            painter.setFont(font)
            for sx, sy, name in self.country_labels:
                vp = canvas.mapFromScene(QPointF(sx, sy))
                rect2 = QRectF(vp.x() - 100, vp.y() - 9, 200, 18)
                painter.setPen(QPen(QColor(15, 15, 15), 3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawText(rect2, Qt.AlignmentFlag.AlignCenter, name)
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.setBrush(QColor(255, 255, 255))
                painter.drawText(rect2, Qt.AlignmentFlag.AlignCenter, name)
        # 兵牌（锚定地块中心；聚合：不透明绿底矩形 + 白框黑底兵牌 + 数量）
        for c in self.counters:
            vp = canvas.mapFromScene(QPointF(*c.scene_point))
            r = QRectF(vp.x() - COUNTER_W / 2, vp.y() - COUNTER_H / 2,
                       COUNTER_W, COUNTER_H)
            painter.fillRect(r, COUNTER_BG)
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)
            num_w = r.width() * NUM_RATIO
            icon_rect = QRectF(r.x(), r.y(),
                               r.width() - num_w, r.height())
            inner = icon_rect.adjusted(2, 2, -2, -2)
            painter.fillRect(inner, QColor(18, 18, 18))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(inner)
            src = c.pixmap
            scaled = src.scaled(int(inner.width()), int(inner.height()),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            dx = (inner.width() - scaled.width()) / 2
            dy = (inner.height() - scaled.height()) / 2
            # PyQt6 无 (float, float, QPixmap) 重载 → 用 QPointF 版本
            painter.drawPixmap(QPointF(inner.x() + dx, inner.y() + dy),
                               scaled)
            num_rect = QRectF(r.x() + r.width() - num_w, r.y(),
                              num_w, r.height())
            font = painter.font()
            font.setPointSizeF(11.0)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.setBrush(QColor(255, 255, 255))
            painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter,
                             str(c.count))
            if c.selected:
                painter.setPen(QPen(QColor(255, 215, 0), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(r.adjusted(-1, -1, 1, 1))
        painter.restore()

    # ---------- 交互 ----------

    def _on_place_mode(self, checked):
        self.place_mode = checked
        if checked:
            self.canvas.setDragMode(self.canvas.DragMode.NoDrag)
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
            self._highlight_color = (255, 215, 0)
            self.status_label.setText(
                "放置模式：移动鼠标预览地块，点击陆地放置所选编制；"
                "按住 Ctrl 拖动平移")
        else:
            self.canvas.set_mode(MODE_PAN)
            self._highlight_color = (120, 220, 255)
            self.status_label.setText("就绪")

    def _hit_counter(self, vp_pos):
        """按 viewport 坐标命中兵牌，返回 ScreenCounter 或 None。"""
        for c in self.counters:
            vp = self.canvas.mapFromScene(QPointF(*c.scene_point))
            if abs(vp.x() - vp_pos.x()) <= COUNTER_W / 2 + 2 \
                    and abs(vp.y() - vp_pos.y()) <= COUNTER_H / 2 + 2:
                return c
        return None

    def _on_hover(self, x, y):
        # 兵牌优先：悬停已放置部队显示部队信息
        counter = self._hit_counter(QPoint(x, y))
        if counter is not None:
            p = counter.placement
            extra = f" | 本地块共 {counter.count} 支" if counter.count > 1 else ""
            self.status_label.setText(
                f"部队: {p.name} | 模板: {p.division_template} | 地块: {p.location}{extra}")
            QToolTip.hideText()
            return
        sp = self.canvas.mapToScene(QPoint(x, y))
        pid = self.map_data.province_at(int(sp.x()), int(sp.y()))
        if pid <= 0:
            self.canvas.clear_highlight()
            self._current_highlight_pid = 0
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
            self.canvas.highlight_pids([pid], self._highlight_color, 160)

    def _on_canvas_clicked(self, x, y):
        vp = QPoint(x, y)
        counter = self._hit_counter(vp)
        if counter is not None and not self.place_mode:
            # 点击兵牌：选中并显示详情（聚合兵牌以首支部队为代表）
            for c in self.counters:
                c.selected = c is counter
            self.canvas.viewport().update()
            p = counter.placement
            extra = f" | 本地块共 {counter.count} 支" if counter.count > 1 else ""
            self.status_label.setText(
                f"{p.name} | 模板: {p.division_template} | 地块: {p.location}"
                + (f" | 经验: {p.start_experience_factor}"
                   if p.start_experience_factor is not None else "")
                + extra)
            return
        sp = self.canvas.mapToScene(vp)
        pid = self.map_data.province_at(int(sp.x()), int(sp.y()))
        if pid <= 0:
            return
        if not self.place_mode:
            for c in self.counters:
                c.selected = False
            self.canvas.viewport().update()
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
        counter = self._hit_counter(vp)
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
