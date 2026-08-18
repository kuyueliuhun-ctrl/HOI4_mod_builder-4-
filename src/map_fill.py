"""地图矢量多边形填充层（放大不模糊 v2）

从省 ID 矩阵提取全部省份的闭合轮廓多边形，供 MapCanvas 高倍缩放时以
矢量填充替代位图底图：省内部与边界都锐利清晰，不随放大模糊。

算法（Marching Squares 的全局等价实现，全批量 numpy）：

1. **有向单位边**：对 4 邻域像素差提取全部地块边界单位边，每条边归属
   其左侧省份（省在左，方向绕省一周）；地图外边界用 0 哨兵填充，
   使轮廓在地图边缘闭合。每个省的所有有向边构成若干闭合环。
2. **左转规则链接**：每个网格顶点处，出边按「最左转 → 直行 → 右转」
   优先（排除掉头），一次向量化求出每条边的 next 指针
   —— 这正是 marching squares 的轮廓追踪规则，能正确处理鞍点
   （对角相邻省）与多连通区域（环状省的内外环）。
3. **环提取**：沿 next 指针走圈，得到每省的闭合轮廓环（像素精度）。
4. **批量简化**：全部环拼接后整体向量化 —— 闭合链填充（让接缝处
   的共线关系在环语义下正确）→ 共线塌缩 → Douglas-Peucker（按波
   批量处理所有活动线段）。

磁盘缓存：与 map_vector 同键（provinces.bmp + definition.csv 的
(mtime, size)），存 .runtime/map_fill/<key>.npz。

数据布局（npz）：
    verts     (M, 2) float32  简化后的环顶点（开环：v0..v_{k-1}）
    loop_off  (K+1,) int32    verts 的环区间偏移
    loop_pid  (K,) int32      每环所属省 id
    loop_bbox (K, 4) float32  每环包围盒 [x0, y0, x1, y1]
"""

from __future__ import annotations
from project_paths import PROJECT_ROOT

import hashlib
import os

import numpy as np


CACHE_ROOT = os.path.join(PROJECT_ROOT,
                          ".runtime", "map_fill")

# 方向编码：0=E(+x) 1=N(-y) 2=W(-x) 3=S(+y)；左转 = (d+1)%4，掉头 = (d+2)%4
DIR_E, DIR_N, DIR_W, DIR_S = 0, 1, 2, 3


def _pad_id_map(id_map):
    """(H,W) uint32 → (H+2, W+2) uint32：0 哨兵边框（地图外/未映射区域）。"""
    h, w = id_map.shape
    pad = np.zeros((h + 2, w + 2), dtype=id_map.dtype)
    pad[1:-1, 1:-1] = id_map
    return pad


