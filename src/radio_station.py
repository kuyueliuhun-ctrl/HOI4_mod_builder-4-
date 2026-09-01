"""电台/广播 S 档后端（P1 调研：电台 OGG 打包/转码 + music.txt 模板）。

HOI4 音乐格式：
- 电台定义：`<mod>/music/<station_id>.txt`，内容为
  `music_station = "<station_id>"` + 若干 `music = { song = "<song_id>" }`。
- 音频文件：`<mod>/music/<song_id>.ogg`（Vorbis）。

本模块提供：
- ``build_music_station_text``：由 station_id + song_ids 生成 station 文本。
- ``write_music_station``：写 station 文本（原子写，mod 内）。
- ``add_ogg_track``：把音频源加入某电台——转码（ffmpeg）或 .ogg 直拷，
  并追加 song 条目。
- ``transcode_ogg``：ffmpeg 转码封装；无 ffmpeg 且源已是 .ogg 时拷贝兜底。

纯函数 + 文件操作，无 Qt；不注册 MCP 工具。
"""

from __future__ import annotations

import os
import shutil
import subprocess

from write_utils import atomic_write_text


def build_music_station_text(station_id, song_ids):
    """生成 station 文本。

    Args:
        station_id: 电台 id（如 "my_station"）
        song_ids: 歌曲 id 列表（对应 music/<id>.ogg）
    """
    lines = ['music_station = "%s"' % station_id, ""]
    for sid in song_ids:
        lines.append("music = {")
        lines.append('\tsong = "%s"' % sid)
        lines.append("")
        lines.append("}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_music_station(mod_path, station_id, song_ids):
    """把电台定义写入 <mod>/music/<station_id>.txt（原子写）。

    Returns:
        {"path": 相对路径, "songs": [song_id]}
    """
    if not mod_path or not os.path.isdir(mod_path):
        raise ValueError("未配置有效 mod 目录")
    if not station_id or not str(station_id).strip():
        raise ValueError("需要 station_id")
    rel = "music/%s.txt" % str(station_id).strip()
    fp = os.path.join(mod_path, *rel.split("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    atomic_write_text(fp, build_music_station_text(
        station_id, [str(s).strip() for s in (song_ids or [])]))
    return {"path": rel, "songs": [str(s).strip() for s in (song_ids or [])]}


def transcode_ogg(src, dst, force=False):
    """把音频源转为 ogg（Vorbis）。

    - 有 ffmpeg：`ffmpeg -y -i src -c:a libvorbis dst`。
    - 无 ffmpeg：源已是 .ogg 且未 force → 拷贝；否则抛 ValueError。

    Returns:
        {"method": "ffmpeg"|"copy", "dst": dst}
    """
    if not os.path.isfile(src):
        raise ValueError("音频源不存在: %s" % src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        subprocess.run(
            [ffmpeg, "-y", "-i", src, "-c:a", "libvorbis", dst],
            check=True, capture_output=True)
        return {"method": "ffmpeg", "dst": dst}
    if not force and src.lower().endswith(".ogg"):
        shutil.copyfile(src, dst)
        return {"method": "copy", "dst": dst}
    raise ValueError("需要 ffmpeg 才能转码非 .ogg 音频（源: %s）" % src)


def add_ogg_track(mod_path, station_id, song_id, src_audio):
    """把音频源加入电台：转码/拷入 music/<song_id>.ogg，并把 song 追加进 station。

    Returns:
        {"ogg": "music/<song_id>.ogg", "station": "music/<station_id>.txt",
         "method": "ffmpeg"|"copy"}
    """
    if not song_id or not str(song_id).strip():
        raise ValueError("需要 song_id")
    sid = str(song_id).strip()
    from mod_stack import resolve_write_path
    dst = resolve_write_path(mod_path, "music/%s.ogg" % sid)
    tr = transcode_ogg(src_audio, dst)
    # 读回 station，追加 song（不存在则新建）
    rel_station = "music/%s.txt" % str(station_id).strip()
    fp = resolve_write_path(mod_path, rel_station)
    if os.path.isfile(fp):
        with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
    else:
        text = build_music_station_text(station_id, [])
    if ('song = "%s"' % sid) not in text:
        text = text.rstrip() + "\n\nmusic = {\n\tsong = \"%s\"\n}\n" % sid
    atomic_write_text(fp, text)
    return {"ogg": "music/%s.ogg" % sid, "station": rel_station,
            "method": tr["method"]}
