"""可复用地图画布（地图编辑 / 点选 / 框选共用底座）

基于 MapData（2^24 LUT 地块矩阵）的 QGraphicsView 封装：
- 底图 + 多层可替换叠加层（边界 / 国家色 / 地形 / 自定义）
- 五种工具模式：手型平移 / 点选 / 涂色 / 矩形框选 / 点选多选
- 选区（框选/多选共用）：统一黄色高亮，selection_changed 信号
- 滚轮缩放预览：滚动期间不重渲染矢量，旧瓦片位图实时缩放显示
  （零矢量重绘）；停止 300ms（map_zoom_settle_ms 可调）后重渲染高质量瓦片
- 区域重绘：MinimalViewportUpdate + DeviceCoordinateCache，只画视口区域
- 地块高亮（numpy 掩码合成，LRU 缓存）、框选矩形、全景/定位
- 矢量填充双缓存：省级 QPainterPath LRU + 视口栅格瓦片（平移纯 blit，
  边界线烘焙进瓦片）——纯缓存优化，不牺牲锐利度
- 信号：province_clicked / province_hovered / paint_province / rect_selected
         / selection_changed

用法：
    from map_canvas import MapCanvas
    canvas = MapCanvas(map_data)
    canvas.set_mode(MapCanvas.MODE_MULTI)
    canvas.selection_changed.connect(on_selection)
    canvas.set_overlay("country", pixmap)
"""

from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QColor, QImage, QPainter, QPainterPath, QPen,
                         QPixmap, QPolygonF, QTransform)
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsView,
)

# 交互模式
MODE_PAN = 0      # 手型：左键/中键拖拽平移；已合并点选语义（悬停/单击报告地块）
MODE_POINT = 1    # 点选：点击报告地块（保留兼容，功能与 PAN 单击一致）
MODE_PAINT = 2    # 涂色：点击报告涂色目标
MODE_RECT = 3     # 框选：拖拽矩形框选地块集合
MODE_MULTI = 4    # 多选：逐个点选地块加入/移出选区

# 选区高亮颜色（框选/多选/选中区域统一，地编同款）
SELECTION_COLOR = (255, 200, 90)
SELECTION_ALPHA = 180
# 目标省份（鼠标悬停）高亮：醒目的青色，与选中黄色区分
HOVER_COLOR = (80, 200, 255)
HOVER_ALPHA = 130

# 滚轮停止后延迟重绘的毫秒数（默认值；可用 settings.json 的 map_zoom_settle_ms 覆盖）。
# 滚轮期间走「预览缩放」（旧瓦片位图实时缩放，零矢量重绘），
# 停止后经此延迟做一次高质量瓦片重渲染（毫秒级），300ms 即可。
ZOOM_SETTLE_MS = 300
# 初次打开的全景放大系数（默认值；settings.json 的 map_initial_zoom 覆盖）。
# 全景适配后地图只占视口 ~60% 高度（宽高比 2.75:1 vs 视口 1.6:1），
# 上下留白严重；初始放大该倍数减少留白（全景按钮仍是完整视野）。
MAP_INITIAL_ZOOM = 1.3
# 矢量渲染（边界线/多边形填充）启用阈值（默认值；settings.json 的 map_zoom_threshold 覆盖）
VECTOR_ZOOM_THRESHOLD = 2.5

# 矢量填充瓦片缓存：缓存区每侧比视口大 TILE_MARGIN_FRAC（区域 ≈ 4× 视口），
# 平移落在缓存区内时纯位图 blit；缩放变化或移出缓存区才重渲染一次
TILE_MARGIN_FRAC = 0.5
# 缓存区最大边长（设备像素）：超大视口/高分屏时自动缩小缓存区防爆内存
TILE_MAX_SIDE = 4096
# 瓦片缩放相对容差：平移（缩放不变）命中缓存；滚轮缩放（1.25 倍档）远超容差 → 重渲染
TILE_ZOOM_EPS = 1e-4
# 省级 QPainterPath 预构建缓存上限（LRU）
_PATH_CACHE_MAX = 2048

_HIGHLIGHT_CACHE_MAX = 8
_HOVER_CACHE_MAX = 16
# 州轮廓高亮（地编圈出所选省份）缓存上限
_STATE_OUTLINE_CACHE_MAX = 32


def read_map_settings(path=None):
    """读取地图画布可调参数（settings.json 的 map_* 键，缺省用内置默认值）。

    Keys:
        map_zoom_threshold: 放大多少倍以上启用矢量渲染（默认 2.5）
        map_zoom_settle_ms: 滚轮停止后延迟重绘的毫秒数（默认 1000）

    Returns:
        dict: {"zoom_threshold": float, "zoom_settle_ms": int}
    """
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    def _num(key, default):
        try:
            v = float(data.get(key, default))
        except (TypeError, ValueError):
            v = default
        return v

    return {
        "zoom_threshold": _num("map_zoom_threshold", VECTOR_ZOOM_THRESHOLD),
        "zoom_settle_ms": max(50, int(_num("map_zoom_settle_ms",
                                           ZOOM_SETTLE_MS))),
        "initial_zoom": max(1.0, min(4.0, _num("map_initial_zoom",
                                               MAP_INITIAL_ZOOM))),
    }


def pids_in_rect(id_map, x0, y0, x1, y1):
    """矩形范围内的地块 ID 集合（纯 numpy，无 GUI 依赖，可测试）。

    Args:
        id_map: (H, W) uint32 地块 ID 矩阵
        x0, y0, x1, y1: 图像像素坐标（任意顺序，自动归一）

    Returns:
        list[int]: 去重后的地块 ID（不含 0）
    """
    if id_map is None or id_map.size == 0:
        return []
    h, w = id_map.shape
    x0, x1 = sorted((int(x0), int(x1)))
    y0, y1 = sorted((int(y0), int(y1)))
    x0 = max(0, min(x0, w - 1))
    x1 = max(0, min(x1, w - 1))
    y0 = max(0, min(y0, h - 1))
    y1 = max(0, min(y1, h - 1))
    if x1 < x0 or y1 < y0:
        return []
    sub = id_map[y0:y1 + 1, x0:x1 + 1]
    pids = np.unique(sub)
    return [int(p) for p in pids if p != 0]


