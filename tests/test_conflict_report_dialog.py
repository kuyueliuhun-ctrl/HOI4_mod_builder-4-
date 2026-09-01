"""冲突报告对话框契约（conflict_report_dialog，阶段B UI）。

offscreen 环境覆盖：
- 播放集下拉：dlc_load 恒在列首 + sqlite 播放集标签
- 扫描端到端（临时多 mod 播放集）：树分组结构 / 统计文案 / 导出按钮态
- 树叶节点携带 ConflictItem；双击跳转回调收到绝对路径
- HTML 渲染：转义、严重度行样式、无外部资源
- 未配置用户目录时的禁用态
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mk(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix="dsh_conflict_ui_" + prefix, dir=root)


def _put(root, rel, content, encoding="utf-8"):
    fp = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding=encoding) as f:
        f.write(content)
    return fp


class ConflictReportDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        """构造：用户目录（sqlite+dlc_load）+ 两个 mod（含冲突）。"""
        user = _mk("user")
        dirA, dirB = _mk("modA"), _mk("modB")
        _put(user, "dlc_load.json", json.dumps(
            {"enabled_mods": ["mod/a.mod", "mod/b.mod"]}))
        os.makedirs(os.path.join(user, "mod"), exist_ok=True)
        _put(user, "mod/a.mod", 'name="ModA"\npath="%s"\n'
             'supported_version="1.19.*"\n' % dirA.replace("\\", "/"))
        _put(user, "mod/b.mod", 'name="ModB"\npath="%s"\n'
             'supported_version="1.19.*"\n' % dirB.replace("\\", "/"))
        # 冲突素材：整文件覆盖 + 实体 id + 本地化
        _put(dirA, "common/x/shared.txt", "A")
        _put(dirB, "common/x/shared.txt", "B")
        _put(dirA, "common/national_focus/a.txt", "focus = {\n id = f1\n}\n")
        _put(dirB, "common/national_focus/b.txt", "focus = {\n id = f1\n}\n")
        _put(dirA, "localisation/simp_chinese/a_l_simp_chinese.yml",
             'l_simp_chinese:\n KEY_1:0 "甲"\n')
        _put(dirB, "localisation/simp_chinese/b_l_simp_chinese.yml",
             'l_simp_chinese:\n KEY_1:0 "乙"\n')
        return user, dirA, dirB

    def _open_dialog(self, settings):
        from conflict_report_dialog import ConflictReportDialog
        dlg = ConflictReportDialog(settings=settings)
        dlg.show()
        self.app.processEvents()
        self.addCleanup(dlg.close)
        return dlg

    def test_playset_combo_and_missing_user_dir(self):
        user, _a, _b = self._make_env()
        dlg = self._open_dialog({"mod_file_path":
                                 os.path.join(user, "mod")})
        # 环境只写 dlc_load.json（无 sqlite）→ 仅 dlc_load 一项
        self.assertEqual(dlg.playset_combo.count(), 1)
        self.assertEqual(dlg.playset_combo.currentData(), "__dlc_load__")

        # 未配置：按钮禁用且不崩溃
        dlg2 = self._open_dialog({})
        self.assertFalse(dlg2.btn_scan.isEnabled())

    def test_scan_end_to_end_and_tree(self):
        user, dirA, _b = self._make_env()
        dlg = self._open_dialog({
            "mod_file_path": os.path.join(user, "mod"),
            "HOI4_path": ""})
        dlg._on_scan()
        self.app.processEvents()
        self.assertIsNotNone(dlg.report)
        top = dlg.tree.topLevelItemCount()
        # 分组：error（实体 id）+ warning（文件遮蔽/本地化）= 2 组
        self.assertEqual(top, 2)
        # 统计：整文件覆盖 + 实体 + 本地化 至少各 1
        text = dlg.lbl_stats.text()
        self.assertIn("条冲突", text)
        self.assertTrue(dlg.btn_export_json.isEnabled())
        self.assertTrue(dlg.btn_export_html.isEnabled())

        # 叶节点携带 ConflictItem，双击回调收到 dirA 内绝对路径
        from PyQt6.QtCore import Qt
        from conflict_scan import ConflictItem
        opened = []
        dlg.open_file_cb = opened.append
        sev0 = dlg.tree.topLevelItem(0)
        kind0 = sev0.child(0)
        leaf = kind0.child(0)
        self.assertIsInstance(leaf.data(0, Qt.ItemDataRole.UserRole),
                              ConflictItem)
        dlg._on_item_open(leaf, 0)
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].startswith(dirA))

    def test_export_html_render(self):
        user, _a, _b = self._make_env()
        dlg = self._open_dialog({"mod_file_path": os.path.join(user, "mod")})
        dlg._on_scan()
        from conflict_report_dialog import _render_html
        html = _render_html(dlg.report)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("多 Mod 冲突报告", html)
        self.assertNotIn("<script", html.lower())

    def test_render_escapes_titles(self):
        from conflict_report_dialog import _render_html
        from conflict_scan import ConflictItem, ConflictReport
        rpt = ConflictReport(playset_name="<set&>")
        rpt.items.append(ConflictItem(
            severity="error", kind="file_shadow",
            title="<b>bad&</b>", victim="A<B", winner="C"))
        html = _render_html(rpt)
        self.assertNotIn("<b>bad&</b>", html)
        self.assertIn("&lt;b&gt;bad&amp;&lt;/b&gt;", html)


if __name__ == "__main__":
    unittest.main()
