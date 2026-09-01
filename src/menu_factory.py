"""UI 层：工具菜单动作构建工厂。

四层分离规范见 PROJECT_DOC.md §1.4：
- 本模块只负责「在 QMenu 上创建 QAction」（UI 搭建）；
- 不连接具体业务槽（信号连接留在 main_window 控制器层）；
- 返回 dict 供调用方按名称取用动作。
"""


def build_tool_actions(menu):
    """向 menu（通常是「工具」菜单）添加工具动作，返回 {动作名: QAction}。

    Args:
        menu: QMenu（PyQt6.QtWidgets.QMenu）

    Returns:
        dict[str, QAction]
    """
    a = {}
    a["coverage_report"] = menu.addAction("文件类型覆盖报告…")
    a["localisation_editor"] = menu.addAction("🌐 本地化编辑器…")
    a["entity_resource_workbench"] = menu.addAction("🗂 实体配套资源工作台…")
    a["health_check"] = menu.addAction("导出前健康检查…")
    a["conflict_check"] = menu.addAction("⚔ 多Mod冲突检查…")
    a["submod_mode"] = menu.addAction("🧩 子Mod制作向导…")
    a["submod_exit"] = menu.addAction("🧩 退出子Mod模式")
    a["content_generators"] = menu.addAction("🧰 内容生成器…")
    a["character_editor"] = menu.addAction("👤 角色编辑器…")
    a["pdx_format"] = menu.addAction("📐 PDX 格式化…")
    a["dds_convert"] = menu.addAction("🖼 批量 DDS 转换…")
    a["vp_loc"] = menu.addAction("📍 VP 本地化生成…")
    a["error_log"] = menu.addAction("🧾 错误日志分析…")
    a["map_editor"] = menu.addAction("🗺 地图编辑…")
    a["region_editor"] = menu.addAction("🗺 区域编辑（框选划分）…")
    a["overlay_report"] = menu.addAction(
        "覆盖规则与增量报告（mod vs 原版）…")
    a["icon_manifest"] = menu.addAction("图标库 manifest…")
    a["unit_counters"] = menu.addAction("单位标牌库…")
    a["undo_write"] = menu.addAction("撤销上次文件写入…")
    a["game_reference"] = menu.addAction("游戏数据参考…")
    a["ai_assist"] = menu.addAction("AI 创作助手…")
    a["ai_config"] = menu.addAction("AI 设置…")
    a["api_dialog"] = menu.addAction("外部接口（外置 Agent）…")
    a["division_editor"] = menu.addAction(
        "🎖️ 师编制编辑器（选择 OOB 文件）…")
    a["ship_designer"] = menu.addAction("🚢 舰艇设计…")
    a["plane_designer"] = menu.addAction("✈ 飞机设计…")
    a["tank_designer"] = menu.addAction("🛡 坦克设计…")
    a["mio_editor"] = menu.addAction("🏭 MIO 编辑器…")
    a["mio_policy_editor"] = menu.addAction("🎯 MIO 方针编辑器…")
    a["mio_ai_weights"] = menu.addAction("⚖️ MIO AI 权重…")
    return a
