"""B3 批二⑤：CWT-lite 类型规则校验测试。"""

from __future__ import annotations

import os
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


def _make_core(mod):
    from api_server import ApiCore
    return ApiCore(mod_path=mod, game_path="")


class CwtLiteRulesTest(unittest.TestCase):
    def test_validate_content_red_on_bad_type(self):
        from cwt_lite_rules import validate_content
        good = "focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = 1\n\t}\n}\n"
        issues = validate_content(good, "focus")
        self.assertFalse([i for i in issues if i["severity"] == "red"])
        bad = "focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = not_a_number\n\t}\n}\n"
        issues2 = validate_content(bad, "focus")
        self.assertTrue([i for i in issues2 if i["severity"] == "red"])

    def test_infer_type(self):
        from cwt_lite_rules import infer_type
        self.assertEqual(infer_type("common/national_focus/ger.txt"), "focus")
        self.assertEqual(infer_type("common/ideas/x.txt"), "idea")
        self.assertEqual(infer_type("history/states/1.txt"), "state")
        self.assertEqual(infer_type("common/characters/ger.txt"), "character")
        self.assertEqual(infer_type("common/technologies/x.txt"), "technology")
        self.assertEqual(infer_type("common/buildings/b.txt"), "building")
        self.assertEqual(infer_type("common/operations/o.txt"), "operation")
        self.assertEqual(infer_type("map/strategicregions/1.txt"),
                         "strategic_region")
        self.assertEqual(infer_type("common/bookmarks/b.txt"), "bookmark")
        self.assertEqual(infer_type("common/scripted_effects/x.txt"),
                         "scripted_effect")
        self.assertEqual(infer_type("common/scripted_triggers/x.txt"),
                         "scripted_trigger")
        self.assertEqual(infer_type("common/scripted_localisation/x.txt"),
                         "scripted_localisation")
        self.assertEqual(infer_type("common/countries/ABC.txt"), "country")
        self.assertEqual(infer_type("history/countries/ABC.txt"),
                         "country_history")
        self.assertEqual(infer_type("common/state_category/city.txt"),
                         "state_category")
        self.assertEqual(infer_type("common/terrain/00_terrain.txt"), "terrain")
        self.assertEqual(infer_type("common/resources/00_resources.txt"),
                         "resource")
        self.assertEqual(infer_type("common/units/x.txt"), "unit")
        self.assertEqual(infer_type("history/units/x.txt"),
                         "division_template")
        self.assertIsNone(infer_type("localisation/en.txt"))

    def test_new_wrapper_types_validate(self):
        from cwt_lite_rules import validate_content
        cases = [
            ("character",
             "characters = {\n\tGER_a = {\n\t\tname = a\n\t\troles = { }\n\t}\n}\n",
             False),
            ("technology",
             "technologies = {\n\ttech_x = {\n\t\tstart_year = 1936\n\t}\n}\n",
             False),
            ("technology",
             "technologies = {\n\ttech_x = {\n\t\tstart_year = nope\n\t}\n}\n",
             True),
            ("bookmark",
             "bookmarks = {\n\tbm1 = {\n\t\tname = x\n\t\tstart_date = 1936.1.1\n\t}\n}\n",
             False),
            ("strategic_region",
             "strategic_region = {\n\tid = 1\n\tprovinces = { 1 2 }\n}\n",
             False),
            ("state_category",
             "state_categories = {\n\tcity = {\n\t\tlocal_building_slots = 6\n\t}\n}\n",
             False),
            ("state_category",
             "state_categories = {\n\tcity = {\n\t\tcolor = 5\n\t}\n}\n",
             True),
            ("terrain",
             "categories = {\n\tforest = {\n\t\tcolor = { 89 199 85 }\n"
             "\t\tmovement_cost = 1.5\n\t\tis_water = no\n\t}\n}\n",
             False),
            ("terrain",
             "categories = {\n\tforest = {\n\t\tis_water = 1\n\t}\n}\n",
             True),
            ("resource",
             "resources = {\n\toil = {\n\t\ticon_frame = 1\n\t\tcic = 0.125\n"
             "\t\tconvoys = 0.1\n\t}\n}\n",
             False),
            ("unit",
             "sub_units = {\n\tinfantry = {\n\t\tsprite = infantry\n"
             "\t\tpriority = 1\n\t\tactive = yes\n\t\ttype = infantry\n\t}\n}\n",
             False),
            ("unit",
             "sub_units = {\n\tinfantry = {\n\t\tactive = 1\n\t}\n}\n",
             True),
        ]
        for type_key, content, expect_red in cases:
            issues = validate_content(content, type_key)
            red = [i for i in issues if i["severity"] == "red"]
            self.assertEqual(bool(red), expect_red, type_key)

    def test_decision_category_traversal(self):
        """真实决议文件为「顶层 category 块 → 直接子块即 decision」结构。"""
        from cwt_lite_rules import validate_content
        content = (
            "GER_ops = {\n"
            "\tGER_anarchist_union = {\n"
            "\t\ticon = GFX_decision_x\n"
            "\t\tdays_remove = DAYS_REMOVE_SOMETHING\n"
            "\t\tfire_only_once = yes\n"
            "\t}\n"
            "}\n")
        issues = validate_content(content, "decision")
        red = [i for i in issues if i["severity"] == "red"]
        self.assertEqual(red, [], "category 结构 + var_int 变量天数不应红")

    def test_top_level_entity_types(self):
        """modifier/operation/occupation_law/game_rule/dynamic_modifier 顶层块即实体。"""
        from cwt_lite_rules import validate_content
        cases = [
            ("modifier",
             "_test_mod = {\n\ticon = GFX_mod_x\n\tis_percent = yes\n}\n", False),
            ("operation",
             "op_rescue = {\n\tname = op_rescue\n\ticon = GFX_op\n\tdays = 35\n\tnetwork_strength = 30\n}\n",
             False),
            ("occupation_law",
             "civilian_oversight = {\n\ticon = 5\n\tdefault_law = yes\n}\n", False),
            ("game_rule",
             "rule_ai = {\n\tname = \"RULE_NAME\"\n\tgroup = \"GRP\"\n\trequired_dlc = \"LaR\"\n}\n",
             False),
            ("dynamic_modifier",
             "test_dyn = {\n\ticon = \"GFX_idea_unknown\"\n\tattacker_modifier = no\n}\n",
             False),
        ]
        for type_key, content, expect_red in cases:
            issues = validate_content(content, type_key)
            red = [i for i in issues if i["severity"] == "red"]
            self.assertEqual(bool(red), expect_red, type_key)

    def test_wargoal_wrapper_and_fixed_top(self):
        from cwt_lite_rules import validate_content
        # wargoal_types wrapper
        wargoal = (
            "wargoal_types = {\n"
            "\ttake_state = {\n\t\tgenerate_base_cost = 200\n\t\tthreat = 10\n\t}\n"
            "}\n")
        red = [i for i in validate_content(wargoal, "wargoal")
               if i["severity"] == "red"]
        self.assertEqual(red, [])
        # autonomous_state 固定键顶层块
        ast = (
            "autonomy_state = {\n"
            "\tid = autonomy_colony\n\tis_puppet = yes\n\tmin_freedom_level = 0.6\n"
            "}\n")
        red = [i for i in validate_content(ast, "autonomous_state")
               if i["severity"] == "red"]
        self.assertEqual(red, [])
        # intelligence_agency 固定键顶层块
        ia = (
            "intelligence_agency = {\n"
            "\tpicture = GFX_ia_usa\n\tnames = { \"A\" \"B\" }\n"
            "\tdefault = { tag = USA }\n}\n")
        red = [i for i in validate_content(ia, "intelligence_agency")
               if i["severity"] == "red"]
        self.assertEqual(red, [])

    def test_event_title_desc_block_or_string(self):
        from cwt_lite_rules import validate_content
        # 标量本地化键（非块）
        scalar = (
            "country_event = {\n\tid = ev.1\n\ttitle = ev.1.t\n\tdesc = ev.1.d\n"
            "\tis_triggered_only = yes\n}\n")
        red = [i for i in validate_content(scalar, "event")
               if i["severity"] == "red"]
        self.assertEqual(red, [])
        # 块形态（text = {...}）
        block = (
            "country_event = {\n\tid = ev.2\n"
            "\ttitle = { text = ev.2.t }\n\tdesc = { text = ev.2.d }\n}\n")
        red = [i for i in validate_content(block, "event")
               if i["severity"] == "red"]
        self.assertEqual(red, [])

    def test_script_ref_and_var_ident(self):
        from cwt_lite_rules import validate_content
        # @常量、var_*、[表达式] 在数值位合法
        for content, t in [
            ("focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = 1\n\t\tcost = @my_cost\n\t}\n}\n", "focus"),
            ("focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = var_x\n\t}\n}\n", "focus"),
        ]:
            red = [i for i in validate_content(content, t)
                   if i["severity"] == "red"]
            self.assertEqual(red, [], t)
        # 纯字母数字裸词仍按非法 int 报红
        bad = ("focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = nope\n\t}\n}\n")
        red = [i for i in validate_content(bad, "focus")
               if i["severity"] == "red"]
        self.assertTrue(red)
        # 命名空间变量（global.x / CZE.x）在 var_* 位合法
        dotted = (
            "GER_ops = {\n"
            "\tGER_decision = {\n"
            "\t\tdays_remove = global.days_add_support\n"
            "\t}\n"
            "}\n")
        red = [i for i in validate_content(dotted, "decision")
               if i["severity"] == "red"]
        self.assertEqual(red, [])

    def test_state_block_empty_value_artifact(self):
        """`key =` 换行 `{` 产生的空值 '' 不应把 block 字段报红。"""
        from cwt_lite_rules import validate_content
        content = (
            "state = {\n\tid = 1\n\tname = \"STATE_1\"\n\thistory=\n\t{\n"
            "\t\towner = GER\n\t}\n}\n")
        red = [i for i in validate_content(content, "state")
               if i["severity"] == "red"]
        self.assertEqual(red, [])

    def test_file_entity_and_scripted_types(self):
        from cwt_lite_rules import validate_content
        # country：整文件即实体，顶层字段直接校验
        c = "graphical_culture = western_gfx\ngraphical_culture_2d = western_2d\n"
        issues = validate_content(c, "country")
        self.assertEqual([i for i in issues if i["severity"] == "red"], [])
        # country_history：顶层字段；block 期望字段出现非空标量报红
        ch = ("capital = 127\nset_research_slots = 3\n"
              "set_technology = {\n\tinfantry_weapons = 1\n}\n")
        issues = validate_content(ch, "country_history")
        self.assertEqual([i for i in issues if i["severity"] == "red"], [])
        bad = "set_technology = 123\n"
        issues = validate_content(bad, "country_history")
        self.assertTrue([i for i in issues if i["severity"] == "red"])
        # scripted_effect / scripted_trigger：空 catalog，仅识别+遍历，不误报
        se = "my_effect = {\n\tadd_political_power = 66\n}\n"
        issues = validate_content(se, "scripted_effect")
        self.assertEqual([i for i in issues if i["severity"] == "red"], [])
        self.assertFalse([i for i in issues if i["severity"] == "yellow"])
        st = "is_valid_token = {\n\tNOT = { has_dlc = \"LaR\" }\n}\n"
        issues = validate_content(st, "scripted_trigger")
        self.assertEqual([i for i in issues if i["severity"] == "red"], [])
        # scripted_localisation：defined_text 顶层块，name 标量 + text 块合法
        sl = ("defined_text = {\n\tname = GetName\n\ttext = {\n"
              "\t\ttrigger = { always = yes }\n\t\tlocalization_key = X\n\t}\n}\n")
        issues = validate_content(sl, "scripted_localisation")
        self.assertEqual([i for i in issues if i["severity"] == "red"], [])
        # text 期望块却给标量 → 红
        sl_bad = "defined_text = {\n\tname = GetName\n\ttext = OOPS\n}\n"
        issues = validate_content(sl_bad, "scripted_localisation")
        self.assertTrue([i for i in issues if i["severity"] == "red"])

    def test_oversize_file_skipped(self):
        """超大文件跳过解析（黄色提示，不红不挂起）。"""
        import cwt_lite_rules
        big = "a" * (cwt_lite_rules.MAX_PARSE_CHARS + 10)
        issues = cwt_lite_rules.validate_content(big, "scripted_localisation")
        self.assertEqual([i for i in issues if i["severity"] == "red"], [])
        self.assertTrue([i for i in issues if i["severity"] == "yellow"])