def _directed_edges(pad):
    """从哨兵填充矩阵提取全部有向单位边（省在左，pid>0 才有边）。

    Returns:
        (starts, ends, dirs, pids): 各为 (N,) 数组——
            starts/ends: (x, y) 网格顶点（x∈[0,w], y∈[0,h]）
            dirs: 方向编码；pids: 左侧省份 id（跳过 pid 0）
    """
    start_parts, end_parts, dir_parts, pid_parts = [], [], [], []

    # 垂直边：pad[py,px]（西）与 pad[py,px+1]（东）不同 → 网格线 x=px, y∈[py-1,py]
    dh = pad[:, :-1] != pad[:, 1:]
    vdy, vdx = np.nonzero(dh)
    west = pad[vdy, vdx]
    east = pad[vdy, vdx + 1]

    # 西侧省份 → 方向北：从 (px, py) 到 (px, py-1)
    wm = west != 0
    if wm.any():
        y = vdy[wm]
        x = vdx[wm]
        start_parts.append(np.column_stack((x, y)))
        end_parts.append(np.column_stack((x, y - 1)))
        dir_parts.append(np.full(int(wm.sum()), DIR_N, dtype=np.int8))
        pid_parts.append(west[wm])
    # 东侧省份 → 方向南：从 (px, py-1) 到 (px, py)
    em = east != 0
    if em.any():
        y = vdy[em]
        x = vdx[em]
        start_parts.append(np.column_stack((x, y - 1)))
        end_parts.append(np.column_stack((x, y)))
        dir_parts.append(np.full(int(em.sum()), DIR_S, dtype=np.int8))
        pid_parts.append(east[em])

    # 水平边：pad[py,px]（北）与 pad[py+1,px]（南）不同 → 网格线 y=py, x∈[px-1,px]
    dv = pad[:-1, :] != pad[1:, :]
    hdy, hdx = np.nonzero(dv)
    north = pad[hdy, hdx]
    south = pad[hdy + 1, hdx]

    # 北侧省份 → 方向东：从 (px-1, py) 到 (px, py)
    nm = north != 0
    if nm.any():
        y = hdy[nm]
        x = hdx[nm]
        start_parts.append(np.column_stack((x - 1, y)))
        end_parts.append(np.column_stack((x, y)))
        dir_parts.append(np.full(int(nm.sum()), DIR_E, dtype=np.int8))
        pid_parts.append(north[nm])
    # 南侧省份 → 方向西：从 (px, py) 到 (px-1, py)
    sm = south != 0
    if sm.any():
        y = hdy[sm]
        x = hdx[sm]
        start_parts.append(np.column_stack((x, y)))
        end_parts.append(np.column_stack((x - 1, y)))
        dir_parts.append(np.full(int(sm.sum()), DIR_W, dtype=np.int8))
        pid_parts.append(south[sm])

    starts = np.concatenate(start_parts, axis=0).astype(np.int32)
    ends = np.concatenate(end_parts, axis=0).astype(np.int32)
    dirs = np.concatenate(dir_parts).astype(np.int8)
    pids = np.concatenate(pid_parts).astype(np.int32)
    return starts, ends, dirs, pids


def _link_next(starts, ends, dirs):
    """左转规则求每条边的 next 指针（Marching Squares 轮廓追踪，向量化）。

    顶点按 (x*stride + y) 1D key 唯一化（避免 np.unique(axis=0) 的慢路径），
    出边按方向散列到 4 槽位矩阵；一条边到达终点顶点后，从「左转、直行、
    右转」（排除掉头）中选第一条存在的出边作为 next。

    Returns:
        np.ndarray (N,) int32 next 指针（-1 = 无出边，正常网格不应出现）
    """
    n = starts.shape[0]
    stride = int(starts[:, 1].max()) + 1 or 1
    keys = (starts[:, 0].astype(np.int64) * stride
            + starts[:, 1].astype(np.int64))
    keys = np.concatenate((keys, ends[:, 0].astype(np.int64) * stride
                           + ends[:, 1].astype(np.int64)))
    _, inv = np.unique(keys, return_inverse=True)
    inv_starts = inv[:n]
    inv_ends = inv[n:]

    mat = np.full((int(inv.max()) + 1, 4), -1, dtype=np.int32)
    # 同一顶点同方向最多一条出边（网格结构保证），直接散列即可
    mat[inv_starts, dirs.astype(np.int32)] = np.arange(n)

    d = dirs.astype(np.int32)
    v = inv_ends
    left = mat[v, (d + 1) % 4]
    straight = mat[v, d]
    right = mat[v, (d + 3) % 4]
    return np.where(left >= 0, left,
                    np.where(straight >= 0, straight, right))


def _extract_loops(nxt, n_edges):
    """沿 next 指针提取闭合环（返回每个环的边索引列表）。

    正常网格中每条边恰好属于一个闭合环；next=-1 或落入已访问环的
    残链（哨兵缺失等异常输入）直接丢弃。
    """
    rings = []
    visited = bytearray(n_edges)
    for i in range(n_edges):
        if visited[i]:
            continue
        ring = []
        cur = i
        while cur >= 0 and not visited[cur]:
            visited[cur] = 1
            ring.append(cur)
            cur = nxt[cur]
        if ring and cur == i:
            rings.append(ring)
    return rings


