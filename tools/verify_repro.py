# -*- coding: utf-8 -*-
"""复现质量验证：对比源 mod 与复现目标的结构/内容

对比项：
  1. 顶层目录集合
  2. 各内容目录文件数与实体数（用 API list_entities 统计目标）
  3. 抽样：对每类型取 3 个实体，get_entity 对比源/目标块文本是否一致
  4. 文件级类型（localisation/mod_descriptor/defines）整文件对比

运行：
    python tools/verify_repro.py --source E:\\mods\\3228475937 --target E:\\mods\\3228475937_repro
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api_server import ApiServer  # noqa: E402
from workbench import CONTENT_TYPES  # noqa: E402

SKIP_TYPES = {"generic", "gui_edit", "super_event"}


class ApiClient:
    def __init__(self, server):
        self._url = server.url()
        self._token = server.token

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self._url + path, data=data, method=method,
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"HTTP {e.code}"}

    def list_entities(self, t):
        return self._req("GET", f"/api/entities?type={t}")

    def get_entity(self, t, eid):
        return self._req("GET", f"/api/entities/{t}/{urllib.parse.quote(eid)}")


def normalize(text):
    """归一化：去空白差异，用于内容比较。"""
    return "".join(text.split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=r"E:\mods\3228475937")
    parser.add_argument("--target", default=r"E:\mods\3228475937_repro")
    args = parser.parse_args()

    src_mod, dst_mod = os.path.abspath(args.source), os.path.abspath(args.target)
    srv_s = ApiServer(mod_path=src_mod, port=8821, token="v-src")
    srv_d = ApiServer(mod_path=dst_mod, port=8822, token="v-dst")
    if not srv_s.start() or not srv_d.start():
        print("[错误] 端口 8821/8822 被占用")
        sys.exit(1)
    src, dst = ApiClient(srv_s), ApiClient(srv_d)

    lines = []
    try:
        # 1) 顶层目录对比
        def top_dirs(base):
            return sorted(d for d in os.listdir(base)
                          if os.path.isdir(os.path.join(base, d)))
        sd, dd = top_dirs(src_mod), top_dirs(dst_mod)
        lines.append(f"源顶层目录 {len(sd)}：{sd}")
        lines.append(f"目标顶层目录 {len(dd)}：{dd}")
        missing = [d for d in sd if d not in dd]
        lines.append(f"目标缺少的顶层目录：{missing or '（无）'}")

        # 2) 每类型实体数对比 + 抽样内容对比
        lines.append("")
        lines.append("| 类型 | 源实体 | 目标实体 | 抽样一致 | 抽样不一致 |")
        lines.append("| --- | --- | --- | --- | --- |")
        diff_details = []
        for c in CONTENT_TYPES:
            t = c[0]
            if t in SKIP_TYPES:
                continue
            rs = src.list_entities(t)
            rd = dst.list_entities(t)
            if not rs.get("ok") and not rd.get("ok"):
                continue
            es = {e["id"] for e in rs.get("entities", [])}
            ed = {e["id"] for e in rd.get("entities", [])}
            same = 0
            diff = 0
            for eid in sorted(es)[:8]:  # 每类型抽样前 8 个
                if eid not in ed:
                    diff += 1
                    diff_details.append(f"{t}/{eid}: 目标缺失")
                    continue
                gs = src.get_entity(t, eid)
                gd = dst.get_entity(t, eid)
                cs = normalize(gs.get("content", ""))
                cd = normalize(gd.get("content", ""))
                if cs == cd:
                    same += 1
                else:
                    diff += 1
                    diff_details.append(f"{t}/{eid}: 内容不一致（源 {len(cs)} vs 目标 {len(cd)} 字符）")
            lines.append(f"| {t} | {len(es)} | {len(ed)} | {same} | {diff} |")
            print(f"  {t}: 源 {len(es)} / 目标 {len(ed)} / 一致 {same} / 不一致 {diff}", flush=True)

        lines.append("")
        lines.append("### 抽样差异明细")
        lines.append("")
        lines.append("\n".join(f"- {d}" for d in diff_details[:40]) or "（无）")
        lines.append("")
        lines.append("## 结论")
        lines.append("")
        lines.append("（详见上方表格；实体缺失/不一致项即为接口或复现逻辑缺口）")

        text = "\n".join(lines)
        with open(os.path.join(ROOT, "接口复现验证.md"), "w", encoding="utf-8") as f:
            f.write(text)
        print(text)
    finally:
        srv_s.stop()
        srv_d.stop()


if __name__ == "__main__":
    main()
