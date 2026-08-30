# MCP 与接口规格

> 本文档是 HOI4 Mod 编辑器**外部接口（MCP / HTTP / ApiCore）的当前规格与参考清单**。
> 旧 `docs/mcp补充计划与执行方式.md` 已完成并删除，本文档取代它；工具清单以 `src/mcp_tools.py` 运行为准。
> 最后核验：2026-08-23；`tools/verify_contracts.py` 全量通过（402 用例）。

## 1. 总览

- **统一核心**：`src/api_server.py` 中的 `ApiCore` 是 HTTP / MCP / CLI 共用的操作核心，禁止另起实现。
- **MCP 工具数**：178 个 = 原有 17 + 域扩展 142 + B3 9（RHoiScribe）+ agent 5 + GFX 1 + debug 2 + CWT 2。
- **HTTP**：仅绑定 `127.0.0.1`，Bearer token 鉴权；提供 `/api/mcp/<tool_name>` 同源桥，可直接调用全部 178 个 MCP 工具。
- **MCP**：优先官方 `mcp` 库（FastMCP）；未安装时回退内置零依赖实现（newline JSON-RPC 2.0，协议 `2024-11-05`）。
- **写回纪律**：所有写路径经 `write_utils.atomic_write_text`（或已有数据层内部原子写），禁止在接口层直接 `open(path, "w")`；本地化 yml 走 `utf-8-sig`。
- **原版保护**：涉及游戏本体文件的写操作先 `ensure_file_in_mod` 复制到 mod，绝不直写游戏本体。
- **dry_run 约定**：批量/结构操作默认 `dry_run=true`，只返回 `{files:[...]}` 预览；显式传 `dry_run=false` 才落盘。

## 2. 架构与文件

| 文件 | 职责 |
| --- | --- |
| `src/api_server.py` | `ApiCore` 组合 9 个域 Mixin；HTTP 服务 `_ApiHTTPServer` / `ApiHandler`；`/api/mcp/<tool_name>` 通用桥 |
| `src/api_core_ext/` | 按域扩展 Mixin：`states` / `designers` / `ai_content` / `bop` / `loc_tools` / `health` / `media` / `generators` / `project` |
| `src/mcp_tools.py` | `build_tools(core)` 返回 178 个工具注册表（schema + handler）；MCP / HTTP 共用 |
| `src/mcp_server.py` | FastMCP 与内置零依赖 MCP Server 入口，消费 `build_tools` |
| `src/mod_creator.py` | 新建 mod 骨架生成纯函数（从 ModCreatorDialog 下沉） |
| `src/bop_loader.py` | BOP 查询与 `set_bop_initial_value` / `set_bop_fields` 保存下沉 |

API 方法约定：dict 进 dict 出；数据层 lazy import；写方法结束后清对应缓存并调用 `_notify_change(path)`；错误抛 `ValueError`（HTTP 400 / MCP 错误文本）。