def build_province_polygons(id_map, tol=1.0, progress=None):
    """从省 ID 矩阵构建全部省份闭合轮廓（Marching Squares + DP 简化）。

    Args:
        id_map: (H, W) uint32 省 ID 矩阵
        tol: Douglas-Peucker 简化容差（像素；1.0 = 亚像素精度）
        progress: 可选回调 fn(stage: str, done: int, total: int)

    Returns:
        dict: {"verts": (M,2) float32, "loop_off": (K+1,) int32,
               "loop_pid": (K,) int32, "loop_bbox": (K,4) float32}
    """
    idm = np.asarray(id_map)
    if idm.ndim != 2 or idm.size == 0:
        raise ValueError("id_map 必须是非空二维数组")

    if progress:
        progress("edges", 0, 4)
    pad = _pad_id_map(idm)
    starts, ends, dirs, pids = _directed_edges(pad)
    n_edges = starts.shape[0]

    empty = {"verts": np.zeros((0, 2), dtype=np.float32),
             "loop_off": np.zeros(1, dtype=np.int32),
             "loop_pid": np.zeros(0, dtype=np.int32),
             "loop_bbox": np.zeros((0, 4), dtype=np.float32)}
    if n_edges == 0:
        return empty

    if progress:
        progress("link", 1, 4)
    nxt = _link_next(starts, ends, dirs)

    if progress:
        progress("loops", 2, 4)
    rings = _extract_loops(nxt, n_edges)
    if not rings:
        return empty
    ring_idx = np.concatenate(rings) if len(rings) > 1 else np.asarray(
        rings[0], dtype=np.int32)
    ring_off = np.zeros(len(rings) + 1, dtype=np.int32)
    np.cumsum([len(r) for r in rings], out=ring_off[1:], dtype=np.int32)
    ring_pids = pids[ring_idx[ring_off[:-1]]]

    if progress:
        progress("simplify", 3, 4)
    flat = np.column_stack((starts[ring_idx, 0], starts[ring_idx, 1]))
    simp_flat, simp_off = _simplify_loops_batch(flat, ring_off, tol)

    verts = simp_flat.astype(np.float32)
    x0 = np.minimum.reduceat(verts[:, 0], simp_off[:-1])[:, None]
    y0 = np.minimum.reduceat(verts[:, 1], simp_off[:-1])[:, None]
    x1 = np.maximum.reduceat(verts[:, 0], simp_off[:-1])[:, None]
    y1 = np.maximum.reduceat(verts[:, 1], simp_off[:-1])[:, None]
    return {
        "verts": verts,
        "loop_off": simp_off.astype(np.int32),
        "loop_pid": ring_pids.astype(np.int32),
        "loop_bbox": np.concatenate((x0, y0, x1, y1), axis=1).astype(
            np.float32),
    }


# ---------------------------------------------------------------- 简化

