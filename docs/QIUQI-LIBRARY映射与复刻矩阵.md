# QIUQI-LIBRARY 映射与复刻矩阵（阶段 0 交付物）

> 建立时间：2026-08-19
> 用途：将 `E:\QIUQI-LIBRARY` 的知识、模板、词条与二进制工具映射到当前
> `hearts_of_iron_builder` 项目，明确每个条目的整合形态与复刻状态。
> 本文是后续所有整合/复刻工作的总索引，不包含原始二进制文件。

---

## 1. 整合总览

| 来源大类 | 当前项目落点 | 整合形态 |
| --- | --- | --- |
| 资料/基础代码/常用模板 | `templates/`、`docs/游戏文件内容详解.md` | 转内置模板 + 机制文档 |
| 资料/基础代码/代码提词 | 词条搜索、`custom_statement_dialog`、`term_registry` | 转结构化词条库 |
| 资料/基础代码/教程合集、特殊案例 | `docs/游戏文件内容详解.md` | 提炼机制结论 |
| 资料/高级代码 | `docs/游戏文件内容详解.md`、高级工作台 | 摘要/按需移植 |
| 资料/适配指南 | `docs/` | 摘要归档 |
| 工具（EXE/RAR/脚本） | `src/` 模块、`tools/` 脚本、菜单功能 | **在本项目复刻** |
| 工具/智能/RHoiScribe | `mcp_server.py` / `api_server.py` / AI 助手 | 调研后接入 |

---

## 2. 资料区映射

### 2.1 常用模板 → 内置模板

| QIUQI-LIBRARY 来源 | 当前项目模板/模块 | 状态 |
| --- | --- | --- |
| `资料/基础代码/常用模板/历史文件模板/OOB文件通用模板` | `oob_loader.py` / `initial_oob_editor.py` / `division_editor.py` / `ship_design.py` / `plane_design.py` / `tank_design.py` | 高优先，已部分覆盖，需补模板 |
| `资料/基础代码/常用模板/历史文件模板/开局部队和生产线设置（完全版）` | `oob_loader.py` / `initial_oob_editor.py` / `design_template.py` | 高优先，需转模板 |
| `资料/基础代码/常用模板/历史文件模板/国家history文件模板` | `country_history` 相关、`generic_tree_editor` | 待转模板 |
| `资料/基础代码/常用模板/脚本文件模板/国策模板/国策模板重制` | `focus_*`、`template_scheduler.py` | 高优先 |
| `资料/基础代码/常用模板/脚本文件模板/事件模板/事件及新闻模板` | 事件工作台 / `tools/event_generator.py`（拟） | 待复刻 |
| `资料/基础代码/常用模板/脚本文件模板/决议模板/两种决议模板和任务模板` | 决议工作台 / `generic_tree_editor` | 待转模板 |
| `资料/基础代码/常用模板/脚本文件模板/idea类模板` | idea / 民族精神工作台 | 待转模板 |
| `资料/基础代码/常用模板/脚本文件模板/人物与特质模板` | character / trait 工作台 | 待转模板 |
| `资料/基础代码/常用模板/脚本文件模板/AI模板/*` | `ai_loader.py`、`ai_*_editor_dialog.py` | 高优先，需对照补全 |
| `资料/基础代码/常用模板/脚本文件模板/科技 装备 学说 制造商 特殊工程模板/*` | 科技工作台、`ship/plane/tank_design*.py`、`design_template.py` | 高优先 |
| `资料/基础代码/常用模板/脚本文件模板/建筑模板` | `building_lib.py` / `state_build_ops.py` / 地图编辑器 | 已部分覆盖，需补模板 |
| `资料/基础代码/常用模板/脚本文件模板/地图类模板` | `map_*` / `map_region_ops.py` | 待转模板 |
| `资料/基础代码/常用模板/脚本文件模板/权力平衡模板` | `bop_loader.py` / `bop_editor_dialog.py` | 已覆盖，可补模板 |
| `资料/基础代码/常用模板/脚本文件模板/阵营模板/*` | 派系工作台（如未来实现） | 暂缓 |
| `资料/基础代码/常用模板/GUI或GFX模板` | `icon_ops.py` / `tech_icon_ops.py` / `icon_manifest.py` | 待转模板 |
| `资料/基础代码/常用模板/修正模板` | `term_registry` / `validation.py` | 转词条库 |
| `资料/高级代码/GUI/*`、`超事件模板`、`预设GUI` | 高级 GUI 工作台（调研后定） | 暂缓 |
| `资料/高级代码/definition/*` | `defines` 文档章节 | 文档归档 |
| `资料/高级代码/高级计算结合/*` | 语法/词条/校验增强 | 文档 + 词条 |
| `资料/适配指南/*` | `docs/` 适配章节 | 摘要归档 |
| `资料/基础代码/特殊案例/*` | `docs/游戏文件内容详解.md` 对应章节 | 高优先提炼 |

