"""契约测试：TreeMode.from_focus_load 重构后的解析结构。"""

from __future__ import annotations

import sys
import os
import unittest
from types import SimpleNamespace


class _Known:
    """模拟 focus_load.known 的容器语义（支持 `in` 与属性访问）。"""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __contains__(self, key):
        return hasattr(self, key)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _make_known(**overrides):
    data = dict(
        icon=None,
        cost=10,
        relative_position_id="",
        search_filters=None,
        prerequisite=None,
        mutually_exclusive=None,
        will_lead_to_war_with=None,
        dynamic=None,
        text_icon=None,
        available_if_capitulated=None,
        cancelable=None,
        bypass_if_unavailable=None,
        continue_if_invalid=None,
        cancel_if_invalid=None,
        ai_will_do=None,
        available=None,
        allow_branch=None,
        select_effect=None,
        bypass=None,
        historical_ai=None,
        cancel=None,
        completion_reward=None,
        unknown=None,
    )
    data.update(overrides)
    return _Known(**data)


class TreeNodeFocusLoadTest(unittest.TestCase):
    def test_from_focus_load_parses_common_fields_and_blocks(self):
        from tree_node import TreeNode
        focus_load = SimpleNamespace(
            focus_id="my_focus",
            known=_make_known(
                icon="GFX_my_focus",
                prerequisite=["{ focus = A focus = B }"],
                mutually_exclusive=["{ focus = C }"],
                ai_will_do={"base": 10, "factor": 2},
                available="always = yes",
                completion_reward="{ hidden_effect = { add_war_support = 0.1 } add_stability = 0.1 }",
                unknown={"custom_flag": "yes"},
            ),
        )
        root = TreeNode.from_focus_load(
            focus_load, x_val="10", y_val="20", raw_fields={})
        keys = [c.key for c in root.children]
        self.assertIn("id", keys)
        self.assertIn("x", keys)
        self.assertIn("y", keys)
        self.assertIn("prerequisite", keys)
        self.assertIn("mutually_exclusive", keys)
        self.assertIn("ai_will_do", keys)
        self.assertIn("available", keys)
        self.assertIn("completion_reward", keys)
        self.assertIn("custom_flag", keys)

        prereq = next(c for c in root.children if c.key == "prerequisite")
        self.assertEqual([v.value for v in prereq.children], ["A", "B"])

    def test_from_focus_load_tolerates_missing_optional_fields(self):
        from tree_node import TreeNode
        focus_load = SimpleNamespace(
            focus_id="minimal", known=_make_known(cost=None))
        root = TreeNode.from_focus_load(focus_load, "", "")
        self.assertEqual(root.key, "focus")
        self.assertEqual([c.key for c in root.children], ["id"])


if __name__ == "__main__":
    unittest.main()