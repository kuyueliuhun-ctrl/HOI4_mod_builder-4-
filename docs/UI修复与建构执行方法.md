# UI 修复与建构 · 后续执行方法（唯一执行文档）

> 生成：2026-08-22。拍板依据：`prototypes/` 下 9 个原型已由用户试用确认
> （P4/P6 无异议；P1/P2/P3/P5/P8/P9 已按反馈改版；**P7 实体工作台框架已拍板
> 暂不实现**，不在本文档范围）。
> 本文档写给**执行代理**：按批次顺序执行，每批次独立可交付、可验证。
> 视觉基准 = `prototypes/proto_*.py`（以最终改版为准）；
> 三设计器机制基准 = `prototypes/设计器槽位与升级调研.md`（真实游戏文件取证）。
> **状态以本文档批次表为唯一事实源**（F8 归档后历史评估见 `docs/archive/`）。

---

## 0. 执行代理须知（硬约束，违反即返工）

1. **验证命令**（每批次结束必跑，双版本退出码 0）：
   ```bat
   python -X utf8 tools/verify_contracts.py
   .venv\Scripts\python.exe -X utf8 tools/verify_contracts.py
   ```
2. **写入纪律**：mod 内容文件一律 `write_utils.atomic_write_text` /
   `icon_ops.write_file_utf8`；游戏本体文件只读，写前先
   `state_build_ops.ensure_file_in_mod(mod, hoi4, rel)`；.txt 无 BOM，
   本地化 .yml 用 `encoding="utf-8-sig", allow_bom=True`。
3. **ui_gap_probe 闭环**（用户明确要求）：每建成一个新 UI / 改造一个类型，
   在根目录 `ui_gap_probe.py` 的 `UI_COVERAGE_SPECS` 补/改该类型 spec，然后
   **全量扫描该类型所有目录**：
   ```bat
   python -X utf8 ui_gap_probe.py --types <类型key> --max-files 0
   ```
   缺口必须收敛为 0，或在报告 note 里写明豁免理由（如「仅 mod 自定义扩展键」）。
4. **Python 3.8 兼容**（.venv 是 3.8.10）：无 walrus/match/`list[str]`/
   `str.removeprefix`；注解用 `from __future__ import annotations`。
5. **GUI 测试 offscreen**：`QT_QPA_PLATFORM=offscreen`；**禁止**生成/提交任何
   UI 预览截图（§4.10）；控制台 GBK——脚本内避免 print emoji 或用
   `python -X utf8`。
6. **PyQt6 坑**：`QPainter.drawPixmap` 无 (float,float,QPixmap) 重载；
   `QWidget.updatesEnabled()` 是方法；`QTest.mouseMove` 不可靠（手工构造
   QMouseEvent）；QComboBox blockSignals 期间 addItem 会自动选中第 0 项。
7. **四层分离**（§4.9）：数据层（xxx_data/xxx_loader 纯逻辑）→ UI 层
   （dialog 控件搭建）→ 信号槽层薄接线；新对话框样式对齐
   `src/theme.py` + `src/ai_ui_common.py` 现有组件（EntityListSidebar /
   KeyValueTableEditor / ScriptBlockEditorDialog），不自造重复件。
8. **本地化双行**：凡可本地化字段（名称/描述/选项名/槽位/类别），显示一律
   「键 + 中文」，写回一律 `localisation_editor_data.upsert_loc_entry`；
   列表/控件右键挂 `quick_loc_menu.install_context_menu`。
9. **未分析大表用法**：需要某类型真实字段全集时，在根目录 `已分析.md`
   （60MB）里 `grep -n "^### common/xxx" 已分析.md` 定位目录节后局部读取，
   **禁止全量读取**。
10. **每批交付物**：代码 + `tests/test_contracts.py` 新用例 + 真实数据冒烟
    （mods：`E:\mods\3350890356`、`E:\mods\3228475937`；游戏本体
    `E:\SteamLibrary\steamapps\common\Hearts of Iron IV`）+ 本文档批次表
    打勾 + `docs/未完成计划.md` 状态同步。

---

## 执行顺序总表（用户已拍板：先修低分 bug，再新建 UI）

> 2026-08-22 执行效果检验后回填真实状态（检验依据：源码符号核对 +
> 双版本 verify_contracts 337 用例全绿 + 真实数据 offscreen 冒烟 +
> ui_gap_probe character 全量扫描）。