### 2.2 代码提词 → 词条库

| 来源 | 接入点 | 状态 |
| --- | --- | --- |
| `mod常用代码最新修订版2025.8.14.txt` | `term_registry` / 词条搜索 | 已完成（2026-08-19）→ `translations/qiqi_modcode_terms.json`（与 dream 修订合并） |
| `mod常用代码（dream修订）.txt` | 同上 | 已完成（2026-08-19）→ `translations/qiqi_modcode_terms.json`（共 939 条） |
| `TFR常用代码合集` / `TNO常用代码合集` | 同上 | 已完成（2026-08-19）分文件导入 → `translations/qiqi_tfr_terms.json`（50 条）/ `qiqi_tno_terms.json`（210 条） |
| `全学说汇总.txt` / `原版科技种类.txt` / `科技列表` | 科技词条 | 已完成（2026-08-19）→ `translations/qiqi_terms.json` |
| `装备类型汇总.txt` / `海军类别提词器.txt` | 设计器词条 | 已完成（2026-08-19）→ `translations/qiqi_terms.json` |
| `钢4国家精神代码.txt` / `国家外交关系修正代码` | idea / 修正词条 | 已完成（2026-08-19）→ 国家精神入 `qiqi_terms.json`；外交关系修正入 `translations/qiqi_diplo_terms.json`（11 条） |
| `钢4人物trait分类参考.txt` / `部分内阁特质提词器.txt` | character / trait 词条 | 已完成（2026-08-19）→ `translations/qiqi_terms.json` |
| `钢铁雄心4 指令代码.txt` | 指令词条 | 已完成（2026-08-19）→ `translations/qiqi_terms.json`（GBK 转码） |
| `本地化wiki.txt` | 本地化键提示 | 已完成（2026-08-19）→ 整理进 `docs/游戏文件内容详解.md` §17.1（文件命名/BOM/键值规则/replace/着色/嵌套/命名空间） |
| **QIUQI 词条库整合** | 词条库 | 已完成（2026-08-19）→ `tools/import_qiqi_terms.py` + `src/qiqi_term_import.py` → `translations/qiqi_terms.json`（1887 条）+ 4 个分文件词条库；`term_registry` 末尾加载，同键冲突以 QIUQI 为正确项目 |
| **实体配套资源工作台** | 批量本地化 + 图标 + 光效 | `src/entity_resource_data.py` / `src/entity_resource_dialog.py` / 工具菜单 | 已完成（2026-08-19） | 按文件/国家/全 mod 列出实体；表格批量编辑翻译；上传图标（复用 icon_ops）；一键补全缺失光效（已有不改，游戏内素材）；含「自动补光效」选项 |

> 导入前需统一格式：词条名、分类、适用文件、备注、来源、是否经游戏文件核实。

### 2.3 教程/特殊案例 → 机制文档

