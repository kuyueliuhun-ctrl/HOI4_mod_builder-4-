"""ApiCore 扩展：CWT-lite 类型规则校验（B3 批二⑤）。

validate_hoi4_file：校验单个文件（path 或 content）；类型从路径推断或显式传 type。
validate_hoi4_project：扫描 mod 常见类型目录做批量红黄绿汇总。
规则库见 `src/cwt_lite_rules.py`（轻量替代，非 cwtools 全量）。
"""

from __future__ import annotations

import os


class CwtLiteMixin:
    """CWT-lite 类型规则校验。"""

    def validate_hoi4_file(self, data=None):
        data = data or {}
        from cwt_lite_rules import infer_type, validate_content
        path = str(data.get("path", "")).strip()
        content = str(data.get("content", ""))
        if path:
            fp = self._safe_join(path)
            if not fp or not os.path.isfile(fp):
                raise ValueError("文件不存在: " + path)
            with open(fp, "r", encoding="utf-8-sig") as f:
                content = f.read()
            type_key = str(data.get("type", "")).strip() or infer_type(path)
        else:
            if not content.strip():
                raise ValueError("需要 path 或 content")
            type_key = str(data.get("type", "")).strip() or None
        if not type_key:
            return {"ok": True, "type": None, "red": 0, "yellow": 0,
                    "issues": [{"severity": "yellow",
                                "message": "无法推断类型（可传 type）"}]}
        issues = validate_content(content, type_key)
        red = [i for i in issues if i["severity"] == "red"]
        yellow = [i for i in issues if i["severity"] == "yellow"]
        return {"ok": True, "type": type_key, "red": len(red),
                "yellow": len(yellow), "green": not red, "issues": issues}

    def validate_hoi4_project(self, data=None):
        data = data or {}
        max_files = int(data.get("max_files", 100) or 100)
        counts = {"red": 0, "yellow": 0, "files": 0}
        file_issues = []
        dirs = ["common/national_focus", "common/ideas", "common/decisions",
                "events", "history/states", "common/ideologies",
                "history/units",
                # B3 批三① 扩充：覆盖 33 类型目录
                "common/characters", "common/technologies", "common/buildings",
                "common/modifiers", "common/opinion_modifiers",
                "common/wargoals", "common/operations", "common/on_actions",
                "map/strategicregions", "map/supplyareas",
                "common/occupation_laws", "common/difficulty_settings",
                "common/game_rules", "common/autonomous_states",
                "common/dynamic_modifiers", "common/bookmarks",
                "common/intelligence_agencies", "common/scripted_effects",
                "common/scripted_triggers", "common/scripted_localisation",
                "common/countries", "history/countries",
                "common/state_category", "common/terrain", "common/resources",
                "common/units"]
        for rel_dir in dirs:
            base = os.path.join(self.mod_path, *rel_dir.split("/"))
            if not os.path.isdir(base):
                continue
            for dp, _dirs, names in os.walk(base):
                for name in sorted(names):
                    if not name.lower().endswith(".txt"):
                        continue
                    fp = os.path.join(dp, name)
                    rel = os.path.relpath(fp, self.mod_path).replace("\\", "/")
                    r = self.validate_hoi4_file({"path": rel})
                    counts["files"] += 1
                    counts["red"] += r["red"]
                    counts["yellow"] += r["yellow"]
                    if r["issues"]:
                        file_issues.append({"file": rel, "issues": r["issues"]})
                    if counts["files"] >= max_files:
                        break
                if counts["files"] >= max_files:
                    break
            if counts["files"] >= max_files:
                break
        return {"ok": True, "counts": counts, "file_issues": file_issues,
                "note": "CWT-lite：内置常见类型规则，非 cwtools 全量"}