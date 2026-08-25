"""地图数据层色阶（P2 ③，纯算法/渲染数据层）。

从游戏/map 与 history/states 数据生成地图叠加层：
- 胜利点 VP / 资源总量：按州数值着色的色阶覆盖层
- 补给区：按区域不同色调分类覆盖层
- 铁路：railways.txt 折线投影到省份质心连线
- 河流：rivers.bmp 非背景/非白色像素近似河流线

全部函数不依赖 Qt；结果返回 numpy RGBA 数组 + bbox 偏移，由 UI 层转 QPixmap。
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw

from tree_node import parse_pdx_text_to_nodes

# rivers.bmp 背景色（灰）与白色（陆地/海岸，不作为河流线）
_RIVER_BG = (122, 122, 122)
_RIVER_EXCLUDE = {(122, 122, 122), (255, 255, 255)}


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def load_supply_areas(mod_path="", hoi4_path=""):
    """map/supplyareas/*.txt -> (state_to_area, area_meta)。

    area_meta: {area_id: {"name": str, "value": int}}
    """
    areas = {}
    meta = {}
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        d = os.path.join(base, "map", "supplyareas")
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(".txt"):
                continue
            fp = os.path.join(d, fn)
            try:
                with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for node in parse_pdx_text_to_nodes(content):
                if node.node_type != "block" or node.key != "supply_area":
                    continue
                aid, value = None, 0
                name = ""
                for c in node.children:
                    if c.node_type == "value":
                        if c.key == "id":
                            try:
                                aid = int(c.value)
                            except ValueError:
                                aid = None
                        elif c.key == "value":
                            try:
                                value = int(float(c.value))
                            except ValueError:
                                pass
                        elif c.key == "name":
                            name = c.value.strip().strip('"')
                    elif c.node_type == "block" and c.key == "states":
                        for p in c.children:
                            if p.node_type == "value" and p.key.strip().isdigit():
                                sid = int(p.key)
                                if aid is not None:
                                    areas[sid] = aid
                if aid is not None:
                    meta[aid] = {"name": name, "value": value}
    return areas, meta


def load_railways(mod_path="", hoi4_path=""):
    """map/railways.txt -> list[{"level": int, "pids": [int, ...]}]（mod 优先）。"""
    out = []
    for base in (mod_path, hoi4_path):
        if not base:
            continue
        fp = os.path.join(base, "map", "railways.txt")
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        for raw in content.splitlines():
            parts = raw.split()
            if len(parts) < 3:
                continue
            try:
                level = int(parts[0])
                count = int(parts[1])
            except ValueError:
                continue
            pids = [int(x) for x in parts[2:2 + count] if x.isdigit()]
            if len(pids) >= 2:
                out.append({"level": level, "pids": pids})
        break  # 仅第一个存在的文件（mod 覆盖游戏）
    return out


def state_vp_and_resources(states):
    """StateData.states -> (vp_by_state, resource_by_state)。

    vp: {state_id: 总胜利点}；resource: {state_id: 资源总量}。
    """
    vp = {}
    res = {}
    for sid, info in (states or {}).items():
        vp[sid] = sum(int(v) for _pid, v in info.get("victory_points", []))
        res[sid] = sum(int(v) for v in info.get("resources", {}).values())
    return vp, res


# ---------------------------------------------------------------------------
# 着色
# ---------------------------------------------------------------------------

def ramp_colors(norm):
    """归一化 [0,1] 数组 → RGB 数组（蓝→青→绿→黄→红 五段色阶）。"""
    t = np.clip(np.asarray(norm, dtype=np.float64), 0.0, 1.0)
    r = np.zeros_like(t)
    g = np.zeros_like(t)
    b = np.zeros_like(t)
    # 0.00-0.25 蓝→青 (0,0,1)->(0,1,1)
    m = t < 0.25
    s = t[m] / 0.25
    r[m] = 0
    g[m] = s
    b[m] = 1
    # 0.25-0.50 青→绿
    m = (t >= 0.25) & (t < 0.5)
    s = (t[m] - 0.25) / 0.25
    r[m] = 0
    g[m] = 1
    b[m] = 1 - s
    # 0.50-0.75 绿→黄
    m = (t >= 0.5) & (t < 0.75)
    s = (t[m] - 0.5) / 0.25
    r[m] = s
    g[m] = 1
    b[m] = 0
    # 0.75-1.00 黄→红
    m = t >= 0.75
    s = (t[m] - 0.75) / 0.25
    r[m] = 1
    g[m] = 1 - s
    b[m] = 0
    return np.stack([r, g, b], axis=-1)


def build_value_overlay(idm, pid_value, alpha=150, vmin=None, vmax=None):
    """按地块数值生成半透明色阶覆盖层。

    idm: numpy 2D int32 省 ID 矩阵；pid_value: {pid: 数值}
    Returns: (rgba HxWx4 uint8, x0, y0) 或 (None, 0, 0)
    """
    if idm is None or pid_value is None:
        return None, 0, 0
    lut = np.zeros(int(idm.max()) + 1, dtype=np.float64)
    has = np.zeros(int(idm.max()) + 1, dtype=bool)
    for p, v in pid_value.items():
        p = int(p)
        if 0 < p < lut.size:
            lut[p] = float(v)
            has[p] = True
    mask = has[idm]
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None, 0, 0
    vals = lut[idm][ys, xs]
    if vmin is None:
        vmin = float(vals.min()) if vals.size else 0.0
    if vmax is None:
        vmax = float(vals.max()) if vals.size else 0.0
    norm = np.zeros_like(vals)
    if vmax > vmin:
        norm = (vals - vmin) / (vmax - vmin)
    colors = ramp_colors(norm)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    h, w = y1 - y0 + 1, x1 - x0 + 1
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    ly = ys - y0
    lx = xs - x0
    rgba[ly, lx, :3] = (colors * 255).astype(np.uint8)
    rgba[ly, lx, 3] = alpha
    return rgba, x0, y0


def _categorical_colors(count, alpha):
    """生成 count 种高区分度颜色（HSV 黄金角旋转）。"""
    import colorsys
    out = []
    for i in range(count):
        hue = (i * 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.72, 0.95)
        out.append((int(r * 255), int(g * 255), int(b * 255), alpha))
    return out


def build_categorical_overlay(idm, pid_cat, alpha=150):
    """按地块类别生成半透明分类覆盖层（每类别一种颜色）。

    pid_cat: {pid: category_id（任意可哈希 int/str）}；同类同色。
    Returns: (rgba, x0, y0) 或 (None, 0, 0)
    """
    if idm is None or not pid_cat:
        return None, 0, 0
    cats = sorted({str(c) for c in pid_cat.values()})
    if not cats:
        return None, 0, 0
    lut_index = np.zeros(int(idm.max()) + 1, dtype=np.int32)
    lut_index[:] = -1
    for p, c in pid_cat.items():
        p = int(p)
        if 0 < p < lut_index.size:
            lut_index[p] = cats.index(str(c))
    cat_map = lut_index[idm]
    mask = cat_map >= 0
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None, 0, 0
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    h, w = y1 - y0 + 1, x1 - x0 + 1
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    ly = ys - y0
    lx = xs - x0
    idx = cat_map[ys, xs]
    colors = _categorical_colors(len(cats), alpha)
    for ci in range(len(cats)):
        m = idx == ci
        if not np.any(m):
            continue
        c = colors[ci]
        rgba[ly[m], lx[m]] = c
    return rgba, x0, y0


def build_line_overlay(width, height, segments, centroid_fn,
                       level_min=1, level_max=3, alpha=220):
    """把折线段列表渲染为全图 RGBA 覆盖层。

    segments: [{"level": int, "pids": [pid,...]}, ...]
    centroid_fn: pid -> (x, y)（像素坐标）
    线宽随 level 增大（1→2px，2→3px，3→4px）。
    Returns: (rgba HxWx4 uint8, 0, 0)；无有效线段返回 (None,0,0)。
    """
    if not segments or width <= 0 or height <= 0:
        return None, 0, 0
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    drawn = False
    for seg in segments:
        pts = []
        for pid in seg.get("pids", []):
            xy = centroid_fn(pid)
            if xy is not None:
                pts.append(tuple(float(v) for v in xy))
        if len(pts) < 2:
            continue
        level = int(seg.get("level", 1))
        try:
            width_px = {1: 2, 2: 3, 3: 4}[level]
        except KeyError:
            width_px = 2
        color = (205, 92, 92, alpha)
        draw.line(pts, fill=color, width=width_px)
        drawn = True
    if not drawn:
        return None, 0, 0
    return np.asarray(img), 0, 0


def build_river_overlay(rivers_path, alpha=170):
    """从 rivers.bmp 生成河流覆盖层（非背景/非白色像素）。

    Returns: (rgba HxWx4 uint8, 0, 0) 或 (None,0,0)。
    """
    if not rivers_path or not os.path.isfile(rivers_path):
        return None, 0, 0
    try:
        im = Image.open(rivers_path).convert("RGB")
    except Exception:
        return None, 0, 0
    arr = np.asarray(im)
    h, w, _ = arr.shape
    mask = np.ones((h, w), dtype=bool)
    for (r, g, b) in _RIVER_EXCLUDE:
        mask &= ~((arr[:, :, 0] == r) & (arr[:, :, 1] == g)
                  & (arr[:, :, 2] == b))
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = (80, 160, 255)
    rgba[mask, 3] = alpha
    return rgba, 0, 0