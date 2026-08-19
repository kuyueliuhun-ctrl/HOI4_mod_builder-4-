# RHoiScribe 知识库吸收：映射与补全

> 来源：`E:\RHoiScribe/resources/knowledge/hoi4/**/*.toml`（RHoiScribe 内置 HOI4 知识，66 条）。
> 目的：把 RHoiScribe 的本地 HOI4 知识逐条映射到本项目 `docs/游戏文件内容详解.md` 对应章节，
> 并对现有文档**缺失的机制**给出精简补全（含真实语法示例）。
> 写 mod 内容仍须遵守项目写入纪律与四层分离。

---

## 一、逐条映射表（RHoiScribe 主题 → 本项目章节）

| RHoiScribe 主题 | 本项目 `游戏文件内容详解.md` 对应 | 覆盖状态 |
| --- | --- | --- |
| ai.ai_strategy | §15 AI 体系 / `ai_*_editor_dialog` | 已覆盖（编辑器） |
| bookmarks.start_dates | §13 剧本 | 已覆盖 |
| buildings.resources | §11 建筑/资源 + `building_lib` | 已覆盖 |
| characters.leaders_advisors | §8 角色 | 已覆盖（+角色专用UI） |
| characters.traits | §8 角色 | 部分覆盖 → 见补全 B |
| countries.cosmetic_tags | 未覆盖 | **补全 D** |
| countries.country_tags | §4.1 国家定义 | 已覆盖 |
| debug.common_errors | §18 编写规范/错误 + `tools/error_log_analyzer.py` | 已覆盖（增强见 §四） |
| decision.basic_category | §6.2 决议 | 已覆盖 |
| decision.mission_vs_decision_blocks | §6.2 决议 | 部分覆盖 → **补全 F** |
| decision.missions_timed | §6.2 决议 | **补全 F** |
| defines.game_constants | 待补（defines 章节） | **补全 E** |
| diplomacy.opinion_autonomy | §14 外交 | 部分 → **补全 C** |
| equipment.archetypes | §9.2 装备 + 设计器 | 已覆盖 |
| events.chains | §6.1 事件 | 部分 → **补全 G** |
| events.country_event | §6.1 事件 | 已覆盖 |
| events.news_event_mtth | §6.1 事件 | 部分 → **补全 G** |
| focus.basic_tree | §5 国策 | 已覆盖 |
| focus.shared_focus_filters | §5 国策 | **补全 H** |
| gui.experimental_asset_pipeline | `icon_batch` / 实体资源工作台 | 已覆盖 |
| gui.gfx_sprites | §17.2 GFX | 已覆盖 |
| history.countries / states / units_oob | §12 历史档 (+OOB) | 已覆盖 |
| ideas.country_ideas | §7 理念 | 已覆盖（生成器） |
| interface.assets_fonts | §17 界面 | 部分 |
| localisation.dynamic_text | §17.1 本地化 | 已覆盖 |
| localisation.encoding | §17.1 本地化 | 已覆盖 |
| map.adjacencies | §3/地图章节 | **补全 I** |
| map.provinces_terrain | 地图章节 | 已覆盖 |
| modifiers.dynamic_modifiers | §16.4 动态修正 | 已覆盖 |
| on_actions.*（8 个） | §16.3 触发动作（很薄） | **补全 A**（重点） |
| rules.game_rules | §16.6 | 已覆盖 |
| script.arrays | §1 脚本 | **补全 A-2** |
| script.effects/triggers/scopes/modifiers/variables/expressions/mtth | §1 脚本 | 已覆盖 |
| script.flags / unique_identifiers | 部分 | **补全 A-3** |
| scripted_gui.dynamic_lists | 未覆盖 | **补全 J** |
| scripted_localisation.entries | §16.2 脚本化本地化 | 已覆盖 |
| scripted_triggers.effects | §16.1 | 已覆盖 |
| sound.music | 未覆盖 | **补全 K** |
| structure.descriptor / mod_tree / replace_path_load_order | §2 Mod 工程结构 | 部分 → **补全 L** |
| technology.tech_trees | §9.1 科技 | 已覆盖 |
| units.division_templates / sub_units | §10 兵种/编制 | 已覆盖 |
| workflow.agent_delivery_rules / project_quality_tools / environment_discovery_debug_launch | §18 + `health_check` | 部分 → **补全 M** |

> A~M 为下方“补全小节”；标「已覆盖」的通常只在此表登记，不再展开。

> **回填入库（2026-08-19）**：A（§16.3 on_actions）、A-2（§18.4 数组）、A-3（§18.5 唯一标识）、
> D（§4.1 化妆标签）、F（§6.2 限时/任务决议）、G（§6.1 新闻事件，news_event）、
> I（§12.5 邻接/补给 + §12.3 战略区域/补给区域）、J（§17.4 脚本化 GUI）、K（§17.5 音乐音效）
> 已把要点+真实语法回填进 `docs/游戏文件内容详解.md` 对应章节；
> 另补 §15.9 逆向 AI 策略（吸收 QIUQI 教程）、§12.6 TNO Admin_Title 特殊案例摘要。
> 仍待补齐：E（defines 章节独立展开）、H（shared_focus_filters 详细）按需继续。