class CwtLiteCoreTest(unittest.TestCase):
    def _mod_with_focus(self):
        mod = _mkdtemp("cwt_")
        d = os.path.join(mod, "common", "national_focus")
        os.makedirs(d)
        with open(os.path.join(d, "ger.txt"), "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = 1\n\t}\n}\n")
        return mod

    def test_validate_file_by_path(self):
        core = _make_core(self._mod_with_focus())
        r = core.validate_hoi4_file(
            {"path": "common/national_focus/ger.txt"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["type"], "focus")
        self.assertTrue(r["green"])
        self.assertEqual(r["red"], 0)

    def test_validate_project(self):
        core = _make_core(self._mod_with_focus())
        r = core.validate_hoi4_project({"max_files": 50})
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["counts"]["files"], 1)
        self.assertIn("CWT-lite", r["note"])

    def test_validate_project_scans_new_dirs(self):
        """validate_hoi4_project 覆盖 33 类型目录（含 common/units）。"""
        mod = _mkdtemp("cwt_scan_")
        d = os.path.join(mod, "common", "national_focus")
        os.makedirs(d)
        with open(os.path.join(d, "ger.txt"), "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n\tfocus = {\n\t\tid = a\n\t\tx = 1\n\t}\n}\n")
        u = os.path.join(mod, "common", "units")
        os.makedirs(u)
        with open(os.path.join(u, "infantry.txt"), "w", encoding="utf-8") as f:
            f.write("sub_units = {\n\tinfantry = {\n\t\tsprite = infantry\n"
                    "\t\tpriority = 1\n\t\tactive = yes\n\t}\n}\n")
        core = _make_core(mod)
        r = core.validate_hoi4_project({"max_files": 100})
        self.assertGreaterEqual(r["counts"]["files"], 2)
        self.assertEqual(r["counts"]["red"], 0)

    def test_validate_content_bad(self):
        core = _make_core(self._mod_with_focus())
        r = core.validate_hoi4_file({
            "content": "focus_tree = {\n\tfocus = {\n\t\tx = nope\n\t}\n}\n",
            "type": "focus"})
        self.assertFalse(r["green"])
        self.assertGreater(r["red"], 0)


class CwtMcpRegistryTest(unittest.TestCase):
    def test_tools_registered_in_health(self):
        from mcp_tools import build_tools, tool_category
        core = _make_core(_mkdtemp("cwt_reg_"))
        names = {t["name"] for t in build_tools(core)}
        self.assertIn("validate_hoi4_file", names)
        self.assertIn("validate_hoi4_project", names)
        self.assertEqual(tool_category("validate_hoi4_file"), "health")


if __name__ == "__main__":
    unittest.main()