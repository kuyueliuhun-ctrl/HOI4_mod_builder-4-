# Scenario Forge 项目分析报告

> 分析对象：<https://github.com/raederhans/scenario-forge>（本地克隆 `E:\scenario-forge-main`，main 分支 HEAD `5461c24`）
> 分析日期：2026-08-15 ｜ 许可证：MIT ｜ 语言：JavaScript（前端）+ Python（构建/后端）+ Node（预览后端）

---

## 1. 项目概况

**定位**：基于浏览器的"剧本优先"（scenario-first）政治地图创作工作台，面向架空历史、HOI4/TNO 等策略游戏模组制作者和地缘叙事创作者。

- 公开演示：<https://raederhans.github.io/scenario-forge/>
- 内置 5 个公开剧本基线：Blank Map、Modern World、HOI4 1936、HOI4 1939、TNO 1962；另有 HGO 1936（开发者本地预览）
- 核心能力：政治涂色（ownership/controller/frontline 三视图）、外观样式（海洋/边境/地形/河流/城市灯光/昼夜）、战略标注（图例/战线/作战线/单位标牌）、交通工作台（公路/铁路/机场/港口/矿产/能源/工业/物流）、双语导出（EN/简体中文）、PNG/JPG 1x-4x 快照导出、可编辑项目 JSON、Cloud Saves/社区（本地后端预览）
- 仓库规模：15768 文件 / 约 1.1 GB（`data/` 13405 个文件是大头），星标 6，持续高频更新（分支含 `codex/audit-*` 流水线分支，全部由 Codex AI 代理驱动开发）

## 2. 仓库结构与技术栈

```
js/           328 个前端模块（无打包器，原生 ESM + vendored 依赖）
backend/      7   Node.js 社区/Cloud Saves 预览后端（app.js + 控制台助手）
map_backend/  7   Python 标准库 http.server 后端（routes/security/service/storage/store）
scenario_builder/  Python HOI4/HGO 数据导入管线（parser/models/compiler/crosswalk/audit/strategic）
map_builder/  79  Python 地图构建管线（分阶段 stage、拓扑、场景物化、发布服务、schema 契约）
tools/        148 构建/校验/测试编排脚本（含 AI 测试监督器、性能门禁）
data/         13405 场景产物 + 地理源数据 + 溯源台账（source_ledger.json / .provenance.json）
tests/        424 Node 行为测试 + Python 边界契约测试 + Playwright E2E
docs/         775 规划/归档/测试文档（含《HOI4 Map Maker 功能借鉴评估》）
dist/         399 已检入的 GitHub Pages 发布产物（含 drift 门禁校验）
.codex/       34  AI 代理预设（browser-debugger/code-mapper/python-pro/qa-expert/ui-fixer）+ ui-ux-pro-max 技能
qa/           23  每轮 AI 开发的质量审计报告（QA-085 ~ QA-101）
ops/          8   Playwright MCP 浏览器巡检脚本 + 性能基准
```

- 前端：原生 ESM（`import` 无打包器），`vendor/` 存放可直接 import 的 npm 依赖，`dist/` 由 `build_pages_dist.py` 生成并**检入仓库**，`verify:dist-drift` 用 `git diff --exit-code` 锁死源码与发布产物同步
- 语言：Python 侧 `from __future__ import annotations` + dataclass + 类型标注；JS 侧纯 ESM
- 双端测试：Node `node --test` + Python `unittest` + Playwright，各有几十个 npm script

## 3. 前端架构（无框架，纯 ESM 分层）

### 3.1 启动管线 `js/bootstrap/`（15 个模块）
`main.js` → boot overlay（启动遮罩与指标）→ `startup_data_pipeline` → 场景启动 → **deferred 分阶段加载**（`deferred_vendor_loader` / `deferred_ui_bootstrap` / `deferred_detail_promotion`）→ `post_ready_scheduler`（空闲期任务）→ `startup_ready_handoff`。整套启动流程带 `startup_failure_recovery`（失败恢复）、`main_runtime_diagnostics`（运行期诊断）、首帧指标埋点（`checkpointBootMetric("first-visible")`）。

