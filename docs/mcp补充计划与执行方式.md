# MCP 补充计划与执行方式

> 目标：让 MCP（外置 Agent 接口）覆盖本项目**全部功能**。
> 本文是完整的设计与执行文档：现状盘点 → 差距分析 → 142 个新增工具全清单（含数据层挂载点）→
> 架构与执行方式 → 测试与验证方案。后续任何代理可按本文直接开工，无需重新调研。
>
> 立项：2026-08-22。用户已拍板三项决策：
> ① **全部细分粒度**（每个操作独立工具，接受工具列表庞大）；
> ② **高危批量操作纳入 + 默认 dry_run**（批量/结构操作只返回预览，显式传 `dry_run=false` 才落盘）；
> ③ **一次性全部实现**（本文"执行步骤"为单轮内部顺序，非分批交付）。

---

## 1. 现状盘点（2026-08-22 核实）

### 1.1 架构事实

- **ApiCore**（`src/api_server.py`，约 887 行）：HTTP / MCP / CLI 共用核心，dict 进 dict 出。
  AGENTS §3.3 硬性规定：**必须共用 ApiCore，禁止另起实现**。
- **MCP**（`src/mcp_server.py`，373 行）：`build_tools(core)` 返回工具列表；优先官方 `mcp` 库
  （FastMCP），未安装回退内置零依赖实现（`BuiltinMcpServer`，newline-delimited JSON-RPC 2.0，
  协议版本 2024-11-05，支持 initialize / notifications/initialized / ping / tools/list / tools/call）。
  **两种实现消费同一个 build_tools 列表——一处注册两端生效。**
- **HTTP**（`api_server.py` 内 `_ApiHTTPServer` / `ApiHandler`）：仅绑 127.0.0.1，Bearer token 鉴权，
  `POST`/`GET`/`PUT`/`DELETE` 全 JSON；错误映射 ValueError→400 / 其他→500。
  GUI 内嵌模式（工具菜单「外部接口…」→ `api_gui_dialog.ApiDialog`）写操作后经
  `core.on_change` 回调刷新界面；独立进程模式无回调。
- ⚠️ `api_server.py` 顶部模块 docstring 的端点清单已过期（缺 /api/files、/api/tech_icon 等），
  以 `ApiCore.help()` 为准——本次一并修正。
- ⚠️ docstring 声称"写操作自动进入撤销管理器"，实际未接入 undo_mgr（原子写内部有撤销快照，
  ApiCore 层无显式接入）——本次 `undo_last_write` 工具直接调 undo_mgr 单例即可，无需改写路径。

### 1.2 现有 17 个 MCP 工具

`get_status` / `list_types` / `list_entities` / `get_entity` / `create_entity` / `update_entity` /
`delete_entity` / `create_focus_project` / `write_localisation` / `validate_mod` /
`list_templates` / `list_files` / `read_file` / `write_file` / `upload_tech_icon` /
`get_icon_manifest` / `get_overlay_report`

### 1.3 存量缺口（ApiCore/HTTP 已有、MCP 未注册，直接补挂）

| 工具名 | ApiCore 方法（已存在） | 数据层 | 测试已覆盖 |
| --- | --- | --- | --- |
| `format_pdx` | `format_pdx` | `pdx_format.format_paths` | ApiCoreToolTest |
| `vp_loc_dry_run` | `vp_loc_dry_run` | `vp_loc` | ApiCoreToolTest |
| `analyze_error_log` | `analyze_error_log` | `error_log.analyze` | ApiCoreToolTest |
| `register_icon_batch` | `register_icon_batch` | `icon_batch.register_missing_gfx` | ApiCoreToolTest |

（`help` 不做：MCP 工具描述自带元信息。）

### 1.4 数据层依赖等级（headless 可行性，已逐一核实）

**纯 Python 无 PyQt6（36 个，可直接封装）**：
`ai_loader` `bop_loader` `ship_design` `plane_design` `tank_design` `state_loader` `state_edit_ops`
`state_build_ops` `building_lib` `map_region_ops` `export_health` `validation` `oob_loader`
`design_template` `overlay_rules` `icon_manifest` `icon_batch` `pdx_format` `vp_loc` `error_log`
`dds_convert` `state_batch` `pdx_sorter` `interface_reg` `event_gen` `idea_gen` `ideology_gen`
`character_gen` `general_gen` `country_boot` `focus_package_gen` `qiqi_term_import`
`term_registry` `localization_mgr` `unique_id_scanner` `coverage_report` `game_data`

