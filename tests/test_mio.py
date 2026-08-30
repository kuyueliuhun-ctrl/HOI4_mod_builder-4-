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


class MioTraitLayoutParse(unittest.TestCase):
    """特质布局数据层：父 token 提取 + 裸 x/y 坐标兼容。"""

    def test_wrapped_parent_block_tokens(self):
        from mio_loader import parse_mio_organizations
        content = (
            "org = {\n"
            "\ttrait = {\n"
            "\t\ttoken = t_child\n"
            "\t\tname = t_child\n"
            "\t\tposition = { x=1 y=1 }\n"
            "\t\tany_parent = { traits = { t_pa t_pb } num_parents_needed = 1 }\n"
            "\t}\n"
            "\ttrait = {\n"
            "\t\ttoken = t_pa\n"
            "\t\tname = t_pa\n"
            "\t\tposition = { x=0 y=0 }\n"
            "\t}\n"
            "}\n")
        org = parse_mio_organizations(content)["org"]
        by = {t["token"]: t for t in org["traits"]}
        self.assertEqual(by["t_child"]["parents"], ["t_pa", "t_pb"])
        self.assertNotIn("traits", by["t_child"]["parents"])
        self.assertNotIn("num_parents_needed", by["t_child"]["parents"])

    def test_plain_xy_keys(self):
        from mio_loader import parse_mio_organizations
        content = (
            "org = {\n"
            "\ttrait = {\n"
            "\t\ttoken = t_x\n"
            "\t\tname = t_x\n"
            "\t\tx = 3\n"
            "\t\ty = 2\n"
            "\t}\n"
            "}\n")
        org = parse_mio_organizations(content)["org"]
        t = org["traits"][0]
        self.assertEqual((t["x"], t["y"]), (3, 2))


    def test_include_merge(self):
        from mio_loader import parse_mio_organizations, resolve_includes
        content = (
            "base_org = {\n"
            "\tinitial_trait = { name = base_init }\n"
            "\ttrait = {\n"
            "\t\ttoken = shared\n"
            "\t\tname = shared\n"
            "\t\tposition = { x=2 y=1 }\n"
            "\t\tequipment_bonus = { reliability = 0.05 }\n"
            "\t}\n"
            "}\n"
            "child_org = {\n"
            "\tinclude = base_org\n"
            "\ttrait = {\n"
            "\t\ttoken = shared\n"
            "\t\tlimit_to_equipment_type = { screen_ship }\n"
            "\t}\n"
            "\ttrait = {\n"
            "\t\ttoken = local_new\n"
            "\t\tname = local_new\n"
            "\t\tposition = { x=3 y=0 }\n"
            "\t}\n"
            "}\n")
        mios = parse_mio_organizations(content)
        merged = resolve_includes(mios)["child_org"]
        by = {t["token"]: t for t in merged["traits"]}
        # 继承特质保留底组织的 position，本地覆盖块字段并入
        self.assertEqual((by["shared"]["x"], by["shared"]["y"]), (2, 1))
        # raw 保留本地可写块（保存写回子组织自身文件）
        self.assertIn("limit_to_equipment_type", by["shared"]["raw"])
        self.assertNotIn("position", by["shared"]["raw"])
        self.assertTrue(any("limit_to_equipment_type" in b
                            for b in by["shared"]["extra_blocks"]))
        self.assertIn("reliability", by["shared"]["equipment_bonus"])
        # 本地新增特质保留
        self.assertEqual((by["local_new"]["x"], by["local_new"]["y"]), (3, 0))
        # initial_trait 缺失时继承
        self.assertEqual(merged["initial_trait"]["name"], "base_init")
        # 底组织自身不受影响
        self.assertEqual(len(mios["base_org"]["traits"]), 1)


    def test_mutually_exclusive_parsed(self):
        from mio_loader import parse_mio_organizations
        content = (
            "org = {\n"
            "\ttrait = {\n"
            "\t\ttoken = t_a\n"
            "\t\tname = t_a\n"
            "\t\tposition = { x=0 y=0 }\n"
            "\t\tmutually_exclusive = { t_b t_c }\n"
            "\t}\n"
            "\ttrait = {\n"
            "\t\ttoken = t_b\n"
            "\t\tname = t_b\n"
            "\t\tposition = { x=1 y=0 }\n"
            "\t}\n"
            "}\n")
        org = parse_mio_organizations(content)["org"]
        by = {t["token"]: t for t in org["traits"]}
        self.assertEqual(by["t_a"]["mutually_exclusive"], ["t_b", "t_c"])
        # 原始块保留在 extra_blocks（写回不丢）
        self.assertTrue(any("mutually_exclusive" in b
                            for b in by["t_a"]["extra_blocks"]))

    def test_file_variables_in_position(self):
        from mio_loader import parse_mio_organizations
        content = (
            "@ship_1_X = 9\n"
            "@ship_1_Y = 3\n"
            "org = {\n"
            "\ttrait = {\n"
            "\t\ttoken = t_v\n"
            "\t\tname = t_v\n"
            "\t\tposition = { x=@ship_1_X y=@ship_1_Y }\n"
            "\t}\n"
            "}\n")
        org = parse_mio_organizations(content)["org"]
        t = org["traits"][0]
        self.assertEqual((t["x"], t["y"]), (9, 3))


