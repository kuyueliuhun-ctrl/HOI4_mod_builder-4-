"""MIO 游戏美术组件层（主题与编辑器全局主题保持一致，仅图片组件）。

复用游戏自带的两张 MIO 主视觉素材（mod 优先于游戏目录）：
- mio_details_background*.dds（945x660，GFX_MIO_details_background[_tank/_plane/_ship/_materiel]）
  游戏内 MIO 详情页的大幅插画背景（工厂/坦克/飞机/军舰主题的暗色照片级插画）。
- mio_entry_bg.dds（1040x100，GFX_mio_entry_bg）
  游戏内 MIO 列表条目的横幅底板（左侧深色徽章区 + 金属渐变条 + 黄铜描边）。

主题原则：颜色一律取自 `theme.COLORS` 全局令牌（与编辑器其他部分一致）；
仅"叠在游戏图片上"的文字使用专属浅色（图片本身是暗色素材）。
素材缺失时回退到全局主题的浅色绘制，文字颜色随之自适应。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from theme import COLORS as C

# 游戏素材相对目录（mio_loader 同款相对根：mod 或游戏根目录）
ART_DIR_REL = "gfx/interface/military_industrial_organization"

# 素材名：两张主视觉图
ART_ENTRY_BG = "mio_entry_bg.dds"
ART_DETAILS_PREFIX = "mio_details_background"

# 叠在游戏暗色图片上的文字色（图片专属，不走全局令牌）
ART_OVERLAY = {
    "text": "#f5ecd6",      # 羊皮纸浅字（叠在暗色素材上）
    "shadow": "#000000",    # 文字阴影
}

_PIXMAP_CACHE = {}


def resolve_art_path(name, mod_path="", hoi4_path=""):
    """解析游戏美术文件绝对路径；mod 优先。找不到返回空串。"""
    rel = "%s/%s" % (ART_DIR_REL, name)
    for root in (mod_path or "", hoi4_path or ""):
        if not root:
            continue
        cand = "%s/%s" % (root.rstrip("/"), rel)
        if os.path.isfile(cand):
            return cand
    return ""


def details_variant_for(equipment_type):
    """按 equipment_type 选详情插画变体（对应游戏 GFX_MIO_details_background_*）。

    tank→tank；plane/fighter/air→plane；ship/hull/naval→ship；
    materiel/infantry/artillery/support→factory；其余→通用版。
    """
    types = equipment_type
    if isinstance(types, str):
        types = [types]
    text = " ".join(str(t or "").lower() for t in (types or []))
    if "tank" in text or "armor" in text:
        return ART_DETAILS_PREFIX + "_tank.dds"
    if "plane" in text or "air" in text or "fighter" in text:
        return ART_DETAILS_PREFIX + "_plane.dds"
    if "ship" in text or "naval" in text or "hull" in text:
        return ART_DETAILS_PREFIX + "_ship.dds"
    if text.strip():
        return ART_DETAILS_PREFIX + "_factory.dds"
    return ART_DETAILS_PREFIX + ".dds"


def load_art_pixmap(name, mod_path="", hoi4_path=""):
    """加载游戏美术为 QPixmap（带内存缓存）；失败返回 null QPixmap。"""
    key = (name, mod_path or "", hoi4_path or "")
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]
    pm = QPixmap()
    path = resolve_art_path(name, mod_path, hoi4_path)
    if path:
        try:
            from dds_loader import DdsLoader
            loaded = DdsLoader.load_as_pixmap(path)
            if loaded is not None:
                pm = loaded
        except Exception:
            pm = QPixmap()
    _PIXMAP_CACHE[key] = pm
    return pm


def _draw_cropped(qp, art, w, h, vx=0.5, vy=0.4):
    """等比缩放铺满 (w,h) 后按视点比例裁切绘制，避免拉伸变形。"""
    scaled = art.scaled(
        w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation)
    sx = int((scaled.width() - w) * vx)
    sy = int((scaled.height() - h) * vy)
    qp.drawPixmap(0, 0, scaled, sx, sy, w, h)


def _paint_fallback_panel(qp, rect, border=True):
    """无素材时的回退底板：全局主题浅色 + 微渐变。"""
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0.0, QColor(C["bg_surface"]))
    grad.setColorAt(1.0, QColor(C["bg_surface_subtle"]))
    qp.fillRect(rect, grad)
    if border:
        qp.setPen(QPen(QColor("#c9d3dc"), 1))
        qp.drawRect(rect.adjusted(0, 0, -1, -1))


def _draw_shadow_text(qp, x, y, text, color, font, shadow=ART_OVERLAY["shadow"]):
    qp.setFont(font)
    qp.setPen(QColor(shadow))
    qp.drawText(x + 1, y + 1, text)
    qp.setPen(QColor(color))
    qp.drawText(x, y, text)


class BannerWidget(QWidget):
    """游戏条目横幅风格标题栏（mio_entry_bg 底板 + 图标位 + 标题 + 动作按钮）。

    主题：有素材时文字用浅色（素材为暗色图）；无素材回退全局主题浅色面板，
    文字切回主题主色，保证两种状态都可读。
    """

    HEIGHT = 68

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self._mod_path = mod_path or ""
        self._hoi4_path = hoi4_path or ""
        self._art = load_art_pixmap(ART_ENTRY_BG, self._mod_path,
                                    self._hoi4_path)
        self.setFixedHeight(self.HEIGHT)
        self.icon_label = QLabel("🏭")
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel("—")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self._apply_text_color()
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        row.addWidget(self.icon_label)
        row.addWidget(self.title_label, 1)

    def _apply_text_color(self):
        """按有无素材自适应标题颜色。"""
        color = ART_OVERLAY["text"] if not self._art.isNull() else C["text_primary"]
        self.title_label.setStyleSheet(
            "color:%s; background:transparent;" % color)

    def set_title(self, text):
        self.title_label.setText(text or "—")

    def paintEvent(self, event):
        qp = QPainter(self)
        if not self._art.isNull():
            qp.fillRect(self.rect(), QColor(ART_OVERLAY["shadow"]))
            _draw_cropped(qp, self._art, self.width(), self.height(),
                          vx=0.5, vy=0.5)
        else:
            _paint_fallback_panel(qp, QRectF(self.rect()))


class IllustrationHeader(QWidget):
    """游戏详情页插画头图（mio_details_background_* 裁切填充 + 组织信息叠字）。"""

    HEIGHT = 128

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self._mod_path = mod_path or ""
        self._hoi4_path = hoi4_path or ""
        self._art = QPixmap()
        self._title = ""
        self._subtitle = ""
        self.setFixedHeight(self.HEIGHT)

    def set_org(self, org_id, equipment_types=(), loc=None):
        """按组织更新插画变体与叠字。"""
        variant = details_variant_for(equipment_types)
        self._art = load_art_pixmap(variant, self._mod_path, self._hoi4_path)
        self._title = org_id or ""
        types_text = " ".join(equipment_types or []) if equipment_types else ""
        if types_text and loc is not None:
            shown = []
            for t in equipment_types or []:
                try:
                    shown.append(loc(t) or t)
                except Exception:
                    shown.append(t)
            types_text = " ".join(shown)
        self._subtitle = types_text
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        w, h = self.width(), self.height()
        has_art = not self._art.isNull()
        if has_art:
            qp.fillRect(0, 0, w, h, QColor(ART_OVERLAY["shadow"]))
            _draw_cropped(qp, self._art, w, h, vx=0.5, vy=0.45)
            # 底部渐晕，保证文字可读
            grad = QLinearGradient(0, h * 0.35, 0, h)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(1.0, QColor(0, 0, 0, 170))
            qp.fillRect(0, int(h * 0.35), w, int(h * 0.65), grad)
            qp.setPen(QPen(QColor("#3d382c"), 1))
            qp.drawRect(0, 0, w - 1, h - 1)
        else:
            _paint_fallback_panel(qp, QRectF(0, 0, w, h))
        title_color = ART_OVERLAY["text"] if has_art else C["text_primary"]
        sub_color = "#d8cba8" if has_art else C["text_secondary"]
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        qp.setFont(f)
        title_w = qp.fontMetrics().horizontalAdvance(self._title)
        _draw_shadow_text(qp, 14, h - 26, self._title, title_color, f,
                          shadow=ART_OVERLAY["shadow"] if has_art else "transparent")
        if self._subtitle:
            f2 = QFont()
            f2.setPointSize(9)
            _draw_shadow_text(qp, 14 + title_w + 18, h - 26, self._subtitle,
                              sub_color, f2,
                              shadow=ART_OVERLAY["shadow"] if has_art else "transparent")


def style_primary_button(button):
    """把按钮标记为全局主题的主色按钮（QSS: QPushButton[class="primary"]）。"""
    button.setProperty("class", "primary")
    style = button.style()
    style.unpolish(button)
    style.polish(button)
