"""外置 Agent 接口：本地 HTTP API 服务

让外部程序 / AI Agent 通过 HTTP 调用本软件的 mod 制作能力（不依赖 GUI）。

运行形态：
  1. 独立进程：  python api_server.py --mod <mod目录> [--game <游戏目录>] [--port 8765] [--token xxx]
  2. GUI 内嵌：  工具菜单「外部接口…」对话框启动（改动实时刷新界面）

安全：默认仅绑定 127.0.0.1；启动时生成随机 Bearer token（--token 可指定），
      未携带正确 token 的请求一律 401。

端点（JSON）：
  GET    /api/status                         → 服务信息
  GET    /api/types                          → 内容类型列表
  GET    /api/entities?type=&country=&kw=    → 实体列表
  GET    /api/entities/<type>/<id>           → 实体详情（含块文本）
  POST   /api/entities                       → 新建实体 {type,id,country?,content?}
  PUT    /api/entities/<type>/<id>           → 更新实体块 {content}
  DELETE /api/entities/<type>/<id>           → 删除实体
  POST   /api/project                        → 项目级联动（国策+事件+决议+图标+本地化）
  POST   /api/localisation                   → 写本地化词条 {tag, entries:{key:val}}
  POST   /api/validate                       → 校验 mod（本地化缺失/国策引用/未知引用/重复ID）
  GET    /api/templates?type=&usage=         → 模板列表
  GET    /api/files?type=                    → 文件列表
  POST   /api/files                          → 读文件 {path} / 写整文件 {path,content}
  POST   /api/tech_icon                      → 科技图标上传
  GET    /api/icon_manifest                  → 图标清单
  GET    /api/overlay_report                 → 覆盖增量报告
  POST   /api/tools/format_pdx               → PDX 格式化
  GET    /api/tools/vp_loc                   → VP 本地化干跑
  POST   /api/tools/error_log                → 错误日志分析
  POST   /api/tools/register_icon_batch      → 批量补注册图标
  POST   /api/mcp/<tool_name>                → 通用同源工具桥（159 个 MCP 工具均可调用）
  GET    /api/help                           → 端点说明

写操作自动进入撤销管理器（undo_mgr），GUI 内嵌模式下自动刷新界面。
"""
from project_paths import PROJECT_ROOT, project_path

import argparse
import json
import os
import re
import secrets
import sys
import threading
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import icon_ops

from api_core_ext import (
    StatesMixin,
    DesignersMixin,
    AiContentMixin,
    BopMixin,
    LocToolsMixin,
    HealthMixin,
    MediaMixin,
    GeneratorsMixin,
    ProjectMixin,
    RhoGapMixin,
)


