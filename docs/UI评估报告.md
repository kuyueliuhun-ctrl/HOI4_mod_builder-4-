# UI 评估报告 v2：词条展示/编辑缺失 + 原始文本操作 = 严重问题

> 更新：2026-08-19（用户定调：**词条的展示及编辑缺失**、**直接让用户对原始文本进行操作** → 一律视为**严重问题**）
> 评估依据：AGENTS.md §4.9/§4.10/§4.11/§4.12（展示 100% + 完整读写 + 写入纪律）、§2 验证。
> 本版取消上一版「设计取舍可接受」的宽松口径，改为逐点排查并给出修复方案与改动面。
> 严重度：🔴=必须修（词条不可见/不可编，或强迫搞原始文本）｜🟠=应修（影响面中）｜🟡=可缓。

---

## 0. 严重问题清单（按规律分类，逐点定位）

### 类型一 🔴 词条展示缺失（字段被隐藏、只剩计数/只读摘要）
| # | 编辑器 | 模块:行 | 缺失的词条（字段） |
| --- | --- | --- | --- |
| 1 | 角色编辑器 | 🔊 已修复（2026-08-19，批 A） | roles 结构化为可编辑职责（类型/ideology/traits/desc/expire/skill…），未知块保留显示计数 |
| 2 | 角色编辑器 | 🔊 已修复（批 A） | 角色 desc 键 + 中文可展示/编辑（保存写本地化） |
| 3 | 地图编辑器 | `map_editor_dialog.py:234-237` | 州字段 `resources / victory_points / manpower / name / state_category 名` **只读展示**（TextSelectable），无编辑 |
| 4 | 师编制 | `division_editor.py` | 营的**名称/兵种组 group/description**、`division_names_group` 只读或缺失 |
| 5 | 设计器三件套 | `ship/plane/tank_design_dialog.py` | 变体 `description/自定义 stats/版本注释` 无结构化展示（仅派生估算面板） |
| 6 | 事件/超事件 | `workbench.py`（无专用编辑器） | `title/desc/picture/option 名` 无结构化编辑器（只剩 tree） |
| 7 | 科技 | `workbench.py`（无专用编辑器） | 科技 `name/desc/图片/成本/前置` 只能 tree 编辑 |
| 8 | BOP 详情 | `bop_editor_dialog.py:731-767` | 区间**修正列表的 modifier 名/值**展示有、但不可在该 UI 编辑 |
| 9 | 顾问分配 | `advisor_assign_dialog.py` | `idea_token / slot / name / desc` 未全字段化（traits 以 raw 呈现，见下） |

### 类型二 🔴 词条编辑缺失（能看不能改，或根本没有入口）
| # | 编辑器 | 缺的编辑 | 后果 |
| --- | --- | --- | --- |
| 1 | 角色编辑器 | 🔊 已修复（批 A）desc/roles 字段表单 + traits/desc 中文 | ✅ 不再需要切树编辑器改这些字段 |
| 2 | 地图编辑器 | resources / victory_points / manpower / 州名 | 改州数据必须去找 raw |
| 3 | 师编制 | 营字段/组名/描述 | 同上 |
| 4 | 设计器 | 变体描述/自定义字段 | 同上 |
| 5 | 事件/科技 | title/desc/picture（无专用 UI） | 同上 |

### 类型三 🔴 直接让用户对原始文本进行操作
| # | 位置（模块:行） | 现状 | 应改方向 |
| --- | --- | --- | --- |
| 1 | `character_editor_dialog.py` | 🔊 已修复（批 A）肖像槽位表（类型/尺寸/贴图，行可增删），告别 raw 原文；inline/多行均解析 | ✅ 已按「肖像槽列表」实现 |
| 2 | `advisor_assign_dialog.py:618-620, 894-896` | traits / available 直接编辑 raw | 拆成结构化列表（trait 选择器 / 触发器编辑） |
| 3 | `ai_plan_editor_dialog.py:183-217` | desc、focus_order 用 QPlainTextEdit raw | desc 单行/多行词条 + 国策顺序用点选器（已有 focus_order_picker 却未接） |
| 4 | `ai_*_editor_dialog.py: _edit_raw` ×7（area/equipment/faction_theater/focus/navy/plan/template） | 每个高级块都给了「原始 PDX」入口 | 结构化字段优先，raw 降级为末选项 |
| 5 | `ai_ui_common.py:366,522-552` ScriptBlockEditor「📝 原始 PDX」 | 未建模块一律丢 raw | 先给通用字段化（键值表格/列表），raw 兜底 |
| 6 | `node_edit_dialog.py:175,352-384`「高级: 直接编辑」 | 任意节点值可落 raw | 保留但仅在字段化不可用时出现 |
| 7 | `bop_editor_dialog.py:731-767`「✏ 编辑定义/动作」 | 势力/区间/修正/动作 → GenericTreeEditor | 结构化表单，tree 降级 |
| 8 | workbench 默认兜底 | 所有无专用 UI 类型 → GenericTreeEditor（其叶子最终可落 raw） | 按类型逐步补专用/结构化编辑器 |
| 9 | `map_editor_dialog.py` 未列字段 | 改 resources/vp 等需出程序外改文件 | 结构化编辑（见类型二-2） |