## 3. HTTP API 端点

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/api/status` | GET | 服务信息（mod/game 路径、内容类型数） |
| `/api/types` | GET | 内容类型列表 |
| `/api/entities?type=&country=&kw=` | GET | 实体列表 |
| `/api/entities/<type>/<id>` | GET / PUT / DELETE | 实体详情 / 更新 / 删除 |
| `/api/entities` | POST | 新建实体 |
| `/api/project` | POST | 项目级国策联动生成 |
| `/api/localisation` | POST | 写本地化词条 |
| `/api/validate` | POST | 校验 mod |
| `/api/templates?type=&usage=` | GET | 模板列表 |
| `/api/files?type=` | GET | 文件列表 |
| `/api/files` | POST | 读文件 `{path}` / 写整文件 `{path, content}` |
| `/api/tech_icon` | POST | 科技图标上传 + GFX 注册 |
| `/api/icon_manifest?query=&source=&limit=` | GET | 图标库 manifest |
| `/api/overlay_report?summary_only=` | GET | mod 覆盖原版增量报告 |
| `/api/tools/format_pdx` | POST | PDX 格式化 |
| `/api/tools/vp_loc` | GET | VP 本地化干跑 |
| `/api/tools/error_log` | POST | 错误日志分析 |
| `/api/tools/register_icon_batch` | POST | 批量补注册缺失图标 GFX |
| `/api/mcp/<tool_name>` | GET / POST | 同源工具桥：调用任意 MCP 工具 |
| `/api/help` | GET | 端点说明 |

鉴权：`Authorization: Bearer <token>`。错误映射：`ValueError` → 400；其他异常 → 500。

## 4. MCP 工具清单（178）

参数格式：`名字* 类型`，`*` 表示必填。类型取值：`string` / `integer` / `number` / `boolean` / `array<...>` / `object`。

### 现有 17 个基础工具

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `create_entity` | 新建实体（写入该国现有文件或类型目录新文件），支持自定义块内容 | `type*` string<br>`id*` string<br>`country` string<br>`content` string |
| `create_focus_project` | 项目级联动：一键生成国策+触发事件+决议+图标占位+本地化词条 | `country*` string<br>`focus_id*` string<br>`name` string<br>`desc` string<br>`x` integer<br>`y` integer<br>`event` boolean<br>`decision` boolean<br>`icon` boolean<br>`localisation` boolean |
| `delete_entity` | 删除实体 | `type*` string<br>`id*` string |
| `get_entity` | 获取单个实体的完整 PDX 块文本（用于读取内容后修改） | `type*` string<br>`id*` string |
| `get_icon_manifest` | 图标库 manifest：扫描 mod+游戏全部 gfx spriteType 定义 | `query` string<br>`source` string<br>`limit` integer |
| `get_overlay_report` | mod 覆盖原版的增量报告（规则分层 + 文件级 delta） | `summary_only` boolean |
| `get_status` | 获取当前 mod 与游戏目录、内容类型数量等状态信息 | — |
| `list_entities` | 列出指定内容类型下的实体（可按国家/关键词过滤） | `type*` string<br>`country` string<br>`keyword` string |
| `list_files` | 列出指定内容类型目录下的全部文件（含路径/大小） | `type*` string |
| `list_templates` | 列出可用模板（可按类型/用途过滤） | `type` string<br>`usage` string |
| `list_types` | 列出全部内容类型（角色/国策/事件/决议/科技/触发动作等 90+ 种） | — |
| `read_file` | 读取 mod 内指定相对路径文件的完整内容（用于文件级编辑/复现） | `path*` string |
| `update_entity` | 替换实体块内容（content 为新块文本） | `type*` string<br>`id*` string<br>`content*` string |
| `upload_tech_icon` | 上传科技图标：图片 base64 写入 gfx/interface/technologies/，并自动注册 GFX_<tech_id>_medium | `tech_id*` string<br>`image_base64*` string<br>`filename` string |
| `validate_mod` | 校验 mod：本地化缺失 / 国策引用悬空 / 未知引用 / 重复 ID | — |
| `write_file` | 整文件写入（新建/覆盖）：{path, content}，路径须为 mod 内相对路径 | `path*` string<br>`content*` string |
| `write_localisation` | 写本地化词条到 mod 翻译文件 | `tag` string<br>`entries*` object |

### 域0：存量补齐（4 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `analyze_error_log` | 游戏错误日志分析 + 子系统归类 | `path` string<br>`absolute_path` string |
| `format_pdx` | PDX 文件格式化写回 | `path*` string<br>`whitespace` boolean<br>`ignore_comments` boolean |
| `register_icon_batch` | 批量补注册文件内缺失图标 GFX | `path*` string<br>`type` string |
| `vp_loc_dry_run` | VP 本地化干跑预览（不写文件） | — |

### 域1：州 / 建筑 / 区域（16 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `batch_set_state_fields` | 批量设置州字段（默认 dry_run） | `state_ids*` array<integer><br>`field*` string<br>`value*` string<br>`dry_run` boolean |
| `create_region` | 新建区域 | `kind*` string<br>`region_id` integer<br>`province_ids*` array<integer> |
| `get_owner_provinces` | 获取国家拥有地块（tag 缺省返回全部 owner 表） | `tag` string |
| `get_province` | 获取省信息（所属州/类型/地形/沿海） | `province_id*` integer |
| `get_state` | 获取州完整信息（建筑/VP/省份/src） | `state_id*` integer |
| `list_building_types` | 列出建筑类型（可建/图标/修饰） | — |
| `list_country_colors` | 列出全部国家颜色 | — |
| `list_regions` | 列出战略区/补给区 | `kind` string |
| `list_states` | 列出州（可按 owner/keyword 过滤） | `owner` string<br>`keyword` string |
| `remove_region` | 删除区域 | `kind*` string<br>`region_id*` integer |
| `set_country_color` | 设置国家颜色（0-255） | `tag*` string<br>`r*` integer<br>`g*` integer<br>`b*` integer |
| `set_region_provinces` | 替换区域省份列表 | `kind*` string<br>`region_id*` integer<br>`province_ids*` array<integer> |
| `set_state_building` | 设置州建筑（省/州级；level<=0 移除） | `state_id*` integer<br>`building*` string<br>`level*` integer<br>`province_id` integer |
| `set_state_category` | 设置州类别 | `state_id*` integer<br>`category*` string |
| `set_state_owner` | 设置州归属（只写 mod，原版自动复制） | `state_id*` integer<br>`tag*` string |
| `sort_state_file` | 按州 id 排序州文件 | `path*` string |

### 域2：三军设计器 + 设计模板（30 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `create_plane_design` | 新建飞机设计 | `country*` string<br>`name*` string<br>`hull*` string<br>`upgrades*` object |
| `create_ship_design` | 新建舰艇设计 | `country*` string<br>`name*` string<br>`hull*` string<br>`upgrades*` object |
| `create_tank_design` | 新建坦克设计 | `country*` string<br>`name*` string<br>`hull*` string<br>`upgrades*` object |
| `delete_plane_design` | 删除飞机设计 | `country*` string<br>`name*` string |
| `delete_ship_design` | 删除舰艇设计 | `country*` string<br>`name*` string |
| `delete_tank_design` | 删除坦克设计 | `country*` string<br>`name*` string |
| `get_plane_design` | 获取单个飞机设计及属性估算 | `country*` string<br>`name*` string |
| `get_ship_design` | 获取单个舰艇设计及属性估算 | `country*` string<br>`name*` string |
| `get_tank_design` | 获取单个坦克设计及属性估算 | `country*` string<br>`name*` string |
| `list_design_templates` | 列出设计模板 | `kind*` string |
| `list_plane_designs` | 列出飞机设计（可按国家过滤） | `country` string |
| `list_plane_hulls` | 列出飞机船体/机型/底盘 | — |
| `list_plane_modules` | 列出飞机模块 | — |
| `list_ship_designs` | 列出舰艇设计（可按国家过滤） | `country` string |
| `list_ship_hulls` | 列出舰艇船体/机型/底盘 | — |
| `list_ship_modules` | 列出舰艇模块 | — |
| `list_tank_designs` | 列出坦克设计（可按国家过滤） | `country` string |
| `list_tank_hulls` | 列出坦克船体/机型/底盘 | — |
| `list_tank_modules` | 列出坦克模块 | — |
| `load_design_template` | 读取设计模板内容 | `kind*` string<br>`name*` string |
| `rename_plane_design` | 重命名飞机设计 | `country*` string<br>`old*` string<br>`new*` string |
| `rename_ship_design` | 重命名舰艇设计 | `country*` string<br>`old*` string<br>`new*` string |
| `rename_tank_design` | 重命名坦克设计 | `country*` string<br>`old*` string<br>`new*` string |
| `save_design_template` | 保存设计模板 | `kind*` string<br>`name*` string<br>`content*` string |
| `sync_plane_design` | 把飞机设计同步到所有同名设计国家（默认 dry_run） | `name*` string<br>`dry_run` boolean |
| `sync_ship_design` | 把舰艇设计同步到所有同名设计国家（默认 dry_run） | `name*` string<br>`dry_run` boolean |
| `sync_tank_design` | 把坦克设计同步到所有同名设计国家（默认 dry_run） | `name*` string<br>`dry_run` boolean |
| `update_plane_design` | 更新飞机设计模块 | `country*` string<br>`name*` string<br>`upgrades*` object |
| `update_ship_design` | 更新舰艇设计模块 | `country*` string<br>`name*` string<br>`upgrades*` object |
| `update_tank_design` | 更新坦克设计模块 | `country*` string<br>`name*` string<br>`upgrades*` object |

### 域3：师编制 / OOB（8 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `create_division_template` | 新建师编制 | `path*` string<br>`name*` string<br>`units` array<object><br>`support` array<object><br>`is_locked` boolean |
| `delete_division_template` | 删除师编制 | `path*` string<br>`name*` string |
| `get_division_template` | 获取单个师编制及统计 | `path*` string<br>`name*` string |
| `list_division_templates` | 列出师编制（可指定文件） | `path` string |
| `list_oob_files` | 列出 OOB 文件（含军种识别） | — |
| `list_sub_units` | 列出营/兵种属性 | `keyword` string |
| `search_equipment` | 搜索装备属性 | `keyword` string<br>`category` string |
| `update_division_template` | 更新师编制 | `path*` string<br>`name*` string<br>`units` array<object><br>`support` array<object><br>`is_locked` boolean<br>`content` string |

### 域4：AI 内容 8 类（49 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `ai_ai_template_create` | 新建AI 师模板 | `id` string<br>`role` string |
| `ai_ai_template_delete` | 删除AI 师模板 | `id` string |
| `ai_ai_template_duplicate` | 复制AI 师模板 | `id` string<br>`new` string |
| `ai_ai_template_list` | 列出AI 师模板 | — |
| `ai_ai_template_rename` | 重命名AI 师模板 | `id` string<br>`new` string |
| `ai_ai_template_update` | 更新AI 师模板 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_area_create` | 新建AI 区域 | `id` string<br>`strategic_regions` array<integer> |
| `ai_area_delete` | 删除AI 区域 | `id` string |
| `ai_area_duplicate` | 复制AI 区域 | `id` string<br>`new` string |
| `ai_area_list` | 列出AI 区域 | — |
| `ai_area_rename` | 重命名AI 区域 | `id` string<br>`new` string |
| `ai_area_update` | 更新AI 区域 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_equipment_create` | 新建AI 装备 | `id` string<br>`category` string |
| `ai_equipment_delete` | 删除AI 装备 | `id` string |
| `ai_equipment_duplicate` | 复制AI 装备 | `id` string<br>`new` string |
| `ai_equipment_list` | 列出AI 装备 | — |
| `ai_equipment_rename` | 重命名AI 装备 | `id` string<br>`new` string |
| `ai_equipment_update` | 更新AI 装备 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_focus_create` | 新建AI 科研权重 | `id` string<br>`research` object |
| `ai_focus_delete` | 删除AI 科研权重 | `id` string |
| `ai_focus_duplicate` | 复制AI 科研权重 | `id` string<br>`new` string |
| `ai_focus_list` | 列出AI 科研权重 | — |
| `ai_focus_rename` | 重命名AI 科研权重 | `id` string<br>`new` string |
| `ai_focus_update` | 更新AI 科研权重 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_navy_create` | 新建AI 海军 | `id` string<br>`section` string<br>`objective_type` string<br>`min_priority` string<br>`max_priority` string |
| `ai_navy_delete` | 删除AI 海军 | `id` string<br>`section` string |
| `ai_navy_duplicate` | 复制AI 海军 | `id` string<br>`section` string<br>`new` string |
| `ai_navy_list` | 列出AI 海军 | — |
| `ai_navy_rename` | 重命名AI 海军 | `id` string<br>`section` string<br>`new` string |
| `ai_navy_update` | 更新AI 海军 | `id` string<br>`section` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_plan_create` | 新建战略计划 | `id` string<br>`name` string<br>`desc` string |
| `ai_plan_delete` | 删除战略计划 | `id` string |
| `ai_plan_duplicate` | 复制战略计划 | `id` string<br>`new` string |
| `ai_plan_list` | 列出战略计划 | — |
| `ai_plan_rename` | 重命名战略计划 | `id` string<br>`new` string |
| `ai_plan_update` | 更新战略计划 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_strategy_create` | 新建战略倾向 | `id` string<br>`entries` array<object> |
| `ai_strategy_delete` | 删除战略倾向 | `id` string |
| `ai_strategy_duplicate` | 复制战略倾向 | `id` string<br>`new` string |
| `ai_strategy_list` | 列出战略倾向 | — |
| `ai_strategy_rename` | 重命名战略倾向 | `id` string<br>`new` string |
| `ai_strategy_update` | 更新战略倾向 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `ai_theater_create` | 新建AI 派系战区 | `id` string<br>`name` string<br>`regions` array<integer> |
| `ai_theater_delete` | 删除AI 派系战区 | `id` string |
| `ai_theater_duplicate` | 复制AI 派系战区 | `id` string<br>`new` string |
| `ai_theater_list` | 列出AI 派系战区 | — |
| `ai_theater_rename` | 重命名AI 派系战区 | `id` string<br>`new` string |
| `ai_theater_update` | 更新AI 派系战区 | `id` string<br>`field` string<br>`value` string<br>`quoted` boolean<br>`content` string<br>`focus_order` array<string><br>`entries` array<object><br>`strategic_regions` array<integer><br>`regions` array<integer><br>`preferred_countries` array<string><br>`role_id` string<br>`target_id` string<br>`group_id` string<br>`variant_id` string |
| `set_ai_plan_focus_order` | 设置 AI 战略计划的国策顺序（等价 focus_order_picker 结果） | `plan_id*` string<br>`ordered_focus_ids*` array<string> |

> AI 工具必填规则：`create/update/delete` 必须 `id`；`rename/duplicate` 必须 `id` 和 `new`；`ai_navy_*` 必须 `section`。完整说明见 §6I。

### 域5：BOP（4 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `get_bop` | 获取单个 BOP（含动作/区间/修正/当前区间） | `bop_id*` string |
| `list_bop` | 列出力量平衡 BOP 概览 | — |
| `set_bop_fields` | 保存 BOP 基础字段（可部分更新） | `bop_id*` string<br>`left_side` string<br>`right_side` string<br>`decision_category` string |
| `set_bop_initial_value` | 保存 BOP initial_value | `bop_id*` string<br>`value*` number |

### 域6：本地化 / 词条（8 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `add_user_term` | 新增用户词条 | `key*` string<br>`cn*` string<br>`node_type` string<br>`tags` array<string><br>`description` string |
| `batch_fill_localisation` | 批量补本地化（默认 dry_run） | `entries` object<br>`dry_run` boolean |
| `get_term` | 获取单个词条 | `key*` string |
| `list_missing_localisation` | 列出缺失本地化词条 | — |
| `remove_user_term` | 删除用户词条 | `key*` string |
| `search_localisation` | 搜索本地化词条（mod 优先回退原版） | `keyword` string<br>`language` string |
| `search_terms` | 搜索词条库（QIUQI 1887 词条） | `keyword` string<br>`node_type` string<br>`tag` string<br>`limit` integer |
| `update_user_term` | 更新用户词条 | `key*` string<br>`cn` string<br>`node_type` string<br>`tags` array<string><br>`description` string |

### 域7：校验 / 健康 / 撤销 / 覆盖（5 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `coverage_report` | 各类型打开方式/模板/文件数覆盖报告 | — |
| `get_undo_status` | 撤销状态（能否撤销/最近文件） | — |
| `health_check` | 导出前健康检查（8 类） | `max_issues` integer |
| `scan_duplicate_ids` | 扫描重复 id（focus/event/decision 等） | `types` string |
| `undo_last_write` | 撤销最近一次文件写入 | — |

### 域8：图标 / 媒体（4 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `convert_dds` | DDS/PNG 转换 | `path` string<br>`direction` string<br>`recursive` boolean<br>`output_dir` string |
| `import_unit_counters` | 从游戏导入单位标牌库（默认 dry_run） | `output_dir` string<br>`dry_run` boolean |
| `list_unit_counters` | 查询单位标牌库 | `keyword` string<br>`category` string |
| `upload_entity_icon` | 上传任意实体图标（base64）并写实体字段 | `type*` string<br>`id*` string<br>`image_base64*` string<br>`slot` string<br>`icon_base` string |

### 域9：内容生成器（7 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `generate_characters` | 生成角色（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`groups` array<object> |
| `generate_country_bootstrap` | 批量建国骨架（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`countries` array<object> |
| `generate_event` | 生成事件（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`event_id` string<br>`namespace` string |
| `generate_focus_package` | 生成国策三件套（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`focuses` array<object> |
| `generate_generals` | 生成将领（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`leaders` array<object> |
| `generate_ideas` | 生成民族精神（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`ideas` array<object> |
| `generate_ideologies` | 生成意识形态（默认 dry_run） | `dry_run` boolean<br>`filename` string<br>`ideologies` array<object> |

### 域10：项目级（7 个）

| 工具 | 说明 | 参数 |
| --- | --- | --- |
| `apply_template` | 应用模板到目标文件（支持变量替换） | `template_name*` string<br>`target_path*` string<br>`variables` object |
| `copy_country_files` | 复制原版国家文件到 mod（默认 dry_run） | `tag*` string<br>`dirs*` array<string><br>`dry_run` boolean |
| `create_blank_overrides` | 创建空覆盖接管（默认 dry_run） | `tag*` string<br>`dirs*` array<string><br>`dry_run` boolean |
| `create_mod` | 新建 mod 项目骨架（默认 dry_run；落盘需 `approved=true`） | `name*` string<br>`folder_name*` string<br>`version*` string<br>`mod_folder_path*` string<br>`tags` array<string><br>`mod_file_path` string<br>`tag` string<br>`dry_run` boolean<br>`approved` boolean |
| `create_new_country_files` | 创建全新国家文件（默认 dry_run） | `tag*` string<br>`dirs*` array<string><br>`dry_run` boolean |
| `get_template` | 读取模板内容 | `template_name*` string |
| `list_countries` | 列出国家（tag/中文名/[mod 已接管]） | — |

## 5. dry_run 工具清单

以下工具默认 `dry_run=true`：

| 工具 | 说明 |
| --- | --- |
| `batch_fill_localisation` | 批量补本地化（默认 dry_run） |
| `batch_set_state_fields` | 批量设置州字段（默认 dry_run） |
| `copy_country_files` | 复制原版国家文件到 mod（默认 dry_run） |
| `create_blank_overrides` | 创建空覆盖接管（默认 dry_run） |
| `create_mod` | 新建 mod 项目骨架（默认 dry_run） |
| `create_new_country_files` | 创建全新国家文件（默认 dry_run） |
| `generate_characters` | 生成角色（默认 dry_run） |
| `generate_country_bootstrap` | 批量建国骨架（默认 dry_run） |
| `generate_event` | 生成事件（默认 dry_run） |
| `generate_focus_package` | 生成国策三件套（默认 dry_run） |
| `generate_generals` | 生成将领（默认 dry_run） |
| `generate_ideas` | 生成民族精神（默认 dry_run） |
| `generate_ideologies` | 生成意识形态（默认 dry_run） |
| `import_unit_counters` | 从游戏导入单位标牌库（默认 dry_run） |
| `sync_plane_design` | 把飞机设计同步到所有同名设计国家（默认 dry_run） |
| `sync_ship_design` | 把舰艇设计同步到所有同名设计国家（默认 dry_run） |
| `sync_tank_design` | 把坦克设计同步到所有同名设计国家（默认 dry_run） |

## 6. MCP Server 运行

```bash
# 命令行方式
python mcp_server.py --mod <mod目录> [--game <游戏目录>]
```
Claude Code 配置示例：
```json
{ "mcpServers": { "hoi4-mod-builder": {
    "command": "python",
    "args": ["E:/hearts_of_iron_builder/mcp_server.py", "--mod", "E:/mods/my_mod"],
    "env": {} } } }