### 3.2 状态机 `js/core/state/`（Flux 风格）
- `state.js` + 各域状态（`scenario_runtime_state` / `strategic_overlay_state` / `renderer_runtime_state` / `boot_state` …）
- **actions 目录**（`state/actions/*_actions.js`）把"动作"与"直接改状态"隔离；配套 ESLint 规则 `no-direct-state-mutation` + `state-writer-allowlist.json`，禁止绕过 action 直接改 state——**状态写入治理**
- 事务语义：`scenario_apply_pipeline` / `scenario_transaction_rollback_actions`（回滚）、`scenario_state_actions_atomicity`（原子性测试）、owner 权限（`*_owner_behavior.test` 类测试锁"谁拥有该状态"）

### 3.3 渲染管线 `js/core/renderer/` + `map_renderer/`（canvas，pass 制）
- **pass 目录**（`render_pass_catalog` / `render_pipeline_catalog` / `render_invalidation_catalog`）：边框网格、政治着色、河流、海洋、城市灯光、地形、战略覆盖层、特殊区域等各是一个 render owner
- **精确失效**：`exact_after_settle_scheduler`（"稳定后精确刷新"）、`render_pass_cache_host_owner`（pass 级缓存）、`render_pass_commit_accounting`（提交记账）、`render_invalidation_catalog`
- 性能：hit canvas 调度、DPR 感知失效、`transformed_frame_compositor`、`visible_frame_diagnostics`、spatial index（`spatial_query_index`）、Web Worker（`political_raster.worker.js`）
- 场景数据分块：`scenario_chunk_manager` + `political.detail.country.<tag>.json` 逐国块 + coarse 块，`chunk promotion` 提交可见帧

### 3.4 UI 层 `js/ui/`
- `toolbar/`：appearance 各 owner（边境/河流/城市点/纹理/参考图）、导出工作台、调色板库、场景上下文条、交通工作台（几十个 owner 模块）
- `sidebar/`：国家检查器、战略覆盖层、水域特殊区域
- `dev_workspace/`：开发者工作区（地区编辑器、场景文本编辑器、选择所有权）——相当于"编辑定义文件"的高级入口

### 3.5 核心服务 `js/core/`
`history_manager`（撤销）、`file_manager`（项目文件）、`data_service`（数据加载）、`palette_manager`、`legend_manager`、`i18n`（`i18n_catalog` + `locales.json`）、`dirty_state`（未保存提示）、`interaction_funnel`（导入/应用编排）、`sovereignty_manager`、`hgo_*`（自有投影模型/栅格渲染器/身份解析，验证 HOI4 风格国别身份）

## 4. HOI4 数据导入管线（对我们最有参考价值）

### 4.1 解析器 `scenario_builder/hoi4/parser.py`（606 行，正则 + 括号配对）
从游戏本体（`discover_hoi4_source_root` 自动找 Steam 安装目录）解析：

| 输入 | 输出 |
| --- | --- |
| `map/definition.csv` | 省 id → RGB → 省类型/地形/大陆（`DefinitionEntry`） |
| `history/states/*.txt` | 州 id、owner/controller、核心、VP、资源、建筑（`StateRecord`） |
| `common/bookmarks/*.txt` | 剧本名/日期/默认国家/推荐国家列表（`BookmarkRecord`） |
| `common/countries.txt` | tag → 国家文件映射 |
| `history/countries/*.txt` | 首都州 id（`CountryHistoryRecord`） |
| `common/victory_points` 本地化 | VP 名称（strategic.py） |

写法：`TAG_RE`/`DATE_BLOCK_RE` 正则 + `_find_matching_brace` 括号配对 + `_strip_comments` 去注释，`utf-8-sig` 容错读文件。只抽取所需字段，不追求完整 AST——工程务实。

### 4.2 交叉映射 `crosswalk.py` + 调色板
- `data/palettes/hoi4_vanilla.palette.json`（HOI4 国家色板）+ `data/palettes-maps/hoi4_vanilla.map.json`：**RGB → 国家 tag**
- `build_feature_indexes` / `assign_feature_owners` / `build_iso2_to_mapped_tag`：把 HOI4 tag（RGB 定义的省）映射到自有地理 feature（ISO2/名称索引）
- `build_country_registry`：国家注册表（tag、全名、色板、首都）

