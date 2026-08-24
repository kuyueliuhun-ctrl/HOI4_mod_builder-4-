"""B3/P38 国家别名编辑器测试。"""

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


class CountryTagAliasesEditorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_and_editor(self):
        from ai_loader import _AI_CACHE, load_country_tag_aliases
        from country_tag_aliases_editor_dialog import (
            CountryTagAliasesEditorDialog)
        _AI_CACHE.clear()
        mod = _mkdtemp("dsh_ctag_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "country_tag_aliases"),
                    exist_ok=True)
        path = os.path.join(mod, "common", "country_tag_aliases", "all.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("GER = {\n"
                    "\talias = DEU\n"
                    "\tcountry = \"Germany\"\n"
                    "}\n")
        aliases = load_country_tag_aliases(mod, "")
        self.assertIn("GER", aliases)
        dlg = CountryTagAliasesEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.tab.sidebar.list.count(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()