| 批次 | 内容 | 原型依据 | 状态 |
| --- | --- | --- | --- |
| 1 | 设计器三件套修复与改版（C3=2/C4=2/C2=5） | ~~P1/P2/P3~~ | ✅ 已执行：src/designer_slots.py（resolve_slots/limits/upgrades）+ designer_common（UpgradePointsCard/槽位摘要/保存校验）+ 三对话框改版；测试 DesignerSlotsTest/VariantTypeConflictTest/DerivedNameFallbackTest 绿；原型 P1~P3 已清除 |
| 2 | 角色编辑器收尾（C8=4：路由/desc/肖像） | 批 A 延伸 | ✅ 已执行：app_routes+workbench 路由/顶层 desc/肖像缩略图列；character spec 补 desc；⚠️ 全量扫描仍有 87938 嵌套缺口（portraits/roles 子树「保留不可编辑」按 note 豁免——建议后续扩 spec `characters.*.portraits.**` 收敛） |
| 3 | 科技树画布修复（B2=4） | — | ✅ 已执行：tidy 布局（子继承父中位）/常量/跨 folder 边不再丢弃；TechLayoutTest 绿；⚠️ 3.4 双击联动依赖批次 4B，未做 |
| 4 | 事件 + 科技专用编辑器（H1/H2 🔴） | P4/P5 | ✅ 已执行：event_data/event_editor_dialog 完整版（侧栏/过滤/表单/图片/MTTH/option 卡/结构化块/其他字段表/本地化）；tech_data/tech_editor_dialog 完整版（QTreeWidget 目录树/表单/图标区/分类/folder/path/加成块/其他字段表）；app_routes/workbench/focus_view_ctrl 路由与画布双击联动；tests/test_batch4_event_tech.py 11 用例绿 |
| 5 | 地图编辑器州字段（批 B 🔴） | P6 | ✅ 已执行：state_loader resources/VP/manpower/name 解析；state_build_ops 写回封装；map_editor_dialog 右侧州字段表单（州名双行/category 下拉/manpower/resources 键值表/VP 两列表）；tests/test_batch5_state.py 11 用例绿 |
| 6 | 力量平衡编辑增强（C7=4） | P8 | ✅ 已执行：bop_loader 区间/势力/决议写回；bop_editor_dialog 亮色三页表单（区间卡 modifier 键值表/势力卡/决议新建编辑/结构化效果块）；tests/test_batch6_bop.py 7 用例绿 |
| 7 | 编制编辑器补充件（C1=6 + 批 E） | P9 | ✅ 已执行：oob_loader terrain 三项/save_sub_unit/names_groups；sub_unit_editor_dialog 完整表单；names_group_dialog 名称条目结构化；division_editor 入口/联动；oob_map_editor 最大连通区初始视野；tests/test_batch7_oob.py 7 用例绿 |
| 8 | raw 兜底降级（批 D 🟠） | P7 顾问标签参考 | ✅ 已执行：ScriptBlockEditorDialog 默认键值表+子块列表、raw 入高级菜单；ai_plan desc 双行+focus_order；advisor traits 多选/idea_token/slot/name/desc 字段化/available 结构化；AI 七编辑器 raw 统一「高级：原始 PDX（兜底）」；node_edit 文案微调；tests/test_batch8_ai_structured.py 7 用例绿 |
| 9 | 收尾：文档同步 + 全量验证 | — | ✅ 已执行：AGENTS §6.22/6.23 更新、未完成计划/UI评估报告同步、`docs/UI树形缺口检测报告.md` 重生成；双版本 verify 全绿（Python 3.14，Windows .venv 3.14.5 / WSL 3.14.4） |

### 0.x 检验追加的补充修复项（2026-08-23 对话.md 评估后）

1. **批次 1 补充 · 设计器变体高级字段卡**：真实变体块除 name/type/modules/
   upgrades 外还有 `design_team = mio:<组织>` / `parent_version` / `obsolete`
   / `icon`（取证：游戏 JAP - Japan.txt:1164-1188）——三个设计器变体表单补
   这四个字段（下拉/数值/复选/图标行）；⚠️ 变体**没有** desc 与「自定义
   stats」字段（本体国家文件已 grep 证实），不要做不存在的字段。
2. **批次 2 补充 · 角色未知块结构化编辑**：portraits/roles 子树之外的未知块
   现「仅保留不可编辑」（87938 嵌套缺口按 note 豁免）违反总纲——改为
   ScriptBlockEditorDialog（结构化）编辑未知块；并解析 TFR 用的
   `instance = { … }` 包装（characters/PRC.txt 实测存在），不得归入只读区。
3. **批次 5/6 补充**：见上表 🔶 标注差距（键值表/两列表/行内编辑），按
   P6/P8 原型补齐后方可改回 ✅。
4. **文档状态单一事实源**：`docs/UI评分清单.md` / `docs/UI评估报告.md` 为
   历史评估快照，进度状态一律以本表为准（两文档已加声明头）。

> 计划外同批改动（另一任务线，非本文档范围）：`src/mcp_tools.py` +
> `src/api_core_ext/`（MCP 工具注册/域冒烟测试）、`src/mod_creator.py`
> 抽取、`docs/mcp补充计划与执行方式.md`。

---

## 批次 1 · 设计器三件套（舰/机/坦）

### 1A 数据层（三个 `src/*_design.py` 共用改造）

