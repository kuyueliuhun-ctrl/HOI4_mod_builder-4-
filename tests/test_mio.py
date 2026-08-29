"""MIO 编辑器测试（数据层 + 对话框冒烟）。"""

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


MIO_SAMPLE = """generic_tank_organization = {
	icon = GFX_idea_generic_tank_manufacturer_1
	initial_trait = {
		name = generic_mio_initial_trait_standardized_production
		equipment_bonus = {
			build_cost_ic = -0.05
		}
	}
	trait = {
		token = trait_a
		name = trait_a
		icon = GFX_trait_a
		position = { x = 1 y = 0 }
		equipment_bonus = {
			reliability = 0.05
		}
	}
	trait = {
		token = trait_b
		name = trait_b
		position = { x = 0 y = 2 }
		relative_position_id = trait_a
		any_parent = { trait_a }
	}
}
"""

POLICY_SAMPLE = """mio_policy_test = {
	icon = GFX_mio_policy_test
	allowed = { always = yes }
	available = { has_mio_size > 5 }
	equipment_bonus = {
		same_as_mio = { maximum_speed = 0.05 }
	}
}
"""


class MioLoaderTest(unittest.TestCase):
    def setUp(self):
        self.mod = _mkdtemp("dsh_mio_")
        self.addCleanup(shutil.rmtree, self.mod, ignore_errors=True)
        p = os.path.join(self.mod, "common", "military_industrial_organization",
                         "organizations", "00_test.txt")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(MIO_SAMPLE)
        pp = os.path.join(self.mod, "common", "military_industrial_organization",
                          "policies", "_test.txt")
        os.makedirs(os.path.dirname(pp), exist_ok=True)
        with open(pp, "w", encoding="utf-8") as f:
            f.write(POLICY_SAMPLE)

    def test_parse_mio(self):
        from mio_loader import load_mios
        mios = load_mios(self.mod, "")
        self.assertIn("generic_tank_organization", mios)
        m = mios["generic_tank_organization"]
        self.assertEqual(m["icon"], "GFX_idea_generic_tank_manufacturer_1")
        self.assertEqual(m["initial_trait"]["name"],
                         "generic_mio_initial_trait_standardized_production")
        self.assertEqual(len(m["traits"]), 2)
        by = {t["token"]: t for t in m["traits"]}
        self.assertEqual(by["trait_a"]["parents"], [])
        self.assertEqual(by["trait_b"]["parents"], ["trait_a"])
        self.assertEqual(by["trait_b"]["relative_position_id"], "trait_a")
        self.assertEqual(by["trait_a"]["x"], 1)
        self.assertEqual(by["trait_a"]["y"], 0)

    def test_trait_crud(self):
        from mio_loader import (
            delete_trait, insert_trait, load_mios,
            replace_mio_fields, replace_trait_block, trait_to_pdx,
        )
        mios = load_mios(self.mod, "")
        p = os.path.join(self.mod, "common", "military_industrial_organization",
                         "organizations", "00_test.txt")
        with open(p, encoding="utf-8") as f:
            content = f.read()
        content = replace_mio_fields(content, "generic_tank_organization",
                                     {"icon": "GFX_new"})
        content = insert_trait(content, "generic_tank_organization",
                               "trait_c", after_token="trait_b")
        self.assertIn("token = trait_c", content)
        new_block = trait_to_pdx("trait_c", "trait_c", "GFX_c", 2, 0)
        content = replace_trait_block(content, "generic_tank_organization",
                                      "trait_c", new_block)
        self.assertIn("icon = GFX_c", content)
        content = delete_trait(content, "generic_tank_organization", "trait_c")
        self.assertNotIn("trait_c", content)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        mios2 = load_mios(self.mod, "")
        self.assertEqual(mios2["generic_tank_organization"]["icon"], "GFX_new")

    def test_policy_crud(self):
        from mio_loader import load_mio_policies, policy_to_pdx, replace_policy_block
        policies = load_mio_policies(self.mod, "")
        self.assertIn("mio_policy_test", policies)
        p = os.path.join(self.mod, "common", "military_industrial_organization",
                         "policies", "_test.txt")
        with open(p, encoding="utf-8") as f:
            content = f.read()
        new_block = policy_to_pdx(
            "mio_policy_test", "GFX_new_policy",
            equipment_bonus="equipment_bonus = {\n\t\tsame_as_mio = { maximum_speed = 0.1 }\n\t}")
        content = replace_policy_block(content, "mio_policy_test", new_block)
        self.assertIn("icon = GFX_new_policy", content)
        self.assertIn("maximum_speed = 0.1", content)

    def test_app_routes_mio_editors(self):
        from app_routes import find_route
        orgs, org_route = find_route(
            r"D:\mod\common\military_industrial_organization\organizations\00_mio.txt")
        self.assertIsNotNone(org_route)
        self.assertEqual(org_route[2], "MIO 编辑器")
        pols, pol_route = find_route(
            r"D:\mod\common\military_industrial_organization\policies\_mio.txt")
        self.assertIsNotNone(pol_route)
        self.assertEqual(pol_route[2], "MIO 方针")

    def test_mio_rel_mod_file(self):
        from mio_loader import _rel
        game = _mkdtemp("dsh_miogame_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        mod_fp = os.path.join(
            self.mod, "common", "military_industrial_organization",
            "organizations", "00_test.txt")
        rel = _rel(mod_fp, game, self.mod)
        self.assertEqual(
            rel, "common/military_industrial_organization/organizations/00_test.txt")

    def test_mio_scan_mod_priority(self):
        from mio_loader import load_mios
        game = _mkdtemp("dsh_miogame_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        gp = os.path.join(
            game, "common", "military_industrial_organization",
            "organizations", "00_test.txt")
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        with open(gp, "w", encoding="utf-8") as f:
            f.write("generic_tank_organization = {\n\ticon = GFX_game\n}\n")
        mios = load_mios(self.mod, game)
        self.assertEqual(
            mios["generic_tank_organization"]["icon"],
            "GFX_idea_generic_tank_manufacturer_1")

    def test_trait_to_pdx_extra_blocks(self):
        from mio_loader import trait_to_pdx
        out = trait_to_pdx(
            "t", "t", "", 0, 0,
            extra_blocks=[
                "mutually_exclusive = { other_trait }",
                "limit_to_equipment_type = { armor }",
            ])
        self.assertIn("mutually_exclusive = { other_trait }", out)
        self.assertIn("limit_to_equipment_type = { armor }", out)

    def test_parse_trait_preserves_parent_and_extra(self):
        from mio_loader import _parse_trait
        raw = (
            "trait = {\n"
            "\t\ttoken = t\n"
            "\t\tname = t\n"
            "\t\tall_parents = { a b }\n"
            "\t\tlimit_to_equipment_type = { armor }\n"
            "\t\tmutually_exclusive = { x }\n"
            "\t}\n"
        )
        t = _parse_trait(raw)
        self.assertEqual(t["parents"], ["a", "b"])
        self.assertIn("all_parents", t["parent_blocks"])
        self.assertTrue(any("limit_to_equipment_type" in b for b in t["extra_blocks"]))

    def test_trait_roundtrip_preserves_bonus_and_extra(self):
        from mio_loader import _parse_trait, trait_to_pdx
        raw = (
            "trait = {\n"
            "\t\ttoken = t\n"
            "\t\tname = t\n"
            "\t\tproduction_bonus = {\n"
            "\t\t\tx = 1\n"
            "\t\t}\n"
            "\t\tmutually_exclusive = { other }\n"
            "\t}\n"
        )
        t = _parse_trait(raw)
        out = trait_to_pdx(
            t["token"], t["name"], t["icon"], t["x"], t["y"],
            t.get("relative_position_id", ""), t.get("parents", []),
            t.get("equipment_bonus", ""), t.get("production_bonus", ""),
            extra_blocks=list(t.get("extra_blocks", [])))
        parsed = _parse_trait(out)
        self.assertTrue(parsed["extra_blocks"])
        self.assertIn("x = 1", parsed["production_bonus"])
        self.assertIn("mutually_exclusive", parsed["extra_blocks"][0])


class MioEditorDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _setup(self):
        mod = _mkdtemp("dsh_miodlg_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        p = os.path.join(mod, "common", "military_industrial_organization",
                         "organizations", "00_test.txt")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(MIO_SAMPLE)
        return mod

    def test_dialog_and_tree_click(self):
        from mio_editor_dialog import MioEditorDialog
        mod = self._setup()
        dlg = MioEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertGreaterEqual(dlg.sidebar.list.count(), 1)
        self.assertIsNotNone(dlg._current_id)
        # 模拟点击树节点
        dlg.tree._on_node_clicked("trait_a")
        self.app.processEvents()
        self.assertEqual(dlg.token_edit.text(), "trait_a")
        dlg.close()

    def test_policy_dialog(self):
        from mio_policy_editor_dialog import MioPolicyEditorDialog
        mod = self._setup()
        pp = os.path.join(mod, "common", "military_industrial_organization",
                          "policies", "_test.txt")
        os.makedirs(os.path.dirname(pp), exist_ok=True)
        with open(pp, "w", encoding="utf-8") as f:
            f.write(POLICY_SAMPLE)
        dlg = MioPolicyEditorDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertGreaterEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.icon_edit.text(), "GFX_mio_policy_test")
        dlg.close()

    def test_menu_factory_has_mio_actions(self):
        from PyQt6.QtWidgets import QMenu
        from menu_factory import build_tool_actions
        menu = QMenu()
        actions = build_tool_actions(menu)
        self.assertIn("mio_editor", actions)
        self.assertIn("mio_policy_editor", actions)
        self.assertIn("mio_ai_weights", actions)


if __name__ == "__main__":
    unittest.main()