| 来源 | 目标章节 | 状态 |
| --- | --- | --- |
| `OOB文件通用模板` + `开局部队和生产线设置` | `docs/游戏文件内容详解.md` §OOB | 高优先 |
| `逆向AI策略简明教程.md` | AI 机制章节 | 高优先 |
| `TNO行政区划系统运作原理.md` | state / 高级机制章节 | 高优先 |
| `HOI4 派系系统说明文档` | 派系章节（未来） | 暂缓 |
| `P语言：从入门到弃坑`、`P语言：兼容性导论` | 语法章节 | 文档摘要 |
| `00_defines.lua文件教程` + 分类解析 | defines 章节 | 中优先 |
| `使用 Python 将 Paradox 脚本文件解析.md` | 解析器设计笔记 | 文档摘要 |
| `GUI系列教程` / `超事件模板` / `Shader 教程` | 高级代码章节 | 暂缓 |

---

## 3. 二进制工具复刻矩阵

> 状态说明：
> - **已覆盖**：现有项目已实现等价或更优功能
> - **需复刻**：尚未实现，计划在项目内新建/扩展
> - **合并增强**：现有模块已有雏形，需按该工具补齐能力
> - **暂缓**：复杂度高/依赖外部能力/优先级低
> - **保留外部**：不适合复刻，仅记录路径

### 3.1 国策类

| 原始工具 | 核心功能 | 当前项目 | 状态 | 复刻计划 |
| --- | --- | --- | --- | --- |
| HOI4 0代码国策树制作工具 | 国策树可视化生成 | `focus_view.py` / `focus_*` | 已覆盖 | 不重复实现，提取缺失能力 |
| HOI4.Focus.Editor v1.0.3 | 国策树编辑 | `focus_view.py` / `focus_parser.py` | 已覆盖 | 不重复 |
| 国策图标自动化设定工具 | 图标批量设置 + gfx 注册 | `icon_ops.py` / `focus` 图标链 | 合并增强 | 补批量图标/注册流程 |
| 国策图片快捷选择与代码装入 | 图片选择 + 代码写入 | `icon_picker_dialog.py` / `icon_upload_dialog.py` | 合并增强 | 补批量选择/装入 |
| 国策图标及本地化注册工具（FTAT） | 图标注册 + 本地化 | `icon_ops.py` / `tech_icon_ops.py` / `localization_mgr.py` | 合并增强 | 补一键注册 |
| 国策图标注册（含shine）工具 | shine 图标注册/转换 | `icon_ops.py`（`upload_icon` 已生成 `_shine.dds` + 注册 gfx） | **已覆盖** | 不单独复刻；如需批量可补批量图标流程 |
| 国策树相关文件自动生成整合工具（FTAT） | 自动生成国策全套配套文件（图标GFX/光效GFX/本地化） | `entity_resource_data.py` / `entity_resource_dialog.py` | 已完成（2026-08-19） | 已克隆 E:\FTAT 分析；配套资源工作台承担「批量本地化 + 图标 + 只补缺失光效 GFX」 |

### 3.2 国家类

| 原始工具 | 核心功能 | 当前项目 | 状态 | 复刻计划 |
| --- | --- | --- | --- | --- |
| 民族精神编辑器 | idea 编辑/生成 | idea 工作台（通用树）+ `src/idea_gen.py` | 需复刻（生成器已完成 2026-08-19） | `tools/content_generators.py ideas`；编辑仍复用树编辑器 |
| （子）意识形态生成器 | 意识形态代码生成 | `country_setup_dialog.py` / `src/ideology_gen.py` | 需复刻（生成器已完成 2026-08-19） | `tools/content_generators.py ideology` |
| idea 排列叠加生成器 | idea 图标/排列生成 | — | **不做** | 用户拍板：不制作（2026-08-19） |
| 事件框架及图片注册一键生成器 | 事件框架 + 图片注册 | 事件工作台 + `src/event_gen.py` / `src/icon_batch.py` | 需复刻（已覆盖 2026-08-19） | 事件生成器 + 图标批量注册可组合 |
| Character 生成器系列 | 人物代码生成 | `src/character_gen.py` + `src/character_data.py` / `src/character_editor_dialog.py` | 需复刻（已完成 2026-08-19） | 生成器 `content_generators.py character` + 专用 UI（工具菜单「👤 角色编辑器」） |
| 钢4将领代码批量生成器 | 将领批量生成 | `src/general_gen.py` | 需复刻（已完成 2026-08-19） | `tools/content_generators.py general` |
| 钢铁雄心4舰船生成器 | 舰船代码生成 | `ship_design.py` / `ship_design_dialog.py` | 已覆盖 | 不重复，可补批量生成 |
| 批量创建国家 Tag 工具 | 国家目录/文件/引用创建 | `country_setup_dialog.py` / `src/country_boot.py` | 已完成（2026-08-19） | `tools/content_generators.py country` |
| P社游戏旗帜创建器 | 旗帜图像生成 | 无 | 暂缓 | 图像算法复杂，先调研 |
| 旗帜转换工具 | 旗帜格式转换 | 无 | 暂缓 | 同上 |
| 旗帜处理 | 旗帜处理 | 无 | 暂缓 | 同上 |

