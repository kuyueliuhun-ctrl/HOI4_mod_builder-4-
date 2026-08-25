# PROJECT_DOC.md — HOI4 Mod 编辑器（hearts_of_iron_builder）项目文档

> **本文档是项目的唯一总文档**，写给下一个接手本项目的人或 AI 代理：
> 一页看全「是什么、怎么跑、怎么改、踩过哪些坑、当前做到哪」。
> 本文档**取代**：`AGENTS.md`（已删除，历史归档 `docs/历史迭代日志.md`）、`README.md`、
> `docs/功能与实现文档.md`、`docs/综合报告.md`、`docs/环境搭建.md`、`docs/验证契约.md` 等一揽子说明文档。
> 深度专项资料（如《游戏文件内容详解》《MCP 与接口规格》《整合计划》）仍作为**参考子文档**保留，本文档是它们的入口索引。

- **核对日期**：2026-08-25（数据均以当日实测为准）
- **项目形态**：Windows 桌面应用，Python 3.14 + PyQt6，直接读写 HOI4 mod 目录脚本文件
- **如何复用**：接手后先通读第 1、3、5 节；改代码前重读第 1.7 节（工程纪律）与第 4 节（UI 要求）；动手后按第 3.2 节跑验证；扩展功能按附录 E 流程。

**总目录**

1. 一、功能架构（§1.1~§1.7）
2. 二、已实现 / 未实现的核心功能模块及实现方式（§2.1~§2.4）
3. 三、项目整体情况数据汇总（含执行进度）（§3.1~§3.4）
4. 四、UI 设计原则与要求（§4.1~§4.5）
5. 五、避坑指南（§5.1~§5.7）
6. 附录 A · 常用命令速查
7. 附录 B · 文档体系（取代关系）
8. 附录 C · 支撑/辅助模块索引
9. 附录 D · 五大节之外的内容与去向（防遗漏清单）
10. 附录 E · 如何扩展（开发流程 How-to）
11. 附录 F · 外部参考
12. 附录 G · 知识类内容索引（按主题查文档）
13. 附录 H · 历史迭代索引（详情见 `docs/历史迭代日志.md`）

---

## 一、功能架构

### 1.1 项目定位

**钢铁雄心 4（HOI4）Mod 编辑器**，面向 mod 作者的桌面可视化工具链：
直接读写 mod 目录下的游戏脚本文件（`.txt` / `.gfx` / `.yml` / `.mod` / `.csv` / `definition.csv`），
并带地图可视化能力。**不是**浏览器应用，**不是**打包器。

覆盖从「创建 Mod 工程」到「国策 / 科技 / 事件 / 决议 / 理念 / 角色 / 编制 / 装备 / 地图 / AI 内容」的完整可视化编辑，
内置 PDX 脚本解析、多源翻译、图标管理、校验体系与 AI 辅助创作。

### 1.2 技术栈与运行环境

| 项 | 值 |
| --- | --- |
| 语言 / GUI | Python 3.14+ / PyQt6（6.11，Qt 6.11） |
| 图像 | Pillow（DDS/PNG/BMP）+ numpy（地图矩阵运算） |
| 外部依赖 | PyQt6、Pillow、numpy、mcp（可选，未装则回退内置零依赖 MCP 实现） |
| 依赖清单 | 根目录 `requirements.txt`（Windows）/ `requirements-wsl.txt`（Linux/CI） |
| 入口 | `src/main.py`；`启动.bat` / `启动.sh` 均指向它 |
| 界面模式 | `settings.json` 的 `ui_mode`：`workbench`（默认，功能最全）/ `classic`（经典文件树） |

**两个 Python 环境（都必须兼容）**：

| 环境 | 路径 | 版本 | 用途 |
| --- | --- | --- | --- |
| Windows | `.venv\Scripts\python.exe` | 3.14.5 | 用户启动器；旧 3.8.10 备份 `.venv_py38_backup` 已于 2025-08-25 清理 |
| WSL/Linux | `/root/hoi4_builder_venv/bin/python` | 3.14.4 | 开发/测试 |
| CI | GitHub Actions `verify.yml` | 3.14 | `push`/`PR` 自动跑 `verify_contracts.py` |

> Python 3.14 升级已完成（2026-08-23），3.8 语法限制解除：新代码可直接用
> `list[str]`、walrus、`match`、`str.removeprefix` 等 3.10+ 语法。

### 1.3 目录结构

```
hearts_of_iron_builder/
├── src/                # 全部 Python 源码（235 个模块，约 6.4 万行）
├── tests/              # 契约/回归测试（86 个文件，510 个用例）
├── tools/              # CLI 工具与契约门禁（21 个脚本）
├── docs/               # 深度参考文档（12 个 md）
├── templates/          # 模板库（67 个系统模板类别 + 顶层 2 类，共 1105 个 txt）
├── translations/       # 词条库（QIUQI/自定义/效果/修正等 10 个 json + README）
├── design_templates/   # 设计器模板（独立目录，普通模板搜索器搜不到）
├── unit_counter_library/  # 单位标牌库（icon/ + manifest.json，448 个标牌）
├── .runtime/           # 运行时缓存（地图矢量/填充等，已被 .gitignore）
├── settings.json       # 用户运行配置（已 git 忽略，本机存在）
├── 启动.bat / 启动.sh  # 启动脚本
├── setup.bat / setup.sh# 一键建 venv + 装依赖 + 跑契约验证
├── ui_gap_probe.py     # UI 覆盖缺口探针（根目录）
├── prototypes/         # 未落地类型的原型（doctrine/mio/equip_def/country_history/faction/script_lib 等，见 §2.3）
├── 常用代码/           # 用户参考：mod 常用代码/模板文本（非源码，不入库）
├── 游戏素材/           # 用户参考：识图素材（学说/MIO 等截图，已入库参考，见 §2.6）
├── ruff.toml           # Ruff 静态检查（只开 E9/F63/F7/F82 错误级，零误报）
└── .github/workflows/verify.yml  # CI 契约验证
```

### 1.4 分层架构（最重要）

所有代码遵循**四层职责分离**，依赖方向单向向下，下层禁止反向 import 上层：

```
算法层（Core Algo） ← 绘图层（Render） ← UI 层（Widget/Layout） ← 信号槽层（Controller/Binding）
```

- **算法层**：纯逻辑、无 Qt 控件。解析/序列化、坐标换算、布局计算、校验。可依赖 `QPointF/QColor` 与数据类；**禁止** `QWidget`/`QPainter`/`connect`/直接写文件。
- **绘图层**：把数据变成 `QGraphicsItem/QPixmap/painter` 图形项与几何。**禁止**弹窗、改业务数据、持布局。
- **UI 层**：搭建控件/布局/样式，把用户动作翻译成语义信号。**禁止**直接写文件、跑算法、`QPainter` 绘图。
- **信号槽层**：最薄，只做接线与编排（`connect`、弹窗、调算法/写文件、刷新）。**禁止**塞大段算法或 UI 细节。

判定顺序：**算法 > 绘图 > UI > 信号槽**（命中上层即归上层，信号槽是兜底薄层）。
命名约定：大型模块按 `<域>_algo.py` / `<域>_render.py` / `<域>_view.py` / `<域>_ctrl.py` 分文件；
小对话框可用类后缀分职责，不强制拆文件。门禁：`tools/check_layer_deps.py`。

已落地的拆分先例：`focus_view.py`（原 2476 行）→ `focus_algo.py` + `focus_render.py` + `focus_view_ctrl.py` + 瘦壳；
`workbench.py` → `content_types.py`（纯数据）+ `entity_scanner.py`；`main_window.py` → `app_routes.py` + `menu_factory.py` + `main_window_docks.py`。

### 1.5 数据流与写入纪律

```
游戏/mod 文件 --(解析)--> 数据层(loader/算法) --(模型)--> 专用 UI / 通用树形编辑器
                                        ▲                            │
                                        └──── atomic_write_text ◄────┘ (信号槽层编排写回)
```

- **解析**：自研 PDX 解析器（`pdx_parser.py` / `tree_node.py` / `tree_model.py`）+ 各域 loader。
  注意 `parse_pdx_text_to_nodes` 只返回**顶层**节点，需递归；大文件要用字符级 `_block_ranges`（见 §5）。
- **写回**：一切 mod 内容文件必须走 `write_utils.atomic_write_text` 或 `icon_ops.write_file_utf8`
  （临时文件 + `os.replace` 原子替换；写失败不破坏原文件；写前自动登记撤销快照）。
- **涉及游戏本体**：一律先 `ensure_file_in_mod` 把原版文件复制到 mod 再写，**绝不直写游戏原版文件**。

### 1.6 内容类型体系

`src/content_types.py` 是**唯一权威**的内容类型注册表（纯数据，无 Qt）。

- `CONTENT_TYPES`：**100 种**内容类型 `(key, 中文名, emoji 图标, mod 相对目录列表, 基础模板类型, 扩展名)`；
- `SPECIAL_TYPE_KEYS`：有专用编辑器的类型置顶分组，含
  `focus / tech / initial_oob / bop / character / event / ai_*` 等 14 项；
- `AI_TYPES`：AI 内容类型集合（文件/实体双击直接走 `generic_file_selected` 分发）。
- **路由**：`src/app_routes.py` 是路径 → 专用编辑器打开函数的纯路由配置；
  双击文件按类型分发：国策→画布、`history/units`→师编制设计器（按军种拉起舰/机/坦）、
  图标型→实体画廊、其余→通用树形编辑器。
- **无文件模式**：不直接操作文件而是操作实体/项目；跨文件合并绘制国策树；
  「🔍 选择国家」**仅切换浏览，不写任何文件**；
  「🌐 国家设置（复制/创建）」才是**显式写操作**（复制原版/创建空覆盖，需确认才写 mod）。

### 1.7 工程纪律（可执行契约，改代码前必读）

