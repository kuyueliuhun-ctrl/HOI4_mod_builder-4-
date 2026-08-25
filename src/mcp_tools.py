"""MCP 工具注册表：159 个工具（现有 17 + 新增 142）

与 HTTP API 共用 ApiCore。工具 schema 供 MCP Agent 选择。
"""
from __future__ import annotations

import itertools


def _tool(name, description, schema, handler):
    return {"name": name, "description": description,
            "inputSchema": schema, "_handler": handler}


def _obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": required or []}


def _str(desc=""):
    return {"type": "string", "description": desc}


def _int(desc=""):
    return {"type": "integer", "description": desc}


def _num(desc=""):
    return {"type": "number", "description": desc}


def _bool(desc=""):
    return {"type": "boolean", "description": desc}


def _arr(items, desc=""):
    return {"type": "array", "items": items, "description": desc}


def _obj_type(desc=""):
    return {"type": "object", "description": desc}


# ══════════════════════════════════════════════════════════════
# 现有 17 个工具（保持名称/行为不变）
# ══════════════════════════════════════════════════════════════

def _existing_tools(core):
    return [
        _tool(
            "get_status",
            "获取当前 mod 与游戏目录、内容类型数量等状态信息",
            _obj({}),
            lambda args: core.status()),
        _tool(
            "list_types",
            "列出全部内容类型（角色/国策/事件/决议/科技/触发动作等 90+ 种）",
            _obj({}),
            lambda args: core.types()),
        _tool(
            "list_entities",
            "列出指定内容类型下的实体（可按国家/关键词过滤）",
            _obj({
                "type": _str("内容类型 key，如 focus/event/decision/operation"),
                "country": _str("国家 tag 过滤，如 GER（可选）"),
                "keyword": _str("关键词过滤（可选）"),
            }, ["type"]),
            lambda args: core.list_entities(
                str(args.get("type", "")),
                str(args.get("country", "")),
                str(args.get("keyword", "")))),
        _tool(
            "get_entity",
            "获取单个实体的完整 PDX 块文本（用于读取内容后修改）",
            _obj({
                "type": _str("内容类型"),
                "id": _str("实体 id，如 GER_anchluss"),
            }, ["type", "id"]),
            lambda args: core.get_entity(str(args["type"]), str(args["id"]))),
        _tool(
            "create_entity",
            "新建实体（写入该国现有文件或类型目录新文件），支持自定义块内容",
            _obj({
                "type": _str("内容类型"),
                "id": _str("新实体 id"),
                "country": _str("国家 tag（可选）"),
                "content": _str("自定义实体块文本（可选）"),
            }, ["type", "id"]),
            lambda args: core.create_entity(args)),
        _tool(
            "update_entity",
            "替换实体块内容（content 为新块文本）",
            _obj({
                "type": _str("内容类型"),
                "id": _str("实体 id"),
                "content": _str("新的实体块文本"),
            }, ["type", "id", "content"]),
            lambda args: core.update_entity(str(args["type"]), str(args["id"]), args)),
        _tool(
            "delete_entity",
            "删除实体",
            _obj({
                "type": _str("内容类型"),
                "id": _str("实体 id"),
            }, ["type", "id"]),
            lambda args: core.delete_entity(str(args["type"]), str(args["id"]))),
        _tool(
            "create_focus_project",
            "项目级联动：一键生成国策+触发事件+决议+图标占位+本地化词条",
            _obj({
                "country": _str("国家 tag，如 GER"),
                "focus_id": _str("国策 id，如 GER_anchluss"),
                "name": _str("中文名称（可选）"),
                "desc": _str("中文描述（可选）"),
                "x": _int("国策网格 X（可选，默认 0）"),
                "y": _int("国策网格 Y（可选，默认 0）"),
                "event": _bool("是否生成触发事件（默认 true）"),
                "decision": _bool("是否生成决议（默认 true）"),
                "icon": _bool("是否生成图标占位（默认 true）"),
                "localisation": _bool("是否写本地化（默认 true）"),
            }, ["country", "focus_id"]),
            lambda args: core.create_focus_project(args)),
        _tool(
            "write_localisation",
            "写本地化词条到 mod 翻译文件",
            _obj({
                "tag": _str("国家/前缀 tag（可选，默认 generic）"),
                "entries": _obj_type("词条字典，如 {\"GER_anchluss\": \"德奥合并\"}"),
            }, ["entries"]),
            lambda args: core.write_localisation(args)),
        _tool(
            "validate_mod",
            "校验 mod：本地化缺失 / 国策引用悬空 / 未知引用 / 重复 ID",
            _obj({}),
            lambda args: core.validate()),
        _tool(
            "list_templates",
            "列出可用模板（可按类型/用途过滤）",
            _obj({
                "type": _str("模板类型，如 focus/event（可选）"),
                "usage": _str("用途 file/node/both（可选）"),
            }),
            lambda args: core.templates(str(args.get("type", "")), str(args.get("usage", "")))),
        _tool(
            "list_files",
            "列出指定内容类型目录下的全部文件（含路径/大小）",
            _obj({
                "type": _str("内容类型 key"),
            }, ["type"]),
            lambda args: core.list_files(str(args.get("type", "")))),
        _tool(
            "read_file",
            "读取 mod 内指定相对路径文件的完整内容（用于文件级编辑/复现）",
            _obj({
                "path": _str("mod 内相对路径，如 common/national_focus/GER.txt"),
            }, ["path"]),
            lambda args: core.get_file(str(args.get("path", "")))),
        _tool(
            "write_file",
            "整文件写入（新建/覆盖）：{path, content}，路径须为 mod 内相对路径",
            _obj({
                "path": _str("mod 内相对路径"),
                "content": _str("完整文件内容"),
            }, ["path", "content"]),
            lambda args: core.write_file(args)),
        _tool(
            "upload_tech_icon",
            "上传科技图标：图片 base64 写入 gfx/interface/technologies/，并自动注册 GFX_<tech_id>_medium",
            _obj({
                "tech_id": _str("科技 id，如 GER_tiger_tank"),
                "image_base64": _str("图片文件（png/jpg/dds 等）的 base64 编码"),
                "filename": _str("原文件名（仅提示用，可选）"),
            }, ["tech_id", "image_base64"]),
            lambda args: core.upload_tech_icon(args)),
        _tool(
            "get_icon_manifest",
            "图标库 manifest：扫描 mod+游戏全部 gfx spriteType 定义",
            _obj({
                "query": _str("sprite 名子串过滤（可选）"),
                "source": _str("来源过滤 mod/vanilla（可选）"),
                "limit": _int("返回条数上限（默认 200）"),
            }),
            lambda args: core.get_icon_manifest(
                str(args.get("query", "")), str(args.get("source", "")),
                int(args.get("limit", 200) or 0))),
        _tool(
            "get_overlay_report",
            "mod 覆盖原版的增量报告（规则分层 + 文件级 delta）",
            _obj({
                "summary_only": _bool("只返回统计（默认 false 返回全量文件列表）"),
            }),
            lambda args: core.get_overlay_report(bool(args.get("summary_only", False)))),
    ]