### 3.3 地图类

| 原始工具 | 核心功能 | 当前项目 | 状态 | 复刻计划 |
| --- | --- | --- | --- | --- |
| MapGen v2.2 | 地图生成/编辑 | `map_loader.py` / `map_canvas.py` / `map_editor_dialog.py` | 已覆盖大部分 | 提取缺失算法 |
| HOI4MapMaker | 地图可视化编辑 | 同上 | 已覆盖大部分 | 不重复 |
| StateRS | state 排序 | `state_loader.py` / `map_region_ops.py` / `pdx_sorter.py` | 已完成（2026-08-19） | `tools/pdx_sorter.py sort` |
| 省份排序器 | province 排序 | `map_region_ops.py` / `pdx_sorter.py` | 已完成（2026-08-19） | `tools/pdx_sorter.py sort` |
| 省份部署（缩进修复版） | province 部署/缩进 | `map_region_ops.py` / `pdx_parser.py` / `pdx_sorter.py` | 已完成（2026-08-19） | `tools/pdx_sorter.py deploy` |
| 战略区域创建 | strategicregion 创建 | `map_region_ops.py` / `region_editor_dialog.py` | **已覆盖** | region_editor_dialog 已支持框选划分 strategicregions/supplyareas/states（调研确认 2026-08-19） |
| 地图建筑批量修改脚本 | 州建筑批量写 | `state_build_ops.py` / `building_lib.py` | 合并增强 | 批量命令/工具菜单 |
| 地图人力放置程序 | 州人力批量写 | `state_build_ops.py` | 合并增强 | 批量命令 |
| 地图战略资源放置程序 | 资源批量写 | `state_build_ops.py` | 合并增强 | 批量命令 |
| 地图文件划分大洲 | 按大洲划分地图文件 | `map_region_ops.py` | 需调研 | 待读原输出格式 |
| 胜利点本地化生成器 | VP 本地化生成 | `localization_mgr.py` / `src/vp_loc.py` | 已完成（2026-08-19） | `tools/vp_loc.py` |
| 省份编辑器（在线） | 省份编辑 | `map_editor_dialog.py` | 已覆盖 | 不重复 |

### 3.4 通用类

