# HOI4 Mod 编辑器（hearts_of_iron_builder）

一个面向《钢铁雄心 4》（Hearts of Iron IV）MOD 作者的**桌面编辑器**，基于 **Python 3.14 + PyQt6** 开发。

提供从「创建 Mod」到「编写国策 / 事件 / 决议 / 科技 / 角色 / MIO / 军事学说 / AI 内容」的完整可视化编辑工具链，内置自研 PDX 脚本解析、多源翻译、地图编辑、图标管理与 AI 辅助创作能力。数据解析与写回严格原子化，绝不直写游戏原版文件。

> 完整项目文档（架构、模块表、进度、UI 原则、避坑）见 [`PROJECT_DOC.md`](./PROJECT_DOC.md)；
> 唯一执行总表（B0~B3 进度 / 待办）见 [`docs/整合计划.md`](./docs/整合计划.md)。

---

## ✨ 核心功能

### 工作台（默认界面，100 种内容类型）
- 左侧按内容类型分类（角色、民族精神、国策、事件、决议、科技、地块、剧本、MIO、装备、兵种、历史档、GUI、本地化等 **100 种**），右侧列出对应文件
- **双击文件**：国策进入设计视图；`history/units` 初始部队直接进入师编制设计器（按军种自动拉起舰艇/飞机/坦克设计器）；图标型内容展示实体图标画廊；其余进入通用树形编辑器
- **新建文件**：基础模板 / 从模板新建 / 新建文件夹（侧边栏「＋」入口）
- **无文件模式**：不直接操作文件而是操作实体 / 项目，跨文件合并绘制国策树

### 专用编辑器
| 功能域 | 说明 |
| --- | --- |
| 国策 / 科技树 | QGraphicsView 自绘画布，网格吸附、拖拽、右键编辑、图标选择 / 上传（自动写 `.gfx` 精灵定义）；科技树 BFS 树形布局、folder 分组、path 连线 |
| 师编制设计器 | 仿游戏内 Division Designer：顶部模板下拉 + 数据面板 + 地形矩阵；营字段优先 / 主装备回退；军种识别自动拉起对应设计器 |
| 舰艇 / 飞机 / 坦克设计器 | hull / airframe / chassis + modules + variants + upgrades 写回；槽位网格；属性估算；原版自动落 mod |
| 事件编辑器 | 结构化 option / effect，文件级字段完整支持 |
| 角色编辑器 | 只替换 name / portraits 区，保留 roles，字符级块定位 |
| 力量平衡 BOP | 仿游戏内弹窗（深色历史风），本地化 / 修正展示 / 区间滑块 / 动作编辑 |
| MIO 编辑器 | 特质树画布 + 特质增删改 + 图标选择 + 方针编辑器（552 MIO / 22 方针） |
| 学说编辑器 | 主要学说 → 4 次要学说面板（陆军精通度 + 满级奖励徽章）→ 子学说编辑 |
| Mod 描述编辑器 | `descriptor.mod` 表单式编辑（name/版本/工坊 ID/路径/封面/tags/replace_path/dependencies），未知条目原样保留 |
| 意识形态编辑器 | 侧栏意识形态列表 + color/派系名/types/rules/modifiers/faction_modifiers 表单 + CRUD |
| 民族精神编辑器 | 按分类分组导航 1.4 万条理念，块内原始脚本体编辑 + 分类内 CRUD |
| AI 内容编辑器 | 8 类 AI 内容完全专用 UI，实体级 CRUD，未知字段保留 |
| 地图编辑器 | 三栏布局（建筑类型 / 画布 / 地块信息），框选划分 strategicregions / supplyareas / states |

### 通用编辑器四件套（B2/B3 批量落地核心）
- **SimpleBlockEditor**：通用顶层块动态编辑器（60+ 个内容类型薄壳 ≤25 行）
- **NestedBlockEditor**：通用嵌套实体编辑器（wrapper → 实体块）
- **RawBlockEditor**：原始块编辑器（脚本库 / 枚举 / 效果 / 条件 / 命名列表 / 游戏定义）
- **GenericTreeEditor**：万能兜底树形编辑器（任意 PDX 脚本）

