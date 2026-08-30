"""MIO 编辑器游戏美术主题层。

识别并复用游戏自带的两张 MIO 主视觉素材（mod 优先于游戏目录）：
- mio_details_background*.dds（945x660，GFX_MIO_details_background[_tank/_plane/_ship/_materiel]）
  游戏内 MIO 详情页的大幅插画背景（工厂/坦克/飞机/军舰主题的暗色照片级插画）。
- mio_entry_bg.dds（1040x100，GFX_mio_entry_bg）
  游戏内 MIO 列表条目的横幅底板（左侧深色徽章区 + 金属渐变条 + 黄铜描边）。

调色板取自素材实测主色（quantize 统计），供 QSS 与画布配色复用。
仅 UI 层：不读 mod 定义、不写任何文件；DDS 解码失败时全部回退到纯色绘制。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

# 游戏素材相对目录（mio_loader 同款相对根：mod 或游戏根目录）
ART_DIR_REL = "gfx/interface/military_industrial_organization"

# 素材名：两张主视觉图 + 方针槽按钮
ART_ENTRY_BG = "mio_entry_bg.dds"
ART_DETAILS_PREFIX = "mio_details_background"
ART_POLICY_SLOT = "MIO_policy_slot_button.dds"

# 实测主色（详情插画 / 条目横幅）
PALETTE = {
    "bg": "#161411",        # 详情插画最暗底色
    "panel": "#1d1b17",     # 面板底
    "panel2": "#23211e",    # 面板浅一档
    "line": "#514936",      # 横幅黄铜描边
    "gold": "#d4b06a",      # 强调金
    "gold_dim": "#7a6842",  # 连线暗金
    "metal": "#6d6c63",     # 金属灰
    "text": "#e8dcc0",      # 羊皮纸主文字
    "text_dim": "#b5a98a",  # 次级文字
    "select": "#3a3325",    # 选中底色
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


def build_qss():
    """MIO 编辑器同款游戏风 QSS（暗底 + 黄铜描边 + 羊皮纸文字）。"""
    p = PALETTE
    return """
QWidget#mioPanel {
    background: %(panel)s;
    border: 1px solid %(line)s;
    border-radius: 2px;
}
QLabel#mioPanelTitle {
    color: %(gold)s;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel {
    color: %(text)s;
    background: transparent;
}
QLineEdit, QPlainTextEdit {
    background: %(bg)s;
    color: %(text)s;
    border: 1px solid %(metal)s;
    selection-background-color: %(select)s;
}
QLineEdit:focus, QPlainTextEdit:focus {
    border: 1px solid %(gold)s;
}
QPushButton {
    background: %(panel2)s;
    color: %(text)s;
    border: 1px solid %(line)s;
    padding: 4px 10px;
}
QPushButton:hover {
    background: %(select)s;
    border: 1px solid %(gold)s;
}
QPushButton:pressed {
    background: %(bg)s;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: %(panel)s;
    width: 10px;
    height: 10px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: %(line)s;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}
""" % p


SIDEBAR_QSS = """
QListWidget {
    background: %(bg)s;
    border: 1px solid %(line)s;
}
QListWidget::item {
    color: %(text)s;
    padding: 6px 4px;
    border-bottom: 1px solid %(panel2)s;
}
QListWidget::item:selected {
    background: %(select)s;
    color: #f0e6c8;
    border-left: 3px solid %(gold)s;
}
QLineEdit {
    background: %(panel2)s;
}
""" % PALETTE


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


def _paint_fallback_panel(qp, rect):
    """无素材时的纯色底板：暗底 + 黄铜描边 + 微渐变。"""
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    p = PALETTE
    grad.setColorAt(0.0, QColor(p["panel2"]))
    grad.setColorAt(1.0, QColor(p["panel"]))
    qp.fillRect(rect, grad)
    qp.setPen(QPen(QColor(p["line"]), 1))
    qp.drawRect(rect.adjusted(0, 0, -1, -1))


def _draw_shadow_text(qp, x, y, text, color, font, shadow="#000000"):
    qp.setFont(font)
    qp.setPen(QColor(shadow))
    qp.drawText(x + 1, y + 1, text)
    qp.setPen(QColor(color))
    qp.drawText(x, y, text)


class BannerWidget(QWidget):
    """游戏条目横幅风格标题栏（mio_entry_bg 底板 + 图标位 + 标题 + 动作按钮）。"""

    HEIGHT = 68

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self._mod_path = mod_path or ""
        self._hoi4_path = hoi4_path or ""
        self._art = load_art_pixmap(ART_ENTRY_BG, self._mod_path,
                                    self._hoi4_path)
        self.setFixedHeight(self.HEIGHT)
        p = PALETTE
        self.icon_label = QLabel("🏭")
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel("—")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color:%s; background:transparent;" % p["text"])
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        row.addWidget(self.icon_label)
        row.addWidget(self.title_label, 1)

    def set_title(self, text):
        self.title_label.setText(text or "—")

    def paintEvent(self, event):
        qp = QPainter(self)
        rect = QRectF(self.rect())
        if not self._art.isNull():
            qp.drawPixmap(self.rect(), self._art,
                          self._art.rect())
        else:
            _paint_fallback_panel(qp, rect)


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
        p = PALETTE
        if self._art.isNull():
            _paint_fallback_panel(qp, QRectF(0, 0, w, h))
        else:
            scaled = self._art.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            sx = (scaled.width() - w) // 2
            sy = max(0, (scaled.height() - h) // 3)
            qp.fillRect(0, 0, w, h, QColor(PALETTE["bg"]))
            qp.drawPixmap(0, 0, scaled, sx, sy, w, h)
        # 底部渐晕，保证文字可读
        grad = QLinearGradient(0, h * 0.35, 0, h)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 170))
        qp.fillRect(0, int(h * 0.35), w, int(h * 0.65), grad)
        qp.setPen(QPen(QColor(p["line"]), 1))
        qp.drawRect(0, 0, w - 1, h - 1)
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        _draw_shadow_text(qp, 14, h - 26, self._title, p["text"], f)
        f2 = QFont()
        f2.setPointSize(9)
        qp.setFont(f2)
        qp.setPen(QColor(p["text_dim"]))
        if self._subtitle:
            qp.drawText(14 + qp.fontMetrics().horizontalAdvance(self._title) + 18,
                        h - 26, self._subtitle)


def style_sidebar(sidebar):
    """把 EntityListSidebar 内部控件调成游戏暗色风格。"""
    sidebar.setStyleSheet(SIDEBAR_QSS)
    p = PALETTE
    for lab in sidebar.findChildren(QLabel):
        lab.setStyleSheet(
            "color:%s; font-weight:bold; background:transparent;" % p["gold"])
    for btn in sidebar.findChildren(QPushButton):
        btn.setStyleSheet("")


def apply_policy_slot_style(button):
    """方针槽按钮：模仿 MIO_policy_slot_button 的金属底 + 双侧铆钉描边。"""
    p = PALETTE
    button.setStyleSheet(
        "QPushButton { background:%(panel2)s; color:%(text)s;"
        " border:1px solid %(line)s; border-left:4px solid %(gold)s;"
        " border-right:4px solid %(gold)s; padding:8px 18px; }"
        "QPushButton:hover { background:%(select)s; }" % p)
