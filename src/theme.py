"""主题：设计令牌 + 全局 QSS（对齐 Scenario Forge 的亮色专业工具风格）

设计令牌（与 Scenario Forge css/style.css 对齐）：
  背景 #e7edf2 淡蓝灰 · 面板白 · 主色深蓝 #1f4f7e · 地图强调土橙 #b05b2d
  语义色柔和版（成功 #2f7d57 / 警告 #b7791f / 危险 #b94d3f）
  卡片圆角 16px · 按钮 10px · 输入框 8px · 三级文字色阶

用法：
    from theme import apply_theme
    apply_theme(app)          # app 创建后、窗口显示前调用
    from theme import COLORS  # 代码内取色（对话框级别色等）
"""

from __future__ import annotations

# ---------------------------------------------------------------- 设计令牌

COLORS = {
    "bg_app": "#e7edf2",                 # 应用背景（淡蓝灰）
    "bg_surface": "#ffffff",             # 面板/浮层
    "bg_input": "#f3f6f8",               # 输入框底色
    "bg_surface_subtle": "#f4f7fa",      # 工具栏/表头/标签栏底色
    "text_primary": "#162333",
    "text_secondary": "#5d6b7a",
    "text_tertiary": "#64717e",
    "text_heading": "#425062",
    "text_disabled": "#95a0ab",
    "accent": "#1f4f7e",                 # 主色（深蓝）
    "accent_hover": "#17456f",
    "map_accent": "#b05b2d",             # 地图强调色（土橙）
    "success": "#2f7d57",
    "warning": "#b7791f",
    "danger": "#b94d3f",
    "border_subtle": "rgba(22, 35, 51, 0.10)",
    "border_strong": "rgba(22, 35, 51, 0.18)",
    "hover_fill": "rgba(22, 35, 51, 0.06)",
    "accent_soft": "rgba(31, 79, 126, 0.12)",
    "map_accent_soft": "rgba(176, 91, 45, 0.12)",
}

RADIUS = {"card": 16, "btn": 10, "input": 8, "item": 6}
FONT_STACK = '"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif'


