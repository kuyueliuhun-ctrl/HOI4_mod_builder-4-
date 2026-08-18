"""设计模板管理 — 编制/舰艇/飞机/坦克设计器的「保存为模板」支持

模板存放到**独立目录** `design_templates/`（项目根，不在 `templates/` 下），
因此普通模板搜索器（TemplateScheduler/TemplateDialog 扫描 templates/）**不会**
搜索到这些设计模板。

目录结构：
    design_templates/division/xxx.txt   编制模板（division_template 块）
    design_templates/ship/xxx.txt       舰艇模板（create_equipment_variant + upgrades）
    design_templates/plane/xxx.txt      飞机模板（create_equipment_variant + modules）
    design_templates/tank/xxx.txt       坦克模板（create_equipment_variant + modules）

模板内容为可读 PDX 文本（设计块原文），加载时由各设计器解析回内存设计。
写入走 write_utils.atomic_write_text（无 BOM 原子写）。
"""
from project_paths import PROJECT_ROOT

import os
import re

from write_utils import atomic_write_text

# 设计器种类 → 中文名（目录名用英文键）
DESIGN_TEMPLATE_KINDS = {
    "division": "编制",
    "ship": "舰艇",
    "plane": "飞机",
    "tank": "坦克",
}


def design_templates_root():
    """设计模板根目录（项目根/design_templates）。"""
    return os.path.join(PROJECT_ROOT, "design_templates")


def _kind_dir(kind):
    """种类 → 子目录；未知种类用 custom。"""
    if kind not in DESIGN_TEMPLATE_KINDS:
        kind = "custom"
    return os.path.join(design_templates_root(), kind)


def _sanitize_filename(name):
    """清理文件名非法字符（Windows/跨平台安全）。"""
    safe = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name or "").strip()
    return safe or "未命名模板"


def save_design_template(kind, name, content):
    """保存设计模板（已存在自动加序号避免覆盖）。

    Args:
        kind: division/ship/plane/tank
        name: 模板名（不含扩展名）
        content: PDX 文本（设计块原文）

    Returns:
        保存的文件路径；失败返回 None。
    """
    try:
        safe = _sanitize_filename(name)
        d = _kind_dir(kind)
        os.makedirs(d, exist_ok=True)
        filepath = os.path.join(d, safe + ".txt")
        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(d, f"{safe}_{counter}.txt")
            counter += 1
        atomic_write_text(filepath, content, undo=False)
        return filepath
    except Exception:
        return None


def list_design_templates(kind):
    """列出某类设计模板。

    Returns:
        list[dict]: [{name, path}]（按名称排序，name 不含扩展名）
    """
    d = _kind_dir(kind)
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith(".txt"):
            name = fn[:-4]
            out.append({"name": name, "path": os.path.join(d, fn)})
    return out


def load_design_template(kind, name):
    """读取设计模板内容（UTF-8 无 BOM）。

    Returns:
        内容字符串；不存在返回 None。
    """
    safe = _sanitize_filename(name)
    path = os.path.join(_kind_dir(kind), safe + ".txt")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return None
