> 状态声明：本文档为 2026-08-19 前后的历史评估快照，其中「未做/只读」等描述不反映后续执行进度。进度与缺口以 docs/整合计划.md 批次总表为唯一事实源。

# UI 评分清单（当前全部界面）

> 建立：2026-08-19
> 用途：把当前程序**所有用户可见界面**列成一张待打分表。
> 你（用户）在「评分」列填 1~10 分（或 优/良/中/差）；之后用 Qwen3.7plus 对每项截图做图像识别，
> 汇总「优秀 UI 有哪些内容 / 低分 UI 缺什么」，再对照本表逐项修复。
> 列说明：ID=稳定编号；实现类型=专用编辑器/半专用/画布/通用树/工具；已知问题=来自 `UI评估报告.md` v2 的 🔴🟠🟡 摘要。

---

## A. 主框架 / 工作台

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 主窗口（菜单栏/文件树/工作台/画布装配） | `main_window.py` | 框架 | 无专门词条问题；工具菜单/路由集中 | 9 |  |
| A2 | 工作台（文件模式/无文件模式） | `workbench.py` + `content_types.py` + `entity_scanner.py` | 专用 | 类型列表已分组；无文件模式国家选择已修 | 8 |  |
| A3 | 通用 PDX 树形编辑器（兜底） | `generic_tree_editor.py` | 通用树 | 🔴 大量类型最终落到原始树/raw；作为兜底可接受，但不应是主入口 | 8 |  |
| A4 | 实体查找（Ctrl+F） | `entity_find_dialog.py` | 工具 | 无严重问题 |  |  |
| A5 | 首次使用配置向导 | `setup_wizard.py` | 工具 | 无严重问题 |  |  |
| A6 | 新建 Mod 项目 | `mod_creator_dialog.py` | 工具 | 无严重问题 |  |  |
| A7 | 国家设置（复制/创建） | `country_setup_dialog.py` | 半专用 | 已与纯选择分离（不误写） |  |  |
| A8 | 新建国策项目（联动生成） | `project_wizard.py` | 工具 | 无严重问题 |  |  |
| A9 | AI 设置 / AI 创作助手 | `ai_assist_dialog.py` + `ai_prompt_dialog.py` | 工具 | 外部接口；无词条问题 |  |  |
| A10 | 外部接口面板（HTTP/MCP） | `api_gui_dialog.py` | 工具 | 无严重问题 |  |  |

## B. 国策 / 科技画布

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 国策树画布 | `focus_view.py` + `focus_algo/render/ctrl` | 画布 | 已按四层拆分；节点词条经 NodeEditDialog | 9 |  |
| B2 | 科技树画布 | `tech_view.py`（同画布） | 画布 | 🔴 科技词条（name/desc/cost/前置）仍无专用表单，需树编辑 | 4 | 科技画图连线混乱，实体之间间隔太小，对于装备迭代类科技（大图标）与加成类科技（小图标）的区分并不好 |
| B3 | 实体画廊 | `focus_view_ctrl.py` EntityGalleryControllerMixin | 画布 | 无严重问题 |  |  |
| B4 | 国策顺序点选 | `focus_order_picker.py` | 专用 | 无严重问题（黑框红底角标/右键调整） |  |  |
| B5 | 树基本信息编辑 | `tree_info_dialog.py` | 半专用 | 表单+树头混合 |  |  |
| B6 | 图标选择 / 上传 | `icon_picker_dialog.py` + `icon_upload_dialog.py` + `tech_icon_ops.py` | 工具 | 无严重问题 |  |  |
| B7 | 节点编辑 / 词条 / 模板 / 自定义语句 | `node_edit_dialog.py` + `node_search_dialog.py` + `template_dialog.py` + `custom_statement_dialog.py` + `term_dialog.py` | 半专用 | 🔴 其「高级: 直接编辑」原始 PDX 保留为兜底（批 F 再隐藏） |  |  |

