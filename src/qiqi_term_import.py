"""QIUQI-LIBRARY 词条导入（算法层）

把 QIUQI-LIBRARY 代码提词目录里的“键→中文”词条文件，解析并合并成统一的
translations 词条库 JSON（`terms` schema），供 term_registry / 词条库搜索使用。

冲突规则（本项目约定）：
  - 同键多来源时，以 QIUQI 词条为正确项目；
  - QIUQI 内部同键冲突，按导入顺序“更具体/更靠后”者胜出（如 科技列表 > 原版科技种类）。

每条词条字段：
  key        英文键
  cn         中文名
  node_type  "value"
  tags       分类标签（含源文件小节标题）
  description 备注/数值/效果说明（保留原文，不丢信息）
  source     "qiqi:<源文件名>"

注意：`钢铁雄心4 指令代码.txt` 为 GBK 编码，读取时自动转码。
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from write_utils import atomic_write_text

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def read_text(path: str) -> str:
    """按 UTF-8 → GBK → latin-1 顺序解码文本（GBK 文件自动转码）。"""
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _term(key, cn, tags, description="", source="qiqi"):
    return {
        "key": key,
        "cn": cn or "",
        "node_type": "value",
        "tags": [t for t in tags if t],
        "description": description or "",
        "source": source,
    }


def _kv_lines(text, cn_after_hash=False):
    """通用解析 `key = 中文` 或 `key # 中文` 行。"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if cn_after_hash:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*#\s*(.*)$", s)
            if m and _KEY_RE.match(m.group(1)):
                out.append((m.group(1), m.group(2).strip()))
        else:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$", s)
            if m and _KEY_RE.match(m.group(1)):
                out.append((m.group(1), m.group(2).strip()))
    return out


def parse_tech_categories(text, source="qiqi"):
    """原版科技种类.txt：`key = 中文`。"""
    return [_term(k, v, ["科技分类"], source=source) for k, v in _kv_lines(text)]


def parse_tech_list(text, source="qiqi"):
    """科技列表：小节标题 + `key = 中文`（空值保留待补标记）。"""
    terms = []
    section = ""
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^([0-9]+\.\s*.+)$", s)
        if m and "=" not in s:
            section = m.group(1).strip()
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$", s)
        if m and _KEY_RE.match(m.group(1)):
            v = m.group(2).strip()
            terms.append(_term(
                m.group(1), v, ["科技", section],
                description="原表未填中文" if not v else "",
                source=source))
    return terms


def parse_equipment(text, source="qiqi"):
    """装备类型汇总.txt：`key = 中文`。"""
    return [_term(k, v, ["装备"], source=source) for k, v in _kv_lines(text)]


def parse_navy(text, source="qiqi"):
    """海军类别提词器.txt：`中文名 key` + 小节标题。"""
    terms = []
    section = ""
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            section = s.lstrip("#").rstrip("#").strip()
            continue
        parts = s.split()
        if len(parts) >= 2 and _KEY_RE.match(parts[-1]):
            terms.append(_term(parts[-1], parts[0], ["海军", section],
                               source=source))
    return terms


def parse_national_spirit(text, source="qiqi"):
    """钢4国家精神代码.txt：小节标题(#陆军) + `key #中文`。"""
    terms = []
    section = ""
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            inner = s.lstrip("#").strip()
            if inner and "=" not in inner:
                section = inner
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*#\s*(.*)$", s)
        if m and _KEY_RE.match(m.group(1)):
            terms.append(_term(m.group(1), m.group(2).strip(),
                               ["修正", section], source=source))
    return terms


def parse_traits(text, source="qiqi"):
    """钢4人物trait分类参考.txt：注释式 `#key = 值` + 下一行中文说明。"""
    terms = []
    section = ""
    pending = None  # (key, value, comment)

    def flush():
        nonlocal pending
        if pending:
            key, val, comment = pending
            cn = comment or ""
            desc = ("数值: " + val) if val else ""
            terms.append(_term(key, cn, ["trait", section], desc, source))
            pending = None

    for line in text.splitlines():
        s = line.strip()
        if not s or not s.startswith("#"):
            continue
        inner = s.lstrip("#").strip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$", inner)
        if m and _KEY_RE.match(m.group(1)):
            flush()
            key = m.group(1)
            rest = m.group(2).strip()
            comment = ""
            if "#" in rest:
                rest, comment = rest.split("#", 1)
                rest = rest.strip()
                comment = comment.strip()
            pending = (key, rest, comment)
            continue
        if pending and "=" not in inner:
            if ":" in inner or len(inner) > 12:
                # 下一行是 pending key 的中文说明
                key, val, comment = pending
                if not comment:
                    comment = inner
                desc = ("数值: " + val) if val else ""
                terms.append(_term(key, comment, ["trait", section], desc, source))
                pending = None
                continue
            # 否则视为小节标题
            section = inner
        elif inner and "=" not in inner and ":" not in inner:
            section = inner
    flush()
    return terms