### 4.3 规则分层 `compiler.py` + manual rules（核心设计）
- **手动规则** `data/scenario-rules/hoi4_1936.manual.json`：人写规则（`include_country_codes` / `include_hierarchy_group_ids` / `include_feature_ids` / `exclude_*` / `base_iso2` / `lookup_iso2` / 颜色覆盖）
- **质量分级**：`direct_country_copy`（直接国家拷贝）→ `manual_reviewed`（人工复核）→ `approx_existing_geometry`（近似几何）→ `geometry_blocker`（几何阻断）——每个 feature 的归属都带质量标签
- **CRITICAL_REGION_IDS** 清单（东普鲁士、苏波、比萨拉比亚、外蒙古、陕西、满洲里边境…）——关键争议地区硬编码优先
- **1939 = 1936 的 delta 叠加**：`DEFAULT_OWNER_RULE_FILES_BY_SCENARIO["hoi4_1939"] = [1936 规则, 1939 规则]`，后者只写变更——**增量剧本模型**
- `compile_scenario_bundle` 产物：`countries.json` / `owners.by_feature.json` / `cores.by_feature.json` / `strategic_values.by_feature.json` / `capital_hints.json` + `audit.json`（溯源审计）+ 报告文件
- 场景输出带 `build_snapshot.json`（构建快照）、`manifest.json`、按语言拆分的 `geo_locale_patch.{en,zh}.json`、**启动 bundle**（`startup.bundle.{en,zh}.json.gz`，带字节预算 `STARTUP_BUNDLE_GZIP_BUDGET_BYTES`）、逐国政治块 `chunks/political.detail.country.<tag>.json`

### 4.4 其他 HOI4 资产导入
- `tools/import_hoi4_unit_counter_library.py` → `data/unit_counter_libraries/hoi4/`：**把游戏本体单位标牌 PNG 提取成图标库**（category_*.png / support_unit_*.png + manifest.json）
- `tools/import_country_palette.py`：国家色板导入
- `tools/materialize_hoi4_reichskommissariat_boundaries.py`：总督辖区边界物化

### 4.5 HGO（自有运行时）
`scenario_builder/hgo/`（compiler/vectorizer）+ `js/core/hgo_*`：自有投影模型、栅格渲染器、运行时预览——用来验证"HOI4 风格国家身份/色板/旗帜/渲染"的开发预览。

## 5. 数据治理与溯源（一条完整链条）

- `data/source_ledger.json` + 各源 `.provenance.json`（Natural Earth / geoBoundaries / GeoNames / NOAA ETOPO / NASA Black Marble / OSM / Geofabrik / 日本国交省 MLIT）
- `tools/build_source_ledger.py` / `check_source_ledger.py` / `source_governance_catalog.py` / `source_smoke_catalog.py`：台账生成与校验
- `tools/freeze_geoboundaries_sources.py` / `freeze_geonames_source.py`：**外部源快照冻结**（把第三方数据固定进仓库，避免上游漂移）
- `data/CATALOG.json` + `CATALOG.md`：数据目录；`check_data_catalog.py` 校验
- 构建产物带 `build_snapshot.json`，发布链路 `materialize`（生成）与 `publish`（发布）**严格分离**，检查点校验（`scenario_bundle_publish_service`）

## 6. 后端与社区预览

- `map_backend/`：纯 Python 标准库 HTTP 服务（**零第三方依赖**），sqlite 存储，会话 cookie + CSRF 头、密码哈希、管理员/版主/成员角色、保存/发布/评论/举报/审核路由（`routes.py` 全正则路由）
- `backend/`：Node.js 预览后端 + 控制台助手（`backend_console_helpers.js`），社区 DTO 白名单（`SHARED_PROJECT_FIELD_ALLOWLIST`）——**分享只暴露可重新导入的项目字段，账号/核销/本地私有运行时态留在后端**
- 启动：`start_backend_preview.bat`（本地 `.runtime/backend/` 存储）

## 7. 工程化与 AI 开发方法论（最大亮点）

### 7.1 SF-ATS 验证契约（AGENTS.md）
每次代码/测试改动必须：识别受影响域 → 自适应选择测试 → 子安全测试自动跑 → 主线程 Playwright 检查须先占 lane → **确定性证据优先于视觉印象** → 真实 bug 修复必须补回归测试 → 最终回复列出改动文件/命令/退出码/产物/跳过项/路由缺口/剩余风险。