```
若未安装官方 `mcp` 库，`BuiltinMcpServer` 使用 newline-delimited JSON-RPC 2.0 over stdio，支持 `initialize` / `notifications/initialized` / `ping` / `tools/list` / `tools/call`。

## 6A. A+B 分类方案（2026-08-25）

为降低 178 个工具对 agent 的上下文/发现性负担，MCP 采用「核心精选 + 分类白名单 + 导航工具」渐进暴露：

- **默认 `tools/list` 只返回核心精选（约 22 个）+ 3 个导航工具**（共 25 个），其余工具不在列表中出现。
- **3 个导航工具**（`mcp_server._build_nav_tools`，均可在 `tools/call` 直接调用）：
  - `list_tools_overview`：全部工具的分类目录（含未直接暴露的），返回 `{total, categories:{分类:[工具名...]}}`；
  - `get_tool_schema(name)`：任意工具的参数 schema + 分类；
  - `invoke_tool(name, args)`：按名调用任意工具（**全部 178 个隐藏工具都可经它调用**，能力不丢）。
- **分类白名单**：环境变量 `MCP_EXPOSE_CATEGORIES`（逗号分隔分类名，或 `all` 全开）会让 `tools/list` 额外包含对应分类的全部工具。分类：`core / states-map / designers / oob / ai / bop / localisation / health / media / generators / project / nav`。
- **HTTP 同步端点**：
  - `GET /api/mcp/overview` → 分类目录；
  - `GET /api/mcp/schema?name=<tool>` → 工具 schema；
  - `POST /api/mcp/invoke_tool` `{name, args}` → 调用任意工具。
- 元数据来源：`mcp_tools.tool_category` / `CORE_TOOLS` / `NAV_TOOLS_META` / `build_catalog`（178 + 3 导航 = 181 条）。
- 说明：MCP 客户端只能看到 `tools/list` 返回的工具，因此隐藏工具在客户端侧非「一等公民」（须经 `invoke_tool`）；官方 mcp 库路径同样只注册暴露集。

## 6B. B3 补充：RHoiScribe 缺失能力（2026-08-25，9 个新工具）

| 工具 | 分类 | 说明 |
| --- | --- | --- |
| `discover_environment` | core | 环境发现：游戏/mod/可执行/文档/error_log/版本 |
| `list_workspace_symbols` | symbols | 工作区符号（块键 + id/name/token 值），可按关键词过滤 |
| `find_definition` | symbols | 符号定义定位（优先块键，其次 id/name 值） |
| `find_references` | symbols | 符号引用定位（按词出现，排除定义行） |
| `suggest_completion` | symbols | 前缀补全候选（块键优先） |
| `explain_diagnostic` | health | 诊断解释：子系统归类 + 可能原因 + 修复建议 |
| `edit_script_file` | core | 块级编辑已有脚本：replace/insert + dry_run diff + 括号平衡检查 |
| `validate_project` | health | 红黄绿项目校验（validate + health_check 分桶） |
| `repair_project` | health | 项目修复：移除 .txt/.gfx/.gui 的 UTF-8 BOM（dry_run/apply） |

实现：`src/project_symbols.py`（纯扫描/定义/引用/补全）+ `src/api_server.py::ApiCore` 新增方法 +
`src/mcp_tools.py::_rho_tools` 注册。仍未落地的高成本项（CWT 类型规则校验 / 调试启动 / GUI-GFX 程序化生成 /
Agent 偏好与工具审计日志）登记为待拍板，见 `docs/RHoiScribe知识映射与补全.md`。

## 6C. MCP resources / prompts（2026-08-25，批二 ①）

内置零依赖 MCP 实现新增 `resources` 与 `prompts` 能力（`initialize` capabilities 声明）：

- **resources**（`resources/list` / `resources/read`）：
  - `hoi4://status` 运行状态；`hoi4://tools/overview` 工具分类目录；
  - `hoi4://terms?keyword=…` 词条库检索；`hoi4://docs/rhoiscribe`、`hoi4://docs/mcp`、`hoi4://docs/quickstart` 项目文档；
  - `hoi4://docs/user` / `hoi4://docs/developer` / `hoi4://docs/pitfalls` 知识文档；
  - `hoi4://templates/mcp` 正确调用模板清单。
