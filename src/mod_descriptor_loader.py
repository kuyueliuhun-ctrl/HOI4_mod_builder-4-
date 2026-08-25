"""Mod 描述（.mod）解析 / 序列化 纯函数（B3-P39）。

descriptor.mod 本质是扁平 PDX 片段：`key = value` 与 `key = { ... }` 两种语句：
    name="The Fire Rises"
    replace_path="common/technologies"
    tags={
        "Military"
        "Gameplay"
    }

本模块只做纯解析 / 格式化 / 字段提取 / 重建，不依赖 PyQt；
写盘由编辑器/信号槽层走 `write_utils.atomic_write_text` 原子写。
"""

from __future__ import annotations

import re

# 编辑器表单认识的已知字段（其余进入「其他条目」原样保留）
SCALAR_FIELDS = (
    "name", "version", "supported_version",
    "remote_file_id", "path", "archive", "picture",
)
LIST_FIELDS = ("tags", "replace_path", "dependencies")

_KNOWN_KEYS = set(SCALAR_FIELDS) | set(LIST_FIELDS)


def _strip_comment(line: str) -> str:
    """去掉行内 `#` 注释并 trim（.mod 一般无行内注释，防御性处理）。"""
    if "#" in line:
        line = line.split("#", 1)[0]
    return line.strip()


def _unquote(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    return value


def parse_mod_entries(text: str):
    """解析 .mod 文本，返回条目列表（保序）。

    每个条目：{"key": str, "value": str|None, "items": list[str]|None}
    - 标量：value 有值、items=None
    - 块：items 有值、value=None
    未知/空行/注释被忽略。
    """
    entries = []
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = _strip_comment(lines[i])
        if not line:
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key = m.group(1)
        rest = m.group(2).strip()
        if rest == "{":
            items = []
            i += 1
            while i < n:
                inner = _strip_comment(lines[i])
                if inner == "}":
                    i += 1
                    break
                if inner:
                    items.append(_unquote(inner))
                i += 1
            # i 已指向块结束 } 的下一行，此处不再自增
            entries.append({"key": key, "value": None, "items": items})
        elif rest.startswith("{") and rest.endswith("}"):
            # 单行块：key = { "a" "b" }
            inner = rest[1:-1]
            items = [a or b for a, b in re.findall(r'"([^"]*)"|([^\s,]+)', inner)]
            entries.append({"key": key, "value": None, "items": items})
            i += 1
        else:
            entries.append({"key": key, "value": _unquote(rest), "items": None})
            i += 1
    return entries


def _needs_quote(value: str) -> bool:
    if not value:
        return True
    return not bool(re.fullmatch(r"[A-Za-z0-9_\-\./:\\]+", value))


def format_mod_entries(entries) -> str:
    """把条目列表格式化为 .mod 文本（统一缩进风格）。"""
    lines = []
    for e in entries:
        key = e["key"]
        if e["items"] is not None:
            lines.append("%s = {" % key)
            for item in e["items"]:
                item = item.strip()
                if _needs_quote(item):
                    lines.append('\t"%s"' % item)
                else:
                    lines.append("\t%s" % item)
            lines.append("}")
        else:
            value = (e.get("value") or "").strip()
            if _needs_quote(value):
                lines.append('%s="%s"' % (key, value))
            else:
                lines.append("%s = %s" % (key, value))
    return "\n".join(lines) + ("\n" if lines else "")


def extract_fields(entries) -> dict:
    """从条目列表提取表单字段。

    返回：
      name/version/supported_version/remote_file_id/path/archive/picture: str
      tags: list[str]
      replace_path: list[str]
      dependencies: list[str]
      other: list[entry]  （未知键 / 重复标量，保序原样保留）
    """
    fields = {k: "" for k in SCALAR_FIELDS}
    fields["tags"] = []
    fields["replace_path"] = []
    fields["dependencies"] = []
    other = []
    for e in entries:
        key = e["key"]
        if key in SCALAR_FIELDS and e["items"] is None:
            if fields[key] == "":
                fields[key] = e["value"] or ""
            else:
                # 单值字段出现重复：首个进表单，其余进 other 保留
                other.append(e)
        elif key == "tags" and e["items"] is not None:
            fields["tags"] = list(e["items"])
        elif key == "replace_path":
            if e["items"] is not None:
                fields["replace_path"].extend(e["items"])
            else:
                fields["replace_path"].append(e["value"] or "")
        elif key == "dependencies":
            if e["items"] is not None:
                fields["dependencies"].extend(e["items"])
            else:
                fields["dependencies"].append(e["value"] or "")
        else:
            other.append(e)
    fields["other"] = other
    return fields


def build_entries(fields: dict) -> list:
    """从表单字段重建条目列表（顺序：已知标量 → replace_path → tags → dependencies → other）。"""
    entries = []
    for key in SCALAR_FIELDS:
        v = (fields.get(key) or "").strip()
        if v:
            entries.append({"key": key, "value": v, "items": None})
    for v in fields.get("replace_path") or []:
        v = str(v).strip()
        if v:
            entries.append({"key": "replace_path", "value": v, "items": None})
    tags = [t.strip() for t in (fields.get("tags") or []) if str(t).strip()]
    if tags:
        entries.append({"key": "tags", "value": None, "items": tags})
    deps = [d.strip() for d in (fields.get("dependencies") or []) if str(d).strip()]
    if deps:
        entries.append({"key": "dependencies", "value": None, "items": deps})
    entries.extend(fields.get("other") or [])
    return entries


def split_list_text(text: str) -> list:
    """把多行文本按行拆成列表（去空行 / 行内逗号）。"""
    out = []
    for line in text.splitlines():
        line = line.strip().rstrip(",").strip()
        if line:
            out.append(line)
    return out
