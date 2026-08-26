# MCP 从零建 Mod 快速开始

> 给空白智能体看的最小可运行工作流。
> 如果下面的工具不在当前 `tools/list` 中，先用 `list_tools_overview` 查看分类，
> 再用 `get_tool_schema` 查参数，最后经 `invoke_tool(name, args)` 调用。

## 1. 环境确认

```json
discover_environment  →  {}
get_status            →  {}
```

拿到当前 mod 目录、游戏目录、可执行文件、error.log 路径。

## 2. 新建 Mod 项目

先 dry-run 预览：

```json
create_mod {
  "name": "我的第一个 Mod",
  "folder_name": "my_first_mod",
  "version": "1.14.*",
  "mod_folder_path": "E:/mods/my_first_mod",
  "dry_run": true
}
```

确认文件清单后真正落盘：

```json
create_mod {
  "name": "我的第一个 Mod",
  "folder_name": "my_first_mod",
  "version": "1.14.*",
  "mod_folder_path": "E:/mods/my_first_mod",
  "dry_run": false,
  "approved": true
}
```

## 3. 查看内容类型与模板

```json
list_types          →  {}
list_templates      →  {}
get_template        →  {"template_name": "focus"}
```

这样可以拿到项目认识的 `type` 键和模板内容，避免自己猜 PDX 格式。

## 4. 添加一个国策

推荐使用生成器，先 dry-run：

```json
generate_focus_package {
  "dry_run": true,
  "filename": "GER_focus",
  "focuses": [
    {
      "id": "GER_test_focus",
      "x": 0,
      "y": 0,
      "icon": "GFX_goal_generic_focus",
      "prerequisite": [],
      "mutually_exclusive": []
    }
  ]
}
```

确认后 `dry_run=false` 落盘。也可以直接用：

```json
create_entity {
  "type": "focus",
  "id": "GER_test_focus",
  "country": "GER",
  "content": "focus = { id = GER_test_focus ... }"
}
```

## 5. 添加一个事件

```json
generate_event {
  "event_id": "GER_test_event",
  "namespace": "GER",
  "title": "测试事件",
  "desc": "测试事件描述",
  "option": "确认",
  "dry_run": true
}
```

确认后 `dry_run=false` 落盘。

## 6. 补中文本地化

```json
write_localisation {
  "tag": "GER",
  "entries": {
    "GER_test_focus": "测试国策",
    "GER_test_focus_desc": "这是测试国策。",
    "GER_test_event.t": "测试事件",
    "GER_test_event.d": "这是测试事件。",
    "GER_test_event.a": "确认"
  }
}
```

如果不在 `tools/list`，用 `invoke_tool` 调用：

```json
invoke_tool {
  "name": "write_localisation",
  "args": { "tag": "GER", "entries": { ... } }
}
```

## 7. 校验与修复

```json
validate_project  →  {}
validate_mod      →  {}
```

红色项必须修复，黄色项建议修复。可用 `explain_diagnostic` 获取修复建议。

## 8. 兜底原则

- 批量/生成/结构操作为了安全都默认 `dry_run=true`，先看 `files` 预览，再 `dry_run=false`。
- 高权限写操作（新建 mod、启动游戏、生成 GUI 资产）还需要 `approved=true`。
- 所有写操作只写 mod 目录，不直接改游戏本体。