1. **写入纪律**：mod 内容文件一律原子写（见 1.5）；禁止直接 `open(path,"w")`；
   确需直写程序配置/数据须登记 `tools/write_discipline_allowlist.json` 并写明理由。
   静态扫描：`python tools/check_write_discipline.py`。
2. **编码契约**：默认 UTF-8 **无 BOM** + LF；BOM 文本默认拒绝（`WriteContractError`）。
   **例外**：本地化 `.yml` 用 `utf-8-sig, allow_bom=True`（HOI4 惯例）。
3. **原子写语义**：写失败绝不破坏原文件（临时文件 + os.replace）。
4. **撤销快照**：写前自动登记 `undo_mgr`（新写入默认 undo=True）。
5. **双版本兼容**：所有新代码必须在 Python 3.14 下编译运行（Windows `.venv` + WSL 双验证）。
6. **契约测试**：新功能必须配套测试（纯函数优先；GUI 用 offscreen 冒烟）；bug 修复必须补回归测试。
7. **写 mod 文件 = 可能破坏游戏**：任何批量写操作先小样本验证。
8. **游戏机制详解契约**：主动/被动了解游戏机制后，必须把结论持久化写入
   `docs/游戏文件内容详解.md`（或对应章节），**不得只留在对话/内存里**；附真实示例片段，切勿臆造字段。
9. **四层分离**（见 1.4）。
10. **禁止输出预览截图**：不得生成/提交 `*_预览.png` 等 UI 截图到仓库；验证界面用 offscreen 冒烟或让用户看实际窗口。
11. **UI 设计先问用户或给方案**：设计/改造任何 UI 必须先提问或给 2~3 个方案让用户拍板，不得按假设直接实现。
12. **UI 必须先吃透游戏机制并保证完整读写**：见第 4 节。

---

## 二、已实现 / 未实现的核心功能模块及实现方式

### 2.1 已实现：核心功能模块总表

> 模块路径均相对 `src/`。行数为 2026-08-25 实测（≈ 四舍五入）。

| 功能域 | 核心模块 | 实现方式要点 | 状态 |
| --- | --- | --- | --- |
| 入口/主题 | `main.py`（23）、`theme.py`（401） | QApplication + 字体 + 主题令牌 + 全局 QSS（亮色专业工具风，对齐 Scenario Forge） | ✅ |
| 主窗口/装配 | `main_window.py`（1046）、`main_window_docks.py`（553）、`menu_factory.py`（46） | 菜单/文件树/工作台/画布装配；工具菜单动作构建 | ✅ |
| 工作台 | `workbench.py`（1175）、`content_types.py`（299）、`entity_scanner.py`（622） | 类型列表/文件列表/实体提取；专用类型置顶分组；文件/无文件双模式 | ✅ |
| 路由 | `app_routes.py`（983） | 信号槽层纯路由表：路径→专用编辑器打开函数 | ✅ |
| 国策/科技树 | `focus_view.py`（1189）+ `focus_algo.py` + `focus_render.py` + `focus_view_ctrl.py`（1106）、`focus_renderer.py`、`tech_view.py`、`focus_order_picker.py` | QGraphicsView 自绘画布；国策树（文件/无文件模式、图标上传自动写 gfx）；科技树 BFS 树形布局、folder 分组、path 连线；国策顺序点选器 | ✅ |
| 通用树形编辑器 | `generic_tree_editor.py`（1260）、`tree_node.py`、`pdx_parser.py`、`tree_model.py`、`node_edit_dialog.py` | 任意 PDX 脚本树形编辑，保存走原子写 | ✅ |
| 事件编辑器 | `event_data.py`（486）+ `event_editor_dialog.py`（1044） | 完整版：unit_leader_event、文件级其他字段、结构化 option/effect | ✅ |
| 科技编辑器 | `tech_data.py`（452）+ `tech_editor_dialog.py`（812）、`tech_icon_ops.py` | 完整版：technologies 包装/零散 folder、allow/加成块、画布双击联动；科技图标自动写 gfx | ✅ |
| 角色编辑器 | `character_data.py`（522）+ `character_editor_dialog.py`（718） | 只替换 name/portraits 区，保留 roles；字符级块定位 | ✅ |
| 顾问分配 | `advisor_assign_dialog.py`（1254） | `generic_advisors.txt` 顾问分配识别与编辑（大文件，行数预算白名单） | ✅ |
| 力量平衡 BOP | `bop_loader.py`（851）+ `bop_editor_dialog.py`（626）+ `bop_editor_pages.py`（764） | 数据层解析 common/bop + 决议动作；仿游戏内 BOP 弹窗（深色历史风）；本地化/修正展示/区间滑块/动作编辑；保存走 ensure_file_in_mod + 原子写 | ✅ |
| 师编制 v2 | `division_editor.py`（1091）、`oob_loader.py`（1027）、`oob_stats.py`（313）、`oob_format.py`、`sub_unit_editor_dialog.py`（425）、`names_group_dialog.py` | 仿游戏内 Division Designer：顶部模板下拉 + 数据面板 + 地形矩阵；技术数据“营字段优先→主装备回退”；军种识别 `detect_oob_kinds` 自动拉起对应设计器 | ✅ |
| OOB 入口/地编 | `initial_oob_editor.py`（246）、`oob_map_editor.py`（640） | 打开 OOB 直接进师编制设计器；地图放置复用 MapCanvas（get_map_data/get_state_data 单例缓存） | ✅ |
| 兵牌图标接入 | `unit_counter_library.py`（含 `find_counter_entry` 兵种→标牌解析，97% 覆盖）、`unit_counter_icons.py` | OOB 地图兵牌与师编制槽位在 GFX 解析失败时回退单位标牌库（448 标牌），消除黑底占位；按兵种缓存 | ✅ |
| 舰艇设计器 | `ship_design.py`（817）+ `ship_design_dialog.py`（486） | hull/modules/variants + upgrades 写回；槽位网格；属性估算（基础+addΣ×multiply 累积）；原版自动落 mod | ✅ |
| 飞机设计器 | `plane_design.py`（533）+ `plane_design_dialog.py`（473） | airframe/modules/variants + modules 写回；同款跨国家同步 | ✅ |
| 坦克设计器 | `tank_design.py`（415）+ `tank_design_dialog.py`（441） | chassis/modules/variants，复用 plane 的 modules 写回 | ✅ |
| 设计器公共 | `designer_base.py`（691）、`designer_common.py`、`designer_slots.py`、`design_template.py` | 三设计器公共基类/控件/槽位数据；模板独立存 `design_templates/`，原子写 | ✅ |
| AI 内容编辑器 | `ai_loader.py`（1085）+ `ai_loader_crud.py`（1130）+ `ai_ui_common.py`（695）+ `ai_*_editor_dialog.py` | 8 类 AI 内容完全专用 UI（固定 300px 侧边栏）；实体级 CRUD（insert/delete/rename/duplicate）；未知字段保留 | ✅ |
| 本地化体系 | `translation_editor.py`、`translation_loader.py`、`gui_translator.py`（708）、`localisation_editor_data.py`、`localisation_editor_dialog.py`、`localization_mgr.py` | 多源翻译（QIUQI 等 10 个词条 json）、批量补写、快速右键本地化；只写 mod 不改游戏原版 | ✅ |
| 词条库 | `term_registry.py`（213）、`qiqi_term_import.py` | translations/ 词条注册表；同键冲突 QIUQI 最后加载胜出 | ✅ |
| 地图数据 | `map_loader.py`（483）、`map_vector.py`、`map_fill.py` | provinces.bmp→2^24 LUT→省 ID 矩阵；矢量边界/多边形填充（numpy + 磁盘缓存） | ✅ |
| 地图画布 | `map_canvas.py`（1244） | 可复用画布：手型/点选/涂色/框选/多选；选区高亮；瓦片缓存+边界烘焙+滚轮预览缩放；state outline | ✅ |
| 地图编辑/区域 | `map_editor_dialog.py`（1015）、`map_region_ops.py`、`region_editor_dialog.py`（358） | 三栏布局（建筑类型/画布/地块信息）；框选划分 strategicregions/supplyareas/states | ✅ |
| 州/建筑/国家色 | `state_loader.py`（317）、`state_edit_ops.py`、`state_build_ops.py`（646）、`building_lib.py`（250）、`state_batch.py` | 州解析（owner/provinces/buildings/VP）、州归属/建筑/类别/国家颜色写回；`ensure_file_in_mod` 原版自动落 mod | ✅ |
| 校验体系 | `export_health.py`（549）、`validation.py`（308）、`health_check_dialog.py`、`unique_id_scanner.py` | 导出前健康检查（8 类：括号/编码/引用/重复 id/贴图/科技图标/本地化/悬空前置）；本地化缺失+国策引用检测 | ✅ |
| 模板系统 | `template_scheduler.py`（583）、`template_dialog.py`、`template_manager_dialog.py`、`gen_system_templates.py` | 按类型分目录；从模板新建文件；变量替换；任意块存为模板 | ✅ |
| SF 移植 | `overlay_rules.py`（300）、`overlay_report_dialog.py`、`icon_manifest.py`（204）、`unit_counter_library.py`（188） | 覆盖规则链+增量报告；图标库 manifest；单位标牌库提取（448 个） | ✅ |
| 内容生成器 | `content_generator_dialog.py`、`*_gen.py`、`mod_creator.py` | country/ideas/ideology/character/general/focus/事件生成器；新建 mod 工程骨架 | ✅ |
| 撤销 | `undo_mgr.py`（81）、`write_utils.py`（114） | 文件写入撤销（画布 Ctrl+Z / 工具菜单）；原子写核心 | ✅ |
| HTTP API | `api_server.py`（929）+ `api_core_ext/`（9 个域 Mixin） | `ApiCore` 唯一操作核心；仅绑定 127.0.0.1 + Bearer token；`/api/mcp/<tool>` 同源桥 | ✅ |
| MCP | `mcp_server.py`（190）、`mcp_tools.py`（651） | stdio 传输；159 个工具注册表（唯一权威来源）；优先官方 mcp 库，回退内置零依赖实现 | ✅ |
| MIO 编辑器 | `mio_loader.py`（333）、`mio_editor_dialog.py`（473）、`mio_trait_tree.py`、`mio_policy_editor_dialog.py` | 特质树画布 + 特质增删改 + 图标选择 + 方针编辑器（552 MIO/22 方针） | ✅ |
| 学说编辑器 | `doctrine_loader.py`（298）、`doctrine_editor_dialog.py`（491） | 主要学说→4 次要学说面板（陆军精通度+满级奖励徽章）→子学说编辑 | ✅ |
| Mod 描述编辑器 | `mod_descriptor_loader.py`、`mod_descriptor_editor_dialog.py` | .mod 表单式编辑：name/version/supported_version/remote_file_id/path/archive/picture/tags/replace_path/dependencies + 其他条目原样保留；原子写 | ✅ |
| 意识形态专用编辑器 | `ideologies_editor_dialog.py` + `load_ideologies_detail` + `political_editor_data.py` | 侧栏意识形态列表（15 个真实意识形态）；color/dynamic_faction_names/types/rules/modifiers/faction_modifiers 表单；CRUD；未知标量与子块原样保留 | ✅ |
| 民族精神（理念）专用编辑器 | `ideas_editor_dialog.py` + `load_ideas_grouped` + `political_editor_data.py` | 按分类分组导航（避免 1.4 万条理念平铺）；块内原始脚本体编辑；分类内新建/复制/改名/删除；原子写 | ✅ |
| 地图数据层色阶 | `map_data_layers.py` + `map_editor_dialog`（数据层下拉）+ `map_canvas.set_overlay_pos` | 胜利点/资源总量色阶覆盖层、补给区分类着色、铁路折线、河流近似线；真实数据冒烟全过 | ✅ |
| AI 集成 | `ai_assist.py`（154）、`ai_assist_dialog.py` | OpenAI 兼容接口直连（DeepSeek/OpenAI/通义千问等）；提示词助手 | ✅ |