### 支撑体系
- **本地化 / 词条库**：多源翻译（QIUQI 等 10 个词条 json，约 3,100 条）、批量补写、快速右键本地化
- **图标体系**：实体图标画廊、按槽位上传（角色大 / 小图标）、`.gfx` 精灵定义自动生成、单位标牌库（448 个标牌）；OOB 地图兵牌与师编制槽位在 GFX 缺失时自动回退标牌库（97% 兵种覆盖）
- **校验 / 健康检查**：导出前 8 类检查（括号 / 编码 / 引用 / 重复 id / 贴图 / 科技图标 / 本地化 / 悬空前置）
- **模板系统**：67 个系统模板类别 + 顶层 2 类，共 1,105 个模板，支持变量替换、任意块存为模板
- **AI 辅助创作**：内容生成器（国家 / 理念 / 意识形态 / 角色 / 将领 / 国策 / 事件）、AI 提示词助手（OpenAI 兼容接口直连）
- **外部接口**：HTTP API（仅绑定 127.0.0.1 + Bearer token）+ MCP 服务器（**159 个工具**）
- **撤销系统**：写前自动登记撤销快照，原子写核心

---

## 🖥️ 技术栈

| 项 | 值 |
| --- | --- |
| 语言 / GUI | Python 3.14+ / PyQt6（Qt 6.11） |
| 图像 | Pillow（DDS / PNG / BMP）+ numpy（地图矩阵运算） |
| 外部依赖 | PyQt6、Pillow、numpy、mcp（可选，未装则回退内置零依赖 MCP 实现） |
| 依赖清单 | `requirements.txt`（Windows）/ `requirements-wsl.txt`（Linux / CI） |
| 入口 | `src/main.py`；`启动.bat` / `启动.sh` 均指向它 |
| 界面模式 | `settings.json` 的 `ui_mode`：`workbench`（默认，功能最全）/ `classic`（经典文件树） |

**双 Python 环境（都必须兼容）**：

| 环境 | 路径 | 版本 |
| --- | --- | --- |
| Windows | `.venv\Scripts\python.exe` | 3.14.5 |
| WSL / Linux | `/root/hoi4_builder_venv/bin/python` | 3.14.4 |
| CI | GitHub Actions `verify.yml` | 3.14 |

---

## 🚀 快速开始

### Windows
```bat
setup.bat            REM 一键建 .venv + 装依赖 + 跑契约验证
启动.bat             REM 启动编辑器
```

### Linux / WSL
```bash
bash setup.sh        # 一键建 venv + 装依赖 + 跑契约验证
bash 启动.sh          # 启动编辑器
# 无头冒烟：
QT_QPA_PLATFORM=offscreen python src/main.py
```

> 首次使用请检查根目录 `settings.json`（已被 git 忽略）：
> `HOI4_path`（游戏安装路径）、`mod_path` / `mod_folder_path` / `mod_file_path`（Mod 路径）。

---

## ✅ 验证 / CI

```bash
# 全量验证（双版本各一遍，退出码 0 才通过）
.venv\Scripts\python.exe tools/verify_contracts.py            # Windows
/root/hoi4_builder_venv/bin/python tools/verify_contracts.py  # WSL

# 只跑契约测试（本机实测 510 用例，约 54s）
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m unittest discover -s tests -t .

# UI 覆盖缺口探针
python ui_gap_probe.py --max-files 5 --output docs/UI树形缺口检测报告.md

# 静态门禁
python tools/check_write_discipline.py   # 写入纪律（AST 扫描直写）
python tools/check_layer_deps.py         # 四层依赖方向
python tools/check_file_budget.py        # 行数预算
```

GitHub Actions（`.github/workflows/verify.yml`）会在 `push` / `PR` 时自动执行 `verify_contracts.py`。

---

## 📁 目录结构

