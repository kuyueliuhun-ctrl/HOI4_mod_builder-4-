"""ApiCore 扩展：项目级（域 10）"""
from __future__ import annotations

import os
import re

import path_safety


class ProjectMixin:
    """国家接管、新建 mod、模板应用。"""

    def list_countries(self, data=None):
        data = data or {}
        from country_setup_dialog import scan_vanilla_countries, scan_mod_countries
        countries = scan_vanilla_countries(self.game_path)
        mod_tags = scan_mod_countries(self.mod_path) if self.mod_path else set()
        out = []
        for tag, rel in sorted(countries.items()):
            out.append({"tag": tag, "file": rel,
                        "mod_override": tag in mod_tags})
        for tag in sorted(mod_tags):
            if tag not in countries:
                out.append({"tag": tag, "file": "",
                            "mod_override": True})
        return {"ok": True, "count": len(out), "countries": out}

    def copy_country_files(self, data=None):
        data = data or {}
        return self._country_op("copy", data)

    def create_blank_overrides(self, data=None):
        data = data or {}
        return self._country_op("blank", data)

    def create_new_country_files(self, data=None):
        data = data or {}
        return self._country_op("new", data)

    def _country_op(self, op, data):
        self.ensure_mod()
        tag = (data.get("tag") or "").strip().upper()
        dirs = data.get("dirs") or []
        dry_run = bool(data.get("dry_run", True))
        if not tag or not dirs:
            raise ValueError("需要 tag/dirs")
        from country_setup_dialog import (
            copy_country_files, create_blank_overrides,
            create_new_country_files)
        # 预览：不执行，仅返回目标文件清单（由原函数逻辑近似）
        if dry_run:
            preview = []
            for rel_dir in dirs:
                preview.append({
                    "path": "%s/<%s>" % (rel_dir, tag),
                    "summary": "%s %s" % (op, tag),
                })
            return {"ok": True, "dry_run": True, "op": op, "tag": tag,
                    "count": len(preview), "files": preview}
        if op == "copy":
            copied = copy_country_files(self.game_path, self.mod_path, tag, dirs)
            files = [{"path": rel, "summary": "copied"} for rel in copied]
        elif op == "blank":
            created = create_blank_overrides(
                self.mod_path, tag, dirs, self.game_path)
            files = [{"path": rel, "summary": "blank"} for rel in created]
        elif op == "new":
            created = create_new_country_files(self.mod_path, tag, dirs,
                                               self.game_path)
            files = [{"path": rel, "summary": "new"} for rel in created]
        else:
            raise ValueError("未知操作: %s" % op)
        for f in files:
            self._notify_change(os.path.join(self.mod_path, f["path"].replace("/", os.sep)))
        return {"ok": True, "dry_run": False, "op": op, "tag": tag,
                "count": len(files), "files": files}

    def _mod_create_allowed_roots(self):
        """返回允许创建 mod 的根目录集合（settings 白名单 + 当前 mod 父目录）。"""
        roots = set()
        from api_server import load_settings
        settings = load_settings()
        for key in ("mod_folder_path", "mod_file_path"):
            v = (settings.get(key) or "").strip()
            if v:
                roots.add(os.path.abspath(os.fspath(v)))
        if self.mod_path:
            roots.add(os.path.abspath(
                os.path.dirname(os.path.abspath(self.mod_path))))
        return sorted(roots)

    def _check_mod_create_path(self, value, label):
        """校验新建 mod 路径必须在允许根内；返回规范化绝对路径。"""
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("缺少 %s" % label)
        roots = self._mod_create_allowed_roots()
        if not roots:
            raise ValueError(
                "未配置允许创建 mod 的根目录（settings mod_folder_path/"
                "mod_file_path，或先加载一个 mod）")
        norm_raw = raw.replace("\\", "/")
        is_abs = os.path.isabs(raw) or bool(re.match(r"^[A-Za-z]:", norm_raw))
        if is_abs:
            for r in roots:
                if path_safety.is_within(r, raw):
                    return os.path.abspath(os.fspath(raw))
            raise ValueError("%s 超出允许的 mod 创建根目录" % label)
        if norm_raw.startswith("/") or ".." in norm_raw.split("/"):
            raise ValueError("%s 不允许绝对/盘符/.. 越界" % label)
        # 相对路径解析到第一个允许根
        fp = os.path.abspath(os.path.join(roots[0], raw))
        if not any(path_safety.is_within(r, fp) for r in roots):
            raise ValueError("%s 超出允许的 mod 创建根目录" % label)
        return fp

    def create_mod(self, data=None):
        data = data or {}
        name = (data.get("name") or "").strip()
        folder = (data.get("folder_name") or data.get("name") or "").strip()
        folder = (data.get("folder") or folder).strip()
        version = (data.get("version") or "1.14.*").strip()
        tags = data.get("tags") or []
        mod_folder_path = (data.get("mod_folder_path") or
                           data.get("path") or "").strip()
        mod_file_path = (data.get("mod_file_path") or data.get("mod_path") or
                         mod_folder_path).strip()
        tag = (data.get("tag") or "").strip().upper()
        dry_run = bool(data.get("dry_run", True))
        approved = bool(data.get("approved", False))
        if not name or not folder or not version:
            raise ValueError("需要 name/folder/version")
        if not mod_folder_path:
            raise ValueError("缺少 path 或 mod_folder_path")
        if not dry_run and not approved:
            raise ValueError("创建 mod 为高权限写操作，需 approved=true 确认")
        mod_folder_abs = self._check_mod_create_path(mod_folder_path,
                                                     "mod_folder_path")
        mod_file_abs = self._check_mod_create_path(mod_file_path,
                                                   "mod_file_path")
        from mod_creator import build_mod_files, write_mod_files
        files = build_mod_files(name, folder, version, tags,
                                mod_folder_abs, mod_file_abs, tag)
        if dry_run:
            return {"ok": True, "dry_run": True, "count": len(files),
                    "files": [{"path": f["path"], "summary": ""}
                              for f in files]}
        written = write_mod_files(files)
        for p in written:
            self._notify_change(p)
        return {"ok": True, "dry_run": False, "count": len(written),
                "files": written}

    def apply_template(self, data=None):
        self.ensure_mod()
        data = data or {}
        template_name = (data.get("template_name") or "").strip()
        target_path = (data.get("target_path") or "").strip()
        variables = data.get("variables") or {}
        if not template_name or not target_path:
            raise ValueError("需要 template_name/target_path")
        from template_scheduler import get_template_scheduler
        sched = get_template_scheduler()
        matches = [m for m in sched.search_templates() if m["name"] == template_name]
        if not matches:
            raise ValueError("未找到模板: %s" % template_name)
        template_path = matches[0]["filepath"]
        fp = self._safe_join(target_path)
        if not fp:
            raise ValueError("非法目标路径: %s" % target_path)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        ok = sched.apply_template(template_path, fp, variables)
        if not ok:
            raise ValueError("应用模板失败")
        self._notify_change(fp)
        return {"ok": True, "template": template_name, "target": target_path}

    def get_template(self, data=None):
        data = data or {}
        template_name = (data.get("template_name") or "").strip()
        if not template_name:
            raise ValueError("缺少 template_name")
        from template_scheduler import get_template_scheduler
        sched = get_template_scheduler()
        matches = [m for m in sched.search_templates() if m["name"] == template_name]
        if not matches:
            raise ValueError("未找到模板: %s" % template_name)
        m = matches[0]
        content = sched.get_template_content(m["filepath"])
        return {"ok": True, "template": m, "content": content}

    def check_oob_version_names(self, data=None):
        """OOB 文件 version_name 引用与设计库一致性检查（后端数据层，未注册 MCP）。

        Args:
            data: {"path": OOB 相对路径}
        Returns:
            {"ok", "path", "count", "resolved", "unresolved", "refs"}
        """
        data = data or {}
        path = (data.get("path") or "").strip()
        if not path:
            raise ValueError("需要 path（OOB 相对路径）")
        fp = self._safe_join(path)
        if not fp or not os.path.isfile(fp):
            raise ValueError("文件不存在: " + path)
        from oob_version_refs import check_version_name_links
        from plane_design import load_plane_variants
        from ship_design import load_ship_variants
        from tank_design import load_tank_variants
        with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
        r = check_version_name_links(
            content,
            load_plane_variants(self.mod_path, self.game_path),
            load_tank_variants(self.mod_path, self.game_path),
            load_ship_variants(self.mod_path, self.game_path))
        return {"ok": True, "path": path, "count": r["count"],
                "resolved": len(r["resolved"]),
                "unresolved": len(r["unresolved"]),
                "refs": r["refs"]}