def _simplify_loops_batch(flat, off, tol):
    """批量简化全部环（向量化）：闭合链填充 → 共线塌缩 → 接缝修剪 → DP。

    Args:
        flat: (n, 2) int32 按环顺序拼接的顶点
        off: (K+1,) int32 环边界偏移
        tol: DP 容差（<=0 跳过 DP）

    Returns:
        (verts', off'): 简化后的扁平顶点与环边界
    """
    K = off.shape[0] - 1
    if K == 0:
        return flat, off
    block_len = off[1:] - off[:-1]

    # ---- 1) 闭合链填充：每环 [last, v0..v_{k-1}, first] ----
    # 让接缝（v_{k-1}→v0）的共线关系在环语义下参与塌缩，
    # 首点 v0 的进边就是闭合边，线性检查即完整正确。
    n = flat.shape[0]
    new_len = n + 2 * K
    new_flat = np.empty((new_len, 2), dtype=flat.dtype)
    loop_of = np.repeat(np.arange(K), block_len)
    new_flat[np.arange(n) + 2 * loop_of + 1] = flat
    new_flat[off[:-1] + 2 * np.arange(K)] = flat[off[1:] - 1]      # last_i
    new_flat[off[1:] + 2 * np.arange(K) + 1] = flat[off[:-1]]      # first_i 副本
    new_off = (off + 2 * np.arange(K + 1)).astype(np.int64)
    new_off[-1] = new_len

    # ---- 2) 共线塌缩（单位边方向精确相等即可） ----
    d = np.diff(new_flat, axis=0)
    same = np.all(d[:-1] == d[1:], axis=1)
    keep = np.ones(new_len, dtype=bool)
    # 可塌缩位置：链内点且非填充位（pad 在 new_off[i] 与 new_off[i+1]-1）。
    # 闭合链表示下每个原环点都有真实的环语义邻边（首点进边=闭合边），
    # 全部参与检查；仅填充位（last 前置 / first 后置）强制剔除。
    interior = np.ones(new_len, dtype=bool)
    interior[new_off[:-1]] = False
    interior[new_off[1:] - 1] = False
    idx = np.nonzero(interior)[0]
    keep[idx] = ~same[idx - 1]
    # 剔除填充位
    keep[new_off[:-1]] = False
    keep[new_off[1:] - 1] = False

    flat2 = new_flat[keep]
    cnt = np.add.reduceat(keep, new_off[:-1].astype(np.int64))
    off2 = np.zeros(K + 1, dtype=np.int64)
    np.cumsum(cnt, out=off2[1:])
    off2 = off2.astype(np.int32)

    # 防御：塌缩后不足 3 点的环（退化输入）恢复原环
    small = np.nonzero((off2[1:] - off2[:-1]) < 3)[0]
    if small.size:
        parts = [flat2[off2[i]:off2[i + 1]] for i in range(K)
                 if i not in set(small.tolist())]
        for i in small:
            parts.append(flat[off[i]:off[i + 1]].copy())
        order = [i for i in range(K) if i not in set(small.tolist())] \
            + small.tolist()
        flat2 = np.concatenate(parts, axis=0)
        off2 = np.zeros(K + 1, dtype=np.int32)
        np.cumsum([len(p) for p in parts], out=off2[1:])

    # ---- 3) 接缝修剪（向量化检测 + 少数环逐环修复） ----
    flat2, off2 = _trim_seams_batch(flat2, off2)

    # ---- 4) Douglas-Peucker（按波批量处理全部活动线段） ----
    if tol > 0:
        flat2, off2 = _dp_batch(flat2, off2, float(tol))

    return flat2, off2


def _trim_seams_batch(flat, off, tol_ratio=0.0):
    """批量接缝修剪：检测首/尾点与闭合边共线的环，逐环修复。

    闭合链填充后绝大多数环已最优；仅当塌缩级联（缝处连续多个共线点）
    时首尾仍有共线残点，这里向量化检测、只对命中环做逐环修剪。
    """
    K = off.shape[0] - 1
    if K <= 1:
        return flat, off
    first = off[:-1]
    last = off[1:] - 1
    d_close = flat[first] - flat[last]
    d_first = flat[first + 1] - flat[first]
    d_last = flat[last] - flat[last - 1]
    flag = ((d_close[:, 0] * d_first[:, 1] - d_close[:, 1] * d_first[:, 0])
            == 0) | ((d_close[:, 0] * d_last[:, 1]
                      - d_close[:, 1] * d_last[:, 0]) == 0)
    hit = np.nonzero(flag)[0]
    if hit.size == 0:
        return flat, off
    parts = []
    new_off = [0]
    hit_set = set(int(i) for i in hit)
    for i in range(K):
        if i in hit_set:
            pts = _trim_seam(flat[off[i]:off[i + 1]])
        else:
            pts = flat[off[i]:off[i + 1]]
        parts.append(pts)
        new_off.append(new_off[-1] + pts.shape[0])
    return np.concatenate(parts, axis=0), np.asarray(new_off, dtype=np.int32)


