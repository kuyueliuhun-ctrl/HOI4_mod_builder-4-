# HOI4 模组编辑器

一个面向《钢铁雄心4》（Hearts of Iron IV）MOD 作者的桌面编辑器，基于 Python + PyQt6 开发。
提供从「创建 Mod」到「编写国策 / 角色 / 事件 / 决议 / 理念 / 科技」的完整可视化编辑工具链，
并内置 PDX 脚本解析、多源翻译、图标管理与 AI 辅助创作能力。

## 主要功能

### 工作台（默认界面）

左侧按内容类型分类（角色、民族精神、国策、事件、决议、科技、地块、剧本、MIO、装备、兵种、历史档、GUI 等 30+ 类型），右侧列出对应文件：

- **双击文件**：国策进入设计视图，图标型内容展示实体图标画廊，其余进入树形编辑器
- **新建文件**：基础模板 / 从模板新建 / 新建文件夹（侧边栏「＋」入口）
- **文件右键**：打开、在资源管理器中显示、新建等

### 国策设计视图

- 网格吸附、拖拽移动国策节点，支持缩放/平移
- 右键节点：编辑、选择父国策、选择图标、上传图标（含拖拽）、移动、删除、新建子国策
- 图标上传自动生成资源、写入 `.gfx` 精灵定义与国策图标字段
- 本地化名称自动回显（游戏与 mod 翻译合并）

### 实体图标画廊

- 以图片网格展示角色 / 理念 / 决议 / 事件等实体的图标
- 角色支持**按槽位上传**：大图标（顾问）/ 小图标（顾问）/ 大图标（将领）/ 小图标（将领），自动写入 `portraits > civilian/army > large/small`
- 上传图片自动按后缀命名避免覆盖，缺失的嵌套结构自动创建
- 右键可编辑实体、选择/上传/删除，并支持**新建实体**（自动生成骨架并打开树形编辑器定位）

### 通用 PDX 树形编辑器

可视化编辑任意 PDX 脚本文件：

- 节点增删改查、上下移动、拖拽重组、剪切/粘贴
- 搜索定位（关键词/类型过滤）、基本信息查看
- 翻译编辑、翻译刷新、固定字段识别高亮
- 右键**将块保存为模板**、添加节点（词条/模板）、管理自定义语句
- 实时中文翻译显示（基于内置字典 + 游戏本地化 + 自定义语句）

### 模板系统

模板存放在项目根目录 `templates/` 中，按类型分目录管理（国策、事件、决议、角色、科技、AI 战略等 20+ 类，分文件级/节点级）：

- 工作台与文件树均可「从模板新建文件」，支持变量替换
- 可将任意文件/块一键存为模板复用

### 翻译与本地化

- 读取游戏 `localisation` 与 mod 本地化文件，支持查看、修改、覆盖保存（只写 mod，不改游戏原始文件）
- 中英翻译编辑器、翻译文件自动加载（支持 JSON / YML / bundle）
- 词条注册表（自动整理 + 自定义词条）为搜索与 AI 提示词提供数据源

### AI 效果提示词助手

- 基于效果器/触发器词条生成带格式的 AI 创作提示词，可复制到任意 AI（ChatGPT/Gemini/DeepSeek 等）
- 粘贴 AI 回复后自动解析标记块并预览，确认后自动回填到树编辑器

### Mod 创建与管理

- 一键创建 Mod 工程：生成 `.mod` 描述文件、`descriptor.mod`、GFX 骨架与本地化骨架
- 路径配置持久化（游戏目录、mod 目录、`.mod` 文件目录）

## 运行环境

- Python 3.10+（推荐 3.10/3.11）
- 依赖库：`PyQt6`、`Pillow`（DDS 图片解码）、`numpy`（DDS 解压）等

## 安装与运行

```bat
:: 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\pip install PyQt6 Pillow numpy

:: 启动（也可直接双击 启动.bat）
python main.py
```

`启动.bat` 会自动激活 `.venv` 虚拟环境并启动主程序。

## 首次使用配置

菜单栏「文件」中依次配置：

1. **选择 HOI4 目录**：游戏根目录（用于读取本地化与图标资源）
2. **打开 Mod**：选择要编辑的 mod 内容目录
3. **选择默认 mod 目录**：存放 mod 内容子文件夹的目录
4. **选择 .mod 文件目录**：存放 `.mod` 描述文件的目录

以上配置保存在 `settings.json` 中（已配置的路径会自动恢复）。

## 界面模式

通过 `settings.json` 的 `ui_mode` 字段切换：

- `workbench`：工作台模式（默认，左侧类型/文件列表，最完整的功能入口）
- `classic`：经典文件树模式（左侧为系统文件树，右键管理文件）

## 目录结构

```
├── main.py                 # 程序入口
├── main_window.py          # 主窗口：菜单、设置、文件树、工作台对接
├── workbench.py            # 工作台停靠面板：类型/文件导航、内容类型配置
├── focus_view.py           # 国策设计视图 + 实体图标画廊
├── focus_renderer.py       # 国策树渲染器
├── focus_parser.py         # 国策文件解析
├── focus_processor.py      # 国策数据处理
├── focus_base_builder.py   # 国策基础构建
├── generic_tree_editor.py  # 通用 PDX 树形编辑器
├── pdx_parser.py           # PDX 脚本解析器
├── tree_node.py            # 树节点数据结构
├── tree_model.py           # 树模型
├── node_edit_dialog.py     # 节点编辑对话框
├── node_search_dialog.py   # 节点搜索对话框
├── tree_info_dialog.py     # 树基本信息对话框
├── custom_statement_dialog.py  # 自定义语句管理
├── fixed_field_recognizer.py   # 固定字段识别
├── gui_translator.py       # 多源翻译引擎
├── localization_mgr.py     # 本地化管理器
├── translation_loader.py   # 翻译文件自动加载
├── translation_editor.py   # 翻译编辑器
├── translation_widget.py   # 翻译控件
├── icon_ops.py             # 图标读改写与上传
├── icon_picker_dialog.py   # 图标选择对话框
├── icon_upload_dialog.py   # 图标上传对话框
├── dds_loader.py           # DDS 图片加载
├── ai_prompt.py            # AI 提示词生成与回填解析
├── ai_prompt_dialog.py     # AI 提示词对话框
├── term_registry.py        # 词条注册表
├── term_dialog.py          # 词条管理对话框
├── template_scheduler.py   # 模板调度器
├── template_dialog.py      # 模板选择对话框
├── mod_creator_dialog.py   # 创建 Mod 向导
├── settings.json           # 运行时配置
├── templates/              # 模板库（按类型分目录）
└── translations/           # 外部翻译包 / 词条文件
```

## 数据目录说明

- `settings.json`：路径与界面模式配置，首次运行自动生成
- `templates/`：模板库，按类型分目录，`usage.json` 可覆盖类型默认用途
- `translations/`：自动加载的外部翻译包，以及 `effect_terms.json` / `custom_terms.json` 词条文件

## 技术栈

- **GUI**：PyQt6
- **图像**：Pillow + numpy（DDS 纹理解码）
- **配置**：JSON 持久化
- **解析**：自研 PDX 脚本解析器 / 国策解析器