# ══════════════════════════════════════════════════════════════
# 新增工具 spec 生成
# ══════════════════════════════════════════════════════════════

def _domain0_tools(core):
    return [
        _tool("format_pdx", "PDX 文件格式化写回",
              _obj({"path": _str("mod 内相对路径"),
                    "whitespace": _bool("是否移除多余空白（可选）"),
                    "ignore_comments": _bool("是否忽略注释（可选）")}, ["path"]),
              lambda args: core.format_pdx(args)),
        _tool("vp_loc_dry_run", "VP 本地化干跑预览（不写文件）", _obj({}),
              lambda args: core.vp_loc_dry_run()),
        _tool("analyze_error_log", "游戏错误日志分析 + 子系统归类",
              _obj({"path": _str("mod 内相对路径（可选）"),
                    "absolute_path": _str("日志绝对路径（可选）")}),
              lambda args: core.analyze_error_log(args)),
        _tool("register_icon_batch", "批量补注册文件内缺失图标 GFX",
              _obj({"path": _str("mod 内相对路径"),
                    "type": _str("内容类型（默认 focus）")}, ["path"]),
              lambda args: core.register_icon_batch(args)),
    ]


def _domain1_tools(core):
    return [
        _tool("list_states", "列出州（可按 owner/keyword 过滤）",
              _obj({"owner": _str("国家 tag 过滤（可选）"),
                    "keyword": _str("州名/键过滤（可选）")}),
              lambda args: core.list_states(args)),
        _tool("get_state", "获取州完整信息（建筑/VP/省份/src）",
              _obj({"state_id": _int("州 id")}, ["state_id"]),
              lambda args: core.get_state(args)),
        _tool("get_province", "获取省信息（所属州/类型/地形/沿海）",
              _obj({"province_id": _int("省 id")}, ["province_id"]),
              lambda args: core.get_province(args)),
        _tool("get_owner_provinces", "获取国家拥有地块（tag 缺省返回全部 owner 表）",
              _obj({"tag": _str("国家 tag（可选）")}),
              lambda args: core.get_owner_provinces(args)),
        _tool("set_state_owner", "设置州归属（只写 mod，原版自动复制）",
              _obj({"state_id": _int("州 id"), "tag": _str("国家 tag")},
                   ["state_id", "tag"]),
              lambda args: core.set_state_owner(args)),
        _tool("set_state_building", "设置州建筑（省/州级；level<=0 移除）",
              _obj({"state_id": _int("州 id"), "building": _str("建筑键"),
                    "level": _int("等级"), "province_id": _int("锚定省 id（可选）")},
                   ["state_id", "building", "level"]),
              lambda args: core.set_state_building(args)),
        _tool("set_state_category", "设置州类别",
              _obj({"state_id": _int("州 id"), "category": _str("state_category")},
                   ["state_id", "category"]),
              lambda args: core.set_state_category(args)),
        _tool("set_country_color", "设置国家颜色（0-255）",
              _obj({"tag": _str("国家 tag"), "r": _int("红"), "g": _int("绿"),
                    "b": _int("蓝")}, ["tag", "r", "g", "b"]),
              lambda args: core.set_country_color(args)),
        _tool("list_building_types", "列出建筑类型（可建/图标/修饰）", _obj({}),
              lambda args: core.list_building_types(args)),
        _tool("list_country_colors", "列出全部国家颜色", _obj({}),
              lambda args: core.list_country_colors(args)),
        _tool("batch_set_state_fields", "批量设置州字段（默认 dry_run）",
              _obj({"state_ids": _arr(_int(), "州 id 列表"),
                    "field": _str("字段名，如 manpower/state_category"),
                    "value": _str("字段值"),
                    "dry_run": _bool("默认 true 只预览")},
                   ["state_ids", "field", "value"]),
              lambda args: core.batch_set_state_fields(args)),
        _tool("sort_state_file", "按州 id 排序州文件",
              _obj({"path": _str("mod 内相对路径")}, ["path"]),
              lambda args: core.sort_state_file(args)),
        _tool("list_regions", "列出战略区/补给区",
              _obj({"kind": _str("strategic_region,supply_area 或逗号组合（可选）")}),
              lambda args: core.list_regions(args)),
        _tool("create_region", "新建区域",
              _obj({"kind": _str("strategic_region 或 supply_area"),
                    "region_id": _int("区域 id（可选，自动）"),
                    "province_ids": _arr(_int(), "省 id 列表")},
                   ["kind", "province_ids"]),
              lambda args: core.create_region(args)),
        _tool("set_region_provinces", "替换区域省份列表",
              _obj({"kind": _str("strategic_region 或 supply_area"),
                    "region_id": _int("区域 id"),
                    "province_ids": _arr(_int(), "省 id 列表")},
                   ["kind", "region_id", "province_ids"]),
              lambda args: core.set_region_provinces(args)),
        _tool("remove_region", "删除区域",
              _obj({"kind": _str("strategic_region 或 supply_area"),
                    "region_id": _int("区域 id")}, ["kind", "region_id"]),
              lambda args: core.remove_region(args)),
    ]


