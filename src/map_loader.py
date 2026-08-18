"""地图数据加载模块

加载 HOI4 游戏/mod 的地图文件，提供地块识别、地块中心点与高亮掩码查询。
文件优先级：mod 目录优先，缺失回退游戏目录（mod 可完整覆盖地图）。

性能设计：
  - provinces.bmp 一次加载为 numpy 数组，经 2^24 LUT 向量化映射为地块ID矩阵
  - 点击取地块 O(1)；地块中心/掩码按需计算并缓存
"""

import os

import numpy as np
from PyQt6.QtGui import QImage, QPixmap, QColor


class MapData:
    """地图数据：地块表 + 地块ID矩阵 + 底图。"""

    def __init__(self, mod_path="", hoi4_path=""):
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        # 地块ID -> 地块信息 dict(r,g,b,type,coastal,terrain,region)
        self.province_table = {}
        # RGB整数值 -> 地块ID
        self.color_to_id = {}
        # (H,W) uint32 地块ID矩阵（像素坐标 -> 地块ID）
        self.id_map = None
        self.width = 0
        self.height = 0
        # 地块ID -> 中心像素 (x, y)，按需缓存
        self._centroids = {}
        # 底图缓存（provinces.bmp 平坦地块色，地形不影响地图颜色）
        self._base_pixmap = None
        # 地块边界线图层缓存
        self._edge_overlay = None
        # 国家着色图层缓存：focus_tag -> QPixmap
        self._country_overlays = {}
        self._load()

    # ---------- 文件定位 ----------

    def map_file(self, name):
        """按 mod -> 游戏 顺序查找地图文件（公开版）。"""
        return self._map_file(name)

    def _map_file(self, name):
        """按 mod -> 游戏 顺序查找地图文件。"""
        for base in (self.mod_path, self.hoi4_path):
            if base and os.path.isfile(os.path.join(base, "map", name)):
                return os.path.join(base, "map", name)
        return None

    # ---------- 加载 ----------

    def _load(self):
        self._load_definitions()
        self._load_provinces()

    def _load_definitions(self):
        """解析 definition.csv：id;R;G;B;type;coastal;terrain;region"""
        path = self._map_file("definition.csv")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(";")
                    if len(parts) < 8:
                        continue
                    try:
                        pid = int(parts[0])
                        r, g, b = int(parts[1]), int(parts[2]), int(parts[3])
                    except ValueError:
                        continue
                    self.province_table[pid] = {
                        "r": r, "g": g, "b": b,
                        "type": parts[4],
                        "coastal": parts[5].strip().lower() == "true",
                        "terrain": parts[6],
                        "region": int(parts[7]) if parts[7].strip().isdigit() else 0,
                    }
                    self.color_to_id[(r << 16) | (g << 8) | b] = pid
        except Exception:
            pass

    def _load_provinces(self):
        """加载 provinces.bmp 并向量化映射为地块ID矩阵。"""
        path = self._map_file("provinces.bmp")
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            return
        self.width = img.width()
        self.height = img.height()
        img2 = img.convertToFormat(QImage.Format.Format_RGB888)
        ptr = img2.constBits()
        ptr.setsize(img2.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(img2.height(), img2.bytesPerLine())
        arr = np.ascontiguousarray(arr[:, :img2.width() * 3]).reshape(
            img2.height(), img2.width(), 3)
        rgb = (arr[..., 0].astype(np.uint32) << 16
               | arr[..., 1].astype(np.uint32) << 8
               | arr[..., 2].astype(np.uint32))
        # 2^24 查表：定义文件颜色 -> 地块ID
        lut = np.zeros(1 << 24, dtype=np.uint32)
        for color, pid in self.color_to_id.items():
            lut[color] = pid
        self.id_map = lut[rgb]

    # ---------- 查询 ----------

    def province_at(self, x, y):
        """像素坐标 -> 地块ID（越界/无效返回 0）。"""
        if self.id_map is None or not (0 <= x < self.width and 0 <= y < self.height):
            return 0
        return int(self.id_map[y, x])

    def province_mask(self, pid):
        """地块ID -> (H,W) bool 掩码（用于高亮绘制）。"""
        if self.id_map is None:
            return None
        return self.id_map == pid

    def province_centroid(self, pid):
        """地块中心像素 (x, y)，未知地块返回 None。结果缓存。"""
        if pid in self._centroids:
            return self._centroids[pid]
        if self.id_map is None:
            return None
        ys, xs = np.nonzero(self.id_map == pid)
        if xs.size == 0:
            return None
        c = (int(xs.mean()), int(ys.mean()))
        self._centroids[pid] = c
        return c

    def precompute_centroids(self):
        """一次性批量计算全部地块中心并缓存（供基地/兵牌等批量定位）。

        用 bincount 汇总，避免对每个地块做全图掩码扫描（1193 个基地
        逐个扫描约 12 秒，批量计算仅需 1-2 秒）。
        """
        if self.id_map is None or self._centroids:
            return
        ys, xs = np.nonzero(self.id_map)
        if ys.size == 0:
            return
        pids = self.id_map[ys, xs]
        n = int(pids.max()) + 1
        cnt = np.bincount(pids, minlength=n)
        sx = np.bincount(pids, weights=xs.astype(np.float32), minlength=n)
        sy = np.bincount(pids, weights=ys.astype(np.float32), minlength=n)
        for pid in range(1, n):
            if cnt[pid]:
                self._centroids[pid] = (int(sx[pid] / cnt[pid]),
                                        int(sy[pid] / cnt[pid]))

    def is_sea(self, pid):
        info = self.province_table.get(pid)
        return bool(info) and info["type"] in ("sea", "lake", "coastal_sea")

    def base_pixmap(self):
        """底图 QPixmap：provinces.bmp 平坦地块色（地形不再影响地图颜色）。"""
        if self._base_pixmap is None:
            img = QImage()
            for name in ("provinces.bmp", "terrain.bmp"):
                path = self._map_file(name)
                if path:
                    img = QImage(path)
                    if not img.isNull():
                        break
            self._base_pixmap = QPixmap.fromImage(img)
        return self._base_pixmap

    # ---------- 地形演示 ----------

    _terrain_pixmap = None
    _hillshade_pixmap = None

    def terrain_pixmap(self):
        """地形类型图 QPixmap：map/terrain.bmp 原图（平原绿/丘陵黄/山地棕…）。"""
        if self._terrain_pixmap is None:
            path = self._map_file("terrain.bmp")
            if path:
                img = QImage(path)
                if not img.isNull():
                    self._terrain_pixmap = QPixmap.fromImage(img)
        return self._terrain_pixmap

    def hillshade_pixmap(self, alpha=110, light=None):
        """伪 3D 地形立体感图层：heights.bmp 高度图 → hillshade 明暗叠加层。

        取巧方案（零生成成本）：游戏自带 16-bit 高度图，numpy 梯度 + 光照点积
        一次合成半透明 overlay（与 country_overlay 同一模式，缓存复用）。
        """
        if self._hillshade_pixmap is None:
            height = self._load_heights()
            if height is None:
                return None
            if light is None:
                light = (0.5, 0.5, 0.85)  # 西北光照
            shade = hillshade_array(height, light)
            h, w = shade.shape
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[..., 0] = 30
            rgba[..., 1] = 35
            rgba[..., 2] = 45
            rgba[..., 3] = (shade.astype(np.uint16) * alpha // 255).astype(np.uint8)
            img = QImage(rgba.data, w, h, w * 4,
                         QImage.Format.Format_RGBA8888).copy()
            self._hillshade_pixmap = QPixmap.fromImage(img)
        return self._hillshade_pixmap

    def _load_heights(self):
        """读取高度图（16-bit 灰度，QImage 不支持，用 PIL）。

        原版文件名为 map/heightmap.bmp；部分 mod 沿用旧名 heights.bmp。
        """
        path = self._map_file("heightmap.bmp") or self._map_file("heights.bmp")
        if not path:
            return None
        try:
            from PIL import Image
            with Image.open(path) as img:
                arr = np.asarray(img)
            if arr.ndim == 3:
                arr = arr[..., 0]
            return arr.astype(np.float32)
        except Exception:
            return None

    def edge_overlay_pixmap(self):
        """地块边界线图层 QPixmap（深色半透明，叠加在底图上）。

        只绘制陆地块之间的边界与海岸线，剔除海-海边界，避免海洋内部
        线网过密。一次性 numpy 计算并缓存。
        """
        if self._edge_overlay is None:
            self._edge_overlay = self._build_edge_overlay()
        return self._edge_overlay

    def _build_edge_overlay(self):
        empty = QPixmap()
        if self.id_map is None:
            return empty
        idm = self.id_map
        h, w = idm.shape
        n = int(idm.max()) + 1
        sea_arr = np.zeros(n, dtype=bool)
        for pid, info in self.province_table.items():
            if info["type"] in ("sea", "lake", "coastal_sea"):
                sea_arr[pid] = True
        land = ~sea_arr[idm]

        edge = np.zeros((h, w), dtype=bool)
        # 水平边界：右邻像素属于不同地块
        dh = idm[:, :-1] != idm[:, 1:]
        edge[:, :-1] |= dh & (land[:, :-1] | land[:, 1:])
        # 垂直边界：下邻像素属于不同地块
        dv = idm[:-1, :] != idm[1:, :]
        edge[:-1, :] |= dv & (land[:-1, :] | land[1:, :])

        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 3] = np.where(edge, 200, 0)
        rgba[..., 0] = 25
        rgba[..., 1] = 25
        rgba[..., 2] = 25
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(img)

    def theater_outline_pixmap(self, province_ids):
        """AI 派系战区红色描边图层：只描 selected province 的外边界。

        Args:
            province_ids (iterable[int]): 属于战区的全部地块 ID
        """
        empty = QPixmap()
        if self.id_map is None:
            return empty
        idm = self.id_map
        h, w = idm.shape
        n = int(idm.max()) + 1
        mask = np.zeros(n, dtype=bool)
        for pid in province_ids:
            try:
                pid = int(pid)
                if 0 < pid < n:
                    mask[pid] = True
            except Exception:
                continue
        m = mask[idm]
        edge = np.zeros((h, w), dtype=bool)
        dh = m[:, :-1] != m[:, 1:]
        edge[:, :-1] |= dh
        edge[:, 1:] |= dh
        dv = m[:-1, :] != m[1:, :]
        edge[:-1, :] |= dv
        edge[1:, :] |= dv
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 3] = np.where(edge, 255, 0)
        rgba[..., 0] = 255
        rgba[..., 1] = 20
        rgba[..., 2] = 20
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(img)

    # ---------- 国家着色 ----------

    def invalidate_country_overlays(self):
        """清除国家着色层缓存（归属编辑后调用，强制重绘）。"""
        self._country_overlays.clear()

    def country_overlay_pixmap(self, owner_by_pid, focus_tag=None,
                               tag_colors=None):
        """国家着色图层：同一国家统一色块 + 地块边界线 + 国界线 + 焦点金边。

        图层顺序（一次 numpy 合成）：
          1) 所有有主国家领土以各自颜色不透明填充（同一国家严格同色，
             不受底图地块颜色影响；海面保持透明露出底图）
          2) 地块边界线与海岸线（深灰细线，保留地块辨识）
          3) 国界线（深色，标出国家大块分界）
          4) 焦点国家金边

        Args:
            owner_by_pid (dict): 地块ID -> 国家标签
            focus_tag (str): 焦点国家标签（金边高亮），可为空
            tag_colors (dict): 国家标签 -> (r, g, b) 文件颜色（building_lib
                load_country_colors）；缺省/未知用色环均匀分配
        Returns:
            QPixmap: 图层，叠加在底图之上（海面无色）
        """
        key = focus_tag or ""
        if key in self._country_overlays:
            return self._country_overlays[key]
        empty = QPixmap()
        if self.id_map is None:
            return empty
        idm = self.id_map
        h, w = idm.shape

        # 标签 -> 索引，颜色按标签文件色或色环均匀分布
        tags = sorted({t for t in owner_by_pid.values() if t})
        tag_idx = {t: i + 1 for i, t in enumerate(tags)}  # 0 = 无主（海面）

        n = int(idm.max()) + 1
        pid_owner = np.zeros(n, dtype=np.uint32)
        for pid, tag in owner_by_pid.items():
            idx = tag_idx.get(tag)
            if idx and 0 < pid < n:
                pid_owner[pid] = idx
        owner_map = pid_owner[idm]

        def _color(idx):
            # 色环均匀分布（黄金角）
            hue = int((idx - 1) * 137.508) % 360
            return hue, 70, 50

        # 颜色表一次向量化着色
        max_idx = len(tags)
        color_table = np.zeros((max_idx + 1, 3), dtype=np.uint8)
        for idx in range(1, max_idx + 1):
            tag = tags[idx - 1]
            file_c = None
            if tag_colors:
                file_c = tag_colors.get(tag) or tag_colors.get(tag.upper())
            if file_c is not None:
                color_table[idx] = (int(file_c[0]), int(file_c[1]),
                                    int(file_c[2]))
            else:
                hue, sat, light = _color(idx)
                cc = QColor.fromHsl(hue, sat, light)
                color_table[idx] = (cc.red(), cc.green(), cc.blue())

        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        # 1) 同一国家统一色块（不透明填充）
        filled = owner_map > 0
        rgba[filled, 0] = color_table[owner_map[filled], 0]
        rgba[filled, 1] = color_table[owner_map[filled], 1]
        rgba[filled, 2] = color_table[owner_map[filled], 2]
        rgba[filled, 3] = 255

        # 海面掩码（海面无填充，露出底图）
        sea_arr = np.zeros(n, dtype=bool)
        for pid, info in self.province_table.items():
            if info["type"] in ("sea", "lake", "coastal_sea"):
                sea_arr[pid] = True
        land = ~sea_arr[idm]

        # 2) 地块边界线：相邻像素属不同地块（含海岸线，海-海不画）
        prov_edge = np.zeros((h, w), dtype=bool)
        dh = idm[:, :-1] != idm[:, 1:]
        prov_edge[:, :-1] |= dh & (land[:, :-1] | land[:, 1:])
        dv = idm[:-1, :] != idm[1:, :]
        prov_edge[:-1, :] |= dv & (land[:-1, :] | land[1:, :])
        rgba[prov_edge, 0] = 45
        rgba[prov_edge, 1] = 45
        rgba[prov_edge, 2] = 45
        rgba[prov_edge, 3] = 170

        # 3) 国界线：相邻像素属不同国家（海面之间不画）
        edge = np.zeros((h, w), dtype=bool)
        dh = owner_map[:, :-1] != owner_map[:, 1:]
        edge[:, :-1] |= dh & ((owner_map[:, :-1] > 0) | (owner_map[:, 1:] > 0))
        dv = owner_map[:-1, :] != owner_map[1:, :]
        edge[:-1, :] |= dv & ((owner_map[:-1, :] > 0) | (owner_map[1:, :] > 0))
        rgba[edge, 0] = 25
        rgba[edge, 1] = 25
        rgba[edge, 2] = 25
        rgba[edge, 3] = 235

        # 4) 焦点国家金边（最上层）
        focus_idx = tag_idx.get((focus_tag or "").upper(), 0)
        if focus_idx:
            fm = edge & (owner_map == focus_idx)
            rgba[fm, 0] = 255
            rgba[fm, 1] = 215
            rgba[fm, 2] = 0
            rgba[fm, 3] = 255
        img = QImage(rgba.data, w, h, w * 4,
                     QImage.Format.Format_RGBA8888).copy()
        pm = QPixmap.fromImage(img)
        self._country_overlays[key] = pm
        return pm

    def country_centroids(self, owner_by_pid):
        """国家标签 -> 领土中心像素 (x, y)，仅含实际拥有领土的国家。

        用 bincount 批量汇总，避免对每个国家做全图掩码扫描。
        """
        if self.id_map is None or not owner_by_pid:
            return {}
        idm = self.id_map
        n = int(idm.max()) + 1
        pid_owner = np.zeros(n, dtype=np.uint32)
        tags = {}
        for pid, tag in owner_by_pid.items():
            if tag and 0 < pid < n:
                tags.setdefault(tag, len(tags) + 1)
                pid_owner[pid] = tags[tag]
        owner_map = pid_owner[idm]
        ys, xs = np.nonzero(owner_map)
        if ys.size == 0:
            return {}
        labels = owner_map[ys, xs]
        cnt = np.bincount(labels)
        sx = np.bincount(labels, weights=xs.astype(np.float64))
        sy = np.bincount(labels, weights=ys.astype(np.float64))
        inv = {idx: tag for tag, idx in tags.items()}
        out = {}
        for idx in range(1, len(tags) + 1):
            if cnt[idx] > 0:
                out[inv[idx]] = (int(sx[idx] / cnt[idx]),
                                 int(sy[idx] / cnt[idx]))
        return out


def hillshade_array(height, light=(0.5, 0.5, 0.85)):
    """高度图 -> hillshade 明暗数组（0-255，纯 numpy，可测试）。

    Args:
        height: (H, W) float 高度矩阵
        light: 光照方向 (lx, ly, lz)，默认西北光

    Returns:
        (H, W) uint8：0=最暗（背光坡），255=最亮（迎光坡）
    """
    if height is None or height.size == 0:
        return None
    gy, gx = np.gradient(height)
    lx, ly, lz = light
    mag = np.sqrt(gx * gx + gy * gy + 1.0)
    # 表面法线近似 (-gx, -gy, 1) 与光照方向点积 → 明暗
    shade = (-gx * lx - gy * ly + lz) / mag
    shade = np.clip((shade + 1.0) * 0.5 * 255.0, 0, 255)
    return shade.astype(np.uint8)
