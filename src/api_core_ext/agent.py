"""ApiCore 扩展：Agent 偏好持久化 + 工具审计日志（B3 批二②）。

- 偏好：`.runtime/agent_prefs.json`（dict），set/list/delete。
- 审计：`.runtime/tool_logs.jsonl`（JSON lines），query/export；`log_tool_call` 为埋点入口
  （由 MCP tools/call 与 HTTP /api/mcp 调用方调用，非公开 MCP 工具）。
存储均走原子写（write_utils），仅在项目 .runtime 下。
"""

from __future__ import annotations

import json
import os
import re
import time

from project_paths import PROJECT_ROOT

_RUNTIME = os.path.join(PROJECT_ROOT, ".runtime")


def _sanitize(obj, depth=0):
    """截断参数/结果，避免日志膨胀。"""
    if depth > 2:
        return "..."
    if isinstance(obj, dict):
        return {k: _sanitize(v, depth + 1)
                for k, v in list(obj.items())[:20]}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v, depth + 1) for v in obj[:20]]
    if isinstance(obj, str) and len(obj) > 200:
        return obj[:200] + "..."
    return obj


class AgentMixin:
    """Agent 偏好与工具审计日志。"""

    def _prefs_path(self):
        os.makedirs(_RUNTIME, exist_ok=True)
        return os.path.join(_RUNTIME, "agent_prefs.json")

    def _logs_path(self):
        os.makedirs(_RUNTIME, exist_ok=True)
        return os.path.join(_RUNTIME, "tool_logs.jsonl")

    def _read_prefs(self):
        try:
            with open(self._prefs_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def list_agent_preferences(self, data=None):
        prefs = self._read_prefs()
        return {"ok": True, "count": len(prefs), "preferences": prefs}

    def set_agent_preference(self, data):
        key = str(data.get("key", "")).strip()
        value = data.get("value")
        if not key:
            raise ValueError("缺少 key")
        prefs = self._read_prefs()
        prefs[key] = value
        from write_utils import atomic_write_text
        atomic_write_text(self._prefs_path(),
                          json.dumps(prefs, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        return {"ok": True, "key": key, "value": value}

    def delete_agent_preference(self, data):
        key = str(data.get("key", "")).strip()
        prefs = self._read_prefs()
        existed = key in prefs
        prefs.pop(key, None)
        from write_utils import atomic_write_text
        atomic_write_text(self._prefs_path(),
                          json.dumps(prefs, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        return {"ok": True, "key": key, "deleted": existed}

    def log_tool_call(self, name, args=None, ok=True):
        """工具调用审计埋点（内部调用）。失败静默。"""
        try:
            rec = {"ts": round(time.time(), 3), "tool": str(name),
                   "args": _sanitize(args or {}), "ok": bool(ok)}
            fp = self._logs_path()
            old = ""
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    old = f.read()
            except Exception:
                old = ""
            from write_utils import atomic_write_text
            body = (old.rstrip("\n") + "\n" if old.strip() else "") \
                + json.dumps(rec, ensure_ascii=False) + "\n"
            atomic_write_text(fp, body, encoding="utf-8")
        except Exception:
            pass

    def query_tool_logs(self, data=None):
        data = data or {}
        rx = str(data.get("regex", "")).strip()
        limit = int(data.get("limit", 200) or 200)
        rows = []
        try:
            with open(self._logs_path(), "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception:
            lines = []
        pat = None
        if rx:
            try:
                pat = re.compile(rx)
            except re.error:
                raise ValueError("正则无效: %s" % rx)
        for ln in lines:
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            if pat is not None and not pat.search(
                    json.dumps(rec, ensure_ascii=False)):
                continue
            rows.append(rec)
            if len(rows) >= limit:
                break
        return {"ok": True, "count": len(rows), "logs": rows}

    def export_tool_logs(self, data=None):
        r = self.query_tool_logs(data)
        text = "\n".join(
            json.dumps(x, ensure_ascii=False) for x in r["logs"])
        return {"ok": True, "count": r["count"], "text": text}