def _design_tool_names(kind):
    return [kind + "_hulls", kind + "_modules", kind + "_designs",
            "get_" + kind + "_design", "create_" + kind + "_design",
            "update_" + kind + "_design", "rename_" + kind + "_design",
            "delete_" + kind + "_design", "sync_" + kind + "_design"]


def _domain2_tools(core):
    tools = []
    for kind in ("ship", "plane", "tank"):
        cn = {"ship": "舰艇", "plane": "飞机", "tank": "坦克"}[kind]
        tools += [
            _tool("list_%s_hulls" % kind, "列出%s船体/机型/底盘" % cn, _obj({}),
                  lambda args, k=kind: getattr(core, "list_%s_hulls" % k)(args)),
            _tool("list_%s_modules" % kind, "列出%s模块" % cn, _obj({}),
                  lambda args, k=kind: getattr(core, "list_%s_modules" % k)(args)),
            _tool("list_%s_designs" % kind, "列出%s设计（可按国家过滤）" % cn,
                  _obj({"country": _str("国家 tag（可选）")}),
                  lambda args, k=kind: getattr(core, "list_%s_designs" % k)(args)),
            _tool("get_%s_design" % kind, "获取单个%s设计及属性估算" % cn,
                  _obj({"country": _str("国家 tag"), "name": _str("设计名")},
                       ["country", "name"]),
                  lambda args, k=kind: getattr(core, "get_%s_design" % k)(args)),
            _tool("create_%s_design" % kind, "新建%s设计" % cn,
                  _obj({"country": _str("国家 tag"), "name": _str("设计名"),
                        "hull": _str("船体/机型/底盘键"),
                        "upgrades": _obj_type("槽位模块字典")},
                       ["country", "name", "hull", "upgrades"]),
                  lambda args, k=kind: getattr(core, "create_%s_design" % k)(args)),
            _tool("update_%s_design" % kind, "更新%s设计模块" % cn,
                  _obj({"country": _str("国家 tag"), "name": _str("设计名"),
                        "upgrades": _obj_type("新槽位模块字典")},
                       ["country", "name", "upgrades"]),
                  lambda args, k=kind: getattr(core, "update_%s_design" % k)(args)),
            _tool("rename_%s_design" % kind, "重命名%s设计" % cn,
                  _obj({"country": _str("国家 tag"), "old": _str("旧名"),
                        "new": _str("新名")}, ["country", "old", "new"]),
                  lambda args, k=kind: getattr(core, "rename_%s_design" % k)(args)),
            _tool("delete_%s_design" % kind, "删除%s设计" % cn,
                  _obj({"country": _str("国家 tag"), "name": _str("设计名")},
                       ["country", "name"]),
                  lambda args, k=kind: getattr(core, "delete_%s_design" % k)(args)),
            _tool("sync_%s_design" % kind, "把%s设计同步到所有同名设计国家（默认 dry_run）" % cn,
                  _obj({"name": _str("设计名"), "dry_run": _bool("默认 true 只预览")},
                       ["name"]),
                  lambda args, k=kind: getattr(core, "sync_%s_design" % k)(args)),
        ]
    tools += [
        _tool("list_design_templates", "列出设计模板",
              _obj({"kind": _str("division/ship/plane/tank")}, ["kind"]),
              lambda args: core.list_design_templates(args)),
        _tool("save_design_template", "保存设计模板",
              _obj({"kind": _str("division/ship/plane/tank"),
                    "name": _str("模板名"), "content": _str("模板内容")},
                   ["kind", "name", "content"]),
              lambda args: core.save_design_template(args)),
        _tool("load_design_template", "读取设计模板内容",
              _obj({"kind": _str("division/ship/plane/tank"),
                    "name": _str("模板名")}, ["kind", "name"]),
              lambda args: core.load_design_template(args)),
    ]
    return tools


