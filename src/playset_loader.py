"""播放集（Playset）读取层 —— 多 mod 冲突检查 / 子 mod 制作共用底座。

数据源（只读，绝不写入）：
  1. launcher-v2.sqlite（HOI4 用户文档目录）
       playsets(id, name, isActive)
       playsets_mods(playsetId, modId, enabled, position)   # position = 加载顺序
       mods(id, gameRegistryId, dirPath, source, status)
  2. dlc_load.json（同目录）：{"enabled_mods": ["mod/xxx.mod", ...]}
       数组顺序即游戏实际加载顺序（越靠后越晚加载、覆盖优先级越高），
       启动器每次以某播放集启动游戏时写入 —— 是「最近一次启动集」的 ground truth。
  3. .mod 描述文件（mod_file_path）：name/path/replace_path/dependencies/…
       解析复用 mod_descriptor_loader。

语义约定（与游戏加载行为对齐）：
  - Playset.mods 按 position 升序 = 游戏加载顺序（先 → 后）；
  - sqlite 只读打开（URI mode=ro），被游戏占用/损坏时回退 dlc_load.json；
  - status='installation_failed' 但目录在盘上的本地 mod 照常纳入（实测存在）；
  - 同 content_dir / 同 registry_path 的重复条目**不去重**，保留给
    conflict_scan 的 L0 重复注册检测。

本模块零写入（sqlite 只读 URI + json 读），无 PyQt 依赖。
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from urllib.parse import quote

from mod_descriptor_loader import extract_fields, parse_mod_entries

# dlc_load.json 兜底播放集的伪 id（list_playsets / load_playset 共用）
DLC_LOAD_PLAYSET_ID = "__dlc_load__"

_SQLITE_NAME = "launcher-v2.sqlite"
_DLC_LOAD_NAME = "dlc_load.json"


@dataclass
class PlaysetMod:
    """播放集中的一个 mod 条目（描述符字段已解析）。"""

    registry_path: str = ""      # "mod/xxx.mod"（相对用户文档目录）或绝对路径
    content_dir: str = ""        # 内容目录绝对路径（可为空 = 无法解析）
    name: str = ""               # descriptor name（缺省用文件名）
    position: int = 0            # 加载顺序，越大越晚加载
    source: str = ""             # "steam" | "local" | ""
    status: str = ""             # launcher 数据库状态（仅展示用）
    replace_paths: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    supported_version: str = ""
    remote_file_id: str = ""
    tags: list = field(default_factory=list)
    descriptor_ok: bool = True   # .mod / descriptor.mod 是否成功解析
    mod_id: str = ""             # launcher 数据库 mods.id（sqlite 源才有）


@dataclass
class Playset:
    """一个播放集：有序 mod 列表。"""

    id: str = ""
    name: str = ""
    source: str = ""             # "sqlite" | "dlc_load"
    mods: list = field(default_factory=list)   # [PlaysetMod]，已按 position 升序


# ---------- 用户文档目录推断 ----------

def hoi4_user_dir(settings) -> str:
    """从设置推断 HOI4 用户文档目录（含 launcher-v2.sqlite / dlc_load.json）。

    优先级：settings["hoi4_user_path"]（显式） > mod_file_path 的父目录。
    候选目录必须真实存在标记文件，否则返回 ""（调用方提示手动配置）。
    """
    if not isinstance(settings, dict):
        return ""
    explicit = (settings.get("hoi4_user_path") or "").strip()
    if explicit and _looks_like_user_dir(explicit):
        return os.path.normpath(explicit)
    mod_file_path = (settings.get("mod_file_path") or "").strip()
    if mod_file_path:
        parent = os.path.dirname(os.path.normpath(mod_file_path))
        if parent and _looks_like_user_dir(parent):
            return parent
    return ""


def _looks_like_user_dir(path) -> bool:
    if not path or not os.path.isdir(path):
        return False
    return any(os.path.isfile(os.path.join(path, marker))
               for marker in (_SQLITE_NAME, _DLC_LOAD_NAME, "game_data.json"))


# ---------- dlc_load.json ----------

def _read_dlc_load(user_dir) -> list:
    """读 dlc_load.json 的 enabled_mods（保序）。损坏/缺失返回 []。"""
    fp = os.path.join(user_dir, _DLC_LOAD_NAME)
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return []
    mods = data.get("enabled_mods") if isinstance(data, dict) else None
    if not isinstance(mods, list):
        return []
    return [str(m) for m in mods if str(m).strip()]


# ---------- sqlite（只读） ----------

def _ro_uri(path) -> str:
    """构造 sqlite 只读 URI。非 ASCII/空格经 percent-encode，
    SQLite 会解码 %HH，避免中文用户名路径打不开。"""
    p = str(path).replace("\\", "/")
    return "file:" + quote(p, safe="/:") + "?mode=ro"


def _open_ro(db_path):
    """只读打开 sqlite；失败返回 None（调用方回退 dlc_load）。"""
    if not os.path.isfile(db_path):
        return None
    try:
        conn = sqlite3.connect(_ro_uri(db_path), uri=True, timeout=1.0)
        conn.execute("SELECT 1")
        return conn
    except Exception:
        return None


def _q(cur, sql, args=()):
    """防御性查询：表/列缺失等异常一律返回空结果。"""
    try:
        return cur.execute(sql, args).fetchall()
    except Exception:
        return []


def _load_sqlite_mods_map(conn) -> dict:
    """{gameRegistryId: {dir_path, source, status, mod_id}}（含 registry 缺失行）。"""
    cur = conn.cursor()
    rows = _q(cur, "SELECT id, gameRegistryId, dirPath, source, status FROM mods")
    out = {}
    for mod_id, registry, dir_path, source, status in rows:
        out[str(mod_id)] = {
            "registry": str(registry or ""),
            "dir_path": str(dir_path or ""),
            "source": str(source or ""),
            "status": str(status or ""),
            "mod_id": str(mod_id),
        }
    return out


def _registry_from_mod_row(row) -> str:
    registry = str(row.get("registry") or "")
    return registry


# ---------- 播放集列举 / 加载 ----------

def list_playsets(user_dir) -> list:
    """列举可用播放集。返回 [{"id","name","is_active","source"}]。

    dlc_load.json 恒在列首（"最近启动"）；其后为 sqlite 播放集
    （isActive 优先，其余按库内顺序）。sqlite 不可用时只返回 dlc_load。
    """
    out = [{
        "id": DLC_LOAD_PLAYSET_ID,
        "name": "dlc_load（最近启动）",
        "is_active": True,
        "source": "dlc_load",
    }]
    if not user_dir or not os.path.isdir(user_dir):
        return out
    conn = _open_ro(os.path.join(user_dir, _SQLITE_NAME))
    if conn is None:
        return out
    try:
        cur = conn.cursor()
        rows = _q(cur, "SELECT id, name, isActive FROM playsets")
        sqlite_sets = []
        for pid, name, active in rows:
            sqlite_sets.append({
                "id": str(pid),
                "name": str(name or "(未命名)"),
                "is_active": bool(active),
                "source": "sqlite",
            })
        sqlite_sets.sort(key=lambda s: (not s["is_active"],))
        out.extend(sqlite_sets)
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return out


def load_playset(user_dir, playset_id=None) -> Playset:
    """加载一个播放集（mods 已按加载顺序升序）。

    Args:
        playset_id: sqlite playsets.id；None / DLC_LOAD_PLAYSET_ID = dlc_load.json。
    """
    if playset_id and playset_id != DLC_LOAD_PLAYSET_ID:
        ps = _load_sqlite_playset(user_dir, playset_id)
        if ps is not None:
            return ps
        # 指定的播放集读不到 → 回退 dlc_load（保证调用方总有可用结果）
    return _load_dlc_load_playset(user_dir)


def _load_dlc_load_playset(user_dir) -> Playset:
    ps = Playset(id=DLC_LOAD_PLAYSET_ID, name="dlc_load（最近启动）",
                 source="dlc_load")
    mods_map = _sqlite_mods_map_safe(user_dir)
    for i, registry in enumerate(_read_dlc_load(user_dir)):
        ps.mods.append(_build_mod_entry(user_dir, registry, i, mods_map))
    return ps


def _sqlite_mods_map_safe(user_dir) -> dict:
    conn = _open_ro(os.path.join(user_dir, _SQLITE_NAME)) if user_dir else None
    if conn is None:
        return {}
    try:
        return _load_sqlite_mods_map(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _load_sqlite_playset(user_dir, playset_id) -> Playset | None:
    conn = _open_ro(os.path.join(user_dir, _SQLITE_NAME)) if user_dir else None
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        rows = _q(cur, "SELECT id, name FROM playsets WHERE id=?", (playset_id,))
        if not rows:
            return None
        ps = Playset(id=str(rows[0][0]), name=str(rows[0][1] or "(未命名)"),
                     source="sqlite")
        mods_map = _load_sqlite_mods_map(conn)
        pm_rows = _q(cur,
                     "SELECT pm.modId, pm.position, m.gameRegistryId, "
                     "m.dirPath, m.source, m.status "
                     "FROM playsets_mods pm LEFT JOIN mods m ON m.id = pm.modId "
                     "WHERE pm.playsetId=? AND pm.enabled=1 ORDER BY pm.position",
                     (playset_id,))
        for i, (mod_id, position, registry, dir_path, source,
                status) in enumerate(pm_rows):
            registry = str(registry or "")
            if not registry:
                # mods 表缺失（极端情况）：用 modId 反查 map
                info = mods_map.get(str(mod_id)) or {}
                registry = info.get("registry", "")
            entry = _build_mod_entry(
                user_dir, registry,
                position if position is not None else i, mods_map)
            entry.mod_id = str(mod_id or "")
            if not entry.source:
                entry.source = str(source or "")
            if not entry.status:
                entry.status = str(status or "")
            if not entry.content_dir and dir_path \
                    and os.path.isdir(str(dir_path)):
                entry.content_dir = str(dir_path)
            ps.mods.append(entry)
        return ps
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _build_mod_entry(user_dir, registry, position, mods_map) -> PlaysetMod:
    """由 registry 路径构建 PlaysetMod：dirPath 优先，.mod path 兜底。"""
    entry = PlaysetMod(registry_path=registry, position=int(position or 0))
    info = {}
    for row in (mods_map or {}).values():
        if row.get("registry") == registry:
            info = row
            break
    entry.source = info.get("source", "")
    entry.status = info.get("status", "")
    entry.mod_id = info.get("mod_id", "")

    mod_fp = registry if os.path.isabs(registry) \
        else os.path.join(user_dir, registry)
    fields = {}
    if mod_fp and os.path.isfile(mod_fp):
        fields = _parse_descriptor_file(mod_fp)
    else:
        entry.descriptor_ok = False

    if fields.get("path") and os.path.isdir(fields["path"]):
        entry.content_dir = os.path.normpath(fields["path"])
    if info.get("dir_path") and os.path.isdir(info["dir_path"]):
        if not entry.content_dir:
            entry.content_dir = os.path.normpath(info["dir_path"])
        # 内容目录里的 descriptor.mod 补缺字段（创意工坊 .mod 偶缺 name）
        desc_fp = os.path.join(entry.content_dir, "descriptor.mod")
        if not fields.get("name") and os.path.isfile(desc_fp):
            fields2 = _parse_descriptor_file(desc_fp)
            for key in ("name", "supported_version", "remote_file_id"):
                if not fields.get(key):
                    fields[key] = fields2.get(key, "")

    entry.name = fields.get("name") or ""
    if not entry.name:
        entry.name = os.path.basename(registry or "").rsplit(".", 1)[0]
    entry.replace_paths = list(fields.get("replace_path") or [])
    entry.dependencies = list(fields.get("dependencies") or [])
    entry.supported_version = fields.get("supported_version") or ""
    entry.remote_file_id = fields.get("remote_file_id") or ""
    entry.tags = list(fields.get("tags") or [])
    return entry


def _parse_descriptor_file(fp) -> dict:
    """解析 .mod / descriptor.mod 文本，返回 extract_fields 字段（失败返回 {}）。"""
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        return extract_fields(parse_mod_entries(text))
    except Exception:
        return {}
