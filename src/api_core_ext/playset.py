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