| 原始工具 | 核心功能 | 当前项目 | 状态 | 复刻计划 |
| --- | --- | --- | --- | --- |
| HOI4 0代码本地化编辑器 | yml 键值编辑/生成 | `translation_editor.py` / `translation_loader.py` / `localization_mgr.py` | **已覆盖** | 已是现有核心能力，不单独复刻；如缺批量表格导入再评估 |
| HOI4 0代码事件生成器 | 事件模板生成 | 事件工作台 / 模板 / `src/event_gen.py` | 已完成（2026-08-19） | `tools/event_generator.py` |
| HOI4 0代码文本格式化工具 | PDX 格式化/缩进 | `pdx_parser.py` / `pdx_format.py` | 已完成（2026-08-19） | `tools/pdx_formatter.py` |
| HOI4 图标GFX自动化生成工具 | spriteType 自动生成 | `icon_ops.py` / `tech_icon_ops.py` / `icon_manifest.py` | 合并增强 | 补批量注册 |
| HOI4 错误日志分析工具 | 解析游戏错误日志 | `src/error_log.py` / `tools/error_log_analyzer.py` | 已完成（2026-08-19） | 含子系统归类 `classify_by_subsystem` |
| interface 注册 | GUI/GFX 注册 | `src/interface_reg.py` | 已完成（2026-08-19） | 合并增强 |
| 本地化生成（IRIS） | 批量生成本地化 | `translation_editor.py` / `localization_mgr.py` / `validation.py` | **已覆盖（重叠）** | 现有“一键补写本地化/缺失检测”已覆盖批量生成；待验证其特有功能后再决定是否增强 |
| MOD文件夹生成 | 创建 mod 目录结构 | `mod_creator_dialog.py` / `project_wizard.py` | 已覆盖 | 不重复 |
| 文件夹比较器 | mod/原版差异 | `overlay_rules.py` / `overlay_report_dialog.py` | 已覆盖 | 可补命令行版 |
| 批量填鸭工具（AOR） | 表格批量生成代码 | `template_scheduler.py` / 词条库 → `src/batch_fill.py` / `tools/batch_fill_generator.py` | **已完成（2026-08-26）** | 已分析 xls 结构（normal/shine/将领）并实现列表驱动模板批量生成器（6.54） |
| HoI4ModdingPythonScripts | 多个 Python 小工具 | `tools/` | 需复刻 | 逐一审查移植 |
| 电台生成 python 脚本 | 电台文件生成 | 无 | 暂缓 | 需调研 |
| 电台系列工具 | OGG 转换/文件生成 | 无 | 暂缓 | OGG 依赖外部编码器，文件部分可脚本化 |
| 批量转 dds | DDS ↔ PNG | `dds_loader.py` / `src/dds_convert.py` | 已完成（2026-08-19） | `tools/dds_convert.py`（DDS→PNG） |
| 图像批处理系统（PS 插件） | PS 批量处理 | 无 | 暂缓 | 外部插件，保留 |
| 系统预览插件 | 资源缩略图 | `dds_loader.py` / 图标库 | 保留外部 | 系统级插件不入库 |
| 大众脸生成器 | 大众脸/人脸生成 | 无 | 保留外部 | GitHub 外部（`工具/通用/…大众脸生成器.url`），人脸生成依赖外部引擎/素材 |
| VModer 代码插件 | VSCode 插件 | `custom_statement_dialog.py` / 词条 | 调研 | 可借鉴词条/语法提示 |

### 3.5 高级类

| 原始工具 | 核心功能 | 当前项目 | 状态 | 复刻计划 |
| --- | --- | --- | --- | --- |
| Shader 编辑器 | HLSL shader 编辑 | 无 | 保留外部 | 编辑器重，仅文档 |
| 彩虹图（帧图）拼接工具 | 帧图拼接 | 无 | 暂缓 | 图像算法，先调研 |
| 自生成 GUI 决议包 | 滑条决议 GUI 全套生成 | 高级模板 / `template_scheduler.py` | 需复刻 | `tools/gui_decision_generator.py`（先出模板） |
| 钢铁雄心4议会 GUI 生成器 | 议会图 GUI 生成 | 无 | 暂缓 | 复杂，先调研 |
| HOI4DEV | 高级开发工具集 | `api_server.py` / `mcp_server.py` / 工具菜单 | 调研 | 参考能力清单 |
| 核心圈层工具 | 核心圈层生成 | 无 | 需调研 | 先反推输出 |

### 3.6 智能/AI 类

