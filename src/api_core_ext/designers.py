"""ApiCore 扩展：三军设计器 + 设计模板 + 师编制/OOB（域 2 + 3）

所有写回目标：mod 优先，原版自动 ensure_file_in_mod 复制后再写。
"""
from __future__ import annotations

import os


class DesignersMixin:
    """设计器与 OOB 工具。"""

    # ---------- 设计器通用信息 ----------

    @staticmethod
    def _design_info(kind):
        if kind == "ship":
            return {
                "kind": "ship",
                "load_hulls": "load_ship_hulls",
                "load_modules": "load_ship_modules",
                "load_variants": "load_ship_variants",
                "stats": "ship_design_stats",
                "apply": "apply_variant_upgrades",
                "insert": "insert_variant",
                "remove": "remove_variant",
                "rename": "rename_variant",
                "module_block": "upgrades",
            }
        if kind == "plane":
            return {
                "kind": "plane",
                "load_hulls": "load_plane_airframes",
                "load_modules": "load_plane_modules",
                "load_variants": "load_plane_variants",
                "stats": "plane_design_stats",
                "apply": "apply_variant_modules",
                "insert": "insert_variant",
                "remove": "remove_variant",
                "rename": "rename_variant",
                "module_block": "modules",
            }
        if kind == "tank":
            return {
                "kind": "tank",
                "load_hulls": "load_tank_chassis",
                "load_modules": "load_tank_modules",
                "load_variants": "load_tank_variants",
                "stats": "tank_design_stats",
                "apply": "apply_variant_modules",  # 与 plane 写回逻辑一致
                "insert": "insert_variant",
                "remove": "remove_variant",
                "rename": "rename_variant",
                "module_block": "modules",
            }
        raise ValueError("kind 必须为 ship/plane/tank")

    @staticmethod
    def _design_module_name(kind):
        return "ship_design" if kind == "ship" else "plane_design" if kind == "plane" else "tank_design"

    def _design_hulls(self, kind):
        info = self._design_info(kind)
        mod = __import__(self._design_module_name(kind), fromlist=[info["load_hulls"]])
        fn = getattr(mod, info["load_hulls"])
        return fn(self.mod_path, self.game_path)

    def _design_modules(self, kind):
        info = self._design_info(kind)
        mod = __import__(self._design_module_name(kind), fromlist=[info["load_modules"]])
        fn = getattr(mod, info["load_modules"])
        return fn(self.mod_path, self.game_path)

    def _design_variants(self, kind):
        info = self._design_info(kind)
        mod = __import__(self._design_module_name(kind), fromlist=[info["load_variants"]])
        fn = getattr(mod, info["load_variants"])
        return fn(self.mod_path, self.game_path)

    def _design_save_path(self, tag):
        from state_build_ops import ensure_file_in_mod
        for base in (self.mod_path, self.game_path):
            if not base:
                continue
            d = os.path.join(base, "history", "countries")
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                first = fn.split()[0].strip()
                if first.lower().endswith(".txt"):
                    first = first[:-4]
                if first == tag and fn.lower().endswith(".txt"):
                    rel = os.path.join("history", "countries", fn).replace("\\", "/")
                    return ensure_file_in_mod(self.mod_path, self.game_path, rel)
        return None, False

    @staticmethod
    def _read_text(fp):
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _write_text(fp, content):
        from write_utils import atomic_write_text
        atomic_write_text(fp, content)

    def _design_refresh(self, kind):
        modname = "ship_design" if kind == "ship" else "plane_design" if kind == "plane" else "tank_design"
        mod = __import__(modname, fromlist=["_VARIANTS_CACHE"])
        if kind == "ship":
            mod._HULLS_CACHE.clear()
            mod._MODULES_CACHE.clear()
            mod._VARIANTS_CACHE.clear()
        elif kind == "plane":
            mod._AIRFRAMES_CACHE.clear()
            mod._PLANE_MODULES_CACHE.clear()
            mod._PLANE_VARIANTS_CACHE.clear()
        elif kind == "tank":
            mod._TANKS_CACHE.clear()
            mod._TANK_MODULES_CACHE.clear()
            mod._TANK_VARIANTS_CACHE.clear()

    # ---------- 设计器查询 ----------

    def list_ship_hulls(self, data=None):
        return self._list_design_hulls("ship", data)
    def list_plane_hulls(self, data=None):
        return self._list_design_hulls("plane", data)
    def list_tank_hulls(self, data=None):
        return self._list_design_hulls("tank", data)

    def list_ship_modules(self, data=None):
        return self._list_design_modules("ship", data)
    def list_plane_modules(self, data=None):
        return self._list_design_modules("plane", data)
    def list_tank_modules(self, data=None):
        return self._list_design_modules("tank", data)

    def list_ship_designs(self, data=None):
        return self._list_designs("ship", data)
    def list_plane_designs(self, data=None):
        return self._list_designs("plane", data)
    def list_tank_designs(self, data=None):
        return self._list_designs("tank", data)

    def get_ship_design(self, data=None):
        return self._get_design("ship", data)
    def get_plane_design(self, data=None):
        return self._get_design("plane", data)
    def get_tank_design(self, data=None):
        return self._get_design("tank", data)

    def create_ship_design(self, data=None):
        return self._create_design("ship", data)
    def create_plane_design(self, data=None):
        return self._create_design("plane", data)
    def create_tank_design(self, data=None):
        return self._create_design("tank", data)

    def update_ship_design(self, data=None):
        return self._update_design("ship", data)
    def update_plane_design(self, data=None):
        return self._update_design("plane", data)
    def update_tank_design(self, data=None):
        return self._update_design("tank", data)

    def rename_ship_design(self, data=None):
        return self._rename_design("ship", data)
    def rename_plane_design(self, data=None):
        return self._rename_design("plane", data)
    def rename_tank_design(self, data=None):
        return self._rename_design("tank", data)

    def delete_ship_design(self, data=None):
        return self._delete_design("ship", data)
    def delete_plane_design(self, data=None):
        return self._delete_design("plane", data)
    def delete_tank_design(self, data=None):
        return self._delete_design("tank", data)

    def sync_ship_design(self, data=None):
        return self._sync_design("ship", data)
    def sync_plane_design(self, data=None):
        return self._sync_design("plane", data)
    def sync_tank_design(self, data=None):
        return self._sync_design("tank", data)

    # ---------- 设计器实现 ----------

    def _list_design_hulls(self, kind, data=None):
        data = data or {}
        hulls = self._design_hulls(kind)
        out = [{"key": k, **v} for k, v in hulls.items()]
        return {"ok": True, "count": len(out), "items": out}

    def _list_design_modules(self, kind, data=None):
        data = data or {}
        mods = self._design_modules(kind)
        out = [{"key": k, **v} for k, v in mods.items()]
        return {"ok": True, "count": len(out), "items": out}

    def _list_designs(self, kind, data=None):
        data = data or {}
        country = (data.get("country") or "").strip().upper()
        variants = self._design_variants(kind)
        designs = []
        for tag, items in variants.items():
            if country and tag != country:
                continue
            for name, v in items.items():
                designs.append({
                    "country": tag,
                    "name": name,
                    "type": v.get("type", ""),
                    "modules": v.get("modules", {}),
                })
        designs.sort(key=lambda x: (x["country"], x["name"]))
        return {"ok": True, "count": len(designs), "designs": designs}

    def _get_design(self, kind, data=None):
        data = data or {}
        country = (data.get("country") or "").strip().upper()
        name = (data.get("name") or "").strip()
        variants = self._design_variants(kind)
        hv = variants.get(country)
        if not hv or name not in hv:
            raise ValueError("未找到设计 %s/%s" % (country, name))
        v = hv[name]
        hulls = self._design_hulls(kind)
        modules = self._design_modules(kind)
        hull = hulls.get(v.get("type", ""))
        if hull is None:
            stats = {"error": "hull definition not found"}
        else:
            stats = getattr(__import__(
                "ship_design" if kind == "ship" else "plane_design"
                if kind == "plane" else "tank_design", fromlist=["_"]),
                self._design_info(kind)["stats"])(v, hull, modules)
        return {"ok": True, "country": country, "name": name,
                "variant": v, "stats": stats}

    def _load_variant_file_for(self, tag):
        fp, copied = self._design_save_path(tag)
        if not fp:
            # 目标国家文件不存在：允许新建（写入 TAG 块）
            return None, False
        return fp, copied

    def _create_design(self, kind, data=None):
        self.ensure_mod()
        data = data or {}
        country = (data.get("country") or "").strip().upper()
        name = (data.get("name") or "").strip()
        hull_key = (data.get("hull") or data.get("type") or "").strip()
        modules = data.get("upgrades") or data.get("modules") or {}
        if not country or not name or not hull_key:
            raise ValueError("需要 country/name/hull")
        info = self._design_info(kind)
        mod = __import__("ship_design" if kind == "ship" else "plane_design"
                         if kind == "plane" else "tank_design",
                         fromlist=[info["insert"]])
        insert = getattr(mod, info["insert"])
        fp, copied = self._load_variant_file_for(country)
        if fp is None:
            # 新建国家文件：TAG = { ... }
            rel = "history/countries/%s.txt" % country
            fp = os.path.join(self.mod_path, rel)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            content = "%s = {\n}\n" % country
        else:
            content = self._read_text(fp)
        new_content = insert(content, country, name, hull_key, modules)
        if new_content is None:
            # 展开式国家文件（无 TAG 顶层块）：直接追加 create_equipment_variant
            block_name = info["module_block"]
            lines = ["create_equipment_variant = {",
                     '\tname = "%s"' % name,
                     "\ttype = %s" % hull_key,
                     "\t%s = {" % block_name]
            for slot, mod in modules.items():
                lines.append("\t\t%s = %s" % (slot, mod))
            lines.append("\t}")
            lines.append("}")
            new_content = content.rstrip() + "\n" + "\n".join(lines) + "\n"
        self._write_text(fp, new_content)
        self._design_refresh(kind)
        self._notify_change(fp)
        return {"ok": True, "country": country, "name": name, "file":
                os.path.relpath(fp, self.mod_path).replace("\\", "/"),
                "copied": bool(copied)}

    def _update_design(self, kind, data=None):
        self.ensure_mod()
        data = data or {}
        country = (data.get("country") or "").strip().upper()
        name = (data.get("name") or "").strip()
        modules = data.get("upgrades") or data.get("modules")
        if not country or not name or modules is None:
            raise ValueError("需要 country/name/upgrades 或 modules")
        variants = self._design_variants(kind)
        v = (variants.get(country) or {}).get(name)
        if not v:
            raise ValueError("未找到设计 %s/%s" % (country, name))
        type_key = v.get("type", "")
        info = self._design_info(kind)
        mod = __import__("ship_design" if kind == "ship" else "plane_design"
                         if kind == "plane" else "tank_design",
                         fromlist=[info["apply"]])
        apply = getattr(mod, info["apply"])
        fp, _ = self._load_variant_file_for(country)
        if not fp:
            raise ValueError("无法定位国家文件 %s" % country)
        content = self._read_text(fp)
        new_content = apply(content, name, modules, type_key=type_key)
        if new_content is None:
            raise ValueError("未找到设计块 %s" % name)
        self._write_text(fp, new_content)
        self._design_refresh(kind)
        self._notify_change(fp)
        return {"ok": True, "country": country, "name": name,
                "file": os.path.relpath(fp, self.mod_path).replace("\\", "/")}

    def _rename_design(self, kind, data=None):
        self.ensure_mod()
        data = data or {}
        country = (data.get("country") or "").strip().upper()
        old = (data.get("old") or data.get("old_name") or "").strip()
        new = (data.get("new") or data.get("new_name") or "").strip()
        if not country or not old or not new:
            raise ValueError("需要 country/old/new")
        variants = self._design_variants(kind)
        v = (variants.get(country) or {}).get(old)
        if not v:
            raise ValueError("未找到设计 %s/%s" % (country, old))
        type_key = v.get("type", "")
        info = self._design_info(kind)
        mod = __import__("ship_design" if kind == "ship" else "plane_design"
                         if kind == "plane" else "tank_design",
                         fromlist=[info["rename"]])
        fn = getattr(mod, info["rename"])
        fp, _ = self._load_variant_file_for(country)
        if not fp:
            raise ValueError("无法定位国家文件 %s" % country)
        content = self._read_text(fp)
        new_content = fn(content, old, new, type_key=type_key)
        if new_content is None:
            raise ValueError("未找到设计块 %s" % old)
        self._write_text(fp, new_content)
        self._design_refresh(kind)
        self._notify_change(fp)
        return {"ok": True, "country": country, "old": old, "new": new,
                "file": os.path.relpath(fp, self.mod_path).replace("\\", "/")}

    def _delete_design(self, kind, data=None):
        self.ensure_mod()
        data = data or {}
        country = (data.get("country") or "").strip().upper()
        name = (data.get("name") or "").strip()
        if not country or not name:
            raise ValueError("需要 country/name")
        variants = self._design_variants(kind)
        v = (variants.get(country) or {}).get(name)
        if not v:
            raise ValueError("未找到设计 %s/%s" % (country, name))
        type_key = v.get("type", "")
        info = self._design_info(kind)
        mod = __import__("ship_design" if kind == "ship" else "plane_design"
                         if kind == "plane" else "tank_design",
                         fromlist=[info["remove"]])
        fn = getattr(mod, info["remove"])
        fp, _ = self._load_variant_file_for(country)
        if not fp:
            raise ValueError("无法定位国家文件 %s" % country)
        content = self._read_text(fp)
        new_content = fn(content, name, type_key=type_key)
        if new_content is None:
            raise ValueError("未找到设计块 %s" % name)
        self._write_text(fp, new_content)
        self._design_refresh(kind)
        self._notify_change(fp)
        return {"ok": True, "country": country, "name": name,
                "file": os.path.relpath(fp, self.mod_path).replace("\\", "/")}

    def _sync_design(self, kind, data=None):
        self.ensure_mod()
        data = data or {}
        name = (data.get("name") or "").strip()
        dry_run = bool(data.get("dry_run", True))
        if not name:
            raise ValueError("缺少 name")
        variants = self._design_variants(kind)
        info = self._design_info(kind)
        mod = __import__("ship_design" if kind == "ship" else "plane_design"
                         if kind == "plane" else "tank_design",
                         fromlist=[info["apply"]])
        apply = getattr(mod, info["apply"])
        files = []
        for country, items in variants.items():
            v = items.get(name)
            if not v:
                continue
            type_key = v.get("type", "")
            modules = v.get("modules", {})
            fp, _ = self._load_variant_file_for(country)
            if not fp:
                continue
            content = self._read_text(fp)
            new_content = apply(content, name, modules, type_key=type_key)
            if new_content is None or new_content == content:
                continue
            rel = os.path.relpath(fp, self.mod_path).replace("\\", "/")
            files.append({"path": rel, "country": country,
                          "summary": "sync modules for %s" % name})
            if not dry_run:
                self._write_text(fp, new_content)
                self._notify_change(fp)
        if not dry_run:
            self._design_refresh(kind)
        return {"ok": True, "dry_run": dry_run, "count": len(files),
                "files": files}

    # ---------- 设计模板 ----------

    def list_design_templates(self, data=None):
        data = data or {}
        kind = (data.get("kind") or "").strip()
        from design_template import list_design_templates
        return {"ok": True, "kind": kind, "count": 0, "templates": []} \
            if not kind else {"ok": True, "kind": kind,
                              "count": len(list_design_templates(kind)),
                              "templates": list_design_templates(kind)}

    def save_design_template(self, data=None):
        data = data or {}
        kind = (data.get("kind") or "").strip()
        name = (data.get("name") or "").strip()
        content = data.get("content") or ""
        if not kind or not name or not content:
            raise ValueError("需要 kind/name/content")
        from design_template import save_design_template
        path = save_design_template(kind, name, content)
        if not path:
            raise ValueError("保存设计模板失败")
        return {"ok": True, "path": path}

    def load_design_template(self, data=None):
        data = data or {}
        kind = (data.get("kind") or "").strip()
        name = (data.get("name") or "").strip()
        if not kind or not name:
            raise ValueError("需要 kind/name")
        from design_template import load_design_template
        content = load_design_template(kind, name)
        if content is None:
            raise ValueError("未找到设计模板 %s/%s" % (kind, name))
        return {"ok": True, "kind": kind, "name": name, "content": content}

    # ---------- OOB ----------

    def list_oob_files(self, data=None):
        self.ensure_mod()
        data = data or {}
        out = []
        seen = set()
        for base, source in ((self.mod_path, "mod"), (self.game_path, "game")):
            if not base:
                continue
            d = os.path.join(base, "history", "units")
            if not os.path.isdir(d):
                continue
            for root, _dirs, names in os.walk(d):
                for fn in sorted(names):
                    if not fn.lower().endswith(".txt"):
                        continue
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, self.mod_path if source == "mod" else base)
                    rel = rel.replace("\\", "/")
                    if rel in seen:
                        continue
                    seen.add(rel)
                    try:
                        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                            content = f.read()
                    except Exception:
                        content = ""
                    from oob_loader import detect_oob_kinds
                    kinds = detect_oob_kinds(content)
                    out.append({"path": rel, "source": source, "kinds": kinds,
                                "size": len(content)})
        return {"ok": True, "count": len(out), "files": out}

    def _oob_read_path(self, rel):
        # 只读：mod 优先，回退游戏（不复制到 mod）
        fp = os.path.join(self.mod_path, rel)
        if os.path.isfile(fp):
            return fp
        if self.game_path:
            gfp = os.path.join(self.game_path, rel)
            if os.path.isfile(gfp):
                return gfp
        return None

    def _oob_write_path(self, rel):
        # 写：mod 优先，否则自动复制原版到 mod
        fp = os.path.join(self.mod_path, rel)
        if os.path.isfile(fp):
            return fp
        if self.game_path:
            gfp = os.path.join(self.game_path, rel)
            if os.path.isfile(gfp):
                from state_build_ops import ensure_file_in_mod
                mod_fp, _copied = ensure_file_in_mod(
                    self.mod_path, self.game_path, rel)
                return mod_fp
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        return fp

    def list_division_templates(self, data=None):
        self.ensure_mod()
        data = data or {}
        rel = (data.get("path") or "").strip()
        from oob_loader import OobFile, division_stats, load_sub_units, load_equipment_stats
        sub_units = load_sub_units(self.mod_path, self.game_path)
        equip_stats = load_equipment_stats(self.mod_path, self.game_path)
        out = []
        if rel:
            fp = self._oob_read_path(rel)
            if not fp:
                raise ValueError("文件不存在: " + rel)
            ob = OobFile(fp)
            for t in ob.templates:
                out.append({"path": rel, "name": t.name, "is_locked": t.is_locked,
                            "regiments": t.regiments, "support": t.support,
                            "stats": division_stats(t, sub_units, equip_stats)})
        else:
            for f in self.list_oob_files()["files"]:
                if not f["kinds"].get("army"):
                    continue
                fp = self._oob_read_path(f["path"])
                if not fp:
                    continue
                try:
                    ob = OobFile(fp)
                except Exception:
                    continue
                for t in ob.templates:
                    out.append({"path": f["path"], "name": t.name,
                                "is_locked": t.is_locked, "regiments": t.regiments,
                                "support": t.support,
                                "stats": division_stats(t, sub_units, equip_stats)})
        return {"ok": True, "count": len(out), "templates": out}

    def get_division_template(self, data=None):
        self.ensure_mod()
        data = data or {}
        rel = (data.get("path") or "").strip()
        name = (data.get("name") or "").strip()
        if not rel or not name:
            raise ValueError("需要 path/name")
        fp = self._oob_read_path(rel)
        if not fp:
            raise ValueError("文件不存在: " + rel)
        from oob_loader import OobFile, division_stats, load_sub_units, load_equipment_stats
        ob = OobFile(fp)
        t = ob.find_template(name)
        if not t:
            raise ValueError("未找到编制 %s" % name)
        return {"ok": True, "path": rel, "name": name, "is_locked": t.is_locked,
                "regiments": t.regiments, "support": t.support,
                "raw": t.raw_block,
                "stats": division_stats(t, load_sub_units(self.mod_path, self.game_path),
                                        load_equipment_stats(self.mod_path, self.game_path))}

    def create_division_template(self, data=None):
        self.ensure_mod()
        data = data or {}
        rel = (data.get("path") or "").strip()
        name = (data.get("name") or "").strip()
        if not rel or not name:
            raise ValueError("需要 path/name")
        fp = self._oob_write_path(rel)
        if not fp:
            raise ValueError("文件不存在: " + rel)
        from oob_loader import OobFile, DivisionTemplate
        ob = OobFile(fp)
        if ob.find_template(name):
            raise ValueError("编制已存在: %s" % name)
        units = []
        for u in data.get("units") or []:
            units.append((u.get("type", ""), int(u.get("x", 0)), int(u.get("y", 0))))
        support = []
        for u in data.get("support") or []:
            support.append((u.get("type", ""), int(u.get("x", 0)), int(u.get("y", 0))))
        t = DivisionTemplate(name=name, is_locked=bool(data.get("is_locked", False)),
                             regiments=units, support=support)
        t.modified = True
        ob.add_template(t)
        ob.save()
        self._notify_change(fp)
        return {"ok": True, "path": rel, "name": name}

    def update_division_template(self, data=None):
        self.ensure_mod()
        data = data or {}
        rel = (data.get("path") or "").strip()
        name = (data.get("name") or "").strip()
        if not rel or not name:
            raise ValueError("需要 path/name")
        fp = self._oob_write_path(rel)
        if not fp:
            raise ValueError("文件不存在: " + rel)
        from oob_loader import OobFile, DivisionTemplate
        ob = OobFile(fp)
        t = ob.find_template(name)
        if not t:
            raise ValueError("未找到编制 %s" % name)
        if "content" in data and data.get("content"):
            # 用解析后的新模板对象替换（内容必须是 division_template 块）
            from oob_loader import parse_division_templates
            parsed = parse_division_templates(data["content"].strip())
            if not parsed:
                raise ValueError("content 不是合法的 division_template 块")
            nt = parsed[0]
            nt.modified = True
            idx = ob.templates.index(t)
            ob.templates[idx] = nt
        else:
            if "units" in data:
                t.regiments = [(u.get("type", ""), int(u.get("x", 0)), int(u.get("y", 0)))
                               for u in data["units"]]
            if "support" in data:
                t.support = [(u.get("type", ""), int(u.get("x", 0)), int(u.get("y", 0)))
                             for u in data["support"]]
            if "is_locked" in data:
                t.is_locked = bool(data["is_locked"])
            t.modified = True
        ob.save()
        self._notify_change(fp)
        return {"ok": True, "path": rel, "name": name}

    def delete_division_template(self, data=None):
        self.ensure_mod()
        data = data or {}
        rel = (data.get("path") or "").strip()
        name = (data.get("name") or "").strip()
        if not rel or not name:
            raise ValueError("需要 path/name")
        fp = self._oob_write_path(rel)
        if not fp:
            raise ValueError("文件不存在: " + rel)
        from oob_loader import OobFile
        ob = OobFile(fp)
        if not ob.remove_template(name):
            raise ValueError("未找到编制 %s" % name)
        ob.save()
        self._notify_change(fp)
        return {"ok": True, "path": rel, "name": name}

    def list_sub_units(self, data=None):
        data = data or {}
        keyword = (data.get("keyword") or "").strip().lower()
        from oob_loader import load_sub_units
        items = load_sub_units(self.mod_path, self.game_path)
        out = []
        for key, info in items.items():
            if keyword and keyword not in key.lower() and \
                    keyword not in (info.get("abbreviation") or "").lower():
                continue
            out.append({"key": key, **info})
        return {"ok": True, "count": len(out), "sub_units": out}

    def search_equipment(self, data=None):
        data = data or {}
        keyword = (data.get("keyword") or "").strip().lower()
        category = (data.get("category") or "").strip().lower()
        from oob_loader import load_equipment_stats
        items = load_equipment_stats(self.mod_path, self.game_path)
        out = []
        for key, info in items.items():
            if keyword and keyword not in key.lower():
                continue
            if category and category not in key.lower():
                continue
            out.append({"key": key, **info})
        return {"ok": True, "count": len(out), "equipment": out}