def _domain3_tools(core):
    return [
        _tool("list_oob_files", "列出 OOB 文件（含军种识别）", _obj({}),
              lambda args: core.list_oob_files(args)),
        _tool("list_division_templates", "列出师编制（可指定文件）",
              _obj({"path": _str("history/units 下相对路径（可选）")}),
              lambda args: core.list_division_templates(args)),
        _tool("get_division_template", "获取单个师编制及统计",
              _obj({"path": _str("OOB 文件相对路径"), "name": _str("编制名")},
                   ["path", "name"]),
              lambda args: core.get_division_template(args)),
        _tool("create_division_template", "新建师编制",
              _obj({"path": _str("OOB 文件相对路径"), "name": _str("编制名"),
                    "units": _arr(_obj_type(), "regiments 列表 [{type,x,y}]"),
                    "support": _arr(_obj_type(), "support 列表 [{type,x,y}]"),
                    "is_locked": _bool("是否锁定（可选）")},
                   ["path", "name"]),
              lambda args: core.create_division_template(args)),
        _tool("update_division_template", "更新师编制",
              _obj({"path": _str("OOB 文件相对路径"), "name": _str("编制名"),
                    "units": _arr(_obj_type(), "新 regiments（可选）"),
                    "support": _arr(_obj_type(), "新 support（可选）"),
                    "is_locked": _bool("是否锁定（可选）"),
                    "content": _str("整块替代内容（可选）")},
                   ["path", "name"]),
              lambda args: core.update_division_template(args)),
        _tool("delete_division_template", "删除师编制",
              _obj({"path": _str("OOB 文件相对路径"), "name": _str("编制名")},
                   ["path", "name"]),
              lambda args: core.delete_division_template(args)),
        _tool("list_sub_units", "列出营/兵种属性", _obj({"keyword": _str("过滤（可选）")}),
              lambda args: core.list_sub_units(args)),
        _tool("search_equipment", "搜索装备属性", _obj({"keyword": _str("过滤（可选）"),
                                                       "category": _str("类别过滤（可选）")}),
              lambda args: core.search_equipment(args)),
    ]


_AI_KINDS_LABEL = {
    "plan": "战略计划", "strategy": "战略倾向", "ai_template": "AI 师模板",
    "equipment": "AI 装备", "navy": "AI 海军", "area": "AI 区域",
    "focus": "AI 科研权重", "theater": "AI 派系战区",
}


def _ai_params(kind, action):
    id_params = {
        "id": _str("%s id" % _AI_KINDS_LABEL[kind]),
    }
    if kind == "navy":
        id_params["section"] = _str("goal/fleet/taskforce（navy 必填）")
    extra = {}
    if action == "create":
        if kind == "plan":
            extra = {"name": _str("名称（可选）"), "desc": _str("描述（可选）")}
        elif kind == "strategy":
            extra = {"entries": _arr(_obj_type(), "ai_strategy 条目列表（可选）")}
        elif kind == "ai_template":
            extra = {"role": _str("role 值（可选）")}
        elif kind == "equipment":
            extra = {"category": _str("air/naval/land（默认 air）")}
        elif kind == "area":
            extra = {"strategic_regions": _arr(_int(), "战略区列表（可选）")}
        elif kind == "focus":
            extra = {"research": _obj_type("科技权重字典（可选）")}
        elif kind == "theater":
            extra = {"name": _str("战区名（可选）"),
                     "regions": _arr(_int(), "区域列表（可选）")}
        elif kind == "navy":
            extra = {"objective_type": _str("goal 目标类型（可选）"),
                     "min_priority": _str("最小优先级（可选）"),
                     "max_priority": _str("最大优先级（可选）")}
    elif action == "rename" or action == "duplicate":
        extra = {"new": _str("新 id（new_id 也可）")}
    elif action == "update":
        extra = {"field": _str("要更新的字段（可选）"),
                 "value": _str("字段新值（可选）"),
                 "quoted": _bool("值是否加引号（可选）"),
                 "content": _str("整块替代内容（可选）"),
                 "focus_order": _arr(_str(), "计划国策顺序（plan 可选）"),
                 "entries": _arr(_obj_type(), "战略倾向条目（strategy 可选）"),
                 "strategic_regions": _arr(_int(), "AI 区域战略区（area 可选）"),
                 "regions": _arr(_int(), "战区 regions（theater 可选）"),
                 "preferred_countries": _arr(_str(), "战区偏好国家（theater 可选）"),
                 "role_id": _str("ai_template 角色 id（可选）"),
                 "target_id": _str("ai_template 目标 id（可选）"),
                 "group_id": _str("ai_equipment 设计组 id（可选）"),
                 "variant_id": _str("ai_equipment 变体 id（可选）")}
    return {**id_params, **extra}


def _ai_tools(core):
    tools = []
    for kind in _AI_KINDS_LABEL:
        for action in ("list", "create", "update", "delete", "rename", "duplicate"):
            name = "ai_%s_%s" % (kind, action)
            if action == "list":
                desc = "列出%s" % _AI_KINDS_LABEL[kind]
                schema = _obj({})
            else:
                desc = "%s%s" % ({"create": "新建", "update": "更新",
                                  "delete": "删除", "rename": "重命名",
                                  "duplicate": "复制"}[action],
                                 _AI_KINDS_LABEL[kind])
                schema = _obj(_ai_params(kind, action))
            tools.append(_tool(name, desc, schema,
                               lambda args, k=kind, a=action:
                               getattr(core, "ai_%s_%s" % (k, a))(args)))
    tools.append(_tool(
        "set_ai_plan_focus_order", "设置 AI 战略计划的国策顺序（等价 focus_order_picker 结果）",
        _obj({"plan_id": _str("计划 id"), "ordered_focus_ids": _arr(_str(), "国策 id 列表")},
             ["plan_id", "ordered_focus_ids"]),
        lambda args: core.set_ai_plan_focus_order(args)))
    return tools


def _domain5_tools(core):
    return [
        _tool("list_bop", "列出力量平衡 BOP 概览", _obj({}),
              lambda args: core.list_bop(args)),
        _tool("get_bop", "获取单个 BOP（含动作/区间/修正/当前区间）",
              _obj({"bop_id": _str("BOP id/tag")}, ["bop_id"]),
              lambda args: core.get_bop(args)),
        _tool("set_bop_initial_value", "保存 BOP initial_value",
              _obj({"bop_id": _str("BOP id"), "value": _num("初始值")},
                   ["bop_id", "value"]),
              lambda args: core.set_bop_initial_value(args)),
        _tool("set_bop_fields", "保存 BOP 基础字段（可部分更新）",
              _obj({"bop_id": _str("BOP id"),
                    "left_side": _str("左势力（可选）"),
                    "right_side": _str("右势力（可选）"),
                    "decision_category": _str("决策分类（可选）")}, ["bop_id"]),
              lambda args: core.set_bop_fields(args)),
    ]