def _trim_seam(pts):
    """单环接缝修剪：首/尾点与闭合边共线（或与首点重合）则删，直到
    接缝两端成为真正的角点（或环退化）。"""
    while pts.shape[0] >= 4:
        if pts[0, 0] == pts[-1, 0] and pts[0, 1] == pts[-1, 1]:
            pts = pts[:-1]
            continue
        d_close = pts[0] - pts[-1]
        d_first = pts[1] - pts[0]
        d_last = pts[-1] - pts[-2]
        if d_close[0] * d_first[1] - d_close[1] * d_first[0] == 0:
            pts = pts[1:]
            continue
        if d_close[0] * d_last[1] - d_close[1] * d_last[0] == 0:
            pts = pts[:-1]
            continue
        break
    return pts


def _dp_batch(flat, off, tol):
    """批量 Douglas-Peucker：所有环的活动线段按「波」同步推进。

    每波把所有活动线段一次向量化计算段内最大偏差；超容差的线段在
    最大偏差点分裂成两条新线段进入下一波。线段按长度 2 的幂分桶，
    桶内最大/最小长度 ≤ 2 倍，垫高浪费有界（每波 ~2× 真实工作量）。
    """
    K = off.shape[0] - 1
    lens = off[1:] - off[:-1]
    big = np.nonzero(lens >= 4)[0]
    if big.size == 0:
        return flat, off

    n = flat.shape[0]
    keep = np.ones(n, dtype=bool)
    # 短环整体保留；长环参与 DP
    a = off[big].astype(np.int64)
    b = (off[big + 1] - 1).astype(np.int64)
    keep[a] = True
    keep[b] = True

    f64 = flat.astype(np.float64)
    while True:
        lens = b - a
        mask = lens >= 2
        if not mask.any():
            break
        aa, bb = a[mask], b[mask]
        lens = lens[mask]
        bk = np.floor(np.log2(lens.astype(np.float64))).astype(np.int32)
        new_a, new_b = [], []
        any_split = False
        for k in range(int(bk.max()), -1, -1):
            sel = bk == k
            if not sel.any():
                continue
            aa2, bb2 = aa[sel], bb[sel]
            max_len = int((bb2 - aa2).max())
            idx = np.minimum(aa2[:, None] + np.arange(1, max_len),
                             (bb2 - 1)[:, None])
            pts = f64[idx]                              # (S, L, 2)
            seg = f64[bb2] - f64[aa2]
            seg_len2 = np.maximum((seg * seg).sum(-1), 1e-12)
            t = ((pts - f64[aa2][:, None, :]) * seg[:, None, :]).sum(-1) \
                / seg_len2[:, None]
            np.clip(t, 0.0, 1.0, out=t)
            proj = f64[aa2][:, None, :] + seg[:, None, :] * t[..., None]
            dist = np.sqrt(((pts - proj) ** 2).sum(-1))
            dmax = dist.max(-1)
            spl = dmax > tol
            if spl.any():
                any_split = True
                mx = dist.argmax(-1) + 1
                keep[aa2 + mx] = True
                new_a.append(np.concatenate((aa2[spl],
                                             aa2[spl] + mx[spl])))
                new_b.append(np.concatenate((aa2[spl] + mx[spl],
                                             bb2[spl])))
            # 未分裂段已完成（段内最大偏差 ≤ tol），不再进入后续波
        if not any_split:
            break
        a = np.concatenate(new_a)
        b = np.concatenate(new_b)

    flat2 = flat[keep]
    cnt = np.add.reduceat(keep, off[:-1])
    off2 = np.zeros(K + 1, dtype=np.int32)
    np.cumsum(cnt, out=off2[1:])
    return flat2, off2


