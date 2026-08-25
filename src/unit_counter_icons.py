"""兵牌图标（标牌库 → QPixmap/QIcon）UI 层助手（P2：兵牌图标接标牌库）。

纯算法层 `unit_counter_library.find_counter_entry` 负责「兵种类型 → 标牌库条目」；
本模块只做 Qt 像素加载/缩放/图标转换，供 OOB 地图兵牌与师编制槽位使用。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

from unit_counter_library import default_library_dir, find_counter_entry, _get_library


def counter_entry_path(unit_type):
    """兵种类型 → 标牌 PNG 绝对路径（找不到返回 None）。"""
    lib = _get_library()
    entry = find_counter_entry(unit_type, lib=lib)
    if not entry:
        return None
    path = os.path.join(default_library_dir(),
                        entry["file"].replace("/", os.sep))
    return path if os.path.isfile(path) else None


def counter_pixmap(unit_type, width=0, height=0):
    """兵种类型 → QPixmap（可选缩放；找不到/解码失败返回 None）。"""
    path = counter_entry_path(unit_type)
    if not path:
        return None
    pm = QPixmap(path)
    if pm.isNull():
        return None
    if width > 0 and height > 0:
        pm = pm.scaled(width, height,
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return pm


def counter_qicon(unit_type):
    """兵种类型 → QIcon（找不到返回 None）。"""
    path = counter_entry_path(unit_type)
    if not path:
        return None
    pm = QPixmap(path)
    if pm.isNull():
        return None
    return QIcon(pm)
