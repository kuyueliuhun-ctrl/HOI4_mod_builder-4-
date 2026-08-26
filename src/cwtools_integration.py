"""CWTools 审查适配（P1：H4MPS 替代）。

CWTools 是 Paradox Clausewitz 脚本语言的官方规则解析/校验工具（F#/.NET）。
本模块不做解析器，只负责：
- ``cwtools_available``：探测 cwtools CLI（PATH 或 ``CWTOOLS_BIN``）。
- ``run_cwtools_check``：子进程调用并将报告 JSON 落盘/解析；未安装时返回可操作引导。
- ``parse_cwtools_report``：把 CWTools 报告（list 或 dict）归一化为
  ``{"errors","warnings","items"}``，未知结构原样透传。

外部命令具体参数随 CWTools 版本调整，本模块以 best-effort 调用，
调用失败返回错误信息而非静默。纯后端，无 Qt；不注册 MCP。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile


def cwtools_available():
    """cwtools CLI 是否可用（PATH 或 CWTOOLS_BIN）。"""
    return bool(os.environ.get("CWTools_BIN") or os.environ.get("CWTOOLS_BIN")
                or shutil.which("cwtools") or shutil.which("cwtools-cli"))


def _cwtools_bin():
    return (os.environ.get("CWTools_BIN") or os.environ.get("CWTOOLS_BIN")
            or shutil.which("cwtools") or shutil.which("cwtools-cli") or "")


def parse_cwtools_report(data):
    """归一化 CWTools 报告。

    支持：
    - list[dict]：每项含 severity/code/message/file/location 字段；
    - dict 含 errors/warnings/items 或 info/errors 等常见键；
    - 其它结构原样透传。
    """
    if isinstance(data, list):
        errors = [i for i in data
                  if str(i.get("severity", "")).lower() in ("error", "red")]
        warnings = [i for i in data
                    if str(i.get("severity", "")).lower() in ("warning", "yellow")]
        return {"errors": errors, "warnings": warnings,
                "items": data, "count": len(data),
                "error_count": len(errors), "warning_count": len(warnings)}
    if isinstance(data, dict):
        out = dict(data)
        out.setdefault("errors", out.get("errors") or out.get("error") or [])
        out.setdefault("warnings", out.get("warnings") or out.get("warning") or [])
        out.setdefault("items", out.get("items") or [])
        return out
    return {"errors": [], "warnings": [], "items": data or [], "raw": data}


def run_cwtools_check(mod_path, game_path="", timeout=120):
    """运行 cwtools 校验，返回归一化报告。

    Returns:
        {"ok": True, "report": ...}  成功
        {"ok": False, "reason": ..., "guide": ...}  未安装/调用失败
    """
    if not mod_path or not os.path.isdir(mod_path):
        return {"ok": False, "reason": "未配置有效 mod 目录",
                "guide": "请先设置 mod_path"}
    bin_path = _cwtools_bin()
    if not bin_path:
        return {
            "ok": False,
            "reason": "cwtools CLI 未安装",
            "guide": "安装 CWTools CLI 并加入 PATH，或设置 CWTOOLS_BIN 指向可执行文件。"
                     "参考：https://github.com/cwtools/cwtools 与 "
                     "https://github.com/cwtools/cwtools-action",
        }
    tmpdir = tempfile.mkdtemp(prefix="cwtools_")
    out_json = os.path.join(tmpdir, "output.json")
    # best-effort 参数（不同版本可能不同；失败会明确报出命令输出）
    cmd = [bin_path, "validate", mod_path,
           "--game", "hoi4", "--output", out_json]
    if game_path:
        cmd += ["--game-path", game_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "cwtools 调用失败: %s" % e,
                "guide": "确认 CWTools CLI 版本与参数兼容（可设置 CWTOOLS_BIN）"}
    if os.path.isfile(out_json):
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                report = parse_cwtools_report(json.load(f))
            return {"ok": True, "report": report}
        except Exception as e:  # noqa: BLE001
            return {"ok": False,
                    "reason": "cwtools 输出解析失败: %s" % e,
                    "guide": "报告文件非标准 JSON：%s" % out_json}
    return {"ok": False,
            "reason": "cwtools 未产出 output.json（exit=%s）" % proc.returncode,
            "guide": "stdout: %s\nstderr: %s" % (proc.stdout[:500],
                                                 proc.stderr[:500])}