### 2.2 通用编辑器四件套（B2/B3 批量的核心架构）

自 2026-08 起，多数内容类型用**通用编辑器 + 薄壳**落地，避免每个类型都写一套 UI：

| 通用编辑器 | 用途 | 薄壳数量 |
| --- | --- | --- |
| `simple_block_editor.py` + `simple_entity_tab.py` | 通用顶层块动态编辑器（动态字段） | 60 个 `*_editor_dialog.py`（≤25 行） |
| `nested_block_editor.py` + `nested_block_crud.py` + `generic_nested_loaders.py` | 通用嵌套实体编辑器（wrapper→实体块） | 决议/理念/on_actions/建筑等 |
| `raw_block_editor.py` + `raw_block_loaders.py` | 原始块编辑器（脚本库/枚举/效果/条件） | defines/names/script_lib |
| `generic_tree_editor.py` | 万能兜底树形编辑器 | 所有类型最后兜底 |

典型的 18 行薄壳模式（以 `decisions_editor_dialog.py` 为例）：

```python
DecisionsEditorDialog = make_nested_block_dialog(load_decisions, "决议", "决议编辑器")
def open_decisions_editor(file_path="", mod_path="", hoi4_path="", entity_id=None, parent=None):
    dlg = DecisionsEditorDialog(mod_path, hoi4_path, parent=parent, initial_id=entity_id)
    dlg.show(); return dlg
```

> 改 B2/B3 类型 = 改 loader + 路由 + ui_gap_probe spec + 测试，四件套闭环。

### 2.3 未实现 / 待办（当前唯一执行总表 = `docs/整合计划.md`）

**功能性待办（P1~P4 批次）：**

| 批次 | 内容 | 状态 |
| --- | --- | --- |
| P1 需调研 | 大洲划分 / 批量填鸭(AOR) / 电台生成 / H4MPS 审查 / 核心圈层 / IRIS / 大众脸 | ⬜ 未开始 |
| P2 需复刻/实现 | 自生成 GUI 决议包、~~民族精神/意识形态专用 UI~~ ✅、编制小项、~~兵牌图标接标牌库~~ ✅、RHoiScribe MCP 插件 | ⬜ 未开始 |
| P2.5 已知限制 | 数值估算、未定义 airframe 容错、version_name 联动、装备 IC 花费（已登记） | ⬜ 长期 |
| P3 转模板/文档 | RHoiScribe 补全、特殊案例/教程提炼 | ⬜ 未开始 |
| P4 暂缓/外部/不做 | 旗帜、议会 GUI、Shader、电台 OGG、系统预览等 | ⬜ 暂缓 |

**B 线剩余缺口：**

| 项 | 说明 |
| --- | --- |
| B2 · P23 国家历史专用化 | `ci_exempt` 长期项，建议豁免（当前通用编辑器可编辑） |
| ~~B3 · P39 高级文件~~ | ✅ 已全部落地：行动阶段/抵抗活动/限时活动/defines + **.mod 专用编辑器** + **.gui/.gfx 显式通用树路由** |

**与 hoi4modutilities 对比发现的新候选缺口（详见 §2.5，需用户拍板是否进入执行）：**
- 游戏状态模拟引擎（条件/剧本求值）+ 世界地图条件换色 / 国策·科技·MIO 可用性预览；
- ~~地图数据层（河流/铁路/补给/资源/VP 色阶）~~ ✅（2026-08-25 已落地：`map_data_layers.py` + 地图编辑数据层下拉）与地图 QA 结构校验；
- 事件树关系图、GUI 预览（.gui 渲染）、DDS/TGA 独立查看、世界地图整图导出、DLC 内容加载。
- 注：其中部分曾列于 P4“系统预览等（暂缓）”，本轮盘点将其转为**明确候选待办**，是否做仍由用户拍板。

**历史遗留 / 可选项（登记在 `docs/历史迭代日志.md` 附录 6.17，以整合计划为准）：**
- ~~兵牌图标接入单位标牌库~~ ✅（2026-08-25 已落地：OOB 地图兵牌与师编制槽位 GFX 解析失败时回退 448 标牌库，97% 兵种覆盖）；
- Scenario Forge 移植剩余方向：导出前校验面板产品化、build_snapshot 溯源台账、关键地区高危 id 清单；
- 编制编辑器：模板改名后部署引用不一致提示、装备 IC 花费估算、OOB 海军/空军 version_name 设计解析（调研完成未实现）。

**触发式/长期项：** `generic_tree_editor.py` / `advisor_assign_dialog.py` / `map_canvas.py`
行数预算白名单保留，下次功能改动时顺手拆分。

**原型目录 `prototypes/`：** 保留未落地/待拍板类型的原型
（`proto_doctrine.py` / `proto_mio.py` / `proto_equip_def.py` / `proto_country_history.py` /
`proto_faction.py` / `proto_script_lib.py` + 调研 md）。已落地类型的原型已删除；
动手前先看对应原型与调研 md，避免从零设计。

### 2.4 外部接口与自动化（HTTP / MCP）

- **唯一操作核心 `ApiCore`**（`src/api_server.py`）：HTTP / MCP / CLI 共用，禁止另起实现；
  组合 9 个域 Mixin（`src/api_core_ext/`：states / designers / ai_content / bop / loc_tools /
  health / media / generators / project）。
- **工具注册表 `src/mcp_tools.py::build_tools(core)`** 返回 **159 个工具**（基础 17 + 域扩展 142），
  MCP 与 HTTP 同源，是工具清单的唯一权威来源。
- **方法约定**：dict 进 dict 出；数据层 lazy import；写方法清缓存 + `_notify_change(path)`；
  错误抛 `ValueError` → HTTP 400 / MCP 错误文本。

**HTTP API**（仅绑定 127.0.0.1，`Authorization: Bearer <token>`）：

| 端点 | 说明 |
| --- | --- |
| `/api/status` | 运行状态 |
| `/api/types` | 内容类型清单 |
| `/api/entities` (GET/POST/DELETE) / `/api/entities/<id>` (GET/PUT/DELETE) | 实体 CRUD |
| `/api/project` | 项目级操作 |
| `/api/localisation` | 本地化写操作 |
| `/api/tech_icon` | 科技图标上传 |
| `/api/validate` | 校验 |
| `/api/templates` | 模板查询 |
| `/api/files` (GET/POST) | 文件读写 |
| `/api/icon_manifest` | 图标库 manifest |
| `/api/overlay_report` | 覆盖规则与增量报告 |
| `/api/tools/format_pdx` / `vp_loc` / `error_log` / `register_icon_batch` | 独立工具 |
| `/api/mcp/<tool_name>` | **同源桥**：可直调全部 159 个 MCP 工具 |
| `/api/help` | 端点帮助 |

**MCP**（stdio 传输；优先官方 mcp 库，未装回退内置零依赖实现）：工具域分布
基础 17 / 域0 存量补齐 4 / 域1 州·建筑·区域 16 / 域2 三军设计器+模板 30 /
域3 师编制·OOB 8 / 域4 AI 内容 8 类 49 / 域5 BOP 4 / 域6 本地化·词条 8 /
域7 校验·健康·撤销 5 / 域8 图标·媒体 4 / 域9 内容生成器 7 / 域10 项目级 7。
运行：`python mcp_server.py --mod <mod目录> [--game <游戏目录>]`。
完整规格见 `docs/MCP与接口规格.md`（含 Claude Code 配置示例）。

**dry_run 约定**：批量/结构操作默认 `dry_run=true`，只返回 `{files:[...]}` 预览，
显式 `false` 才落盘（17 个默认 dry_run 工具）。

### 2.5 与 hoi4modutilities（E:\hoi4modutilities）对比：功能缺口盘点

> 对比日期：2026-08-25。对象：`E:\hoi4modutilities`（VSCode 扩展，herbix/hoi4modutilities，
> 强项是「预览 / 游戏状态模拟 / 查错 / DLC 加载」）。
> 结论：本项目在「编辑 / 写回」维度远超对方；功能缺口大多落在“预览—模拟—校验”这条线上。
> 以下清单供后续拍板是否补齐；涉及 UI 必须先按 §4.1 问用户 / 给方案，写回必须走原子写 + 撤销（§1.7）。

