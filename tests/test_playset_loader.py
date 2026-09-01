"""播放集读取层契约（playset_loader，阶段A 共用底座）。

覆盖：
- hoi4_user_dir 推断（显式 hoi4_user_path > mod_file_path 父目录 > 标记文件校验）
- list_playsets：dlc_load 恒在列首 + sqlite 播放集（isActive 优先）
- load_playset(dlc_load)：数组顺序 = 加载顺序；.mod 字段解析
- load_playset(sqlite)：enabled 过滤、position 排序、dirPath/.mod path 双源、
  descriptor 缺失容错（descriptor_ok=False 不炸）
- sqlite 损坏 / 指定播放集不存在 → 回退 dlc_load
- 中文/空格路径只读 URI 打开
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from playset_loader import (  # noqa: E402
    DLC_LOAD_PLAYSET_ID,
    PlaysetMod,
    hoi4_user_dir,
    list_playsets,
    load_playset,
)
from mod_descriptor_loader import format_mod_entries, build_entries  # noqa: E402


def _mk(prefix):
    return tempfile.mkdtemp(prefix="dsh_playset_" + prefix)


def _write(path, text, encoding="utf-8"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(text)
    return path


def _mod_descriptor(name, path, replace_paths=(), deps=(), version="1.19.*"):
    fields = {
        "name": name,
        "path": path,
        "supported_version": version,
        "tags": ["Balance"],
        "replace_path": list(replace_paths),
        "dependencies": list(deps),
    }
    return format_mod_entries(build_entries(fields))


def _make_sqlite(user_dir, playsets, pm_rows, mods_rows):
    """建一个最小 launcher-v2.sqlite（表结构与真实库一致）。"""
    db = os.path.join(user_dir, "launcher-v2.sqlite")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE playsets (id TEXT, name TEXT, isActive INTEGER)")
    conn.execute("CREATE TABLE playsets_mods (playsetId TEXT, modId TEXT, "
                 "enabled INTEGER, position INTEGER)")
    conn.execute("CREATE TABLE mods (id TEXT, gameRegistryId TEXT, "
                 "dirPath TEXT, source TEXT, status TEXT)")
    conn.executemany("INSERT INTO playsets VALUES (?,?,?)", playsets)
    conn.executemany("INSERT INTO playsets_mods VALUES (?,?,?,?)", pm_rows)
    conn.executemany("INSERT INTO mods VALUES (?,?,?,?,?)", mods_rows)
    conn.commit()
    conn.close()


class TestHoi4UserDir(unittest.TestCase):
    def test_explicit_key_wins(self):
        d = _mk("explicit")
        _write(os.path.join(d, "dlc_load.json"), '{"enabled_mods":[]}')
        other = _mk("other")
        self.assertEqual(hoi4_user_dir({
            "hoi4_user_path": d, "mod_file_path": other}), d)

    def test_infer_from_mod_file_path(self):
        user = _mk("user")
        moddir = os.path.join(user, "mod")
        os.makedirs(moddir)
        _write(os.path.join(user, "launcher-v2.sqlite"), "x")
        self.assertEqual(
            hoi4_user_dir({"mod_file_path": os.path.join(moddir, "")}), user)

    def test_candidate_without_markers_rejected(self):
        d = _mk("nomark")
        moddir = os.path.join(d, "mod")
        os.makedirs(moddir)
        self.assertEqual(hoi4_user_dir({"mod_file_path": moddir}), "")

    def test_empty_settings(self):
        self.assertEqual(hoi4_user_dir({}), "")
        self.assertEqual(hoi4_user_dir(None), "")


class TestListPlaysets(unittest.TestCase):
    def test_dlc_load_first_then_sqlite_active_first(self):
        user = _mk("list")
        _write(os.path.join(user, "dlc_load.json"), '{"enabled_mods":[]}')
        _make_sqlite(
            user,
            [("id-b", "普通集", 0), ("id-a", "活动集", 1)],
            [], [])
        got = list_playsets(user)
        self.assertEqual(got[0]["id"], DLC_LOAD_PLAYSET_ID)
        self.assertEqual(got[0]["source"], "dlc_load")
        ids = [s["id"] for s in got[1:]]
        self.assertEqual(ids, ["id-a", "id-b"])   # isActive 优先

    def test_sqlite_corrupt_falls_back_to_dlc_only(self):
        user = _mk("corrupt")
        _write(os.path.join(user, "dlc_load.json"), '{"enabled_mods":[]}')
        _write(os.path.join(user, "launcher-v2.sqlite"), "not a sqlite file")
        got = list_playsets(user)
        self.assertEqual([s["source"] for s in got], ["dlc_load"])

    def test_chinese_and_space_path(self):
        base = _mk("zh")
        user = os.path.join(base, "枯月 流魂", "Hearts of Iron IV")
        os.makedirs(user)
        _write(os.path.join(user, "dlc_load.json"), '{"enabled_mods":[]}')
        _make_sqlite(user, [("p1", "中文播放集", 0)], [], [])
        got = list_playsets(user)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[1]["name"], "中文播放集")


class TestLoadPlaysetDlcLoad(unittest.TestCase):
    def test_array_order_is_load_order(self):
        user = _mk("dlc")
        modA = os.path.join(user, "mod", "a.mod")
        modB = os.path.join(user, "mod", "b.mod")
        dirA = os.path.join(user, "mods", "a")
        dirB = os.path.join(user, "mods", "b")
        os.makedirs(dirA)
        os.makedirs(dirB)
        _write(modA, _mod_descriptor("ModA", dirA, replace_paths=["common/x"]))
        _write(modB, _mod_descriptor("ModB", dirB, deps=("ModA",)))
        _write(os.path.join(user, "dlc_load.json"), json.dumps({
            "enabled_mods": ["mod/b.mod", "mod/a.mod"]}))
        ps = load_playset(user)
        self.assertEqual(ps.source, "dlc_load")
        self.assertEqual([m.name for m in ps.mods], ["ModB", "ModA"])
        self.assertEqual([m.position for m in ps.mods], [0, 1])
        a = ps.mods[1]
        self.assertEqual(a.content_dir, os.path.normpath(dirA))
        self.assertEqual(a.replace_paths, ["common/x"])
        self.assertEqual(ps.mods[0].dependencies, ["ModA"])
        self.assertTrue(all(m.descriptor_ok for m in ps.mods))

    def test_missing_mod_file_marked(self):
        user = _mk("dmiss")
        _write(os.path.join(user, "dlc_load.json"),
               '{"enabled_mods":["mod/nope.mod"]}')
        ps = load_playset(user)
        self.assertEqual(len(ps.mods), 1)
        self.assertFalse(ps.mods[0].descriptor_ok)
        self.assertEqual(ps.mods[0].content_dir, "")
        self.assertEqual(ps.mods[0].name, "nope")   # 文件名兜底

    def test_absolute_registry_path(self):
        user = _mk("dabs")
        outside = os.path.join(_mk("dabs_out"), "abs.mod")
        d = _mk("dabs_dir")            # mkdtemp 已建目录，勿重复 makedirs
        _write(outside, _mod_descriptor("AbsMod", d))
        _write(os.path.join(user, "dlc_load.json"), json.dumps(
            {"enabled_mods": [outside]}))
        ps = load_playset(user)
        self.assertEqual(ps.mods[0].name, "AbsMod")


class TestLoadPlaysetSqlite(unittest.TestCase):
    def setUp(self):
        self.user = _mk("sq")
        self.dirA = os.path.join(self.user, "mods", "a")
        os.makedirs(self.dirA)
        _write(os.path.join(self.user, "dlc_load.json"), '{"enabled_mods":[]}')
        _write(os.path.join(self.user, "mod", "b.mod"),
               _mod_descriptor("ModB", self.dirA))
        _write(os.path.join(self.user, "mod", "c.mod"),
               _mod_descriptor("ModC", self.dirA))
        _make_sqlite(
            self.user,
            [("ps1", "测试集", 0)],
            [("ps1", "m-b", 1, 5),      # enabled, position=5
             ("ps1", "m-c", 1, 2),      # enabled, position=2（应排前）
             ("ps1", "m-d", 0, 0)],     # disabled → 不出现
            [("m-b", "mod/b.mod", "", "local", "ready_to_play"),
             ("m-c", "mod/c.mod", self.dirA, "local", "ready_to_play"),
             ("m-d", "mod/d.mod", self.dirA, "local", "ready_to_play")])

    def test_enabled_only_sorted_by_position(self):
        ps = load_playset(self.user, "ps1")
        self.assertEqual(ps.source, "sqlite")
        names = [m.name for m in ps.mods]
        self.assertEqual(names, ["ModC", "ModB"])   # c=position2 在前
        self.assertEqual([m.position for m in ps.mods], [2, 5])
        self.assertEqual(ps.mods[0].mod_id, "m-c")
        self.assertEqual(ps.mods[1].mod_id, "m-b")
        # c 走 mods.dirPath，b 走 .mod path= —— 双源都落到同一目录
        self.assertEqual(ps.mods[0].content_dir, os.path.normpath(self.dirA))
        self.assertEqual(ps.mods[1].content_dir, os.path.normpath(self.dirA))

    def test_unknown_playset_falls_back_to_dlc_load(self):
        ps = load_playset(self.user, "no-such-id")
        self.assertEqual(ps.source, "dlc_load")

    def test_status_and_source_from_mods_table(self):
        self.user2 = _mk("sq2")
        _write(os.path.join(self.user2, "dlc_load.json"), '{"enabled_mods":[]}')
        _make_sqlite(
            self.user2, [("ps2", "s2", 0)],
            [("ps2", "m-x", 1, 0)],
            [("m-x", "", "Z:\\gone", "steam", "installation_failed")])
        ps = load_playset(self.user2, "ps2")
        m = ps.mods[0]
        self.assertEqual(m.status, "installation_failed")
        self.assertEqual(m.source, "steam")
        self.assertEqual(m.content_dir, "")   # dirPath 不存在 → 空

    def test_position_none_uses_row_order(self):
        user = _mk("sq3")
        _write(os.path.join(user, "dlc_load.json"), '{"enabled_mods":[]}')
        _make_sqlite(user, [("ps3", "s3", 0)],
                     [("ps3", "m1", 1, None), ("ps3", "m2", 1, None)],
                     [("m1", "mod/one.mod", "", "", ""),
                      ("m2", "mod/two.mod", "", "", "")])
        for tag in ("one", "two"):
            _write(os.path.join(user, "mod", tag + ".mod"),
                   'name="%s"\nsupported_version="1.19.*"\n' % tag)
        ps = load_playset(user, "ps3")
        self.assertEqual([m.name for m in ps.mods], ["one", "two"])
        self.assertEqual([m.position for m in ps.mods], [0, 1])


class TestPlaysetDataclass(unittest.TestCase):
    def test_defaults(self):
        m = PlaysetMod()
        self.assertEqual(m.replace_paths, [])
        self.assertTrue(m.descriptor_ok)


if __name__ == "__main__":
    unittest.main()