class MioBonusLocalization(unittest.TestCase):
    """加成属性本地化：loc 链 + 内置词典兜底 + 系数百分比格式化。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_stat_label_mapping(self):
        from mio_editor_dialog import MioEditorDialog
        dlg = MioEditorDialog("", "")
        self.assertEqual(dlg._stat_label("soft_attack"), "软攻击")
        self.assertEqual(dlg._stat_label("build_cost_ic"), "生产花费")
        self.assertEqual(dlg._stat_label("totally_unknown_key"),
                         "totally_unknown_key")

    def test_format_bonus_percent(self):
        from mio_editor_dialog import MioEditorDialog
        dlg = MioEditorDialog("", "")
        lines = dlg._format_bonus("{\n\tbuild_cost_ic = -0.05\n}")
        self.assertTrue(any("生产花费 = -5%" in ln for ln in lines))
        lines2 = dlg._format_bonus("{\n\tproduction_capacity_factor = 0.1\n}")
        self.assertTrue(any("= +10%" in ln for ln in lines2))

    def test_format_bonus_strips_wrapper_and_templates(self):
        from mio_editor_dialog import MioEditorDialog
        dlg = MioEditorDialog("", "")
        raw = "equipment_bonus = {\n\t\t\tarmor_value = -0.05\n\t\t\tdefense =-0.05\n\t\t\tbuild_cost_ic = -0.03\n\t\t}\n\t}\n\n\t"
        text = "\n".join(dlg._format_bonus(raw))
        self.assertNotIn("equipment_bonus", text)   # 外层键不出现
        self.assertIn("装甲厚度 = -0.05", text)      # 模板串候选被跳过
        self.assertIn("防御 = -0.05", text)
        self.assertIn("生产花费 = -3%", text)


class MioTraitTreeDrawing(unittest.TestCase):
    """特质树绘图回归：文本不溢出节点 / 空特质占位提示。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_multiline_text_stays_inside_node(self):
        from PyQt6.QtWidgets import QGraphicsTextItem
        from mio_trait_tree import MioTraitTreeView
        tree = MioTraitTreeView()
        long_token = "tfr_mio_trait_extremely_long_token_name_for_overflow"
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [{"token": long_token, "name": long_token,
                        "icon": "", "x": 0, "y": 0}],
        })
        node = [i for i in tree._scene.items()
                if i.__class__.__name__ == "_TraitNode"][0]
        nrb = node.sceneBoundingRect()
        texts = [i for i in tree._scene.items()
                 if isinstance(i, QGraphicsTextItem)
                 and i.toPlainText() != "★"]
        self.assertTrue(texts)
        for it in texts:
            self.assertLessEqual(
                it.sceneBoundingRect().right(), nrb.right() + 1)
            self.assertLessEqual(
                it.sceneBoundingRect().bottom(), nrb.bottom() + 1)
        # 完整名称保留在 tooltip（截断只发生在显示层）
        self.assertIn(long_token, texts[0].toolTip())

    def test_long_name_renders_multiline(self):
        from PyQt6.QtWidgets import QGraphicsTextItem
        from mio_trait_tree import MioTraitTreeView
        tree = MioTraitTreeView()
        name = "tfr_mio_trait_extremely_long_token_name_for_overflow"
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [{"token": name, "name": name,
                        "icon": "", "x": 0, "y": 0}],
        })
        texts = [i for i in tree._scene.items()
                 if isinstance(i, QGraphicsTextItem)]
        self.assertEqual(len(texts), 1)
        txt = texts[0]
        # 文档高度明显超过单行（多行换行展示）或已做显示层截断
        shown = txt.toPlainText()
        self.assertGreater(txt.document().size().height(), 20)
        self.assertTrue(shown == name or shown.endswith("…"))

    def test_mutually_exclusive_line_drawn(self):
        from PyQt6.QtWidgets import QGraphicsLineItem
        from mio_trait_tree import MioTraitTreeView
        from theme import COLORS as C
        tree = MioTraitTreeView()
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [
                {"token": "a", "name": "a", "icon": "", "x": 0, "y": 0,
                 "mutually_exclusive": ["b"]},
                {"token": "b", "name": "b", "icon": "", "x": 1, "y": 0,
                 "mutually_exclusive": []},
            ],
        })
        lines = [i for i in tree._scene.items()
                 if isinstance(i, QGraphicsLineItem)]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].pen().color().name(), C["danger"].lower())

    def test_empty_traits_placeholder(self):
        from mio_trait_tree import MioTraitTreeView
        tree = MioTraitTreeView()
        tree.set_mio({"id": "x", "initial_trait": {}, "traits": []})
        self.assertTrue(tree._scene.items())  # 有占位提示而非空画布

    def test_theme_colors_match_app(self):
        from mio_trait_tree import MioTraitTreeView
        from theme import COLORS as C
        tree = MioTraitTreeView()
        self.assertEqual(tree.backgroundBrush().color().name(),
                         C["bg_surface_subtle"].lower())

    # ---------- 相对位置 / 连线还原游戏规则 ----------

    def test_relative_positions_resolved(self):
        from mio_trait_tree import CELL_H, CELL_W, MioTraitTreeView
        tree = MioTraitTreeView()
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [
                {"token": "base", "name": "base", "icon": "",
                 "x": 1, "y": 0, "relative_position_id": ""},
                {"token": "child", "name": "child", "icon": "",
                 "x": 1, "y": 2, "relative_position_id": "base"},
            ],
        })
        pos = tree._resolve_positions(tree._mio["traits"])
        self.assertEqual(pos["base"], (1, 0))
        self.assertEqual(pos["child"], (2, 2))  # (1,0) + (1,2)
        node = [i for i in tree._scene.items()
                if i.__class__.__name__ == "_TraitNode"
                and i.token == "child"][0]
        self.assertAlmostEqual(node.rect().x(), 2 * CELL_W + 10)
        self.assertAlmostEqual(node.rect().y(), 2 * CELL_H + 10)

    def test_relative_id_not_drawn_as_line(self):
        from PyQt6.QtWidgets import QGraphicsLineItem
        from mio_trait_tree import MioTraitTreeView
        tree = MioTraitTreeView()
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [
                {"token": "base", "name": "base", "icon": "",
                 "x": 0, "y": 0, "relative_position_id": ""},
                {"token": "child", "name": "child", "icon": "",
                 "x": 1, "y": 1, "relative_position_id": "base"},  # 仅定位
            ],
        })
        lines = [i for i in tree._scene.items()
                 if isinstance(i, QGraphicsLineItem)]
        self.assertEqual(lines, [])  # 游戏不为 relative_position_id 画线

    def test_parent_line_anchors_touch_nodes(self):
        from PyQt6.QtWidgets import QGraphicsLineItem
        from mio_trait_tree import NODE_H, NODE_W, MioTraitTreeView
        tree = MioTraitTreeView()
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [
                {"token": "pa", "name": "pa", "icon": "",
                 "x": 0, "y": 0, "relative_position_id": "",
                 "parents": []},
                {"token": "ch", "name": "ch", "icon": "",
                 "x": 0, "y": 1, "relative_position_id": "",
                 "parents": ["pa"]},
            ],
        })
        lines = [i for i in tree._scene.items()
                 if isinstance(i, QGraphicsLineItem)]
        self.assertEqual(len(lines), 1)
        ln = lines[0].line()
        # 子节点顶边中心 / 父节点底边中心（节点 x = col*CELL_W+10）
        self.assertAlmostEqual(ln.x1(), 0 + 10 + NODE_W // 2)
        self.assertAlmostEqual(ln.y1(), 1 * 94 + 10)
        self.assertAlmostEqual(ln.x2(), 0 + 10 + NODE_W // 2)
        self.assertAlmostEqual(ln.y2(), 0 * 94 + 10 + NODE_H)

    def test_cycle_guard_no_hang(self):
        from mio_trait_tree import MioTraitTreeView
        tree = MioTraitTreeView()
        tree.set_mio({
            "id": "x", "initial_trait": {},
            "traits": [
                {"token": "a", "name": "a", "icon": "",
                 "x": 0, "y": 0, "relative_position_id": "b"},
                {"token": "b", "name": "b", "icon": "",
                 "x": 1, "y": 1, "relative_position_id": "a"},
            ],
        })
        pos = tree._resolve_positions(tree._mio["traits"])
        self.assertEqual(len(pos), 2)  # 成环退化，不死循环

    def test_resolved_positions_collision_free(self):
        from mio_loader import load_mios
        from mio_trait_tree import MioTraitTreeView
        tree = MioTraitTreeView()
        mios = load_mios("/mnt/e/mods/3350890356",
                         "/mnt/e/SteamLibrary/steamapps/common/"
                         "Hearts of Iron IV")
        stacked = 0
        checked = 0
        for m in mios.values():
            if not (m.get("traits") or []):
                continue
            checked += 1
            pos = tree._resolve_positions(m["traits"])
            cells = list(pos.values())
            if len(cells) != len(set(cells)):
                stacked += 1
        self.assertEqual(stacked, 0)  # 解析后无同格叠加


if __name__ == "__main__":
    unittest.main()