- **prompts**（`prompts/list` / `prompts/get`）：`create_focus` / `validate_project` / `fix_error_log` / `edit_script_block`
  工作流提示，以及 `create_mod_from_scratch`（从零新建 mod 的端到端步骤）、`mcp_workflow`（使用者/开发者工作流）。
- 实现位置：`src/mcp_server.py::BuiltinMcpServer`；官方 mcp 库路径暂只注册 tools（若后续 mcp 库可用再补
  resources/prompts 动态注册）。

## 6D. Agent 偏好持久化 + 工具审计日志（2026-08-25，批二②）

> 注意：6D-6G 中的“工具总数”是各批次落地时的累计快照；当前唯一权威为 `src/mcp_tools.py::build_tools()`，共 178 个。

- 偏好：`list_agent_preferences` / `set_agent_preference` / `delete_agent_preference`
  （`.runtime/agent_prefs.json`，跨会话持久化）。
- 审计：`query_tool_logs` / `export_tool_logs`（`.runtime/tool_logs.jsonl`，JSON lines，可按正则过滤）。
- 埋点：MCP `tools/call`、HTTP `/api/mcp/invoke_tool` 与 `/api/mcp/<tool>` 桥自动记录 `log_tool_call`。
- 分类：`agent`；工具总数 173（159 + 9 + 5）。