| # | 缺口 | 对方实现（E:\hoi4modutilities） | 本项目现状 | 严重度 |
| --- | --- | --- | --- | --- |
| 1 | **游戏状态模拟引擎**（条件/剧本/效果求值） | `src/hoiformat/condition.ts` + `effect.ts` + `scope.ts`：把 `owner`/`controller`/`core`/`claim_by`/`DMZ`、`allow_branch`、`available` 解析成带作用域的逻辑表达式，按用户勾选条件/剧本求值 | `available`/`bypass`/`allow_branch` 仅存原始块文本（`focus_processor.py`/`tree_node.py`），**从不求值** | 🔴 架构级 |
| 1a | 世界地图按条件/剧本换色（owner/controller/core/claim/DMZ） | `webviewsrc/worldmap/loader.ts`（`getCountryByState`/`getStateToCountryMap`）+ `conditionExprs` + bookmarks | 地图只按静态 `owner` 着色（`map_loader.country_overlay_pixmap`） | 🔴 |
| 1b | 国策可用性预览（`allow_branch`/offset/icon 条件） | `previewdef/focustree/schema.ts` + 条件下拉 | 国策画布只画静态树，无“已完成后哪些国策可用” | 🔴 |
| 1c | 科技可用性预览（`allowBranch`+`leadsTo`+`xor`） | `webviewsrc/techtree.ts` | 科技树画布纯布局，无可用性模拟 | 🔴 |
| 1d | MIO 条件预览/警告 | `previewdef/mio/*`（条件下拉 + add/remove/override trait 校验） | MIO 特质树只按 position 画图（`mio_trait_tree.py`） | 🟡 |
| 2 | **地图数据层缺失**（河流/铁路/补给/资源/VP 色阶） | `worldmap/loader.ts` + `definitions.ts`：`rivers.bmp`、railways、supply_nodes、resources/manpower/VP/州类别/大洲等色阶、DMZ、本地化省名标签 | `map_loader.py` 只加载 provinces/terrain/heights/definition；地图图层仅国家色/边界/地形/hillshade/AI 战区（州数据面板已能读写 resources/VP/manpower，但未画成图层） | 🔴 |
| 3 | **地图 QA / 结构校验** | `i18n/en.ts` 的 `worldmap.warnings.*` 全套：省像素（one-pixel/过大过小/颜色冲突/id 重复）、邻接、河流、州/战略区/补给区结构 | `export_health.py` 是通用健康检查（括号/编码/引用/重复 id），**无地图几何/地图数据文件级校验** | 🔴 |
| 4 | **事件树关系图预览** | `previewdef/event/contentbuilder.ts` + `webviewsrc/eventtree.ts`：event→option→子事件、MTTH/延迟/作用域/事件图/循环检测/搜索/跳转定义 | 表单式事件编辑器（`event_editor_dialog.py`），无事件链可视化 | 🔴 |
| 4a | 跨文件引用扫描（Scan References） | `util/dependency.ts`：扫事件引用与本地化，自动补 `#!event:` / `#!localisation:` 头 | 无等价自动引用扫描 | 🟡 |
| 5 | **GUI 预览（.gui 渲染）** | `previewdef/gui/*` + `webviewsrc/guipreview.ts`：`containerwindowtype` 真实渲染、切换子窗口可见性、全屏、进度条 sprite | `.gui` 待补（整合计划 P39），目前只能通用树编辑 | 🟡 |
| 6 | **DDS/TGA 直接预览** | `ddsviewprovider.ts` 把 `.dds`/`.tga` 当图片直接打开 | `dds_loader.py`/`dds_convert.py` 只能解码/转换，无独立查看窗口 | 🟢 |
| 7 | **世界地图整图导出** | `topbar.ts` export：1~10 倍缩放导出 PNG | 无整图导出（grep 无 QImageWriter/QPixmap.save） | 🟢 |
| 8 | **DLC 内容加载** | `util/fileloader.ts`：读 `dlc/*.zip` + `integrated_dlc/`，优先级 workspace>DLC>游戏本体，并读 `.mod` 的 `replace_path` | 统一 mod>游戏本体 两级，**不读 DLC zip** | 🟡 |
| 9 | 实时预览/自动刷新 + 预览状态持久化 | `previewmanager.ts` 依赖订阅 debounce 自动刷新；`topbar.ts` savestate 持久化 | 无文件监听，仅 `(mtime,size)` 缓存；地图面板状态不持久化 | 🟢 |

> 补充说明：部分表面相似能力不算缺口——gfx 预览 ↔ 本项目“图标库 manifest”（`icon_manifest.py`）；
> 国策拖拽改坐标 ↔ 本项目国策画布拖拽；科技树预览 ↔ 本项目科技树画布（但对方按**游戏真实
> `countrytechtreeview.gui` 布局**渲染并可切换 folder，本项目是自研 BFS 布局，保真度不同）；
> MIO 预览 ↔ 本项目 MIO 特质树画布（但对方多了条件/警告校验）。

**建议补齐优先级**：
① 条件/剧本求值引擎（含 1a~1d）→ ② 地图数据层（河流/铁路/补给/资源/VP 色阶）→
③ 地图 QA 结构校验 → ④ 事件树关系图 → ⑤ GUI 预览 → ⑥ DDS/TGA 查看、整图导出、DLC 加载。
①是根，其余大多能建在它之上；每一项启动前先按 §4.1 拍板 UI 方案。

---

### 2.6 DeepSeek 视觉识图工作流（AI 辅助 UI 设计）

> 适用：主模型不能读图时，用 DeepSeek 官方视觉模型识别游戏 UI 截图，产出识图规格供编辑器设计。
> 2026-08-25 已用其完成 MIO / 学说 界面识图（素材在 `游戏素材/`，学说结论在 `docs/学说识图.md`）。

**调用方式**（不走 `ai_assist`，直接调官方接口）：
- 模型：`deepseek-v4-flash-vision-exp`（harness `deepseek-official` provider 内置，`inputModalities: [text, image]`）
- 凭据：harness 凭据 `~/.dsh/.credentials.yaml` 的 `DEEPSEEK_API_KEY`（或环境变量同名）；**不写进 settings.json**
- 端点：`POST https://api.deepseek.com/chat/completions`，`Authorization: Bearer <key>`
- 请求体：`messages[0].content = [{type:text, text:提示词}, {type:image_url, image_url:{url:"data:image/png;base64,..."}}]`
- 图片约束：像素 ≤ 640k（PIL 缩放）、编码 ≤ 1MiB（PNG 超限回退 JPEG q90）
- `max_tokens` 建议 ≥ 8000：该模型会产出 `reasoning_content`，输出 token 易被占满
  （`finish_reason: length` 会导致 `content` 为空），识图用 12000 实测稳定

**提示词要点**：让模型按「整体布局 / 全部可见文本（中英保留）/ 层级与交互 / 图标·状态·数值」四段输出，
并强调“不要臆造界面上不存在的字段”。

**产物落点**：识图结论写入 `docs/*识图.md`（如 `docs/学说识图.md`）供编辑器设计；素材截图放 `游戏素材/`。

---

## 三、项目整体情况数据汇总（含执行进度）

> 数据为 2026-08-25 实测（本机 WSL 环境）。

### 3.1 代码规模

| 指标 | 数值 |
| --- | --- |
| `src/` 源码模块数 | **235** 个 `.py`，约 **63,773** 行 |
| 内容类型 `CONTENT_TYPES` | **100** 种（旧文档写 90+/93/94，以当前为准） |
| 测试文件 / 用例 | **86** 个文件 / **510** 个 `test_*` 方法 |
| 工具脚本 `tools/` | **21** 个 |
| 模板库 | **67** 个系统模板类别 + 顶层 `country_history`/`focus_tree`，共 **1,105** 个 `.txt` |
| 词条库 `translations/` | **10** 个 json + README（QIUQI 主库 1887 + modcode 939 + diplo 11 + tfr 50 + tno 210 ≈ 3,097 条，另有效果/修正/自定义词条） |
| 单位标牌库 | **448** 个标牌（`unit_counter_library/icon` + `manifest.json`） |
| MCP 工具 | **159** 个（基础 17 + 域扩展 142，`src/mcp_tools.py` 唯一权威） |
| HTTP API | `ApiCore` + `api_core_ext/` **9** 个域 Mixin |
| 文档 `docs/` | **12** 个 `.md` |
| 架构分层 | 四层分离已落地，`check_layer_deps.py` 门禁通过 |

### 3.2 验证状态（2026-08-25 实测）

```bash
# 全量契约测试
cd /mnt/e/hearts_of_iron_builder
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m unittest discover -s tests -t .
# 结果：Ran 510 tests in 53.7s — OK (skipped=1)
```

`tools/verify_contracts.py` 一键验证 6 步，退出码 0 才算完成：
1. 语法编译（全部 `.py` py_compile，跳过 `.venv*`/git 等）；
2. 单元契约测试（含原子写/BOM 拒绝/撤销/健康检查检出/纪律扫描）；
3. 写入纪律静态扫描 `check_write_discipline.py`（AST 扫描直写）；
4. 四层分离依赖方向检查 `check_layer_deps.py`；
5. 行数预算门禁 `check_file_budget.py`（防存量大文件名单变长）；
6. **UI 缺口探针（轻量）**：仅本地有 `settings.json` 时执行，对
   `event,tech,character,bop` 跑 `ui_gap_probe.py --types ... --max-files 5 --output .runtime/ui_gap_verify.md --ci`；
   CI/新环境无 settings 自动 SKIP。

双版本都要跑（Windows `.venv` 3.14.5 + WSL 3.14.4）；CI 在 ubuntu-3.14 上等价执行。
改专用 UI 后另需手跑一次全量 `python ui_gap_probe.py --max-files 0` 确认缺口收敛。

### 3.3 真实数据冒烟（历史实测，2026-08）

