"""ApiCore 扩展：本地化 / 词条（域 6）"""
from __future__ import annotations

import os


class LocToolsMixin:
    """本地化与词条工具。"""

    def search_localisation(self, data=None):
        data = data or {}
        keyword = (data.get("keyword") or data.get("key") or "").strip()
        language = (data.get("language") or "chi").strip().lower()
        if language in ("chi", "cn", "simp_chinese"):
            sub = "simp_chinese"
        elif language in ("eng", "en", "english"):
            sub = "english"
        else:
            sub = language
        from localization_mgr import load_loc_yml_dir
        cache = {}
        # mod 优先（后写覆盖游戏）
        for base in (self.game_path, self.mod_path):
            if not base:
                continue
            d = os.path.join(base, "localisation", sub)
            if os.path.isdir(d):
                load_loc_yml_dir(d, cache)
        out = []
        for key, val in cache.items():
            if keyword and keyword.lower() not in key.lower() \
                    and keyword.lower() not in val.lower():
                continue
            out.append({"key": key, "value": val})
        out.sort(key=lambda x: x["key"])
        return {"ok": True, "count": len(out), "items": out[:2000]}

    def list_missing_localisation(self, data=None):
        data = data or {}
        from validation import check_localisation_coverage
        missing = check_localisation_coverage(self.mod_path, self.game_path)
        return {"ok": True, "count": len(missing), "items": missing}

    def batch_fill_localisation(self, data=None):
        data = data or {}
        dry_run = bool(data.get("dry_run", True))
        from validation import check_localisation_coverage, fix_localisation_missing
        missing = check_localisation_coverage(self.mod_path, self.game_path)
        entries = data.get("entries") or {}
        if dry_run:
            files = [{
                "path": "localisation/simp_chinese/validation_mod_l_simp_chinese.yml",
                "summary": "%d 条缺失词条" % len(missing),
            }]
            if entries:
                files.append({
                    "path": "localisation/simp_chinese/api_batch_l_simp_chinese.yml",
                    "summary": "%d 条自定义词条" % len(entries),
                })
            return {"ok": True, "dry_run": True, "count": len(missing),
                    "missing": missing, "files": files}
        n, target = fix_localisation_missing(
            self.mod_path, self.game_path, missing)
        rel = os.path.relpath(target, self.mod_path).replace("\\", "/")
        self._notify_change(target)
        return {"ok": True, "dry_run": False, "count": n, "file": rel}

    def search_terms(self, data=None):
        data = data or {}
        from term_registry import get_term_registry
        reg = get_term_registry()
        items = reg.search(
            keyword=data.get("keyword", ""),
            node_type=data.get("node_type") or None,
            tag=data.get("tag") or None,
            limit=int(data.get("limit", 300) or 300))
        return {"ok": True, "count": len(items), "items": items}

    def get_term(self, data=None):
        data = data or {}
        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError("缺少 key")
        from term_registry import get_term_registry
        reg = get_term_registry()
        term = reg.get(key)
        if not term:
            raise ValueError("未找到词条: %s" % key)
        return {"ok": True, "term": term}

    def add_user_term(self, data=None):
        data = data or {}
        key = (data.get("key") or "").strip()
        cn = (data.get("cn") or "").strip()
        if not key or not cn:
            raise ValueError("需要 key/cn")
        from term_registry import get_term_registry
        reg = get_term_registry()
        reg.add_user_term(key, cn, data.get("node_type", "value"),
                          data.get("tags"), data.get("description", ""))
        return {"ok": True, "key": key}

    def update_user_term(self, data=None):
        data = data or {}
        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError("缺少 key")
        from term_registry import get_term_registry
        reg = get_term_registry()
        ok = reg.update_user_term(
            key, cn=data.get("cn"), node_type=data.get("node_type"),
            tags=data.get("tags"), description=data.get("description"))
        if not ok:
            raise ValueError("仅可更新用户自定义词条: %s" % key)
        return {"ok": True, "key": key}

    def remove_user_term(self, data=None):
        data = data or {}
        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError("缺少 key")
        from term_registry import get_term_registry
        reg = get_term_registry()
        ok = reg.remove_user_term(key)
        if not ok:
            raise ValueError("仅可删除用户自定义词条: %s" % key)
        return {"ok": True, "key": key}