**需注意**：
- `map_loader.py` 第 14 行 `from PyQt6.QtGui import QImage, QPixmap, QColor`（渲染用）——
  **地图域工具只用 `StateData` + definition.csv 轻量解析，绝不触碰位图/渲染路径**
  （省份→州映射来自 states 文件，省份类型/地形来自 definition.csv，与 provinces.bmp 无关）。
- `icon_ops.py` 可能 import QtGui——`upload_entity_icon` 优先参照
  `tech_icon_ops.upload_tech_icon_base64`（已被现有 API 证明 headless 可行）的 base64 路径模式；
  实现时验证，若受阻则在 `api_core_ext/media.py` 内做纯函数版（PIL 缩放 + `icon_ops` 的
  sprite 注册逻辑复用）。

---

## 2. 差距分析（GUI/数据层有、MCP 没有）

| # | 功能域 | GUI / 数据层现状 | MCP 现状 |
| --- | --- | --- | --- |
| 0 | 存量 ApiCore 方法 | §1.3 四个（已有 HTTP 端点+测试） | ❌ 全缺 |
| 1 | 州/建筑/区域/归属 | StateData 查询 + state_edit_ops / state_build_ops / map_region_ops / state_batch / pdx_sorter 写回（= 地编三栏全部能力） | ❌ 完全没有 |
| 2 | 三军设计器 | ship/plane/tank_design：load / stats / insert / remove / rename / apply_variant_* + 跨国同步 + design_template | ❌ 完全没有 |
| 3 | 师编制 / OOB | oob_loader：parse_division_templates / load_sub_units / load_equipment_stats / division_stats / detect_oob_kinds | ❌ 完全没有 |
| 4 | AI 内容 8 类 | ai_loader 约 50 个 CRUD/写回函数（计划/倾向/师模板/装备/海军/区域/科研/战区） | ❌ 完全没有 |
| 5 | 力量平衡 BOP | bop_loader 查询 + 对话框内保存逻辑（需下沉为纯函数） | ❌ 完全没有 |
| 6 | 本地化读取/批量补写/词条库 | localization_mgr 解析、validation.fix_localisation_missing、term_registry（QIUQI 1887 词条 + 用户词条 CRUD） | ❌ 只能写不能读 |
| 7 | 校验/健康/撤销/覆盖 | export_health 8 类、unique_id_scanner、undo_mgr、coverage_report | ❌ 只有 4 类 validate |
| 8 | 图标/媒体 | icon_ops.upload_icon（任意实体）、dds_convert、unit_counter_library | ❌ 只有科技图标 |
| 9 | 内容生成器 7 种 | idea/ideology/character/general/country_boot/focus_package/event `_gen` 纯函数 | ❌ 完全没有 |
| 10 | 项目级 | 国家接管三操作（country_setup_dialog 模块级纯函数）、ModCreatorDialog（需下沉）、模板应用+变量替换 | ❌ 完全没有 |

### 2.1 明确不做（及理由）

- **画布交互**（国策/科技树拖拽、focus_order_picker 点选、地图涂色/框选）：GUI 交互语义；
  文件级/实体级 CRUD + 工具参数（如 `set_ai_plan_focus_order` 传国策 id 列表）已等价覆盖。
- **map_loader 位图渲染**（底图/地形/hillshade/矢量边界）：QImage/QPixmap 依赖，且对
  外置 Agent 无意义；省/州数据查询由域 1 工具覆盖。
- **ai_assist.chat**（OpenAI 兼容直连）：外置 Agent 自身是 LLM，转发无意义。
- **overlay_rules / icon_manifest / validate / templates 列表**：已有工具，不重复。
- **coverage_report UI 部分 / 对话框类能力**（ScriptBlockEditorDialog、quick_loc 右键等）：
  对话框是 GUI 壳，其数据操作已由对应域工具覆盖。

---

## 3. 新增工具全清单（142 个，按域）

