"""游戏定义原始块编辑器测试（B2/B3，RawBlockEditor）。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class DefinesEditorDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _setup(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_test_defines_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        path = os.path.join(mod, *"common/defines/00_test.lua".split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("""NDefines = {
	NGame = {
		START_DATE = "1936.1.1"
	}
}
""")
        return mod, path

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_defines
        from defines_editor_dialog import DefinesEditorDialog
        mod, _path = self._setup()
        items = load_defines(mod, "")
        self.assertTrue(len(items) >= 1, items)
        dlg = DefinesEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertGreaterEqual(dlg.sidebar.list.count(), 1)
        dlg.close()

    def test_save_body(self):
        from ai_loader import _AI_CACHE, load_defines
        from defines_editor_dialog import DefinesEditorDialog
        from PyQt6.QtWidgets import QMessageBox
        mod, path = self._setup()
        dlg = DefinesEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        dlg.editor.setPlainText("\tnew_value = 1\n")
        with mock.patch.object(QMessageBox, "information",
                               return_value=QMessageBox.StandardButton.Ok):
            dlg._on_save()
        self.app.processEvents()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("new_value = 1", content)
        self.assertIn("= {", content)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