ROOT = PROJECT_ROOT
SRC = project_path("src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_PORT = 8765


# ══════════════════════════════════════════════════════════════
# 核心操作逻辑（HTTP / MCP / CLI 共用，不依赖 PyQt 界面）
# ══════════════════════════════════════════════════════════════

def load_settings():
    """读取 settings.json（mod/game 路径）。"""
    try:
        with open(os.path.join(ROOT, "settings.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class ApiCore(StatesMixin, DesignersMixin, AiContentMixin, BopMixin,
             LocToolsMixin, HealthMixin, MediaMixin, GeneratorsMixin,
             ProjectMixin, RhoGapMixin):
    """mod 制作操作核心：输入 dict → 输出 dict。"""

    def __init__(self, mod_path="", game_path=""):
        self.mod_path = mod_path
        self.game_path = game_path
        self._change_callbacks = []
        self._icon_manifest_cache = None

    # ---------- 路径 ----------

    def ensure_mod(self):
        if not self.mod_path or not os.path.isdir(self.mod_path):
            raise ValueError("未配置有效的 mod 目录（请通过 --mod 或 GUI 打开 mod）")

    def on_change(self, callback):
        """注册文件变更回调（GUI 内嵌刷新界面）。"""
        self._change_callbacks.append(callback)

    def _notify_change(self, path):
        for cb in self._change_callbacks:
            try:
                cb(path)
            except Exception:
                pass

    # ---------- 状态 / 类型 ----------

    def status(self):
        self.ensure_mod()
        try:
            from workbench import CONTENT_TYPES
            n_types = len(CONTENT_TYPES)
        except Exception:
            n_types = 0
        return {
            "ok": True,
            "mod_path": self.mod_path,
            "game_path": self.game_path or "",
            "content_types": n_types,
            "service": "hoi4-mod-builder-api",
        }

    def types(self):
        try:
            from workbench import CONTENT_TYPES
            return {"ok": True, "types": [
                {"key": c[0], "name": c[1], "folders": c[3],
                 "exts": [c[5]] if isinstance(c[5], str) else list(c[5] or [])}
                for c in CONTENT_TYPES]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------- 实体 ----------

    def _scan_files(self, type_key):
        """返回类型对应的 (文件夹, 扩展名列表) 与全部文件。"""
        from workbench import WorkbenchDock, CONTENT_TYPES
        folders, exts = [], [".txt"]
        found = False
        for c in CONTENT_TYPES:
            if c[0] == type_key:
                folders = c[3]
                exts = [c[5]] if isinstance(c[5], str) else list(c[5] or [])
                found = True
                break
        if not found:
            raise ValueError(f"未知内容类型: {type_key!r}（可用 /api/types 查看全部类型）")
        files = []
        for rel in folders:
            base = self.mod_path if rel == "." else os.path.join(self.mod_path, rel)
            if not os.path.isdir(base):
                continue
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    if not name.lower().endswith(tuple(exts)):
                        continue
                    files.append(os.path.join(root, name))
        return folders, exts, files

    def list_entities(self, type_key, country="", keyword=""):
        self.ensure_mod()
        from workbench import WorkbenchDock
        _folders, _exts, files = self._scan_files(type_key)
        entities = []
        seen = set()
        for fp in files:
            content = WorkbenchDock._read_file(fp)
            if not content:
                continue
            real = os.path.realpath(fp)
            if real in seen:
                continue
            seen.add(real)
            try:
                es = WorkbenchDock._collect_file_entities(type_key, content, fp)
            except Exception:
                es = []
            for e in es:
                name = e.get("name") or ""
                if not name:
                    continue
                ent = {
                    "id": name,
                    "name": name,
                    "icon": e.get("icon", ""),
                    "country": (e.get("tags") or [""])[0] or "",
                    "file": os.path.relpath(fp, self.mod_path).replace(os.sep, "/"),
                    "range": list(e.get("range", (-1, -1))),
                }
                if country and ent["country"] != country:
                    continue
                if keyword and keyword.lower() not in f"{name} {ent['country']}".lower():
                    continue
                entities.append(ent)
        return {"ok": True, "type": type_key, "count": len(entities), "entities": entities}

    def _find_entity(self, type_key, entity_id):
        """定位实体：返回 (file_path, content, (start, end))。"""
        from workbench import WorkbenchDock
        _folders, _exts, files = self._scan_files(type_key)
        for fp in files:
            content = WorkbenchDock._read_file(fp)
            if not content:
                continue
            try:
                es = WorkbenchDock._collect_file_entities(type_key, content, fp)
            except Exception:
                es = []
            for e in es:
                if (e.get("name") or "") == entity_id:
                    rng = e.get("range", (-1, -1))
                    if rng[0] < 0:
                        continue
                    end = self._block_end(content, rng[0])
                    if end <= rng[0]:
                        # 无花括号实体（赋值式/文件级，如纯 recruit_character、单行 lua、yml）：
                        # 回退到提取范围（整文件），支持整文件读写
                        end = rng[1] if rng[1] > rng[0] else len(content)
                    if end > rng[0]:
                        return fp, content, (rng[0], end)
        return None, None, None

    @staticmethod
    def _block_end(content, start_char):
        """返回实体块起始位置对应的平衡右括号结束位置（含 }）。"""
        i = content.find("{", start_char)
        if i < 0:
            return -1
        depth = 0
        in_str = False
        n = len(content)
        while i < n:
            c = content[i]
            if in_str:
                if c == '"':
                    in_str = False
                i += 1
                continue
            if c == '"':
                in_str = True
            elif c == "#":
                while i < n and content[i] != "\n":
                    i += 1
                continue
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return -1

    def get_entity(self, type_key, entity_id):
        self.ensure_mod()
        fp, content, rng = self._find_entity(type_key, entity_id)
        if not fp:
            return {"ok": False, "error": f"未找到实体 {type_key}/{entity_id}"}
        return {
            "ok": True, "type": type_key, "id": entity_id,
            "file": os.path.relpath(fp, self.mod_path).replace(os.sep, "/"),
            "content": content[rng[0]:rng[1]],
        }

    def _insert_entity_block(self, file_path, content_type, block):
        """写入实体块：character 并入包装块，其余追加末尾（文件/目录不存在则新建）。"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        else:
            content = ""
        if content_type == "character":
            start, end = icon_ops.find_block_range(content, {"characters"})
            if start >= 0 and end > start:
                return content[:end - 1] + block + content[end - 1:]
            return content.rstrip() + "\ncharacters = {\n" + block + "}\n"
        return content.rstrip() + "\n" + block

    def _build_block(self, type_key, entity_id, content=None):
        """生成实体块：有 content 用 content，否则用项目模板/内置骨架。"""
        if content and content.strip():
            return content if content.strip().startswith("\t") \
                else "\t" + content.strip().replace("\n", "\n\t") + "\n"
        try:
            from focus_view import FocusView
            return FocusView._build_entity_block(type_key, entity_id)
        except Exception:
            return f"\t{entity_id} = {{\n\t\t# 新实体\n\t}}\n"

    def create_entity(self, data):
        """新建实体：{type, id, country?, content?}。

        目标文件：优先 country 匹配的现有文件；否则该类型首个文件夹下 <TAG>_ai.txt。
        """
        self.ensure_mod()
        type_key = (data.get("type") or "").strip()
        entity_id = (data.get("id") or "").strip()
        if not type_key or not entity_id:
            raise ValueError("缺少 type 或 id")
        # HOI4 id 允许字母/数字/下划线/点号/连字符/空格（事件 id 常含点如 EX_SOV.1；
        # 文件级实体（国家历史/国家定义）id 为文件名，可能含空格）
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_.\- ]*$", entity_id):
            raise ValueError("实体 id 只能包含字母/数字/下划线/点号/连字符/空格，且不能以数字开头")

        # 目标文件：优先国家匹配，否则类型目录下首个文件，否则新建
        from workbench import WorkbenchDock
        _folders, _exts, files = self._scan_files(type_key)
        target = ""
        country = (data.get("country") or "").strip().upper()
        if country:
            for fp in files:
                content = WorkbenchDock._read_file(fp)
                if country in WorkbenchDock._detect_country_tags(fp, content):
                    target = fp
                    break
        if not target and files:
            target = files[0]
        if not target:
            rel_dir = _folders[0] if _folders and _folders[0] != "." else ""
            rel = os.path.join(rel_dir, f"{country}_ai.txt" if country else "ai_generated.txt")
            target = os.path.join(self.mod_path, rel)

        block = self._build_block(type_key, entity_id, data.get("content"))
        new_content = self._insert_entity_block(target, type_key, block)
        icon_ops.write_file_utf8(target, new_content)
        self._notify_change(target)
        return {
            "ok": True, "type": type_key, "id": entity_id,
            "file": os.path.relpath(target, self.mod_path).replace(os.sep, "/"),
        }

    def update_entity(self, type_key, entity_id, data):
        self.ensure_mod()
        content_text = (data.get("content") or "").strip()
        if not content_text:
            raise ValueError("缺少 content（新的实体块文本）")
        fp, content, rng = self._find_entity(type_key, entity_id)
        if not fp:
            return {"ok": False, "error": f"未找到实体 {type_key}/{entity_id}"}
        new_block = content_text if content_text.startswith("\t") \
            else "\t" + content_text.replace("\n", "\n\t") + "\n"
        new_content = content[:rng[0]] + new_block + content[rng[1]:]
        icon_ops.write_file_utf8(fp, new_content)
        self._notify_change(fp)
        return {"ok": True, "file": os.path.relpath(fp, self.mod_path).replace(os.sep, "/")}

    def delete_entity(self, type_key, entity_id):
        self.ensure_mod()
        fp, content, rng = self._find_entity(type_key, entity_id)
        if not fp:
            return {"ok": False, "error": f"未找到实体 {type_key}/{entity_id}"}
        new_content = content[:rng[0]] + content[rng[1]:]
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)
        icon_ops.write_file_utf8(fp, new_content)
        self._notify_change(fp)
        return {"ok": True, "file": os.path.relpath(fp, self.mod_path).replace(os.sep, "/")}

    # ---------- 项目级联动 ----------

    def list_files(self, type_key):
        """列出类型目录下的全部文件（路径/大小/扩展名），含内容可选。"""
        self.ensure_mod()
        _folders, _exts, files = self._scan_files(type_key)
        out = []
        for fp in files:
            rel = os.path.relpath(fp, self.mod_path).replace(os.sep, "/")
            try:
                size = os.path.getsize(fp)
            except Exception:
                size = -1
            out.append({"path": rel, "size": size,
                        "name": os.path.basename(fp)})
        return {"ok": True, "type": type_key, "count": len(out), "files": out}

    def get_file(self, rel_path):
        """读取 mod 内指定相对路径的文件内容（路径安全校验）。"""
        self.ensure_mod()
        fp = self._safe_join(rel_path)
        if not fp or not os.path.isfile(fp):
            raise ValueError(f"文件不存在: {rel_path}")
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        return {"ok": True, "path": rel_path, "content": content,
                "size": len(content)}

    def write_file(self, data):
        """整文件写入（新建/覆盖）：{path, content}。

        路径安全：必须为 mod 内相对路径（禁止绝对路径与 .. 越界），
        目录自动创建；写入自动进入撤销管理器。
        """
        self.ensure_mod()
        rel_path = (data.get("path") or "").strip().replace("\\", "/")
        content = data.get("content")
        if not rel_path:
            raise ValueError("缺少 path（mod 内相对路径）")
        if content is None:
            raise ValueError("缺少 content")
        fp = self._safe_join(rel_path)
        if not fp:
            raise ValueError("非法路径（禁止绝对路径或 .. 越界）")
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        icon_ops.write_file_utf8(fp, content)
        self._notify_change(fp)
        return {"ok": True, "path": rel_path, "size": len(content)}

    def _safe_join(self, rel_path):
        """把 mod 内相对路径安全拼接到 mod 根（越界/绝对路径返回 None）。"""
        rel_path = (rel_path or "").replace("\\", "/").lstrip("/")
        if not rel_path or os.path.isabs(rel_path) or ".." in rel_path.split("/"):
            return None
        fp = os.path.normpath(os.path.join(self.mod_path, rel_path))
        root = os.path.normpath(self.mod_path)
        if not fp.startswith(root + os.sep) and fp != root:
            return None
        return fp

    # ---------- 工具接口（第一批复刻工具） ----------

    def format_pdx(self, data):
        """格式化 PDX 文件：{path, whitespace?, ignore_comments?}"""
        rel = (data.get("path") or "").strip()
        fp = self._safe_join(rel)
        if not fp or not os.path.isfile(fp):
            raise ValueError("文件不存在: " + rel)
        from pdx_format import format_file
        ok = format_file(fp, remove_whitespace=bool(data.get("whitespace")),
                         ignore_comments=bool(data.get("ignore_comments")))
        self._notify_change(fp)
        return {"ok": ok, "path": rel}

    def vp_loc_dry_run(self):
        """干跑生成 VP 本地化文本（不写文件）。"""
        self.ensure_mod()
        from vp_loc import collect_vps, build_vp_loc_text
        vps = collect_vps(self.mod_path)
        return {"ok": True, "count": len(vps),
                "text": build_vp_loc_text(vps, lang="simp_chinese")}

    def analyze_error_log(self, data):
        """分析错误日志：{path(相对mod) 或 absolute_path} → 归类。"""
        rel = (data.get("path") or "").strip()
        if rel:
            fp = self._safe_join(rel)
            if not fp:
                raise ValueError("非法路径")
        else:
            fp = data.get("absolute_path", "")
        if not fp or not os.path.isfile(fp):
            raise ValueError("日志文件不存在")
        from error_log import analyze_file, summarize, classify_by_subsystem
        results = analyze_file(fp)
        return {"ok": True, "count": len(results),
                "categories": summarize(results),
                "subsystems": classify_by_subsystem(results),
                "items": [{"lineno": r["lineno"], "category": r["category"],
                           "message": r["message"]} for r in results]}

    def register_icon_batch(self, data):
        """在脚本文件中批量补注册缺失图标 GFX：{path, type?}"""
        self.ensure_mod()
        rel = (data.get("path") or "").strip()
        type_key = (data.get("type") or "focus").strip()
        fp = self._safe_join(rel)
        if not fp or not os.path.isfile(fp):
            raise ValueError("文件不存在: " + rel)
        from icon_batch import register_missing_gfx
        r = register_missing_gfx(self.mod_path, rel, type_key,
                                 hoi4_path=self.game_path)
        return {"ok": True, "file": rel,
                "registered": r["registered"],
                "skipped_no_texture": r["skipped_no_texture"]}

    def create_focus_project(self, data):
        self.ensure_mod()
        from project_wizard import generate_project
        country = (data.get("country") or "").strip().upper()
        focus_id = (data.get("focus_id") or "").strip()
        if not country or not focus_id:
            raise ValueError("项目需要 country 与 focus_id")
        # 目标国策文件：该国现有文件，否则新建
        from workbench import WorkbenchDock
        base = os.path.join(self.mod_path, "common", "national_focus")
        focus_file = ""
        if os.path.isdir(base):
            for root, _dirs, names in os.walk(base):
                for name in sorted(names):
                    if not name.lower().endswith(".txt"):
                        continue
                    fp = os.path.join(root, name)
                    content = WorkbenchDock._read_file(fp)
                    if country in WorkbenchDock._detect_country_tags(fp, content):
                        focus_file = fp
                        break
                if focus_file:
                    break
        if not focus_file:
            focus_file = os.path.join(base, f"{country}_ai.txt")
        project_data = {
            "country": country,
            "focus_id": focus_id,
            "name": (data.get("name") or focus_id),
            "desc": data.get("desc") or "",
            "x": int(data.get("x", 0) or 0),
            "y": int(data.get("y", 0) or 0),
            "event": bool(data.get("event", True)),
            "decision": bool(data.get("decision", True)),
            "icon": bool(data.get("icon", True)),
            "localisation": bool(data.get("localisation", True)),
        }
        summary = generate_project(project_data, self.mod_path, focus_file)
        self._notify_change(focus_file)
        return {"ok": True, "summary": summary}

    # ---------- 本地化 ----------

    def write_localisation(self, data):
        self.ensure_mod()
        tag = (data.get("tag") or "generic").strip().upper()
        entries = data.get("entries") or {}
        if not isinstance(entries, dict) or not entries:
            raise ValueError("缺少 entries（{key: value}）")
        from project_wizard import _write_loc_entries
        path = _write_loc_entries(self.mod_path, tag, entries)
        self._notify_change(path)
        return {"ok": True, "file": os.path.relpath(path, self.mod_path).replace(os.sep, "/"),
                "count": len(entries)}

    def upload_tech_icon(self, data):
        """上传科技图标并自动注册 GFX_<id>_medium sprite（程序自动编写 gfx 文件）。

        data: {tech_id: str, image_base64: str}（可选 filename 仅作提示）
        """
        self.ensure_mod()
        tech_id = (data.get("tech_id") or "").strip()
        image_b64 = data.get("image_base64") or ""
        if not tech_id:
            raise ValueError("缺少 tech_id")
        if not image_b64:
            raise ValueError("缺少 image_base64（图片的 base64 编码）")
        from tech_icon_ops import upload_tech_icon_base64
        info = upload_tech_icon_base64(self.mod_path, tech_id, image_b64)
        self._notify_change(info["image_file"])
        self._notify_change(os.path.join(self.mod_path,
                                         info["gfx_file"].replace("/", os.sep)))
        return {"ok": True, **info}

    # ---------- 校验 ----------

    def validate(self):
        self.ensure_mod()
        import validation
        from game_data import build_dictionary, validate_directory, find_duplicate_ids
        issues = {}
        if self.game_path and os.path.isdir(self.game_path):
            try:
                dictionary = build_dictionary(self.game_path)
                issues = validate_directory(dictionary, self.mod_path)
            except Exception as e:
                issues["_dict"] = [f"构建游戏数据字典失败: {e}"]
        duplicates = find_duplicate_ids(self.mod_path)
        loc_missing = validation.check_localisation_coverage(self.mod_path, self.game_path)
        focus_refs = validation.check_focus_references(self.mod_path)
        return {
            "ok": True,
            "unknown_references": issues,
            "duplicate_ids": duplicates,
            "localisation_missing": [
                {"key": m["key"], "type": m["type"], "country": m["country"],
                 "file": m["file"], "missing_keys": m.get("missing_keys", [])}
                for m in loc_missing],
            "focus_references": focus_refs,
            "summary": {
                "unknown_reference_count": sum(len(v) for v in issues.values()),
                "duplicate_count": len(duplicates),
                "localisation_missing_count": len(loc_missing),
                "focus_dangling_count": len(focus_refs),
            },
        }

    # ---------- 模板 ----------

    def templates(self, template_type="", usage=""):
        from template_scheduler import get_template_scheduler
        scheduler = get_template_scheduler()
        matches = scheduler.search_templates(template_type=template_type, usage=usage)
        return {"ok": True, "count": len(matches), "templates": [
            {"name": m["name"], "type": m["type"], "usage": m["usage"],
             "file": m["filepath"]} for m in matches]}

    # ---------- 图标清单 / 覆盖增量报告（SF 移植：manifest + delta 模型） ----------

    def get_icon_manifest(self, query="", source="", limit=200):
        """图标库 manifest：扫描 mod+游戏全部 spriteType 定义。

        Args:
            query: sprite 名子串过滤
            source: mod / vanilla 来源过滤
            limit: 返回条数上限（默认 200；0 = 全部，可能很大）

        Returns:
            {"ok", "stats", "count", "entries": [...]}
        """
        from icon_manifest import build_icon_manifest
        if self._icon_manifest_cache is None:
            self._icon_manifest_cache = build_icon_manifest(
                self.mod_path, self.game_path)
        manifest = self._icon_manifest_cache
        entries = manifest["entries"]
        if query:
            entries = [e for e in entries if query in e["name"]]
        if source:
            entries = [e for e in entries if e.get("source") == source]
        if limit and len(entries) > limit:
            entries = entries[:limit]
        return {"ok": True, "stats": manifest["stats"],
                "count": len(entries), "entries": entries}

    def get_overlay_report(self, summary_only=False):
        """mod 覆盖原版的增量报告（规则分层 + 文件级 delta）。

        Returns:
            {"ok", "stats", "files": [...]}（summary_only 时不含 files）
        """
        self.ensure_mod()
        from overlay_rules import build_override_report
        report = build_override_report(self.mod_path, self.game_path)
        return {"ok": True, "stats": report["stats"],
                "layers": report["layers"],
                "files": [] if summary_only else report["files"]}

    def help(self):
        return {"ok": True, "endpoints": [
            "GET    /api/status",
            "GET    /api/types",
            "GET    /api/entities?type=&country=&kw=",
            "GET    /api/entities/<type>/<id>",
            "POST   /api/entities  {type,id,country?,content?}",
            "PUT    /api/entities/<type>/<id>  {content}",
            "DELETE /api/entities/<type>/<id>",
            "GET    /api/files?type=",
            "POST   /api/files  {path}（读） / {path,content}（写整文件）",
            "POST   /api/project  {country,focus_id,name?,desc?,event?,decision?,icon?,localisation?}",
            "POST   /api/localisation  {tag,entries:{key:value}}",
            "POST   /api/tech_icon  {tech_id,image_base64}（自动注册 GFX_<id>_medium）",
            "POST   /api/validate",
            "GET    /api/templates?type=&usage=",
            "GET    /api/icon_manifest?query=&source=&limit=",
            "GET    /api/overlay_report?summary_only=",
            "POST   /api/tools/format_pdx  {path,whitespace?,ignore_comments?}",
            "GET    /api/tools/vp_loc     （干跑 VP 本地化，不写文件）",
            "POST   /api/tools/error_log  {path|absolute_path}",
            "POST   /api/tools/register_icon_batch  {path,type?}",
            "POST   /api/mcp/<tool_name> 通用同源工具桥（159 个 MCP 工具均可调用）",
            "GET    /api/help",
        ]}


# ══════════════════════════════════════════════════════════════
# HTTP 层
# ══════════════════════════════════════════════════════════════

class _ApiHTTPServer(ThreadingHTTPServer):
    """携带 core/token 的服务实例（每个 ApiServer 独立，避免多实例串号）。"""

    def __init__(self, addr, handler_cls, core, token):
        super().__init__(addr, handler_cls)
        self.api_core = core
        self.api_token = token


class ApiHandler(BaseHTTPRequestHandler):
    # core/token 从 self.server（_ApiHTTPServer 实例）获取，
    # 不使用类属性，保证同一进程内多个服务实例互不干扰
    @property
    def core(self):
        return self.server.api_core

    @property
    def token(self):
        return self.server.api_token

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self):
        if not self.token:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {self.token}" or auth == self.token

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _route(self):
        if not self._check_auth():
            self._send(401, {"ok": False, "error": "未授权的请求（需要 Authorization: Bearer <token>）"})
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = urllib.parse.parse_qs(parsed.query)
        q = {k: (v[0] if v else "") for k, v in qs.items()}
        try:
            if path == "/api/status" and self.command == "GET":
                self._send(200, self.core.status())
            elif path == "/api/types" and self.command == "GET":
                self._send(200, self.core.types())
            elif path == "/api/help" and self.command == "GET":
                self._send(200, self.core.help())
            elif path == "/api/entities" and self.command == "GET":
                type_key = q.get("type", "")
                if not type_key:
                    self._send(400, {"ok": False, "error": "缺少 type 参数"})
                    return
                self._send(200, self.core.list_entities(
                    type_key, q.get("country", ""), q.get("kw", "")))
            elif path == "/api/entities" and self.command == "POST":
                self._send(200, self.core.create_entity(self._read_json()))
            elif path == "/api/entities" and self.command == "DELETE":
                self._send(400, {"ok": False, "error": "DELETE 需要 /api/entities/<type>/<id>"})
            elif path.startswith("/api/entities/") and self.command == "GET":
                parts = path[len("/api/entities/"):].split("/", 1)
                if len(parts) == 2:
                    self._send(200, self.core.get_entity(parts[0], urllib.parse.unquote(parts[1])))
                else:
                    self._send(400, {"ok": False, "error": "路径需为 /api/entities/<type>/<id>"})
            elif path.startswith("/api/entities/") and self.command == "PUT":
                parts = path[len("/api/entities/"):].split("/", 1)
                if len(parts) == 2:
                    self._send(200, self.core.update_entity(
                        parts[0], urllib.parse.unquote(parts[1]), self._read_json()))
                else:
                    self._send(400, {"ok": False, "error": "路径需为 /api/entities/<type>/<id>"})
            elif path.startswith("/api/entities/") and self.command == "DELETE":
                parts = path[len("/api/entities/"):].split("/", 1)
                if len(parts) == 2:
                    self._send(200, self.core.delete_entity(
                        parts[0], urllib.parse.unquote(parts[1])))
                else:
                    self._send(400, {"ok": False, "error": "路径需为 /api/entities/<type>/<id>"})
            elif path == "/api/project" and self.command == "POST":
                self._send(200, self.core.create_focus_project(self._read_json()))
            elif path == "/api/localisation" and self.command == "POST":
                self._send(200, self.core.write_localisation(self._read_json()))
            elif path == "/api/tech_icon" and self.command == "POST":
                self._send(200, self.core.upload_tech_icon(self._read_json()))
            elif path == "/api/validate" and self.command == "POST":
                self._send(200, self.core.validate())
            elif path == "/api/templates" and self.command == "GET":
                self._send(200, self.core.templates(q.get("type", ""), q.get("usage", "")))
            elif path == "/api/files" and self.command == "GET":
                type_key = q.get("type", "")
                if not type_key:
                    self._send(400, {"ok": False, "error": "缺少 type 参数"})
                    return
                self._send(200, self.core.list_files(type_key))
            elif path == "/api/files" and self.command == "POST":
                body = self._read_json()
                if "path" in body and "content" in body:
                    self._send(200, self.core.write_file(body))
                else:
                    # 读文件：{path}
                    self._send(200, self.core.get_file(body.get("path", "")))
            elif path == "/api/icon_manifest" and self.command == "GET":
                self._send(200, self.core.get_icon_manifest(
                    q.get("query", ""), q.get("source", ""),
                    int(q.get("limit", "200") or 0)))
            elif path == "/api/overlay_report" and self.command == "GET":
                self._send(200, self.core.get_overlay_report(
                    summary_only=q.get("summary_only", "") == "1"))
            elif path == "/api/tools/format_pdx" and self.command == "POST":
                self._send(200, self.core.format_pdx(self._read_json()))
            elif path == "/api/tools/vp_loc" and self.command == "GET":
                self._send(200, self.core.vp_loc_dry_run())
            elif path == "/api/tools/error_log" and self.command == "POST":
                self._send(200, self.core.analyze_error_log(self._read_json()))
            elif path == "/api/tools/register_icon_batch" and self.command == "POST":
                self._send(200, self.core.register_icon_batch(self._read_json()))
            elif path == "/api/mcp/overview" and self.command == "GET":
                from mcp_tools import build_catalog
                cats = {}
                for meta in build_catalog(self.core):
                    cats.setdefault(meta["category"], []).append(meta["name"])
                self._send(200, {
                    "total": sum(len(v) for v in cats.values()),
                    "categories": {k: sorted(v) for k, v in sorted(cats.items())},
                    "note": "未直接暴露的工具请用 invoke_tool 调用；用 /api/mcp/schema?name= 查参数。",
                })
            elif path == "/api/mcp/schema" and self.command == "GET":
                from mcp_tools import build_catalog
                name = q.get("name", "")
                meta = next((m for m in build_catalog(self.core)
                             if m["name"] == name), None)
                if meta is None:
                    self._send(404, {"ok": False, "error": "未知工具: %s" % name})
                else:
                    self._send(200, meta)
            elif path == "/api/mcp/invoke_tool" and self.command == "POST":
                from mcp_tools import build_tools
                body = self._read_json()
                name = body.get("name", "")
                args = body.get("args") or {}
                t = next((x for x in build_tools(self.core)
                          if x["name"] == name), None)
                if t is None:
                    self._send(404, {"ok": False, "error": "未知工具: %s" % name})
                    return
                result = t["_handler"](args)
                self._send(200, result if isinstance(result, dict)
                           else {"ok": True, "result": result})
            elif path.startswith("/api/mcp/") and self.command in ("GET", "POST"):
                tool_name = urllib.parse.unquote(path[len("/api/mcp/"):])
                method = getattr(self.core, tool_name, None)
                if method is None:
                    self._send(404, {"ok": False, "error": f"未知 MCP 工具: {tool_name}"})
                    return
                if self.command == "POST":
                    body = self._read_json()
                else:
                    body = q
                try:
                    result = method(body)
                    self._send(200, result if isinstance(result, dict) else {"ok": True, "result": result})
                except TypeError:
                    # 兼容无参方法
                    result = method()
                    self._send(200, result if isinstance(result, dict) else {"ok": True, "result": result})
            else:
                self._send(404, {"ok": False, "error": f"未知端点: {self.command} {self.path}"})
        except ValueError as e:
            # 参数/类型错误 → 400
            self._send(400, {"ok": False, "error": str(e)})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"ok": False, "error": str(e)})

    def do_GET(self):
        self._route()

    def do_POST(self):
        self._route()

    def do_PUT(self):
        self._route()

    def do_DELETE(self):
        self._route()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()


class ApiServer:
    """HTTP 服务封装（可独立运行，也可嵌入 GUI）。"""

    def __init__(self, mod_path="", game_path="", port=DEFAULT_PORT, token=""):
        self.core = ApiCore(mod_path=mod_path, game_path=game_path)
        self.port = int(port)
        self.token = token or secrets.token_hex(16)
        self._httpd = None
        self._thread = None

    def start(self):
        if self._httpd is not None:
            return False
        self._httpd = _ApiHTTPServer(("127.0.0.1", self.port), ApiHandler,
                                     self.core, self.token)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        if self._httpd is None:
            return
        try:
            self._httpd.shutdown()
        except Exception:
            pass
        try:
            self._httpd.server_close()
        except Exception:
            pass
        self._httpd = None
        self._thread = None

    @property
    def running(self):
        return self._httpd is not None

    def url(self):
        return f"http://127.0.0.1:{self.port}"


def main():
    parser = argparse.ArgumentParser(description="HOI4 模组编辑器 · 外置 Agent HTTP API")
    parser.add_argument("--mod", default="", help="mod 内容目录（缺省读 settings.json）")
    parser.add_argument("--game", default="", help="游戏根目录（缺省读 settings.json）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("--token", default="", help="Bearer token（缺省随机生成）")
    args = parser.parse_args()

    settings = load_settings()
    mod_path = args.mod or settings.get("mod_path", "")
    game_path = args.game or settings.get("HOI4_path", "")
    if not mod_path or not os.path.isdir(mod_path):
        print(f"[错误] 无效的 mod 目录: {mod_path!r}")
        sys.exit(1)

    server = ApiServer(mod_path=mod_path, game_path=game_path,
                       port=args.port, token=args.token)
    if not server.start():
        print(f"[错误] 端口 {args.port} 被占用")
        sys.exit(1)
    print(f"HOI4 模组编辑器 API 已启动")
    print(f"  mod  : {mod_path}")
    print(f"  game : {game_path or '(未配置)'}")
    print(f"  url  : {server.url()}")
    print(f"  token: {server.token}")
    print(f"  示例 : curl -H 'Authorization: Bearer {server.token}' {server.url()}/api/status")
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n正在关闭…")
        server.stop()


if __name__ == "__main__":
    main()