> 命名约定：全部域前缀 + 动词（`set_state_building`、`list_ship_designs`、`ai_plan_create`…），
> description 首词为域词，便于外置 Agent 检索。写操作默认直接执行；标注 **[dry_run]** 的
> 默认 `dry_run=true` 只返回预览（将写入的文件清单 + 内容摘要），显式传 `false` 落盘。

### 域 0：存量补齐（4 个，零新逻辑）

| 工具 | 参数 | 说明 |
| --- | --- | --- |
| `format_pdx` | path, whitespace?, ignore_comments? | PDX 文件格式化写回 |
| `vp_loc_dry_run` | 无 | VP 本地化干跑预览（不写文件） |
| `analyze_error_log` | path 或 absolute_path | 游戏错误日志分析 + 子系统归类 |
| `register_icon_batch` | path, type? | 批量补注册文件内缺失图标 GFX |

### 域 1：州 / 建筑 / 区域（16 个）

| 工具 | 参数 | 挂载函数（已存在） |
| --- | --- | --- |
| `list_states` | owner?, keyword? | `StateData`（id/名/owner/省份数/类别/人力） |
| `get_state` | state_id | `StateData`（建筑/buildings_pid/VP/类别/省份列表/src） |
| `get_province` | province_id | `StateData.state_of_province` + definition.csv 轻量解析（类型/地形/沿海） |
| `get_owner_provinces` | tag? | `StateData.owner_province_map()`（tag→pids；无 tag 返回全部 owner 表） |
| `set_state_owner` | state_id, tag | `state_edit_ops.set_state_owner`（块级替换，只写 mod） |
| `set_state_building` | state_id, building, level, province_id? | `state_build_ops.set_state_building`（省/州级；level<=0 移除） |
| `set_state_category` | state_id, category | `state_build_ops.set_state_category` |
| `set_country_color` | tag, r, g, b | `state_build_ops.set_country_color`（0-255） |
| `list_building_types` | 无 | `building_lib.load_building_types`（59 项：可建造/图标帧/中文名/state_modifiers） |
| `list_country_colors` | 无 | `building_lib.load_country_colors`（694 项） |
| `batch_set_state_fields` **[dry_run]** | state_ids[], field, value | `state_batch.batch_write` / `set_field_for_states` |
| `sort_state_file` | path | `pdx_sorter.sort_state_file`（按 id 排序） |
| `list_regions` | kind=strategic\|supply（缺省两者） | `map_region_ops.scan_region_files`（含每区域省份） |
| `create_region` | kind, region_id?, province_ids[] | `append_region` + `next_region_id`（id 缺省自动） |
| `set_region_provinces` | kind, region_id, province_ids[] | `set_region_provinces`（整块替换） |
| `remove_region` | kind, region_id | `remove_region` |

写回统一经 `ensure_file_in_mod`（原版自动复制到 mod）+ 原子写；写后 `StateData.reload()`。

### 域 2：三军设计器 + 设计模板（30 个）

三军结构同构但函数独立，前缀区分（ship / plane / tank）。每军 9 个：

| 工具（以 ship 为例，plane/tank 同名替换） | 挂载函数 |
| --- | --- |
| `list_ship_hulls`（含 archetype/变体/槽位表） | `load_ship_hulls` |
| `list_ship_modules`（含 add/multiply stats 与 category） | `load_ship_modules` |
| `list_ship_designs`（country? 过滤） | `load_ship_variants` |
| `get_ship_design`（name + country；含槽位占用 + `ship_design_stats` 属性估算） | `load_ship_variants` + `ship_design_stats` |
| `create_ship_design`（country, name, hull, upgrades{}） | `insert_variant` |
| `update_ship_design`（country, name, upgrades{}） | `apply_variant_upgrades` |
| `rename_ship_design`（country, old, new） | `rename_variant` |
| `delete_ship_design`（country, name） | `remove_variant` |
| `sync_ship_design` **[dry_run]**（name；同步到所有同名设计国家） | 各国循环 `apply_variant_upgrades`（同款同步，参考 ship_design_dialog「🔄 同步到所有同款」） |

- plane 用 `load_plane_airframes` / `load_plane_modules` / `load_plane_variants` /
  `plane_design_stats` / `apply_variant_modules`；tank 用 `load_tank_chassis` / `load_tank_modules` /
  `load_tank_variants` / `tank_design_stats`，写回**复用 `plane_design.apply_variant_modules` 等**（已验证逻辑一致）。