def build_qss() -> str:
    c = COLORS
    return """
/* ===== 全局 ===== */
QMainWindow, QDialog {
    background-color: %(bg_app)s;
}
QWidget {
    color: %(text_primary)s;
    font-size: 13px;
}

/* ===== 工具栏 / 状态栏 ===== */
QToolBar {
    background: %(bg_surface_subtle)s;
    border: none;
    border-bottom: 1px solid %(border_subtle)s;
    padding: 5px 10px;
    spacing: 4px;
}
QToolBar QToolButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 5px 10px;
    color: %(text_primary)s;
}
QToolBar QToolButton:hover { background: %(hover_fill)s; }
QToolBar QToolButton:pressed { background: %(accent_soft)s; }
QToolBar QToolButton:checked {
    background: %(accent_soft)s;
    color: %(accent)s;
}
QStatusBar {
    background: %(bg_surface_subtle)s;
    color: %(text_secondary)s;
    border-top: 1px solid %(border_subtle)s;
}

/* ===== 按钮 ===== */
QPushButton {
    background: %(bg_surface)s;
    color: %(text_primary)s;
    border: 1px solid %(border_strong)s;
    border-radius: 10px;
    padding: 6px 16px;
}
QPushButton:hover {
    background: %(bg_surface_subtle)s;
    border-color: rgba(22, 35, 51, 0.28);
}
QPushButton:pressed { background: %(bg_app)s; }
QPushButton:checked {
    background: %(accent_soft)s;
    border-color: rgba(31, 79, 126, 0.35);
    color: %(accent)s;
}
QPushButton:disabled {
    color: %(text_disabled)s;
    background: #f0f3f6;
    border-color: rgba(22, 35, 51, 0.08);
}
QPushButton[class="primary"] {
    background: %(accent)s;
    color: #ffffff;
    border: 1px solid %(accent)s;
}
QPushButton[class="primary"]:hover { background: %(accent_hover)s; }
QPushButton[class="primary"]:disabled {
    background: #8fa3b8;
    border-color: #8fa3b8;
    color: rgba(255, 255, 255, 0.85);
}
QPushButton[class="danger"] {
    background: %(bg_surface)s;
    color: %(danger)s;
    border: 1px solid rgba(185, 77, 63, 0.4);
}
QPushButton[class="danger"]:hover { background: rgba(185, 77, 63, 0.08); }
QPushButton[class="success"] {
    background: %(bg_surface)s;
    color: %(success)s;
    border: 1px solid rgba(47, 125, 87, 0.4);
}
QPushButton[class="success"]:hover { background: rgba(47, 125, 87, 0.08); }

/* ===== 输入控件 ===== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
QPlainTextEdit, QTextEdit, QDateTimeEdit, QDateEdit {
    background: %(bg_surface)s;
    color: %(text_primary)s;
    border: 1px solid rgba(22, 35, 51, 0.15);
    border-radius: 8px;
    padding: 5px 9px;
    selection-background-color: rgba(31, 79, 126, 0.25);
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border-color: %(accent)s;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background: #f0f3f6;
    color: %(text_disabled)s;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: %(bg_surface)s;
    border: 1px solid rgba(22, 35, 51, 0.15);
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: %(accent_soft)s;
    selection-color: %(text_primary)s;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: transparent; border: none; width: 18px;
}

/* ===== 菜单 ===== */
QMenuBar {
    background: %(bg_surface_subtle)s;
    color: %(text_primary)s;
    border-bottom: 1px solid %(border_subtle)s;
    padding: 2px 6px;
}
QMenuBar::item { padding: 5px 10px; border-radius: 6px; background: transparent; }
QMenuBar::item:selected { background: %(accent_soft)s; color: %(accent)s; }
QMenu {
    background: %(bg_surface)s;
    border: 1px solid rgba(22, 35, 51, 0.12);
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 6px 28px 6px 12px;
    border-radius: 6px;
    color: %(text_primary)s;
}
QMenu::item:selected { background: %(accent_soft)s; color: %(accent)s; }
QMenu::item:disabled { color: %(text_disabled)s; }
QMenu::separator {
    height: 1px;
    background: %(border_subtle)s;
    margin: 5px 8px;
}

/* ===== 表格 ===== */
QTableWidget, QTableView {
    background: %(bg_surface)s;
    alternate-background-color: #f7f9fb;
    border: 1px solid %(border_subtle)s;
    border-radius: 10px;
    gridline-color: rgba(22, 35, 51, 0.06);
    selection-background-color: %(accent_soft)s;
    selection-color: %(text_primary)s;
}
QHeaderView::section {
    background: %(bg_surface_subtle)s;
    color: %(text_secondary)s;
    border: none;
    border-bottom: 1px solid %(border_subtle)s;
    border-right: 1px solid rgba(22, 35, 51, 0.05);
    padding: 7px 9px;
}
QTableCornerButton::section {
    background: %(bg_surface_subtle)s;
    border: none;
}

/* ===== 树 / 列表 ===== */
QTreeView, QTreeWidget, QListWidget {
    background: %(bg_surface)s;
    border: 1px solid %(border_subtle)s;
    border-radius: 10px;
    outline: none;
}
QTreeView::item, QTreeWidget::item, QListWidget::item {
    padding: 4px 6px;
    border-radius: 6px;
}
QTreeView::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {
    background: %(hover_fill)s;
}
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
    background: %(accent_soft)s;
    color: %(text_primary)s;
}
QTreeView::branch { background: transparent; }

/* ===== 选项卡 ===== */
QTabWidget::pane {
    border: 1px solid %(border_subtle)s;
    border-radius: 10px;
    background: %(bg_surface)s;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: %(text_secondary)s;
    padding: 7px 18px;
    border-radius: 8px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: %(bg_surface)s;
    color: %(accent)s;
    border: 1px solid rgba(31, 79, 126, 0.25);
}
QTabBar::tab:hover:!selected { background: %(hover_fill)s; }

/* ===== 停靠面板 ===== */
QDockWidget {
    color: %(text_primary)s;
    border: 1px solid %(border_subtle)s;
    border-radius: 12px;
    background: %(bg_surface)s;
}
QDockWidget::title {
    background: %(bg_surface_subtle)s;
    padding: 7px 12px;
    border-top-left-radius: 11px;
    border-top-right-radius: 11px;
}
QDockWidget QWidget { background: %(bg_surface)s; }

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    background: transparent; width: 12px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(22, 35, 51, 0.22);
    border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: rgba(22, 35, 51, 0.35); }
QScrollBar:horizontal {
    background: transparent; height: 12px; margin: 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(22, 35, 51, 0.22);
    border-radius: 5px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: rgba(22, 35, 51, 0.35); }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ===== 勾选 / 单选 ===== */
QCheckBox, QRadioButton { color: %(text_primary)s; spacing: 7px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px;
}
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    border: 1.5px solid rgba(22, 35, 51, 0.32);
    border-radius: 4px;
    background: %(bg_surface)s;
}
QCheckBox::indicator:checked {
    border: 1.5px solid %(accent)s;
    border-radius: 4px;
    background: %(accent)s;
}
QCheckBox::indicator:disabled { border-color: rgba(22, 35, 51, 0.12); }
QRadioButton::indicator:unchecked {
    border-radius: 8px;
}
QRadioButton::indicator:checked {
    border: 5px solid %(accent)s;
    border-radius: 8px;
    background: %(bg_surface)s;
}

/* ===== 分组框 / 分割条 ===== */
QGroupBox {
    border: 1px solid %(border_subtle)s;
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 10px;
    color: %(text_secondary)s;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: %(text_heading)s;
}
QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background: %(accent_soft)s; }

/* ===== 提示 / 其他 ===== */
QToolTip {
    background: %(text_primary)s;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
}
QMessageBox QLabel { color: %(text_primary)s; }
QProgressBar {
    background: #eef2f6;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: %(text_secondary)s;
    height: 14px;
}
QProgressBar::chunk {
    background: %(accent)s;
    border-radius: 6px;
}

/* ===== 语义化属性类（代码里 setProperty("class", ...) 使用） ===== */
QFrame[class="card"] {
    background: %(bg_surface)s;
    border: 1px solid rgba(22, 35, 51, 0.08);
    border-radius: 16px;
}
QLabel[class="title"] {
    font-size: 17px;
    font-weight: 600;
    color: %(text_primary)s;
}
QLabel[class="subtitle"] { color: %(text_secondary)s; }
QLabel[class="map_accent"] {
    background: %(map_accent)s;
    color: #ffffff;
    border-radius: 6px;
    padding: 3px 10px;
}
QLabel[class="sev_error"] {
    background: %(danger)s;
    color: #ffffff;
    border-radius: 6px;
    padding: 2px 10px;
}
QLabel[class="sev_warning"] {
    background: %(warning)s;
    color: #ffffff;
    border-radius: 6px;
    padding: 2px 10px;
}
QLabel[class="sev_info"] {
    background: %(accent)s;
    color: #ffffff;
    border-radius: 6px;
    padding: 2px 10px;
}
""" % c


QSS = build_qss()


def apply_theme(app):
    """应用全局主题（app 创建后、窗口显示前调用；失败静默回退默认样式）。"""
    try:
        app.setStyleSheet(QSS)
    except Exception:
        pass
