"""契约测试：通用装备加载层（equipment_loader.py）。

覆盖 load_equipment_defs / load_equipment_modules / load_equipment_variants
的直接行为，与 ship/tank/plane 的薄封装共用同一套通用逻辑。
"""

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


class EquipmentLoaderTest(unittest.TestCase):
    def _make_env(self):
        mod = _mkdtemp("dsh_eq_loader_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq_dir = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(eq_dir, exist_ok=True)
        # 装备定义：archetype + inherit 变体
        with open(os.path.join(eq_dir, "00_weapon_defs.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tweapon_base = {\n'
                    '\t\tis_archetype = yes\n'
                    '\t\tmodule_slots = {\n'
                    '\t\t\tslot_a = {\n'
                    '\t\t\t\trequired = yes\n'
                    '\t\t\t\tallowed_module_categories = { cat_a }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t\tdefault_modules = { slot_a = mod_a }\n'
                    '\t\tattack = 5\n'
                    '\t\tderived = base_derived\n'
                    '\t}\n'
                    '\tweapon_var = {\n'
                    '\t\tarchetype = weapon_base\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        # 模块
        mod_dir = os.path.join(eq_dir, "modules")
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, "00_test_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tmod_a = {\n'
                    '\t\tabbreviation = "m"\n'
                    '\t\tcategory = cat_a\n'
                    '\t\tadd_stats = { attack = 2 }\n'
                    '\t\tmultiply_stats = { speed = -0.1 }\n'
                    '\t}\n'
                    '}\n')
        # 国家设计：只收 weapon_var 类型
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "AAA.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Weapon"\n'
                    '\ttype = weapon_var\n'
                    '\tmodules = { slot_a = mod_a }\n'
                    '}\n'
                    'create_equipment_variant = {\n'
                    '\tname = "Other"\n'
                    '\ttype = other_thing\n'
                    '}\n')
        return mod

    def test_load_equipment_defs_with_extra_and_inherit(self):
        from equipment_loader import load_equipment_defs
        from oob_loader import _node_field_value
        mod = self._make_env()
        cache = {}

        def parse_extra(node, info):
            info["derived"] = _node_field_value(node, "derived") or ""

        def inherit_extra(info, arch, _arch_key):
            if not info.get("derived"):
                info["derived"] = arch.get("derived") or ""

        defs = load_equipment_defs(
            mod, "", cache, ("attack",),
            file_filter=lambda fn: fn.lower().startswith("00_weapon_defs"),
            extra_init={"derived": ""},
            extra_parse=parse_extra,
            extra_inherit=inherit_extra,
        )
        base = defs["weapon_base"]
        var = defs["weapon_var"]
        self.assertTrue(base["is_archetype"])
        self.assertEqual(base["stats"]["attack"], 5.0)
        self.assertEqual(base["derived"], "base_derived")
        self.assertEqual(sorted(var["module_slots"]), ["slot_a"])
        self.assertEqual(var["stats"]["attack"], 5.0, "变体应继承 archetype stats")
        self.assertEqual(var["derived"], "base_derived", "extra_inherit 应生效")

    def test_load_equipment_modules_generic(self):
        from equipment_loader import load_equipment_modules
        mod = self._make_env()
        mods = load_equipment_modules(mod, "", {}, "test")
        self.assertEqual(mods["mod_a"]["category"], "cat_a")
        self.assertEqual(mods["mod_a"]["add_stats"], {"attack": 2.0})
        self.assertEqual(mods["mod_a"]["multiply_stats"], {"speed": -0.1})

    def test_load_equipment_variants_generic(self):
        from equipment_loader import load_equipment_variants, _tag_of
        mod = self._make_env()
        variants = load_equipment_variants(
            mod, "", {}, {"weapon_var"},
            lambda t: t in {"weapon_var"} or "weapon" in t,
            tag_of=_tag_of,
        )
        self.assertEqual(list(variants.keys()), ["AAA"])
        v = variants["AAA"]["Test Weapon"]
        self.assertEqual(v["type"], "weapon_var")
        self.assertEqual(v["modules"], {"slot_a": "mod_a"})
        self.assertNotIn("Other", variants["AAA"])


if __name__ == "__main__":
    unittest.main()