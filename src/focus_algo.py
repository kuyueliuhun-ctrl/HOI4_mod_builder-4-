"""算法层：国策/科技/实体画廊的纯逻辑（无 Qt 控件、无绘图、无文件编排）。

四层分离规范见 AGENTS.md §4.9：
- 本模块只做解析/序列化、坐标换算、布局/文本构建、块边界计算等纯逻辑；
- 禁止 import PyQt6 控件类、禁止 QPainter/QGraphicsItem、禁止 connect；
- 允许使用 QPointF 等纯值类型（若确有需要）与标准库。
"""
from project_paths import PROJECT_ROOT

import os
import re


def scene_to_grid(scene_pos, grid_x=90, grid_y=130):
    """将场景坐标转换为国策网格坐标 (x, y)。

    渲染时国策 (x,y) 绘制在场景 ((x+0.5)*90, (y+0.5)*130)，
    因此反算应为 round(px/90 - 0.5)。旧实现 round(px/90)-1 会偏差一整格。
    """
    return (round(scene_pos.x() / grid_x - 0.5),
            round(scene_pos.y() / grid_y - 0.5))


def grid_to_scene(gx, gy, grid_x=90, grid_y=130):
    """国策网格坐标 (x,y) 转场景坐标（单元格中心，即渲染时图标中心）。"""
    return (gx + 0.5) * grid_x, (gy + 0.5) * grid_y


def snap_to_grid_center(scene_pos, grid_x=90, grid_y=130):
    """将场景坐标吸附到最近单元格中心，返回 (吸附后的场景坐标, 网格坐标)。"""
    gx = round(scene_pos.x() / grid_x - 0.5)
    gy = round(scene_pos.y() / grid_y - 0.5)
    return grid_to_scene(gx, gy, grid_x, grid_y), (gx, gy)


def build_focus_text(focus_id, x, y, parent_id=None, template_dir=None):
    """根据模板生成新国策的文本块，可选写入母国策 prerequisite 关系。

    国策使用绝对 x/y 定位，故不再写入 relative_position_id
    （否则会与绝对坐标叠加，导致渲染/游戏内位置偏移）。
    """
    if template_dir is None:
        template_dir = PROJECT_ROOT
    template_path = os.path.join(template_dir, "templates", "focus.txt")
    if os.path.isfile(template_path):
        with open(template_path, 'r', encoding='utf-8-sig', newline='') as f:
            template_content = f.read()
        template_content = template_content.replace('\r\n', '\n').replace('\r', '\n')
        new_focus_text = template_content.replace("id = ", "id = %s" % focus_id, 1)
        new_focus_text = new_focus_text.replace("x = ", "x = %s" % x, 1)
        new_focus_text = new_focus_text.replace("y = ", "y = %s" % y, 1)
        if parent_id:
            new_focus_text = re.sub(
                r'prerequisite\s*=\s*\{\s*\}',
                'prerequisite = { focus = %s }' % parent_id,
                new_focus_text,
                count=1,
            )
    else:
        new_focus_text = (
            "focus = {\n"
            "\tid = %s\n"
            "\ticone = unknown\n"
            "\tx = %s\n"
            "\ty = %s\n"
            "\tcost = 70\n" % (focus_id, x, y)
        )
        if parent_id:
            new_focus_text += "\tprerequisite = {\n\t\tfocus = %s\n\t}\n" % parent_id
        new_focus_text += "}"
    return new_focus_text


def find_focus_block_range(content, focus_id):
    """在文件内容中定位包含指定 id 的国策块，返回 (起始字符, 结束字符)，未找到返回 (-1, -1)。"""
    token_pattern = r'("[^"]*"|#.*|\{|\}|=|[\w\.\-]+)'
    raw_matches = list(re.finditer(token_pattern, content))
    tokens = [m.group(0) for m in raw_matches if not m.group(0).startswith('#')]

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in ('focus', 'shared_focus', 'joint_focus'):
            if i + 2 < len(tokens) and tokens[i + 1] == '=' and tokens[i + 2] == '{':
                block_start = raw_matches[i].start()
                depth = 1
                j = i + 3
                while j < len(tokens) and depth > 0:
                    if tokens[j] == '{':
                        depth += 1
                    elif tokens[j] == '}':
                        depth -= 1
                    j += 1
                block_end_idx = j - 1

                # 检查块内是否包含目标 id
                block_tokens = tokens[i + 3:block_end_idx]
                has_id = False
                for k, t in enumerate(block_tokens):
                    if t == 'id' and k + 2 < len(block_tokens) and block_tokens[k + 1] == '=':
                        id_val = block_tokens[k + 2].strip('"')
                        if id_val == focus_id:
                            has_id = True
                            break

                if has_id:
                    return block_start, raw_matches[block_end_idx].end()
                i = j
                continue
        i += 1
    return -1, -1


