"""B3/P38 装备组编辑器测试。"""

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


class EquipmentGroupsEditorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_equipment_groups2
        from equipment_groups_editor_dialog import EquipmentGroupsEditorDialog
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_eqgrp_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "equipment_groups"), exist_ok=True)
        path = os.path.join(mod, "common", "equipment_groups", "tank.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("tank_group = {\n"
                    "\tcategory = vehicle\n"
                    "\tpriority = 5\n"
                    "}\n")
        groups = load_equipment_groups2(mod, "")
        self.assertIn("tank_group", groups)
        dlg = EquipmentGroupsEditorDialog(groups, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()