# ---------------------------------------------------------------- 缓存

def _cache_key(map_data):
    """按地图源文件 (mtime, size) 计算缓存键（mod 覆盖地图时自动失效）。"""
    digest = hashlib.sha1()
    for name in ("provinces.bmp", "definition.csv"):
        path = map_data.map_file(name)
        if not path:
            return None
        try:
            st = os.stat(path)
            digest.update(name.encode("utf-8"))
            digest.update(b"%d|%d|" % (int(st.st_mtime), st.st_size))
        except OSError:
            return None
    return digest.hexdigest()[:20]


def load_cached_fill(key):
    """读取缓存填充数据；无缓存返回 None。"""
    if not key:
        return None
    fp = os.path.join(CACHE_ROOT, key + ".npz")
    if not os.path.isfile(fp):
        return None
    try:
        with np.load(fp) as z:
            return FillData(
                verts=z["verts"], loop_off=z["loop_off"],
                loop_pid=z["loop_pid"], loop_bbox=z["loop_bbox"])
    except Exception:
        return None


def save_cached_fill(key, fill):
    """写入缓存（失败静默，不影响功能）。"""
    if not key or fill is None:
        return
    try:
        os.makedirs(CACHE_ROOT, exist_ok=True)
        fp = os.path.join(CACHE_ROOT, key + ".npz")
        tmp = fp + ".tmp"
        np.savez(tmp, verts=fill.verts, loop_off=fill.loop_off,
                 loop_pid=fill.loop_pid, loop_bbox=fill.loop_bbox)
        os.replace(tmp, fp)
    except Exception:
        pass


class FillData:
    """闭合轮廓多边形集合：verts + 环区间 + 环省份 + 环包围盒。"""

    def __init__(self, verts, loop_off, loop_pid, loop_bbox):
        self.verts = np.asarray(verts, dtype=np.float32)
        self.loop_off = np.asarray(loop_off, dtype=np.int32)
        self.loop_pid = np.asarray(loop_pid, dtype=np.int32)
        self.loop_bbox = np.asarray(loop_bbox, dtype=np.float32)
        if self.loop_off.shape[0] != self.loop_pid.shape[0] + 1:
            raise ValueError("loop_off 长度必须等于 loop_pid 长度 + 1")

    @property
    def n_loops(self):
        return self.loop_pid.shape[0]

    def loop_vertices(self, li):
        """第 li 个环的顶点数组 (k, 2) float32。"""
        return self.verts[self.loop_off[li]:self.loop_off[li + 1]]

    def loops_in_rect(self, x0, y0, x1, y1):
        """与矩形 [x0,x1]×[y0,y1] 包围盒相交的环索引（向量化）。"""
        if self.n_loops == 0:
            return np.zeros(0, dtype=np.int64)
        bb = self.loop_bbox
        return np.nonzero((bb[:, 0] <= x1) & (bb[:, 2] >= x0)
                          & (bb[:, 1] <= y1) & (bb[:, 3] >= y0))[0]

    def pids_in_rect(self, x0, y0, x1, y1):
        """矩形覆盖到的省份 id（去重排序）。"""
        idx = self.loops_in_rect(x0, y0, x1, y1)
        if idx.size == 0:
            return []
        return sorted(set(int(p) for p in self.loop_pid[idx]))


def get_province_polygons(map_data, tol=1.0):
    """取省份闭合轮廓（带磁盘缓存）：MapData → FillData 或 None。"""
    key = _cache_key(map_data)
    fill = load_cached_fill(key) if key else None
    if fill is None:
        if map_data.id_map is None:
            return None
        parts = build_province_polygons(map_data.id_map, tol=tol)
        fill = FillData(parts["verts"], parts["loop_off"],
                        parts["loop_pid"], parts["loop_bbox"])
        if key:
            save_cached_fill(key, fill)
    return fill