- 变体解析统一 `parse_equipment_variants`（字符级 `_block_ranges`，大国家文件安全）。
- 保存目标：`_save_path` 模式（mod 优先，否则 `ensure_file_in_mod` 复制原版——**绝不直写游戏本体**）。
- 设计模板 3 个：`list_design_templates` / `save_design_template` / `load_design_template`
  （`design_template.py`；load 只返回内容不直接写 mod）。

### 域 3：师编制 / OOB（8 个）

| 工具 | 挂载函数 |
| --- | --- |
| `list_oob_files`（mod+game history/units；每文件含 `detect_oob_kinds` 军种识别） | `oob_loader` 目录扫描 + `detect_oob_kinds` |
| `list_division_templates`（path? 缺省全部 OOB；含 `division_stats`） | `parse_division_templates` + `division_stats` |
| `get_division_template`（path, name；完整 PDX + 统计） | 同上 |
| `create_division_template`（path, name, units{}?, support{}?） | DivisionTemplate 构造 + `to_pdx()` 插入 |
| `update_division_template`（path, name, content 或 units/support） | 块级替换（同 parse/serialize roundtrip） |
| `delete_division_template`（path, name） | 块级删除 |
| `list_sub_units`（keyword?；营+属性+need+terrain） | `load_sub_units` |
| `search_equipment`（keyword?, category?；354 项统计） | `load_equipment_stats` |

### 域 4：AI 内容 8 类（49 个）

8 类：`plan`（战略计划）/ `strategy`（战略倾向）/ `ai_template`（师模板）/ `equipment`（装备）/
`navy`（海军）/ `area`（区域）/ `focus`（科研权重）/ `theater`（派系战区）。
统一命名 `ai_<类>_<动作>`（`ai_template` 避免与设计器模板混淆）：

| 动作 | 语义 | 挂载函数模式（以 plan 为例） |
| --- | --- | --- |
| `ai_plan_list` | 列出（含名称/描述摘要） | `load_ai_plans(mod, game)` |
| `ai_plan_create` | 新建（骨架或自定义块） | `insert_ai_plan(content, plan_id, name, desc)` |
| `ai_plan_update` | 更新（块内容或字段） | `replace_top_block_child` / `replace_ai_plan_field` |
| `ai_plan_delete` | 删除 | `delete_ai_plan(content, plan_id)` |
| `ai_plan_rename` | 重命名 | `rename_ai_plan(content, old, new)` |
| `ai_plan_duplicate` | 复制 | `duplicate_ai_plan(content, plan_id, new_id)` |

- 其余 7 类同构：`insert/delete/rename/duplicate_ai_{strategy_group|template_role|equipment|navy|area|focus|faction_theater}`
  + 各自 `load_ai_*` + 字段写回（如 `replace_ai_area_regions`、`ai_template` 的 target_template、
  `ai_equipment` 的 target_variant modules）。
- 计划类专属第 7 个：`set_ai_plan_focus_order`（plan_id, ordered_focus_ids[]）→
  `replace_ai_plan_focus_order`（等价 focus_order_picker 的点选结果）。
- 8 类 × 6 + 1 = **49** 个。全部 `ensure_file_in_mod` + 原子写 + 写后清 `ai_loader` 模块缓存。

### 域 5：BOP（4 个）

| 工具 | 挂载 |
| --- | --- |
| `list_bop` | `load_bop_definitions`（名称/势力/区间概览，含中文名） |
| `get_bop`（bop_id；含 actions/ranges/sides/modifiers/当前区间） | `load_bop_definitions` + `load_bop_actions` + `find_active_range` |
| `set_bop_initial_value`（bop_id, value） | **下沉**：bop_editor_dialog 保存逻辑 → `bop_loader.set_bop_initial_value` |
| `set_bop_fields`（bop_id, left_side?, right_side?, decision_category?） | **下沉**：同上，`bop_loader.set_bop_fields` |

### 域 6：本地化 / 词条（8 个）