## 6E. GUI/GFX 程序化资产生成（2026-08-25，批二③）

- 工具：`generate_gui_gfx_asset`（`src/api_core_ext/media.py` + `src/procedural_assets.py`）。
- 流程：`dry_run=true` 返回计划文件清单；写盘需 `approved=true` 且 `dry_run=false`。
- 产物：PIL 程序化渐变圆角 PNG → `.gfx` spriteType 注册（复用 `ensure_sprite_in_gfx_file`）→ 可选 `.gui` 骨架。
- 分类：`media`；工具总数 **174**（159 + 9 + 5 + 1）。

## 6F. 调试启动（2026-08-25，批二④）

- 工具：`validate_hoi4_debug_run`（预检游戏/可执行/文档/launcher/error_log；`launch=true`+`approved=true` 才拉起
  `hoi4.exe -gdpr-compliant -debug_mode`）、`launch_hoi4_debug_with_rchadow`（Rchadow 外部工具未内置，返回引导）。
- 安全边界：**显式 approved=true 才启动进程**；预检非全绿不启动。
- 分类：`debug`；工具总数 **176**（159 + 9 + 5 + 1 + 2）。

## 6G. CWT-lite 类型规则校验（2026-08-25，批二⑤；2026-08-26 批三①扩充）

- 工具：`validate_hoi4_file`（按路径推断类型或显式 `type`，校验常见字段类型，红黄绿）、
  `validate_hoi4_project`（扫描常见类型目录批量汇总）。