def _has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def parse_cabinet(text, source="qiqi"):
    """部分内阁特质提词器.txt：`key 中文 效果说明...`。

    要求第二段为中文名（过滤英文双词名如 "Cuts Corners"，其非本地化键）。
    """
    terms = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "-")):
            continue
        parts = s.split()
        if (len(parts) >= 2 and _KEY_RE.match(parts[0])
                and _has_cjk(parts[1])):
            terms.append(_term(parts[0], parts[1], ["特质", "内阁"],
                               " ".join(parts[2:]), source))
    return terms


def parse_commands(text, source="qiqi"):
    """钢铁雄心4 指令代码.txt（GBK）：`key = 值 #中文说明`。

    跳过值为 `{...}` 的块行（如 `CZE = {`，非词条）。
    """
    terms = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*([^#]*?)(?:#\s*(.*))?$", s)
        if m and _KEY_RE.match(m.group(1)):
            value = m.group(2).strip()
            if value.startswith("{"):
                continue
            comment = (m.group(3) or "").strip()
            desc = "示例值: " + value if value else ""
            terms.append(_term(m.group(1), comment, ["效果", "修正"],
                               desc, source))
    return terms


def parse_doctrine(text, source="qiqi"):
    """全学说汇总.txt：`效果名 = { #中文说明`。"""
    terms = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{\s*#\s*(.*)$", s)
        if m and _KEY_RE.match(m.group(1)):
            terms.append(_term(m.group(1), m.group(2).strip(), ["学说"],
                               source=source))
    return terms


def parse_collection(text, source="qiqi", tags=None):
    """通用“常用代码合集”解析：`key = value #中文` 或 `key = value 中文`。

    规则：
      - 键必须是合法标识符（`_KEY_RE`）；
      - 值以 `{` 开头且无 `#` 说明 → 块定义，跳过（非词条）；
      - `#` 后的文字作为中文名；无 `#` 时取值后紧跟的中文段作为中文名；
      - 值保留到 description（示例值）。
    """
    tags = list(tags or [])
    terms = []
    section = ""
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            inner = s.lstrip("#").rstrip("#").strip()
            if inner:
                section = inner
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$", s)
        if not m or not _KEY_RE.match(m.group(1)):
            continue
        key = m.group(1)
        rest = m.group(2).strip()
        if not rest:
            continue
        cn = ""
        value = rest
        if "#" in rest:
            value, cn = rest.split("#", 1)
            value = value.strip()
            cn = cn.lstrip("#").strip()
        else:
            parts = rest.split(None, 1)
            head = parts[0]
            if not _has_cjk(head):
                value = head
                if len(parts) > 1 and _has_cjk(parts[1]):
                    cn = parts[1].strip()
                elif len(parts) > 1:
                    value = rest
            else:
                # 值本身就是中文说明（如 FROM = 让这个事件触发的国家…）
                cn = rest
                value = ""
        if value.startswith("{") and not cn:
            continue  # 无说明的块定义，跳过
        desc = "示例值: " + value if value else ""
        terms.append(_term(key, cn, list(tags) + ([section] if section else []),
                           desc, source))
    return terms


# 解析器清单：顺序即冲突优先级（后出现者胜出）
FILE_PARSERS = [
    ("原版科技种类.txt", parse_tech_categories, "科技分类"),
    ("装备类型汇总.txt", parse_equipment, "装备"),
    ("海军类别提词器.txt", parse_navy, "海军"),
    ("钢4国家精神代码.txt", parse_national_spirit, "修正"),
    ("钢4人物trait分类参考.txt", parse_traits, "trait"),
    ("部分内阁特质提词器.txt", parse_cabinet, "特质"),
    ("钢铁雄心4 指令代码.txt", parse_commands, "效果"),
    ("全学说汇总.txt", parse_doctrine, "学说"),
    ("科技列表（截至抗战DLC）.txt", parse_tech_list, "科技"),
]

# 分文件导入组：每个输出文件独立于 qiqi_terms.json
# 格式：(输出文件名, [(源文件名, 解析器, 基础标签), ...])
GROUP_FILES = [
    ("qiqi_modcode_terms.json", [
        ("mod常用代码最新修订版2025.8.14.txt", parse_collection, ["常用代码"]),
        ("mod常用代码（dream修订）.txt", parse_collection, ["常用代码"]),
    ]),
    ("qiqi_diplo_terms.json", [
        ("国家外交关系修正代码_opinion_modifiers.txt", parse_collection, ["外交"]),
    ]),
    ("qiqi_tfr_terms.json", [
        ("TFR常用代码合集（TFX制作组制）.txt", parse_collection, ["TFR"]),
    ]),
    ("qiqi_tno_terms.json", [
        ("TNO常用代码合集(25.1.5)(1).txt", parse_collection, ["TNO"]),
    ]),
]


def find_source_dir(explicit: Optional[str] = None) -> Optional[str]:
    """定位 QIUQI-LIBRARY 根目录（支持显式参数 / 环境变量 / 常见路径）。"""
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    env = os.environ.get("QIUQI_LIBRARY", "")
    if env and os.path.isdir(env):
        return env
    for cand in (r"E:\QIUQI-LIBRARY", "/mnt/e/QIUQI-LIBRARY",
                 os.path.join(os.path.expanduser("~"), "QIUQI-LIBRARY")):
        if os.path.isdir(cand):
            return cand
    return None


def code_terms_dir(source_dir: str) -> str:
    """定位代码提词目录（QIUQI 根/资料/基础代码/代码提词 或其本身）。"""
    cand = os.path.join(source_dir, "资料", "基础代码", "代码提词")
    if os.path.isdir(cand):
        return cand
    return source_dir


# 源文件可能出现的子目录（按优先级）
_SOURCE_SUBDIRS = (
    "",
    os.path.join("资料", "基础代码", "代码提词"),
    os.path.join("资料", "基础代码", "常用模板", "修正模板"),
    os.path.join("资料", "基础代码", "常用模板"),
    os.path.join("资料", "基础代码"),
    os.path.join("资料"),
)


def locate_source_file(source_dir: str, filename: str) -> Optional[str]:
    """在 QIUQI 常见子目录中定位源文件。"""
    for sub in _SOURCE_SUBDIRS:
        cand = os.path.join(source_dir, sub, filename) if sub else os.path.join(source_dir, filename)
        if os.path.isfile(cand):
            return cand
    return None


def build_terms(source_dir: str) -> List[dict]:
    """解析全部词条文件并合并（同键后出现者覆盖，QIUQI 为正确项目）。"""
    code_dir = code_terms_dir(source_dir)
    by_key: Dict[str, dict] = {}
    for filename, parser, _tag in FILE_PARSERS:
        path = os.path.join(code_dir, filename)
        if not os.path.isfile(path):
            continue
        text = read_text(path)
        for term in parser(text, source="qiqi:" + os.path.splitext(filename)[0]):
            if term.get("key"):
                by_key[term["key"]] = term
    return list(by_key.values())


def build_terms_from_texts(files_text: Dict[str, str]) -> List[dict]:
    """按 (文件名→文本) 构建词条（供测试用）。"""
    by_key: Dict[str, dict] = {}
    for filename, text in files_text.items():
        for name, parser, _tag in FILE_PARSERS:
            if filename == name:
                for term in parser(text, source="qiqi:" + os.path.splitext(name)[0]):
                    if term.get("key"):
                        by_key[term["key"]] = term
    return list(by_key.values())


def build_group_terms(source_dir: str, group_files) -> List[dict]:
    """解析一组分文件词条（同键后出现者覆盖）。"""
    by_key: Dict[str, dict] = {}
    for filename, parser, tags in group_files:
        path = locate_source_file(source_dir, filename)
        if not path:
            continue
        text = read_text(path)
        for term in parser(text, source="qiqi:" + os.path.splitext(filename)[0],
                           tags=tags if parser is parse_collection else None):
            if term.get("key"):
                by_key[term["key"]] = term
    return list(by_key.values())


def _dump_terms(output_path: str, terms: List[dict]) -> int:
    data = {"version": 1, "terms": sorted(terms, key=lambda t: t["key"])}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    atomic_write_text(output_path, json.dumps(data, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    return len(terms)


def write_group_terms(output_path: str, source_dir: str, group_files) -> int:
    """把一组词条写入独立 JSON，返回词条数。"""
    return _dump_terms(output_path, build_group_terms(source_dir, group_files))


def write_qiqi_terms(output_path: str, source_dir: str) -> int:
    """把合并后的主词条（qiqi_terms.json）写入，返回词条数。"""
    return _dump_terms(output_path, build_terms(source_dir))


def import_all(output_dir: str, source_dir: str) -> List[tuple]:
    """导入主词条 + 全部分文件词条组。

    返回 [(文件名, 词条数), ...]。
    """
    results = []
    main_path = os.path.join(output_dir, "qiqi_terms.json")
    results.append((os.path.basename(main_path), write_qiqi_terms(main_path, source_dir)))
    for out_name, group_files in GROUP_FILES:
        path = os.path.join(output_dir, out_name)
        results.append((out_name, write_group_terms(path, source_dir, group_files)))
    return results


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="导入 QIUQI-LIBRARY 词条 → translations/*.json（主词条 + 分文件组）")
    ap.add_argument("--source", default=None, help="QIUQI-LIBRARY 根目录（缺省自动探测）")
    ap.add_argument("--output-dir", default=None, help="输出目录（缺省 translations/）")
    args = ap.parse_args(argv)

    source = find_source_dir(args.source)
    if not source:
        print("未找到 QIUQI-LIBRARY 目录；请用 --source 指定。")
        return 1

    from project_paths import PROJECT_ROOT
    output_dir = args.output_dir or os.path.join(PROJECT_ROOT, "translations")
    for name, n in import_all(output_dir, source):
        print("已导入 {} 条词条 → {}".format(n, os.path.join(output_dir, name)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