| 工具 | 挂载 |
| --- | --- |
| `search_localisation`（key 或 keyword, language=chi 缺省；mod 优先回退原版） | `localization_mgr.parse_loc_yml_file` / `load_loc_yml_dir`（utf-8-sig） |
| `list_missing_localisation` | `validation.check_localisation_coverage` |
| `batch_fill_localisation` **[dry_run]**（entries 或自动骨架） | `validation.fix_localisation_missing` |
| `search_terms`（keyword?, node_type?, tag?；QIUQI 1887 词条） | `term_registry.get_term_registry().search` |
| `get_term`（key） | `TermRegistry.get / get_cn / get_tags` |
| `add_user_term` / `update_user_term` / `remove_user_term` | `add_user_term` / `update_user_term` / `remove_user_term` |

### 域 7：校验 / 健康 / 撤销 / 覆盖（5 个）

| 工具 | 挂载 |
| --- | --- |
| `health_check`（8 类：descriptor/编码/括号/gfx 贴图/国策引用/本地化/重复 id/科技图标 sprite） | `export_health.run_export_health_check(mod, game, max_issues?)` |
| `scan_duplicate_ids`（types? 缺省 focus/event/dynamic_modifier/decision/character） | `unique_id_scanner.scan_duplicates` |
| `undo_last_write` | `undo_mgr.get_undo_manager().undo()` |
| `get_undo_status` | `can_undo()` + 最近快照信息（文件/时间） |
| `coverage_report`（各类型打开方式/模板/文件数） | `coverage_report.build_coverage_rows` |

### 域 8：图标 / 媒体（4 个）

| 工具 | 挂载 |
| --- | --- |
| `upload_entity_icon`（type, id, image_base64, slot?；写 png + gfx sprite + 实体 icon 字段） | `icon_ops.upload_icon`（Qt 依赖受阻则按 `tech_icon_ops.upload_tech_icon_base64` 模式做纯函数版） |
| `convert_dds`（path, direction=dds2png\|png2dds，recursive?） | `dds_convert.convert_dir` / `dds_to_png` / `png_to_dds` |
| `import_unit_counters` **[dry_run]**（从游戏 `counters/*/onmap_*.dds` 导入 PNG+manifest） | `unit_counter_library.import_unit_counter_library` |
| `list_unit_counters`（keyword?, category?） | `UnitCounterLibrary` 查询 |

### 域 9：内容生成器（7 个，全部 [dry_run] 默认 true）

统一参数：结构化入参 + `dry_run`；预览返回 `{files: [{path, content}]}`；落盘走原子写。
`generate_ideas`（`idea_gen.generate_ideas`）/ `generate_ideologies`（`ideology_gen`）/
`generate_characters`（`character_gen`）/ `generate_generals`（`general_gen.generate_leader_blocks`）/
`generate_country_bootstrap`（`country_boot.generate_country_bootstrap` 批量建国）/
`generate_focus_package`（`focus_package_gen.generate_package`：树+loc+图标 gfx 三件套）/
`generate_event`（`event_gen.generate_event` + namespace 块）。

### 域 10：项目级（7 个）

| 工具 | 挂载 |
| --- | --- |
| `list_countries`（tag/中文名/[mod 已接管]） | `game_data.load_game_countries` + `country_setup_dialog.scan_mod_countries` |
| `copy_country_files` **[dry_run]**（tag；复制原版国家文件到 mod） | `copy_country_files(game, mod, tag, dirs)` |
| `create_blank_overrides` **[dry_run]**（tag；空覆盖接管） | `create_blank_overrides(mod, tag, dirs, game)` |
| `create_new_country_files` **[dry_run]**（tag, name；全新国家） | `create_new_country_files(mod, tag, dirs, game)` |
| `create_mod` **[dry_run]**（name, path, tag?；.mod/descriptor/GFX/本地化骨架） | **下沉**：ModCreatorDialog 生成逻辑 → 新建 `src/mod_creator.py` 纯函数 |
| `apply_template`（template_name, target_path, variables{}） | `template_scheduler.apply_template` + `apply_template_variables` |
| `get_template`（template_name） | `template_scheduler.search_templates` + 读内容 |

**合计：4 + 16 + 30 + 8 + 49 + 4 + 8 + 5 + 4 + 7 + 7 = 142 新增；加现有 17 = 159 个。**

---

## 4. 架构与执行方式

### 4.1 代码结构（最小侵入 + 遵守四层分离 §4.9）

