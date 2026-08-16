# -*- coding: utf-8 -*-
"""通过 HTTP API 接口复现 mod（端到端接口验证 / 查漏补缺）

流程：
  1. 启动两个本地 API 服务：源服务（原 mod，只读）+ 目标服务（空目录，写入）
  2. 对每个内容类型：list_entities 读源 → get_entity 取块 → create_entity 写入目标
  3. 文件级类型（localisation/mod_descriptor/defines）用 create+update 两段式复现
  4. 输出：复现统计 + 接口缺口清单（保存为 接口复现报告.md）

运行：
    python tools/repro_via_api.py --source E:\\mods\\3228475937 [--target E:\\mods\\3228475937_repro]
"""

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api_server import ApiServer  # noqa: E402

# 跳过与其它类型同目录/无实体化意义的类型
SKIP_TYPES = {"generic", "gui_edit", "super_event"}


class ApiClient:
    """HTTP API 客户端（Bearer token）。"""

    def __init__(self, server):
        self._url = server.url()
        self._token = server.token

    def _req(self, method, path, body=None):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            self._url + path, data=data, method=method,
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode("utf-8"))
            except Exception:
                return {"ok": False, "error": f"HTTP {e.code}"}

    def list_entities(self, type_key):
        return self._req("GET", f"/api/entities?type={type_key}")

    def get_entity(self, type_key, entity_id):
        import urllib.parse
        return self._req("GET", f"/api/entities/{type_key}/{urllib.parse.quote(entity_id)}")

    def create_entity(self, type_key, entity_id, content, country=""):
        body = {"type": type_key, "id": entity_id, "content": content}
        if country:
            body["country"] = country
        return self._req("POST", "/api/entities", body)

    def update_entity(self, type_key, entity_id, content):
        import urllib.parse
        return self._req("PUT", f"/api/entities/{type_key}/{urllib.parse.quote(entity_id)}",
                         {"content": content})

    def create_project(self, data):
        return self._req("POST", "/api/project", data)

    def write_loc(self, tag, entries):
        return self._req("POST", "/api/localisation", {"tag": tag, "entries": entries})

    def templates(self, type_key=""):
        return self._req("GET", f"/api/templates?type={type_key}")