1. **槽位解析重做**（新公共函数，建议放 `src/designer_slots.py` 新模块，
   三个设计器共用）：
   - `resolve_slots(archetype, variant_node)`：合并 archetype
     `module_slots` 与变体重定义（`inherit` → 沿 parent/archetype 链回溯；
     变体整块重定义 → 以变体为准）。返回
     `[(slot_key, required(bool), categories[list], is_alias(bool))]`，
     **保留定义顺序**（顺序即布局顺序：坦克「炮塔必须最上」等游戏内顺序）。
   - 支持引用式槽位 `mid_2_custom_slot = mid_1_custom_slot`（值非块 =
     引用同定义；标记 `is_alias`，UI 显示「同 XX 槽」）。
   - `parse_module_count_limits(node)` → `[(category, max_count)]`
     （`module_count_limit = { category = X count < N }`，注意 `<` 号解析）。
   - `parse_default_modules(node)` → dict（空设计初始模块）。
   - `load_upgrade_definitions(hoi4, mod)`：解析
     `common/units/equipment/upgrades/{land,air,naval}_upgrades.txt`
     （键/abbreviation/max_level/level_requirements），按 (mod,hoi4) 缓存。
   - `hull_upgrades(equipment_node)`：装备原型的 `upgrades = { … }` 声明列表。
   - **变体 upgrades 读写**：读 = 变体块内 `upgrades = { key = level }`；
     写 = 块级替换（舰艇已有 `apply_variant_upgrades`，飞机/坦克补同款；
     坦克 NSB 键 `tank_nsb_engine_upgrade`/`tank_nsb_armor_upgrade`，0~20）。
2. **模块类别/槽位中文表重写**（删掉现有臆造键）：
   - `ship_design.SLOT_LABELS` 补：`front_1_custom_slot` 船头自定义 1、
     `front_2… / mid_1/2/3 / rear_1/2`、`fixed_ship_secondaries_slot` 副炮、
     `fixed_ship_armor_slot` 装甲、`fixed_ship_sonar_slot` 声呐。
   - `plane_design.CATEGORY_LABELS` 重写为真实类别：
     `plane_engine_type` 引擎 / `twin_plane_engine_type` 双列引擎 /
     `plane_special_module_small` 小型特殊 / `plane_special_module_defense_turret`
     自卫炮塔 / `plane_special_module_electronics` 电子设备 /
     `plane_weapon`（武器）等；缺失键回退「英文键 + term_registry 查询」。
   - `tank_design.SLOT_LABELS` 补 `special_type_slot_4`、
     `lc_main_armament_slot` / `lc_secondary_armament_slot`；
     `CATEGORY_LABELS` 重写：`tank_small_main_armament` /
     `tank_medium_main_armament` / `tank_light_turret_type` /
     `tank_medium_turret_type` / `tank_suspension_type` /
     `tank_non_tracked_suspension_type` / `tank_armor_type` /
     `tank_engine_type` / `tank_special_module` / `tank_radio_module` /
     `tank_secondary_turret` / `tank_flamethrower`。
   - 全部走 localization_mgr.get_name 回退链（中文 loc → 原始键）。
3. **同名跨设计器冲突修复**（`ship_design.parse_equipment_variants:398-427`）：
   返回键从 `name` 改 `(name, kind)`（kind 由 type 含 ship_hull/airframe/
   chassis 判定）；`plane_design.find_variant_block:378-387` /
   tank 同款：匹配块时**校验 type**（type 相等或为其 archetype/派生名），
   消除「飞机保存写进同名舰艇块」。
4. **派生变体名回退**：`derived_variant_name → airframe/chassis 键` 反查表
   （解析 archetype 时收集）；variant.type 未命中时回退，消除「机体定义未找到」。
5. **`plane_design._AIRFRAME_FILES:28-30` 白名单放宽**：目录扫描
   `common/units/equipment/*airframe*.txt`（mod 可自建文件名），tank/ship 同理。

### 1B UI 层（三个 `*_design_dialog.py`，视觉基准 P1/P2/P3）

1. **required 语义反转**（三处同一 bug）：
   `plane_design_dialog.py:413,430-435`、`tank_design_dialog.py:390-395`、
   `ship_design_dialog.py:454,471-476` —— 删除「required 且空 → 🔒 禁用」分支；
   改为：`required 且空` → 橙色虚线框「必装·待填」**可点击**；仅
   `allowed_module_categories` 为空且非 required → 灰🔒（tooltip 写明
   「该槽位不允许任何模块类别」）。槽位卡片：图标在上/中文名在下/零间隔
   （复用原型 `SlotCard` 的三种状态样式，迁入 `designer_common.py`）。