- 规则库：`src/cwt_lite_rules.py`（自研 PDX 解析；未知字段不报避免误报）。**为轻量替代，非 cwtools 全量**。
- **批三①扩充（2026-08-26）**：`RULE_CATALOG` 从 7 类扩到 **24 类**——新增 character / technology /
  building / modifier / opinion_modifier / wargoal / operation / on_action / strategic_region /
  supply_area / occupation_law / difficulty_setting / game_rule / autonomous_state /
  dynamic_modifier / bookmark / intelligence_agency；`infer_type` 新增 ~17 条路径推断；
  `_WRAPPER_TYPES` + `_iter_entity_blocks` 支持 wrapper 型顶层块（characters/technologies/
  buildings/modifiers/operations…）与 strategic_region/supply_area 顶层块遍历。
  真实数据校验（character/technology/building/bookmark/strategic_region/on_action/game_rule）→ 0 红。
- **批三①b 深度扩充（2026-08-26）**：`_iter_entity_blocks` 覆盖真实结构——决议 category 顶层块
  （任意键 → 直接子块即 decision）、modifier/operation/occupation_law/game_rule/dynamic_modifier
  顶层块即实体、wargoal `wargoal_types` 包装、autonomous_state/intelligence_agency 固定键顶层块；
  数值字段引入 `var_int`/`var_number`（容忍 `@const`/`var_*`/`[表达式]`/`global.x` 命名空间变量）；
  event `title/desc` 允许块或本地化键标量；block 字段遇 `key=` 换行 `{` 的空值产物不报红。
  **全量真实数据冒烟：24 类型 mod+game 共 6,388 文件 0 红**。