```
src/api_core_ext/            # 新包：ApiCore 扩展 mixin，按域一文件（算法/编排层，禁 import QtWidgets）
  __init__.py                #   导出全部 Mixin
  states.py      # StatesMixin      域 1
  designers.py   # DesignersMixin   域 2 + 3
  ai_content.py  # AiContentMixin   域 4
  bop.py         # BopMixin         域 5（含保存逻辑下沉）
  loc_tools.py   # LocToolsMixin    域 6
  health.py      # HealthMixin      域 7
  media.py       # MediaMixin       域 8
  generators.py  # GeneratorsMixin  域 9
  project.py     # ProjectMixin     域 10（含 mod_creator 下沉调用）
src/mod_creator.py           # 新：ModCreatorDialog 骨架生成下沉为纯函数（对话框改为调用它，行为不变）
src/mcp_tools.py             # 新：按域提供 *_tools(core) 列表构建函数；mcp_server.build_tools 汇总
```

- `api_server.py` 中 `class ApiCore(StatesMixin, DesignersMixin, AiContentMixin, BopMixin,
  LocToolsMixin, HealthMixin, MediaMixin, GeneratorsMixin, ProjectMixin):`——
  **现有 17 工具对应方法原地不动，零回归风险**；mixin 只新增方法。
- mixin 方法统一约定：dict 进 dict 出；**lazy import** 数据层（保持启动轻）；
  写操作完成后 `self._notify_change(path)` + 清缓存（`StateData.reload()` /
  `bop_loader._clear_cache()` / ai_loader 与设计器模块级缓存清理）；
  错误一律抛 ValueError（HTTP 自动 400，MCP 回传错误文本）。
- `src/mcp_tools.py`：每域一个构建函数（`_states_tools(core)` 返回 `_tool(...)` 列表），
  现有 17 条目从 `mcp_server.build_tools` 迁入并**保持工具名不变**；
  `build_tools(core)` = 各域汇总。工具 description 中文一句话 + 每参数 description
  （外置 Agent 依赖描述选工具，这是质量关键）。
- HTTP parity：`ApiHandler._route` 加域分派辅助（`/api/states*`、`/api/designs/<kind>/*`、
  `/api/divisions*`、`/api/ai/<kind>/*`、`/api/bop*`、`/api/loc/*`、`/api/health*`、
  `/api/media/*`、`/api/generators/<type>`、`/api/project/*`），与 MCP 完全同源 ApiCore。
  同时修正 `api_server.py` docstring 端点清单。

### 4.2 dry_run 与安全约定

- **[dry_run] 工具**（§3 标注的批量/结构操作）：默认 `dry_run=true` 返回
  `{dry_run: true, files: [{path, summary/content}], ...}`；显式 `false` 才落盘。
- 单点写操作直接执行；全部经已有数据层（内部即 `write_utils.atomic_write_text` +
  撤销快照，天然满足写入纪律 §4.1——mixin 自身**不出现任何 `open(path,'w')`**，
  写入纪律 AST 扫描自动通过）。
- 游戏本体文件一律先 `ensure_file_in_mod` 复制到 mod 再写（三军设计器/BOP/AI/州写回
  已有现成模式）；本地化 yml 走 `utf-8-sig`（§4.2 编码例外）。
- 沿用 127.0.0.1 + Bearer token，不放宽。

### 4.3 执行步骤（单轮内部顺序）

1. **逻辑下沉**（2 处，先做、独立可测）：
   a. `bop_editor_dialog` 保存逻辑 → `bop_loader.set_bop_initial_value / set_bop_fields`
      （纯函数：定位文件→ `ensure_file_in_mod` → 块内字段替换 → 原子写；对话框改为调用）；
   b. `ModCreatorDialog` 骨架生成 → `src/mod_creator.py`（.mod/descriptor/GFX/本地化骨架，
      返回将写文件清单，支持 dry_run；对话框改为调用，现有行为不变）。
