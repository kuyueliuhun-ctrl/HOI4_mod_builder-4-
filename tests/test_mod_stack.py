"""Mod 层栈契约（mod_stack，阶段A 共用底座）。

覆盖：
- scan_rel 合并视图：高层遮蔽低层、后缀大小写、排序稳定性、
  include_shadowed 全命中（含层下标）
- resolve / resolve_all 顶层命中语义
- layer_index_of / rel_path_of 子目录归属与跨盘符健壮性
- write_target 恒指子 mod；无写层抛错
- copy_up：低层复制（内容字节一致、目录自动创建）、顶层 no-op、无命中 None
- route_existing 栈模式（子 mod 直用 / 低层复制上来 / 无命中）
- route_existing 传统模式与 state_build_ops.ensure_file_in_mod 逐一对拍
- from_paths 无效目录过滤 / set_active_stack 校验与全局激活往返
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import mod_stack as ms  # noqa: E402
from mod_stack import (  # noqa: E402
    ModLayer,
    ModStack,
    active_stack,
    clear_active_stack,
    from_paths,
    route_existing,
    set_active_stack,
)
from state_build_ops import ensure_file_in_mod  # noqa: E402


def _mk(prefix):
    return tempfile.mkdtemp(prefix="dsh_stack_" + prefix)


def _put(root, rel, content=b"data"):
    fp = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(fp, mode) as f:
        f.write(content)
    return fp


def _three_layer_stack():
    sub, base, van = _mk("sub"), _mk("base"), _mk("van")
    _put(base, "common/a.txt", b"base-a")
    _put(van, "common/a.txt", b"van-a")
    _put(van, "common/b.txt", b"van-b")
    _put(sub, "common/c.txt", b"sub-c")
    stack = ModStack([
        ModLayer("子mod", sub, True, "submod"),
        ModLayer("底层", base, False, "mod"),
        ModLayer("原版", van, False, "vanilla"),
    ])
    return stack, sub, base, van


class TestScanRel(unittest.TestCase):
    def setUp(self):
        self.stack, self.sub, self.base, self.van = _three_layer_stack()

    def test_merged_view_top_wins(self):
        got = self.stack.scan_rel("common", ".txt")
        rels = {r.rel_path: r for r in got}
        self.assertEqual(set(rels), {"common/a.txt", "common/b.txt",
                                     "common/c.txt"})
        self.assertEqual(os.path.basename(rels["common/a.txt"].path), "a.txt")
        self.assertEqual(rels["common/a.txt"].layer_index, 1)   # 底层胜原版
        with open(rels["common/a.txt"].path, "rb") as f:
            self.assertEqual(f.read(), b"base-a")
        self.assertEqual(rels["common/c.txt"].layer_index, 0)   # 子 mod

    def test_shadowed_top_layer_wins(self):
        _put(self.sub, "common/b.txt", b"sub-b")
        got = {r.rel_path: r for r in self.stack.scan_rel("common", ".txt")}
        self.assertEqual(got["common/b.txt"].layer_index, 0)
        self.assertEqual(got["common/b.txt"].layer_name, "子mod")

    def test_include_shadowed_returns_all_hits(self):
        _put(self.sub, "common/b.txt", b"sub-b")
        got = self.stack.scan_rel("common", ".txt", include_shadowed=True)
        b_hits = [r for r in got if r.rel_path == "common/b.txt"]
        self.assertEqual([r.layer_index for r in b_hits], [0, 2])
        # 排序稳定：按 (rel_path, layer_index)
        keys = [(r.rel_path, r.layer_index) for r in got]
        self.assertEqual(keys, sorted(keys))

    def test_ext_case_insensitive_and_filter(self):
        _put(self.sub, "common/d.GFX", b"x")
        _put(self.sub, "common/e.yml", b"x")
        rels = {r.rel_path for r in self.stack.scan_rel("common", ".gfx")}
        self.assertEqual(rels, {"common/d.GFX"})
        all_rels = {r.rel_path for r in self.stack.scan_rel("common", None)}
        self.assertIn("common/e.yml", all_rels)

    def test_missing_dir_and_root_scan(self):
        self.assertEqual(self.stack.scan_rel("no/such/dir"), [])
        root_rels = {r.rel_path for r in self.stack.scan_rel("", ".txt")}
        self.assertEqual(root_rels, set())   # 三层根目录都无散文件


class TestResolve(unittest.TestCase):
    def setUp(self):
        self.stack, self.sub, self.base, self.van = _three_layer_stack()

    def test_resolve_top_hit_order(self):
        self.assertEqual(self.stack.resolve("common/c.txt"),
                         os.path.join(self.sub, "common", "c.txt"))
        self.assertEqual(self.stack.resolve("common/b.txt"),
                         os.path.join(self.van, "common", "b.txt"))
        self.assertIsNone(self.stack.resolve("common/zz.txt"))

    def test_resolve_all_order_and_layers(self):
        hits = self.stack.resolve_all("common/a.txt")
        self.assertEqual([h[0] for h in hits], [1, 2])
        self.assertEqual(hits[0][1], "底层")

    def test_layer_index_of_and_rel_path_of(self):
        fp = os.path.join(self.base, "common", "a.txt")
        self.assertEqual(self.stack.layer_index_of(fp), 1)
        self.assertEqual(self.stack.rel_path_of(fp), "common/a.txt")
        self.assertIsNone(self.stack.layer_index_of(tempfile.gettempdir()
                                                    + "/outside.txt"))

    def test_layer_index_of_root_itself(self):
        self.assertEqual(self.stack.layer_index_of(self.van), 2)


class TestWriteRouting(unittest.TestCase):
    def setUp(self):
        self.stack, self.sub, self.base, self.van = _three_layer_stack()

    def test_write_target_always_submod(self):
        self.assertEqual(self.stack.write_target("common/new.txt"),
                         os.path.join(self.sub, "common", "new.txt"))

    def test_write_target_without_writable_top_raises(self):
        ro = ModStack([ModLayer("r", self.base, False, "mod")])
        with self.assertRaises(RuntimeError):
            ro.write_target("x.txt")

    def test_copy_up_from_lower_layer(self):
        got = self.stack.copy_up("common/a.txt")
        self.assertEqual(got, os.path.join(self.sub, "common", "a.txt"))
        with open(got, "rb") as f:
            self.assertEqual(f.read(), b"base-a")   # 底层版本（非原版）
        self.assertTrue(os.path.isdir(os.path.dirname(got)))

    def test_copy_up_creates_dirs_for_vanilla_file(self):
        got = self.stack.copy_up("common/b.txt")
        with open(got, "rb") as f:
            self.assertEqual(f.read(), b"van-b")

    def test_copy_up_top_noop_and_missing_none(self):
        self.assertEqual(self.stack.copy_up("common/c.txt"),
                         os.path.join(self.sub, "common", "c.txt"))
        self.assertIsNone(self.stack.copy_up("common/none.txt"))

    def test_stack_route_existing(self):
        p1, c1 = self.stack.route_existing("common/c.txt")
        self.assertEqual(p1, os.path.join(self.sub, "common", "c.txt"))
        self.assertFalse(c1)
        p2, c2 = self.stack.route_existing("common/a.txt")
        self.assertTrue(c2)
        self.assertTrue(p2.startswith(self.sub))
        self.assertIsNone(self.stack.route_existing("common/none.txt")[0])

    def test_route_existing_low_layer_copy_is_from_base_not_vanilla(self):
        # a.txt 在底层与原版都有 → 必须复制「底层」版本（加载语义：高遮蔽低）
        p, copied = self.stack.route_existing("common/a.txt")
        self.assertTrue(copied)
        with open(p, "rb") as f:
            self.assertEqual(f.read(), b"base-a")


class TestLegacyParity(unittest.TestCase):
    """未激活栈时 route_existing 与旧 ensure_file_in_mod 逐一对拍。"""

    def setUp(self):
        clear_active_stack()
        self.mod = _mk("leg_mod")
        self.game = _mk("leg_game")

    def test_parity_all_cases(self):
        _put(self.mod, "history/in_mod.txt", b"m")
        _put(self.game, "history/in_game.txt", b"g")
        cases = ["history/in_mod.txt", "history/in_game.txt",
                 "history/missing.txt"]
        for rel in cases:
            # 两侧各用独立 mod 目录（求值顺序会复制文件，同目录会污染对拍）；
            # 结果按语义比较：copied 标志 + 相对路径 + 文件内容
            r_mod, e_mod = _mk("leg_r"), _mk("leg_e")
            r = route_existing(r_mod, self.game, rel)
            e = ensure_file_in_mod(e_mod, self.game, rel)
            self.assertEqual(r[1], e[1], rel)
            self.assertEqual(
                None if r[0] is None else os.path.relpath(r[0], r_mod),
                None if e[0] is None else os.path.relpath(e[0], e_mod), rel)
            if r[0] and e[0]:
                with open(r[0], "rb") as f1, open(e[0], "rb") as f2:
                    self.assertEqual(f1.read(), f2.read(), rel)

    def test_copy_from_game_content_identical(self):
        _put(self.game, "history/s.txt", b"game-bytes")
        p, copied = route_existing(self.mod, self.game, "history/s.txt")
        self.assertTrue(copied)
        with open(p, "rb") as f:
            self.assertEqual(f.read(), b"game-bytes")
        self.assertTrue(p.startswith(self.mod))

    def test_invalid_mod_path(self):
        self.assertEqual(route_existing("", self.game, "x.txt"), (None, False))
        self.assertEqual(
            route_existing(os.path.join(self.mod, "gone"), self.game, "x.txt"),
            (None, False))

    def test_active_stack_overrides_legacy_args(self):
        stack, sub, base, van = _three_layer_stack()
        set_active_stack(stack)
        try:
            # 传统参数全无效，但栈激活 → 仍按栈路由
            p, copied = route_existing("", "", "common/a.txt")
            self.assertTrue(copied)
            self.assertTrue(p.startswith(sub))
        finally:
            clear_active_stack()


class TestContextAndFactory(unittest.TestCase):
    def setUp(self):
        clear_active_stack()
        self.addCleanup(clear_active_stack)

    def test_from_paths_filters_invalid(self):
        sub, base, van = _mk("f_sub"), _mk("f_base"), _mk("f_van")
        stack = from_paths(sub_mod=sub, mod_paths=[base, "/no/such"],
                           vanilla=van, submod_name="我的子mod")
        self.assertEqual(len(stack), 3)
        self.assertEqual(stack.layers[0].name, "我的子mod")
        self.assertEqual(stack.layers[0].kind, "submod")
        self.assertEqual(stack.layers[2].kind, "vanilla")
        self.assertEqual(stack.submod_path, sub)

    def test_from_paths_all_invalid_empty_stack(self):
        self.assertEqual(len(from_paths(sub_mod="/no/x")), 0)

    def test_active_stack_roundtrip_and_validation(self):
        self.assertIsNone(active_stack())
        stack, sub, _b, _v = _three_layer_stack()
        set_active_stack(stack)
        self.assertIs(active_stack(), stack)
        clear_active_stack()
        self.assertIsNone(active_stack())
        with self.assertRaises(ValueError):
            set_active_stack(ModStack([ModLayer("r", _mk("ro"), False)]))
        with self.assertRaises(ValueError):
            set_active_stack("not a stack")

    def test_empty_stack_cannot_be_activated(self):
        with self.assertRaises(ValueError):
            set_active_stack(ModStack([]))


if __name__ == "__main__":
    unittest.main()