def _domain6_tools(core):
    return [
        _tool("search_localisation", "搜索本地化词条（mod 优先回退原版）",
              _obj({"keyword": _str("关键词或 key（可选）"),
                    "language": _str("语言目录，chi/eng（默认 chi）")}),
              lambda args: core.search_localisation(args)),
        _tool("list_missing_localisation", "列出缺失本地化词条", _obj({}),
              lambda args: core.list_missing_localisation(args)),
        _tool("batch_fill_localisation", "批量补本地化（默认 dry_run）",
              _obj({"entries": _obj_type("自定义词条（可选）"),
                    "dry_run": _bool("默认 true 只预览")}),
              lambda args: core.batch_fill_localisation(args)),
        _tool("search_terms", "搜索词条库（QIUQI 1887 词条）",
              _obj({"keyword": _str("关键词（可选）"),
                    "node_type": _str("block/value（可选）"),
                    "tag": _str("标签（可选）"),
                    "limit": _int("上限（默认 300）")}),
              lambda args: core.search_terms(args)),
        _tool("get_term", "获取单个词条", _obj({"key": _str("词条 key")}, ["key"]),
              lambda args: core.get_term(args)),
        _tool("add_user_term", "新增用户词条",
              _obj({"key": _str("命令名"), "cn": _str("中文翻译"),
                    "node_type": _str("block/value（默认 value）"),
                    "tags": _arr(_str(), "标签（可选）"),
                    "description": _str("描述（可选）")}, ["key", "cn"]),
              lambda args: core.add_user_term(args)),
        _tool("update_user_term", "更新用户词条",
              _obj({"key": _str("词条 key"), "cn": _str("中文（可选）"),
                    "node_type": _str("类型（可选）"),
                    "tags": _arr(_str(), "标签（可选）"),
                    "description": _str("描述（可选）")}, ["key"]),
              lambda args: core.update_user_term(args)),
        _tool("remove_user_term", "删除用户词条", _obj({"key": _str("词条 key")}, ["key"]),
              lambda args: core.remove_user_term(args)),
    ]


def _domain7_tools(core):
    return [
        _tool("health_check", "导出前健康检查（8 类）",
              _obj({"max_issues": _int("结果上限（默认 500）")}),
              lambda args: core.health_check(args)),
        _tool("scan_duplicate_ids", "扫描重复 id（focus/event/decision 等）",
              _obj({"types": _str("类型逗号列表（默认 focus,event,dynamic_modifier,decision,character）")}),
              lambda args: core.scan_duplicate_ids(args)),
        _tool("undo_last_write", "撤销最近一次文件写入", _obj({}),
              lambda args: core.undo_last_write(args)),
        _tool("get_undo_status", "撤销状态（能否撤销/最近文件）", _obj({}),
              lambda args: core.get_undo_status(args)),
        _tool("coverage_report", "各类型打开方式/模板/文件数覆盖报告", _obj({}),
              lambda args: core.coverage_report(args)),
    ]


def _domain8_tools(core):
    return [
        _tool("upload_entity_icon", "上传任意实体图标（base64）并写实体字段",
              _obj({"type": _str("内容类型，如 focus/idea/event"),
                    "id": _str("实体 id"),
                    "image_base64": _str("图片 base64"),
                    "slot": _str("字段槽位（可选，如 character 的 advisor_large）"),
                    "icon_base": _str("图标基础名（可选，默认实体 id）")},
                   ["type", "id", "image_base64"]),
              lambda args: core.upload_entity_icon(args)),
        _tool("convert_dds", "DDS/PNG 转换",
              _obj({"path": _str("文件或目录（mod 相对或绝对）"),
                    "direction": _str("dds2png/png2dds（默认 dds2png）"),
                    "recursive": _bool("目录是否递归（可选）"),
                    "output_dir": _str("输出目录（可选）")}),
              lambda args: core.convert_dds(args)),
        _tool("import_unit_counters", "从游戏导入单位标牌库（默认 dry_run）",
              _obj({"output_dir": _str("输出目录（可选）"),
                    "dry_run": _bool("默认 true 只预览")}),
              lambda args: core.import_unit_counters(args)),
        _tool("list_unit_counters", "查询单位标牌库",
              _obj({"keyword": _str("名称过滤（可选）"),
                    "category": _str("类别过滤（可选）")}),
              lambda args: core.list_unit_counters(args)),
    ]


def _domain9_tools(core):
    specs = [
        ("generate_ideas", "生成民族精神", "ideas", "ideas"),
        ("generate_ideologies", "生成意识形态", "ideologies", "ideologies"),
        ("generate_characters", "生成角色", "characters", "groups"),
        ("generate_generals", "生成将领", "generals", "leaders"),
        ("generate_country_bootstrap", "批量建国骨架", "country_bootstrap", "countries"),
        ("generate_focus_package", "生成国策三件套", "focus_package", "focuses"),
        ("generate_event", "生成事件", "event", "event_id"),
    ]
    tools = []
    for name, desc, kind, payload_key in specs:
        props = {
            "dry_run": _bool("默认 true 只返回预览"),
            "filename": _str("输出文件名主干（可选）"),
        }
        if payload_key == "event_id":
            props["event_id"] = _str("事件 id（可选）")
            props["namespace"] = _str("命名空间（可选）")
        else:
            props[payload_key] = _arr(_obj_type(), "结构化入参")
        tools.append(_tool(name, "%s（默认 dry_run）" % desc, _obj(props),
                           lambda args: getattr(core, name)(args)))
    return tools


