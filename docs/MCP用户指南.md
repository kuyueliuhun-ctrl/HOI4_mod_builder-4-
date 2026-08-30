# MCP 用户指南 — HOI4 Mod 编辑器

> 适用角色：**使用者（User）** —— 通过 MCP 客户端（Claude Code / Cline / Cursor / DSH 等）
> 使用本软件制作/修改 HOI4 Mod 的 AI Agent 或人类操作者。
> 本文档与 `docs/MCP开发者指南.md` 结构一致，便于整合。
> 权威接口清单仍以 `src/mcp_tools.py::build_tools()` 与 `docs/MCP与接口规格.md` 为准。

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

- 本指南面向 **MCP 使用者**：只需要调用工具完成 mod 内容制作，不修改 MCP 注册表/源码。
- 工具入口：
  - 默认 `tools/list` 只暴露 **核心精选 + 3 个导航工具**；
  - 隐藏工具用 `list_tools_overview` 看分类，`get_tool_schema` 查参数，`invoke_tool(name, args)` 调用。
- 所有写操作默认安全：批量/结构操作默认 `dry_run=true`；高权限写操作需 `approved=true`。

## 2. 工具分类速览

| 分类 | 用途 | 典型工具 |
| --- | --- | --- |
| `core` | 状态/实体/文件/校验基础 | `get_status`、`read_file`、`write_file`、`list_entities` |
| `states-map` | 州/省/区域/国家颜色 | `get_state`、`set_state_building`、`set_country_color` |
| `designers` | 舰艇/飞机/坦克设计器 | `create_ship_design`、`sync_plane_design` |
| `oob` | 师编制/OOB/兵种 | `list_division_templates`、`search_equipment` |
| `ai` | AI 内容 8 类 | `ai_plan_create`、`ai_theater_update` |
| `bop` | 力量平衡 | `list_bop`、`set_bop_initial_value` |
| `localisation` | 本地化/词条 | `write_localisation`、`search_terms` |
| `health` | 校验/健康/撤销/覆盖 | `validate_project`、`explain_diagnostic` |
| `symbols` | 符号/定义/引用/补全 | `find_definition`、`find_references` |
| `media` | 图标/DDS/标牌/GUI GFX | `upload_tech_icon`、`generate_gui_gfx_asset` |
| `generators` | 内容生成器 | `generate_focus_package`、`generate_event` |
| `project` | 新建 mod/模板/国家文件 | `create_mod`、`apply_template` |
| `agent` | Agent 偏好/审计日志 | `set_agent_preference`、`query_tool_logs` |
| `debug` | 调试启动 | `validate_hoi4_debug_run` |
| `nav` | 导航工具 | `list_tools_overview`、`get_tool_schema`、`invoke_tool` |

## 3. 正确范式（按工具类型分类）

### 3.1 新建/项目类

- `create_mod`：
  - 先 `dry_run=true` 看 `files` 预览；
  - 确认后 `dry_run=false` **且 `approved=true`**，`mod_folder_path` 必填。
- `copy_country_files` / `create_blank_overrides` / `create_new_country_files`：
  - 均默认 `dry_run=true`；先看预览再落盘。

### 3.2 内容生成器类

- `generate_focus_package` / `generate_event` / `generate_ideas` 等：
  - 参数可用 `get_tool_schema` 查；schema 内 `examples` 是最小可运行入参；
  - 批量生成先 `dry_run=true`，确认文件清单后再 `dry_run=false`。

### 3.3 本地化类

- `write_localisation`：
  - `entries` 是 `{键: 中文}` 字典；本地化 yml 写回自动使用 `utf-8-sig`（BOM 惯例）；
  - 缺失词条用 `list_missing_localisation` / `batch_fill_localisation` 补。
- `search_terms` / `get_term` / `add_user_term`：
  - 词条库优先 mod，回退原版；批量补本地化默认 dry_run。

### 3.4 文件编辑类

- `read_file` / `write_file`：
  - `path` 必须是 **mod 内相对路径**（如 `common/national_focus/GER.txt`）；
  - 禁止传绝对路径、`..`、盘符；MCP 校验器会拦截越界路径。
- `edit_script_file`：
  - 先 `dry_run=true` 看 diff，确认后 `dry_run=false`；括号平衡自动检查。

