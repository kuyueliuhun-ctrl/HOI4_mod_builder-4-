"""地图矢量边界层（放大不模糊）

从省 ID 矩阵向量化提取全部地块边界线段（水平/垂直像素边，同向连续段合并），
供 MapCanvas 在放大时以矢量方式绘制：边界锐利清晰，不受位图放大模糊影响。

数据量（原版 5632×2048）：合并后约几十万条线段；渲染时按视口裁剪，
放大后视口内线段数量少，drawForeground 每帧毫秒级。

磁盘缓存：按 (provinces.bmp, definition.csv) 的 (mtime, size) 计算缓存键，
存 .runtime/map_vectors/<key>.npz（列 [x0,y0,x1,y1]，int32）。
"""

from __future__ import annotations
from project_paths import PROJECT_ROOT

import hashlib
import os

import numpy as np


CACHE_ROOT = os.path.join(PROJECT_ROOT,
                          ".runtime", "map_vectors")


def _merge_horizontal(mask):
    """(H,W) bool → 沿行方向合并连续 True run。

    Returns:
        (N,3) int32: [s, start, end]——s 为行索引，[start, end) 为列区间。
    """
    h, w = mask.shape
    out = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([False], row, [False])).astype(np.int8))
        starts = np.where(d == 1)[0]
        ends = np.where(d == -1)[0]
        for s, e in zip(starts, ends):
            out.append((y, s, e))
    if not out:
        return np.zeros((0, 3), dtype=np.int32)
    return np.asarray(out, dtype=np.int32)


def build_edge_segments(id_map, sea_pids=None):
    """从省 ID 矩阵提取全部地块边界线段（向量化，同向合并）。

    Args:
        id_map: (H, W) uint32 省 ID 矩阵
        sea_pids: 海域省 id 集合（用于剔除海-海边界；None 保留全部）

    Returns:
        np.ndarray (N, 4) int32: [x0, y0, x1, y1]
            竖直线段: x0==x1（边界在像素右缘，格点坐标）；
            水平线段: y0==y1（边界在像素下缘，格点坐标）
    """
    idm = np.asarray(id_map)
    h, w = idm.shape
    if h == 0 or w == 0:
        return np.zeros((0, 4), dtype=np.int32)

    land = None
    if sea_pids:
        lut = np.zeros(int(idm.max()) + 1, dtype=bool)
        for p in sea_pids:
            if 0 < p < lut.size:
                lut[p] = True
        land = ~lut[idm]

    # 垂直边界（水平相邻像素不同省）：True 像素 (y,x) 的右缘有竖直线段。
    # 同一竖直线 = 同一列上纵向连续 → 转置后按行（=原列）合并。
    dh = idm[:, :-1] != idm[:, 1:]
    if land is not None:
        dh &= (land[:, :-1] | land[:, 1:])
    v = _merge_horizontal(dh.T)          # (x, y0, y1)

    # 水平边界（垂直相邻像素不同省）：True 像素 (y,x) 的下缘有水平线段。
    # 同一水平线 = 同一行上横向连续 → 按行合并。
    dv = idm[:-1, :] != idm[1:, :]
    if land is not None:
        dv &= (land[:-1, :] | land[1:, :])
    hsegs = _merge_horizontal(dv)        # (y, x0, x1)

    parts = []
    if v.size:
        parts.append(np.column_stack((v[:, 0] + 1, v[:, 1],
                                      v[:, 0] + 1, v[:, 2])))
    if hsegs.size:
        parts.append(np.column_stack((hsegs[:, 1], hsegs[:, 0] + 1,
                                      hsegs[:, 2], hsegs[:, 0] + 1)))
    if not parts:
        return np.zeros((0, 4), dtype=np.int32)
    return np.concatenate(parts, axis=0).astype(np.int32)


# ---------------------------------------------------------------- 缓存

def cache_key(map_data):
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


def load_cached_segments(key):
    """读取缓存线段；无缓存返回 None。"""
    if not key:
        return None
    fp = os.path.join(CACHE_ROOT, key + ".npy")
    if not os.path.isfile(fp):
        return None
    try:
        return np.load(fp)
    except Exception:
        return None


def save_cached_segments(key, segs):
    """写入缓存（失败静默，不影响功能）。"""
    if not key:
        return
    try:
        os.makedirs(CACHE_ROOT, exist_ok=True)
        fp = os.path.join(CACHE_ROOT, key + ".npy")
        tmp = fp + ".tmp.npy"   # np.save 自动补 .npy 后缀，tmp 名须带后缀
        np.save(tmp, segs)
        os.replace(tmp, fp)
    except Exception:
        pass


def get_edge_segments(map_data):
    """取边界线段（带磁盘缓存）：MapData → (N,4) int32 数组。"""
    key = cache_key(map_data)
    segs = load_cached_segments(key) if key else None
    if segs is None:
        sea_pids = [pid for pid, info in map_data.province_table.items()
                    if info.get("type") in ("sea", "lake", "coastal_sea")]
        segs = build_edge_segments(map_data.id_map, sea_pids=sea_pids)
        if key:
            save_cached_segments(key, segs)
    return segs