| 原始内容 | 类型 | 当前项目 | 状态 | 计划 |
| --- | --- | --- | --- | --- |
| RHoiScribe | MCP + Skill | `mcp_server.py` / `api_server.py` + 知识吸收 + 工具接口 | 已完成吸收（2026-08-19） | 已克隆 E:\RHoiScribe 通读；知识映射进 `docs/RHoiScribe知识映射与补全.md`；接口新增 format_pdx/vp_loc/error_log/register_icon_batch；error_log 增子系统归类 |
| AI 相关模板/逆向 AI 教程 | 知识 | `ai_loader.py` / `ai_*_editor_dialog.py` | 高优先 | 转模板 + 文档 |

---

## 4. 复刻优先级与批次

### 第一批：高价值纯脚本/批量类（优先执行）

| 序号 | 复刻项 | 建议实现 |
| --- | --- | --- |
| 1 | 事件生成器 | `tools/event_generator.py` |
| 2 | PDX 文本格式化 | `tools/pdx_formatter.py` |
| 3 | 图标 GFX 自动化注册 | 增强 `icon_ops.py` / `tech_icon_ops.py` |
| 4 | 州建筑/人力/资源批量写 | 增强 `state_build_ops.py` + 工具命令 |
| 5 | 批量 DDS 转换 | `tools/dds_convert.py` |
| 6 | 胜利点本地化生成 | `tools/vp_localisation_generator.py`（仅此生成器不是通用编辑，仍保留） |
| 7 | 省份/州排序与部署 | `tools/state_sorter.py` / `tools/province_sorter.py` / `tools/province_deploy.py` |

### 第二批：编辑器/工作台类（需 UI 确认）

| 序号 | 复刻项 | 建议实现 |
| --- | --- | --- |
| 1 | 民族精神/意识形态生成器 | idea 专用编辑器或 `tools/idea_generator.py` |
| 2 | 人物/Character 生成器 | `tools/character_generator.py` + 专用 UI |
| 3 | 将领代码批量生成器 | `tools/general_generator.py` |
| 4 | 批量创建国家 Tag | `tools/country_bootstrap.py` |
| 5 | 国策全套文件生成器 | `tools/focus_package_generator.py` |
| 6 | 错误日志分析 | `tools/error_log_analyzer.py` + 结果对话框 |
| 7 | 战略区域创建增强 | `map_region_ops.py` + 框选生成 |
| 8 | 地图大洲划分 | `tools/continent_splitter.py` |

### 第三批：调研/暂缓

- 旗帜创建/转换/处理
- 议会 GUI 生成器
- Shader 编辑器
- 电台工具
- 彩虹图拼接
- 核心圈层工具
- ~~批量填鸭 xls~~ ✅（2026-08-26，`src/batch_fill.py`）
- VModer / HOI4DEV 参考借鉴
- 自生成 GUI 决议包（可先做模板再决定是否脚本化）

---

## 5. 状态跟踪表

> 每完成一项，将状态更新为 `已完成` 并填写实现位置/PR/说明。