2. **布局改版**（对齐原型）：
   - 舰艇：固定装备区（6 列网格）+ 甲板自定义区（6 列网格），多则换行；
     区标题行显示「解锁槽位 N（必装 M）」与「同类上限：雷达≤2 …」。
   - 飞机：上排 5（主武器 + 辅助×3 + 引擎）单行；下排 7 列特殊槽区；
     **任何机体只有 1 个 `engine_type_slot`**（不要按双发画两个引擎槽）。
   - 坦克：上排 6（炮塔/主炮/特殊×4）+ 下排 3（悬挂/装甲/引擎）+
     下方升级加点区。
   - 文字放槽位下方、去间隔（用户已拍板）。
3. **船体/机体/底盘选择器**：顶栏 QComboBox（archetype 分组 + 中文名 +
   year 排序）；`_add_design`（`ship:561-575`/`plane:522-535`/
   `tank:477-490`）弹选择框（QInputDialog 或小对话框），不再 `keys[0]`
   写死；编辑中切换 → 确认「将清空模块」→ 重建槽位区。
   顺带修 `tank_design_dialog.py:480` 的 `"New Plane Design"` →
   「新坦克设计」及文件 docstring「Plane Designer」→「Tank Designer」。
4. **保存校验条**（左栏底部固定，参照原型 `SaveValidationBar`）：
   必装槽存在未填 → 红条「必装槽未填 N 个」+ **禁用保存按钮**；
   全填 → 绿条放行。保存成功提示注明「已自动复制到 mod」（现有语义）。
5. **升级加点区**（参照原型 `UpgradePointsCard`）：按 hull/机体/底盘
   `upgrades` 声明生成行（中文键名 + 0~max_level SpinBox +
   `level_requirements` 科技上限备注）；保存随 modules/upgrades 一并写回。
6. **变体中文名**：设计下拉与顶部标题显示设计名中文（name 键 →
   localization_mgr.get_name），无则显示原名并右键快速本地化。

### 1C 验证

- 契约测试（`tests/test_contracts.py`）：
  `DesignerSlotsTest`：resolve_slots 继承/重定义/引用别名/顺序保留；
  `ModuleCountLimitTest`：`count < 2` 解析；`VariantKeyConflictTest`：
  同名舰机坦变体互不覆盖（roundtrip）；`DerivedNameFallbackTest`；
  `DesignerDialogSmokeTest` 扩展：必装空槽可点、真锁定不可点、
  保存按钮随必装缺失禁用、机体切换重建、升级读写 roundtrip。
- 真实数据冒烟：56 船体/120 模块/118 airframe/101 模块/108 chassis/
  116 模块全解析零异常；upgrades 定义 land 13/air 8+/naval 8+ 加载。
- `ui_gap_probe.py`：新增 spec `plane_variant/tank_variant` 不适用
  （变体在 history/countries，见批次 7 的 country_history spec）；
  本批不加新 spec，跑既有 spec 确认无回归即可。

---

## 批次 2 · 角色编辑器收尾（C8）

1. **路由接入**（当前唯一入口是工具菜单，工作台双击落通用树）：
   - `src/app_routes.py`：`ROUTES`（:133-144）加
     `("common/characters", _open_character_editor)`；`_open_character`
     延迟 import `character_editor_dialog.open_character_editor`。
   - `open_character_editor`（`character_editor_dialog.py:545`）加可选参数
     `file_path="", entity_id=""`：打开时定位到该文件/角色。
   - `src/workbench.py`：`_on_file_double_clicked:613-645` 与
     `_on_entity_double_clicked:661` 对 `common/characters` 路径/角色实体
     特判 → `generic_file_selected`（走路由）而不是画廊。
   - `content_types.SPECIAL_TYPE_KEYS` 加 `"character"`（置顶）。
2. **顶层 desc**：`character_data.parse_character_block:296-344` 提取顶层
   `desc = "键"` 到 `meta["desc"]`（现落入 others_lines）；
   `character_editor_dialog.py:272-273` 优先显示文件真实键，无键时显示
   灰字「无 desc 键」+「＋ 创建 desc 键」按钮（默认 `<角色id>_desc`）。
3. **肖像预览 + 上传**：肖像表（:119-123）加缩略图列（
   `icon_resolver.resolve_pixmap(texture值, mod/hoi4)`，失败占位）；
   表格右键/按钮「⬆ 上传肖像」→ `icon_ops.upload_icon(mod, img, base,
   ICON_RULES["character"])`（content_types.py:241-264，gfx/Leaders，
   ref_mode=path）→ 回填 texture 相对路径。行为对齐国策图标上传。
4. **ui_gap_probe**：character spec（ui_gap_probe.py:71-80）covered 补
   `characters.*.desc`；跑 `--types character --max-files 0` 收敛。
5. 测试：`CharacterRouteTest`（文件/实体双击路由到角色编辑器）；
   `CharacterDescTest`（顶层 desc 提取/写回 roundtrip）；
   `CharacterPortraitPreviewTest`（缩略图列存在、上传回填路径——patch
   QFileDialog）。

---

## 批次 3 · 科技树画布修复（B2）

