"""地形专用编辑器测试（B3 嵌套实体 + 侧栏 CRUD）。"""

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


class TerrainEditorDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _setup(self):
        from ai_loader import _AI_CACHE
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_test_terrain_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        path = os.path.join(mod, *"common/terrain/00_terrain.txt".split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("""categories = {
	forest = {
		movement_cost = 1.0
		color = { 89 199 85 }
	}
}
""")
        return mod, path

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_terrain
        from terrain_editor_dialog import TerrainEditorDialog
        mod, _path = self._setup()
        items = load_terrain(mod, "")
        self.assertTrue(len(items) >= 1, items)
        dlg = TerrainEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertGreaterEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()

    def test_crud_create_rename_delete(self):
        from ai_loader import _AI_CACHE, load_terrain
        from terrain_editor_dialog import TerrainEditorDialog
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        mod, path = self._setup()
        dlg = TerrainEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        before = dlg.tab.sidebar.list.count()
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("NEW_ENT", True)), \
             mock.patch.object(QMessageBox, "information",
                               return_value=QMessageBox.StandardButton.Ok):
            dlg._on_create()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), before + 1)
        with open(path, "r", encoding="utf-8") as f:
            self.assertIn("NEW_ENT", f.read())
        dlg.tab.sidebar.set_current("NEW_ENT")
        self.app.processEvents()
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("RENAMED", True)), \
             mock.patch.object(QMessageBox, "information",
                               return_value=QMessageBox.StandardButton.Ok):
            dlg._on_rename()
        self.app.processEvents()
        with open(path, "r", encoding="utf-8") as f:
            self.assertIn("RENAMED", f.read())
        with mock.patch.object(QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes), \
             mock.patch.object(QMessageBox, "information",
                               return_value=QMessageBox.StandardButton.Ok):
            dlg._on_delete()
        self.app.processEvents()
        with open(path, "r", encoding="utf-8") as f:
            self.assertNotIn("RENAMED", f.read())
        dlg.close()


if __name__ == "__main__":
    unittest.main()
