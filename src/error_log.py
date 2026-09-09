"""错误日志分析（算法层）

解析游戏 error.log / text.log / game.log，按正则分类常见错误。

6.94 内容补全（真实 error.log 驱动）：
- 位置提取：从错误消息里解析「具体文件:行号」——
  引擎实际使用四种形态（括号尾注 / in file:"X" near line:N / file: X line:N /
  行内 path:line 前缀），全部收敛到 extract_location；
- 位置落位：resolve_location 把相对路径解析到 mod / 游戏根 / HOI4 用户目录
  （mod/ugc_*.mod 描述符），标注来源，给出可直接打开的绝对路径；
- 实体 token + 修复建议：GFX 缺注册 / entity 重复 / 角色作用域缺失等，
  提取可行动的 token 与中文 hint；
- 去重与按文件汇总：真实 error.log 数万行且大量重复，dedupe 合并相同
  （类别, 消息）条目保留首行号与计数，summarize_by_file 按文件聚合；
- 时间戳/引擎来源前缀（[hh:mm:ss][date][x.cpp:NN]:）剥离后再匹配与展示。
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

_RULES = [
    ("缺本地化键", re.compile(r"(?:not\s*found|missing|loc|localis\w*)[^:\\]*(?:key|loc)[^:]*", re.IGNORECASE)),
    ("着色字符错误", re.compile(r"coloring|color\s*for\s*character", re.IGNORECASE)),
    ("括号/引用不匹配", re.compile(r"(?:unbalanced|unexpected|expected)[^.]*(?:brace|bracket|end|token)|unexpected\s*\}", re.IGNORECASE)),
    ("找不到文件/精灵", re.compile(r"(?:could\s*not\s*find|cannot\s*(?:load|find))[^.]*(?:file|sprite|texture|gfx)", re.IGNORECASE)),
    ("图标/实体缺失", re.compile(r"missing\s+(?:icon|shine|sprite|entity|texture|flag|emblem)|failed\s+to\s+find\s+entity|does\s+not\s+exist", re.IGNORECASE)),
    ("重复定义", re.compile(r"duplicate\s+(?:id|focus|decision|event)|duplicate\s+of\s+\S+\s+added", re.IGNORECASE)),
    ("变量/作用域", re.compile(r"(?:variable|scope|scope\s*error|in\s*scope|as\s*scope)", re.IGNORECASE)),
    ("GFX键缺失", re.compile(r"GFX\s*key\s+\S+\s+is\s+missing", re.IGNORECASE)),
    ("effect/trigger错误", re.compile(r"does\s+not\s+have\s+\w+|unknown\s+(?:effect|trigger|command)", re.IGNORECASE)),
]

# 引擎来源/时间戳前缀：[hh:mm:ss][date][x.cpp:NN]: → 剥离后匹配与展示
_TS_PREFIX_RE = re.compile(r"^(?:\[[^\]]*\]\s*)+(?::\s*)?")

# ---------- 位置提取（真实 error.log 四种形态） ----------

# 1) 行尾括号：(common/national_focus/xxx.txt:3516 )
_LOC_PAREN_RE = re.compile(
    r"\(([\w\-.\\/]+\.[A-Za-z0-9]{2,5}):(\d+)\s*\)")
# 2) in file: "X" (near )line: N —— persistent.cpp 解析错误
_LOC_INFILE_RE = re.compile(
    r'in\s+file:\s*"?([^"\n:]+?)"?\s+(?:near\s+)?line:\s*(\d+)', re.IGNORECASE)
# 3) file: X line: N —— dlc.cpp / assetfactory_audio.cpp
_LOC_FILELINE_RE = re.compile(
    r"file:\s*([^\s:\"]+)\s+line:\s*(\d+)", re.IGNORECASE)
# 4) 行内 path:line 前缀：common/national_focus/france.txt:3516: add_compliance …
#    扩展名白名单排除 .cpp/.h 引擎内部位置
_LOC_INLINE_RE = re.compile(
    r"\b((?:[\w\-.]+/)*[\w\-.]+\.(?:txt|gfx|gui|yml|csv|asset|json|mod|lua"
    r"|dds|png|tga|wav)):(\d+)\b", re.IGNORECASE)


def extract_location(message: str) -> Optional[dict]:
    """从错误消息中解析「文件:行号」，返回 {rel_path, line, kind} 或 None。

    优先级：括号尾注 > in file:"X" near line > file: X line:N > 行内前缀。
    引擎内部位置（x.cpp:NN）不属于 mod 内容，一律不返回。
    """
    msg = message or ""
    for kind, pat in (("括号尾注", _LOC_PAREN_RE),
                      ("in-file", _LOC_INFILE_RE),
                      ("file-line", _LOC_FILELINE_RE),
                      ("行内前缀", _LOC_INLINE_RE)):
        m = pat.search(msg)
        if m:
            rel = m.group(1).strip().strip('"').replace("\\", "/")
            try:
                line = int(m.group(2))
            except (TypeError, ValueError):
                continue
            if rel and line > 0:
                return {"rel_path": rel, "line": line, "kind": kind}
    return None


def resolve_location(loc: Optional[dict], mod_path: str = "",
                     hoi4_path: str = "", user_dir: str = "") -> dict:
    """把相对位置解析为可打开的绝对路径并标注来源。

    查找顺序：mod 根 → 游戏根 → HOI4 用户目录（.mod 描述符所在）。
    `mod/ugc_*.mod` 形态按 HOI4 用户目录下的 mod/ 前缀解析。
    找不到时保留相对路径（source=未找到），便于人工定位。
    """
    rel = (loc or {}).get("rel_path", "")
    line = int((loc or {}).get("line") or 0)
    out = {"rel_path": rel, "line": line, "abs_path": "", "source": "未找到"}
    rel_norm = (rel or "").replace("\\", "/").strip().strip('"')
    if not rel_norm:
        return out
    candidates: List[tuple] = []
    if rel_norm.lower().startswith("mod/"):
        # 描述符：HOI4 用户目录下 mod/ 前缀即真实位置
        if user_dir:
            candidates.append((os.path.join(user_dir, rel_norm), "用户mod目录"))
        if mod_path:
            candidates.append((os.path.join(mod_path, rel_norm[4:]), "mod"))
        if hoi4_path:
            candidates.append((os.path.join(hoi4_path, rel_norm), "游戏"))
    else:
        if mod_path:
            candidates.append((os.path.join(mod_path, rel_norm), "mod"))
        if hoi4_path:
            candidates.append((os.path.join(hoi4_path, rel_norm), "游戏"))
        if user_dir:
            candidates.append((os.path.join(user_dir, rel_norm), "用户mod目录"))
    for abs_path, source in candidates:
        if abs_path and os.path.isfile(abs_path):
            out["abs_path"] = os.path.normpath(abs_path)
            out["source"] = source
            return out
    return out


# ---------- 实体 token + 修复建议 ----------

_TOKEN_RULES = [
    (re.compile(r"GFX key (GFX_\S+) is missing", re.IGNORECASE),
     "GFX", "sprite 未注册：在 mod 的 interface/*.gfx 中补该 SpriteType"
            "（或用「批量补注册缺失图标」工具）"),
    (re.compile(r"Missing icon shine for focus: (\S+)"),
     "focus", "国策缺 shine 高光图（GFX_<id>_shine），非致命；"
              "可在图标库选择/上传 shine 图标，或忽略"),
    (re.compile(r"Duplicate of (\S+) added to entity system"),
     "entity", "entity 重复定义：多个 .gfx 文件定义了同名 entity，靠后者生效"),
    (re.compile(r"Failed to find entity \"([^\"]+)\""),
     "entity", "entity 未定义：检查 .gfx/entity 文件是否定义该实体"),
    (re.compile(r'"([^"]+)" does not exist', re.IGNORECASE),
     "entity", "引用的实体/资源不存在：检查名称拼写与定义文件"),
    (re.compile(r"tried to use (?:\w+\s+)?(\S+) as scope, but could not find"),
     "scope", "角色/作用域不存在：确认 recruit_character/国家标签拼写与执行顺序"),
    (re.compile(r"Invalid supported_version", re.IGNORECASE),
     "meta", ".mod 描述符 supported_version 与当前游戏版本不一致"),
    (re.compile(r"Could not load sound file '([^']+)'"),
     "sound", "音效文件缺失：检查 sound/*.asset 引用的 wav 是否存在"),
    (re.compile(r"Unexpected token: (\S+), near line", re.IGNORECASE),
     "parse", "解析失败：引擎不认识该 token（常见多写/漏写引号或括号）"),
    (re.compile(r"(\S+) does not have resistance"),
     "effect", "add_compliance 只对存在抵抗（被占领）的州生效"),
]


def extract_token(message: str) -> tuple:
    """提取可行动 token 与中文修复建议，返回 (token, hint)，无匹配 ("", "")。"""
    msg = message or ""
    for pat, kind, hint in _TOKEN_RULES:
        m = pat.search(msg)
        if m:
            token = m.group(1) if m.groups() else kind
            return token, hint
    return "", ""


def analyze(text: str, dedupe: bool = False) -> List[dict]:
    """逐行分析日志，返回 [{lineno, category, message, rel_path, line,
    token, hint, count}]。

    message 已剥离时间戳/引擎来源前缀；dedupe=True 时合并相同
    （类别, 消息）条目（保留首行号，count 累计）——真实 error.log
    数万行且大量重复，去重后才能进表不卡 UI。
    """
    results: List[dict] = []
    seen: Dict[tuple, dict] = {}
    for idx, line in enumerate(text.splitlines(), start=1):
        message = _TS_PREFIX_RE.sub("", line.strip(), count=1).strip()
        if not message:
            continue
        for category, pat in _RULES:
            if pat.search(message):
                token, hint = extract_token(message)
                item = {"lineno": idx, "category": category,
                        "message": message, "rel_path": "", "line": 0,
                        "token": token, "hint": hint, "count": 1}
                loc = extract_location(message)
                if loc:
                    item["rel_path"] = loc["rel_path"]
                    item["line"] = loc["line"]
                if dedupe:
                    key = (category, message)
                    first = seen.get(key)
                    if first is not None:
                        first["count"] += 1
                        continue
                    seen[key] = item
                results.append(item)
                break
    return results


def summarize(results: List[dict]) -> Dict[str, int]:
    """按类别汇总条数。"""
    out: Dict[str, int] = {}
    for r in results:
        cat = r["category"]
        out[cat] = out.get(cat, 0) + 1
    return out


def summarize_by_file(results: List[dict]) -> Dict[str, int]:
    """按解析出的源文件聚合错误数（无位置的记为「引擎内部/未标注」）。"""
    out: Dict[str, int] = {}
    for r in results:
        key = r.get("rel_path") or "(引擎内部/未标注)"
        out[key] = out.get(key, 0) + r.get("count", 1)
    return out


def analyze_file(path: str, mod_path: str = "", hoi4_path: str = "",
                 user_dir: str = "", dedupe: bool = False) -> List[dict]:
    """分析日志文件并为每条解析「文件:行号」的绝对落位。

    同一 rel_path 的多条错误只做一次磁盘查找（真实日志上万行但唯一
    文件数通常 <100），结果 (abs_path, source) 按文件缓存复用。
    """
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return []
    results = analyze(text, dedupe=dedupe)
    resolved: Dict[str, tuple] = {}
    for r in results:
        rel = r.get("rel_path")
        if not rel:
            continue
        hit = resolved.get(rel)
        if hit is None:
            loc = resolve_location(r, mod_path=mod_path, hoi4_path=hoi4_path,
                                   user_dir=user_dir)
            resolved[rel] = (loc.get("abs_path", ""), loc.get("source", ""))
            r["abs_path"] = loc.get("abs_path", "")
            r["source"] = loc.get("source", "")
        else:
            r["abs_path"], r["source"] = hit
    return results


# 子系统归类关键字（借鉴 RHoiScribe classify_error_log）
_SUBSYSTEM_RULES = [
    ("focus", re.compile(r"focus|national_focus", re.IGNORECASE)),
    ("decision", re.compile(r"decision", re.IGNORECASE)),
    ("event", re.compile(r"event\b|\.t\b|\.d\b|namespace", re.IGNORECASE)),
    ("technology", re.compile(r"tech|technology|research", re.IGNORECASE)),
    ("state", re.compile(r"state\b|province|owner", re.IGNORECASE)),
    ("character", re.compile(r"character|leader|advisor|portrait", re.IGNORECASE)),
    ("localisation", re.compile(r"localis|\.txt|translation|key", re.IGNORECASE)),
    ("gfx/gui", re.compile(r"gfx|sprite|texture|\.gui|\.dds|\.png|entity", re.IGNORECASE)),
    ("map", re.compile(r"map|province|terrain|adjacenc", re.IGNORECASE)),
    ("ai", re.compile(r"ai\b|ai_will", re.IGNORECASE)),
    ("script/scope", re.compile(r"scope|variable|effect|trigger|this|root|from", re.IGNORECASE)),
    ("其他", re.compile(r".*")),
]


def classify_by_subsystem(results: List[dict]) -> Dict[str, int]:
    """把分析结果按 HOI4 子系统归类汇总。"""
    out: Dict[str, int] = {}
    for r in results:
        msg = r.get("message", "")
        sub = "其他"
        for name, pat in _SUBSYSTEM_RULES:
            if name == "其他":
                break
            if pat.search(msg):
                sub = name
                break
        out[sub] = out.get(sub, 0) + r.get("count", 1)
    return out