1. **布局算法**（`src/tech_view.py:106-178` `layout_tech_trees`）：
   - x 坐标改为「子节点继承父节点 x 中位数」（tidy tree）；同层冲突时
     整体右移避让；保持 folder 分树。
   - 常量（:25-29）：`GRID_X = NODE_W + 60`（=310）、
     `GRID_Y = NODE_H + SUBTECH_H + 40`（NODE_H=112、子科技槽高 30 → ≈190），
     消除水平零间隙/垂直贴边。
2. **跨 folder 边不丢**（`src/focus_render.py:106-108`）：删除
   `if child not in pos: continue` 的静默丢弃；布局完成后统一收集全部
   `path/leads_to_tech` 边，跨树边画灰色虚线（同树边保持现样式）。
3. **装备迭代 vs 加成区分**：`_SubTechSlot`（tech_view.py:256-279）从
   46×30 编号小格改为并排 48×48 中等图标（`sub_technologies` 各项解析
   图标，`icon_resolver` 按 `GFX_<sub_id>_medium` 解析）；普通加成/奖励
   徽章维持小尺寸。
4. **与批次 4 联动**：画布节点**双击** → 打开科技编辑器并定位该科技
   （`tech_editor_dialog.open_tech_editor(file_path, tech_id)`，见批次 4）；
   编辑器保存后回调画布刷新（信号或重新加载）。
5. 测试：`TechLayoutTest`（纯函数：同层无重叠、子继承父中位、跨树边计数）；
   `TechCanvasSmokeTest`（offscreen 渲染无异常、双击发信号）。

---

## 批次 4 · 事件 + 科技专用编辑器（新模块）

### 4A 事件（`src/event_data.py` + `src/event_editor_dialog.py`，视觉基准 P4）

数据层（模式对齐 `ai_loader.py`，复用其通用函数）：
- `load_event_entities(mod, hoi4)`：扫描 `events/**/*.txt`（mod 优先，
  `_scan_files` 模式 + 缓存）；**字符级 `_block_ranges`** 定位顶层
  `add_namespace` 词条与 `country_event` / `news_event` 块（大文件
  parse_pdx_text_to_nodes 会截断，教训见 AGENTS §6.7）。
  实体字段（真实键，已从 `已分析.md` events 节核实）：`id / title / desc /
  picture / major / is_triggered_only / fire_only_once / hidden /
  mean_time_to_happen{days,modifier} / immediate / option* / after /
  fire_for_sender / minor_flavor`。
- CRUD：复用 `ai_loader.insert_top_block / delete_top_block /
  rename_top_block / duplicate_top_block`；字段写回
  `replace_top_block_fields`（:256）；`option` 子块用
  `upsert_top_block_child`（:1048，支持多个同名 option：按索引定位，
  需新增 `replace_nth_child(content, top_id, key, index, text)`）。
- 保存：`ensure_file_in_mod` + 内容级替换 + `atomic_write_text`。

UI（对话架构 = EntityListSidebar + 滚动表单区 + StructuredBlockCard 样式行）：
- 侧栏：事件列表（id + 中文名 + 类型徽章）+ 类型过滤（全部/
  country_event/news_event/隐藏）+ CRUD。
- 表单：事件类型/id/命名空间；title、desc **本地化双行**
  （键 + 中文，`LocEdit` 样式）；picture 行 = 96×64 预览
  （`icon_resolver.resolve_pixmap`）+「⬆ 上传」
  （`icon_ops.upload_icon` + `ICON_RULES["event"]`）+「🔍 图标库选择」；
  major/is_triggered_only/fire_only_once/hidden 复选；MTTH 天数 +
  `mean_time_to_happen.modifier` 结构化块（`ScriptBlockEditorDialog`）。
- **option 列表卡**（参照原型 OptionCard）：每选项 = name 本地化双行 +
  trigger / ai_chance / 效果体三个结构化块按钮 + ↑↓⧉🗑；
  「＋ 新增选项」追加 `option = { name = … }` 模板块。
- immediate / after 结构化块行；**「其他字段」表**（原型
  OtherFieldsTable：文件内其余键统一键值编辑，读写无损——这是
  §4.12「100% 展示」的兜底，替代 raw）。
- 本地化：title/desc/option name 保存时 `upsert_loc_entry`
  （`find_mod_file_for_key` 定位目标 yml）；列表右键快速本地化；
  「🌐 批量补写缺失本地化」= `batch_fill_missing_loc` 限定本文件键集。
- 路由：`app_routes.ROUTES` 加 `("events", _open_event_editor)`；
  workbench 文件/实体双击特判（events 目录）；`SPECIAL_TYPE_KEYS`
  加 `"event"`。

ui_gap_probe 新 spec：
```python
"event": {
    "label": "事件编辑器", "top": "*",
    "covered": ["add_namespace", "country_event.**", "news_event.**"],
    "note": "全部子字段经表单+结构化块+其他字段表覆盖；.** 即整子树",
},
```
跑 `--types event --max-files 0`（events 目录 44 万条目，聚合输出可行），
缺口应为 0 或仅 mod 特殊顶层键。