用 `E:\mods\3350890356`（542 科技、1493 州文件、完整地图）与游戏本体验证过的关键数字：

| 数据 | 数值 |
| --- | --- |
| 建筑 | 59 种（32 可建造 / 27 不可建造），55 图标，38 种带效果段；694 个国家颜色 |
| 装备定义 | 354 个（common/units/equipment 整树扫描） |
| 舰艇 | 56 船体 / 120 模块 / JAP 38 个设计 |
| 飞机 | 118 airframe / 101 模块 / 95 国 449 设计（42 组同名） |
| 坦克 | 108 chassis / 116 模块 / 72 国 197 设计 |
| 军事工业 MIO | 552 MIO / 22 方针 |
| 学说 | 12 主要学说 / 4+ track / 95 子学说 |
| 派系 | 351 个实体 |
| 科技图标 | 游戏本体 1318 个科技文件、2133 个 `GFX_*_medium` sprite、1894 条贴图引用 |
| 单位标牌 | 448 个（导入 2.6s） |

### 3.4 执行进度（截至 2026-08-25）

**整合计划状态**（唯一执行总表 `docs/整合计划.md`）：

| 块 | 状态 |
| --- | --- |
| 工程债 F0~F10 / UI 第一批 A1~A8 / 问题 P1~P11 | ✅ 已完成 |
| B0 公共组件（`ui_widgets.py` 等） | ✅ 已完成 |
| B1 AI 工作台（P10~P16） | ✅ 已完成 |
| B2 通用类型（P17~P27） | 🔶 **基本完成**（P17~P22/P24~P27 已落地；P23 国家历史建议豁免） |
| B3 全量覆盖（P28~P39） | ✅ **已全部落地**（P39 已闭环：.mod 专用编辑器 + .gui/.gfx 显式通用树路由） |
| 未完成计划 P1~P4 | ⬜ 未开始（按拍板/调研推进） |

**Git 状态**：分支 `main`，工作区干净，与 `origin/main` 同步。
最近提交序列（自新至旧）：

```
eee635c B2-P25: 学说编辑器（主要学说→4次要学说面板→子学说编辑）
fc87ebc B2-P22: MIO 编辑器（特质树画布+特质增删改+图标选择+方针编辑器）
c86a86f B3: 新增命名列表(names)与游戏定义(defines) 原始块编辑器（P38/P39 部分）
ed7b6ed B2/B3: 新增派系(factions)/国策内嵌窗口/装备定义(equipment) 编辑器
2279eee B2-P17: 脚本库专用编辑器（RawBlockEditor），工作台拆为效果/条件/枚举三项
...
```

**里程碑回顾**：
- 2026-08-15 地图编辑器体验、编制 v2、舰/机/坦设计器、设计器模板；
- 2026-08-16 BOP 专用工作台、AI 内容编辑器（专用 UI + 固定侧边栏）；
- 2026-08-18 四层分离重构落地（focus_view 拆分、工作台收敛、门禁上线）、src/ 包化；
- 2026-08-19 本地化+QIUQI 词条库+实体资源工作台+RHoiScribe 吸收；
- 2026-08-22 MCP 142 新工具（共 159）、UI 修复与建构批次 1~9；
- 2026-08-23 Python 3.14 升级完成；整合计划 B2/B3 批量铺开；
- 2026-08-25 学说编辑器落地（最近一次提交）；
- 2026-08-25（本轮）与 hoi4modutilities 对比盘点：登记预览/模拟/校验/DLC 等 9 类缺口候选（§2.5）；
- 2026-08-25（本轮）B3 P39 闭环：.mod 专用编辑器 + .gui/.gfx 显式通用树路由（见附录 H 6.27）；
- 2026-08-25（本轮）P2 兵牌图标接标牌库：OOB 地图兵牌与师编制槽位回退 448 标牌库，97% 兵种覆盖（见附录 H 6.28）；
- 2026-08-25（本轮）P2 民族精神/意识形态专用 UI：意识形态表单编辑器 + 民族精神分类分组编辑器（见附录 H 6.29）；
- 2026-08-25（本轮）P2 地图数据层色阶：VP/资源/补给区/铁路/河流五类数据覆盖层（见附录 H 6.30）。

---

## 四、UI 设计原则与要求

### 4.1 三条硬性纪律（可执行）

1. **先问用户或给方案**：设计/改造任何 UI 或工作台 UI 前，必须先向用户提问，
   或给出 2~3 个方案让用户拍板（如亮色 vs 深色、侧边栏 vs 顶栏、入口位置）。
   **不得**未经确认直接按自己假设实现界面形态。
2. **先吃透游戏机制，保证完整读写**：动手前必读相关游戏文件与 Wiki，弄清加载/解析/引用/写回语义。要求：
   - **100% 展示**文件内容：界面必须能呈现文件中的全部字段/块/值，不得因设计取舍隐藏或丢弃；
   - **思考引申内容**：默认值、回退、引用联动、其他 mod 用法、DLC/派生块要在方案中说明；
   - **完整读写**：覆盖新建/编辑/删除/保存，遵守写入纪律（§1.5/§1.7）。
   - 若存在游戏内设计器（编制/舰艇/飞机/坦克/国策等），**主动要游戏内 UI 的文字描述/识图规格**，不得仅凭猜测设计。
3. **禁止输出预览截图**：不生成/提交 `*_预览.png` 等 UI 截图；验证用 offscreen 冒烟/统计或让用户看实际窗口。

### 4.2 UI 覆盖验证闭环

- **`ui_gap_probe.py`**（根目录）：对已有专用 UI 的类型，按 `UI_COVERAGE_SPECS` 比对真实文件，
  输出「树形编辑器有、专用 UI 无展示/编辑」的顶层键与嵌套路径缺口报告。
  **新增/修改专用 UI 后必须同步 spec 并运行验证缺口收敛**。
  ```bash
  python ui_gap_probe.py --max-files 5 --output docs/UI树形缺口检测报告.md   # 缺口报告
  python ui_gap_probe.py --dump-all --output 已分析.md                        # 全类型词条统计
  ```
- `tools/check_ui_coverage.py`：扫「未覆盖词条」的旧工具。
- 参考目录：游戏根目录（`settings.json` 的 HOI4_path）、mod 目录（mod_path）、
  `E:\SteamLibrary\steamapps\workshop\content\394360`。

### 4.3 主题规范

- **主题**：`src/theme.py`，集中设计令牌 + 全局 QSS，亮色专业工具风（对齐 Scenario Forge）。
- **主色令牌**（`COLORS`）：`accent=#1f4f7e`（深蓝）、`map_accent=#b05b2d`（土橙）、
  `success/#warning/#danger`、文本四级灰阶、边框 `rgba` 细线、hover 半透明填充。
- **圆角**：`RADIUS = {card:16, btn:10, input:8, item:6}`；字体栈含微软雅黑。
- 代码内取色用 `from theme import COLORS`；新对话框先套令牌，不要硬编码色值。

### 4.4 已确立的 UI 惯例（新 UI 应沿用）

| 惯例 | 说明 |
| --- | --- |
| 固定侧边栏 | 列表型编辑器用 300px 固定侧边栏（`ai_ui_common.EntityListSidebar`），**强制关闭横向滚动条**，长文本省略号+tooltip |
| 数据面板定宽 | 右侧信息面板 `setFixedWidth(330)`，内容变化不影响布局 |
| 三栏布局 | 地图编辑器：左=建筑类型列表 / 中=画布 / 右=地块信息面板 |
| 图标按钮 | 建筑类型用 QToolButton 纯图标网格（5 列，56×56，iconSize 52），不可建造项置下方文本按钮分组 |
| 高亮语义 | 悬停=青色 `HOVER_COLOR=(80,200,255)`；选中=黄色 `SELECTION_COLOR`，alpha 150→180，外扩 2px 州轮廓提示 |
| emoji 图标 | 类型列表/工具按钮用 emoji 图标（如 👤💡🌳📜🔬🗺️）；控制台/测试里慎打 emoji（GBK，见 §5） |
| 中文名 | 按钮/实体名/修正名/本地化自动回显中文（mod 优先） |
| 深色专项 | BOP 用黑绿历史政治军事风（米白标题、金色棕色描边、深橄榄绿动作行）——深色风格需用户拍板 |
| 槽位网格 | 设计器槽位卡片垂直 label+按钮，自动换行；锁定槽灰色 🔒；空配件橙色提示 |
| 顶部下拉切换 | 编制/设计器用顶部 ComboBox 切换模板/国家/设计，而非左侧长列表 |

### 4.5 UI 分层要求

- UI 层只做控件/布局/语义信号；绘图逻辑进绘图层；数据变换进算法层；连线/写文件进信号槽层（§1.4）。
- 弹窗类对话框用 `exec()` 模态时要警惕测试阻塞（`ModulePickerDialog` 不能直接进测试，见 §5）。
- 信息展示坚持「点选/操作才刷新，悬停不刷详情」的既有交互（地图编辑器已确立）。

---

## 五、避坑指南

> 每条都是本项目真实踩过的坑；新代码前先扫一遍，避免重复踩。

### 5.1 环境 / 工具坑

- **当前模型/主 AI 无法读图**：`read_image` 会失败——验证界面用「截图 + 统计颜色数」
  （PIL `getcolors`）间接确认，或直接让用户看实际窗口；禁止产出预览截图（§4.1）。
- **控制台是 GBK（Windows）**：`print` emoji（✅❌✋）会 UnicodeEncodeError。
  跑脚本加 `python -X utf8`，或代码里 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`；
  `verify_contracts.py` 子进程已固定 `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` 规避。
- **GUI 测试用 offscreen**：`QT_QPA_PLATFORM=offscreen`（字体缺失警告可忽略）；
  需要真实字体渲染才用 `windows` 平台（窗口会短暂闪现）。
- **沙箱无外网直连**：访问 GitHub 需经 Clash 代理 `http://127.0.0.1:7890`
  （`git -c http.proxy=...` / `curl -x`）；**curl.exe 的 schannel 在沙箱会失败**，
  python urllib 设 `HTTP_PROXY`/`HTTPS_PROXY` 可用。
