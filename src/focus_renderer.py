import os
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsEllipseItem,
    QGraphicsSimpleTextItem
)
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QPixmap, QFont, QPainter
from PyQt6.QtCore import Qt
from dds_loader import DdsLoader


class FocusScene(QGraphicsScene):
    """优化版自定义场景：利用底层 QBrush 平铺代替 Python 循环画线实现网格"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.bg_color = (45, 45, 48)
        self.grid_color = (255, 255, 255)
        self.grid_alpha = 30

        self.grid_size_x = 90
        self.grid_size_y = 130

        self._grid_pixmap = None
        self.setBackgroundBrush(self._create_grid_brush())

    def _create_grid_brush(self):
        self._grid_pixmap = QPixmap(self.grid_size_x, self.grid_size_y)
        self._grid_pixmap.fill(QColor(*self.bg_color))

        painter = QPainter(self._grid_pixmap)
        pen = QPen(QColor(*self.grid_color, self.grid_alpha))
        pen.setWidth(1)
        painter.setPen(pen)

        painter.drawLine(0, 0, self.grid_size_x, 0)
        painter.drawLine(0, 0, 0, self.grid_size_y)
        painter.end()

        return QBrush(self._grid_pixmap)


class FocusRenderer:
    """国策树渲染器：将 focus_data 绘制到 QGraphicsScene 上"""

    def __init__(self, scene: FocusScene):
        self.scene = scene
        self.hoi4_path = ""
        self.mod_path = ""
        self.gfx_map = {}
        self._fallback_pixmap = None
        self._icon_cache = {}
        self._text_font = None
        self.loc_manager = None
        # 国策ID -> (文本项, 节点中心x, 节点中心y, 文本Y偏移)，用于翻译保存后定向重绘
        self._text_layout = {}

    def set_hoi4_path(self, path):
        self.hoi4_path = path
        self._fallback_pixmap = None
        self._icon_cache.clear()

    def set_mod_path(self, path):
        self.mod_path = path or ""
        self._fallback_pixmap = None
        self._icon_cache.clear()

    def set_gfx_map(self, gfx_map):
        self.gfx_map = gfx_map or {}

    def set_loc_manager(self, loc_manager):
        self.loc_manager = loc_manager

    def _get_text_font(self):
        if self._text_font is None:
            self._text_font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
        return self._text_font

    MAX_ICON_SIZE = 192  # 图标解码尺寸上限（超过则缩放，避免超大贴图拖慢绘制）

    def _load_scaled(self, tex_path):
        """加载纹理并限制最大尺寸（过大贴图缩放，兼顾清晰度与性能）。"""
        pm = DdsLoader.load_as_pixmap(tex_path)
        if pm is not None and not pm.isNull():
            w, h = pm.width(), pm.height()
            if max(w, h) > self.MAX_ICON_SIZE:
                pm = pm.scaled(
                    self.MAX_ICON_SIZE, self.MAX_ICON_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
        return pm

    def _get_fallback_pixmap(self):
        if self._fallback_pixmap is not None:
            return self._fallback_pixmap
        candidates = []
        if self.mod_path:
            candidates.append(os.path.join(self.mod_path, "gfx", "interface", "goals", "goal_unknown.dds"))
        if self.hoi4_path:
            candidates.append(os.path.join(self.hoi4_path, "gfx", "interface", "goals", "goal_unknown.dds"))
        for path in candidates:
            pm = DdsLoader.load_as_pixmap(path)
            if pm:
                self._fallback_pixmap = pm
                return pm
        return None

    def _search_icon_dirs(self, icon_name, stripped, base_path):
        """在指定基础路径下查找图标文件（goals/ideas 目录），限制最大尺寸。"""
        goals_dir = os.path.join(base_path, "gfx", "interface", "goals")
        for ext in ('.dds', '.png'):
            result = self._load_scaled(os.path.join(goals_dir, icon_name + ext))
            if result:
                return result
        for ext in ('.dds', '.png'):
            result = self._load_scaled(os.path.join(goals_dir, stripped + ext))
            if result:
                return result

        ideas_dir = os.path.join(base_path, "gfx", "interface", "ideas")
        for ext in ('.dds', '.png'):
            result = self._load_scaled(os.path.join(ideas_dir, icon_name + ext))
            if result:
                return result
        for ext in ('.dds', '.png'):
            result = self._load_scaled(os.path.join(ideas_dir, stripped + ext))
            if result:
                return result
        return None

    def _load_icon_pixmap(self, icon_name):
        if not icon_name or not isinstance(icon_name, str):
            return self._get_fallback_pixmap()

        if icon_name in self._icon_cache:
            return self._icon_cache[icon_name]

        result = None
        if icon_name.startswith("GFX_goal_"):
            stripped = icon_name[9:]
        elif icon_name.startswith("GFX_"):
            stripped = icon_name[4:]
        else:
            stripped = icon_name

        # 1. 通过 gfx_map 直接定位纹理（含游戏与 mod 合并的映射）
        if self.gfx_map and icon_name in self.gfx_map:
            tex_path = self.gfx_map[icon_name]
            result = self._load_scaled(tex_path)
            if result:
                self._icon_cache[icon_name] = result
                return result

        # 2. 在 mod 文件夹内查找图标
        if self.mod_path:
            result = self._search_icon_dirs(icon_name, stripped, self.mod_path)
            if result:
                self._icon_cache[icon_name] = result
                return result

        # 3. 在游戏文件夹内查找图标
        if self.hoi4_path:
            result = self._search_icon_dirs(icon_name, stripped, self.hoi4_path)
            if result:
                self._icon_cache[icon_name] = result
                return result

        legacy_path = f"gfx/{icon_name}.png"
        if os.path.exists(legacy_path):
            result = self._load_scaled(legacy_path)
            if result:
                self._icon_cache[icon_name] = result
                return result

        fallback = self._get_fallback_pixmap()
        self._icon_cache[icon_name] = fallback
        return fallback

    def draw_graph(self, focus_data, file_path):
        self.scene.clear()
        self._icon_cache.clear()
        self._text_layout = {}

        for fid, node in focus_data.items():
            x, y = node['abs_x'], node['abs_y']
            icon_name = node['basic'].get('icon', '')
            if isinstance(icon_name, dict):
                # 动态图标（icon = { GFX_a = {...} GFX_b = {...} }）：取首个精灵名作预览
                for k in icon_name:
                    if isinstance(k, str):
                        icon_name = k
                        break
                else:
                    icon_name = ""

            node_item = None
            offset_y = 32

            pixmap = self._load_icon_pixmap(icon_name)
            if pixmap:
                pix_item = QGraphicsPixmapItem(pixmap)
                pix_item.setPos(x - pixmap.width() / 2, y - pixmap.height() / 2)
                self.scene.addItem(pix_item)
                node_item = pix_item
                offset_y = pixmap.height() / 2
            else:
                ellipse = QGraphicsEllipseItem(-32, -32, 64, 64)
                ellipse.setBrush(QBrush(Qt.GlobalColor.yellow))
                ellipse.setPos(x, y)
                self.scene.addItem(ellipse)
                node_item = ellipse

            node_item.setData(0, fid)
            node_item.setData(1, file_path)

            display_text = fid
            if self.loc_manager:
                cn_name = self.loc_manager.get_name(fid)
                if cn_name:
                    display_text = cn_name

            text_item = QGraphicsSimpleTextItem(display_text)
            text_item.setBrush(QBrush(Qt.GlobalColor.white))
            text_item.setFont(self._get_text_font())
            text_w = text_item.boundingRect().width()
            text_item.setPos(x - text_w / 2, y + offset_y + 5)

            text_item.setData(0, fid)
            text_item.setData(1, file_path)
            self.scene.addItem(text_item)
            # 记录布局，便于翻译保存后只重绘该节点的名称
            self._text_layout[fid] = (text_item, x, y, offset_y)

            for prereq in node['draw']['prerequisite']:
                if prereq in focus_data:
                    target = focus_data[prereq]

                    start_x, start_y = target['abs_x'], target['abs_y'] + 32
                    end_x, end_y = x, y - 32
                    mid_y = (start_y + end_y) / 2

                    path = QPainterPath()
                    path.moveTo(start_x, start_y)
                    path.lineTo(start_x, mid_y)
                    path.lineTo(end_x, mid_y)
                    path.lineTo(end_x, end_y)

                    path_item = QGraphicsPathItem(path)

                    pen = QPen(QColor(180, 180, 180, 255))
                    pen.setWidth(2)
                    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
                    path_item.setPen(pen)

                    path_item.setZValue(-1)
                    path_item.setData(0, fid)

                    self.scene.addItem(path_item)

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100))

    def update_focus_text(self, focus_id, name=None):
        """翻译保存后定向重绘指定国策节点的名称文本。

        可传入最新名称直接更新；未传入时从本地化管理器重新读取。

        Args:
            focus_id (str): 国策ID
            name (str, optional): 最新名称文本，None 时从 loc_manager 读取
        """
        if focus_id not in self._text_layout:
            return
        text_item, x, y, offset_y = self._text_layout[focus_id]
        if name is None:
            name = focus_id
            if self.loc_manager:
                cn = self.loc_manager.get_name(focus_id)
                if cn:
                    name = cn
        text_item.setText(name)
        w = text_item.boundingRect().width()
        text_item.setPos(x - w / 2, y + offset_y + 5)
        self.scene.invalidate()