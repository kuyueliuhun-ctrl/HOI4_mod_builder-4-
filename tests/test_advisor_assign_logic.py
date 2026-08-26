"""契约测试：顾问分配模块重构后的纯逻辑（advisor_assign_dialog.py）。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class AdvisorAssignLogicTest(unittest.TestCase):
    def test_char_name_from_text_handles_inline_comment(self):
        from advisor_assign_dialog import _char_name_from_text
        text = (
            "every_possible_country = {\n"
            "\tgenerate_character = {\n"
            "\t\tname = GEN_NAME # 角色名\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_char_name_from_text(text), "GEN_NAME")

    def test_parse_character_assignment_extracts_excluded_and_slot(self):
        from advisor_assign_dialog import _parse_character_assignment
        text = (
            "every_possible_country = {\n"
            "\tlimit = {\n"
            "\t\tNOT = { OR = { tag = GER tag = SOV } }\n"
            "\t}\n"
            "\tgenerate_character = {\n"
            "\t\ttoken_base = GEN\n"
            "\t\tadvisor = {\n"
            "\t\t\tslot = political_advisor\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        parsed = _parse_character_assignment(text)
        self.assertIsNotNone(parsed)
        char_name, excluded, slot = parsed
        self.assertEqual(char_name, "GEN")
        self.assertEqual(excluded, ["GER", "SOV"])
        self.assertEqual(slot, "political_advisor")

    def test_load_character_assignments_from_temp_mod(self):
        from advisor_assign_dialog import load_character_assignments
        mod = _mkdtemp("dsh_advisor_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        gen_dir = os.path.join(mod, "history", "general")
        os.makedirs(gen_dir, exist_ok=True)
        with open(os.path.join(gen_dir, "generic_advisors.txt"),
                  "w", encoding="utf-8") as f:
            f.write(
                "every_possible_country = {\n"
                "\tlimit = { NOT = { tag = GER } }\n"
                "\tgenerate_character = {\n"
                "\t\tname = GEN\n"
                "\t\tadvisor = { slot = theorist }\n"
                "\t}\n"
                "}\n"
            )
        result = load_character_assignments(mod, "")
        self.assertIn("GEN", result)
        self.assertEqual(result["GEN"]["excluded"], ["GER"])
        self.assertEqual(result["GEN"]["slot"], "theorist")


if __name__ == "__main__":
    unittest.main()