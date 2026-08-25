"""学说（Doctrine）编辑器测试（数据层 + 对话框冒烟）。"""

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


GRAND_SAMPLE = """new_mobile_warfare = {
    folder = land
    name = GRAND_DOCTRINE_MOBILE_WARFARE
    icon = GFX_doctrine_mobile_warfare_medium
    xp_cost = 100
    xp_type = army
    tracks = { infantry combat_support armor operations }
    milestones = {
        {
            #Infantry
            org_loss_when_moving = -0.15
        }
        {
            #Artillery/Support
            planning_speed = 0.1
        }
        {
            #Armor
            additional_brigade_column_size = 1
        }
        {
            #Operations
            planning_speed = 0.2
        }
    }
}
"""

TRACKS_SAMPLE = """infantry = {
    name = DOCTRINE_TRACK_INFANTRY
    icon = "GFX_doctrine_milestone_infantry_land"
    mastery = {
        multiplier = 1.0
        categories = { category_all_infantry }
    }
}
combat_support = {
    name = DOCTRINE_TRACK_COMBAT_SUPPORT
    icon = "GFX_doctrine_milestone_artillery_land"
    mastery = {
        multiplier = 8.0
        categories = { category_line_artillery }
    }
}
"""

SUBDOC_SAMPLE = """mobile_infantry = {
    track = infantry
    name = SUBDOCTRINE_MOBILE_INFANTRY
    icon = GFX_doctrine_mobile_infantry_medium
    xp_cost = 100
    xp_type = army
    available = { always = yes }
    rewards = {
        combined_arms_planning = {
            category_all_infantry = { max_organisation = 10 }
        }
    }
}
"""


def _write(mod, rel, content):
    p = os.path.join(mod, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


class DoctrineLoaderTest(unittest.TestCase):
    def setUp(self):
        self.mod = _mkdtemp("dsh_doctrine_")
        self.addCleanup(shutil.rmtree, self.mod, ignore_errors=True)
        _write(self.mod, "common/doctrines/grand_doctrines/land_grand_doctrines.txt", GRAND_SAMPLE)
        _write(self.mod, "common/doctrines/tracks/land_doctrine_tracks.txt", TRACKS_SAMPLE)
        self.sd_path = _write(self.mod, "common/doctrines/subdoctrines/land/infantry_subdoctrines.txt", SUBDOC_SAMPLE)

    def test_parse(self):
        from doctrine_loader import (load_doctrine_tracks, load_grand_doctrines,
                                     load_subdoctrines)
        grand = load_grand_doctrines(self.mod, "")
        self.assertIn("new_mobile_warfare", grand)
        g = grand["new_mobile_warfare"]
        self.assertEqual(g["tracks"][:2], ["infantry", "combat_support"])
        self.assertEqual(len(g["milestones"]), 4)
        tracks = load_doctrine_tracks(self.mod, "")
        self.assertEqual(tracks["infantry"]["mastery"]["multiplier"], "1.0")
        self.assertEqual(tracks["infantry"]["mastery"]["categories"],
                         ["category_all_infantry"])
        subs = load_subdoctrines(self.mod, "")
        self.assertIn("mobile_infantry", subs)
        s = subs["mobile_infantry"]
        self.assertEqual(s["track"], "infantry")
        self.assertEqual(s["xp_cost"], "100")

    def test_subdoctrine_crud(self):
        from doctrine_loader import (delete_subdoctrine, insert_subdoctrine,
                                     replace_subdoctrine_child,
                                     replace_subdoctrine_fields)
        with open(self.sd_path, encoding="utf-8") as f:
            content = f.read()
        content = replace_subdoctrine_fields(content, "mobile_infantry",
                                             {"xp_cost": "150"})
        self.assertIn("xp_cost = 150", content)
        content = replace_subdoctrine_child(
            content, "mobile_infantry", "rewards",
            "rewards = {\n\t\tnew_reward = {\n\t\t\tdefense = 0.2\n\t\t}\n\t}")
        self.assertIn("new_reward", content)
        content = insert_subdoctrine(content, "new_sd", "infantry",
                                     after_id="mobile_infantry")
        self.assertIn("new_sd", content)
        content = delete_subdoctrine(content, "new_sd")
        self.assertNotIn("new_sd", content)


class DoctrineEditorDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog(self):
        from doctrine_editor_dialog import DoctrineEditorDialog
        mod = _mkdtemp("dsh_doctrinedlg_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        _write(mod, "common/doctrines/grand_doctrines/land_grand_doctrines.txt", GRAND_SAMPLE)
        _write(mod, "common/doctrines/tracks/land_doctrine_tracks.txt", TRACKS_SAMPLE)
        _write(mod, "common/doctrines/subdoctrines/land/infantry_subdoctrines.txt", SUBDOC_SAMPLE)
        dlg = DoctrineEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertGreaterEqual(dlg.sidebar.list.count(), 1)
        # 4 个 track 卡片
        self.assertGreaterEqual(dlg.tracks_row.count(), 2)
        # 点击 infantry 面板
        dlg._on_track_clicked("infantry")
        self.app.processEvents()
        self.assertGreaterEqual(dlg.sd_list.count(), 1)
        if dlg.sd_list.count():
            dlg.sd_list.setCurrentRow(0)
            self.app.processEvents()
            self.assertNotEqual(dlg.sd_title.text(), "")
        dlg.close()


if __name__ == "__main__":
    unittest.main()