## C. 专用编辑器

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | 师编制编辑器 v2 | `division_editor.py` + `oob_loader.py` + `oob_format.py` | 专用 | 🟠 营名称/组名/description、division_names_group 未字段化（批 E） | 6 | 对于地形仅单一展示了地形加成，但地形加成有三项，移动，攻击，防御 |
| C2 | 舰艇设计器 | `ship_design_dialog.py` + `ship_design.py` | 专用 | 🟠 变体 description/自定义 stats 未结构化（批 E） | 5 | 本地化未完全，界面设计缺少对称性，文字与槽位间隔过大，修改意见是统一将文字放置在槽位下，删除间隔。同时对于某些槽位的锁定我无法理解。对于船体无法让用户进行选择 |
| C3 | 飞机设计器 | `plane_design_dialog.py` + `plane_design.py` | 专用 | 🟠 同上 | 2 | 界面问题与舰艇类似，未完全的本地化，槽位安排错误，槽位数量不对。对于同种飞机（名字相同但不在对应国家名字中）在不同的空军设计器中无法编辑。对于飞机机体无法让用户选择 |
| C4 | 坦克设计器 | `tank_design_dialog.py` + `tank_design.py` | 专用 | 🟠 同上 | 2 | 同飞机设计器，槽位位置不对，本地化不完全，无法选择底盘 |
| C5 | 模块选择器 | `designer_common.py` ModulePickerDialog | 专用 | 无严重问题 |  |  |
| C6 | OOB 地图放置 | `oob_map_editor.py` | 专用 | 复用 MapCanvas；兵牌/国家标签 | 7 | 对于默认视图，没有定位到所选国家，没有放大到对应国家 |
| C7 | 力量平衡工作台 | `bop_editor_dialog.py` + `bop_loader.py` | 专用 | 🟠 区间修正名/值可看不可改；势力/动作经树编辑（批 D） | 4 | 仅有展示，无法添加删除决议，对于编辑相关数值，依旧是在树形编辑器 |
| C8 | 角色编辑器（单页三栏） | `character_editor_dialog.py` + `character_data.py` | 专用 | ✅ 批 A 已修：roles/描述/肖像槽位结构化 | 4 | 未展示角色肖像，未展示角色本地化，在角色工作台无法被正确调用，图片上传功能应该向国策部分学习，对于desc键，不知道是关联错误还是本就不存在，所有角色均无desc键 |
| C9 | 顾问分配编辑 | `advisor_assign_dialog.py` | 半专用 | 🔴 traits/available 仍 raw；idea_token/slot/name/desc 未全字段化（批 D） |  |  |

## D. AI 内容编辑器（固定侧边栏专用 UI）

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | AI 战略计划编辑器 | `ai_plan_editor_dialog.py` | 专用 | 🟠 desc/focus_order 用 raw；有 focus_order_picker 未接（批 D） |  |  |
| D2 | AI 战略倾向编辑器 | `ai_strategy_editor_dialog.py` | 专用 | 键值表；高级块 raw 兜底 |  |  |
| D3 | AI 师模板编辑器 | `ai_template_editor_dialog.py` | 专用 | 目标编制接 DivisionEditor；高级块 raw |  |  |
| D4 | AI 装备编辑器 | `ai_equipment_editor_dialog.py` | 专用 | 模块/变体高级块 raw 兜底 |  |  |
| D5 | AI 海军编辑器 | `ai_navy_editor_dialog.py` | 专用 | 三页签；复杂块树编辑/raw |  |  |
| D6 | AI 派系战区编辑器 | `ai_faction_theater_editor_dialog.py` | 专用 | 高级块 raw 兜底 |  |  |
| D7 | AI 区域编辑器 | `ai_area_editor_dialog.py` | 专用 | 高级块 raw 兜底 |  |  |
| D8 | AI 科研权重编辑器 | `ai_focus_editor_dialog.py` | 专用 | 键值表；高级块 raw |  |  |
| D9 | 高级脚本块编辑器 | `ai_ui_common.py` ScriptBlockEditorDialog | 半专用 | 🔴 未建模块一律丢「原始 PDX」（批 D 先键值/列表结构化，raw 末项） |  |  |
| D10 | 固定侧边栏/键值表组件 | `ai_ui_common.py` EntityListSidebar / KeyValueTableEditor | 组件 | 无横向滚动；本身非独立窗口 |  |  |

