"""绘图层：国策/科技/实体画廊的图形项生成与绘制（不包含控件与业务编排）。

四层分离规范见 AGENTS.md §4.9：
- 本模块只负责「把数据/算法结果变成 QGraphicsItem / 绘制」；
- 禁止创建对话框、直接写文件、持有窗口布局；
- 调用方（控制器）负责传 scene 与必要的回调（图标解析、本地化、字体）。
"""

from PyQt6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsSimpleTextItem


def add_tech_edge(scene, x1, y1, x2, y2):
    """父→子折线（与国策树连线风格一致）。

    纯绘图层函数：只向 scene 添加一个 QGraphicsPathItem。
    """
    mid_y = (y1 + y2) / 2
    path = QPainterPath()
    path.moveTo(x1, y1)
    path.lineTo(x1, mid_y)
    path.lineTo(x2, mid_y)
    path.lineTo(x2, y2)
    pi = QGraphicsPathItem(path)
    pen = QPen(QColor(150, 150, 150, 220))
    pen.setWidth(2)
    pi.setPen(pen)
    pi.setZValue(-10)
    scene.addItem(pi)


def render_tech_tree(scene, techs, tech_files, current_file_path, source_files,
                     pixmap_getter, loc_getter, font_getter):
    """在 scene 中绘制科技树（文件模式 / 无文件模式共用）。

    Args:
        scene: QGraphicsScene
        techs: dict tech_id -> node（含 file / sub_techs / leads_to）
        tech_files: dict tech_id -> file（画布映射，当前实现保留给外部状态）
        current_file_path: str 或 None（当前文件模式路径）
        source_files: list[str]（无文件模式源文件列表）
        pixmap_getter: callable(tech_id) -> QPixmap | None
        loc_getter: callable(tech_id) -> str（本地化名）
        font_getter: callable() -> QFont（基础字体）

    Returns:
        (tree_ids, non_tree_ids): 分类结果，供控制器保存状态。
    """
    from tech_view import (_classify, layout_tech_trees, _TechNodeItem,
                           _SubTechSlot, FOLDER_COLORS, GRID_X, GRID_Y,
                           NODE_W, NODE_H, SUBTECH_W, SUBTECH_H,
                           NON_TREE_COLS)
    scene.clear()
    if not techs:
        tip = QGraphicsSimpleTextItem(
            "🔬 没有可绘制的科技（该文件/目录下没有 common/technologies 定义）")
        tip.setBrush(QBrush(QColor(160, 160, 160)))
        tip.setFont(font_getter())
        tip.setPos(30, 30)
        scene.addItem(tip)
        return [], []

    tree_ids, non_tree_ids, sub_ids = _classify(techs)
    layout = layout_tech_trees(techs, tree_ids)

    # 多棵 folder 树瀑布流布局（每列最多 3 棵，纵向换行，避免横向拉太长）
    trees = []
    for fname, pos in layout.items():
        tw = max((v[0] for v in pos.values()), default=0) + NODE_W
        th = max((v[1] for v in pos.values()), default=0) + NODE_H
        trees.append((fname, pos, tw, th))
    n_cols = 3
    col_x = [40.0] * n_cols
    col_y = [80.0] * n_cols
    col_w = [0.0] * n_cols
    for ti, (fname, pos, tw, th) in enumerate(trees):
        ci = col_y.index(min(col_y))
        x0, y0 = col_x[ci], col_y[ci]
        color = FOLDER_COLORS[ti % len(FOLDER_COLORS)]
        title = QGraphicsSimpleTextItem("📁 %s（%d 科技）" % (fname, len(pos)))
        title.setBrush(QBrush(QColor(255, 200, 90)))
        tf = QFont(font_getter())
        tf.setBold(True)
        tf.setPointSize(tf.pointSize() + 1)
        title.setFont(tf)
        title.setPos(x0, y0 - 40)
        scene.addItem(title)
        for tid, (tx, ty) in pos.items():
            node = techs[tid]
            item = _TechNodeItem(tid, node, pixmap_getter(tid),
                                 loc_getter(tid), color,
                                 x0 + tx, y0 + ty)
            item.setData(1, node.get("file", ""))
            scene.addItem(item)
        for tid, (tx, ty) in pos.items():
            node = techs[tid]
            cx = x0 + tx + NODE_W / 2
            cy = y0 + ty
            for i, sub_id in enumerate(node.get("sub_techs", [])):
                if sub_id not in techs:
                    continue
                slot = _SubTechSlot(i, sub_id, cx - SUBTECH_W / 2,
                                    cy + NODE_H + 2)
                slot.setData(1, techs[sub_id].get("file", ""))
                scene.addItem(slot)
            for child in node.get("leads_to", []):
                if child not in pos:
                    continue
                ex, ey = pos[child]
                add_tech_edge(scene, cx, cy + NODE_H,
                              x0 + ex + NODE_W / 2, y0 + ey)
        col_y[ci] += th + 70
        col_w[ci] = max(col_w[ci], tw)
    cursor_x = max(col_x[i] + col_w[i] for i in range(n_cols)) + 40
    max_bottom = max(col_y)

    # 非树科技：下方网格分散展示
    if non_tree_ids:
        gy = max_bottom + 90
        title = QGraphicsSimpleTextItem(
            "🗂 非树科技（不在科技树中，由国策/事件/决议等获得）"
            "（%d 个）" % len(non_tree_ids))
        title.setBrush(QBrush(QColor(200, 230, 255)))
        tf = QFont(font_getter())
        tf.setBold(True)
        title.setFont(tf)
        title.setPos(40, gy - 35)
        scene.addItem(title)
        col = 0
        row = 0
        for tid in sorted(non_tree_ids):
            node = techs[tid]
            item = _TechNodeItem(tid, node, pixmap_getter(tid),
                                 loc_getter(tid),
                                 FOLDER_COLORS[6],
                                 40 + col * (NODE_W + 30),
                                 gy + row * (NODE_H + 40))
            item.setData(1, node.get("file", ""))
            scene.addItem(item)
            col += 1
            if col >= NON_TREE_COLS:
                col = 0
                row += 1
        max_bottom = max(max_bottom, gy + (row + 1) * (NODE_H + 40))

    # 标题：模式 + 统计
    nfile = len(source_files) if source_files else 0
    if current_file_path:
        import os
        head = "🔬 科技树 · %s" % os.path.basename(current_file_path)
    else:
        head = "🔬 科技树 · 无文件模式（%d 文件）" % nfile
    head += ("（共 %d 科技：树 %d · 非树 %d · 子科技 %d）"
             % (len(techs), len(tree_ids), len(non_tree_ids), len(sub_ids)))
    title = QGraphicsSimpleTextItem(head)
    tfont = QFont(font_getter())
    tfont.setBold(True)
    tfont.setPointSize(tfont.pointSize() + 2)
    title.setFont(tfont)
    title.setBrush(QBrush(QColor(255, 200, 90)))
    title.setPos(14, 10)
    title.setZValue(100)
    scene.addItem(title)

    rect = scene.itemsBoundingRect().adjusted(-100, -60, 100, 100)
    scene.setSceneRect(rect)
    return tree_ids, non_tree_ids