| 条目 | 来源 | 复刻/整合位置 | 状态 | 备注 |
| --- | --- | --- | --- | --- |
| OOB 模板与机制文档 | QIUQI-LIBRARY 资料 | `docs/游戏文件内容详解.md` / `templates/` | 待开始 | 高优先 |
| AI 策略模板与文档 | QIUQI-LIBRARY 资料 | `docs/游戏文件内容详解.md` / `ai_*` | 待开始 | 高优先 |
| 本地化生成器 | `工具/通用/本地化生成` | 现有 `translation_editor.py` / `validation.py` | 已覆盖（重叠） | 待验证特有功能后决定是否增强 |
| 本地化编辑器（全量/修正词条） | 需求补充 | `src/localisation_editor_data.py` / `src/localisation_editor_dialog.py` / 工具菜单+工具栏 | 已完成（2026-08-19） | 套用词条管理 UI；支持搜索/新增/编辑/删除/只看修正 |
| 本地化批量补写 + 多语言 | 需求补充 | `src/localisation_editor_data.py` / `src/localisation_editor_dialog.py` | 已完成（2026-08-19） | 默认中文；英文可选；批量补写缺失词条 |
| 快速本地化编辑小窗口 | 需求补充 | `src/quick_localisation_edit.py` / `src/generic_tree_editor.py` | 已完成（2026-08-19） | 右键当前键弹小窗编辑，不跳转本地化编辑器 |
| 本地化词条分类筛选 | 需求补充 | `src/localisation_editor_data.py` / `src/localisation_editor_dialog.py` | 已完成（2026-08-19） | 下拉框分类：国策/决议/事件/理念/科技/修正/人物/界面/其他 |
| 各专用编辑器右键快速本地化 | 需求补充 | `src/quick_loc_menu.py` / `division/ship/plane/tank/AI*/bop_editor_dialog.py` | 已完成（2026-08-19） | 编制/设计器/AI/编制下拉与列表右键弹小窗；BOP 名称+描述 |
| 事件生成器 | `工具/通用/HOI4 0代码事件生成器` | `src/event_gen.py` / `tools/event_generator.py` | 已完成（2026-08-19） | 第一批 |
| PDX 格式化 | `工具/通用/HOI4 0代码文本格式化工具` | `src/pdx_format.py` / `tools/pdx_formatter.py` | 已完成（2026-08-19） | 第一批 |
| 图标 GFX 自动化 | `工具/通用/HOI4 图标GFX自动化生成工具` | `src/icon_batch.py` | 已完成（2026-08-19） | 第一批（批量补缺失注册） |
| 州批量写 | `工具/地图/地图建筑/人力/资源` | `src/state_batch.py`（复用 state_build_ops） | 已完成（2026-08-19） | 第一批 |
| DDS 转换 | `工具/通用/批量转dds` | `src/dds_convert.py` / `tools/dds_convert.py` | 已完成（2026-08-19） | 第一批（DDS→PNG） |
| VP 本地化 | `工具/地图/胜利点本地化生成器` | `src/vp_loc.py` / `tools/vp_loc.py` | 已完成（2026-08-19） | 第一批 |
| 州/省排序与部署 | `StateRS`/`省份排序器`/`省份部署` | `src/pdx_sorter.py` / `tools/pdx_sorter.py` | 已完成（2026-08-19） | 第一批 |
| interface 注册 | `工具/通用/interface 注册` | `src/interface_reg.py` | 已完成（2026-08-19） | 合并增强 |
| 错误日志分析 | `工具/通用/HOI4错误日志分析工具` | `src/error_log.py` / `tools/error_log_analyzer.py` | 已完成（2026-08-19） | 第二批 |
| 地图大洲划分 | `工具/地图/...` | `tools/continent_splitter.py` | 需调研 | 待读原输出格式 |
| 国策全套生成 | `工具/国策/国策树相关文件自动生成整合工具` | `src/focus_package_gen.py` / `tools/content_generators.py focus` | 已完成（2026-08-19） | 树+本地化+图标 GFX 文本 |
| 国家批量创建 | `工具/国家/批量创建国家Tag` | `src/country_boot.py` / `tools/content_generators.py country` | 已完成（2026-08-19） | 历史文件+tag 行+本地化 |
| 角色/将领生成 | `工具/国家/人物工具` | `src/character_gen.py` / `src/general_gen.py` | 已完成（2026-08-19） | `tools/content_generators.py character / general` |
| RHoiScribe | `工具/智能/RHoiScribe` | MCP/API + 知识吸收 | 已完成（2026-08-19） | 知识映射与补全文档 + 接口/工具增强 |

---

## 6. 下一步建议

> **未完成条目的唯一总表 = `docs/整合计划.md`**（整合本矩阵未完成行 +
> `docs/RHoiScribe知识映射与补全.md` 剩余主题 + `docs/历史迭代日志.md 附录：6.17` 遗留，按 P0~P4 批次编排；
> 含需用户拍板清单）。第一、二批与 RHoiScribe 已全部落地，剩下以「需调研 / 需转模板文档 /
> 专用 UI（待拍板）」为主。完成某项时：改本矩阵对应状态 + 同步 `未完成计划.md`。

> 本文件后续随复刻进度持续更新。