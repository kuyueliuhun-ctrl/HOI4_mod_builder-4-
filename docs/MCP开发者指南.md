# MCP 开发者指南 — HOI4 Mod 编辑器

> 适用角色：**开发者（Developer）** —— 扩展/维护 MCP 工具注册表、schema、校验器、
> 模板与文档的工程人员或 AI Agent。
> 本文档与 `docs/MCP用户指南.md` 结构一致，便于整合。
> 权威实现：`src/mcp_tools.py::build_tools()`；校验器：`src/mcp_validator.py`。

---

## 目录（TOC）

1. [角色与范围](#1-角色与范围)
2. [工具分类速览](#2-工具分类速览)
3. [正确范式（按工具类型分类）](#3-正确范式按工具类型分类)
4. [踩坑索引](#4-踩坑索引)
5. [模板与回归测试](#5-模板与回归测试)
6. [工作流程](#6-工作流程)
7. [校验器与自动化拦截](#7-校验器与自动化拦截)
8. [关联文档](#8-关联文档)

---

## 1. 角色与范围

- 本文档面向 **MCP 开发者**：在 `src/mcp_tools.py` 注册/修改工具，在 `src/mcp_validator.py`
  维护规则，在 `templates/mcp/` 沉淀调用模板，在 `docs/` 维护知识文档。
- 扩展 MCP 的硬性纪律：
  - **禁止另起实现**：所有工具 handler 必须复用 `ApiCore`（`src/api_server.py`），
    MCP/HTTP/CLI 共用同一操作核心；
  - **写回纪律**：写路径必须走 `write_utils.atomic_write_text`（或数据层原子写），
    接口层禁止 `open(path, "w")`；本地化 yml 用 `utf-8-sig`；
  - **原版保护**：涉及游戏本体的写操作先 `ensure_file_in_mod` 复制到 mod；
  - **dry_run 约定**：批量/结构操作默认 `dry_run=true`；
  - **行数预算**：`src/*.py` 默认 ≤1200 行，超限需白名单并拆分。

## 2. 工具分类速览

| 分类 | 说明 | 注册位置/要点 |
| --- | --- | --- |
| `core` | 基础工具回退分类 | `_existing_tools` + `_rho_tools` 未登记分类默认 core |
| `states-map` | 州/省/区域/颜色 | `_domain1_tools` |
| `designers` | 舰艇/飞机/坦克设计器 | `_domain2_tools` |
| `oob` | 师编制/OOB/兵种 | `_domain3_tools` |
| `ai` | AI 内容 8 类 | `_ai_tools`（动态 schema 生成） |
| `bop` | 力量平衡 | `_domain5_tools` |
| `localisation` | 本地化/词条 | `_domain6_tools` + `write_localisation` |
| `health` | 校验/健康/撤销/覆盖 | `_domain7_tools` + `_rho_tools` + CWT |
| `symbols` | 符号/定义/引用/补全 | `_rho_tools` |
| `media` | 图标/DDS/标牌/GUI GFX | `_domain8_tools` + `_rho_tools` |
| `generators` | 内容生成器 | `_domain9_tools` |
| `project` | 新建 mod/模板/国家文件 | `_domain10_tools` |
| `agent` | Agent 偏好/审计 | `_agent_tools` |
| `debug` | 调试启动 | `_rho_tools` |
| `nav` | 导航工具 | `NAV_TOOLS_META` / `mcp_server._build_nav_tools` |

新增分类时同步维护 `_CATEGORY_TOOLS`、`CORE_TOOLS`、`docs/MCP与接口规格.md §4`、
`docs/MCP用户指南.md`、`docs/MCP开发者指南.md`。

## 3. 正确范式（按工具类型分类）

### 3.1 工具注册

- 工具结构必须为：
  ```python
  _tool(name, description, inputSchema, handler)
  ```
  - `name` 全局唯一，小写下划线，禁止与既有工具冲突；
  - `description` 非空，中文，说明用途 + 正确范式（dry_run/approved/路径约束）；
  - `inputSchema` 为 `{"type":"object","properties":{...},"required":[...]}`；
  - `required` 只列真正必填项；所有 `required` 中的 key 必须出现在 `properties`；
  - `handler` callable，dict 进 dict 出；业务错误抛 `ValueError`（HTTP 400 / MCP 错误文本）。

### 3.2 schema 正确范式

| 场景 | 必须写进 schema |
| --- | --- |
| 写类/批量/生成工具 | 提供 `dry_run` 布尔参数，description 注明“默认 dry_run” |
| `create_mod` | `mod_folder_path*`；`dry_run`；`approved`；description 写“dry_run=false 时须 approved=true” |
| AI CRUD | `create/update/delete` 必填 `id`；`rename/duplicate` 必填 `id`+`new`；`ai_navy_*` 必填 `section` |
| 生成器 | 附加 `examples` 字段，含最小可运行入参 |
| 文件路径参数 | description 写“mod 内相对路径”，禁止绝对/`..`/盘符 |
| 可选参数 | description 末尾标注“（可选）” |

### 3.3 handler 正确范式

- 先 `path_safety` 校验，再进入数据层；
- 返回结构包含 `ok` / `files` / `dry_run` 等可读字段；
- 写方法结束后清对应缓存并 `_notify_change(path)`；
- 不要吞掉 `ValueError`，让调用方可读。

## 4. 踩坑索引

- 全项目踩坑索引见 **`docs/踩坑索引.md`**；开发前先读对应类别。
- MCP 开发者高频坑：
  1. 新增工具忘记登记 `_CATEGORY_TOOLS` → 工具掉进 `core`，A+B 分类混乱；
  2. schema 与 handler 的必填不一致 → `tests/test_mcp_validator.py` 拦截；
  3. 写工具漏 `dry_run` → 冒烟会按写工具跳过，且用户可能误落盘；
  4. 文件路径没走 `path_safety` → P0-3 安全回归测试拦截；
  5. 工具描述/schema 改了但 `docs/MCP与接口规格.md` 未同步 → verify_contracts 不查文档，
     但工作流要求手动同步。
- 新增规则/新坑时同步 `src/mcp_validator.py` 与 `docs/踩坑索引.md`。

## 5. 模板与回归测试

### 5.1 模板目录

- `templates/mcp/` 存放 **MCP 正确调用模板**（JSON），按分类组织：
  - 每个文件：`{"name": "...", "tool": "...", "args": {...}, "note": "..."}`；
  - `args` 必须是可通过 `validate_call` 且 dry-run 不写盘/无报错的入参；
  - 同分类可合并为一个 `README.md` 索引。
- 模板不是 PDX 内容模板；PDX 内容模板仍在 `templates/系统模板/`。

### 5.2 新增模板流程

1. 在真实/临时 core 上手工调用，确认返回无 error 且（若有写操作）`dry_run=true`；
2. 写入 `templates/mcp/<category>/<tool>.json`；
3. 运行 `python tools/gen_mcp_templates.py --check` 或 `tests/test_mcp_templates.py`
   校验模板 schema 与调用；
4. 模板若依赖真实数据（如具体 bop_id），`note` 写明“示例数据，按环境替换”。

### 5.3 回归测试

- `tests/test_mcp_templates.py`：加载全部模板，逐条做：
  - `validate_call(tool, args)` 通过；
  - `_handler(args)` 在临时 core 上不抛非 ValueError（数据缺失类跳过）；
- `tests/test_mcp_validator.py`：覆盖校验器规则本身。

## 6. 工作流程

### 6.1 新增/修改一个 MCP 工具的标准流程

1. **读踩坑**：打开 `docs/踩坑索引.md` 对应分类（MCP 工具注册/schema、调用安全）；
2. **查接口**：确认 `ApiCore` 已有方法，或先在 `api_server.py` / `api_core_ext/` 实现；
3. **注册**：在 `src/mcp_tools.py` 对应 `_*_tools` 新增 `_tool(...)`，
   同时维护 `_CATEGORY_TOOLS` / `CORE_TOOLS`（如需直接暴露）；
4. **写描述/schema**：按 §3 正确范式填写 description、参数说明、`required`、`examples`；
5. **加校验规则**：若新工具引入新的安全/正确性要求，在 `src/mcp_validator.py` 增加规则；
6. **沉淀模板**：把正确调用写入 `templates/mcp/<category>/`；
7. **测试**：`tests/test_mcp_templates.py` + `tests/test_mcp_validator.py` + 领域测试；
8. **冒烟**：`tools/smoke_mcp_tools.py --limit N` 或全量（真实环境）；
9. **文档同步**：更新 `docs/MCP与接口规格.md`、`docs/MCP用户指南.md`、
   `docs/MCP开发者指南.md`、`docs/踩坑索引.md`、`docs/历史迭代日志.md`。

### 6.2 修改校验器规则

1. 在 `src/mcp_validator.py` 的 `_METADATA_RULES` / `_CALL_RULES` 增加规则；
2. 规则 ID 使用 `MCPVAL-<CAT>-NNN`；
3. 在 `tests/test_mcp_validator.py` 增加正/反例；
4. 在 `docs/踩坑索引.md` 对应分类补充/关联。

### 6.3 知识文档维护

- 使用者身份操作 → 更新 `docs/MCP用户指南.md`；
- 开发者身份操作 → 更新 `docs/MCP开发者指南.md`；
- 两份文档结构一致，便于后续合并/交叉引用；
- 新踩坑 → 更新 `docs/踩坑索引.md` 与 `docs/历史迭代日志.md`。

## 7. 校验器与自动化拦截

### 7.1 实现位置

- `src/mcp_validator.py`：
  - `validate_tool_metadata(tool)` → list[Issue]；检查注册/schema/描述正确范式；
  - `validate_call(tool, args)` → list[Issue]；调用前拦截缺参/类型错/安全违规；
  - `validate_all_tools(core)` → 汇总全部工具 metadata 问题。
- `tools/check_mcp_contracts.py`：CLI，对 `build_tools(core)` 跑 metadata 校验，
  并在 `tools/verify_contracts.py` 中作为独立步骤执行。
- `src/mcp_server.py`：
  - `BuiltinMcpServer.tools/call` 先 `validate_call` 再 handler；
  - `run_with_official_lib` 用同一 `validate_call` 包装工具 handler。
- `src/api_server.py`：`/api/mcp/invoke_tool` 同样先 `validate_call` 再 handler。

### 7.2 拦截规则（MCPVAL）

| 规则 ID | 类别 | 拦截内容 |
| --- | --- | --- |
| MCPVAL-REG-001 | 注册 | 工具名空/重复 |
| MCPVAL-REG-002 | 注册 | schema 非 object / properties 缺失 |
| MCPVAL-REG-003 | 注册 | required 中出现未定义 property |
| MCPVAL-REG-004 | 注册 | description 为空或含 TODO |
| MCPVAL-DRY-001 | 调用 | 批量/生成工具 `dry_run=false` 时无确认字段（如 approved） |
| MCPVAL-REQ-001 | 调用 | 缺少 required 参数 |
| MCPVAL-TYPE-001 | 调用 | 参数类型与 schema 不符（string/int/bool/array） |
| MCPVAL-PATH-001 | 调用 | 文件路径参数含绝对路径/`..`/盘符 |
| MCPVAL-APPROVE-001 | 调用 | `create_mod` 等工具 `dry_run=false` 但 `approved` 不为 true |
| MCPVAL-EX-001 | 元数据 | 生成器工具缺少 `examples` |
| MCPVAL-DRYSCHEMA-001 | 元数据 | dry_run 工具 schema 缺 `dry_run` 属性 |

### 7.3 运行

```bash
python tools/check_mcp_contracts.py          # 只跑 MCP 校验器
python tools/verify_contracts.py             # 全量（含 MCP 校验器步骤）
python -m unittest tests.test_mcp_validator -v
python -m unittest tests.test_mcp_templates -v
```

## 8. 关联文档

- `docs/MCP_quickstart.md`：快速开始示例（用户向）。
- `docs/MCP与接口规格.md`：完整工具清单/HTTP/协议规格。
- `docs/MCP用户指南.md`：使用者同结构文档（使用 MCP 时读）。
- `docs/踩坑索引.md`：全项目踩坑索引。
- `docs/已知问题与修复.md`：P0 问题核验与修复跟踪。
- `docs/历史迭代日志.md`：历史记录与交付说明。