def _domain10_tools(core):
    return [
        _tool("list_countries", "列出国家（tag/中文名/[mod 已接管]）", _obj({}),
              lambda args: core.list_countries(args)),
        _tool("copy_country_files", "复制原版国家文件到 mod（默认 dry_run）",
              _obj({"tag": _str("国家 tag"), "dirs": _arr(_str(), "目录列表"),
                    "dry_run": _bool("默认 true 只预览")}, ["tag", "dirs"]),
              lambda args: core.copy_country_files(args)),
        _tool("create_blank_overrides", "创建空覆盖接管（默认 dry_run）",
              _obj({"tag": _str("国家 tag"), "dirs": _arr(_str(), "目录列表"),
                    "dry_run": _bool("默认 true 只预览")}, ["tag", "dirs"]),
              lambda args: core.create_blank_overrides(args)),
        _tool("create_new_country_files", "创建全新国家文件（默认 dry_run）",
              _obj({"tag": _str("国家 tag"), "dirs": _arr(_str(), "目录列表"),
                    "dry_run": _bool("默认 true 只预览")}, ["tag", "dirs"]),
              lambda args: core.create_new_country_files(args)),
        _tool("create_mod", "新建 mod 项目骨架（默认 dry_run）",
              _obj({"name": _str("模组显示名"), "folder_name": _str("文件夹名"),
                    "version": _str("支持版本，默认 1.14.*"),
                    "tags": _arr(_str(), "标签列表（可选）"),
                    "mod_folder_path": _str("mod 内容根目录（或 path）"),
                    "mod_file_path": _str(".mod 文件目录（可选，默认同 mod_folder_path）"),
                    "tag": _str("可选初始国家 tag"),
                    "dry_run": _bool("默认 true 只预览")},
                   ["name", "folder_name", "version"]),
              lambda args: core.create_mod(args)),
        _tool("apply_template", "应用模板到目标文件（支持变量替换）",
              _obj({"template_name": _str("模板名"),
                    "target_path": _str("mod 内目标相对路径"),
                    "variables": _obj_type("变量替换字典（可选）")},
                   ["template_name", "target_path"]),
              lambda args: core.apply_template(args)),
        _tool("get_template", "读取模板内容",
              _obj({"template_name": _str("模板名")}, ["template_name"]),
              lambda args: core.get_template(args)),
    ]


def _rho_tools(core):
    """B3：补充 RHoiScribe 缺失能力（环境发现/符号/定义/引用/补全/解释/块级编辑/红黄绿/修复）。"""
    return [
        _tool("discover_environment",
              "环境发现：游戏/mod/可执行/文档/error_log/版本（尽力而为）",
              _obj({}),
              lambda args: core.discover_environment()),
        _tool("list_workspace_symbols",
              "列出工作区符号（块键 + id/name/token 值），可按关键词过滤",
              _obj({
                  "keyword": _str("关键词过滤（可选）"),
                  "limit": _int("最多返回数，默认 500"),
                  "include_game": _bool("是否并入游戏目录（默认否）"),
              }),
              lambda args: core.list_workspace_symbols(args)),
        _tool("find_definition",
              "查找符号定义（优先块键，其次 id/name 值）",
              _obj({
                  "name": _str("符号名"),
                  "include_game": _bool("是否并入游戏目录（默认否）"),
              }, ["name"]),
              lambda args: core.find_definition(args)),
        _tool("find_references",
              "查找符号引用（按词出现，排除定义行）",
              _obj({
                  "name": _str("符号名"),
                  "limit": _int("最多返回数，默认 200"),
                  "include_game": _bool("是否并入游戏目录（默认否）"),
              }, ["name"]),
              lambda args: core.find_references(args)),
        _tool("suggest_completion",
              "按前缀给出补全候选（块键优先）",
              _obj({
                  "prefix": _str("前缀"),
                  "limit": _int("最多返回数，默认 50"),
                  "include_game": _bool("是否并入游戏目录（默认否）"),
              }, ["prefix"]),
              lambda args: core.suggest_completion(args)),
        _tool("explain_diagnostic",
              "解释一条诊断/错误：子系统归类 + 可能原因 + 修复建议",
              _obj({"diagnostic": _str("诊断文本或错误信息")},
                   ["diagnostic"]),
              lambda args: core.explain_diagnostic(args)),
        _tool("edit_script_file",
              "块级编辑已有脚本文件：replace 替换命名块内部文本 / insert 在 after_id 后插入新块；dry_run 返回 diff，括号不平衡禁止写入",
              _obj({
                  "path": _str("mod 内相对文件路径"),
                  "block": _str("块名（replace 必填；insert 也用于描述）"),
                  "action": _str("replace / insert，默认 replace"),
                  "content": _str("新块内部文本（replace）或完整新块文本（insert）"),
                  "after_id": _str("insert 时插到该顶层块之后（可选）"),
                  "dry_run": _bool("默认 true 只预览，不写盘"),
              }, ["path"]),
              lambda args: core.edit_script_file(args)),
        _tool("validate_project",
              "红黄绿项目校验：封装 validate + health_check，按严重度分桶",
              _obj({"max_issues": _int("健康检查最多问题数，默认 500")}),
              lambda args: core.validate_project(args)),
        _tool("repair_project",
              "项目修复：移除 .txt/.gfx/.gui 的 UTF-8 BOM；dry_run 返回清单",
              _obj({
                  "dry_run": _bool("默认 true 只预览"),
                  "bom": _bool("是否做 BOM 规范化，默认 true"),
              }),
              lambda args: core.repair_project(args)),
        _tool("generate_gui_gfx_asset",
              "程序化 GUI/GFX 资产生成：PIL 渐变 PNG + .gfx spriteType 注册 + 可选 .gui 骨架；需 dry_run 后 approved=true 写盘",
              _obj({
                  "name": _str("资产名（会生成 GFX_<name> 与文件）"),
                  "size": _arr(_int(), "宽高 [w, h]，默认 [64,64]"),
                  "colors": _arr(_str(), "渐变两端颜色 hex，默认蓝系"),
                  "gui": _bool("是否同时生成 .gui 骨架（默认否）"),
                  "output_root": _str("输出相对目录（默认 gfx/interface/procedural）"),
                  "dry_run": _bool("默认 true 只返回计划"),
                  "approved": _bool("写盘需显式 true"),
              }, ["name"]),
              lambda args: core.generate_gui_gfx_asset(args)),
        _tool("validate_hoi4_debug_run",
              "调试启动预检：游戏/可执行/文档/launcher/error_log；launch=true+approved=true 才拉起 hoi4.exe -debug_mode",
              _obj({
                  "launch": _bool("是否尝试启动（默认 false）"),
                  "approved": _bool("显式批准启动（默认 false）"),
              }),
              lambda args: core.validate_hoi4_debug_run(args)),
        _tool("launch_hoi4_debug_with_rchadow",
              "Rchadow 调试启动（外部工具未内置，返回引导）",
              _obj({}),
              lambda args: core.launch_hoi4_debug_with_rchadow(args)),
        _tool("validate_hoi4_file",
              "CWT-lite 文件校验：按路径推断类型或显式 type，检查常见字段类型（红黄）",
              _obj({
                  "path": _str("mod 内相对路径（与 content 二选一）"),
                  "content": _str("脚本内容（无 path 时用）"),
                  "type": _str("类型（focus/idea/decision/event/state/ideology/division_template，可选）"),
              }),
              lambda args: core.validate_hoi4_file(args)),
        _tool("validate_hoi4_project",
              "CWT-lite 项目校验：扫描常见类型目录汇总红黄绿",
              _obj({"max_files": _int("最多扫描文件数，默认 100")}),
              lambda args: core.validate_hoi4_project(args)),
    ]