def _blend_border(vals, a_, na, sr, sg, sb):
    """预乘 alpha 混合 1px 边界描边：out = src_premul + dst*(1-src_a)。

    vals: (N,) uint32 视图（ARGB32_Premultiplied 小端 0xAARRGGBB），就地修改。
    这是对 QPainter 长线描边的替代：Qt 光栅器对数千设备像素长的线段
    逐条描边要 ~1ms/条（整幅地图合并后就是这种长线），numpy 批量混合
    同样像素量仅需几十毫秒。
    """
    a = (vals >> 24) & 0xFF
    vals[...] = (
        ((a_ + (a * na) // 255) << 24)
        | ((sr + (((vals >> 16) & 0xFF) * na) // 255) << 16)
        | ((sg + (((vals >> 8) & 0xFF) * na) // 255) << 8)
        | (sb + ((vals & 0xFF) * na) // 255)
    )


class VectorBaseItem(QGraphicsPixmapItem):
    """矢量底图层：高倍缩放时用闭合多边形填充替代位图（放大不模糊 v2）。

    - 无填充数据或低于阈值：走 QGraphicsPixmapItem 原位图路径
      （保留 DeviceCoordinateCache 位图缓存）
    - 达到阈值且填充数据可用：paint() 绘制视口内省份的多边形填充，
      省内部与边界都锐利；叠加层（国家色/地形等）在本层之上不受影响
    - 多边形颜色取 definition.csv 的省份色（与 provinces.bmp 平坦色一致）；
      同省多环（孔洞/多连通）用 even-odd 填充规则
    - 相邻多边形用同色 cosmetic pen 封边，消除抗锯齿接缝

    缓存策略（2026-08 新增，纯缓存优化、不牺牲锐利度）：
      1. **省级 QPainterPath LRU 缓存**：每省一条 path（含全部环，even-odd）
         只在首次绘制时构建一次；旧实现每帧为每个可见环重建 QPolygonF。
      2. **视口栅格瓦片缓存**：矢量填充按「缩放档 + 视口区域」渲染一次到
         离屏位图（区域 = 视口外扩 TILE_MARGIN_FRAC，设备像素对齐），
         平移落在缓存区内时整帧只做一次位图 blit（不再逐省重绘）；
         缩放变化或移出缓存区才重渲染。边界线层同步烘焙进瓦片，
         drawForeground 在瓦片有效时跳过（避免每帧重建 QLineF 列表）。
    """

    def __init__(self, pixmap, map_data, parent=None):
        super().__init__(pixmap, parent)
        self._map_data = map_data
        self._fill = None
        self._fill_threshold = 2.5
        # 省级 path 缓存（LRU）：pid -> QPainterPath
        self._path_cache = OrderedDict()
        # 省 -> 环索引区间（set_fill 时一次建好）
        self._pid_loop_order = None
        self._pid_loop_off = {}
        # 瓦片缓存：(zoom, dpr, mx, my, (rx0,ry0,rx1,ry1), QPixmap, 是否含边界)
        self._tile = None
        self._tile_hits = 0
        # 滚轮预览缩放：滚动期间用现有瓦片位图实时缩放（不重渲染矢量）
        self._preview_mode = False
        # 边界线来源回调（canvas 提供）：() -> (enabled, segs)
        self._border_provider = None

    def set_fill(self, fill, threshold, border_provider=None):
        """设置/清除多边形填充数据（None = 关闭矢量填充）。"""
        self._fill = fill
        self._fill_threshold = float(threshold)
        if border_provider is not None:
            self._border_provider = border_provider
        # 缓存全部失效（填充数据变了）
        self._path_cache.clear()
        self._tile = None
        self._tile_hits = 0
        self._build_pid_loop_index()
        # 矢量填充时关闭位图缓存（DeviceCoordinateCache 会缓存光栅结果，
        # 破坏矢量锐利度）；无填充时恢复原缓存行为
        self.setCacheMode(
            QGraphicsItem.CacheMode.NoCache if fill is not None
            else QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.update()

    def set_border_provider(self, border_provider):
        """设置/更新边界线数据源（无填充时 drawForeground 也要画边界）。"""
        self._border_provider = border_provider

    # -------------------------------------------------------- 索引/路径缓存

    def _build_pid_loop_index(self):
        """set_fill 时按省分组环索引（一次 argsort，O(K log K)）。"""
        fill = self._fill
        if fill is None or fill.n_loops == 0:
            self._pid_loop_order = None
            self._pid_loop_off = {}
            return
        order = np.argsort(fill.loop_pid, kind="stable")
        spid = fill.loop_pid[order]
        uniq, starts = np.unique(spid, return_index=True)
        ends = np.concatenate(
            (starts[1:], np.array([order.shape[0]], dtype=np.int64)))
        self._pid_loop_order = order
        self._pid_loop_off = {}
        for i in range(uniq.shape[0]):
            self._pid_loop_off[int(uniq[i])] = (int(starts[i]), int(ends[i]))

    def _path_for_province(self, pid):
        """省 -> 预构建 QPainterPath（even-odd 多环；LRU 缓存）。

        旧实现每帧为每个可见环重建 QPolygonF；这里只构建一次，
        绘制时按省 drawPath（含孔洞/多连通）。
        """
        cached = self._path_cache.get(pid)
        if cached is not None:
            self._path_cache.move_to_end(pid)
            return cached
        fill = self._fill
        off = self._pid_loop_off
        order = self._pid_loop_order
        if fill is None or order is None or pid not in off:
            return None
        s, e = off[pid]
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for li in order[s:e]:
            verts = fill.loop_vertices(int(li))
            if verts.shape[0] < 3:
                continue
            poly = QPolygonF()
            for vx, vy in verts:
                poly.append(QPointF(float(vx), float(vy)))
            path.addPolygon(poly)
        if path.isEmpty():
            return None
        self._path_cache[pid] = path
        self._path_cache.move_to_end(pid)
        while len(self._path_cache) > _PATH_CACHE_MAX:
            self._path_cache.popitem(last=False)
        return path

    # -------------------------------------------------------- 瓦片缓存

    def tile_valid(self, zoom):
        """瓦片是否对当前缩放有效（供 drawForeground 决定是否跳过边界线）。

        瓦片在 item 绘制阶段（先于 drawForeground）已按当前可见区域刷新，
        因此此处只校验缩放档一致即可。
        """
        t = self._tile
        if t is None:
            return False
        return abs(zoom - t[0]) <= max(abs(t[0]) * TILE_ZOOM_EPS, 1e-9)

    def invalidate_tile(self):
        """瓦片失效（边界线开关等底图相关状态变化后强制重渲染）。"""
        self._tile = None
        self._tile_hits = 0

    def set_preview_mode(self, enabled):
        """滚轮预览缩放：滚动期间用现有瓦片位图实时缩放显示。

        开启后 paint() 不再因缩放变化重渲染瓦片，而是把旧瓦片按当前
        变换直接 blit（Qt 平滑缩放，成本 ~1-3ms/帧）；停止缩放后应
        关闭本模式并 invalidate_tile() 恢复高质量渲染。
        """
        self._preview_mode = bool(enabled)

    def _preview_blit(self, painter, option, vis, dpr):
        """预览路径：现有瓦片位图按当前变换缩放显示（零矢量重绘）。

        放大时可见区缩小，落在瓦片覆盖区内 → 纯 blit；
        缩小时可见区可能超出瓦片 → 先以底图位图补全，再叠瓦片。
        """
        t = self._tile
        if t is None:
            self._paint_fill(painter, option)
            return
        rx0, ry0, rx1, ry1 = t[4]
        if (vis[0] < rx0 - 0.5 or vis[1] < ry0 - 0.5
                or vis[2] > rx1 + 0.5 or vis[3] > ry1 + 0.5):
            # 缩小超界：底图位图补全（整图覆盖，预览期模糊可接受）
            try:
                super().paint(painter, option)
            except Exception:
                pass
        self._blit_tile(painter, dpr)

    def _visible_rect(self, painter):
        """可见范围（item 场景坐标）+ 设备信息。

        由 painter 设备尺寸反变换得到，精确且与 clip/exposedRect 无关
        （grab 场景下 exposedRect 会退化成整个 item）。
        """
        inv, ok = painter.worldTransform().inverted()
        if not ok:
            return None
        dev = painter.device()
        if dev is None:
            return None
        dpr = 1.0
        try:
            dpr = dev.devicePixelRatioF() or 1.0
        except Exception:
            dpr = 1.0
        w = max(1, dev.width())
        h = max(1, dev.height())
        tl = inv.map(QPointF(0.0, 0.0))
        br = inv.map(QPointF(w / dpr, h / dpr))
        x0, y0 = min(tl.x(), br.x()), min(tl.y(), br.y())
        x1, y1 = max(tl.x(), br.x()), max(tl.y(), br.y())
        return (x0, y0, x1, y1), dpr, w, h

    def _try_blit_tile(self, painter, dpr, vis):
        """瓦片命中：缩放/DPR 一致且可见区落在缓存区内 → 纯 blit。"""
        t = self._tile
        if t is None:
            return False
        z0, d0, mx, my, rect, pm, has_borders = t
        z = painter.worldTransform().m11()
        if (d0 != dpr
                or abs(z - z0) > max(abs(z0) * TILE_ZOOM_EPS, 1e-9)):
            return False
        rx0, ry0, rx1, ry1 = rect
        if (vis[0] < rx0 - 0.5 or vis[1] < ry0 - 0.5
                or vis[2] > rx1 + 0.5 or vis[3] > ry1 + 0.5):
            return False
        self._tile_hits += 1
        self._blit_tile(painter, dpr)
        return True

    def _blit_tile(self, painter, dpr):
        """按设备像素对齐 blit 瓦片（1:1 拷贝，无重采样模糊）。

        瓦片内容是「瓦片场景区在渲染时视图下的设备像素」；视图平移/缩放后
        变换已变，必须把瓦片场景区原点投影到**当前视图**的设备位置再拷贝，
        否则色块钉在原地不随地图移动（曾致小幅平移时底图不动的 bug）。
        """
        t = self._tile
        if t is None:
            return
        z0, d0, mx, my, rect, pm, has_borders = t
        rx0, ry0, rx1, ry1 = rect
        # 瓦片场景区原点 → 当前视图逻辑坐标 → 设备像素对齐（四舍五入）
        p = painter.worldTransform().map(QPointF(rx0, ry0))
        dx = round(p.x() * dpr) / dpr
        dy = round(p.y() * dpr) / dpr
        painter.save()
        painter.setWorldTransform(QTransform())
        painter.drawPixmap(QPointF(dx, dy), pm)
        painter.restore()

    def _render_tile(self, painter, vis, dpr, w, h):
        """离屏渲染瓦片（区域 = 视口外扩 margin，设备像素对齐）并 blit。

        渲染在场景坐标下进行（变换 = 设备缩放 s=zoom*dpr 平移至区域原点），
        结果与直接绘制完全一致，只是缓存复用；边界线层同步烘焙进瓦片。
        尺寸全部按设备像素计算（w/h 为逻辑像素，×dpr 换算），
        高分屏（dpr>1）下缓存区也能完整覆盖视口。
        """
        z = painter.worldTransform().m11()
        s = z * dpr
        wd = w * dpr
        hd = h * dpr
        mx = int(min(TILE_MARGIN_FRAC * wd,
                     max(0.0, (TILE_MAX_SIDE - wd) / 2.0)))
        my = int(min(TILE_MARGIN_FRAC * hd,
                     max(0.0, (TILE_MAX_SIDE - hd) / 2.0)))
        rw = int(wd + 2 * mx)
        rh = int(hd + 2 * my)
        x0, y0, x1, y1 = vis
        rx0 = x0 - mx / s
        ry0 = y0 - my / s
        rx1 = x1 + mx / s
        ry1 = y1 + my / s
        img = QImage(rw, rh, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        off = QPainter(img)
        off.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # p -> (p - 区域原点) * s：设备像素坐标（与最终 blit 的映射一致）
        off.setWorldTransform(
            QTransform().scale(s, s).translate(-rx0, -ry0))
        self._draw_fill_into(off, (rx0, ry0, rx1, ry1))
        off.end()
        # 边界线：numpy 直接混合进像素缓冲（QPainter 长线描边极慢，
        # 合并后的海岸线/省界可达数千设备像素，逐条描边每秒只能画几百条）
        has_borders = self._bake_borders(img, rx0, ry0, s,
                                         (rx0, ry0, rx1, ry1))
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)
        self._tile = (z, dpr, mx, my, (rx0, ry0, rx1, ry1), pm, has_borders)
        self._tile_hits = 0
        self._blit_tile(painter, dpr)

    def _draw_fill_into(self, painter, rect):
        """把 rect 内可见省份的填充画到 painter（场景坐标，省级 path 缓存）。"""
        fill = self._fill
        if fill is None or fill.n_loops == 0:
            return
        idx = fill.loops_in_rect(rect[0], rect[1], rect[2], rect[3])
        if idx.size == 0:
            return
        pids = np.unique(fill.loop_pid[idx])
        table = self._map_data.province_table
        for pid in pids:
            pid_i = int(pid)
            path = self._path_for_province(pid_i)
            if path is None:
                continue
            info = table.get(pid_i)
            if info is None:
                continue
            color = QColor(int(info["r"]), int(info["g"]), int(info["b"]))
            painter.setBrush(color)
            # 同色 cosmetic pen 封边：消除相邻多边形抗锯齿接缝
            painter.setPen(QPen(color, 0))
            painter.drawPath(path)

    _BORDER_R, _BORDER_G, _BORDER_B, _BORDER_A = 40, 40, 45, 200

    def _select_borders(self, rect):
        """选中与 rect 相交的边界线段并做轴对齐几何裁剪。

        返回裁剪后的 (N,4) int32 数组（丢弃退化线段）。几何裁剪是必需的：
        合并后的线段可能横跨整幅地图（数千像素），整条绘制会被 Qt 光栅器
        拖到秒级；裁剪到可见区后每段至多 rect 大小。
        """
        if self._border_provider is None:
            return None
        try:
            enabled, segs = self._border_provider()
        except Exception:
            return None
        if not enabled or segs is None or segs.shape[0] == 0:
            return None
        x0, y0 = int(rect[0]) - 1, int(rect[1]) - 1
        x1, y1 = int(rect[2]) + 1, int(rect[3]) + 1
        # 竖直线段（x0==x1）：列在 rect 内且 y 区间相交
        vmask = ((segs[:, 0] >= x0) & (segs[:, 0] <= x1)
                 & (segs[:, 1] <= y1) & (segs[:, 2] >= y0))
        # 水平线段（y0==y1）：行在 rect 内且 x 区间相交
        hmask = ((segs[:, 1] >= y0) & (segs[:, 1] <= y1)
                 & (segs[:, 0] <= x1) & (segs[:, 2] >= x0))
        sel = segs[vmask | hmask].copy()
        if sel.shape[0] == 0:
            return None
        v = sel[:, 0] == sel[:, 2]
        sel[v, 1] = np.maximum(sel[v, 1], y0)
        sel[v, 3] = np.minimum(sel[v, 3], y1)
        h = sel[:, 1] == sel[:, 3]
        sel[h, 0] = np.maximum(sel[h, 0], x0)
        sel[h, 2] = np.minimum(sel[h, 2], x1)
        lens = (sel[:, 2] - sel[:, 0]).astype(np.int64) \
            + (sel[:, 3] - sel[:, 1]).astype(np.int64)
        sel = sel[lens > 0]
        if sel.shape[0] == 0:
            return None
        return sel

    def _bake_borders(self, img, ox, oy, s, rect):
        """把边界线直接混合进瓦片像素缓冲（numpy，绕开 QPainter 慢路径）。

        img 为 ARGB32_Premultiplied（小端 0xAARRGGBB），填充已就绪；
        同列/同行且相接的线段先归并（numpy），再逐段连续切片混合
        （预乘 alpha「over」可结合，归并结果与逐段混合完全一致）。
        大端平台回退 QPainter 描边（极罕见）。
        """
        sel = self._select_borders(rect)
        if sel is None:
            return False
        if sys.byteorder != "little":
            # 回退：QPainter 描边（几何已裁剪，仅大端罕见平台）
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(QPen(QColor(self._BORDER_R, self._BORDER_G,
                                 self._BORDER_B, self._BORDER_A), 0))
            lines = [QLineF(float(s[0]), float(s[1]),
                            float(s[2]), float(s[3])) for s in sel]
            p.drawLines(lines)
            p.end()
            return True
        rw, rh = img.width(), img.height()
        ptr = img.bits()
        ptr.setsize(rw * rh * 4)
        buf = np.frombuffer(ptr, dtype=np.uint8).reshape(rh, rw, 4)
        px = buf.view(np.uint32)      # (rh, rw) 0xAARRGGBB（小端）
        r_, g_, b_, a_ = (self._BORDER_R, self._BORDER_G,
                          self._BORDER_B, self._BORDER_A)
        sr, sg, sb = r_ * a_ // 255, g_ * a_ // 255, b_ * a_ // 255
        na = 255 - a_

        xs0 = np.round((sel[:, 0] - ox) * s).astype(np.int64)
        ys0 = np.round((sel[:, 1] - oy) * s).astype(np.int64)
        xs1 = np.round((sel[:, 2] - ox) * s).astype(np.int64)
        ys1 = np.round((sel[:, 3] - oy) * s).astype(np.int64)
        vert = sel[:, 0] == sel[:, 2]
        for vsel, axis, fix, a0, a1 in (
                (vert, 0, xs0, np.minimum(ys0, ys1), np.maximum(ys0, ys1)),
                (~vert, 1, ys0, np.minimum(xs0, xs1), np.maximum(xs0, xs1))):
            if not vsel.any():
                continue
            f = fix[vsel]
            lo = a0[vsel]
            hi = a1[vsel]
            # 归并：同轴位置（列/行）且区间相接的段合成一条
            order = np.lexsort((lo, f))
            f2, lo2, hi2 = f[order], lo[order], hi[order]
            same = f2[1:] == f2[:-1]
            touch = lo2[1:] <= hi2[:-1] + 1
            run_start = np.concatenate(([True], ~(same & touch)))
            run_idx = np.nonzero(run_start)[0]
            f3 = f2[run_idx]
            lo3 = np.minimum.reduceat(lo2, run_idx)
            hi3 = np.maximum.reduceat(hi2, run_idx)
            n = f3.shape[0]
            for i in range(n):
                fi = int(f3[i])
                if axis == 0:         # 竖直线段：固定列
                    if fi < 0 or fi >= rw:
                        continue
                    y0i = max(0, int(lo3[i]))
                    y1i = min(rh - 1, int(hi3[i]))
                    if y1i >= y0i:
                        _blend_border(px[y0i:y1i + 1, fi], a_, na,
                                      sr, sg, sb)
                else:                 # 水平线段：固定行
                    if fi < 0 or fi >= rh:
                        continue
                    x0i = max(0, int(lo3[i]))
                    x1i = min(rw - 1, int(hi3[i]))
                    if x1i >= x0i:
                        _blend_border(px[fi, x0i:x1i + 1], a_, na,
                                      sr, sg, sb)
        return True

    def paint(self, painter, option, widget=None):
        if self._fill is None:
            super().paint(painter, option, widget)
            return
        # 世界变换即视图变换（逻辑坐标，含 DPR 的物理缩放由 QPainter 内部处理）
        zoom = painter.worldTransform().m11()
        if zoom < self._fill_threshold:
            super().paint(painter, option, widget)
            return
        self._paint_fill(painter, option)

    def _paint_fill(self, painter, option=None):
        fill = self._fill
        if fill is None or fill.n_loops == 0:
            return
        vis = self._visible_rect(painter)
        if vis is None:
            return
        rect, dpr, w, h = vis
        if self._preview_mode:
            self._preview_blit(painter, option, rect, dpr)
            return
        try:
            if not self._try_blit_tile(painter, dpr, rect):
                self._render_tile(painter, rect, dpr, w, h)
        except Exception:
            # 兜底：直接绘制（旧路径），任何异常下画面不丢
            try:
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                self._draw_fill_into(painter, rect)
                painter.restore()
            except Exception:
                pass


class MapCanvas(QGraphicsView):
    """可复用地图画布。"""

    province_clicked = pyqtSignal(int, int, int)      # pid, 图像x, 图像y
    province_hovered = pyqtSignal(int)
    paint_province = pyqtSignal(int)                  # 涂色模式点击的地块
    rect_selected = pyqtSignal(list, int, int, int, int)  # pids, x0, y0, x1, y1
    selection_changed = pyqtSignal(list)              # 选区变化（多选/框选后）
    # 通用交互扩展（供 OOB 等自定义应用使用；与模式系统正交）
    left_clicked = pyqtSignal(int, int)               # 左键单击（viewport 坐标）
    right_clicked = pyqtSignal(int, int, object)      # 右键单击（viewport 坐标 + 全局 QPoint）
    hover_moved = pyqtSignal(int, int)                # 鼠标移动（viewport 坐标）

    def __init__(self, map_data, parent=None, zoom_threshold=None,
                 zoom_settle_ms=None):
        super().__init__(parent)
        self.map_data = map_data
        self._mode = MODE_PAN
        self._overlays = {}          # key -> QGraphicsPixmapItem
        self._highlight_cache = []   # [(key, item)]
        self._drag_origin = None     # 框选起点 (scene x, y)
        self._rect_item = None
        # 选区（框选/多选共用）
        self._selection = set()
        # 通用交互：点击近距检测 + 前景 painter 钩子
        self._press_pos = None
        self._painters = []
        # 滚轮缩放防抖：滑动期间挂起重绘，停止 settle_ms 后统一重绘。
        # 间隔与矢量渲染阈值可由 settings.json（map_zoom_settle_ms /
        # map_zoom_threshold）或构造参数覆盖。
        _map_cfg = read_map_settings()
        if zoom_threshold is None:
            zoom_threshold = _map_cfg["zoom_threshold"]
        if zoom_settle_ms is None:
            zoom_settle_ms = _map_cfg["zoom_settle_ms"]
        self._updates_disabled = False
        # 滚轮预览缩放：滚动期间 base_item 用旧瓦片位图实时缩放
        self._preview_active = False
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(zoom_settle_ms)
        self._zoom_timer.timeout.connect(self._flush_zoom)

        self.setScene(QGraphicsScene(self))
        self.setRenderHints(
            self.renderHints()
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.Antialiasing)
        # 区域重绘：只更新视口内失效区域（配合 DeviceCoordinateCache）
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(self.DragMode.NoDrag)
        self.setMouseTracking(True)

        # 底图（矢量填充层：高倍缩放时以闭合多边形替代位图）
        self.base_item = VectorBaseItem(self.map_data.base_pixmap(),
                                        self.map_data)
        self.base_item.setCacheMode(
            QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.scene().addItem(self.base_item)
        self.scene().setSceneRect(
            0, 0, self.base_item.pixmap().width(),
            self.base_item.pixmap().height())

        # 高亮层（最上，除框选矩形外）：选中地块
        self.highlight_item = QGraphicsPixmapItem()
        self.highlight_item.setZValue(50)
        self.scene().addItem(self.highlight_item)
        self.highlight_item.hide()

        # 目标省份高亮层（鼠标悬停，醒目青色；在选中层之下）
        self.hover_item = QGraphicsPixmapItem()
        self.hover_item.setZValue(40)
        self.scene().addItem(self.hover_item)
        self.hover_item.hide()
        self._hover_pid = 0
        self._hover_enabled = False
        self._hover_cache = []       # [(pid, holder)] LRU

        # 州轮廓高亮层（地编：黄色描边圈出所选地块所属的省份）
        self._state_outline_items = []   # [QGraphicsPixmapItem]
        self._state_outline_cache = {}   # key -> (QPixmap, x0, y0)

        # 矢量边界层（放大不模糊；drawForeground 绘制，视口裁剪）
        self._vsegs = None            # (N,4) int32 [x0,y0,x1,y1]
        self._vector_border_enabled = True
        self._vector_zoom_threshold = float(zoom_threshold)

        self.set_mode(MODE_PAN)

    # ------------------------------------------------------------ 模式

    def set_mode(self, mode):
        """切换工具模式（MODE_*）。"""
        self._mode = mode
        if mode == MODE_PAN:
            self.setDragMode(self.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(self.DragMode.NoDrag)
            if mode == MODE_PAINT:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif mode in (MODE_POINT, MODE_RECT, MODE_MULTI):
                self.setCursor(Qt.CursorShape.CrossCursor)
        if mode != MODE_RECT:
            self._cancel_rect()

    def mode(self):
        return self._mode

    # ------------------------------------------------------------ 选区

    def set_selection(self, pids):
        """设置选区（替换）：高亮统一 SELECTION_COLOR，发 selection_changed。"""
        pids = sorted({int(p) for p in pids if int(p) > 0})
        if set(pids) == self._selection:
            return
        self._selection = set(pids)
        if pids:
            self.highlight_pids(pids, SELECTION_COLOR, SELECTION_ALPHA)
        else:
            self.clear_highlight()
        self.selection_changed.emit(list(pids))

    def toggle_province_selection(self, pid):
        """点选多选：切换单个地块的选中状态。"""
        pid = int(pid)
        if pid <= 0:
            return
        if pid in self._selection:
            self._selection.discard(pid)
        else:
            self._selection.add(pid)
        pids = sorted(self._selection)
        if pids:
            self.highlight_pids(pids, SELECTION_COLOR, SELECTION_ALPHA)
        else:
            self.clear_highlight()
        self.selection_changed.emit(list(pids))

    def clear_selection(self):
        if self._selection:
            self._selection.clear()
            self.clear_highlight()
            self.selection_changed.emit([])

    def selection(self):
        return sorted(self._selection)

    # ------------------------------------------------------------ 图层

    def set_overlay(self, key, pixmap, z=10):
        """设置/替换叠加层（QGraphicsPixmapItem）。传空 QPixmap 移除。"""
        if pixmap is None or pixmap.isNull():
            self.remove_overlay(key)
            return
        item = self._overlays.get(key)
        if item is None:
            item = QGraphicsPixmapItem()
            item.setZValue(z)
            item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
            self.scene().addItem(item)
            self._overlays[key] = item
        item.setPixmap(pixmap)

    def remove_overlay(self, key):
        item = self._overlays.pop(key, None)
        if item is not None:
            self.scene().removeItem(item)

    def clear_overlays(self):
        for key in list(self._overlays):
            self.remove_overlay(key)

    # ------------------------------------------------------------ 高亮

    @staticmethod
    def _mask_overlay(idm, pids, color, alpha):
        """地块集合 -> (QPixmap, x0, y0) 半透明覆盖层（仅包围盒局部）。

        地块内部用 (color, alpha) 半透明填充；**边缘 1px 白色不透明
        描边**，使选中/悬停目标省在浅色地形上也醒目。

        Returns:
            (pm, x0, y0) 或 (None, 0, 0)（无命中）
        """
        lut = np.zeros(int(idm.max()) + 1, dtype=bool)
        for p in pids:
            if 0 < p < lut.size:
                lut[p] = True
        mask = lut[idm]
        ys, xs = np.nonzero(mask)
        if xs.size == 0:
            return None, 0, 0
        # 4 邻域边缘：掩码与邻域异或
        edge = np.zeros_like(mask)
        edge[1:, :] |= mask[1:, :] & ~mask[:-1, :]
        edge[:-1, :] |= mask[:-1, :] & ~mask[1:, :]
        edge[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
        edge[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), \
            int(ys.min()), int(ys.max())
        sub = mask[y0:y1 + 1, x0:x1 + 1]
        ed = edge[y0:y1 + 1, x0:x1 + 1]
        h, w = sub.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        inside = sub & ~ed
        rgba[..., 0] = np.where(ed, 255, np.where(inside, color[0], 0))
        rgba[..., 1] = np.where(ed, 255, np.where(inside, color[1], 0))
        rgba[..., 2] = np.where(ed, 255, np.where(inside, color[2], 0))
        rgba[..., 3] = np.where(ed, 255, np.where(inside, alpha, 0))
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(img), x0, y0

    def highlight_pids(self, pids, color=(255, 200, 90), alpha=150):
        """高亮一组地块（选中层：黄色，numpy 掩码合成，LRU 缓存）。"""
        idm = self.map_data.id_map
        if idm is None:
            return
        pids = [int(p) for p in pids if int(p) > 0]
        if not pids:
            self.clear_highlight()
            return
        key = (tuple(sorted(pids)), tuple(color), int(alpha))
        for k, holder in self._highlight_cache:
            if k == key:
                self._apply_highlight(holder)
                return
        pm, x0, y0 = self._mask_overlay(idm, pids, color, alpha)
        if pm is None:
            self.clear_highlight()
            return
        holder = self._make_cached(pm)
        holder.setPos(x0, y0)
        self._highlight_cache.append((key, holder))
        if len(self._highlight_cache) > _HIGHLIGHT_CACHE_MAX:
            self._highlight_cache.pop(0)
        self._apply_highlight(holder)

    def _apply_highlight(self, holder):
        self.highlight_item.setPixmap(holder.pixmap())
        self.highlight_item.setPos(holder.pos())
        self.highlight_item.show()

    @staticmethod
    def _make_cached(pm):
        holder = QGraphicsPixmapItem(pm)
        holder.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        return holder

    def clear_highlight(self):
        self.highlight_item.hide()

    # ------------------------------------------------------------ 州轮廓高亮

    @staticmethod
    def _state_outline_overlay(idm, pids, color, alpha, width=2):
        """州地块集合 -> (QPixmap, x0, y0)：仅外扩黄色描边（不填充）。

        用于地编中圈出所选地块所属的省份（state）边界：比地块级高亮更醒目。
        width 为外扩像素圈数（默认 2，形成较粗黄边）。
        """
        lut = np.zeros(int(idm.max()) + 1, dtype=bool)
        for p in pids:
            if 0 < p < lut.size:
                lut[p] = True
        mask = lut[idm]
        ys, xs = np.nonzero(mask)
        if xs.size == 0:
            return None, 0, 0
        width = max(1, int(width))
        d = mask.copy()
        for _ in range(width):
            prev = d.copy()
            d[1:, :] |= prev[:-1, :]
            d[:-1, :] |= prev[1:, :]
            d[:, 1:] |= prev[:, :-1]
            d[:, :-1] |= prev[:, 1:]
        edge = d & ~mask
        x0 = max(0, int(xs.min()) - width)
        x1 = min(idm.shape[1] - 1, int(xs.max()) + width)
        y0 = max(0, int(ys.min()) - width)
        y1 = min(idm.shape[0] - 1, int(ys.max()) + width)
        sub = edge[y0:y1 + 1, x0:x1 + 1]
        h, w = sub.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 0] = np.where(sub, color[0], 0)
        rgba[..., 1] = np.where(sub, color[1], 0)
        rgba[..., 2] = np.where(sub, color[2], 0)
        rgba[..., 3] = np.where(sub, alpha, 0)
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(img), x0, y0

    def set_state_outlines(self, states_pids, color=SELECTION_COLOR,
                           alpha=255, width=2):
        """设置州轮廓高亮：每个州一个独立 outline item（黄色描边）。

        states_pids: list[list[int]]，每个元素是一个州的地块 id 列表。
        会先清除旧轮廓；QPixmap 按 (州地块集合, 颜色, 宽度) 缓存。
        """
        self.clear_state_outlines()
        idm = self.map_data.id_map
        if idm is None or not states_pids:
            return
        for pids in states_pids:
            pids = [int(p) for p in pids if int(p) > 0]
            if not pids:
                continue
            key = (tuple(sorted(pids)), tuple(color), int(alpha), int(width))
            hit = self._state_outline_cache.get(key)
            if hit is None:
                pm, x0, y0 = self._state_outline_overlay(
                    idm, pids, color, alpha, width)
                if pm is None:
                    continue
                hit = (pm, x0, y0)
                self._state_outline_cache[key] = hit
                if len(self._state_outline_cache) > _STATE_OUTLINE_CACHE_MAX:
                    self._state_outline_cache.pop(
                        next(iter(self._state_outline_cache)))
            pm, x0, y0 = hit
            item = QGraphicsPixmapItem(pm)
            item.setZValue(55)
            item.setPos(x0, y0)
            item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
            self.scene().addItem(item)
            self._state_outline_items.append(item)
        self.viewport().update()

    def clear_state_outlines(self):
        """清除全部州轮廓高亮。"""
        for item in self._state_outline_items:
            self.scene().removeItem(item)
        self._state_outline_items = []
        self.viewport().update()

    # ------------------------------------------------------------ 目标省高亮

    def set_hover_highlight_enabled(self, enabled):
        """开启/关闭悬停目标省份高亮（醒目青色层）。"""
        self._hover_enabled = bool(enabled)
        if not self._hover_enabled:
            self.clear_hover()

    def hover_highlight_enabled(self):
        return self._hover_enabled

    def clear_hover(self):
        """清除目标省份高亮。"""
        self._hover_pid = 0
        self.hover_item.hide()

    def _set_hover(self, pid):
        """更新目标省份高亮（悬停层，青色；pid<=0 清除）。"""
        pid = int(pid)
        if pid == self._hover_pid:
            return
        self._hover_pid = pid
        if pid <= 0:
            self.hover_item.hide()
            return
        idm = self.map_data.id_map
        if idm is None:
            return
        for k, holder in self._hover_cache:
            if k == pid:
                self._apply_hover(holder)
                return
        pm, x0, y0 = self._mask_overlay(idm, [pid], HOVER_COLOR, HOVER_ALPHA)
        if pm is None:
            return
        holder = self._make_cached(pm)
        holder.setPos(x0, y0)
        self._hover_cache.append((pid, holder))
        if len(self._hover_cache) > _HOVER_CACHE_MAX:
            self._hover_cache.pop(0)
        self._apply_hover(holder)

    def _apply_hover(self, holder):
        self.hover_item.setPixmap(holder.pixmap())
        self.hover_item.setPos(holder.pos())
        self.hover_item.show()

    # ------------------------------------------------------------ 视图

    def fit_map(self, factor=1.0):
        """全景适配（保持宽高比）；factor>1 时在全景基础上再放大。

        初次打开用 factor=map_initial_zoom（默认 1.3）减少上下留白；
        「全景」按钮不传 factor（=1.0）保持完整视野。
        """
        self.fitInView(self.scene().sceneRect(),
                       Qt.AspectRatioMode.KeepAspectRatio)
        if factor != 1.0:
            self.scale(factor, factor)

    def center_on_pixel(self, x, y):
        self.centerOn(x, y)

    # ------------------------------------------------------------ 交互

    def _image_pos(self, pos):
        """视图坐标 -> 图像像素坐标 (x, y) 或 None。

        pos 可以是 QPoint/QPointF；PyQt6 的 mapToScene 只接受 QPoint 重载，
        因此统一先转成 QPoint。
        """
        pt = pos.toPoint() if hasattr(pos, "toPoint") else pos
        sp = self.mapToScene(pt)
        return int(sp.x()), int(sp.y())

    def _pid_at_view(self, pos):
        p = self._image_pos(pos)
        if p is None:
            return 0
        return self.map_data.province_at(p[0], p[1])

    def mousePressEvent(self, event):
        # 滚轮防抖挂起期间用户交互 → 立即恢复重绘
        self._flush_zoom()
        if event.button() == Qt.MouseButton.LeftButton:
            if self._mode == MODE_POINT:
                pid = self._pid_at_view(event.position())
                if pid:
                    x, y = self._image_pos(event.position())
                    self.province_clicked.emit(pid, x, y)
                event.accept()
                return
            if self._mode == MODE_PAINT:
                pid = self._pid_at_view(event.position())
                if pid:
                    self.paint_province.emit(pid)
                event.accept()
                return
            if self._mode == MODE_MULTI:
                pid = self._pid_at_view(event.position())
                if pid:
                    self.toggle_province_selection(pid)
                event.accept()
                return
            if self._mode == MODE_RECT:
                self._drag_origin = self.mapToScene(event.position().toPoint())
                if self._rect_item is None:
                    self._rect_item = QGraphicsRectItem()
                    pen = QPen(QColor(31, 79, 126), 2,
                               Qt.PenStyle.DashLine)
                    self._rect_item.setPen(pen)
                    self._rect_item.setZValue(100)
                    self.scene().addItem(self._rect_item)
                event.accept()
                return
        if event.button() == Qt.MouseButton.RightButton and self._mode == MODE_RECT:
            self._cancel_rect()
            event.accept()
            return
        if event.button() in (Qt.MouseButton.LeftButton,
                              Qt.MouseButton.RightButton):
            # 仅未被模式系统消费的按键参与通用点击检测（区分拖拽）
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        vp = event.position().toPoint()
        self.hover_moved.emit(vp.x(), vp.y())
        if self._mode == MODE_RECT and self._drag_origin is not None:
            cur = self.mapToScene(event.position().toPoint())
            r = QRectF(self._drag_origin, cur).normalized()
            self._rect_item.setRect(r)
            event.accept()
            return
        if self._mode in (MODE_POINT, MODE_PAINT, MODE_PAN):
            # PAN（手型）已合并点选语义：非拖拽时悬停报告地块
            dragging = (self._mode == MODE_PAN
                        and bool(event.buttons() & Qt.MouseButton.LeftButton))
            if not dragging:
                pid = self._pid_at_view(event.position())
                if self._hover_enabled:
                    # 目标省份高亮层（悬停醒目青色；pid=0 清除）
                    self._set_hover(pid)
                if pid:
                    self.province_hovered.emit(pid)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 通用点击检测：按下与释放位置接近视为单击（区分拖拽平移）
        if self._press_pos is not None:
            dist = (event.position().toPoint()
                    - self._press_pos).manhattanLength()
            if dist < 5:
                vp = event.position().toPoint()
                if event.button() == Qt.MouseButton.LeftButton:
                    # PAN（手型）已合并点选语义：单击报告地块
                    if self._mode == MODE_PAN:
                        pid = self._pid_at_view(event.position())
                        if pid:
                            x, y = self._image_pos(event.position())
                            self.province_clicked.emit(pid, x, y)
                    self.left_clicked.emit(vp.x(), vp.y())
                elif event.button() == Qt.MouseButton.RightButton:
                    self.right_clicked.emit(
                        vp.x(), vp.y(), event.globalPosition().toPoint())
            self._press_pos = None
        if (event.button() == Qt.MouseButton.LeftButton
                and self._mode == MODE_RECT
                and self._drag_origin is not None):
            cur = self.mapToScene(event.position().toPoint())
            r = QRectF(self._drag_origin, cur).normalized()
            self._finish_rect(r)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # 滚轮缩放 + 预览模式：滚动期间不重渲染矢量内容，直接把上次
        # 渲染好的瓦片位图按新变换实时缩放显示（预览 blit ~1-3ms/帧，
        # 画面实时跟随缩放）；停止 ZOOM_SETTLE_MS 后 _flush_zoom 关闭
        # 预览并做一次高质量瓦片重渲染（毫秒级）。
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        if not self._preview_active:
            self._preview_active = True
            self.base_item.set_preview_mode(True)
        self.scale(factor, factor)
        self._zoom_timer.start()

    def _flush_zoom(self):
        """滚轮防抖结束/用户交互时：退出预览并重渲染一次高质量瓦片。"""
        if self._zoom_timer.isActive():
            self._zoom_timer.stop()
        if self._preview_active:
            self._preview_active = False
            self.base_item.set_preview_mode(False)
            self.base_item.invalidate_tile()
            self.viewport().update()
        # 兼容旧路径：若曾有重绘挂起，一并恢复
        if self._updates_disabled:
            self._updates_disabled = False
            self.setUpdatesEnabled(True)
            self.viewport().update()

    # ------------------------------------------------------------ 矢量边界

    def enable_vector_borders(self, segments):
        """启用矢量边界层（map_vector.get_edge_segments 的 (N,4) 数组）。"""
        self._vsegs = segments
        # 无填充时也接上 provider：drawForeground 走几何裁剪绘制
        self.base_item.set_border_provider(self._border_provider)
        self.base_item.invalidate_tile()
        self.viewport().update()

    def set_vector_border_enabled(self, enabled):
        self._vector_border_enabled = bool(enabled)
        self.base_item.invalidate_tile()
        self.viewport().update()

    # ------------------------------------------------------------ 前景绘制钩子

    def add_painter(self, cb):
        """注册前景 painter 钩子：cb(painter, scene_rect, canvas)。

        在 drawForeground 末尾（矢量边界之后）按注册顺序调用，
        供自定义应用（如 OOB 兵牌/国家标签）在场景坐标下绘制。
        绘制屏幕恒定大小的元素时可用 painter.setWorldTransform(QTransform())
        切换到视口逻辑坐标，再经 canvas.mapFromScene 换算。
        """
        if cb not in self._painters:
            self._painters.append(cb)
        self.viewport().update()

    def clear_painters(self):
        self._painters = []
        self.viewport().update()

    def enable_vector_fill(self, fill, threshold=None):
        """启用矢量多边形填充层（map_fill.get_province_polygons 的结果）。

        高倍缩放（>= 阈值）时底图由位图切换为矢量多边形填充，
        省内部与边界均锐利不模糊。传 None 关闭（回退位图）。

        边界线（enable_vector_borders 的线段）会随填充一起烘焙进
        瓦片缓存：平移时整帧只做一次位图 blit，无需每帧重建 QLineF。
        """
        if threshold is None:
            threshold = self._vector_zoom_threshold
        self.base_item.set_fill(fill, threshold,
                                border_provider=self._border_provider)
        self.viewport().update()

    def _border_provider(self):
        """瓦片烘焙边界线的数据源（与 drawForeground 同款判定）。"""
        return self._vector_border_enabled, self._vsegs

    def _zoom_factor(self):
        return self.transform().m11()

    def drawForeground(self, painter, rect):
        """前景绘制：矢量边界（放大超过阈值时锐利绘制）+ 自定义钩子。

        矢量填充瓦片已把边界线烘焙进缓存位图时跳过绘制：
        避免平移时每帧重建 QLineF 列表（item 先于本方法绘制，瓦片
        已在同一渲染帧内刷新，tile_valid 判定即可）。
        """
        super().drawForeground(painter, rect)
        if (self._vector_border_enabled and self._vsegs is not None
                and self._vsegs.shape[0] > 0
                and self._zoom_factor() >= self._vector_zoom_threshold
                and not self._preview_active
                and not self.base_item.tile_valid(self._zoom_factor())):
            # 回退路径（无填充瓦片时）：几何裁剪后绘制，避免整条长线描边
            sel = self.base_item._select_borders(
                (rect.left(), rect.top(), rect.right(), rect.bottom()))
            if sel is not None and sel.shape[0] > 0:
                painter.save()
                painter.setPen(QPen(QColor(40, 40, 45, 200), 0))
                lines = [QLineF(float(s[0]), float(s[1]),
                                float(s[2]), float(s[3])) for s in sel]
                painter.drawLines(lines)
                painter.restore()
        # 自定义前景钩子（兵牌/标签等；与矢量边界开关无关，始终执行）
        for cb in self._painters:
            try:
                cb(painter, rect, self)
            except Exception:
                pass
    def _finish_rect(self, rect):
        x0, y0 = int(rect.left()), int(rect.top())
        x1, y1 = int(rect.right()), int(rect.bottom())
        pids = pids_in_rect(self.map_data.id_map, x0, y0, x1, y1)
        self._cancel_rect()
        if pids:
            # 框选结果进入选区（与多选同色高亮，加强反馈）
            self.set_selection(pids)
            self.rect_selected.emit(pids, x0, y0, x1, y1)

    def _cancel_rect(self):
        self._drag_origin = None
        if self._rect_item is not None:
            self.scene().removeItem(self._rect_item)
            self._rect_item = None