---

## 二、补全：机制要点（吸收自 RHoiScribe 知识库）

### A. 触发动作 on_actions（重点补全）

`common/on_actions/` 是一组“钩子”，在特定游戏事件时触发，每个钩子有**独立作用域**（THIS/ROOT/FROM 等不能给全局固定含义）。

**通用与脉冲钩子**（默认作用域=迭代对象）：
- `on_startup`：新游戏首日、选完国家后触发（读档不触发）；**默认无国家作用域**，需手动 `ENG = { ... }` 之类再写国家效果。
- `on_daily` / `on_weekly` / `on_monthly`：每天/周/月对**每个国家**各自执行，性能较高。
- `TAG` 变体（`on_daily_ENG` 等）：仅当该 tag 国家存在时执行。

```txt
on_startup = { effect = { ENG = { country_event = { id = my_mod.1 days = 365 } } } }
on_monthly = { random_events = { 1 = my_mod.10 99 = 0 } }
```

**政治/和平钩子**：`on_stage_coup / on_coup_succeeded / on_government_change / on_ruling_party_change / on_new_term_election / on_before_peace_conference_start / on_peaceconference_started / on_peaceconference_ended`。

**外交/战争钩子**：`on_declare_war / on_war / on_peace / on_capitulation(_immediate) / on_uncapitulation / on_annex / on_civil_war_end(_before_annexation) / on_puppet / on_liberate / on_release_as_free(_as_puppet) / on_guarantee / on_military_access / on_offer_military_access / on_call_allies / on_join_allies / on_lend_lease / on_incoming_lend_lease / on_send_expeditionary_force / on_return_expeditionary_forces / on_request_expeditionary_forces / on_ask_for_state_control / on_give_state_control / on_peace_proposal / on_send_attache / on_send_volunteers / on_border_war_lost / on_war_relation_added`。

**作用域注意**：
- `on_state_control_changed`：ROOT=新控制者，FROM=旧控制者，FROM.FROM=州。
- `on_naval_invasion / on_paradrop`：THIS ≠ ROOT。
- `random_events` 在脉冲钩子里会在钩子作用域内评估事件触发器。

**校验要求**：生成任何 OA 前写清 钩子名/类别/默认作用域/ROOT/FROM/PREV/OWNER；未知钩子不要臆造作用域（查当前游戏文档）；避免替换原版 on_actions 文件。

### A-2. 数组 / 数据结构（script.arrays）

数组存放作用域或值列表，常用于脚本化 GUI 动态列表与重复脚本操作，需明确**属主作用域与重置行为**：

```txt
clear_temp_array = temp_items
add_to_temp_array = { array = temp_items value = mtth:score_1 }
is_in_array = { array = ROOT.my_array value = THIS }
temp_items^index
```

校验：重建前先清临时数组；`dynamic_lists` 里定义索引/值名；区分数组值是作用域还是数字。

### A-3. 唯一标识符（script.unique_identifiers）

创建新 角色/旗标/TAG/理念 token/动态修正/国策/决议/事件命名空间/脚本化效果/触发器/Character 等**可复用标识符**前，应做结构化唯一性扫描（跨 mod + game 根）。
- **只把“创建意图”当作重复风险**；引用已有内容属信息性。
- 国策 ID 特殊处理：`focus = { id = ... }`、`shared_focus = { id = ... }`、`joint_focus = { id = ... }` 是**国策节点 ID**；`focus_tree = { id = ... }` 是**国策树 ID**，勿混淆。
- 旗标区分 `country_flag / global_flag / state_flag / character_flag / mio_flag / project_flag`（`unit_leader_flag` 归 legacy character 旗标族）。
- 生成的文件/目录/脚本标识符保持 **ASCII**；本地化文案是正常例外。
- `replace_path` 会隐藏原版文件夹，计划写入其下路径时应提示。

### B. 特质 traits（characters.traits）

领袖/顾问特质通常给修正或旗标；`traits = { <trait_id> }`。常见分类参考见本项目 `translations/qiqi_terms.json`（trait 词条，QIUQI 导入）。

### C. 外交/自治（diplomacy.opinion_autonomy）

涉及 好感度(`opinion`)、阵营(factions)、自治(autonomy)。见 §14.5 力量平衡、§14.6 派系；深度钩子见补全 A。

### D. 化妆标签（cosmetic_tags）

`common/country_tags` 之外的显示名覆盖可用 cosmetic tag（`TAG: "cosmetic_name"`），主要用于动态国名显示，本地化键对应显示名。

### E. defines（defines.game_constants）

`common/defines/00_defines.lua` 定义游戏全局常量；mod 可用 `common/defines/*.lua` 覆盖。字段直接改影响全游戏平衡，需谨慎。

### F. 限时决议/任务（decision.missions_timed / mission_vs_decision_blocks）

议决块 vs 任务块 vs 定向决议 vs 州目标块 语义不同。限时/任务决议有超时、取消、重复语义：

