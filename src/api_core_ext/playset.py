"""ApiCore 扩展：播放集 / 多 mod 冲突检查（只读工具，阶段D）"""
from __future__ import annotations

import os


class PlaysetMixin:
    """播放集列举与冲突扫描（只读，不写任何文件）。"""

    def _hoi4_user_dir(self, data):
        """解析用户文档目录：显式 user_dir > settings.json 推断。"""
        from playset_loader import hoi4_user_dir
        user_dir = (data or {}).get("user_dir") or ""
        if user_dir and os.path.isdir(user_dir):
            return user_dir
        try:
            import json
            from project_paths import PROJECT_ROOT
            with open(os.path.join(PROJECT_ROOT, "settings.json"),
                      "r", encoding="utf-8-sig") as f:
                settings = json.load(f)
        except Exception:
            settings = {}
        return hoi4_user_dir(settings)

    def playset_list(self, data=None):
        data = data or {}
        from playset_loader import list_playsets
        user_dir = self._hoi4_user_dir(data)
        if not user_dir:
            return {"ok": False, "error": "未找到 HOI4 用户文档目录"
                    "（可传 user_dir 参数）"}
        return {"ok": True, "user_dir": user_dir,
                "playsets": list_playsets(user_dir)}

    def playset_conflict_scan(self, data=None):
        data = data or {}
        from conflict_scan import scan_conflicts
        from playset_loader import load_playset
        user_dir = self._hoi4_user_dir(data)
        if not user_dir:
            return {"ok": False, "error": "未找到 HOI4 用户文档目录"
                    "（可传 user_dir 参数）"}
        playset = load_playset(user_dir, data.get("playset_id"))
        report = scan_conflicts(
            playset, hoi4_path=self.game_path,
            include_vanilla=bool(data.get("include_vanilla", False)),
            scan_entities=bool(data.get("scan_entities", True)),
            scan_loc=bool(data.get("scan_loc", True)))
        return {
            "ok": True,
            "playset": playset.name,
            "mod_count": len(playset.mods),
            "counts": report.counts(),
            "duration_ms": report.duration_ms,
            "scanned_files": report.scanned_files,
            "skipped_files": report.skipped_files,
            "truncated_kinds": report.truncated_kinds,
            "items": report.to_dicts(),
        }

    # ---------- 子 Mod 模式（与 GUI 共用 mod_stack / submod_wizard） ----------

    def _load_project_settings(self):
        try:
            import json
            from project_paths import PROJECT_ROOT
            with open(os.path.join(PROJECT_ROOT, "settings.json"),
                      "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {}

    def _persist_submod_settings(self, fields):
        """settings.json 读改写（仅合并 submod_* 字段，保留其余配置）。"""
        import json
        from project_paths import PROJECT_ROOT
        fp = os.path.join(PROJECT_ROOT, "settings.json")
        settings = self._load_project_settings()
        settings.update(fields)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return fp

    def _resolve_base_layers(self, data, playset):
        """底层 mod 读取层：显式 base_paths > base_names 匹配 > 播放集全部。"""
        base_paths = [p for p in (data.get("base_paths") or [])
                      if p and os.path.isdir(p)]
        if base_paths:
            name_by_dir = {os.path.normpath(m.content_dir): m.name
                           for m in playset.mods if m.content_dir}
            names = [name_by_dir.get(os.path.normpath(p),
                                     os.path.basename(os.path.normpath(p)))
                     for p in base_paths]
            return base_paths, names
        all_mods = [m for m in playset.mods if m.content_dir
                    and os.path.isdir(m.content_dir)]
        base_names = [n for n in (data.get("base_names") or []) if n]
        if base_names:
            picked = [m for m in all_mods if m.name in base_names]
            missing = [n for n in base_names
                       if n not in {m.name for m in picked}]
            if missing:
                raise ValueError("播放集中找不到底层 mod: %s" % "、".join(missing))
            return [m.content_dir for m in picked], [m.name for m in picked]
        if data.get("base_names") is not None:
            return [], []      # 显式传空列表 = 无底层（仅原版层）
        return ([m.content_dir for m in all_mods],
                [m.name for m in all_mods])

    def _activate_core_stack(self, submod_path, submod_name, base_paths,
                             persist=True):
        """进程内激活层栈 + 可选持久化（与 GUI 的 SubmodModeMixin 等价）。"""
        from mod_stack import from_paths, set_active_stack
        from submod_wizard import submod_settings_fields
        stack = from_paths(sub_mod=submod_path, mod_paths=base_paths,
                           vanilla=self.game_path,
                           submod_name=submod_name)
        if not stack.layers or not stack.submod_path:
            raise ValueError("子 mod 目录无效: %s" % submod_path)
        set_active_stack(stack)
        if persist:
            self._persist_submod_settings(submod_settings_fields(
                stack.submod_path, stack.layers[0].name, base_paths))
        return stack

    def submod_status(self, data=None):
        """子 mod 模式状态：当前进程层栈 + settings.json 持久化字段。"""
        data = data or {}
        from mod_stack import active_stack
        st = active_stack()
        settings = self._load_project_settings()
        persisted = {k: settings.get(k)
                     for k in ("submod_active", "submod_path",
                               "submod_name", "submod_bases")}
        return {
            "ok": True,
            "active": st is not None,
            "submod_path": st.submod_path if st is not None else "",
            "layers": ([{"name": l.name, "path": l.path,
                         "writable": l.writable, "kind": l.kind}
                        for l in st.layers] if st is not None else []),
            "persisted": persisted,
        }

    def submod_create(self, data=None):
        """创建子 mod（真实可玩 mod，dependencies=底层 name），并可选激活。

        读取层 = 整个播放集（read_all，默认）或仅勾选底层；
        写路由激活后恒落子 mod（copy_up 自动，无 GUI 弹窗）。
        """
        data = data or {}
        name = str(data.get("submod_name") or "").strip()
        if not name:
            raise ValueError("需要 submod_name")
        from mod_creator import write_mod_files
        from playset_loader import load_playset
        from submod_wizard import build_submod_files, resolve_folder_name

        user_dir = self._hoi4_user_dir(data)
        playset = load_playset(user_dir, data.get("playset_id"))
        base_paths, base_names = self._resolve_base_layers(data, playset)
        if data.get("read_all", True) and playset.mods:
            read_paths = [m.content_dir for m in playset.mods
                          if m.content_dir and os.path.isdir(m.content_dir)]
        else:
            read_paths = list(base_paths)

        settings = self._load_project_settings()
        mod_folder_path = data.get("mod_folder_path") or \
            settings.get("mod_folder_path")
        mod_file_path = data.get("mod_file_path") or \
            settings.get("mod_file_path") or mod_folder_path
        if not mod_folder_path:
            raise ValueError("需要 mod_folder_path（或 settings.json "
                             "的 mod_folder_path）")

        folder = resolve_folder_name(
            data.get("folder_name") or name,
            existing_names=os.listdir(mod_folder_path)
            if os.path.isdir(mod_folder_path) else ())
        tags = [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()]
        files = build_submod_files(
            name=name, folder_name=folder,
            version=data.get("version") or "1.19.*",
            tags=tags, base_names=base_names,
            mod_folder_path=mod_folder_path, mod_file_path=mod_file_path)
        written = write_mod_files(files)
        submod_path = os.path.dirname(files[1]["path"])

        activate = bool(data.get("activate", True))
        stack = None
        if activate:
            stack = self._activate_core_stack(
                submod_path, name, read_paths,
                persist=bool(data.get("persist", True)))
        return {
            "ok": True,
            "submod_path": submod_path,
            "mod_file": files[0]["path"],
            "folder": folder,
            "base_names": base_names,
            "read_paths": read_paths,
            "written": written,
            "activated": stack is not None,
            "layers": ([{"name": l.name, "kind": l.kind}
                        for l in stack.layers] if stack is not None else []),
        }

    def submod_activate(self, data=None):
        """激活已有子 mod（进程内层栈 + 可选持久化）。"""
        data = data or {}
        submod_path = str(data.get("submod_path") or "").strip()
        if not submod_path or not os.path.isdir(submod_path):
            raise ValueError("需要有效的 submod_path")
        settings = self._load_project_settings()
        base_paths = [p for p in (data.get("base_paths")
                                  or settings.get("submod_bases") or [])
                      if p and os.path.isdir(p)]
        name = data.get("submod_name") or \
            os.path.basename(os.path.normpath(submod_path))
        stack = self._activate_core_stack(
            submod_path, name, base_paths,
            persist=bool(data.get("persist", True)))
        return {"ok": True, "submod_path": stack.submod_path,
                "layers": [{"name": l.name, "kind": l.kind}
                           for l in stack.layers]}

    def submod_exit(self, data=None):
        """退出子 mod 模式（清进程内层栈；persist=True 时同步 settings）。"""
        data = data or {}
        from mod_stack import clear_active_stack
        clear_active_stack()
        if data.get("persist", False):
            self._persist_submod_settings({"submod_active": False})
        return {"ok": True, "active": False}