测试：`EventDataTest`（解析/CRUD/第 N 个 option 替换 roundtrip）、
`EventEditorSmokeTest`（offscreen：侧栏过滤、选项增删、表单读写）、
`EventWorkbenchRouteTest`（双击路由）。

### 4B 科技（`src/tech_data.py` + `src/tech_editor_dialog.py`，视觉基准 P5）

数据层：
- `load_tech_entities(mod, hoi4)`：`common/technologies/*.txt` 顶层
  `technologies = { }` 与零散 folder 键（已分析.md 证实两种形态）；
  字段：`start_year / research_cost / categories / folder{name,position} /
  path{leads_to_tech,research_cost_coeff} / enable_equipments / allow /
  ai_will_do / sub_technologies / special_project_specialization /
  category_* 装备加成块 / priority`。
- CRUD + 字段写回复用 ai_loader 通用族；`folder.position` 用
  `replace_or_upsert_nested_child`（:1346）。
- `set_tech_folder_position(content, tech_id, x, y)`。

UI（视觉基准 P5 改版）：
- **左边栏 = QTreeWidget**（folder 目录 → 科技叶子；中文名 + 年份；
  搜索框过滤；folder 项不可选）。点击科技叶子 → 右侧表单加载。
- 表单：科技名/desc 本地化双行；**图标区 183×84**（真实展示尺寸，
  见 docs/科技图标存储规则.md）+「⬆ 上传」=
  `tech_icon_ops.upload_tech_icon`（自动注册 GFX sprite）+「图标库选择」；
  start_year/research_cost 数值；categories 徽章增删（候选来自
  `common/technology_tags`）；folder 下拉 + position x/y；
  path 表（leads_to_tech/research_cost_coeff 行）；
  enable_equipments 列表增删；allow / category_* 加成块结构化编辑
  （修正名自动中文化 + 百分比格式化）；「其他字段」表。
- 入口：科技树画布节点双击（批次 3.4）+ 工作台科技文件**右键**
  「编辑科技词条…」（文件双击仍进画布，不改变现习惯）；
  「🌳 在科技树画布中定位」反向联动。

ui_gap_probe：`tech` spec（:104-109）covered 从 `[]` 改为
`["technologies.**"]`（画布只读拓扑，编辑能力由本编辑器承担）；
跑 `--types tech --max-files 0`。

测试：`TechDataTest`、`TechEditorSmokeTest`（树形侧栏选中→表单加载）、
`TechEditorRouteTest`（画布双击/右键入口）。

---

## 批次 5 · 地图编辑器州字段（批 B，视觉基准 P6）

1. 数据层 `src/state_loader.py`：
   - `_parse_state:130-159` 补解析 `resources` 块（dict 键→数值；
     ⚠️ tree_node 把块内裸值解析为 key——按「key 无值」处理数值需取
     raw 行，参照 victory_points 的解析方式）；
   - 暴露 `victory_points`（已解析未展示）；`manpower`、
     `history.name`（本地化键，如 STATE_124）。
2. 写回 `src/state_build_ops.py`（模式全部对齐现有
   `set_state_category_in_content:263-282` + `_set_key_line:228-247`）：
   - `set_state_resources_in_content(content, state_id, {res: val})`
     （块级替换，val<=0 删键，键删光删空块）+ `set_state_resources` 包装；
   - `set_state_victory_points_in_content`（`pid = points` 配对序列块级
     重写）+ 包装；
   - `set_state_manpower`（标量）；
   - `set_state_name_in_content`（name 键替换）+ `set_state_name`
     （附带 `upsert_loc_entry(mod yml, STATE_<id>, 中文)`）。
   - 全部：`ensure_file_in_mod` → 读 → 改 → `atomic_write_text`。
3. UI `src/map_editor_dialog.py` 右侧面板（视觉基准 P6；三栏结构与
   建筑按钮区不动）：
   - 州信息卡改可编辑表单：州名双行（STATE_ 键 + 中文）、
     state_category 下拉（`load_state_categories` 中文名）、
     manpower QSpinBox、resources 键值表（KeyValueTableEditor，
     候选 = 游戏资源键钢/铝/铬/油/橡胶/钨 + 自定义）、
     victory_points 两列表（pid/点数，增删行）。
   - 建筑区/归属/国家色按钮原样保留；底部「💾 保存州文件」。
   - 点选省份 → 面板加载所属州；保存后 `StateData.reload()`。
4. ui_gap_probe：state spec（:196-204）covered 补
   `state.name, state.resources.**, state.history.victory_points.**,
   state.history.manpower`（以真实州文件嵌套为准——实现时抽 1 个
   原版州文件确认 resources/victory_points 是否在 history 内）；
   跑 `--types state --max-files 0`。