def main():
    parser = argparse.ArgumentParser(description="通过 HTTP API 复现 mod")
    parser.add_argument("--source", default=r"E:\mods\3228475937")
    parser.add_argument("--target", default=r"E:\mods\3228475937_repro")
    args = parser.parse_args()

    src_mod = os.path.abspath(args.source)
    dst_mod = os.path.abspath(args.target)
    if not os.path.isdir(src_mod):
        print(f"[错误] 源 mod 不存在: {src_mod}")
        sys.exit(1)
    if os.path.exists(dst_mod):
        shutil.rmtree(dst_mod)
    os.makedirs(dst_mod)

    src_server = ApiServer(mod_path=src_mod, port=8811, token="repro-src")
    dst_server = ApiServer(mod_path=dst_mod, port=8812, token="repro-dst")
    if not src_server.start() or not dst_server.start():
        print("[错误] 端口 8811/8812 被占用，请先关闭其它 API 实例")
        sys.exit(1)
    src = ApiClient(src_server)
    dst = ApiClient(dst_server)

    from workbench import CONTENT_TYPES

    report = []
    stats = []  # (type, 源文件数, 源实体数, 复现成功, 失败, 缺口说明)
    gaps = []   # [(type, 说明)]

    try:
        for c in CONTENT_TYPES:
            tkey = c[0]
            if tkey in SKIP_TYPES:
                continue
            # 源实体列表
            try:
                r = src.list_entities(tkey)
            except Exception as e:
                gaps.append((tkey, f"list_entities 失败: {e}"))
                continue
            if not r.get("ok"):
                gaps.append((tkey, f"list_entities: {r.get('error')}"))
                continue
            entities = r.get("entities", [])
            if not entities:
                stats.append((tkey, 0, 0, 0, 0, "源无实体"))
                continue

            ok_n = fail_n = 0
            fail_samples = []
            for ent in entities:
                eid = ent.get("id", "")
                try:
                    g = src.get_entity(tkey, eid)
                except Exception as e:
                    fail_n += 1
                    fail_samples.append(f"{eid}:get {e}")
                    continue
                if not g.get("ok"):
                    fail_n += 1
                    fail_samples.append(f"{eid}:{g.get('error')}")
                    continue
                content = g.get("content", "")
                try:
                    c_res = dst.create_entity(tkey, eid, content,
                                              country=ent.get("country", ""))
                except Exception as e:
                    fail_n += 1
                    fail_samples.append(f"{eid}:create {e}")
                    continue
                if c_res.get("ok"):
                    # 文件级类型：create 会添加缩进破坏格式，立即用原文整文件覆盖修正
                    if tkey in ("localisation", "mod_descriptor"):
                        try:
                            dst.update_entity(tkey, eid, content)
                        except Exception as e:
                            fail_n += 1
                            fail_samples.append(f"{eid}:fixup {e}")
                            continue
                    ok_n += 1
                else:
                    fail_n += 1
                    fail_samples.append(f"{eid}:{c_res.get('error')}")

            # 文件级类型：两段式复现（先建占位实体再整文件更新）
            if tkey in ("localisation", "mod_descriptor") and ok_n == 0 and fail_n > 0:
                pass

            gap_note = ""
            if tkey in ("localisation", "mod_descriptor"):
                gap_note = "文件级类型（create+update 两段式修正，缺专用文件端点）"
            elif tkey == "gfx_definition":
                gap_note = "gfx 文件为 spriteTypes 包装结构，实体化复现会破坏包装（缺口）"
            elif tkey == "defines":
                gap_note = "lua 格式块追加复现（无专用 lua 端点）"
            stats.append((tkey, len(set(e["file"] for e in entities)),
                          len(entities), ok_n, fail_n, gap_note))
            if fail_samples:
                gaps.append((tkey, "; ".join(fail_samples[:5]) +
                             (f"…（共 {fail_n} 条失败）" if fail_n > 5 else "")))
            print(f"  {tkey}: 实体 {len(entities)} → 成功 {ok_n} / 失败 {fail_n}",
                  flush=True)

        # ── 项目级联动 / 本地化 / 模板：验证写接口可用性 ──
        proj = dst.create_project({
            "country": "RPT", "focus_id": "RPT_probe", "name": "探针",
            "event": False, "decision": False, "icon": False, "localisation": True})
        stats.append(("_probe_project", 0, 0,
                      1 if proj.get("ok") else 0, 0 if proj.get("ok") else 1,
                      "create_focus_project 探针（仅验证接口，非源内容）"))
        loc = dst.write_loc("RPT", {"RPT_probe": "探针"})
        stats.append(("_probe_loc", 0, 0,
                      1 if loc.get("ok") else 0, 0 if loc.get("ok") else 1,
                      "write_localisation 探针"))
        tpl = dst.templates()
        tpl_ok = 1 if tpl.get("ok") else 0

        # ── 报告 ──
        lines = []
        lines.append("# 接口复现报告 · E:\\mods\\3228475937")
        lines.append("")
        lines.append(f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"- 源 mod：{src_mod}")
        lines.append(f"- 目标：{dst_mod}")
        lines.append(f"- 复现方式：仅通过 HTTP API（list/get/create/update/project/localisation）")
        lines.append("")
        lines.append("## 一、按类型复现统计")
        lines.append("")
        lines.append("| 类型 | 源文件数 | 源实体数 | 复现成功 | 失败 | 说明/缺口 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        total_ent = total_ok = total_fail = 0
        for t, nf, ne, ok, fail, note in stats:
            total_ent += ne
            total_ok += ok
            total_fail += fail
            lines.append(f"| {t} | {nf} | {ne} | {ok} | {fail} | {note} |")
        lines.append("")
        lines.append(f"合计实体 {total_ent}，复现成功 {total_ok}，失败 {total_fail}"
                     f"（成功率 {total_ok / max(total_ent, 1) * 100:.1f}%）")
        lines.append("")
        lines.append("## 二、接口缺口清单（查漏补缺）")
        lines.append("")
        if gaps:
            for t, note in gaps:
                lines.append(f"- **{t}**：{note}")
        else:
            lines.append("（无失败项）")
        lines.append("")
        lines.append("## 三、结构性缺口（接口设计层面）")
        lines.append("")
        lines.append("1. **文件级操作端点缺失**：复现无法还原源 mod 的目录/文件组织"
                     "（实体被集中写入国家匹配/首个/新建文件），"
                     "缺少 `POST /api/files`（按指定路径写入整文件）与 `GET /api/files?type=`（文件列表）；"
                     "localisation/mod_descriptor 需两段式 create+update hack");
        lines.append("2. **gfx_definition 无法通过实体接口复现**：.gfx 为 spriteTypes 包装结构，"
                     "追加式写入会破坏包装；需要文件级或专用 sprite 端点");
        lines.append("3. **defines（.lua）无专用端点**：块追加可复现但依赖 PDX 大括号语法与 lua 兼容，"
                     "游戏 define 值类型（数值/数组）未校验");
        lines.append("4. **无批量端点**：上千实体需逐个请求（本次 "
                     f"{total_ent} 次 get + {total_ent} 次 create），建议增加批量 list-with-content "
                     "或 POST /api/entities/batch");
        lines.append("5. **无实体删除确认/干跑模式**：复现失败可回滚（撤销管理器），但无 dry-run 校验");
        lines.append("")
        lines.append("## 四、模板接口")
        lines.append("")
        lines.append(f"- list_templates：{'可用' if tpl_ok else '不可用'}（返回 {tpl.get('count', 0)} 条）")
        lines.append("")
        report_text = "\n".join(lines)
        with open(os.path.join(ROOT, "接口复现报告.md"), "w", encoding="utf-8") as f:
            f.write(report_text)
        print(report_text)
    finally:
        src_server.stop()
        dst_server.stop()


if __name__ == "__main__":
    main()
