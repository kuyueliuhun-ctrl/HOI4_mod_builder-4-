"""电台语音广播后端（Piper TTS 适配，P1 电台 M 档）。

Piper 是本地开源神经 TTS（https://github.com/rhasspy/piper）。
本模块是适配层：未安装时返回可操作引导（同 cwtools/Rchadow 模式）；
已安装时：`piper --model <voice> --output_file tmp.wav` 生成语音 → 转码为 ogg。

流程可离线（Piper + ffmpeg 均本地）。纯后端，无 Qt；不注册 MCP。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from radio_station import transcode_ogg


def piper_available():
    """Piper CLI 是否可用（PATH 或 PIPER_BIN）。"""
    return bool(os.environ.get("PIPER_BIN") or shutil.which("piper"))


def _piper_bin():
    return (os.environ.get("PIPER_BIN") or shutil.which("piper") or "")


def synthesize_ogg(text, output_ogg, voice="en_US-lessac-medium"):
    """用 Piper 生成语音并转码为 ogg。

    Returns:
        {"ok": True, "ogg": output_ogg, "method": "piper+ffmpeg"|"piper+copy"}
        或 {"ok": False, "reason": ..., "guide": ...}
    """
    if not text or not str(text).strip():
        return {"ok": False, "reason": "缺少广播文本",
                "guide": "请提供要合成的文字"}
    if not output_ogg:
        return {"ok": False, "reason": "缺少输出 ogg 路径", "guide": ""}
    if not piper_available():
        return {
            "ok": False,
            "reason": "piper TTS 未安装",
            "guide": "安装 Piper（https://github.com/rhasspy/piper）并加入 PATH，"
                     "或设置 PIPER_BIN 指向可执行文件。",
        }
    tmpdir = tempfile.mkdtemp(prefix="piper_")
    wav = os.path.join(tmpdir, "out.wav")
    try:
        subprocess.run(
            [_piper_bin(), "--model", voice, "--output_file", wav],
            input=str(text), text=True, capture_output=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "piper 调用失败: %s" % e,
                "guide": "确认 Piper 可执行与模型 voice=%s 可用" % voice}
    if not os.path.isfile(wav):
        return {"ok": False, "reason": "piper 未产出 wav",
                "guide": "检查 voice=%s 是否已下载模型" % voice}
    try:
        tr = transcode_ogg(wav, output_ogg)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "转码失败: %s" % e,
                "guide": "需要 ffmpeg 才能把 wav 转 ogg（或源为 ogg 可直拷）"}
    return {"ok": True, "ogg": output_ogg, "method": "piper+" + tr["method"]}