- **PyQt6 枚举位置**：`RenderHint` 在 `QPainter`；`QLineF` 在 `QtCore`；`QGraphicsItem.CacheMode`。
- **`np.save` 会自动补 `.npy` 后缀**：临时文件名必须带 `.npy` 结尾（如 `fp + ".tmp.npy"`）。

### 5.2 HOI4 文件事实

- 高度图文件名是 **`heightmap.bmp`**（不是 heights.bmp）；`terrain.bmp` 是地形类型图。
- **本地化 yml 带 BOM 是惯例**：`utf-8-sig + allow_bom=True`；脚本文件默认无 BOM。
- 科技图标三层结构：`common/technologies/*.txt`（无图字段）→ `interface/*.gfx`
  （sprite 名必须 `GFX_<科技id>_medium`）→ `gfx/interface/technologies/`（扁平目录，文件名任意）。
- 科技树 `path = {}` 是**树连线**（leads_to_tech），不是图标；全游戏 390 条 path 全部是连线。
- 建筑图标 strip 帧宽 = strip 宽 / `noOfFrames`（按建筑定义来源选图集）——
  **mod 与游戏的帧宽可能不同**（游戏 1426x46/31 帧=46px，3350890356 mod 1170x45/26 帧=45px），别硬编码。

### 5.3 解析 / 写回坑

- **`parse_pdx_text_to_nodes` 只返回顶层节点**：`equipments = { }` 包裹时必须递归
  （`_iter_blocks` 对 node 自身先检查再递归）；舰艇/飞机/坦克数据层都吃过这个亏。
- **大国家文件会提前截断**：`GER - Germany.txt` 等大文件必须用**字符级 `_block_ranges`**
  定位块（舰艇/飞机变体解析统一走 `parse_equipment_variants` 修复过）。
- **`tree_node` 把块内裸值解析成 key（value 为空）**：`51 204 51` 是三个 key；
  `victory_points = { 10 2 11 1 }` 需按 pid-points 配对解析。
- **国家文件是展开式**：`history/countries/*.txt` 顶层直接 `capital/create_equipment_variant`，
  无 TAG 包裹；TAG 从**文件名前缀**取（`JAP - Japan.txt` → JAP），异常名回退内容正则。
- **单行内联块要支持**：`modules = { slot = mod }`、`10 = { naval_base = 3 }` 行尾带 `}`——
  块匹配/替换必须同时支持多行块与单行内联块（`_block_map`、非行首匹配替换）。
- **写回纪律**：涉及游戏本体先 `ensure_file_in_mod` 复制到 mod，**绝不直写原版**；
  州/国家是整文件覆盖语义，复制全文安全；删除不存在对象返回 `None` 而非原内容（测试断言注意）。
- **dry_run 约定**：批量/结构操作默认 `dry_run=true`，只返回 `{files:[...]}` 预览，
  显式 `false` 才落盘（MCP 有 17 个默认 dry_run 工具）。

### 5.4 PyQt6 / UI 坑

- **`QPainter.drawPixmap` 没有 `(float, float, QPixmap)` 重载**：必须用 `drawPixmap(QPointF(...), pixmap)`。
- **`QWidget.updatesEnabled` 在 PyQt6 是方法不是属性**：`c.updatesEnabled()`。
- **QGraphicsView 默认 QFrame 边框 ~2px**：`grab()` 图像坐标 ≠ viewport 坐标
  （单像素采样会偏移到白边）——hover 高亮测试断言 `hover_item.pixmap()` 内容，不要 grab 像素。
- **`QTest.mouseMove` 不可靠**：构造的事件不带按键状态（模拟拖拽须手工构造 QMouseEvent
  带 `buttons=LeftButton`）；offscreen 多窗口时事件根本不投递（测试顺序敏感）——悬停模拟统一用
  `_send_move` helper（app.sendEvent + QMouseEvent）。
- **`ModulePickerDialog` 用 `exec()` 模态**：测试不得直接调用（offscreen 阻塞），
  直接改 upgrades/modules + 重建编辑器。
- **`QComboBox.addItem` 在 `blockSignals` 期间自动选中第 0 项**，随后 `setCurrentIndex(0)`
  索引未变不触发信号——初始化需手动补 `_on_combo_changed(0)`。
- 测试 patch `QInputDialog` 需指向 `PyQt6.QtWidgets.QInputDialog`（对话框内是方法级 import，模块级无该名字）。

### 5.5 测试坑

- 全量测试在 offscreen 下跑：`QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m unittest discover -s tests -t .`
- **第二个未关闭窗口**会导致事件不投递（测试顺序敏感）——用例里及时 close 对话框。
- **Windows 只读目录测试跳过**：契约测试里 POSIX 权限用例在 Windows skip。
- 测试素材：`E:\mods\3350890356`（542 科技、1493 州文件、完整地图）、
  `E:\mods\3228475937`（88 科技、无 states）、游戏本体
  `E:\SteamLibrary\steamapps\common\Hearts of Iron IV`。
- 无文件模式测试构造国家名需在 `game/common/country_tags` 写 `TAG = "countries/…"`
  （`scan_vanilla_countries` 只扫 country_tags/countries，不扫 history）。

### 5.6 地图渲染坑

- **QTransform 组合语义**：`scale(s,s).translate(-rx0,-ry0)` = 点先平移后缩放（`(p-r)*s`），
  写反会整体错位数百像素。
- **瓦片尺寸必须按设备像素计算**（w×dpr），否则高分屏（dpr>1）下缓存区小于视口会缺画面。
- **`_blend_border` 依赖小端 0xAARRGGBB 布局**（大端回退 QPainter）。
- **item paint 里 `clipBoundingRect()`/`option.exposedRect` 在 grab 场景不可靠**：
  `_paint_fill` 用设备尺寸反变换算可见范围。
- **瓦片位置跟随**：瓦片内容=渲染时视图下的设备像素，blit 时须把场景区原点经
  `worldTransform().map()` 投影到当前设备位置并四舍五入，否则平移时色块钉在原地。

### 5.7 settings.json 与数据单例

- **调试先读 `settings.json` 当前值**（mod_path / HOI4_path / ui_mode，地图可选键
  `map_zoom_threshold`=2.5、`map_zoom_settle_ms`=300、`map_initial_zoom`=1.3，经
  `read_map_settings()` 读取）——它反映用户真实环境；**如无必要不要改**；确需改先备份并在交付时说明。
- **无文件模式国家流程**：「选择国家」纯选择不写文件；「国家设置（复制/创建）」才是
  写操作——测试断言「选择后 mod 目录字节级快照不变」（`test_pure_select_does_not_write_files`）。
- 数据单例：`oob_map_editor.get_map_data / get_state_data`（按 mod+game 键缓存）。
- **方向别搞反**：`owner_province_map()` 返回 **tag→pids**；
  `country_overlay_pixmap` 需要 **pid→tag**。

---

## 附录 A · 常用命令速查

```bash
# 启动（Windows）
启动.bat
# 直接跑（Linux/WSL）
QT_QPA_PLATFORM=offscreen python src/main.py   # 仅冒烟/无窗口

# 全量验证（双版本各一遍，退出码 0 才通过）
.venv\Scripts\python.exe tools/verify_contracts.py            # Windows
/root/hoi4_builder_venv/bin/python tools/verify_contracts.py  # WSL

# 只跑契约测试（本机实测 510 用例，约 54s）
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m unittest discover -s tests -t .

# UI 覆盖缺口
python ui_gap_probe.py --max-files 5 --output docs/UI树形缺口检测报告.md
python ui_gap_probe.py --dump-all --output 已分析.md

# 静态门禁
python tools/check_write_discipline.py   # 写入纪律（AST 扫描直写）
python tools/check_layer_deps.py         # 四层依赖方向
python tools/check_file_budget.py        # 行数预算
```

## 附录 B · 文档体系（取代关系）

| 被取代 | 去向 |
| --- | --- |
| `AGENTS.md` | **已由本文档取代**；历史迭代已归档为 `docs/历史迭代日志.md`（索引见附录 H） |
| `README.md` | 精简版并入本文档；对外介绍入口已于 2025-08-25 重建为独立 `README.md`（README=对外概览，本文档=权威内部文档） |
| `docs/功能与实现文档.md` | 并入本文档第 2 节 |
| `docs/综合报告.md` | 数据并入本文档第 3 节 |
| `docs/环境搭建.md` | 并入本文档 §1.2 |
| `docs/验证契约.md` | 并入本文档 §1.7 / §3.2 / §5 |
| **保留为深度参考** | 见下表 |

| 参考文档 | 用途 |
| --- | --- |
| `docs/游戏文件内容详解.md` | 19 章 HOI4 机制/文件结构详解（国策/事件/地图/AI/本地化等），改专用 UI 前必查 |
| `docs/MCP与接口规格.md` | 159 个 MCP 工具、HTTP 端点、ApiCore 约定、dry_run 清单、Claude Code 配置 |
| `docs/整合计划.md` | **唯一执行总表**：B0~B3 进度、P1~P4 待办、需用户拍板清单 |
| `docs/科技图标存储规则.md` | 科技图标三层结构与实测数据（GFX 命名/尺寸/DDS 格式） |
| `docs/识图提示词.md` | 外部多模态模型识图规格（主 AI 不能读图时的协作流程） |
| `docs/学说识图.md` | 游戏内学说 UI 识图结论（大类→流派→分支→节点、经验值花费） |
| `docs/QIUQI-LIBRARY映射与复刻矩阵.md` | QIUQI 词条库/功能复刻状态表（3100+ 词条来源与映射） |
| `docs/RHoiScribe知识映射与补全.md` | RHoiScribe 外部工具的知识 A~M 补全映射与本项目吸收记录 |

