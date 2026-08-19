"""快速本地化编辑右键菜单辅助（UI 层）

为组合框 / 标签等控件统一安装「✎ 快速编辑本地化」右键菜单，
弹出 QuickLocalisationEditDialog 直接编辑当前对象的本地化键。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu


def install_context_menu(widget, mod_path="", hoi4_path="",
                         key_provider=None, desc_key_provider=None,
                         parent=None):
    """给控件安装快速本地化编辑右键菜单。

    参数：
        widget            目标控件（QComboBox / QLabel 等）
        mod_path          当前 mod 根目录
        hoi4_path         当前游戏根目录
        key_provider      返回当前本地化键的可调用对象
        desc_key_provider 可选：返回描述本地化键（仅 BOP 等需要名称+描述）
        parent            快速对话框的父窗口
    """
    widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _on_context_menu(pos):
        key = key_provider() if key_provider else ""
        if not key:
            return
        menu = QMenu(widget)
        act = menu.addAction("✎ 快速编辑本地化（{}）…".format(key))
        desc_key = desc_key_provider() if desc_key_provider else ""
        if desc_key:
            act2 = menu.addAction("✎ 快速编辑本地化（名称 + 描述）…")
            act2.triggered.connect(
                lambda _=False: _open_dialog(key, desc_key))
        act.triggered.connect(lambda _=False: _open_dialog(key, None))
        menu.exec(widget.mapToGlobal(pos))

    def _open_dialog(key, desc_key):
        from quick_localisation_edit import QuickLocalisationEditDialog
        dlg = QuickLocalisationEditDialog(
            key=key,
            mod_path=mod_path,
            hoi4_path=hoi4_path,
            desc_key=desc_key or "",
            parent=parent or widget)
        dlg.show()

    widget.customContextMenuRequested.connect(_on_context_menu)
    return _on_context_menu


def install_combo_context_menu(combo, mod_path="", hoi4_path="",
                               key_provider=None, parent=None):
    """组合框的便捷封装：默认用当前项 data/text 作为键。"""
    if key_provider is None:
        key_provider = lambda: (combo.currentData()
                                if combo.currentData() not in (None, "")
                                else combo.currentText())
    return install_context_menu(combo, mod_path=mod_path, hoi4_path=hoi4_path,
                                key_provider=key_provider, parent=parent)
