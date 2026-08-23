"""ApiCore 扩展：力量平衡 BOP（域 5）"""
from __future__ import annotations

import os


class BopMixin:
    """BOP 查询与写回。"""

    def list_bop(self, data=None):
        data = data or {}
        from bop_loader import load_bop_definitions
        bops = load_bop_definitions(self.mod_path, self.game_path)
        out = []
        for tag, b in bops.items():
            out.append({
                "tag": tag,
                "id": b.get("id", ""),
                "initial_value": b.get("initial_value"),
                "left_side": b.get("left_side", ""),
                "right_side": b.get("right_side", ""),
                "decision_category": b.get("decision_category", ""),
                "range_count": len(b.get("ranges", [])),
                "side_count": len(b.get("sides", [])),
                "file": b.get("file", ""),
            })
        return {"ok": True, "count": len(out), "items": out}

    def get_bop(self, data=None):
        data = data or {}
        bop_id = (data.get("bop_id") or data.get("tag") or "").strip()
        if not bop_id:
            raise ValueError("缺少 bop_id")
        from bop_loader import load_bop_definitions, load_bop_actions, find_active_range
        bops = load_bop_definitions(self.mod_path, self.game_path)
        bop = bops.get(bop_id.upper())
        if not bop:
            raise ValueError("未找到 BOP: %s" % bop_id)
        actions = load_bop_actions(self.mod_path, self.game_path,
                                   bop.get("decision_category", ""))
        side, rng = find_active_range(bop, bop.get("initial_value", 0.0))
        return {"ok": True, "bop": bop, "actions": actions,
                "active_side": side, "active_range": rng}

    def set_bop_initial_value(self, data=None):
        data = data or {}
        bop_id = (data.get("bop_id") or "").strip()
        value = data.get("value")
        if not bop_id or value is None:
            raise ValueError("需要 bop_id/value")
        from bop_loader import set_bop_initial_value
        r = set_bop_initial_value(self.mod_path, self.game_path, bop_id, value)
        self._notify_change(os.path.join(self.mod_path, r["file"].replace("/", os.sep)))
        return {"ok": True, **r}

    def set_bop_fields(self, data=None):
        data = data or {}
        bop_id = (data.get("bop_id") or "").strip()
        if not bop_id:
            raise ValueError("缺少 bop_id")
        from bop_loader import set_bop_fields
        r = set_bop_fields(
            self.mod_path, self.game_path, bop_id,
            left_side=data.get("left_side"),
            right_side=data.get("right_side"),
            decision_category=data.get("decision_category"))
        self._notify_change(os.path.join(self.mod_path, r["file"].replace("/", os.sep)))
        return {"ok": True, **r}