def _agent_tools(core):
    """B3 批二②：Agent 偏好持久化 + 工具审计日志。"""
    return [
        _tool("list_agent_preferences",
              "列出 Agent 持久化偏好（.runtime/agent_prefs.json）",
              _obj({}),
              lambda args: core.list_agent_preferences(args)),
        _tool("set_agent_preference",
              "设置 Agent 偏好（跨会话持久化）",
              _obj({"key": _str("偏好键"), "value": _str("偏好值（任意 JSON 值）")},
                   ["key"]),
              lambda args: core.set_agent_preference(args)),
        _tool("delete_agent_preference",
              "删除 Agent 偏好",
              _obj({"key": _str("偏好键")}, ["key"]),
              lambda args: core.delete_agent_preference(args)),
        _tool("query_tool_logs",
              "查询工具调用审计日志（可按正则过滤）",
              _obj({
                  "regex": _str("正则过滤（可选）"),
                  "limit": _int("最多返回数，默认 200"),
              }),
              lambda args: core.query_tool_logs(args)),
        _tool("export_tool_logs",
              "导出工具调用审计日志为文本（可按正则过滤）",
              _obj({"regex": _str("正则过滤（可选）"),
                    "limit": _int("最多返回数，默认 200")}),
              lambda args: core.export_tool_logs(args)),
    ]


# ══════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════

def build_tools(core):
    tools = []
    tools.extend(_existing_tools(core))
    tools.extend(_domain0_tools(core))
    tools.extend(_domain1_tools(core))
    tools.extend(_domain2_tools(core))
    tools.extend(_domain3_tools(core))
    tools.extend(_ai_tools(core))
    tools.extend(_domain5_tools(core))
    tools.extend(_domain6_tools(core))
    tools.extend(_domain7_tools(core))
    tools.extend(_domain8_tools(core))
    tools.extend(_domain9_tools(core))
    tools.extend(_domain10_tools(core))
    tools.extend(_rho_tools(core))
    tools.extend(_agent_tools(core))
    return tools


# ══════════════════════════════════════════════════════════════
# A+B 分类方案（B3）：核心集 / 分类 / 目录元数据
# ══════════════════════════════════════════════════════════════

# 默认直接暴露给 MCP 客户端的核心精选集（约 28 个，跨域高价值）
CORE_TOOLS = frozenset({
    "get_status", "list_types", "list_entities", "get_entity",
    "create_entity", "update_entity", "delete_entity",
    "read_file", "write_file", "list_files",
    "search_terms", "get_state", "list_states",
    "list_sub_units", "search_equipment",
    "validate_mod", "health_check", "get_overlay_report",
    "list_countries", "create_mod", "list_templates", "get_template",
    "discover_environment", "list_workspace_symbols", "find_definition",
    "edit_script_file", "validate_project", "explain_diagnostic",
})