```
hearts_of_iron_builder/
├── src/                # 全部 Python 源码（235 个模块，约 6.4 万行）
├── tests/              # 契约 / 回归测试（86 个文件，510 个用例）
├── tools/              # CLI 工具与契约门禁（21 个脚本）
├── docs/               # 深度参考文档（12 个 md）
├── templates/          # 模板库（67 个系统模板类别 + 顶层 2 类，共 1105 个 txt）
├── translations/       # 词条库（QIUQI / 自定义 / 效果 / 修正等 10 个 json + README）
├── unit_counter_library/   # 单位标牌库（icon/ + manifest.json，448 个标牌）
├── .runtime/           # 运行时缓存（地图矢量 / 填充等，已 git 忽略）
├── settings.json       # 用户运行配置（已 git 忽略，本机存在）
├── 启动.bat / 启动.sh   # 启动脚本
├── setup.bat / setup.sh # 一键建 venv + 装依赖 + 跑契约验证
├── ui_gap_probe.py     # UI 覆盖缺口探针（根目录）
├── prototypes/         # 未落地类型的原型（doctrine/mio/equip_def/country_history/faction/script_lib 等）
├── 常用代码/           # 用户参考：mod 常用代码 / 模板文本（非源码，不入库）
├── 游戏素材/           # 用户参考：识图素材（学说 / MIO 等截图，已入库参考）
└── .github/workflows/verify.yml  # CI 契约验证
```

---

## 📚 文档索引

| 文档 | 用途 |
| --- | --- |
| [`PROJECT_DOC.md`](./PROJECT_DOC.md) | **权威项目文档**：架构（四层分离）、模块总表、工程纪律、进度、避坑、历史索引 |
| [`docs/整合计划.md`](./docs/整合计划.md) | **唯一执行总表**：B0~B3 进度、P1~P4 待办、需用户拍板清单 |
| [`docs/游戏文件内容详解.md`](./docs/游戏文件内容详解.md) | 19 章 HOI4 机制 / 文件结构详解 |
| [`docs/MCP与接口规格.md`](./docs/MCP与接口规格.md) | 159 个 MCP 工具、HTTP 端点、ApiCore 约定 |
| [`docs/历史迭代日志.md`](./docs/历史迭代日志.md) | 每轮迭代强制追加的开发日志（含索引） |
| [`docs/环境搭建.md`](./docs/环境搭建.md) | 环境搭建指南 |
| [`docs/学说识图.md`](./docs/学说识图.md) | 游戏内学说 UI 识图结论（视觉识图工作流，见 PROJECT_DOC §2.6） |
| 其他 | `科技图标存储规则.md` / `识图提示词.md` / `QIUQI-LIBRARY映射与复刻矩阵.md` / `RHoiScribe知识映射与补全.md` / `功能与实现文档.md` / `综合报告.md` / `验证契约.md` / `MCP与接口规格.md` |

---

## 🧱 架构原则（摘要）

**四层职责分离**，依赖方向单向向下，下层禁止反向 import 上层：

```
算法层（Core Algo） ← 绘图层（Render） ← UI 层（Widget/Layout） ← 信号槽层（Controller/Binding）
```

- **算法层**：纯逻辑、无 Qt 控件，解析 / 序列化 / 校验
- **绘图层**：把数据变成 `QGraphicsItem / QPixmap / painter`
- **UI 层**：控件 / 布局 / 样式，禁止直接写文件
- **信号槽层**：最薄，只做接线与编排（connect、弹窗、写文件、刷新）

**写入纪律**：一切 mod 内容文件必须走 `write_utils.atomic_write_text`（临时文件 + `os.replace` 原子替换，写前自动登记撤销快照）；涉及游戏本体一律先复制原版到 mod 再写，**绝不直写游戏原版文件**。

---

## 📊 现状概览

| 指标 | 数值 |
| --- | --- |
| `src/` 源码模块数 | 235 个 `.py`，约 63,773 行 |
| 内容类型 `CONTENT_TYPES` | 100 种 |
| 测试文件 / 用例 | 86 个文件 / 510 个用例 |
| 模板库 | 1,105 个 `.txt` |
| 词条库 | 约 3,100 条（10 个 json） |
| MCP 工具 | 159 个 |
| 文档 | 12 个 `.md` |

进度与待办始终以 [`docs/整合计划.md`](./docs/整合计划.md) 与 [`PROJECT_DOC.md`](./PROJECT_DOC.md) §3.4 为准。
