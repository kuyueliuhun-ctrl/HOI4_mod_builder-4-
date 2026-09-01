"""子 mod 模式控制器（阶段C）：激活/退出/恢复/徽标/确认钩子。

以 Mixin 形式并入 MyWindow（与 MainWindowDocksMixin 同模式）；
settings.json 写入沿用主窗口登记过的豁免（程序配置，非 mod 内容）。

对外入口（工具菜单）：
  - on_submod_wizard：三步向导 → activate_cb=_activate_submod_stack
  - on_submod_exit：恢复传统两层语义
"""
from __future__ import annotations

import json
import os

from PyQt6.QtWidgets import QLabel, QMessageBox


class SubmodModeMixin:
    """子 mod 模式生命周期管理（依赖 self.settings / workbench_dock /
    _refresh_tree / _sync_loc_manager / statusBar，均由 MyWindow 提供）。"""

    # ---------- 菜单入口 ----------

    def on_submod_wizard(self):
        """工具菜单：子 Mod 制作向导（选播放集 → 勾底层 mod → 生成激活）。"""
        from submod_wizard import SubmodWizard
        from playset_loader import hoi4_user_dir
        user_dir = hoi4_user_dir(self.settings)
        if not user_dir:
            QMessageBox.information(
                self, "子 Mod 制作",
                "未找到 HOI4 用户文档目录。\n"
                "请确认「.mod 文件目录」指向 …/Hearts of Iron IV/mod，"
                "或在 settings.json 配置 hoi4_user_path。")
            return
        SubmodWizard(self, settings=self.settings, user_dir=user_dir,
                     activate_cb=self._activate_submod_stack).show()

    def on_submod_exit(self):
        """退出子 mod 模式：恢复传统两层语义与原 mod 界面。"""
        from mod_stack import clear_active_stack, set_copy_up_confirm
        clear_active_stack()
        set_copy_up_confirm(None)
        self.settings["submod_active"] = False
        self._persist_settings()
        self._register_copy_up_confirm(False)
        self.workbench_dock.set_mod_path(self.settings.get("mod_path", ""))
        self._refresh_tree()
        self._sync_loc_manager()
        self._set_submod_badge(None)
        self.statusBar().showMessage("已退出子mod模式", 4000)

    # ---------- 生命周期 ----------

    def _activate_submod_stack(self, submod_path, submod_name, base_paths):
        """激活子 mod 模式：层栈 + settings 持久化 + 界面刷新 + 徽标。"""
        from mod_stack import from_paths, set_active_stack
        stack = from_paths(sub_mod=submod_path, mod_paths=base_paths,
                           vanilla=self.settings.get("HOI4_path", ""),
                           submod_name=submod_name)
        if not stack.layers or not stack.submod_path:
            QMessageBox.critical(self, "子 Mod 模式", "子 mod 目录无效")
            return
        set_active_stack(stack)
        self.settings["submod_active"] = True
        self.settings["submod_path"] = submod_path
        self.settings["submod_name"] = submod_name
        self.settings["submod_bases"] = list(base_paths)
        self._persist_settings()
        self._register_copy_up_confirm(True)
        if self.workbench_dock is not None:
            self.workbench_dock.set_mod_path(stack.submod_path)
        self._refresh_tree()
        self._sync_loc_manager()
        self._set_submod_badge(stack)
        self.statusBar().showMessage(
            "子mod模式已激活：新建/保存的文件将写入子mod目录", 6000)

    def _restore_submod_if_active(self):
        """启动时恢复子 mod 模式（settings.submod_active 且目录有效）。"""
        if not self.settings.get("submod_active"):
            return
        submod_path = self.settings.get("submod_path", "")
        if not submod_path or not os.path.isdir(submod_path):
            return
        name = self.settings.get("submod_name", "") or \
            os.path.basename(os.path.normpath(submod_path))
        self._activate_submod_stack(
            submod_path, name, self.settings.get("submod_bases", []) or [])

    # ---------- UI 钩子 ----------

    def _register_copy_up_confirm(self, enabled):
        """copy_up 确认钩子：子 mod 模式下低层文件复制前弹窗确认。"""
        from mod_stack import set_copy_up_confirm
        if not enabled:
            set_copy_up_confirm(None)
            return

        def _confirm(rel_path, src, target):
            ret = QMessageBox.question(
                self, "复制到子mod",
                "该文件来自底层 mod / 原版。\n"
                "操作将在子mod中创建覆盖副本：\n%s\n\n是否继续？" % target,
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            return ret == QMessageBox.StandardButton.Yes

        set_copy_up_confirm(_confirm)

    def _set_submod_badge(self, stack):
        """状态栏常驻徽标：子mod模式激活信息（None = 清除）。"""
        if self._submod_badge is None:
            self._submod_badge = QLabel("")
            self.statusBar().addPermanentWidget(self._submod_badge)
        if stack is None:
            self._submod_badge.setText("")
            return
        bases = [l.name for l in stack.layers[1:] if l.kind == "mod"]
        has_vanilla = any(l.kind == "vanilla" for l in stack.layers[1:])
        self._submod_badge.setText("🧩 子mod：%s ← %s%s" % (
            stack.layers[0].name,
            " + ".join(bases) if bases else "（无底层 mod）",
            " + 原版" if has_vanilla else ""))
        self._submod_badge.setToolTip(
            "子mod模式：读取覆盖整个播放集；新建/保存的文件写入子mod目录")

    def _persist_settings(self):
        """持久化 settings.json（主窗口统一出口，写入纪律已登记豁免）。"""
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