### 7.2 AI 测试监督器 `tools/ai_test_supervisor/`
- `domain_registry.json`（域注册表）+ `build_change_dossier.mjs`（变更档案）+ `supervise_adaptive_verification.mjs`（监督自适应验证）
- 计划/档案/验证台账全部有 JSON Schema（`schemas/*.schema.json`）
- `run_adaptive_tests.mjs`：按 touched domain 选择测试子集

### 7.3 测试体系分层
- **owner 行为测试**（`*_owner_behavior.test.mjs`）：每个状态/渲染/交互模块锁"谁拥有它"
- **boundary 契约测试**（Python `test_map_renderer_*_boundary_contract.py`）：前后端边界双端锁
- **inventory/boundary 配对**：`*_owner_behavior + *_inventory_boundary` 成对出现
- E2E 分层：`e2e_layering.mjs run smoke/contract/regression/feature`，`test_route_registry.mjs` 路由注册
- 治理：`check_console_allowlist_decay`（控制台白名单衰减）、`test_timeout_guardrails`、`check_test_import_graph`、`check_architecture_boundaries`
- 性能：`perf:baseline` / `perf:gate`（阈值 1.15 回退检测）、`run_williams_crossover`（**跨 Windows 电源方案性能交叉验证**，C# 作业运行器 + PowerShell 电源方案切换）

### 7.4 .codex 代理预设
`browser-debugger` / `code-mapper` / `python-pro` / `qa-expert` / `ui-fixer` 五个子代理（GPT-5.4，workspace-write 沙箱，各自带 developer_instructions：先画执行边界 → 找根因 → 最小修复 → 验证一条成功路径+一条失败路径 → 报告剩余风险）；`ui-ux-pro-max` 技能内置 CSV 知识库（样式/排版/UX 规则）

### 7.5 《lessons learned.md》（579 行工程教训，核心条目）
- **canonical 输入只能有一份**：internal partial 当主输入，公开诊断文件和组合产物默认当输出；不从最终组合产物反推主输入
- **materialize 与 publish 必须分开**；UI 要"保存后立即可见"时显式串联两者
- **先按事务边界切逻辑**，再抽 service/materializer；入口函数理想状态只剩校验/锁/调用/提交/响应
- **锁语义覆盖真实并发模型**：owner-aware 锁至少建模 pid/thread/transaction
- merged state 区分"缺失"和"明确为空"（`hasOwnProperty` 判断）
- **render pass 维护单一生命周期**：依赖场景 mask/atlas/canvas 尺寸/DPR/baseline 的 pass 在对应输入变化时统一失效
- 性能优化先减阻塞边界（bundle 边界 → coarse preload → exact pass/mesh/hit canvas 缓存放可见集和 clean frame）
- 严格哈希的 JSON 必须在 `.gitattributes` 固定 `eol=lf`（Windows checkout 会破坏字节级契约）
- Windows 发布大 dist 先镜像到 `%TEMP%` 短路径再上传（Vercel CLI 长路径问题）
- 浏览器原生 zoom 是独立渲染输入（DPR 可能 <1 且被上下限钳制）
- 项目 ZIP 导入同时锁完整性（manifest 校验）和预算（体积/条目数/解压总字节）
- 文档纪律：active 目录只保留推进中的主线，完成的即归档

### 7.6 文档驱动开发
`docs/active/` 是"preflight 计划 → owner 提取 → inventory → boundary contract"的流水线文档；`qa/` 是每轮 AI 开发的质量审计报告（QA-085~101 编号连续）。

## 8. 竞品借鉴评估（他们自己做过这件事）