### 3.5 状态/设计器/OOB/AI/BOP/媒体类

- 状态类 `set_state_*`：只写 mod，原版自动复制；`level<=0` 表示移除。
- 设计器/OOB 类：`sync_*` 跨国家同步默认 dry_run。
- AI CRUD：`create/update/delete` 必须 `id`；`rename/duplicate` 必须 `id`+`new`；`ai_navy_*` 必须 `section`。
- 媒体类：`upload_*` 图片 base64；`convert_dds` 路径限 mod 内。

### 3.6 校验/修复类

- `validate_project` 返回红/黄/绿：红色先修，黄色用 `explain_diagnostic` 定位。
- `analyze_error_log`：可用 `discover_environment` 拿 error.log 路径，`absolute_path` 限 mod/game 根内。

## 4. 踩坑索引

- 全项目踩坑索引见 **`docs/踩坑索引.md`**。
- MCP 高频用户侧坑：
  1. 没先 `list_tools_overview` 就猜工具名/schema → 用 `get_tool_schema` 查参数。
  2. 写操作不传 `dry_run` 直接落盘 → 批量/生成类先预览。
  3. `create_mod` 不传 `approved=true` 无法落盘 → 确认后同时传 `dry_run=false`。
  4. `write_file` 传了绝对路径 → 用 mod 内相对路径。
  5. 本地化展示文本带 `--中文` 后缀 → 数据层实际是原始 key/value，不要按展示文本回写。

## 5. 模板与回归测试

- 正确调用模板保存在 `templates/mcp/`，按分类/场景组织：
  - `templates/mcp/core/`、`templates/mcp/project/`、`templates/mcp/generators/`、
    `templates/mcp/localisation/`、`templates/mcp/health/` 等。
- 每个模板是 JSON：`{"name", "tool", "args", "note"}`；`tests/test_mcp_templates.py`
  会对模板做 schema 校验和 dry-run 冒烟，保证“正确且无报错”。
- 需要模板时可用 `read_file` 读取模板 JSON，或直接复制其中 `args` 调用。

## 6. 工作流程

### 6.1 最小从零建 mod

1. `discover_environment` / `get_status` 确认环境。
2. `create_mod` 先 dry-run 预览，后 `dry_run=false + approved=true` 落盘。
3. `list_tools_overview` 看分类，`get_tool_schema` 查参数。
4. `generate_focus_package` / `generate_event` 生成内容（先 dry-run）。
5. `write_localisation` 补中文。
6. `validate_project` / `validate_mod` 校验并修复。
7. 可读资源 `hoi4://docs/user` / `hoi4://docs/quickstart` / `hoi4://docs/pitfalls`。

### 6.2 日常修改已有 mod

1. `list_entities` / `get_entity` 定位内容。
2. `list_files` / `read_file` 看文件级内容。
3. 用 `edit_script_file` 或领域工具修改（先 dry-run）。
4. `validate_project` 收尾。

### 6.3 工作流沉淀

- 遇到新的“正确且无报错”的调用组合，按分类写入 `templates/mcp/` 并补测试；
- 遇到新坑写入 `docs/踩坑索引.md` 对应分类；
- 本文档（用户版）与 `docs/MCP开发者指南.md` 保持同一结构，方便合并维护。

## 7. 校验器与自动化拦截

- MCP server 在调用工具前会执行 `src/mcp_validator.py::validate_call`：
  - 必填参数缺失 → 拒绝；
  - 参数类型明显错误 → 拒绝；
  - `create_mod` 未 `approved` 就 `dry_run=false` → 拒绝；
  - 文件路径越界/绝对路径 → 拒绝。
- 工具注册清单由 `tools/check_mcp_contracts.py` 在 `verify_contracts.py` 中自动检查：
  - 工具名唯一、schema 合法、描述非空、正确范式已入 description/schema。
- 使用者不需要安装额外工具；拦截失败会得到明确错误文本。

## 8. 关联文档

- `docs/MCP_quickstart.md`：快速开始示例。
- `docs/MCP与接口规格.md`：完整工具清单/HTTP/协议规格（开发者向）。
- `docs/MCP开发者指南.md`：开发者同结构文档（扩展 MCP 时读）。
- `docs/踩坑索引.md`：全项目踩坑索引。
- `docs/已知问题与修复.md`：P0 问题核验与修复跟踪。