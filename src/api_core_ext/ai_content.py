"""ApiCore 扩展：AI 内容 8 类 CRUD（域 4）

每类 6 个动作 + 计划专属 focus_order 写回，共 49 个工具。
"""
from __future__ import annotations

import os


_AI_KINDS = {
    "plan": {"dir": "common/ai_strategy_plans", "load": "load_ai_plans"},
    "strategy": {"dir": "common/ai_strategy", "load": "load_ai_strategies"},
    "ai_template": {"dir": "common/ai_templates", "load": "load_ai_templates"},
    "equipment": {"dir": "common/ai_equipment", "load": "load_ai_equipment"},
    "navy": {"dir": "common/ai_navy", "load": "load_ai_navy"},
    "area": {"dir": "common/ai_areas", "load": "load_ai_areas"},
    "focus": {"dir": "common/ai_focuses", "load": "load_ai_focuses"},
    "theater": {"dir": "common/ai_faction_theaters", "load": "load_ai_faction_theaters"},
}

_NAVY_SECTIONS = {
    "goal": ("goals", "insert_ai_navy_goal", "delete_ai_navy_goal",
             "rename_ai_navy_goal", "duplicate_ai_navy_goal"),
    "fleet": ("fleets", "insert_ai_navy_fleet", "delete_ai_navy_fleet",
              "rename_ai_navy_fleet", "duplicate_ai_navy_fleet"),
    "taskforce": ("taskforces", "insert_ai_navy_taskforce",
                  "delete_ai_navy_taskforce", "rename_ai_navy_taskforce",
                  "duplicate_ai_navy_taskforce"),
}

_CRUD_FUNCS = {
    "plan": ("insert_ai_plan", "delete_ai_plan", "rename_ai_plan", "duplicate_ai_plan"),
    "strategy": ("insert_ai_strategy_group", "delete_ai_strategy_group",
                 "rename_ai_strategy_group", "duplicate_ai_strategy_group"),
    "ai_template": ("insert_ai_template_role", "delete_ai_template_role",
                    "rename_ai_template_role", "duplicate_ai_template_role"),
    "equipment": ("insert_ai_equipment_group", "delete_ai_equipment_group",
                  "rename_ai_equipment_group", "duplicate_ai_equipment_group"),
    "area": ("insert_ai_area", "delete_ai_area", "rename_ai_area", "duplicate_ai_area"),
    "focus": ("insert_ai_focus", "delete_ai_focus", "rename_ai_focus", "duplicate_ai_focus"),
    "theater": ("insert_ai_faction_theater", "delete_ai_faction_theater",
                "rename_ai_faction_theater", "duplicate_ai_faction_theater"),
}