# 工具名 → 分类（未列出的回退 core）
_CATEGORY_TOOLS = {
    "states-map": [
        "list_states", "get_state", "get_province", "get_owner_provinces",
        "set_state_owner", "set_state_building", "set_state_category",
        "set_country_color", "list_building_types", "list_country_colors",
        "batch_set_state_fields", "sort_state_file", "list_regions",
        "create_region", "set_region_provinces", "remove_region",
    ],
    "designers": [
        "list_ship_hulls", "list_ship_modules", "list_ship_designs",
        "get_ship_design", "create_ship_design", "update_ship_design",
        "rename_ship_design", "delete_ship_design", "sync_ship_design",
        "list_plane_hulls", "list_plane_modules", "list_plane_designs",
        "get_plane_design", "create_plane_design", "update_plane_design",
        "rename_plane_design", "delete_plane_design", "sync_plane_design",
        "list_tank_hulls", "list_tank_modules", "list_tank_designs",
        "get_tank_design", "create_tank_design", "update_tank_design",
        "rename_tank_design", "delete_tank_design", "sync_tank_design",
        "list_design_templates", "save_design_template", "load_design_template",
    ],
    "oob": [
        "list_oob_files", "list_division_templates", "get_division_template",
        "create_division_template", "update_division_template",
        "delete_division_template", "list_sub_units", "search_equipment",
    ],
    "ai": [
        "set_ai_plan_focus_order",
        "ai_plan_list", "ai_plan_create", "ai_plan_update", "ai_plan_delete",
        "ai_plan_rename", "ai_plan_duplicate",
        "ai_strategy_list", "ai_strategy_create", "ai_strategy_update",
        "ai_strategy_delete", "ai_strategy_rename", "ai_strategy_duplicate",
        "ai_ai_template_list", "ai_ai_template_create", "ai_ai_template_update",
        "ai_ai_template_delete", "ai_ai_template_rename", "ai_ai_template_duplicate",
        "ai_equipment_list", "ai_equipment_create", "ai_equipment_update",
        "ai_equipment_delete", "ai_equipment_rename", "ai_equipment_duplicate",
        "ai_navy_list", "ai_navy_create", "ai_navy_update", "ai_navy_delete",
        "ai_navy_rename", "ai_navy_duplicate",
        "ai_area_list", "ai_area_create", "ai_area_update", "ai_area_delete",
        "ai_area_rename", "ai_area_duplicate",
        "ai_focus_list", "ai_focus_create", "ai_focus_update", "ai_focus_delete",
        "ai_focus_rename", "ai_focus_duplicate",
        "ai_theater_list", "ai_theater_create", "ai_theater_update",
        "ai_theater_delete", "ai_theater_rename", "ai_theater_duplicate",
    ],
    "bop": [
        "list_bop", "get_bop", "set_bop_initial_value", "set_bop_fields",
    ],
    "localisation": [
        "write_localisation", "search_localisation", "list_missing_localisation",
        "batch_fill_localisation", "search_terms", "get_term", "add_user_term",
        "update_user_term", "remove_user_term", "vp_loc_dry_run",
    ],
    "health": [
        "validate_mod", "health_check", "scan_duplicate_ids",
        "undo_last_write", "get_undo_status", "coverage_report",
        "analyze_error_log", "get_overlay_report",
        "explain_diagnostic", "validate_project", "repair_project",
        "validate_hoi4_file", "validate_hoi4_project",
    ],
    "symbols": [
        "list_workspace_symbols", "find_definition", "find_references",
        "suggest_completion",
    ],
    "agent": [
        "list_agent_preferences", "set_agent_preference",
        "delete_agent_preference", "query_tool_logs", "export_tool_logs",
    ],
    "debug": [
        "validate_hoi4_debug_run", "launch_hoi4_debug_with_rchadow",
    ],
    "media": [
        "upload_tech_icon", "get_icon_manifest", "register_icon_batch",
        "upload_entity_icon", "convert_dds", "import_unit_counters",
        "list_unit_counters", "generate_gui_gfx_asset",
    ],
    "generators": [
        "generate_ideas", "generate_ideologies", "generate_characters",
        "generate_generals", "generate_country_bootstrap",
        "generate_focus_package", "generate_event", "create_focus_project",
    ],
    "project": [
        "list_countries", "copy_country_files", "create_blank_overrides",
        "create_new_country_files", "create_mod", "apply_template",
        "get_template", "list_templates",
    ],
}
_CATEGORY_MAP = {
    name: cat
    for cat, names in _CATEGORY_TOOLS.items()
    for name in names
}


def tool_category(name):
    """工具名 → 分类（未登记回退 core）。"""
    return _CATEGORY_MAP.get(name, "core")


# 导航工具元数据（MCP server 与 HTTP 共用；handler 由 mcp_server 装配）
NAV_TOOLS_META = [
    ("list_tools_overview",
     "列出全部 MCP 工具的分类目录（含未直接暴露的工具），供先看分类再选定工具",
     _obj({})),
    ("get_tool_schema",
     "获取任意 MCP 工具的参数 schema（含未直接暴露的工具）",
     _obj({"name": _str("工具名")}, ["name"])),
    ("invoke_tool",
     "按名调用任意 MCP 工具（含未直接暴露的工具）；参数对象放 args",
     _obj({"name": _str("工具名"),
           "args": _obj_type("工具参数对象（可空）")}, ["name"])),
]


def build_catalog(core):
    """返回全部工具 + 导航工具的元数据（含分类/核心标记/schema），供 HTTP/概览使用。"""
    metas = []
    for t in build_tools(core):
        metas.append({
            "name": t["name"],
            "description": t["description"],
            "category": tool_category(t["name"]),
            "core": t["name"] in CORE_TOOLS,
            "inputSchema": t["inputSchema"],
        })
    for name, desc, schema in NAV_TOOLS_META:
        metas.append({
            "name": name, "description": desc,
            "category": "nav", "core": True, "inputSchema": schema,
        })
    return metas