- **批三①c 再扩充（2026-08-26）**：新增 5 类型 → **29 类**——`scripted_effect`/`scripted_trigger`
  （空 catalog 仅识别+遍历）、`scripted_localisation`（defined_text：name/text/trigger/
  localization_key）、`country`/`country_history`（整文件即实体，直接校验顶层字段，如
  graphical_culture/capital/set_research_slots/oob/set_technology/add_ideas…）；
  `infer_type` 新增 5 条路径；`MAX_PARSE_CHARS` 超大文件（>2MB，如 19 万行自动生成 RU 本地化）
  跳过解析返回黄色提示，避免既有解析器性能问题导致挂起。
  **全量真实数据冒烟：5 新类型 mod+game 共 2,419 文件 0 红**。
- **批三①d 再扩充（2026-08-26）**：新增 3 类型 → **32 类**——`state_category`
  （state_categories wrapper：local_building_slots/color）、`terrain`
  （categories wrapper：movement_cost/combat_width/is_water/naval_terrain/sound_type…）、
  `resource`（resources wrapper：icon_frame/cic/convoys）；`infer_type` 新增 3 条路径。
  **全量真实数据冒烟：3 新类型 mod+game 17 文件 0 红**。
- **批三①e 再扩充（2026-08-26）**：新增 `unit` → **33 类**——`common/units` 的
  `sub_units` wrapper（sprite/priority/active/max_organisation/supply_consumption/
  breakthrough/soft_attack…约 60 字段）；`common/units` 推断从 division_template 修正为
  unit（history/units 仍为 division_template）；`var_*` 增加点号数字容忍（3.5.5 mod 写法）。
  `validate_hoi4_project` 扫描目录扩至全部 33 类型目录（原 7 目录 → 33）。
  **全量真实数据冒烟：unit mod+game 548 文件 0 红；真实 mod project 扫描 300 文件 0 红**。
- 分类：`health`；工具总数 **178**（159 + 9 + 5 + 1 + 2 + 2）。

## 6H. MCP 全量工具真实数据冒烟（2026-08-26，批三②）

- 工具：`tools/smoke_mcp_tools.py`——对真实 mod（`/mnt/e/mods/3350890356`）跑全量
  **178 个工具**默认冒烟（`--full` 含重型）；自动构造参数、写工具要求 `dry_run`、
  数据缺失记 `skip-data`（非致命）、重型工具记 `skipped-heavy`。