5. 测试：`StateResTest`（resources 解析/写回 roundtrip）、
   `StateVpNameTest`、`MapStatePanelSmokeTest`（表单读写、保存调用链）。

---

## 批次 6 · 力量平衡编辑增强（C7，视觉基准 P8 亮色版）

> 用户拍板：**换回程序基本亮色风格**（现深色主题废弃）。

1. 数据层 `src/bop_loader.py` 补写回：
   - `set_bop_range(mod, hoi4, bop_id, range_id, min, max)` /
     `set_bop_range_modifiers(..., {key: val})`（range 子块字段/嵌套
     modifier 块级替换，`replace_or_upsert_nested_child`）；
   - `set_bop_side_fields`（图标/本地化键）；
   - `insert_bop_decision(mod, hoi4, category, block_text)` /
     `delete_bop_decision`（定位 `common/decisions` 同名分类块，
     `insert_top_block_child` / `delete_top_block`）；
   - 决议 cost / add_power_balance_value 字段
     `replace_top_block_fields`。
   - 本地化：BOP/势力/区间/动作名 upsert（沿用现有链）。
2. UI `src/bop_editor_dialog.py`：
   - 移除深色 QSS，全局走 `theme.py` 亮色 + Card 样式（结构参照原型 P8）。
   - 「平衡与区间」：滑块 + 初始值；每区间卡 = min/max SpinBox +
     modifier 键值表（行内编辑）；区间增删。
   - 「势力与修正」：左右势力卡可编辑（图标/中文名/关联区间勾选）。
   - 「决议（动作）」：动作列表 + 「＋ 新建决议」（模板选择：通用/限时/
     切换类，块文本来自 `templates/系统模板/决议/`）+ 选中项编辑表单
     （名称本地化双行/花费/BOP 增量/效果结构化块）+ 删除。
   - 保存：`ensure_file_in_mod` + 原子写（BOP 文件与决策文件分别写）。
3. ui_gap_probe：bop spec（:131-139）covered 扩为
   `["*", "*.**"]`（表单+结构化全覆盖，note 说明动作在 decisions 文件）；
   跑 `--types bop --max-files 0`。
4. 测试：`BopEditTest`（区间/势力/动作 CRUD roundtrip）、
   `BopDialogLightSmokeTest`（无深色样式断言、表单读写、新建决议模板插入）。

---

## 批次 7 · 编制编辑器补充件（C1 + 批 E + 小项，视觉基准 P9）

