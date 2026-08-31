# HOI4 Mod 编辑器

qq群：720723415

一个面向《钢铁雄心 4》（Hearts of Iron IV）**模组制作者**的桌面工具。

你可以用它来浏览、编辑、生成和检查自己的 Mod，不需要手写大量重复代码。程序基于 Python + PyQt6 开发，运行在你的电脑上，直接读写你的 Mod 文件夹。

> 当前最新发布：**v0.6.0**
> 下载与更新记录见 [GitHub Releases](https://github.com/kuyueliuhun-ctrl/HOI4_mod_builder-4-/releases)

---

## 它能帮你做什么

### 🗺️ 地图与地区
- 在地图上直观查看大洲划分、核心圈层、补给区、资源、铁路、河流和胜利点。
- 可以框选地块，把它们划分到州、战略区域或补给区域。
- 可以把当前地图按图层合成，导出成一张完整图片。

### 📝 编辑模组内容
- 国策、事件、决议、科技、角色、民族精神、意识形态、MIO、学说、派系、装备、AI 内容等常用内容，都有对应的可视化编辑界面。
- 双击文件即可打开对应编辑器；多数内容也可以直接用树形方式编辑。
- 舰艇、飞机、坦克设计器支持槽位、模块、变体和升级，并自动把原版内容复制到你的 Mod 中再修改，不会直接改动游戏本体。

### ⚡ 批量与自动化
- 「批量填鸭」：把表格里的名单套用模板，一键生成批量代码，适合图标注册、将领代码等重复工作。
- 内容生成器：国家、理念、意识形态、角色、将领、国策、事件都可以按模板快速生成。
- 本地化批量补写：自动补全缺失的中文/多语言词条。
- 电台相关：支持生成 OGG 音频文件，并可接入本地语音合成。

### ✅ 发布前检查
- 内置“导出前健康检查”：自动检查括号配对、编码、引用、重复 id、贴图、本地化等问题。
- 发现错误会列出具体文件和问题位置，方便你在发布前修好。

### 🛡️ 安全与撤销
- 所有写入都会先经过安全处理，不直接写游戏原版文件。
- 支持撤销，手滑改错可以恢复。

---

## 系统要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 10/11（推荐）或 Linux/WSL |
| Python | 3.10+（推荐 3.14） |
| 游戏 | 已安装《钢铁雄心 4》（用于读取原版数据） |

如果你有现成的 Python 3.10+ 环境，也可以直接用源码运行；没有的话，请先安装 Python
（推荐 3.14）。

---

## 安装与启动

项目自带跨平台启动器 `launcher.py`：它会自动定位项目根、创建/复用虚拟环境、
安装依赖并启动编辑器。不再依赖任何写死的 Python/venv 绝对路径，也兼容
路径含空格、中文或目录移动的情况。

### 一键启动（推荐）

```bat
:: Windows
启动.bat
```

```bash
# Linux / WSL
bash 启动.sh
```

首次运行会自动创建环境并安装依赖；之后每次直接启动即可。

### 便携版（无需安装 Python/Qt）

如果你不想安装 Python，可以使用发布页提供的 **便携版**：
解压后双击 `启动.bat` 即可运行，包内已自带 Python 和全部依赖。

开发者可用 `python tools\build_portable.py --runtime-only` 在当前项目生成
`portable\win` / `portable\linux` 便携运行时，替换本地 `.venv`；
也可用 `--zip` 生成完整发布包。说明见 `docs/便携版打包.md`。

### 首次安装 / 重装依赖（可选）

```bat
:: Windows
setup.bat
```

```bash
# Linux / WSL
bash setup.sh
```

等价于 `launcher.py --setup --verify`：准备环境后跑一次全量契约验证。

### 手动安装（可选）

如果你更喜欢自己管理环境：

```bash
python -m venv .venv
# Windows
.venv\Scripts\python.exe -m pip install -r requirements.txt
# Linux/WSL
source .venv/bin/activate
pip install -r requirements-wsl.txt
```

然后仍建议通过启动器运行（它会自动把工作目录固定在项目根）：

```bash
# Windows
python launcher.py
# Linux/WSL
python3 launcher.py
```

高级用法与路径规则见 `docs/启动器.md`。

---

## 第一次使用

1. 启动程序后，在设置里填写两个路径：
   - **游戏路径**：例如 `E:/SteamLibrary/steamapps/common/Hearts of Iron IV`
   - **Mod 路径**：你的 Mod 所在目录，例如 `E:/mods/我的模组`
2. 打开或新建一个 Mod。
3. 从工作台左侧选择内容类型，开始编辑。
4. 发布前，使用「导出前健康检查」检查一遍。

> 这些路径保存在本机 `settings.json` 中，不会上传到 GitHub，也不会打包进 Release。

---

## 常见使用流程

1. **新建/打开 Mod**：在工作台中选择「新建 Mod」或打开已有 Mod 目录。
2. **添加内容**：例如添加一个国策，可以用「生成国策包」快速创建，也可以直接新建国策文件后编辑。
3. **补本地化**：编辑完内容后，用本地化编辑器补写中文字幕和描述。
4. **检查**：运行「导出前健康检查」，修复红色错误。
5. **发布**：确认没问题后，把 Mod 文件夹上传到 Steam 创意工坊或分享给朋友。

---

## 常见问题

- **打不开程序？**
  确认已安装 Python 3.10+（推荐 3.14），然后直接运行 `启动.bat` / `bash 启动.sh`；
  首次运行会自动创建虚拟环境并安装依赖。不想安装 Python 的话，请使用发布页的便携版。
- **看不到原版内容？**
  检查设置里的游戏路径是否正确；程序需要读取游戏文件作为基础数据。
- **改了原版文件？**
  不会。程序会优先把原版文件复制到你的 Mod 目录后再修改。
- **想从源码包开始？**
  当前 Release 是源码发布，GitHub 会自动附带 Source code zip/tar.gz；下载后按上面的安装步骤运行即可。

---

## 给开发者 / 高级用户

如果你想看技术文档、架构说明、模块清单、验证命令或参与开发，请阅读：

- [`PROJECT_DOC.md`](./PROJECT_DOC.md) — 权威项目文档
- [`docs/整合计划.md`](./docs/整合计划.md) — 开发计划与待办
- [`docs/MCP与接口规格.md`](./docs/MCP与接口规格.md) — MCP/HTTP 接口说明
- [`docs/MCP_quickstart.md`](./docs/MCP_quickstart.md) — AI 助手快速开始
- [`docs/MCP用户指南.md`](./docs/MCP用户指南.md) — MCP 使用者知识文档
- [`docs/MCP开发者指南.md`](./docs/MCP开发者指南.md) — MCP 开发者知识文档
- [`docs/踩坑索引.md`](./docs/踩坑索引.md) — 全项目踩坑索引（开发前必读）
- [`docs/启动器.md`](./docs/启动器.md) — 启动器路径规则与高级用法
- [`docs/便携版打包.md`](./docs/便携版打包.md) — 生成“无需安装 Python/Qt”的便携版

---

## 更新记录

完整的迭代日志见 [`docs/历史迭代日志.md`](./docs/历史迭代日志.md)；
面向用户的版本更新说明见 [GitHub Releases](https://github.com/kuyueliuhun-ctrl/HOI4_mod_builder-4-/releases)。
