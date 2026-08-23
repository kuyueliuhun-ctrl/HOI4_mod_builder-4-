"""ApiCore 扩展：校验 / 健康 / 撤销 / 覆盖（域 7）"""
from __future__ import annotations

import os


class HealthMixin:
    """健康检查、重复 id、撤销与覆盖报告。"""

    def health_check(self, data=None):
        data = data or {}
        from export_health import run_export_health_check
        report = run_export_health_check(
            self.mod_path, self.game_path,
            max_issues=int(data.get("max_issues", 500) or 500))
        return {"ok": True, "mod_path": report.mod_path,
                "hoi4_path": report.hoi4_path or "",
                "counts": report.counts,
                "issues": [i.to_dict() for i in report.issues]}

    def scan_duplicate_ids(self, data=None):
        data = data or {}
        raw = data.get("types") or "focus,event,dynamic_modifier,decision,character"
        if isinstance(raw, str):
            types = [x.strip() for x in raw.split(",") if x.strip()]
        else:
            types = list(raw)
        from unique_id_scanner import scan_duplicates
        dups = scan_duplicates(self.mod_path, self.game_path, types)
        return {"ok": True, "types": types, "duplicates": dups,
                "count": sum(len(v) for v in dups.values())}

    def undo_last_write(self, data=None):
        data = data or {}
        from undo_mgr import undo
        path, ok = undo()
        return {"ok": ok, "path": path}

    def get_undo_status(self, data=None):
        data = data or {}
        from undo_mgr import can_undo, get_undo_manager
        mgr = get_undo_manager()
        last = mgr._stack[-1] if getattr(mgr, "_stack", None) else None
        return {"ok": True, "can_undo": can_undo(),
                "last_file": last[0] if last else "",
                "last_time": ""}

    def coverage_report(self, data=None):
        data = data or {}
        from coverage_report import build_coverage_rows
        rows = build_coverage_rows(self.mod_path)
        return {"ok": True, "count": len(rows), "rows": rows}