> 更新约定：以后所有「改了什么 / 做到哪 / 踩了什么坑」按**开发流程**同步三处——
> ① 每轮迭代**必须**追加 `docs/历史迭代日志.md`（附录 E.3，强制）；
> ② 现状/结论只追加维护**本文档**（§2 模块表、§3.4 进度、附录 H 索引）；
> ③ 深度机制结论写入 `docs/游戏文件内容详解.md`；执行状态以 `docs/整合计划.md` 为准并回填本文档第 3.4 节。

## 附录 C · 支撑/辅助模块索引

> 第 2.1 节列的是核心功能模块；以下为未在正文逐一列出的支撑/辅助模块，按域分组，便于定位。
> 模块路径均相对 `src/`。

| 分组 | 模块（职责） |
| --- | --- |
| 顾问/兵种 | `advisor_assign_dialog.py`（1254 行，顾问分配识别与编辑，白名单大文件）、`fixed_field_recognizer.py`（固定字段识别） |
| 本地化/翻译辅助 | `gui_translator.py`（708，多源翻译核心）、`translation_widget.py`、`quick_loc_menu.py`、`quick_localisation_edit.py`、`translation_loader.py` |
| 实体资源 | `entity_resource_data.py` / `entity_resource_dialog.py`（批量本地化+图标+GFX 补全） |
| 图标/Gfx | `icon_ops.py`、`icon_resolver.py`、`icon_picker_dialog.py`、`icon_upload_dialog.py`、`icon_batch.py`、`interface_reg.py`、`dds_loader.py`、`dds_convert.py` |
| 模板/词条对话框 | `node_edit_dialog.py`、`node_find_dialog.py`、`node_search_dialog.py`、`custom_statement_dialog.py`、`term_dialog.py`、`template_dialog.py`、`template_manager_dialog.py` |
| 国策辅助 | `focus_parser.py`、`focus_processor.py`、`focus_base_builder.py`、`focus_package_gen.py`、`tree_info_dialog.py` |
| 内容生成/项目 | `content_generator_dialog.py`、`event_gen.py`、`idea_gen.py`、`ideology_gen.py`、`character_gen.py`、`general_gen.py`、`country_boot.py`、`mod_creator.py`、`mod_creator_dialog.py`、`project_wizard.py` |
| 配置/引导 | `setup_wizard.py`（首次配置向导）、`country_setup_dialog.py`（国家选择/创建）、`reference_panel.py`（游戏数据参考面板）、`api_gui_dialog.py`（GUI 内启停 API） |
| 通用组件 | `ui_widgets.py`（B0 公共组件）、`ui_untitled.py`（遗留 Form 壳，勿依赖）、`standalone_tool_dialogs.py`（PDX 格式化/DDS 转换/VP 本地化/错误日志工具窗） |
| 校验/工具算法 | `coverage_report.py`（文件类型覆盖报告）、`game_data.py`、`country_filter.py`、`error_log.py`（错误日志分析）、`pdx_format.py`、`pdx_sorter.py`、`vp_loc.py` |
| 通用 B2/B3 引擎 | `simple_block_editor.py`、`simple_entity_tab.py`、`nested_block_editor.py`、`nested_block_crud.py`、`generic_block_loaders.py`、`generic_nested_loaders.py`、`raw_block_editor.py`、`raw_block_loaders.py`（详见 §2.2） |

## 附录 D · 五大节之外的内容与去向（防遗漏清单）

> 本文档一~五节覆盖：功能架构 / 模块实现 / 数据与进度 / UI 原则 / 踩坑。
> **以下内容天然不属于这五类**，替换旧文档时若不显式保留会丢失——请按「去向」保留。

| 内容类别 | 说明 | 去向 |
| --- | --- | --- |
| **游戏机制详解** | HOI4 文件结构/字段语义/加载回退/机制坑（19 章），是"游戏知识"而非"本程序功能" | 保留 `docs/游戏文件内容详解.md` |
| **接口规格** | 159 个 MCP 工具逐条、HTTP 端点、dry_run 清单；本文档 §2.4 只有摘要 | 保留 `docs/MCP与接口规格.md` |
| **外部知识/工具映射** | QIUQI 词条矩阵、RHoiScribe 补全、识图提示词、学说识图、科技图标存储规则 | 保留对应 5 个 docs 文件 |
| **开发流程 How-to** | 新增内容类型四件套、模板/词条维护、测试/验证流程 | 见下方附录 E |
| **外部参考来源** | Scenario Forge（分析对象/方法论来源）、SF-ATS 验证契约模板 | 见下方附录 F |
| **用户素材（非源码）** | `常用代码/`、`游戏素材/` | 不入库，不随文档管理 |
| **历史迭代记录** | 原 AGENTS §6.1~§6.24 的过程日志/性能数字（非"现状"） | **已归档** `docs/历史迭代日志.md`，索引见附录 H |

## 附录 E · 如何扩展（开发流程 How-to）

### E.1 新增 / 改造一个内容类型的标准流程（四件套闭环）

1. **数据层 loader**：解析 + 写回（纯函数优先，遵守写入纪律 §1.5/§1.7，涉及游戏本体先 `ensure_file_in_mod`）；
2. **对话框**：专用 UI，或通用编辑器薄壳（`SimpleBlockEditorDialog` / `NestedBlockEditorDialog` / `RawBlockEditor` / `generic_tree_editor`，见 §2.2）；
3. **路由**：`content_types.py` 注册类型（要置顶就加 `SPECIAL_TYPE_KEYS`）→ `app_routes.py` 加路径分发 → workbench/文件树接线；
4. **验证闭环**：契约测试 + 真实数据冒烟 + 更新 `ui_gap_probe` spec 并 `--max-files 0` 收敛；
5. **双版本**：Windows `.venv` + WSL 各跑 `tools/verify_contracts.py`，退出码 0。

### E.2 维护模板 / 词条

- **系统模板**：`templates/系统模板/<类型>/基础模板.txt + 项目模板.txt`；
  新类型骨架用 `tools/gen_system_templates.py` 生成；新增分类需注册 `template_dialog.CATEGORIES`。
- **词条库**：`translations/*.json`；QIUQI 词条用 `tools/import_qiqi_terms.py` 导入；
  `term_registry.TERM_FILES` 末尾加载、同键冲突 QIUQI 胜出（`translate_key` 里为最低回退）。

### E.3 写入历史迭代（开发流程强制步骤）

> 每轮功能/修复/重构完成后，**必须**把本轮写入 `docs/历史迭代日志.md`，并回填
> `PROJECT_DOC.md` 与 `docs/整合计划.md`。这是交付定义的一部分，不是可选项。

**收尾清单（与 E.1 验证闭环同时执行）：**

1. 在 `docs/历史迭代日志.md` 文末追加新节（编号 6.x 序列，同日多批用 `6.xb`/`6.xc`）；
2. 节内容必须包含：用户要求/拍板 → 涉及模块与实现方式 → 关键数据/性能 → ⚠️ 踩坑/结论 → 验证结果；
3. 同步更新该文件文首的「历史迭代索引」表（# / 日期 / 主题 / 核心成果 / 现状对应）；
4. 同步更新 `PROJECT_DOC.md`：
   - §2.1/§2.2 模块实现表（新增/变化的功能）；
   - §3.4 执行进度里程碑；
   - 附录 H 历史迭代索引（新增一行）；
5. 若本轮涉及执行计划项，同步更新 `docs/整合计划.md` 状态表；
6. 新增节模板与完整清单见 `docs/历史迭代日志.md` 文末「维护流程」。

## 附录 F · 外部参考

- **Scenario Forge**：浏览器端 HOI4 地图编辑器（分析对象，克隆在 `E:\scenario-forge-main`）；
  本项目移植了它的工程方法论（原子写 / 健康检查 / 可执行契约 / 主题令牌）；
  它的 `AGENTS.md`（SF-ATS 验证契约）是本文档工程纪律的参考模板。
- **hoi4modutilities**（VSCode 扩展，位于 `E:\hoi4modutilities`，herbix/hoi4modutilities）：
  HOI4 mod 预览/模拟/查错工具（世界地图条件预览、事件树/GUI/MIO 预览、DLC 加载、地图校验）。
  本项目与其功能对比/缺口盘点见 §2.5。
- **关键旧文档**：`docs/验证契约.md`（写入纪律/契约清单，已并入 §1.7/§3.2/§5）、
  `docs/科技图标存储规则.md`（保留）、`docs/综合报告.md`（数据并入 §3）。

## 附录 G · 知识类内容索引（按主题查文档）

> 用途：想了解某个 HOI4 机制/接口/外部资料时，先查下表定位到具体文档与章节。
> 所有路径相对仓库根目录；这些文档**不属于** PROJECT_DOC 五大节，但作为知识库保留。

### G.1 主题 → 文档/章节 速查

