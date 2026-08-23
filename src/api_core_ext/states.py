"""ApiCore 扩展：州 / 建筑 / 区域 / 归属（域 1）

纯数据层编排，不依赖 QtWidgets；所有写操作走已有数据层原子写。
"""
from __future__ import annotations

import os
import re


class StatesMixin:
    """州/建筑/区域查询与写回。"""

    # ---------- 内部辅助 ----------

    def _state_data(self):
        from state_loader import StateData
        return StateData(self.mod_path, self.game_path)

    def _state_file_for(self, state_id):
        from state_build_ops import _state_file_for
        sd = self._state_data()
        return _state_file_for(self.mod_path, self.game_path, int(state_id), sd)

    def _province_meta(self, pid):
        """从 definition.csv 读取省类型/地形/沿海（轻量解析，不碰位图）。"""
        rows = {}
        for base in (self.mod_path, self.game_path):
            if not base:
                continue
            fp = os.path.join(base, "map", "definition.csv")
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or ";" not in line:
                            continue
                        parts = line.split(";")
                        if not parts[0].strip().isdigit():
                            continue
                        if int(parts[0].strip()) == int(pid):
                            rows = {
                                "type": parts[1].strip() if len(parts) > 1 else "",
                                "terrain": parts[6].strip() if len(parts) > 6 else "",
                                "coastal": parts[7].strip().lower() in ("yes", "true", "1")
                                if len(parts) > 7 else False,
                            }
                            return rows
            except Exception:
                continue
        return {"type": "", "terrain": "", "coastal": False}

    # ---------- 查询 ----------

    def list_states(self, data=None):
        self.ensure_mod()
        data = data or {}
        owner = (data.get("owner") or "").strip().upper()
        keyword = (data.get("keyword") or "").strip()
        sd = self._state_data()
        out = []
        for sid, info in sd.states.items():
            if owner and info.get("owner") != owner:
                continue
            if keyword and keyword.lower() not in "{0} {1} {2}".format(
                    sid, info.get("name_key", ""), sd.state_name(sid)).lower():
                continue
            out.append({
                "id": sid,
                "name": sd.state_name(sid),
                "owner": info.get("owner", ""),
                "provinces": len(info.get("provinces") or []),
                "category": info.get("state_category", ""),
                "manpower": info.get("manpower", 0),
                "src": info.get("src", ""),
            })
        out.sort(key=lambda x: x["id"])
        return {"ok": True, "count": len(out), "states": out}

    def get_state(self, data=None):
        self.ensure_mod()
        data = data or {}
        try:
            sid = int(data.get("state_id"))
        except (TypeError, ValueError):
            raise ValueError("缺少或非法的 state_id")
        sd = self._state_data()
        info = sd.states.get(sid)
        if not info:
            raise ValueError("未找到州: %d" % sid)
        return {
            "ok": True,
            "state": {
                "id": sid,
                "name": sd.state_name(sid),
                "name_key": info.get("name_key", ""),
                "owner": info.get("owner", ""),
                "provinces": list(info.get("provinces") or []),
                "naval": dict(info.get("naval") or {}),
                "air_level": info.get("air_level", 0),
                "category": info.get("state_category", ""),
                "manpower": info.get("manpower", 0),
                "buildings": info.get("buildings", {}),
                "buildings_pid": info.get("buildings_pid", {}),
                "victory_points": list(info.get("victory_points") or []),
                "slots": sd.slots_of(sid),
                "src": info.get("src", ""),
            },
        }

    def get_province(self, data=None):
        self.ensure_mod()
        data = data or {}
        try:
            pid = int(data.get("province_id"))
        except (TypeError, ValueError):
            raise ValueError("缺少或非法的 province_id")
        sd = self._state_data()
        sid = sd.state_of_province(pid)
        meta = self._province_meta(pid)
        owner = sd.owner_of_province(pid)
        state = None
        if sid:
            info = sd.states.get(sid)
            state = {
                "id": sid,
                "name": sd.state_name(sid),
                "owner": info.get("owner", "") if info else "",
                "category": info.get("state_category", "") if info else "",
            }
        return {
            "ok": True,
            "province": {
                "id": pid,
                "state_id": sid,
                "owner": owner,
                "type": meta["type"],
                "terrain": meta["terrain"],
                "coastal": meta["coastal"],
                "state": state,
            },
        }

    def get_owner_provinces(self, data=None):
        self.ensure_mod()
        data = data or {}
        tag = (data.get("tag") or "").strip().upper()
        sd = self._state_data()
        mapping = sd.owner_province_map()
        if tag:
            if tag not in mapping:
                raise ValueError("未找到该国家拥有的地块: %s" % tag)
            return {"ok": True, "tag": tag, "count": len(mapping[tag]),
                    "province_ids": mapping[tag]}
        return {"ok": True, "count": len(mapping), "owners": {
            k: v for k, v in sorted(mapping.items())}}

    # ---------- 写回 ----------

    def set_state_owner(self, data=None):
        self.ensure_mod()
        data = data or {}
        try:
            sid = int(data.get("state_id"))
        except (TypeError, ValueError):
            raise ValueError("缺少或非法的 state_id")
        tag = (data.get("tag") or "").strip().upper()
        if not tag:
            raise ValueError("缺少 tag")
        from state_edit_ops import set_state_owner
        ok, msg, rel = set_state_owner(
            self.mod_path, sid, tag, state_data=self._state_data())
        if not ok:
            raise ValueError("设置州归属失败: %s" % msg)
        self._state_data().reload()
        self._notify_change(os.path.join(self.mod_path, rel.replace("/", os.sep)))
        return {"ok": True, "state_id": sid, "tag": tag, "message": msg,
                "file": rel}

    def set_state_building(self, data=None):
        self.ensure_mod()
        data = data or {}
        try:
            sid = int(data.get("state_id"))
            level = int(data.get("level"))
        except (TypeError, ValueError):
            raise ValueError("state_id 与 level 必须为整数")
        btype = (data.get("building") or "").strip()
        if not btype:
            raise ValueError("缺少 building")
        pid = data.get("province_id")
        if pid is not None:
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                raise ValueError("province_id 必须为整数")
        from state_build_ops import set_state_building
        ok, msg, rel = set_state_building(
            self.mod_path, self.game_path, sid, btype, level, pid=pid,
            state_data=self._state_data())
        if not ok:
            raise ValueError("设置州建筑失败: %s" % msg)
        self._state_data().reload()
        self._notify_change(os.path.join(self.mod_path, rel.replace("/", os.sep)))
        return {"ok": True, "state_id": sid, "building": btype, "level": level,
                "province_id": pid, "message": msg, "file": rel}

    def set_state_category(self, data=None):
        self.ensure_mod()
        data = data or {}
        try:
            sid = int(data.get("state_id"))
        except (TypeError, ValueError):
            raise ValueError("缺少或非法的 state_id")
        category = (data.get("category") or "").strip()
        if not category:
            raise ValueError("缺少 category")
        from state_build_ops import set_state_category
        ok, msg, rel = set_state_category(
            self.mod_path, self.game_path, sid, category,
            state_data=self._state_data())
        if not ok:
            raise ValueError("设置州类别失败: %s" % msg)
        self._state_data().reload()
        self._notify_change(os.path.join(self.mod_path, rel.replace("/", os.sep)))
        return {"ok": True, "state_id": sid, "category": category,
                "message": msg, "file": rel}

    def set_country_color(self, data=None):
        self.ensure_mod()
        data = data or {}
        tag = (data.get("tag") or "").strip().upper()
        try:
            rgb = [int(data.get("r")), int(data.get("g")), int(data.get("b"))]
        except (TypeError, ValueError):
            raise ValueError("r/g/b 必须为 0-255 整数")
        if not tag or not all(0 <= v <= 255 for v in rgb):
            raise ValueError("tag 与 r/g/b 必须提供且颜色值在 0-255")
        from state_build_ops import set_country_color
        ok, msg, rel = set_country_color(
            self.mod_path, self.game_path, tag, tuple(rgb))
        if not ok:
            raise ValueError("设置国家颜色失败: %s" % msg)
        self._notify_change(os.path.join(self.mod_path, rel.replace("/", os.sep)))
        return {"ok": True, "tag": tag, "rgb": rgb, "message": msg, "file": rel}

    def list_building_types(self, data=None):
        data = data or {}
        from building_lib import load_building_types
        items = load_building_types(self.mod_path, self.game_path)
        return {"ok": True, "count": len(items), "building_types": items}

    def list_country_colors(self, data=None):
        data = data or {}
        from building_lib import load_country_colors
        colors = load_country_colors(self.mod_path, self.game_path)
        return {"ok": True, "count": len(colors), "colors": colors}

    def batch_set_state_fields(self, data=None):
        """批量设置州字段（manpower/resources/state_category 等）。

        默认 dry_run=true 只返回将写入文件与内容摘要。
        """
        self.ensure_mod()
        data = data or {}
        state_ids = data.get("state_ids") or []
        field = (data.get("field") or "").strip()
        value = data.get("value")
        dry_run = bool(data.get("dry_run", True))
        if not state_ids or not field or value is None:
            raise ValueError("需要 state_ids/field/value")
        from state_batch import set_field_for_states
        sd = self._state_data()
        by_file = {}
        for sid in state_ids:
            path, _ = self._state_file_for(sid)
            if not path:
                raise ValueError("无法定位州文件: %s" % sid)
            by_file.setdefault(path, {})[str(sid)] = str(value)
        files = []
        for path, fvals in by_file.items():
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
            new_content = set_field_for_states(content, fvals, field)
            rel = os.path.relpath(path, self.mod_path).replace("\\", "/")
            changed = new_content != content
            files.append({
                "path": rel,
                "changed": changed,
                "summary": "%s = %s" % (field, value),
            })
            if not dry_run and changed:
                from write_utils import atomic_write_text
                atomic_write_text(path, new_content)
                self._notify_change(path)
        if not dry_run:
            sd.reload()
        return {"ok": True, "dry_run": dry_run, "count": len(files),
                "files": files}

    def sort_state_file(self, data=None):
        self.ensure_mod()
        data = data or {}
        rel = (data.get("path") or "").strip()
        fp = self._safe_join(rel)
        if not fp or not os.path.isfile(fp):
            raise ValueError("文件不存在: " + rel)
        from pdx_sorter import sort_state_file
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        new_content = sort_state_file(content)
        if new_content != content:
            from write_utils import atomic_write_text
            atomic_write_text(fp, new_content)
            self._notify_change(fp)
        return {"ok": True, "path": rel, "changed": new_content != content}

    # ---------- 区域 ----------

    def list_regions(self, data=None):
        data = data or {}
        kinds = data.get("kind") or ""
        if kinds:
            kinds = [k.strip() for k in str(kinds).split(",") if k.strip()]
        else:
            kinds = ["strategic_region", "supply_area"]
        from map_region_ops import scan_region_files
        files = scan_region_files(self.mod_path, self.game_path, kinds=kinds)
        out = []
        for f in files:
            out.append({
                "kind": f["kind"],
                "rel": f["rel"],
                "source": f["source"],
                "regions": [{
                    "id": r["id"], "provinces": r["provinces"],
                } for r in f["regions"]],
            })
        return {"ok": True, "count": len(out), "files": out}

    def _region_file_for(self, kind, rid=None):
        """定位区域文件相对路径：包含 rid 优先，否则第一个该 kind 文件。"""
        from map_region_ops import scan_region_files
        files = scan_region_files(self.mod_path, self.game_path, kinds=[kind])
        if rid is not None:
            for f in files:
                if any(r["id"] == int(rid) for r in f["regions"]):
                    return f
        return files[0] if files else None

    def create_region(self, data=None):
        self.ensure_mod()
        data = data or {}
        kind = (data.get("kind") or "").strip()
        if kind not in ("strategic_region", "supply_area"):
            raise ValueError("kind 必须为 strategic_region 或 supply_area")
        province_ids = [int(x) for x in (data.get("province_ids") or [])]
        rid = data.get("region_id")
        if rid is not None:
            try:
                rid = int(rid)
            except (TypeError, ValueError):
                raise ValueError("region_id 必须为整数")
        from map_region_ops import append_region, next_region_id, parse_region_file
        found = self._region_file_for(kind)
        if found:
            rel = found["rel"]
            content = found["content"]
            regions = []
            for f in self.list_regions({"kind": kind})["files"]:
                for r in f["regions"]:
                    regions.append(r)
            if rid is None:
                rid = next_region_id(regions)
            new_content = append_region(content, kind, rid, province_ids)
        else:
            rel_dir = ("map/strategicregions" if kind == "strategic_region"
                       else "map/supplyareas")
            rel = "%s/%s.txt" % (rel_dir, "generated")
            os.makedirs(os.path.join(self.mod_path, rel_dir.replace("/", os.sep)),
                        exist_ok=True)
            content = ""
            if rid is None:
                rid = 1
            new_content = append_region(content, kind, rid, province_ids)
        fp = self._safe_join(rel)
        if not fp:
            fp = os.path.join(self.mod_path, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        from write_utils import atomic_write_text
        atomic_write_text(fp, new_content)
        self._notify_change(fp)
        return {"ok": True, "kind": kind, "region_id": rid, "file": rel,
                "provinces": province_ids}

    def set_region_provinces(self, data=None):
        self.ensure_mod()
        data = data or {}
        kind = (data.get("kind") or "").strip()
        try:
            rid = int(data.get("region_id"))
        except (TypeError, ValueError):
            raise ValueError("缺少或非法的 region_id")
        province_ids = [int(x) for x in (data.get("province_ids") or [])]
        from map_region_ops import set_region_provinces
        found = self._region_file_for(kind, rid)
        if not found:
            raise ValueError("未找到 %s 区域文件" % kind)
        content = found["content"]
        new_content = set_region_provinces(content, kind, rid, province_ids)
        if new_content is None:
            raise ValueError("设置区域失败")
        fp = self._safe_join(found["rel"])
        if not fp:
            raise ValueError("无法定位区域文件")
        from write_utils import atomic_write_text
        atomic_write_text(fp, new_content)
        self._notify_change(fp)
        return {"ok": True, "kind": kind, "region_id": rid,
                "file": found["rel"], "provinces": province_ids}

    def remove_region(self, data=None):
        self.ensure_mod()
        data = data or {}
        kind = (data.get("kind") or "").strip()
        try:
            rid = int(data.get("region_id"))
        except (TypeError, ValueError):
            raise ValueError("缺少或非法的 region_id")
        from map_region_ops import remove_region
        found = self._region_file_for(kind, rid)
        if not found:
            raise ValueError("未找到 %s 区域文件" % kind)
        new_content = remove_region(found["content"], kind, rid)
        if new_content is None:
            raise ValueError("未找到区域 %d" % rid)
        fp = self._safe_join(found["rel"])
        if not fp:
            raise ValueError("无法定位区域文件")
        from write_utils import atomic_write_text
        atomic_write_text(fp, new_content)
        self._notify_change(fp)
        return {"ok": True, "kind": kind, "region_id": rid, "file": found["rel"]}