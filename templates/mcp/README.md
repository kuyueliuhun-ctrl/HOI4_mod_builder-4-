# MCP 正确调用模板

> 这里保存「正确且无报错」的 MCP 工具调用示例，按工具分类组织。
> 每个文件是一个 JSON 模板：`{"name", "tool", "args", "note"}`。
> 它们由 `tests/test_mcp_templates.py` 自动校验：
> 1. `mcp_validator.validate_call` 无 error；
> 2. 在临时 core 上调用 handler 不抛异常。
>
> 用户可直接复制 `args` 使用；开发者新增模板时按 `docs/MCP开发者指南.md` §5 流程执行。

## 分类

| 目录 | 模板 |
| --- | --- |
| `core/` | 状态/实体/文件类基础调用 |
| `project/` | 新建 mod / 模板 / 项目级调用 |
| `generators/` | 内容生成器（默认 dry_run） |
| `localisation/` | 本地化 / 词条 |
| `health/` | 校验 / 修复 |
| `states-map/` | 州 / 省 / 区域（预留） |
| `designers/` | 设计器（预留） |
| `oob/` | 师编制 / OOB（预留） |
| `ai/` | AI 内容（预留） |
| `bop/` | 力量平衡（预留） |
| `media/` | 图标 / DDS / 资源（预留） |
| `debug/` | 调试启动（预留） |