---

## 1. 规范符合度复评（新口径）

| 规范 | 结论 | 说明 |
| --- | --- | --- |
| §4.1/4.2/4.4 写入/编码/撤销 | ✅ 仍合规 | 未受影响 |
| §4.9 四层 / §4.10 禁图 / §2 验证 | ✅ 仍合规 | 未受影响 |
| §4.12 展示 100% | 🔴 **多编辑器未达标** | 角色 roles、地图州字段、事件/科技、营字段只读或缺失 → 见 §0 类型一 |
| §4.12 完整读写 | 🔴 **多处只能 raw 实现** | 见 §0 类型三：用户被迫编辑原始 PDX 文本 |
| §4.11 先确认 | ⚠️ 后续修复需逐项确认 | 下面的修复方案涉及 UI 形态改动，按规则先给方案 |

---

## 2. 修复方案（按批次，标注改动面与是否需设计确认）

### 批 A — 角色编辑器（✅ 已完成 2026-08-19，方案 B 单页三栏）
- `character_data.py`：roles 拆为结构化条目（类型/字段/traits/desc/未知块无损）；肖像槽位表；`render_character_block_v2` + `save_file_v2` 原子写。
- `character_editor_dialog.py`：单页三栏（左角色列表 / 中基本信息+角色描述+肖像表 / 右职责表单）；保存 upsert 名称/角色/职责 desc 本地化。
- 新增 `CharacterStructuredDataTest`(3)+`CharacterEditorStructSmokeTest`(3)；真实数据 160 文件/3448 角色/0 错误。

### 批 B — 🔴 地图编辑器补州字段编辑
- `state_loader/state_build_ops`：新增 `resources / victory_points / manpower / state_name` 的读写。
- `map_editor_dialog.py`：右侧信息面板加可编辑表单项。
- 改动面：数据层 + 面板。**需设计确认**。

### 批 C — 🔴 事件 + 科技 专用编辑器
- 新增 `event_editor_dialog.py`（列表：id/title/desc/picture/option；触发/效果块暂用结构化脚本块编辑器）；科技同理。
- 改动面：新模块。**需设计确认**（这属新工作台 UI，按 §4.11 必须给方案）。

### 批 D — 🟠 广撒的 raw 兜底降级
- `ai_ui_common.ScriptBlockEditorDialog`：未建模块先给「键值/列表结构化编辑」，raw 设为末项。
- AI 其余 `_edit_raw` 入口：把高频字段（desc/order/modules…）字段化。
- `advisor_assign_dialog`：traits 结构化选择器。
- 改动面：各对话框添加表单。**部分需确认**。

### 批 E — 🟠 师编制/设计器补齐字段
- `oob_loader`：暴露营名称/组名/description 读写。
- `division_editor`：营字段可编辑；`*_design` 变体 desc 编辑。
- 改动面：数据层 + 面板。**需确认**。

### 批 F — 🟡 长期
- 其余无专用 UI 的通用类型逐个补专用/结构化编辑。
- 删除/隐藏「高级: 直接编辑」在字段化能覆盖时的入口（保留为兜底）。

---

## 3. 结论

- **规范硬约束**（写入纪律/四层/编码/禁图/验证）依旧全部合规；
- 但按新口径，**§4.12「展示 100% + 完整读写」在角色/地图/事件/科技/AI 高级块/顾问/编制/设计器多处不达标，且大量路径把用户推向原始文本** —— 均列为 🔴 严重。
- `docs/未完成计划.md` 已并入本清单（P0/P1），先修角色→地图→事件/科技，再降级 raw 兜底。

> 进展：批 A 已完成；待你拍板项 = 批 B（地图州字段）/ 批 C（事件+科技专用 UI）/ 批 D / 批 E。
