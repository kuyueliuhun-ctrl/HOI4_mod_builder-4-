"""ApiCore 扩展：B3 补充 RHoiScribe 缺失能力（环境发现/符号/解释/块级编辑/红黄绿/修复）。

实现类 `RhoGapMixin`，组合进 ApiCore。依赖 ApiCore 既有：
- self.mod_path / self.game_path / self.ensure_mod() / self._safe_join / self._notify_change
- self.validate() / self.health_check()（来自 HealthMixin / base）
"""

from __future__ import annotations

import os


def _diff_preview(old, new, context=3, max_lines=24):
    """简单 unified diff 预览（限制行数）。"""
    import difflib
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                     lineterm="", n=context))
    if len(diff) > max_lines:
        diff = diff[:max_lines] + ["... (%d 行被截断)" % (len(diff) - max_lines)]
    return "\n".join(diff)


class RhoGapMixin:
    """RHoiScribe 缺失能力：环境发现 / 符号 / 解释 / 块级编辑 / 红黄绿 / 修复。"""

    def discover_environment(self):
        """环境发现：游戏/mod/可执行/文档/error_log/版本（尽力而为）。"""
        game = self.game_path or ""
        exe = ""
        if game:
            for n in ("hoi4.exe", "dowser.exe"):
                c = os.path.join(game, n)
                if os.path.isfile(c):
                    exe = c
                    break
        docs = ""
        home = os.path.expanduser("~")
        candidate = os.path.join(home, "Documents", "Paradox Interactive",
                                 "Hearts of Iron IV")
        if os.path.isdir(candidate):
            docs = candidate
        error_log = ""
        for base in (docs, game):
            if not base:
                continue
            for rel in ("logs/error.log", "error.log"):
                p = os.path.join(base, rel)
                if os.path.isfile(p):
                    error_log = p
                    break
        version = ""
        if game:
            ver_file = os.path.join(game, "launcher-settings.json")
            if os.path.isfile(ver_file):
                try:
                    import json as _json
                    with open(ver_file, "r", encoding="utf-8-sig") as f:
                        launcher = _json.load(f)
                    version = str(launcher.get("version", ""))
                except Exception:
                    version = ""
        return {
            "mod_path": self.mod_path,
            "game_path": game,
            "game_executable_path": exe,
            "game_version": version or "未知",
            "document_path": docs,
            "error_log_path": error_log,
        }

    def list_workspace_symbols(self, data):
        self.ensure_mod()
        from project_symbols import scan_workspace
        entries = scan_workspace(
            self.mod_path, self.game_path,
            keyword=str(data.get("keyword", "")),
            limit=int(data.get("limit", 500) or 500),
            include_game=bool(data.get("include_game", False)))
        return {"ok": True, "count": len(entries), "symbols": entries}

    def find_definition(self, data):
        self.ensure_mod()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("缺少 name")
        from project_symbols import find_definition as _fd
        r = _fd(name, self.mod_path, self.game_path,
                include_game=bool(data.get("include_game", False)))
        return {"ok": True, "definition": r}

    def find_references(self, data):
        self.ensure_mod()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("缺少 name")
        from project_symbols import find_references as _fr
        refs = _fr(name, self.mod_path, self.game_path,
                   limit=int(data.get("limit", 200) or 200),
                   include_game=bool(data.get("include_game", False)))
        return {"ok": True, "count": len(refs), "references": refs}

    def suggest_completion(self, data):
        self.ensure_mod()
        from project_symbols import suggest_completion as _sc
        cands = _sc(str(data.get("prefix", "")), self.mod_path, self.game_path,
                    limit=int(data.get("limit", 50) or 50),
                    include_game=bool(data.get("include_game", False)))
        return {"ok": True, "count": len(cands), "candidates": cands}

    def explain_diagnostic(self, data):
        """解释一条诊断：归类 + 可能原因 + 修复建议（不写文件）。"""
        raw = str(data.get("diagnostic", "")).strip()
        if not raw:
            raise ValueError("缺少 diagnostic")
        low = raw.lower()
        from error_log import classify_by_subsystem
        subsystem = ""
        try:
            cats = classify_by_subsystem([{"category": "error",
                                           "message": raw}])
            if cats:
                subsystem = next(iter(cats))
        except Exception:
            subsystem = ""
        repair = []
        if any(k in low for k in ("localisation", "localization", "本地化")):
            repair.append("补充 localisation/<lang>_l_<lang>.yml 词条，或运行 "
                          "batch_fill_localisation / generate_missing_localisation 生成候选。")
        if "duplicate" in low or "重复" in raw:
            repair.append("用 scan_duplicate_ids 定位重复 id 并重命名其中一个。")
        if "brace" in low or "括号" in raw or "balance" in low:
            repair.append("检查块花括号配对；edit_script_file 的 replace 可整体重建该块。")
        if "gfx" in low or "sprite" in low or "icon" in low:
            repair.append("确认 gfx/*.gfx 已注册 spriteType 且贴图路径存在；可运行 register_icon_batch。")
        if ("focus" in low and "refer" in low) or ("国策" in raw and "引用" in raw):
            repair.append("检查国策前置/完成奖励引用的 id 是否存在（validate_mod 的 focus_references）。")
        if not repair:
            repair.append("用 analyze_error_log 归类 error.log；若为脚本语义问题，检查 scope 与字段类型。")
        return {"ok": True, "subsystem": subsystem or "general",
                "likely_cause": raw,
                "repair_guidance": repair}

    def edit_script_file(self, data):
        """块级编辑已有脚本文件：{path, block, action, content, after_id?, dry_run}
        action=replace 替换命名块内部文本；action=insert 在 after_id 后插入新块。
        花括号不平衡禁止写入；dry_run 返回 diff 预览。"""
        self.ensure_mod()
        rel = str(data.get("path", "")).strip()
        block = str(data.get("block", "")).strip()
        action = str(data.get("action", "replace")).strip()
        content = str(data.get("content", ""))
        after_id = str(data.get("after_id", "")).strip() or None
        dry_run = bool(data.get("dry_run", True))
        fp = self._safe_join(rel)
        if not fp or not os.path.isfile(fp):
            raise ValueError("文件不存在: " + rel)
        with open(fp, "r", encoding="utf-8-sig") as f:
            original = f.read()
        if action == "replace":
            if not block:
                raise ValueError("replace 需要 block 名")
            from ai_loader_crud import replace_block_body
            patched = replace_block_body(original, block,
                                         content.strip("\n"))
        elif action == "insert":
            if not block or not content.strip():
                raise ValueError("insert 需要 block 名与 content")
            from ai_loader_crud import insert_top_block
            patched = insert_top_block(original, content, after_id=after_id)
        else:
            raise ValueError("action 只能是 replace / insert")
        if patched == original:
            return {"ok": True, "dry_run": dry_run, "changed": False,
                    "path": rel, "message": "无变化（块未命中）"}
        if patched.count("{") != patched.count("}"):
            raise ValueError("编辑后花括号不平衡，已阻止写入")
        preview = _diff_preview(original, patched)
        if dry_run:
            return {"ok": True, "dry_run": True, "changed": True,
                    "path": rel, "block": block, "action": action,
                    "diff": preview}
        from write_utils import atomic_write_text
        atomic_write_text(fp, patched, encoding="utf-8")
        self._notify_change(fp)
        return {"ok": True, "dry_run": False, "changed": True,
                "path": rel, "block": block, "action": action,
                "diff": preview}

    def validate_project(self, data=None):
        """红黄绿项目校验：封装 validate() + health_check() 并按严重度分桶。"""
        data = data or {}
        self.ensure_mod()
        v = self.validate()
        h = self.health_check({"max_issues": int(data.get("max_issues", 500) or 500)})
        red = []
        yellow = []
        s = v.get("summary", {})
        if s.get("duplicate_count"):
            red.append({"check": "duplicate_ids",
                        "count": s["duplicate_count"]})
        if s.get("unknown_reference_count"):
            yellow.append({"check": "unknown_references",
                           "count": s["unknown_reference_count"]})
        if s.get("localisation_missing_count"):
            yellow.append({"check": "localisation_missing",
                           "count": s["localisation_missing_count"]})
        if s.get("focus_dangling_count"):
            yellow.append({"check": "focus_dangling",
                           "count": s["focus_dangling_count"]})
        counts = h.get("counts") or {}
        if isinstance(counts, dict):
            red_count = counts.get("error", 0)
            yellow_count = counts.get("warning", 0)
            if red_count:
                red.append({"check": "health_errors", "count": red_count})
            if yellow_count:
                yellow.append({"check": "health_warnings",
                               "count": yellow_count})
        green = len(v.get("unknown_references", {})) or 0
        return {"ok": True, "red": red, "yellow": yellow,
                "green_ok": green,
                "summary": {"red": len(red), "yellow": len(yellow),
                            "green": green,
                            "note": "red=须修复；yellow=建议修复；green=已通过检查项数"}}

    def repair_project(self, data=None):
        """项目修复：{dry_run, bom} —— 移除 .txt/.gfx/.gui 的 UTF-8 BOM。
        dry_run 返回需修复文件清单，不写盘。"""
        data = data or {}
        self.ensure_mod()
        dry_run = bool(data.get("dry_run", True))
        do_bom = bool(data.get("bom", True))
        skip = {".git", "__pycache__", ".runtime", ".idea", ".venv",
                ".jspace", "node_modules"}
        bom_files = []
        for dp, dirs, names in os.walk(self.mod_path):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in names:
                if not name.lower().endswith((".txt", ".gfx", ".gui")):
                    continue
                fp = os.path.join(dp, name)
                try:
                    with open(fp, "rb") as f:
                        head = f.read(3)
                except Exception:
                    continue
                if do_bom and head.startswith(b"\xef\xbb\xbf"):
                    bom_files.append(
                        os.path.relpath(fp, self.mod_path).replace("\\", "/"))
        applied = []
        if not dry_run and bom_files:
            from write_utils import atomic_write_text
            for rel in bom_files:
                fp = os.path.join(self.mod_path, rel.replace("/", os.sep))
                with open(fp, "r", encoding="utf-8-sig") as f:
                    text = f.read()
                atomic_write_text(fp, text, encoding="utf-8")
                applied.append(rel)
        return {"ok": True, "dry_run": dry_run,
                "bom_remove": sorted(bom_files),
                "applied": sorted(applied),
                "summary": {"bom": len(bom_files),
                            "applied": len(applied),
                            "note": "BOM 规范化：非 localisation 文本不应带 BOM"}}
