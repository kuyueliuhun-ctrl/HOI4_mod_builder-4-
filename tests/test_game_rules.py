"""B3/P33 游戏规则编辑器测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class GameRulesEditorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_game_rules
        from game_rules_editor_dialog import GameRulesEditorDialog
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_grules_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "game_rules"), exist_ok=True)
        path = os.path.join(mod, "common", "game_rules", "all.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("historical_focus = {\n"
                    "\tname = \"historical_focus\"\n"
                    "\tdefault = yes\n"
                    "}\n")
        rules = load_game_rules(mod, "")
        self.assertIn("historical_focus", rules)
        dlg = GameRulesEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()