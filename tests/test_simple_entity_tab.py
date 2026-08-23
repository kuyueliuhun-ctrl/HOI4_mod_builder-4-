"""B3 simple_entity_tab 通用实体页签测试。"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class SimpleEntityTabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_tab(self):
        from simple_entity_tab import SimpleEntityTab
        entities = [
            {"id": "A", "name": "Entity A", "cost": "10",
             "modifier": [("soft_attack", "5")]},
            {"id": "B", "name": "Entity B", "cost": "20", "modifier": []},
        ]
        fields = [
            {"key": "name", "label": "名称", "type": "text"},
            {"key": "cost", "label": "花费", "type": "int"},
            {"key": "modifier", "label": "修正", "type": "weight_table"},
            {"key": "allow", "label": "可用条件", "type": "trigger"},
        ]
        tab = SimpleEntityTab(entities, fields, "", "")
        return tab, entities

    def test_populate_and_values(self):
        tab, entities = self._make_tab()
        tab.show()
        self.app.processEvents()
        self.assertEqual(tab.sidebar.list.count(), 2)
        tab.sidebar.set_current("A")
        self.app.processEvents()
        vals = tab.values()
        self.assertEqual(vals["name"], "Entity A")
        self.assertEqual(vals["cost"], "10")
        self.assertEqual(vals["modifier"], [("soft_attack", "5")])
        tab.close()


if __name__ == "__main__":
    unittest.main()