1. **地形三项**（C1）：`oob_loader._parse_terrain:315-323` 解析
   movement/attack/**defence**（注意英式拼写）三键 →
   `{地形: {movement, attack, defence}}`；`division_stats:543-553` 三键
   各自平均；`division_editor.py:845-849` 徽章卡片改三行（移/攻/防分色，
   参照原型 `_terrain_card`），:468 tooltip 同步。
2. **兵种（sub_unit）编辑对话框**（新 `src/sub_unit_editor_dialog.py` +
   数据层函数入 `oob_loader.py`）：
   - `load_sub_units` 已读（:326-374）；补 `save_sub_unit(mod, hoi4, uid,
     fields, need, terrain, stats, others)`：定位 `common/units/*.txt`
     所在文件（ensure_file_in_mod）→ 块级替换（ai_loader 通用族）→
     原子写。
   - UI 参照原型 P9「编辑兵种」：id/名称双行（本地化）/描述双行/
     group 下拉/parent/sprite；need 键值表；terrain 键值表
     （值 = `movement, attack, defence` 逗号三元组，或三列展开——
     执行时选三列展开，避免手输逗号）；22 属性字段表；其他字段表。
   - 入口：`division_editor` 的 UnitPickerDialog 加「✎ 编辑兵种」按钮。
3. **division_names_group**（当前完全无 UI）：`OobFile`（:711-880）补
   解析顶层 `division_names_group = { <组id> = { icon / order /
   is_name / generic / name … } }`（块级保留，不替换未编辑项）；
   `division_editor` 模板栏旁加「🏷 命名组…」按钮 → 小对话框
   （组列表 + 表单 + 名称条目结构化块，参照原型 P9 第③件）。
4. **设计器联动小项**：`division_editor.py:1010-1023` 打开三设计器时传
   `country_tag`；`find_oob_country:617-658` 兜底正则放宽大小写。
5. **C6 OOB 地编初始视野**：`oob_map_editor.py` 把 `_focus_region` 定位
   （:226-241, :246-255）移到 `showEvent` 首次显示执行（fitInView 在
   show 前调用按临时几何计算会偏）；fit 改为国家**本体最大连通区**
   （首都所在州优先），避免海外领土拉成全球视野。
6. **country_history spec**（变体兜底）：ui_gap_probe 加
   ```python
   "country_history": {
       "label": "国家历史文件（变体/顾问等）", "top": "*",
       "covered": ["create_equipment_variant.**"],
       "note": "变体（模块/升级）由三设计器覆盖；其余块走树编辑器，逐步收敛",
   },
   ```
   跑 `--types country_history --max-files 0` 记录基线（预期缺口大，
   属长期项，报告注明即可）。
7. 测试：`Terrain3Test`、`SubUnitEditorTest`（roundtrip）、
   `NamesGroupTest`、`OobViewFocusTest`（showEvent 定位调用）。

---

## 批次 8 · raw 兜底降级（批 D）

> 原则：结构化优先，raw 只作「高级」菜单末项；不得删除 raw 能力（兜底保留）。

1. `src/ai_ui_common.py` `ScriptBlockEditorDialog`（:296，raw 入口 :522）：
   默认视图改为「键值表（KeyValueTableEditor）+ 子块列表（双击进入，
   面包屑）」；「📝 原始 PDX」移入「高级 ▾」菜单末项。
2. `src/ai_plan_editor_dialog.py:183-217`：desc 改本地化双行编辑；
   focus_order 接入已有 `focus_order_picker`（点选回填顺序）。
3. `src/advisor_assign_dialog.py:618-620, 894-896`：traits/available 的
   raw QPlainTextEdit 换结构化：traits = 多选弹窗（候选 =
   `common/unit_leader/*_traits` + `country_leader_traits` 并集，
   徽章展示选中，参照原型 P7 顾问标签——**仅取该弹窗交互**，P7 框架
   本身仍不实现）；available = ScriptBlockEditorDialog。
   idea_token/slot/name/desc 字段化（slot 下拉候选固定枚举）。
4. AI 七编辑器 `_edit_raw` 入口：文案统一「高级：原始 PDX（兜底）」并
   放入「高级 ▾」菜单（不删功能）。
5. `src/node_edit_dialog.py`「高级: 直接编辑」（:352-384）：保留，仅当
   当前键无词条/模板命中时默认展开提示（文案微调，不强制隐藏）。
6. 测试：`ScriptBlockStructuredTest`（默认结构化视图、raw 在菜单）、
   `AdvisorTraitsTest`（选择器回写格式）、`AiPlanDescTest`。

---

## 批次 9 · 收尾

1. 文档同步：
   - `AGENTS.md` §6 补本批摘要（沿用 §6.22 风格）；
   - `docs/未完成计划.md`：3d 批 B/C/D/E 状态改完成、需拍板清单更新
     （民族精神/意识形态/决议专用 UI → 指向 P7 暂不实现的决策）；
   - `docs/UI评分清单.md`：补批次落点列；`docs/UI评估报告.md` 批次表打勾；
   - `prototypes/设计器槽位与升级调研.md` 内容并入
     `docs/游戏文件内容详解.md` §9（科技与装备）——按 §4.8 契约。
2. 全量验证：双版本 `verify_contracts.py` 退出码 0；
   `ui_gap_probe.py`（全部 spec、`--max-files 5` 默认档）重生成
   `docs/UI树形缺口检测报告.md` 存档。
3. 汇报格式：每批次一行「批次 N ✅（测试 +N 用例，共 M 绿；缺口扫描：
   类型 X 0 缺失 / 类型 Y 豁免理由）」。

---

## 附：复用件速查（执行时直接 import，不要重写）

| 需求 | 函数/类 | 位置 |
| --- | --- | --- |
| 侧栏实体列表 | `EntityListSidebar` | src/ai_ui_common.py:39 |
| 键值表 | `KeyValueTableEditor` | src/ai_ui_common.py:191 |
| 结构化块编辑 | `ScriptBlockEditorDialog` | src/ai_ui_common.py:296 |
| 顶层块 CRUD | `insert/delete/rename/duplicate_top_block` | src/ai_loader.py |
| 块内字段替换 | `replace_top_block_fields` :256 / `replace_top_block_field` :993 | src/ai_loader.py |
| 子块 upsert | `upsert_top_block_child` :1048 / `replace_or_upsert_nested_child` :1346 | src/ai_loader.py |
| 原版文件落 mod | `ensure_file_in_mod` | src/state_build_ops.py:29 |
| 原子写 | `atomic_write_text` | src/write_utils.py:52 |
| 本地化读 | `load_effective_dict` :131 / `LocalizationManager.get_name` | src/localization_editor_data.py / localization_mgr.py |
| 本地化写 | `upsert_loc_entry` :230（目标定位 `find_mod_file_for_key` :304） | src/localization_editor_data.py |
| 右键快速本地化 | `install_context_menu` | src/quick_loc_menu.py:13 |
| 图标读 | `resolve_pixmap` | src/icon_resolver.py:205 |
| 图标写（通用/科技） | `upload_icon` / `upload_tech_icon` | src/icon_ops.py:285 / tech_icon_ops.py:169 |
| 路由注册 | `ROUTES` + `_open_xxx` | src/app_routes.py:133 |
| 缺口扫描 | `UI_COVERAGE_SPECS` | ui_gap_probe.py:71 |