- 结果（默认模式）：**ok=40 error=0**（另有 skipped=36 / skipped-write=56 /
  skip-data=7 / skipped-heavy=39）；退出码 0。
- 踩坑与修复：
  1. **挂死定位**：`get_icon_manifest`（`build_icon_manifest` 全库扫描 mod+game
     spriteType，实测 **238s / 20,430 条**）→ 归入 `HEAVY_TOOLS`；
     `list_missing_localisation`/`batch_fill_localisation`
     （`check_localisation_coverage` 全项目扫描，实测 **202s / 8,193 条缺失**）→ 归入
     `HEAVY_TOOLS`。
  2. **真实 bug**：`list_unit_counters` 调 `lib.search(keyword=, category=)` 但
     `UnitCounterLibrary.search(kw=)` 不接收 → 修复 `unit_counter_library.search`
     兼容 `keyword/category`（`src/unit_counter_library.py`）。
- 回归：新增 `tests/test_mcp_smoke_real.py`（guarded：无真实 mod/game 目录时
  `skipUnless` 跳过；真实环境跑全量默认冒烟断言 0 error）。
- 分类：`health`；工具总数 **178**。

## 6I. P0/P1 可发现性修补（2026-08-26）

针对空白智能体“能不能明白该怎么做”的评估结果，补齐以下可发现性缺口：

- **`create_mod` schema 修正**：
  - `mod_folder_path` 改为必填（与 handler 一致）；
  - 新增 `approved` 布尔参数；描述明确“`dry_run=false` 时须 `approved=true`”。
- **AI CRUD 必填修正**：
  - `ai_*_create/update/delete` 必填 `id`；
  - `ai_*_rename/duplicate` 必填 `id`、`new`；
  - `ai_navy_*` 必填 `section`（goal/fleet/taskforce）。
- **生成器示例**：
  - 7 个 `generate_*` 工具的 schema 均附加 `examples` 字段，包含最小可运行入参；
  - `generate_event` 补充 `event_ids` / `title` / `desc` / `option` 可选参数；
  - `generate_focus_package` 补充 `tree_id` / `with_icon_gfx`；
  - `generate_generals` 补充 `character_id`。
- **新增 `hoi4://docs/quickstart` 资源**：
  - 对应 `docs/MCP_quickstart.md`，给出 `create_mod → 内容 → 本地化 → 校验` 的最小端到端示例。
- **新增 `create_mod_from_scratch` prompt**：
  - 返回从零建 mod 的完整步骤，并提示隐藏工具经 `invoke_tool` 调用。

## 6J. MCP 知识体系 / 校验器 / 模板（2026-08-31）

- **角色文档（同结构）**：
  - `docs/MCP用户指南.md`：使用者视角（分类/正确范式/踩坑/模板/工作流/校验器）；
  - `docs/MCP开发者指南.md`：开发者视角（注册/schema/handler/踩坑/模板/MCPVAL/工作流）；
  - 两份文档 TOC 结构一致，便于整合；开发时按身份写入对应文件。
- **全项目踩坑索引**：`docs/踩坑索引.md`，12 类别；开发前按类别读取。
- **校验器**：`src/mcp_validator.py`：
  - metadata：工具名/schema/description/生成器 examples/AI CRUD 必填/dry_run/create_mod approved；
  - call：缺必填/类型错/越界路径/未批准写操作；
  - `tools/check_mcp_contracts.py` 已并入 `tools/verify_contracts.py`；
  - MCP server 内置与官方 FastMCP 调用前自动拦截。
- **正确调用模板**：`templates/mcp/` 按分类保存 JSON 模板；
  `tests/test_mcp_templates.py` 保证 schema 校验 + handler 无异常。
- **工作流**：MCP `prompts/list|get` 新增 `mcp_workflow`（user/developer 两分支）；
  resources 新增 `hoi4://docs/user`、`hoi4://docs/developer`、`hoi4://docs/pitfalls`、
  `hoi4://templates/mcp`。

## 7. 验证

- `tests/test_infra.py`：`McpRegistrationTest`（工具数 ≥178、名称唯一、schema 合法、handler 可调）、`McpDomainSmokeTest`（州/AI/BOP/设计器/区域/生成器/OOB roundtrip 与 dry_run 不落盘）。
- `tests/test_mcp_smoke_real.py`：真实数据全量 178 工具默认冒烟（guarded，0 error）。
- `tests/test_mcp_validator.py`：MCP 校验器 metadata/call/server 拦截 12 例。
- `tests/test_mcp_templates.py`：`templates/mcp/` 正确调用模板 schema + handler 回归。
- `tools/check_mcp_contracts.py`：MCP 工具注册表 metadata 校验，已并入 `tools/verify_contracts.py`。
- `tools/verify_contracts.py`：语法编译、ruff、契约测试、写入纪律、四层依赖、MCP校验器、行数预算、UI 缺口探针全部通过。
- 工具清单与本文档不同步时，以 `src/mcp_tools.py::build_tools()` 为唯一权威。