2. **`src/api_core_ext/` 包**：9 个 mixin 按域实现（挂载数据层 + 缓存清理 + `_notify_change`）。
3. **`api_server.py`**：ApiCore 组合 mixin + `_route` 域分派 + docstring 修正。
4. **`src/mcp_tools.py` + `mcp_server.py`**：注册全部 159 工具（域构建函数 + 汇总）。
5. **测试**：见 §5。
6. **文档**：`docs/接口复现报告.md` 增补本批端点；本文标记状态为已实现；
   AGENTS.md §3.3（api_server/mcp_server 行）与 §6 增补本批记录；
   `mcp_server.py` docstring 配置示例核对。
7. **验证**：`python tools/verify_contracts.py` + `.venv\Scripts\python.exe tools/verify_contracts.py`
   双版本退出码 0；真实 mod（`E:\mods\3350890356`）headless 冒烟：抽样调 query 类工具
   （list_states / list_ship_designs / ai_plan_list / list_bop / search_terms）核对数量级，
   写类工具在临时复制目录上 roundtrip。

### 4.4 Python 3.14 兼容（§4.5）

已升级到 Python 3.14（Windows `.venv` 3.14.5 / WSL 3.14.4）；3.8 语法限制已解除。
旧代码保留的 `from __future__ import annotations` 不影响运行；`verify_contracts.py` 双版本把关。

---

## 5. 测试与验证方案（契约 §4.6）

`tests/test_contracts.py` 新增（模式参考 `ApiCoreToolTest`，tests/test_contracts.py:7067）：

1. **MCP 注册完整性**（关键回归网，一个测试类）：
   - `build_tools(core)` 工具数 ≥ 159；名称全局唯一；
   - 每个工具 schema 是合法 JSON Schema（type=object + properties）；
   - 每个工具 lambda 可调用（抽检全部：对 query 类工具逐个空参/缺省参调用不抛非 ValueError）；
   - 工具名 ↔ ApiCore 方法对应关系快照（防止注册与实现脱节）。
2. **每域功能测试类**（约 14 个，各含 3~6 用例）：
   - 查询冒烟：临时 mod 夹具（或真实 3350890356 冒烟脚本）上调 list/get 断言数量与关键字段；
   - 写 roundtrip：临时目录上 create → get 校验 → delete 还原（或快照对比）；
   - dry_run 断言：目录字节级快照在 dry_run 调用后不变；
   - ensure_file_in_mod 断言：mod 无目标文件时写后游戏本体字节不变（参考
     `test_save_original_copies_to_mod` 模式）。
3. **HTTP parity 冒烟**：新域端点各抽 1 条路由调用（ApiServer 起在随机端口 + token）。
4. **下沉函数回归**：`bop_loader.set_bop_initial_value` / `mod_creator` 纯函数 roundtrip +
   原对话框现有契约测试保持全绿（锁定行为不变）。

预计新增 15~16 个测试类 / 60+ 用例；完成后全量 `verify_contracts.py`（语法编译 /
契约测试 / 写入纪律扫描 / 四层依赖检查）双版本退出码 0。

---

## 6. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 工具总数 159，外置 Agent 选择混淆 | 域前缀命名 + description 首词域词 + tools/list 按域排序；用户已确认接受 |
| `icon_ops` Qt 依赖阻碍 headless | 参照 `tech_icon_ops.upload_tech_icon_base64` 已验证模式；必要时 media.py 内纯函数版（PIL） |
| `map_loader` QImage 误引入 | 地图域只用 StateData + definition.csv；code review 时 grep `map_loader` 不得出现在 mixin import |
| api_server.py 膨胀 | 全部新逻辑进 `api_core_ext/` mixin；api_server.py 仅组合 + 路由 |
| mixin 写路径绕过原子写 | mixin 禁止直写（§4.2）；写入纪律 AST 扫描是门禁 |
| 大国家文件解析截断 | 变体/国家文件解析统一走字符级 `_block_ranges`（`parse_equipment_variants` / ai_loader 现有实现已满足） |
| 写后读到旧缓存 | 每个写方法末尾统一清对应缓存 + `_notify_change`（GUI 模式同时刷新界面） |

---

## 7. 状态

- [x] 已实施（2026-08-22 单轮完成）。159 个 MCP 工具已注册；ApiCore 已组合 9 个域 Mixin；
  HTTP 提供 `/api/mcp/<tool_name>` 同源桥；mod_creator 与 BOP 保存逻辑已下沉；契约测试新增
  MCP 注册完整性与域冒烟用例。