| 想了解的内容 | 去这里 |
| --- | --- |
| PDX 脚本语言（键值/块/作用域/变量/AI 权重） | `docs/游戏文件内容详解.md` 一 |
| Mod 工程结构（.mod / descriptor / replace_path / 目录结构） | `docs/游戏文件内容详解.md` 二、三 |
| 国家/意识形态/国家颜色/化妆标签 | `docs/游戏文件内容详解.md` 四 |
| 国策/持续国策/共享国策 | `docs/游戏文件内容详解.md` 五；RHoiScribe 补全 H |
| 事件/决议/限时任务/MTTH | `docs/游戏文件内容详解.md` 六；RHoiScribe 补全 F、G |
| 理念/法案/内阁 | `docs/游戏文件内容详解.md` 七 |
| 角色/国家领袖/特质 | `docs/游戏文件内容详解.md` 八；RHoiScribe 补全 B |
| 科技/装备/变体 | `docs/游戏文件内容详解.md` 九 |
| 科技图标存储规则（三层结构/尺寸/实测） | `docs/科技图标存储规则.md` 全文 |
| 兵种/师编制模板 | `docs/游戏文件内容详解.md` 十 |
| 建筑/资源 | `docs/游戏文件内容详解.md` 十一 |
| 国家历史/州/OOB/顾问分配 | `docs/游戏文件内容详解.md` 十二（12.1~12.4） |
| 地图邻接/补给拓扑/TNO 行政区划 | `docs/游戏文件内容详解.md` 12.5、12.6 |
| 剧本（Bookmarks） | `docs/游戏文件内容详解.md` 十三 |
| 外交/政治：关系修正/战争目标/占领法/自治/BOP/派系/和会 | `docs/游戏文件内容详解.md` 十四 |
| AI 体系（战略/计划/模板/装备/海军/区域/战区/逆向 AI） | `docs/游戏文件内容详解.md` 十五 |
| 脚本化机制（effects/triggers/localisation/on_actions/动态修正/defines） | `docs/游戏文件内容详解.md` 十六；RHoiScribe 补全 A、E |
| 本地化/GFX/GUI/scripted GUI/音乐 | `docs/游戏文件内容详解.md` 十七；RHoiScribe 补全 J、K |
| 编码规范/常见错误/引用完整性/唯一标识 | `docs/游戏文件内容详解.md` 十八；RHoiScribe 补全 A-2、A-3 |
| 常用 trigger/effect/modifier 速查 | `docs/游戏文件内容详解.md` 十九 |
| HTTP API 端点 | `docs/MCP与接口规格.md` §3 |
| MCP 159 工具清单/域分布 | `docs/MCP与接口规格.md` §4 |
| dry_run 工具清单 | `docs/MCP与接口规格.md` §5 |
| MCP Server 运行与配置 | `docs/MCP与接口规格.md` §6、§7 |
| 外部多模态模型识图（界面/地图/设计器验收、UI 还原） | `docs/识图提示词.md` 一~八 |
| 学说界面识图结论 | `docs/学说识图.md` 全文 |
| QIUQI 词条库/二进制工具复刻矩阵/状态跟踪 | `docs/QIUQI-LIBRARY映射与复刻矩阵.md` 全文 |
| RHoiScribe 知识吸收/逐条映射/补全 A~M | `docs/RHoiScribe知识映射与补全.md` 全文 |
| 当前执行总表/待办/P1~P4 | `docs/整合计划.md`（状态回填本文档 §3.4） |
| 与 hoi4modutilities 功能对比 / 缺口盘点 | 本文件 §2.5 |

### G.2 各知识文档章节索引

**`docs/游戏文件内容详解.md`（19 章）**

| 章 | 内容 |
| --- | --- |
| 一 | 前置知识：PDX 脚本语言（基本元素/作用域/三大脚本元素/逻辑/变量/AI 权重） |
| 二 | Mod 工程结构（描述文件/内容目录） |
| 三 | 游戏目录总览 |
| 四 | 国家与意识形态 |
| 五 | 国策与持续国策 |
| 六 | 事件与决议 |
| 七 | 民族精神与理念 |
| 八 | 角色与国家领袖 |
| 九 | 科技与装备 |
| 十 | 兵种与师编制 |
| 十一 | 建筑与资源 |
| 十二 | 历史档：国家 / 州 / 初始部队 / 顾问 / 地图补给 / TNO |
| 十三 | 剧本（Bookmarks） |
| 十四 | 外交与政治机制（BOP/派系/和会等） |
| 十五 | AI 体系（含逆向 AI 策略） |
| 十六 | 脚本化机制（effects/triggers/localisation/on_actions/动态修正/规则） |
| 十七 | 本地化与界面资源（yml/GFX/GUI/scripted GUI/音乐） |
| 十八 | 编写规范与常见错误 |
| 十九 | 速查附录（trigger/effect/modifier） |

**`docs/MCP与接口规格.md`**：1 总览 → 2 架构与文件 → 3 HTTP API 端点 →
4 MCP 工具清单（159，域0~域10）→ 5 dry_run 工具清单 → 6 Server 运行 → 7 验证。

**`docs/科技图标存储规则.md`**：一 结论摘要 → 二 三层结构详解 → 三 图片规格（实测）→
四 五个 mod 实测证据 → 五 配图标操作清单 → 六 编辑器实现现状。

**`docs/识图提示词.md`**：一 通用界面截图验收 → 二 地图渲染验收 → 三 建筑图标按钮区 →
四 设计器界面验收 → 五 快速版 → 六 界面设计还原 → 七 输出约定 → 八 按 UI 评分清单识别。

**`docs/学说识图.md`**：1 界面整体布局 → 2 可见文本/按钮 → 3 元素层级与交互 → 4 图标/状态/数值细节。

**`docs/QIUQI-LIBRARY映射与复刻矩阵.md`**：1 整合总览 → 2 资料区映射（模板/词条/机制）→
3 二进制工具复刻矩阵（国策/国家/地图/通用/高级/AI）→ 4 优先级与批次 → 5 状态跟踪表 → 6 下一步建议。

**`docs/RHoiScribe知识映射与补全.md`**：一 逐条映射表 → 二 补全机制要点（A~M）→
三 落地链接 → 四 工具增强。

## 附录 H · 历史迭代索引

> 完整历史细节（含性能数据、决策过程、踩坑现场）见 **`docs/历史迭代日志.md`**（冻结归档）。
> 下表是快速索引；当前状态/待办以本文档 §3.4 与 `docs/整合计划.md` 为准。

| # | 日期 | 主题 | 核心成果 |
| --- | --- | --- | --- |
| 6.1 | 08-15 | 地图编辑器体验改进 | 滚轮防抖、多选、选区、1440×900 |
| 6.2 | 08-15 | 遗留问题 4 项 | 地图矢量填充 v2、OOB 迁 MapCanvas、阈值可调、SF 移植 4 子项 |
| 6.3 | 08-15 | 地图渲染缓存优化 | 瓦片缓存、边界烘焙（~300× 提速）、预览缩放、手型点选、高亮 |
| 6.4 | 08-15 | 建筑/国家色/三栏面板 | state/buildings/color 读写、建筑图标按钮 |
| 6.5 | 08-15 | 编制编辑器 v2 | 仿 Division Designer、数据层+UI 重构 |
| 6.6 | 08-15 | 舰艇设计器 | hull/modules/variants、原版自动落 mod |
| 6.7 | 08-15 | 飞机设计器 | airframe/modules/variants、字符级解析修复 |
| 6.8 | 08-15 | 坦克设计器 | chassis/modules/variants |
| 6.9 | 08-15 | 设计器模板 + 无文件入口 | design_templates/、工具菜单 4 项 |
| 6.10 | 08-15 | 无文件国家选择优化 | 纯选择/写操作分离（修误写 bug） |
| 6.11 | 08-15 | OOB 直开设计器 | open_oob_designer、军种识别拉起 |
| 6.12 | 08-15 | 工作台类型分组 | SPECIAL_TYPE_KEYS 置顶 |
| 6.13 | 08-15 | 动态修正模板 | 官方机制重写 |
| 6.14 | 08-15 | 舰/机设计器修正 | 槽位列、锁定槽、同款同步、内联块修复 |
| 6.15 | 08-16 | 地编州轮廓 + 图标区放大 | 州轮廓描边、56×56 图标 |
| 6.16 | 08-16 | BOP 专用工作台 | 数据层+深色 UI+本地化/修正 |
| 6.18 | 08-16 | AI 内容编辑器 | 8 类专用编辑器、战区联动 |
| 6.19 | 08-16 | AI 专用 UI + 固定侧边栏 | ai_ui_common、实体 CRUD |
| 6.20 | 08-18 | 四层分离重构 | focus_view 拆分、门禁、CI |
| 6.21 | 08-18 | src/ 包化 | 110 源码入 src/、project_paths |
| 6.22 | 08-19 | 本地化/QIUQI/实体资源/工具复刻 | 词条库、批量工具 |
| 6.23 | 08-22 | MCP 142 新工具 | ApiCore 9 Mixin、159 工具 |
| 6.23b | 08-22 | UI 修复与建构批次 1~9 | 设计器/角色/科技树/事件/科技/BOP 等 |
| 6.23c | 08-23 | 执行文档剩余缺口 + §0.x | 批次 4~8 完整版、变体高级字段 |
| 6.24 | 08-23 | Python 升级 3.14 | 3.8→3.14.5、GBK 根治 |
| — | 08-25 | B2/B3 批量铺开 + 学说编辑器 | 脚本库/MIO/派系/装备/学说等 |
| 6.25 | 08-25 | 与 hoi4modutilities 对比盘点 | 梳理 9 类功能缺口（预览/模拟/地图数据层/地图 QA/事件树/GUI/DDS/DLC/导出），登记为候选待办（§2.5） |
| 6.26 | 08-25 | DeepSeek 视觉识图工作流 | 用 `deepseek-v4-flash-vision-exp` 识图 MIO/学说 UI → 编辑器设计；工作流见 §2.6 |
| 6.27 | 08-25 | B3 P39 闭环：Mod 描述编辑器 + GUI/GFX 路由 | `mod_descriptor_loader`/`mod_descriptor_editor_dialog`（表单式 .mod 编辑）；`app_routes` 新增 descriptor.mod / interface / gfx 显式路由；ui_gap_probe 新增 4 类型 spec + 根目录扫描 |
| 6.28 | 08-25 | P2：兵牌图标接标牌库 | `unit_counter_library.find_counter_entry`（兵种→448 标牌，97% 覆盖）+ `unit_counter_icons`（QPixmap/QIcon）；`oob_map_editor`/`division_editor` GFX 失败回退标牌库，消除黑底占位 |
| 6.29 | 08-25 | P2：民族精神/意识形态专用 UI | `political_editor_data`（子块替换/列表/嵌套整块替换/分类插入）；意识形态表单编辑器（15 意识形态）；民族精神分类分组编辑器（1.4 万条按分类导航 + CRUD） |
| 6.30 | 08-25 | P2：地图数据层色阶 | `map_data_layers`（VP/资源色阶、补给区分色、铁路折线、河流近似线）+ 地图编辑数据层下拉 + `set_overlay_pos`；真实数据全层冒烟通过 |