```txt
days_mission_timeout = 30
timeout_effect = { country_event = my_mod.4 }
cancel_trigger = { has_war = no }
```

校验：定义超时行为；避免可重复刷点漏洞；用旗标/变量做链状态；AI 行为控制重复使用。

### G. 事件链 / 新闻 / MTTH（events.chains / news_event_mtth）

事件链通过 `days = N`、`hidden_effect`、`option` 触发下一事件。MTTH（`*_mtth`）用于非确定性触发，含变量与动态脚本值。随机事件权重 `0` 表示“大多不触发”。

### H. 共享国策 / 过滤器 / AI（focus.shared_focus_filters）

```txt
search_filters = { FOCUS_FILTER_POLITICAL }
ai_will_do = { factor = 1 modifier = { factor = 0 has_war = yes } }
```

校验：不要生成 `ai factor = 0` 除非故意禁用；过滤器与奖励类型一致；不生成不可能的前置链。

### I. 邻接/战略区域/补给（map.adjacencies）

`adjacencies.csv`（邻接）、`strategicregions/*.txt`（战略区域，供空/海逻辑）、`supply_nodes.txt` / `railways.txt`（补给/铁路）。生成内容须交叉核对省 ID 与区域归属；州归属不能推断补给拓扑。

### J. 脚本化 GUI 动态列表（scripted_gui.dynamic_lists）

```txt
scripted_gui = { my_gui = { context_type = player_context window_name = "my_window"
  visible = { always = yes }
  dynamic_lists = { my_grid = { array = ROOT.my_array entry_container = my_entry change_scope = no value = my_value index = my_index } } } }
```

校验：`window_name` 必须存在于 `.gui`；可见触发器要便宜；动态列表计算前清空并重建临时数组；GUI 元素名须与 trigger/effect/property 完全一致。

### K. 音乐/音效（sound.music）

```txt
music = { song = { name = my_song file = "my_song.ogg" } }
sound = { name = my_sound file = "sound/my_sound.wav" }
```

校验：音频文件存在；用支持格式（ogg/wav）；避免重名；音乐台需本地化 + 素材文件。

### L. 结构 / 加载顺序（structure.replace_path_load_order / mod_tree / descriptor）

- HOI4 mod 是对选定游戏文件夹的镜像：内容放 `common/ events/ history/ interface/ gfx/ map/ music/ sound/ localisation/` 等。
- **`replace_path`** 是 descriptor 级**高风险覆盖**：`replace_path="history/states"` 会隐藏原版该文件夹内容，生成文件须尽量避免。
- 避免通用文件名（如 `00_common.txt`）除非有意覆盖；生成 ID 用 mod 前缀减少冲突。
- 工具层：拒绝 mod 根之外的绝对路径/越界路径；生成脚本与本地化分文件。

### M. 项目质量 / 调试预检（workflow project_quality_tools / debug_launch）

- 项目校验：红/黄/绿静态检查，覆盖 CWT schema、重复 ID、括号平衡、缺失 GUI/GFX/本地化引用、`replace_path` 风险。
- 本地化：先用 `generate_missing_localisation` **干跑审核**，再交给批量写入；写入只放 `localisation/<lang>/`，`_l_<lang>.yml` 后缀、`utf-8-bom`。
- 错误日志：先按子系统**归类**，再只检查可能改动的文件，不盲目重写 mod；调试启动前确认文档/map/localisation/history 文件夹为空以免污染。
- 交付规则：面向玩家的本地化必须是成品散文（非占位/设计注释）；隐藏实现性 trigger/effect 不泄漏给玩家。

---

## 三、对本项目的落地链接

| 补全主题 | 项目现有/对应实现 |
| --- | --- |
| on_actions / 事件链 | `templates/系统模板/`、事件生成器 `tools/content_generators.py`（可扩展） |
| 唯一标识扫描 | `validation.collect_entity_keys` / `tools/error_log_analyzer.py`（重复 ID 思路） |
| 本地化 BOM/散文 | `localisation_editor_*` / `游戏文件内容详解.md §17.1` |
| 项目校验红黄绿 | `export_health.py` / `tools/check_ui_coverage.py` |
| 错误日志归类 | 见下节「工具增强」 |
| scripted_gui / 音乐/结构 | 本项目编辑器不支持自动生成，可作参考模板后续扩展 |

---

## 四、工具增强（同步实施）

- `src/error_log.py` 增加**子系统归类** `classify_by_subsystem()`：按关键字（focus/decision/event/technology/state/character/localisation/gfx/map/ai）分组 error.log 行，供 `tools/error_log_analyzer.py` 输出。
- 接口层：为 `pdx_format / vp_loc / dds_convert / icon_batch / error_log` 提供可被 api_server / mcp_server 调用的统一入口（见对应模块与 `tools/` CLI）。

---

> 本文档为 RHoiScribe 知识库在项目内的镜像补全；遇到 RHoiScribe 与游戏实际不符时，以游戏本体文件与 `游戏文件内容详解.md` 为准。