def unique_entity_key(base, entities):
    """生成不与现有实体冲突的键。"""
    existing = {e["name"] for e in entities}
    key = base
    n = 1
    while key in existing:
        key = "%s_%s" % (base, n)
        n += 1
    return key


def entity_block_end(content, start_char):
    """返回实体块起始字符对应的平衡右括号结束位置（含 }），未找到返回 -1。

    扫描时跳过双引号字符串与 # 注释，避免花括号被误配对。
    """
    i = content.find("{", start_char)
    if i < 0:
        return -1
    depth = 0
    in_str = False
    n = len(content)
    while i < n:
        c = content[i]
        if in_str:
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == "#":
            while i < n and content[i] != "\n":
                i += 1
            continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def entity_block_text_from_file(entity, current_file_path=None):
    """从源文件提取实体的完整块文本（含尾部 }）；失败返回 None。"""
    file_path = entity.get("file") or current_file_path
    if not file_path or not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        start, end = entity.get("range", (-1, -1))
        if start < 0:
            return None
        end_char = entity_block_end(content, start)
        if end_char <= start:
            return None
        return content[start:end_char]
    except Exception:
        return None


def entity_block_text_source(source, entity):
    """从源文件删除实体块后的内容（供移动使用）。"""
    with open(source, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    start, end = entity.get("range", (-1, -1))
    if start < 0:
        return content
    end_char = entity_block_end(content, start)
    if end_char <= start:
        return content
    new_content = content[:start] + content[end_char:]
    return re.sub(r'\n{3,}', '\n\n', new_content)


def build_entity_block(content_type, key, template_dir=None):
    """按内容类型生成实体块文本（优先系统「项目模板」，否则内置最小块）。

    - character：内置带 portraits 的最小角色块
    - 其余类型：尝试 系统模板/<类型>/项目模板.txt 的节点骨架
    """
    from template_scheduler import get_template_scheduler
    if content_type == "character":
        return (
            "\t%s = {\n"
            "\t\tname = %s\n"
            "\t\tportraits = {\n"
            "\t\t\tcivilian = {\n"
            "\t\t\t\tlarge = \"gfx/Leaders/%s.png\"\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n" % (key, key, key)
        )
    try:
        from content_types import CONTENT_TYPES
        scheduler = get_template_scheduler()
        # 系统模板类型键：优先英文模板类型，否则用内容类型中文名
        tkey = None
        for c in CONTENT_TYPES:
            if c[0] == content_type:
                tkey = c[4] or c[1]
                break
        if tkey:
            matches = scheduler.search_templates(
                template_type=tkey, usage="node")
            if matches:
                with open(matches[0]["filepath"], "r",
                          encoding="utf-8-sig", errors="ignore") as f:
                    tpl_text = f.read()
                # 把模板第一行键名替换为新实体 key
                lines = tpl_text.splitlines()
                if lines:
                    m = re.match(r'^(\s*)(\S+)(\s*=\s*\{.*)$', lines[0])
                    if m:
                        lines[0] = "%s%s%s" % (m.group(1), key, m.group(3))
                body = "\n".join("\t" + ln if ln.strip() else ln
                                 for ln in lines)
                return body.rstrip() + "\n"
    except Exception:
        pass
    return "\t%s = {\n\t\t# 新实体\n\t}\n" % key


def entity_field_for_slot(cfg, slot):
    """返回指定槽位对应的写入字段。

    槽位为 slots 配置键（如 advisor_large / general_small）时返回其单个字段路径；
    slot 为 "large"/"small" 时按字段列表过滤；否则返回完整字段。
    """
    cfg = cfg or {}
    if slot:
        slots_cfg = cfg.get("slots") or {}
        if slot in slots_cfg:
            return slots_cfg[slot]["field"]
    field = cfg.get("field", "icon")
    if isinstance(field, list) and slot:
        return [f for f in field if f.endswith(">%s" % slot)]
    return field
