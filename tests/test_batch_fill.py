"""批量填鸭（AOR）列表驱动模板生成测试。"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class BatchFillTest(unittest.TestCase):
    def test_idea_sprite_expands_names(self):
        from batch_fill import generate_preset
        text = generate_preset("idea_sprite", ["CH", "AH"])
        self.assertIn('name = "GFX_idea_CH"', text)
        self.assertIn('texturefile = "gfx/interface/ideas/CH.dds"', text)
        self.assertIn('name = "GFX_idea_AH"', text)
        self.assertEqual(text.count("GFX_idea_"), 2)

    def test_shine_sprite_expands_names(self):
        from batch_fill import generate_preset
        text = generate_preset("shine_sprite", ["逻各斯"])
        self.assertIn('name = "GFX_逻各斯_shine"', text)
        self.assertIn('texturefile = "gfx/interface/goals/逻各斯.dds"', text)

    def test_general_expands_numeric_and_job(self):
        from batch_fill import generate_preset
        rows = [{
            "name": "VMS",
            "job": "corps_commander",
            "skill": "1",
            "attack": "2",
            "defense": "3",
            "planning": "4",
            "logistics": "5",
        }]
        text = generate_preset("general", rows)
        self.assertIn("VMS= {", text)
        self.assertIn("name = VMS", text)
        self.assertIn("corps_commander = {", text)
        self.assertIn("skill = 1", text)
        self.assertIn("attack_skill = 2", text)
        self.assertIn("defense_skill = 3", text)
        self.assertIn("planning_skill = 4", text)
        self.assertIn("logistics_skill = 5", text)

    def test_case_insensitive_keys_and_percent_placeholder(self):
        from batch_fill import expand_template
        text = expand_template("GFX_portrait_%NAME%_small", {"name": "AAA"})
        self.assertEqual(text, "GFX_portrait_AAA_small")

    def test_double_underscore_placeholder_supported(self):
        from batch_fill import expand_template
        text = expand_template("__NAME__ = { name = __NAME__ }", {"NAME": "X"})
        self.assertEqual(text, "X = { name = X }")

    def test_parse_table(self):
        from batch_fill import parse_table
        text = "name\tjob\tskill\nA\tcorps_commander\t2\nB\tfield_marshal\t3\n"
        rows = parse_table(text)
        self.assertEqual(rows, [
            {"name": "A", "job": "corps_commander", "skill": "2"},
            {"name": "B", "job": "field_marshal", "skill": "3"},
        ])

    def test_generate_batch_empty(self):
        from batch_fill import generate_batch
        self.assertEqual(generate_batch("abc", []), "")

    def test_preset_help_lists_all(self):
        from batch_fill import BATCH_PRESETS, format_preset_help
        help_text = format_preset_help()
        for name in BATCH_PRESETS:
            self.assertIn(name, help_text)


if __name__ == "__main__":
    unittest.main()