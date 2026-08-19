"""事件生成器（算法层）

输入事件 ID / 命名空间 / 国家，生成事件骨架文本 + 本地化占位。
只生成文本，写文件由调用方/CLI 负责（原子写）。
"""

from __future__ import annotations

from typing import Dict, List, Optional


def generate_event(event_id: str, title_placeholder: str = "",
                   desc_placeholder: str = "",
                   option_placeholder: str = "",
                   namespace: str = "") -> dict:
    """生成单事件骨架。

    Returns: {"text": 事件脚本, "loc": [{"key","value"}, ...]}
    """
    eid = (event_id or "event_0").strip()
    ns = (namespace or "").strip()
    if ns:
        eid = eid.replace(":", ".")
        if "." not in eid:
            eid = ns + "." + eid
    else:
        if "." in eid:
            ns = eid.split(".")[0]
    key_name = eid
    key_title = eid + ".t"
    key_desc = eid + ".d"
    key_opt = eid + ".a"

    text = []
    if ns:
        text.append("add_namespace = " + ns)
        text.append("")
    text.append("country_event = {")
    text.append("\tid = " + eid)
    text.append("\ttitle = " + key_title)
    text.append("\tdesc = " + key_desc)
    text.append("")
    text.append("\tis_triggered_only = yes")
    text.append("")
    text.append("\toption = {")
    text.append("\t\tname = " + key_opt)
    text.append("\t\ttrigger = {")
    text.append("\t\t}")
    text.append("\t\teffect = {")
    text.append("\t\t}")
    text.append("\t}")
    text.append("}")

    loc = [
        {"key": key_name, "value": title_placeholder or (eid + " 名称")},
        {"key": key_title, "value": title_placeholder or (eid + " 标题")},
        {"key": key_desc, "value": desc_placeholder or (eid + " 描述")},
        {"key": key_opt, "value": option_placeholder or (eid + " 选项")},
    ]
    return {"text": "\n".join(text) + "\n", "loc": loc, "id": eid,
            "namespace": ns}


def generate_event_namespace_block(event_ids: List[str], namespace: str = "") -> dict:
    """生成一个事件文件的命名空间 + 多个事件 + 全部本地化占位。"""
    ns = (namespace or "").strip()
    blocks = []
    locs: List[dict] = []
    for eid in event_ids:
        r = generate_event(eid, namespace=ns)
        blocks.append(r["text"])
        locs.extend(r["loc"])
    header = ("add_namespace = " + ns + "\n\n") if ns else ""
    return {"text": header + "\n".join(blocks), "loc": locs}