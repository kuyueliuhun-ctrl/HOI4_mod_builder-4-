# -*- coding: utf-8 -*-
"""文件级复现（第二版）：通过文件端点完整还原 mod 结构

实体级接口（/api/entities）用于内容编辑，但复现需要保留源文件的包装结构
（ideas/technologies/decisions 等顶层包装块），故使用文件级端点：

  GET  /api/files?type=    → 文件列表
  POST /api/files {path}   → 读取文件内容
  POST /api/files {path,content} → 整文件写入

流程：对每个内容类型 → list_files 源 → read_file 逐个读取 → write_file 到目标
（保持相对路径）；随后逐文件对比源/目标内容一致性，输出报告。

运行：
    python tools/repro_files_via_api.py --source E:\\mods\\3228475937 --target E:\\mods\\3228475937_repro
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
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from api_server import ApiServer  # noqa: E402
from workbench import CONTENT_TYPES  # noqa: E402

SKIP_TYPES = {"generic", "gui_edit", "super_event"}


class ApiClient:
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

    def list_files(self, t):
        return self._req("GET", f"/api/files?type={t}")

    def read_file(self, path):
        return self._req("POST", "/api/files", {"path": path})

    def write_file(self, path, content):
        return self._req("POST", "/api/files", {"path": path, "content": content})


def main():
    parser = argparse.ArgumentParser()
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

    s_srv = ApiServer(mod_path=src_mod, port=8831, token="f-src")
    d_srv = ApiServer(mod_path=dst_mod, port=8832, token="f-dst")
    if not s_srv.start() or not d_srv.start():
        print("[错误] 端口 8831/8832 被占用")
        sys.exit(1)
    src, dst = ApiClient(s_srv), ApiClient(d_srv)

    lines = []
    stats = []
    try:
        total_files = total_ok = total_fail = 0
        for c in CONTENT_TYPES:
            t = c[0]
            if t in SKIP_TYPES:
                continue
            r = src.list_files(t)
            if not r.get("ok"):
                stats.append((t, 0, 0, 0, r.get("error", "")))
                continue
            flist = r.get("files", [])
            ok = fail = 0
            fails = []
            for f in flist:
                path = f["path"]
                total_files += 1
                rd = src.read_file(path)
                if not rd.get("ok"):
                    fail += 1
                    fails.append(f"{path}:读 {rd.get('error')}")
                    continue
                wr = dst.write_file(path, rd.get("content", ""))
                if wr.get("ok"):
                    ok += 1
                    total_ok += 1
                else:
                    fail += 1
                    fails.append(f"{path}:写 {wr.get('error')}")
                    total_fail += 1
            stats.append((t, len(flist), ok, fail, ""))
            if fails:
                print("  !!", t, fails[:3], flush=True)
            print(f"  {t}: 文件 {len(flist)} → 成功 {ok} / 失败 {fail}", flush=True)

        # ── 逐文件内容对比 ──
        lines.append("# 文件级复现报告")
        lines.append("")
        lines.append(f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"- 源：{src_mod}")
        lines.append(f"- 目标：{dst_mod}")
        lines.append("")
        lines.append("## 一、按类型文件复制统计")
        lines.append("")
        lines.append("| 类型 | 源文件 | 成功 | 失败 | 说明 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for t, n, ok, fail, note in stats:
            lines.append(f"| {t} | {n} | {ok} | {fail} | {note} |")
        lines.append("")
        lines.append(f"合计 {total_files} 个文件，成功 {total_ok}，失败 {total_fail}")
        lines.append("")
        lines.append("## 二、内容一致性对比（逐文件）")
        lines.append("")
        diff_count = 0
        for c in CONTENT_TYPES:
            t = c[0]
            if t in SKIP_TYPES:
                continue
            r = src.list_files(t)
            for f in r.get("files", []):
                path = f["path"]
                rs = src.read_file(path)
                rd = dst.read_file(path)
                if not rs.get("ok") or not rd.get("ok"):
                    diff_count += 1
                    lines.append(f"- **{path}**：读取失败（源 {rs.get('error')} / 目标 {rd.get('error')}）")
                    continue
                if rs.get("content") != rd.get("content"):
                    diff_count += 1
                    lines.append(f"- **{path}**：内容不一致"
                                 f"（源 {rs.get('size')} vs 目标 {rd.get('size')} 字符）")
        lines.append(f"对比完成：不一致文件 {diff_count} 个"
                     + ("（全部一致 ✅）" if diff_count == 0 else ""))
        lines.append("")
        lines.append("## 三、接口缺口（本次验证发现）")
        lines.append("")
        lines.append("1. 二进制资源（gfx 图片/dds、music、sound、portraits）不在任何文本类型内，"
                     "文件级端点也只面向文本；复现二进制素材需文件系统层（接口范围外）")
        lines.append("2. 实体级 create 为追加式，不保留源文件包装结构——文件级端点已补齐该缺口")
        lines.append("3. 无批量端点：本次按文件逐请求（" + str(total_files) + " 次读写）")
        lines.append("")

        text = "\n".join(lines)
        with open(os.path.join(ROOT, "接口复现报告.md"), "w", encoding="utf-8") as f:
            f.write(text)
        print(text)
    finally:
        s_srv.stop()
        d_srv.stop()


if __name__ == "__main__":
    main()
