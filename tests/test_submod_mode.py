"""子 mod 模式契约（阶段C：submod_wizard / mod_stack 钩子 / 接线）。

覆盖：
- build_submod_files：清单形状、dependencies 中文引号转义、
  path 正斜杠、yml BOM、解析回读一致、不含 country_tags
- resolve_folder_name：非法字符替换、重名加序号、空名兜底
- submod_settings_fields 字段形状
- copy_up 确认钩子：默认自动复制 / 回调拒绝返回 None / 回调参数正确
- ensure_file_in_mod 层栈路由：低层复制上来（74 处调用方零改动）
- workbench._iter_rel_files 层栈合并视图 + 底层文件标识数据
- SubmodWizard 端到端（offscreen）：播放集装载、勾选项、accept 生成
  文件并回调激活
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mk(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix="dsh_submod_" + prefix, dir=root)


def _put(root, rel, content, encoding="utf-8"):
    fp = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding=encoding) as f:
        f.write(content)
    return fp


class TestBuildSubmodFiles(unittest.TestCase):
    def test_file_list_shape(self):
        from submod_wizard import build_submod_files
        from mod_descriptor_loader import parse_mod_entries, extract_fields
        mod_dir = _mk("mods")
        files = build_submod_files(
            name="我的子mod", folder_name="submod_test", version="1.19.*",
            tags=["Balance"], base_names=["底层A", "底层 B"],
            mod_folder_path=mod_dir, mod_file_path=mod_dir)
        paths = [f["path"] for f in files]
        self.assertEqual(len(files), 4)
        self.assertTrue(any(p.endswith("submod_test.mod") for p in paths))
        self.assertTrue(any(p.endswith("descriptor.mod") for p in paths))
        self.assertTrue(any(p.endswith("submod_test.gfx") for p in paths))
        self.assertTrue(any(p.endswith("_l_simp_chinese.yml") for p in paths))
        self.assertFalse(any("country_tags" in p for p in paths))
        # path 字段正斜杠、指向子 mod 目录（解析回读验证，与分隔符风格无关）
        desc = next(f for f in files if f["path"].endswith("descriptor.mod"))
        fields = extract_fields(parse_mod_entries(desc["content"]))
        self.assertEqual(fields["path"],
                         os.path.join(mod_dir, "submod_test")
                         .replace("\\", "/"))

    def test_dependencies_roundtrip_with_chinese_and_space(self):
        from submod_wizard import build_submod_files
        from mod_descriptor_loader import parse_mod_entries, extract_fields
        mod_dir = _mk("deps")
        files = build_submod_files(
            name="子mod", folder_name="sub", version="1.19.*",
            base_names=["日共重置：粉碎帝国", "The Road to 56"],
            mod_folder_path=mod_dir, mod_file_path=mod_dir)
        content = files[0]["content"]
        fields = extract_fields(parse_mod_entries(content))
        self.assertEqual(fields["name"], "子mod")
        self.assertEqual(fields["dependencies"],
                         ["日共重置：粉碎帝国", "The Road to 56"])

    def test_path_always_quoted(self):
        """path 无空格也必须带引号（含空格目录如 Pax Britannica 不加引号会坏档）。"""
        from submod_wizard import build_submod_files
        mod_dir = _mk("quote")
        files = build_submod_files(
            name="子mod", folder_name="sub",
            mod_folder_path=mod_dir, mod_file_path=mod_dir)
        line = next(l for l in files[0]["content"].splitlines()
                    if l.strip().startswith("path"))
        self.assertIn('path="', line)
        self.assertTrue(line.rstrip().endswith('"'))

    def test_loc_file_has_bom(self):
        from submod_wizard import build_submod_files
        mod_dir = _mk("bom")
        files = build_submod_files(
            name="子mod", folder_name="sub", mod_folder_path=mod_dir,
            mod_file_path=mod_dir)
        yml = next(f for f in files if f["path"].endswith(".yml"))
        self.assertTrue(yml["bom"])

    def test_write_and_activate_flow(self):
        from submod_wizard import build_submod_files
        from mod_creator import write_mod_files
        from mod_descriptor_loader import parse_mod_entries, extract_fields
        mod_dir = _mk("flow")
        files = build_submod_files(
            name="我的子mod", folder_name="submod_x",
            base_names=["底层A"], mod_folder_path=mod_dir,
            mod_file_path=mod_dir)
        written = write_mod_files(files)
        self.assertEqual(len(written), 4)
        desc = os.path.join(mod_dir, "submod_x", "descriptor.mod")
        self.assertTrue(os.path.isfile(desc))
        fields = extract_fields(parse_mod_entries(
            open(desc, encoding="utf-8-sig").read()))
        self.assertEqual(fields["path"],
                         os.path.join(mod_dir, "submod_x").replace("\\", "/"))
        self.assertTrue(os.path.isdir(os.path.join(mod_dir, "submod_x",
                                                   "gfx")))


class TestFolderNameAndSettings(unittest.TestCase):
    def test_resolve_folder_name(self):
        from submod_wizard import resolve_folder_name
        self.assertEqual(resolve_folder_name("正常名字"), "正常名字")
        self.assertEqual(resolve_folder_name('a/b\\c:d*e?f"g<h>i|j'),
                         "abcdefghij")
        self.assertEqual(resolve_folder_name(""), "submod")
        self.assertEqual(resolve_folder_name("x", ("x",)), "x_2")
        self.assertEqual(resolve_folder_name("x", ("x", "x_2")), "x_3")

    def test_settings_fields(self):
        from submod_wizard import submod_settings_fields
        got = submod_settings_fields("/p/sub", "子mod", ["/p/base", ""])
        self.assertEqual(got, {"submod_active": True, "submod_path": "/p/sub",
                               "submod_name": "子mod",
                               "submod_bases": ["/p/base"]})


class TestCopyUpConfirmHook(unittest.TestCase):
    def setUp(self):
        from mod_stack import clear_active_stack, set_copy_up_confirm
        clear_active_stack()
        set_copy_up_confirm(None)
        self.addCleanup(clear_active_stack)
        self.addCleanup(set_copy_up_confirm, None)
        self.sub, self.base = _mk("hook_sub"), _mk("hook_base")
        _put(self.base, "common/a.txt", "base-a")

    def _stack(self):
        from mod_stack import ModLayer, ModStack
        return ModStack([
            ModLayer("子mod", self.sub, True, "submod"),
            ModLayer("底层", self.base, False, "mod"),
        ])

    def test_default_auto_copy(self):
        from mod_stack import route_existing
        stack = self._stack()
        stack.set_active = None
        import mod_stack as ms
        ms.set_active_stack(stack)
        p, copied = route_existing("", "", "common/a.txt")
        self.assertTrue(copied)
        self.assertTrue(p.startswith(self.sub))

    def test_declined_copy_returns_none(self):
        import mod_stack as ms
        calls = []

        def cb(rel, src, target):
            calls.append((rel, src, target))
            return False

        ms.set_active_stack(self._stack())
        ms.set_copy_up_confirm(cb)
        p, copied = ms.route_existing("", "", "common/a.txt")
        self.assertIsNone(p)
        self.assertFalse(copied)
        self.assertFalse(os.path.isfile(os.path.join(self.sub,
                                                     "common/a.txt")))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "common/a.txt")
        self.assertTrue(os.path.isfile(calls[0][1]))   # src 来自底层
        self.assertTrue(calls[0][2].startswith(self.sub))   # target 落子 mod

    def test_exception_in_cb_treated_as_decline(self):
        import mod_stack as ms
        ms.set_active_stack(self._stack())
        ms.set_copy_up_confirm(lambda *_a: 1 / 0)
        p, copied = ms.route_existing("", "", "common/a.txt")
        self.assertIsNone(p)
        self.assertFalse(copied)

    def test_existing_submod_file_skips_confirm(self):
        import mod_stack as ms
        _put(self.sub, "common/a.txt", "sub-a")
        called = []
        ms.set_active_stack(self._stack())
        ms.set_copy_up_confirm(lambda *a: called.append(a) or False)
        p, copied = ms.route_existing("", "", "common/a.txt")
        self.assertEqual(p, os.path.join(self.sub, "common", "a.txt"))
        self.assertFalse(copied)
        self.assertEqual(called, [])   # 顶层已有 → 不需要复制 → 不询问


class TestEnsureFileInModStackRouting(unittest.TestCase):
    def setUp(self):
        from mod_stack import clear_active_stack
        clear_active_stack()
        self.addCleanup(clear_active_stack)
        self.sub, self.base, self.van = _mk("r_sub"), _mk("r_base"), \
            _mk("r_van")
        _put(self.base, "history/countries/AAA.txt", "base")
        _put(self.van, "history/countries/BBB.txt", "van")
        _put(self.sub, "history/countries/CCC.txt", "sub")

    def _activate(self):
        from mod_stack import from_paths, set_active_stack
        set_active_stack(from_paths(
            sub_mod=self.sub, mod_paths=[self.base], vanilla=self.van,
            submod_name="子mod"))

    def test_state_build_ops_routes_through_stack(self):
        from state_build_ops import ensure_file_in_mod
        self._activate()
        # 子 mod 已有 → 直接用
        p1, c1 = ensure_file_in_mod("", "", "history/countries/CCC.txt")
        self.assertFalse(c1)
        self.assertTrue(p1.startswith(self.sub))
        # 底层有 → 复制上来
        p2, c2 = ensure_file_in_mod("", "", "history/countries/AAA.txt")
        self.assertTrue(c2)
        self.assertTrue(p2.startswith(self.sub))
        with open(p2, encoding="utf-8") as f:
            self.assertEqual(f.read(), "base")
        # 原版有 → 复制上来
        p3, c3 = ensure_file_in_mod("", "", "history/countries/BBB.txt")
        self.assertTrue(c3)
        self.assertTrue(p3.startswith(self.sub))

    def test_ai_loader_scan_files_stack_aware(self):
        import mod_stack as ms
        from ai_loader import _scan_files
        _put(self.base, "common/ai_strategy/x.txt", "b")
        _put(self.van, "common/ai_strategy/v.txt", "v")
        _put(self.sub, "common/ai_strategy/s.txt", "s")
        self._activate()
        got = {os.path.basename(p) for p in
               _scan_files("", "", "common/ai_strategy")}
        self.assertEqual(got, {"x.txt", "v.txt", "s.txt"})
        # 传统模式不受影响（参数为空 → 空结果）
        ms.clear_active_stack()
        self.assertEqual(_scan_files("", "", "common/ai_strategy"), [])


class TestWorkbenchIterRelFiles(unittest.TestCase):
    def setUp(self):
        from mod_stack import clear_active_stack
        clear_active_stack()
        self.addCleanup(clear_active_stack)
        self.sub, self.base = _mk("w_sub"), _mk("w_base")
        _put(self.sub, "common/national_focus/sub_only.txt", "s")
        _put(self.base, "common/national_focus/base_only.txt", "b")
        _put(self.base, "common/national_focus/both.txt", "b")
        _put(self.sub, "common/national_focus/both.txt", "s")

    def _activate(self):
        from mod_stack import ModLayer, ModStack, set_active_stack
        set_active_stack(ModStack([
            ModLayer("子mod", self.sub, True, "submod"),
            ModLayer("底层", self.base, False, "mod"),
        ]))

    def _names(self, mod_path=""):
        from workbench import WorkbenchDock
        return {os.path.basename(p) for p in WorkbenchDock._iter_rel_files(
            mod_path, ("common/national_focus",), (".txt",))}

    def test_merged_view_without_stack(self):
        # 未激活：只扫传入的 mod_path（指向子 mod 目录时只见子 mod 文件）
        self.assertEqual(self._names(self.sub),
                         {"sub_only.txt", "both.txt"})

    def test_merged_view_with_stack(self):
        self._activate()
        self.assertEqual(self._names(""),
                         {"sub_only.txt", "base_only.txt", "both.txt"})

    def test_top_layer_wins_for_same_rel(self):
        self._activate()
        from workbench import WorkbenchDock
        paths = list(WorkbenchDock._iter_rel_files(
            "", ("common/national_focus",), (".txt",)))
        by_name = {os.path.basename(p): p for p in paths}
        self.assertTrue(by_name["both.txt"].startswith(self.sub))


class TestSubmodWizardUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        """用户目录（sqlite 播放集 1 个含 2 mod）+ 默认 mod 目录。"""
        from playset_loader import DLC_LOAD_PLAYSET_ID
        user = _mk("user")
        dirA, dirB = _mk("baseA"), _mk("baseB")
        _put(user, "dlc_load.json", json.dumps({"enabled_mods": []}))
        db = os.path.join(user, "launcher-v2.sqlite")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE playsets (id TEXT, name TEXT, "
                     "isActive INTEGER)")
        conn.execute("CREATE TABLE playsets_mods (playsetId TEXT, "
                     "modId TEXT, enabled INTEGER, position INTEGER)")
        conn.execute("CREATE TABLE mods (id TEXT, gameRegistryId TEXT, "
                     "dirPath TEXT, source TEXT, status TEXT)")
        conn.execute("INSERT INTO playsets VALUES ('ps1', '测试播放集', 0)")
        conn.execute("INSERT INTO playsets_mods VALUES ('ps1','m1',1,0)")
        conn.execute("INSERT INTO playsets_mods VALUES ('ps1','m2',1,1)")
        conn.execute("INSERT INTO mods VALUES ('m1','mod/a.mod',?,"
                     "'local','ready')", (dirA,))
        conn.execute("INSERT INTO mods VALUES ('m2','mod/b.mod',?,"
                     "'steam','ready')", (dirB,))
        conn.commit()
        conn.close()
        os.makedirs(os.path.join(user, "mod"))
        _put(user, "mod/a.mod", 'name="底层A"\npath="%s"\n'
             % dirA.replace("\\", "/"))
        _put(user, "mod/b.mod", 'name="底层B"\npath="%s"\n'
             % dirB.replace("\\", "/"))
        return user, dirA, dirB, DLC_LOAD_PLAYSET_ID

    def test_wizard_end_to_end(self):
        from submod_wizard import SubmodWizard
        user, dirA, dirB, _dlc = self._make_env()
        mod_root = _mk("mods_root")
        activated = []

        def activate_cb(submod_path, name, base_paths):
            activated.append((submod_path, name, base_paths))

        wiz = SubmodWizard(settings={"mod_folder_path": mod_root,
                                     "mod_file_path": mod_root},
                           user_dir=user, activate_cb=activate_cb)
        wiz.show()
        self.app.processEvents()
        self.assertEqual(wiz.playset_combo.count(), 2)

        # 进入第 2 页：装载 mod 列表（默认选 dlc_load → 空集）
        wiz._on_page_changed(1)
        self.assertEqual(wiz.mods_list.count(), 0)
        # 切换到 sqlite 播放集再装载
        idx = next(i for i in range(wiz.playset_combo.count())
                   if wiz.playset_combo.itemData(i) == "ps1")
        wiz.playset_combo.setCurrentIndex(idx)
        wiz._on_page_changed(1)
        self.assertEqual(wiz.mods_list.count(), 2)
        self.assertEqual(wiz.selected_base_paths(), [dirA, dirB])

        # 第 3 页：填写并 accept（mod_folder_path 来自 settings，无弹窗）
        wiz.name_edit.setText("我的子mod")
        wiz.folder_edit.setText("submod_ui")
        wiz.accept()
        self.app.processEvents()
        self.assertEqual(len(activated), 1)
        sub_path, name, base_paths = activated[0]
        self.assertEqual(name, "我的子mod")
        self.assertEqual(base_paths, [dirA, dirB])
        self.assertTrue(os.path.isfile(os.path.join(
            mod_root, "submod_ui.mod")))
        self.assertTrue(os.path.isfile(os.path.join(
            sub_path, "descriptor.mod")))


class TestResolveWritePath(unittest.TestCase):
    """直接写场景（国家建立/电台）的层栈写路径解析。"""

    def setUp(self):
        from mod_stack import clear_active_stack
        clear_active_stack()
        self.addCleanup(clear_active_stack)
        self.sub, self.base = _mk("wp_sub"), _mk("wp_base")

    def test_active_routes_to_submod(self):
        from mod_stack import ModLayer, ModStack, resolve_write_path
        from mod_stack import set_active_stack
        set_active_stack(ModStack([
            ModLayer("子mod", self.sub, True, "submod"),
            ModLayer("底层", self.base, False, "mod")]))
        got = resolve_write_path(self.base, "common/countries/AAA.txt")
        self.assertEqual(got, os.path.join(self.sub, "common",
                                           "countries", "AAA.txt"))

    def test_inactive_joins_mod_path(self):
        from mod_stack import resolve_write_path
        got = resolve_write_path(self.base, "common/countries/AAA.txt")
        self.assertEqual(got, os.path.join(self.base, "common", "countries",
                                           "AAA.txt"))

    def test_country_setup_writes_into_submod(self):
        from mod_stack import ModLayer, ModStack, set_active_stack
        from mod_stack import clear_active_stack
        from country_setup_dialog import create_new_country_files
        set_active_stack(ModStack([
            ModLayer("子mod", self.sub, True, "submod"),
            ModLayer("底层", self.base, False, "mod")]))
        created = create_new_country_files(
            self.base, "AAA", ["common/countries", "common/country_tags"],
            game_path=None)
        self.assertIn("common/countries/AAA.txt", created)
        self.assertTrue(os.path.isfile(os.path.join(
            self.sub, "common", "countries", "AAA.txt")))
        self.assertFalse(os.path.isfile(os.path.join(
            self.base, "common", "countries", "AAA.txt")))
        clear_active_stack()


class TestSubmodMcpTools(unittest.TestCase):
    """MCP 子 mod 工具（ApiCore.PlaysetMixin）契约。"""

    def _make_fixture(self):
        user = _mk("mcp_user")
        dirA, dirB = _mk("mcp_A"), _mk("mcp_B")
        _put(dirA, "common/ai_strategy/x.txt", "a")
        _put(dirB, "common/ai_strategy/y.txt", "b")
        _put(dirA, "interface/base_a.gfx", "gfx")
        _put(user, "dlc_load.json", json.dumps(
            {"enabled_mods": ["mod/a.mod", "mod/b.mod"]}))
        os.makedirs(os.path.join(user, "mod"), exist_ok=True)
        _put(user, "mod/a.mod", 'name="底层A"\npath="%s"\n'
             % dirA.replace("\\", "/"))
        _put(user, "mod/b.mod", 'name="底层B"\npath="%s"\n'
             % dirB.replace("\\", "/"))
        mod_root = _mk("mcp_mods")
        return user, dirA, dirB, mod_root

    def _core(self):
        from api_server import ApiCore
        return ApiCore(mod_path="", game_path="")

    def tearDown(self):
        from mod_stack import clear_active_stack
        clear_active_stack()

    def test_submod_create_activate_and_routing(self):
        user, dirA, dirB, mod_root = self._make_fixture()
        core = self._core()
        r = core.submod_create({
            "submod_name": "MCP子mod", "folder_name": "submod_mcp",
            "base_names": ["底层A", "底层B"],
            "user_dir": user, "mod_folder_path": mod_root,
            "mod_file_path": mod_root,
            "activate": True, "persist": False})
        self.assertTrue(r["ok"])
        self.assertTrue(os.path.isfile(r["mod_file"]))
        self.assertTrue(os.path.isfile(os.path.join(
            r["submod_path"], "descriptor.mod")))
        self.assertEqual(r["base_names"], ["底层A", "底层B"])
        self.assertTrue(r["activated"])
        self.assertEqual([l["kind"] for l in r["layers"]],
                         ["submod", "mod", "mod"])

        # 激活后写路由：ensure_file_in_mod 落子 mod
        from state_build_ops import ensure_file_in_mod
        p, copied = ensure_file_in_mod("", "", "common/ai_strategy/x.txt")
        self.assertTrue(copied)
        self.assertTrue(p.startswith(r["submod_path"]))
        # 读路由：ai_loader 合并视图
        from ai_loader import _scan_files
        names = {os.path.basename(q) for q in
                 _scan_files("", "", "common/ai_strategy")}
        self.assertEqual(names, {"x.txt", "y.txt"})

        # 状态回读
        st = core.submod_status({})
        self.assertTrue(st["active"])
        self.assertEqual(st["submod_path"], r["submod_path"])
        self.assertEqual(len(st["layers"]), 3)

        # 退出
        self.assertTrue(core.submod_exit({})["ok"])
        from mod_stack import active_stack
        self.assertIsNone(active_stack())
        self.assertFalse(core.submod_status({})["active"])

    def test_submod_create_read_all_and_base_paths(self):
        user, dirA, dirB, mod_root = self._make_fixture()
        core = self._core()
        r = core.submod_create({
            "submod_name": "仅勾选", "base_names": ["底层B"],
            "read_all": False, "user_dir": user,
            "mod_folder_path": mod_root, "mod_file_path": mod_root,
            "activate": True, "persist": False})
        self.assertEqual(r["base_names"], ["底层B"])
        self.assertEqual(r["read_paths"], [dirB])

        # 显式 base_paths 优先，且缺失的 base_names 报错（不写盘）
        core2 = self._core()
        with self.assertRaises(ValueError):
            core2.submod_create({
                "submod_name": "会失败", "base_names": ["不存在"],
                "user_dir": user, "mod_folder_path": mod_root,
                "mod_file_path": mod_root, "activate": False})
        r2 = core2.submod_create({
            "submod_name": "显式路径", "base_paths": [dirA],
            "read_all": False, "user_dir": user,
            "mod_folder_path": mod_root, "mod_file_path": mod_root,
            "activate": False})
        self.assertEqual(r2["base_names"], ["底层A"])
        self.assertFalse(r2["activated"])

    def test_submod_activate_missing_path_raises(self):
        core = self._core()
        with self.assertRaises(ValueError):
            core.submod_activate({"submod_path": ""})

    def test_persist_writes_settings_fields(self):
        import unittest.mock as mock
        user, dirA, dirB, mod_root = self._make_fixture()
        import project_paths
        fake_root = _mk("persist_root")
        real_settings = os.path.join(PROJECT_ROOT_SNAPSHOT, "settings.json")
        fake_settings = os.path.join(fake_root, "settings.json")
        with open(fake_settings, "w", encoding="utf-8") as f:
            json.dump({"ui_mode": "workbench", "HOI4_path": "X:/game"}, f)
        core = self._core()
        with mock.patch.object(project_paths, "PROJECT_ROOT", fake_root):
            r = core.submod_create({
                "submod_name": "持久化子mod", "folder_name": "sub_p",
                "base_paths": [dirA], "read_all": False,
                "user_dir": user, "mod_folder_path": mod_root,
                "mod_file_path": mod_root,
                "activate": True, "persist": True})
        self.assertTrue(r["activated"])
        with open(fake_settings, encoding="utf-8") as f:
            persisted = json.load(f)
        self.assertEqual(persisted["ui_mode"], "workbench")   # 其余字段保留
        self.assertEqual(persisted["HOI4_path"], "X:/game")
        self.assertTrue(persisted["submod_active"])
        self.assertEqual(persisted["submod_path"], r["submod_path"])

    def test_playset_conflict_scan_via_core(self):
        user, dirA, dirB, _mod_root = self._make_fixture()
        _put(dirA, "common/x/shared.txt", "A")
        _put(dirB, "common/x/shared.txt", "B")
        core = self._core()
        r = core.playset_conflict_scan({"user_dir": user})
        self.assertTrue(r["ok"])
        self.assertEqual(r["playset"], "dlc_load（最近启动）")
        self.assertGreaterEqual(
            r["counts"]["by_kind"].get("file_shadow", 0), 1)


PROJECT_ROOT_SNAPSHOT = os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))


if __name__ == "__main__":
    unittest.main()