class AiContentMixin:
    """AI 内容 8 类 CRUD。"""

    # ---------- 内部辅助 ----------

    def _ai_load(self, kind):
        import ai_loader
        fn = getattr(ai_loader, _AI_KINDS[kind]["load"])
        return fn(self.mod_path, self.game_path)

    def _ai_clear(self):
        import ai_loader
        ai_loader._clear_cache()

    def _ai_dirs_for(self, kind, section=None):
        base_dir = _AI_KINDS[kind]["dir"]
        if kind == "navy":
            if section in _NAVY_SECTIONS:
                base_dir = os.path.join(_AI_KINDS[kind]["dir"],
                                        _NAVY_SECTIONS[section][0])
        return base_dir

    def _ai_existing_files(self, kind, section=None):
        rel_dir = self._ai_dirs_for(kind, section).replace("/", os.sep)
        out = []
        for base, source in ((self.mod_path, "mod"), (self.game_path, "game")):
            if not base:
                continue
            d = os.path.join(base, rel_dir)
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(".txt"):
                    fp = os.path.join(d, fn)
                    rel = os.path.join(rel_dir, fn).replace("\\", "/")
                    out.append((fp, rel, source))
        # mod 优先
        return out

    def _ai_find_record(self, kind, item_id, section=None):
        data = self._ai_load(kind)
        if kind == "navy":
            sec = _NAVY_SECTIONS.get(section, _NAVY_SECTIONS["goal"])[0]
            table = data.get(sec, {})
            rec = table.get(item_id)
            if rec:
                return rec
            # 找不到指定 section 时在所有 section 中找
            for tbl in data.values():
                if item_id in tbl:
                    return tbl[item_id]
            return None
        return data.get(item_id)

    def _ai_ensure_mod_file(self, fp):
        """返回 (mod 绝对路径, copied)。"""
        mod_norm = os.path.normcase(os.path.normpath(self.mod_path or ""))
        fp_norm = os.path.normcase(os.path.normpath(fp))
        if mod_norm and fp_norm.startswith(mod_norm):
            return fp, False
        if self.game_path and os.path.normcase(os.path.normpath(fp)).startswith(
                os.path.normcase(os.path.normpath(self.game_path))):
            rel = os.path.relpath(fp, self.game_path).replace("\\", "/")
            from state_build_ops import ensure_file_in_mod
            return ensure_file_in_mod(self.mod_path, self.game_path, rel)
        return fp, False

    def _ai_atomic_write(self, fp, content):
        from write_utils import atomic_write_text
        atomic_write_text(fp, content)

    def _ai_target_file(self, kind, section=None):
        """返回新建时的目标文件（mod 内绝对路径）。"""
        files = self._ai_existing_files(kind, section)
        # 优先 mod 文件，其次把游戏文件复制到 mod
        for fp, rel, source in files:
            if source == "mod":
                return fp, False
        for fp, rel, source in files:
            return self._ai_ensure_mod_file(fp)
        rel_dir = self._ai_dirs_for(kind, section).replace("/", os.sep)
        fp = os.path.join(self.mod_path, rel_dir, "ai_generated.txt")
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        return fp, False

    def _ai_read(self, fp):
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()

    def _ai_update_content(self, kind, content, item_id, data, section=None):
        import ai_loader
        if kind == "plan" and "focus_order" in data:
            return ai_loader.replace_ai_plan_focus_order(
                content, item_id, list(data.get("focus_order") or []))
        if kind == "strategy" and "entries" in data:
            return ai_loader.replace_ai_strategy_entries(
                content, item_id, data["entries"])
        if kind == "area" and "strategic_regions" in data:
            return ai_loader.replace_ai_area_regions(
                content, item_id, list(data.get("strategic_regions") or []))
        if kind == "area" and "content" in data:
            return ai_loader.replace_ai_area_block(content, item_id,
                                                   data["content"])
        if kind == "theater" and "regions" in data:
            return ai_loader.replace_ai_region_list(
                content, item_id, "regions", list(data.get("regions") or []))
        if kind == "theater" and "preferred_countries" in data:
            return ai_loader.replace_ai_region_list(
                content, item_id, "preferred_countries",
                list(data.get("preferred_countries") or []))
        if "content" in data:
            if kind == "area":
                return ai_loader.replace_ai_area_block(content, item_id,
                                                       data["content"])
            # 整块替换：删除旧块后插入新内容末尾
            new_content = ai_loader.delete_top_block(content, item_id)
            return ai_loader.insert_top_block(new_content, data["content"])
        if "field" in data and "value" in data:
            field = str(data["field"])
            value = data["value"]
            quoted = bool(data.get("quoted", False))
            if kind == "ai_template" and data.get("role_id") and data.get("target_id"):
                return ai_loader.replace_ai_template_target_field(
                    content, data["role_id"], data["target_id"],
                    field, value, quoted=quoted)
            if kind == "equipment" and data.get("group_id") and data.get("variant_id"):
                return ai_loader.replace_ai_equipment_variant_field(
                    content, data["group_id"], data["variant_id"],
                    field, value, quoted=quoted)
            return ai_loader.replace_top_block_field(
                content, item_id, field, value, quoted=quoted)
        return content

    # ---------- 核心动作 ----------

    def _ai_list(self, kind):
        """list 动作：返回该类型全部记录。"""
        payload = self._ai_load(kind)
        if kind == "navy":
            return {"ok": True, "sections": {
                "goals": payload.get("goals", {}),
                "fleets": payload.get("fleets", {}),
                "taskforces": payload.get("taskforces", {}),
            }}
        out = []
        for key, rec in payload.items():
            item = {"id": key}
            item.update(rec)
            out.append(item)
        return {"ok": True, "count": len(out), "items": out}

    def _ai_create(self, kind, item_id, section, data):
        """create 动作：新建记录并写回 mod。"""
        import ai_loader
        fp, copied = self._ai_target_file(kind, section or None)
        content = self._ai_read(fp) if os.path.isfile(fp) else ""
        if kind == "navy":
            if section not in _NAVY_SECTIONS:
                raise ValueError("navy 需要 section=goal/fleet/taskforce")
            fn = getattr(ai_loader, _NAVY_SECTIONS[section][1])
            if section == "goal":
                new_content = fn(
                    content, item_id,
                    data.get("objective_type", ""),
                    data.get("min_priority", "0"),
                    data.get("max_priority", "0"))
            else:
                new_content = fn(content, item_id)
        else:
            fn = getattr(ai_loader, _CRUD_FUNCS[kind][0])
            if kind == "plan":
                new_content = fn(content, item_id,
                                 data.get("name", ""), data.get("desc", ""))
            elif kind == "strategy":
                new_content = fn(content, item_id, data.get("entries"))
            elif kind == "ai_template":
                new_content = fn(content, item_id, data.get("role", ""))
            elif kind == "equipment":
                new_content = fn(content, item_id, data.get("category", "air"))
            elif kind == "area":
                new_content = fn(content, item_id, data.get("strategic_regions"))
            elif kind == "focus":
                new_content = fn(content, item_id, data.get("research"))
            elif kind == "theater":
                new_content = fn(content, item_id, data.get("name", ""),
                                 data.get("regions"))
            else:
                new_content = fn(content, item_id)
        self._ai_atomic_write(fp, new_content)
        self._ai_clear()
        self._notify_change(fp)
        return {"ok": True, "kind": kind, "action": "create", "id": item_id,
                "file": os.path.relpath(fp, self.mod_path).replace("\\", "/"),
                "copied": bool(copied)}

    def _ai_mutate(self, kind, action, item_id, section, data, content):
        """update/delete/rename/duplicate：返回 (新内容, 新 id)。"""
        import ai_loader
        if action == "update":
            new_content = self._ai_update_content(
                kind, content, item_id, data, section or None)
            return new_content, item_id
        if action == "delete":
            if kind == "navy":
                fn_name = (_NAVY_SECTIONS[section][2]
                           if section in _NAVY_SECTIONS else "delete_ai_navy_goal")
                fn = getattr(ai_loader, fn_name)
            else:
                fn = getattr(ai_loader, _CRUD_FUNCS[kind][1])
            return fn(content, item_id), item_id
        new_id = str(data.get("new") or data.get("new_id") or "").strip()
        if not new_id:
            raise ValueError("缺少 new/new_id")
        if action == "rename":
            if kind == "navy":
                fn_name = (_NAVY_SECTIONS[section][3]
                           if section in _NAVY_SECTIONS else "rename_ai_navy_goal")
                fn = getattr(ai_loader, fn_name)
            else:
                fn = getattr(ai_loader, _CRUD_FUNCS[kind][2])
            return fn(content, item_id, new_id), new_id
        if action == "duplicate":
            if kind == "navy":
                fn_name = (_NAVY_SECTIONS[section][4]
                           if section in _NAVY_SECTIONS else "duplicate_ai_navy_goal")
                fn = getattr(ai_loader, fn_name)
            else:
                fn = getattr(ai_loader, _CRUD_FUNCS[kind][3])
            return fn(content, item_id, new_id), new_id
        raise ValueError("未知动作: %s" % action)

    def _ai_action(self, kind, action, data=None):
        data = data or {}
        if action == "list":
            return self._ai_list(kind)

        item_id = str(data.get("id") or data.get("plan_id") or
                      data.get("group_id") or data.get("role_id") or
                      data.get("block_id") or data.get("area_id") or
                      data.get("theater_id") or data.get("goal_id") or
                      data.get("fleet_id") or data.get("taskforce_id") or "").strip()
        section = (data.get("section") or "").strip()
        if not item_id:
            raise ValueError("缺少 id")

        if action == "create":
            return self._ai_create(kind, item_id, section, data)

        rec = self._ai_find_record(kind, item_id, section or None)
        if rec is None:
            raise ValueError("未找到 AI %s: %s" % (kind, item_id))
        fp = rec.get("file", "")
        if not fp:
            raise ValueError("记录缺少文件路径")
        content = self._ai_read(fp) if os.path.isfile(fp) else ""

        new_content, new_id = self._ai_mutate(
            kind, action, item_id, section, data, content)

        fp2, _ = self._ai_ensure_mod_file(fp)
        if not fp2:
            raise ValueError("无法定位写入文件")
        self._ai_atomic_write(fp2, new_content)
        self._ai_clear()
        self._notify_change(fp2)
        return {"ok": True, "kind": kind, "action": action, "id": new_id,
                "file": os.path.relpath(fp2, self.mod_path).replace("\\", "/")}

    def set_ai_plan_focus_order(self, data=None):
        data = data or {}
        return self._ai_action("plan", "update", data)


def _make_ai_methods():
    kinds = list(_AI_KINDS.keys())
    actions = ("list", "create", "update", "delete", "rename", "duplicate")
    for kind in kinds:
        for action in actions:
            def _method(self, data=None, _kind=kind, _action=action):
                return self._ai_action(_kind, _action, data)
            _method.__name__ = "ai_{}_{}".format(kind, action)
            _method.__doc__ = "AI {} {}".format(kind, action)
            setattr(AiContentMixin, _method.__name__, _method)


_make_ai_methods()