`docs/HOI4_MAP_MAKER_REFERENCE_2026-04-16/00_INDEX_AND_EVALUATION.md`：他们系统评估了 [HOI4 Fantasy World Map Maker](https://steamcommunity.com/sharedfiles/filedetails/?id=3707251866)（AmonStreeling/hoi4-mod-maker，从零生成完整 HOI4 地图 MOD 的工具），结论：

| 借鉴方向 | 评估 | 结论 |
| --- | --- | --- |
| 项目打包文件 | 参考价值很高 | 做（补齐 project file 资源缺口） |
| Project Health / 导出前检查 | 很高 | 做（已有 Diagnostics，缺产品化入口） |
| HOI4 donor 导入 | 很高/难度高 | 做（把工作台变成 mod 创作入口） |
| 启动页 + contextual hint | 高 | 做（提升冷启动成功率） |
| Quick Init 批量初始化 | 中高 | 做 |

原则：吸收对方 workflow 与"用户感知到的确定性"（我能开始/我知道下一步/我知道哪里有问题/我知道导出后能不能用），保留自身 scenario-first 架构。

## 9. 对我们 HOI4 Builder（PyQt6）的可借鉴点

**A. 数据/解析层**
1. **HOI4 规则分层 + 质量分级**：我们的游戏参考/覆盖编辑可引入 `direct/manual_reviewed/approx/blocker` 质量标签与 manual 规则文件（`include/exclude` + `lookup_iso2`），替代现在的隐式优先级
2. **delta 剧本模型**：1939 覆盖 1936 的"增量规则叠加"思路，直接对应我们 mod 覆盖原版（overwrite 文件）的场景——把"覆盖"建模成显式规则链
3. **definition.csv/state/bookmark 解析器**：他们的 parser 是"正则+括号配对+只取所需字段"的务实路线；我们的解析器已更完整，但可补 `discover_hoi4_source_root`（自动找 Steam 目录）和"RGB→tag 调色板映射"（做地图类功能时）
4. **单位标牌图标库**：`unit_counter_libraries` 的提取+manifest 结构，可对照我们的图标上传/GFX 管理做"图标库 manifest"
5. **关键地区硬编码清单**（CRITICAL_REGION_IDS）：我们的编辑校验可维护"高危 id 列表"（如必填焦点/科技链）

**B. 状态与工程**
6. **状态写入治理**：ESLint `no-direct-state-mutation` + allowlist 的思路 → 我们 PyQt 侧可做"所有模型修改必须走 Command/Service，加静态扫描"（undo 已有，缺的是写入纪律）
7. **事务边界先于 service**：编辑操作先定义完整事务输入/输出，再实现；回滚动作测试（`scenario_transaction_rollback_actions`）
8. **原子写**：`map_builder/io/writers.py` 的 `write_json_atomic`——我们已用 `write_file_utf8`，可补临时文件+rename 的原子语义
9. **materialize/publish 分离 + build_snapshot**：我们"导出 mod"与"写文件"可记录 build snapshot（来源文件 hash），供校验/回滚
10. **导出前检查（Project Health）**：他们从竞品借鉴的产品化入口——我们可做"导出前校验面板"（缺文件/格式错误/引用断裂清单），替代现在零散的校验对话框

**C. 测试与 AI 方法论**
11. **owner/boundary 契约测试配对**：为我们的核心模块（解析器/布局器/图标写入）建"行为测试+边界契约"双层，锁真实行为
12. **domain registry + 自适应测试选择**：我们 20+ 内容类型已有校验，可加"变更域 → 相关校验子集"的映射
13. **回归覆盖纪律**：bug 修复必配回归测试（我们现在靠人工验证）
14. **字节级契约**：我们写 mod 文件用 UTF-8 无 BOM；可补"严格校验时文件级 hash + LF 固定"（HOI4 对 BOM/CRLF 敏感，已在做）
15. **预算守卫**：启动 bundle 字节预算思路 → 我们导出产物可设体积/条目上限检查

**D. 产品**
16. **场景基线 + 项目 JSON 快照**：我们的"新建项目向导"可升级为"基线场景（1936/1939/TNO…）+ 增量编辑 + 可分享项目包（含校验和）"
17. **双语 i18n 治理**：他们 EN/ZH 双语的 key 审计、非翻译词规则——如果我们的编辑器要出中文版之外的语言可参考
18. **数据溯源台账**：我们编辑/上传（图标、GFX 写入）可记录 `.provenance`（来源文件、时间、hash），mod 出问题时能回溯

## 10. 一句话结论

Scenario Forge 是一个**无打包器 ESM 浏览器前端 + Python 分阶段构建管线 + 严格数据溯源 + AI 代理驱动工程化**的 HOI4 剧本地图编辑器；对它的分析价值不在"抄界面"，而在三点：**HOI4 数据的规则分层与增量剧本模型、状态写入与渲染失效的纪律、以及把工程教训写成可执行契约（SF-ATS/lessons learned）的方法**——这三样都能直接移植到我们的 PyQt6 builder 上。