## E. 地图

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | 地图编辑器（三栏） | `map_editor_dialog.py` + `map_canvas.py` | 专用 | 🔴 resources/victory_points/manpower/州名 只读不可编辑（批 B） |  |  |
| E2 | 区域编辑器（框选划分） | `region_editor_dialog.py` + `map_region_ops.py` | 专用 | 支持 strategicregions/supplyareas/states；无已知词条缺失 |  |  |
| E3 | 地图画布组件（内部） | `map_canvas.py` | 组件 | 悬停/选中/州轮廓/瓦片缓存；非独立窗口 |  |  |

## F. 本地化 / 资源

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | 本地化编辑器 | `localisation_editor_dialog.py` + `localisation_editor_data.py` | 专用 | 全量词条浏览/搜索/新增/编辑/删除/补写/多语言 |  |  |
| F2 | 快速本地化编辑 | `quick_localisation_edit.py` + `quick_loc_menu.py` | 专用 | 各编辑器右键快速小窗 |  |  |
| F3 | 实体配套资源工作台 | `entity_resource_dialog.py` + `entity_resource_data.py` | 专用 | 表格批量中文/英文/图标/光效 |  |  |
| F4 | 游戏数据参考·国家 | `reference_panel.py` | 工具 | 浏览 tag/中文名/意识形态/复制 |  |  |

## G. 检查 / 工具 / 生成

| ID | 界面名称 | 入口 / 模块 | 实现类型 | 已知问题 / 说明 | 评分(1-10) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | 导出前健康检查 | `health_check_dialog.py` + `export_health.py` | 工具 | 8 类检查 |  |  |
| G2 | 覆盖规则与增量报告 | `overlay_report_dialog.py` + `overlay_rules.py` | 工具 | 规则链+增量报告 |  |  |
| G3 | 图标库 manifest | `icon_manifest_dialog.py` | 工具 | 表格/搜索/导出 |  |  |
| G4 | 单位标牌库 | `unit_counter_library_dialog.py` | 工具 | 搜索/类别过滤/双击复制 |  |  |
| G5 | 文件类型覆盖检查报告 | `coverage_report.py` | 工具 | 应用内查看+复制 Markdown |  |  |
| G6 | 模板管理 | `template_manager_dialog.py` | 工具 | 模板增删改/搜索 |  |  |
| G7 | 独立工具对话框（格式化/DDS/VP本地化/错误日志） | `standalone_tool_dialogs.py` | 工具 | 选择路径→运行→结果表 |  |  |
| G8 | 词条管理 / 自定义语句 | `term_dialog.py` + `custom_statement_dialog.py` | 工具 | 词条库（QIUQI 优先） |  |  |
| G9 | 内容生成器工作台 | `content_generator_dialog.py` + `*_gen.py` | 专用 | country/ideas/ideology/character/general/focus 生成 |  |  |
| G10 | 唯一 ID 扫描（CLI，无 UI） | `tools/unique_id_scanner.py` | CLI | 暂无界面；如需可加报告对话框 |  |  |

---

## 待补界面（尚未做成独立 UI，但用户会遇到的入口）

| ID | 名称 | 现状 | 说明 |
| --- | --- | --- | --- |
| H1 | 事件 / 超事件专用编辑器 | 无专用 UI，走通用树 | 🔴 批 C：title/desc/picture/option 需要专用表单 |
| H2 | 科技专用编辑器 | 无专用 UI，走通用树 | 🔴 批 C：name/desc/图片/成本/前置 |
| H3 | 决议 / 民族精神 / 意识形态等其余通用类型 | 无专用 UI，走通用树 | 🟠 批 F 长期逐个补专用/结构化 |
