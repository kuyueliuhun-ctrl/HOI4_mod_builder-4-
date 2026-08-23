# AGENTS.md — HOI4 Mod 编辑器（hearts_of_iron_builder）AI 代理指南

> 本文档写给**下一个接手本项目的 AI 代理**：说明项目是什么、怎么跑、怎么验证、
> 有哪些硬性纪律和踩坑记录，以及当前进行中的工作与遗留问题。
> 请先通读本文档再动代码；本文档会随项目演进更新。

---

## 1. 这是什么项目

**钢铁雄心 4（HOI4）Mod 编辑器**，Python + PyQt6 桌面应用，运行在 Windows。
不是浏览器应用、不是打包器——它直接读写 mod 目录下的游戏脚本文件
（`.txt` / `.gfx` / `.yml` / `.mod` / `definition.csv` 等），并带地图可视化能力。

核心能力速览：

- **工作台**：按内容类型浏览 mod 文件/实体（国策/科技/事件/决议/理念/角色等 90+ 类型）
- **国策树画布**：像游戏内一样的树形绘制（文件模式/无文件模式），节点可上传图标
- **科技树画布**：与国策树同一画布绘制（folder 分组、path 连线、BFS 树形布局）
- **通用 PDX 树形编辑器**：任意脚本文件的树形编辑
- **地图能力**：`map/provinces.bmp` 位图加载（2^24 LUT → 省 ID 矩阵）、
  国家着色、地形演示（terrain.bmp / heightmap.bmp hillshade）、
  矢量边界层（放大不模糊）、地图编辑界面（点选/涂色改归属/框选）、
  区域编辑（框选划分 strategicregions / supplyareas / states）
- **校验体系**：本地化缺失、国策引用、重复 id、导出前健康检查
- **写入纪律**：原子写 + BOM 拒绝 + 撤销快照 + 静态扫描（详见 §4）
- **外部接口**：HTTP API + MCP（供外置 Agent 驱动本程序）
- **AI 创作助手**：OpenAI 兼容接口直连生成 mod 内容

## 2. 运行与验证

```bat
启动.bat          :: 正常启动（.venv\Scripts\python.exe src\main.py）
```

**两个 Python 环境（重要）**：
- `.venv` = **Python 3.14.5**（Windows 启动器用这个，原 3.8.10 备份为 `.venv_py38_backup`）
- WSL/Linux 开发/测试 = **Python 3.14.4**（`/root/hoi4_builder_venv`，已验证）

**任何改动后必须跑（双版本）**：
```bat
.venv\Scripts\python.exe tools/verify_contracts.py     :: Windows 3.14：语法编译 + 契约测试 + 写入纪律扫描
/root/hoi4_builder_venv/bin/python tools/verify_contracts.py   :: WSL 3.14 同样跑一遍
```
退出码 0 才算完成。契约测试以 `python -m unittest discover -s tests -v` 实时输出为准
（2026-08-23 约 395 个用例，分布见 tests/ 按域文件）。
`verify_contracts.py` 已内置轻量 UI 缺口探针（`event,tech,character,bop`，本地有
`settings.json` 时执行并走 `--ci` 门禁）；改专用 UI 后仍需手跑一次全量
`ui_gap_probe.py --max-files 0` 确认收敛。

**UI 树形缺口探针 / 全量词条分析（根目录 `ui_gap_probe.py`）**：
```bash
# 专用 UI 缺口报告（只输出统计 + 目录/词条树）
python ui_gap_probe.py --max-files 5 --output docs/UI树形缺口检测报告.md

# 全类型全文件词条统计（不跳过大文件，输出 已分析.md）
python ui_gap_probe.py --dump-all --output 已分析.md
```
- 缺口模式：以通用树形编辑器内容为基准，检测“树里有、专用 UI 里没有展示/编辑”的顶层键与嵌套词条；
- 全量模式：统计全部类型的块/词条数量，并按“目录 → 词条树”展示，不逐行输出文件/行号；
- 每次改动专用 UI 覆盖范围后应运行并同步报告。

## 3. 架构地图（模块清单）

> 全部 Python 源码已归档到 `src/` 目录；下表中模块路径均相对 `src/`。

### 3.1 核心 UI
| 模块 | 职责 |
| --- | --- |
| `src/main.py` | 入口：QApplication + 字体 + 主题 + MyWindow |
| `main_window.py` | 主窗口：菜单/文件树/工作台/画布装配，工具菜单入口 |
| `workbench.py` | 工作台 Dock：类型列表/文件列表/实体提取（`_quick_*_scan` 是实体解析器） |
| `focus_view.py` | 国策树/科技树画布（QGraphicsView 自绘） |
| `focus_renderer.py` | 国策树图形渲染（节点卡片/连线） |
| `tech_view.py` | 科技树布局工具（BFS 树形布局，非对话框） |
| `generic_tree_editor.py` | 通用 PDX 树形编辑器（保存走原子写） |
| `bop_loader.py` / `bop_editor_dialog.py` | 力量平衡（Balance of Power）数据层与专用工作台（本地化/修正展示/动作编辑） |
| `ai_loader.py` / `ai_*_editor_dialog.py` / `focus_order_picker.py` | AI 内容数据层与编辑器（战略计划/战略倾向/师模板/装备/海军/派系战区） |
| `translation_editor.py` / `localization_mgr.py` | 本地化编辑（yml 带 BOM 惯例） |
| `division_editor.py` / `oob_loader.py` / `initial_oob_editor.py` | 师编制/初始部队编辑器 |
| `ship_design.py` / `ship_design_dialog.py` | 舰艇设计器（hull/modules/variants + upgrades 写回） |
| `plane_design.py` / `plane_design_dialog.py` | 飞机设计器（airframe/modules/variants + modules 写回） |
| `tank_design.py` / `tank_design_dialog.py` | 坦克设计器（chassis/modules/variants + modules 写回） |
| `design_template.py` | 设计器模板（独立 `design_templates/`，原子写） |
| `oob_map_editor.py` | 初始部队地图放置窗口（**含 `get_map_data`/`get_state_data` 单例缓存**） |

### 3.2 地图系统（2026-08 新增）
| 模块 | 职责 |
| --- | --- |
| `map_loader.py` | `MapData`：provinces.bmp → 2^24 LUT → 省 ID 矩阵；definition.csv 解析；底图/边界/国家色 overlay 合成；terrain_pixmap / hillshade（heightmap.bmp） |
| `map_canvas.py` | `MapCanvas`：可复用地图画布（模式：手型/点选/涂色/框选/**多选**；选区高亮；滚轮防抖；MinimalViewportUpdate；矢量边界前景） |
| `map_vector.py` | 矢量边界线段提取（numpy 向量化 + 磁盘缓存 `.runtime/map_vectors/`） |
| `map_editor_dialog.py` | 地图编辑界面（点选信息/涂色写归属/框选/图层开关/定位） |
| `map_region_ops.py` | 区域文件解析/写回（strategicregions / supplyareas / states，块级替换） |
| `region_editor_dialog.py` | 区域编辑界面（框选划分区域） |
| `state_loader.py` | `StateData`：states 解析（owner/provinces/基地），`owner_province_map()` 返回 **tag→pids** |
| `state_edit_ops.py` | 州归属写回（块级 owner 替换，只写 mod 内 state 文件） |
| `state_build_ops.py` / `building_lib.py` | 州建筑/州类别/国家颜色写回与数据（`ensure_file_in_mod` 原版自动落 mod） |

### 3.3 工程基础设施
| 模块 | 职责 |
| --- | --- |
| `write_utils.py` | **原子写核心**：`atomic_write_text()`（临时文件 + os.replace；BOM 拒绝；撤销快照） |
| `icon_ops.py` | 图标上传（`write_file_utf8` = 原子写转发）、gfx sprite 注册 |
| `tech_icon_ops.py` | 科技图标上传（GUI/API/MCP 共用，自动写 gfx） |
| `undo_mgr.py` | 文件写入撤销（画布 Ctrl+Z / 工具菜单） |
| `export_health.py` | 导出前健康检查（括号/编码/引用/重复 id 等 8 类） |
| `health_check_dialog.py` | 健康检查结果表对话框 |
| `validation.py` | 本地化缺失/国策引用检测（可复用函数） |
| `theme.py` | 设计令牌 + 全局 QSS（亮色专业工具风，对齐 Scenario Forge） |
| `api_server.py` / `mcp_server.py` | HTTP API / MCP（**必须共用 `ApiCore`，禁止另起实现**） |
| `dds_loader.py` / `icon_resolver.py` | DDS 读取（PIL）/ 图标解析 |

## 4. 工程纪律（可执行契约——改代码前必读）

1. **写入纪律**：mod 内容文件（.txt/.gfx/.yml/.mod/.csv）必须走
   `write_utils.atomic_write_text` 或 `icon_ops.write_file_utf8`（内部已原子化）。
   禁止直接 `open(path, "w")`；确需直写（程序配置/数据）登记到
   `tools/write_discipline_allowlist.json` 并写明理由。
   静态扫描：`python tools/check_write_discipline.py`（AST 扫描，新增直写即失败）。
2. **编码契约**：默认 UTF-8 **无 BOM** + LF；BOM 文本默认拒绝（`WriteContractError`）。
   **例外**：本地化 `.yml` 用 `encoding="utf-8-sig", allow_bom=True`（HOI4 惯例）。
3. **原子写语义**：写失败绝不破坏原文件（临时文件 + os.replace）。
4. **撤销快照**：写前自动登记 undo_mgr（新写入默认 undo=True）。
5. **双版本兼容**：所有新代码必须在 Python 3.14 下编译运行
   （Windows `.venv` 3.14.5 与 WSL `/root/hoi4_builder_venv` 3.14.4 双版本验证）。
   3.8 限制已解除：新代码可直接使用 `list[str]`、walrus、`match`、
   `str.removeprefix` 等 3.10+ 语法；旧文件保留 `from __future__ import annotations`
   不影响运行。用 `tools/verify_contracts.py` 验证。
6. **契约测试**：新功能必须配套 `tests/test_contracts.py` 的用例
   （纯函数优先可测；GUI 逻辑用 offscreen 冒烟）。bug 修复必须补回归测试。
7. **写 mod 文件 = 可能破坏游戏**：任何批量写操作先小样本验证。
8. **游戏机制详解文档契约（重要）**：AI 代理在**主动或被动**了解游戏机制时——
   无论是自己读游戏/ mod 文件、解析字段，还是用户讲解、识图规格、调研查证得出的
   结论——都必须把**游戏文件内容详解**持久化写入项目文档（推荐维护 `游戏机制详解.md`，
   或对应类型章节），**不得只留在对话或内存里**。详解至少包含：
   - 涉及的文件路径与相关键/块结构（附**真实示例片段**，切勿臆造字段）；
   - 字段语义、默认值、嵌套关系、缺失/回退行为，以及踩坑（沿用 §5 的记录风格）；
   - 解析/写回时须遵守的规则（块级替换、引用联动、是否可删等）。
   目的：让下一个接手代理能直接复用这些结论，避免重复调研或凭记忆编造不存在的
   游戏字段/机制。
9. **四层分离开发规范（重要）**：所有新代码与重构必须遵守四层职责分离，
   依赖方向单向向下：
   ```
   算法层（Core Algo） ← 绘图层（Render） ← UI 层（Widget/Layout） ← 信号槽层（Controller/Binding）
   ```
   上层可依赖下层，下层**禁止**反向 import/依赖上层。
   - **算法层**：纯逻辑、无 Qt 控件。解析/序列化、坐标换算、布局计算、数据变换、
     校验。可依赖 `QPointF/QColor` 等纯值类型与 `TreeNode`/数据类；禁止 `QWidget`、
     `QPainter`、`connect`、直接写文件（写文件属于信号槽层编排）。
   - **绘图层**：把数据/算法结果变成 `QGraphicsItem/QPixmap/painter` 图形项与几何
     计算。禁止弹对话框、改业务数据、持有布局。
   - **UI 层**：搭建控件/布局/样式，把用户动作翻译成语义信号。禁止直接写文件、
     直接跑算法、直接 `QPainter` 绘图。
   - **信号槽层**：最薄，只做接线与编排：`connect`、弹窗、调用算法/写文件、
     刷新 UI/绘图。禁止在槽里塞大段算法或 UI 细节。
   判定顺序：**算法 > 绘图 > UI > 信号槽**（命中上层即归上层，信号槽是兜底薄层）。
   命名约定：大型模块按 `<域>_algo.py` / `<域>_render.py` / `<域>_view.py` /
   `<域>_ctrl.py` 分文件；小对话框可用类后缀（`XxxDialog` + `XxxController` +
   模块顶层纯函数）分职责，不强制拆文件。新增方法先判层再写。
   已有良好先例：`focus_processor.py`（算法）、`focus_renderer.py`（绘图）、
   `tech_view.py`（算法+图元）、`tree_model.py`（模型）。当前主要违规标本：
   `focus_view.py`（2476 行/101 方法/133 状态字段，五合一），按本规范应逐步拆为
   `FocusView` 瘦壳 + `focus_algo.py` + `focus_render.py` + `focus_view_ctrl.py`。
   分层重构计划见 `docs/分层重构计划.md`。
10. **禁止输出预览图（重要）**：不得生成/保存 UI 预览截图（如 `*_预览.png`、
    `主题预览.png`、`地编_*.png` 等）到项目目录或提交到仓库。需要验证界面时，
    使用 offscreen 冒烟/统计方式，或直接让用户查看实际窗口；不产出截图产物。
11. **UI/工作台 UI 设计必须先问用户或给方案（重要）**：设计或改造任何 UI /
    工作台 UI 时，必须先向用户提问需要什么样的 UI，或给出 2~3 个可选方案让用户
    做决断；**不得**未经确认直接按自己假设实现界面形态。用户拍板后再动代码。
12. **UI 设计必须先吃透游戏机制并保证完整读写（重要）**：Agent 进行任何 UI /
    工作台 UI 设计时，必须先研读相关游戏文件及 Wiki，弄清该文件如何在游戏内起作用
    （加载/解析/引用/写回语义）。提供 UI 设计参考时的基本要求：
    - 能**展示 100% 对应文件内容**：界面必须能呈现文件中的全部字段/块/值，
      不得因设计取舍而隐藏或丢弃；
    - 对**引申内容的存在可能**进行思考：如默认值、回退、引用联动、其他 mod 用法、
      DLC/派生块等，须在方案中说明；
    - 能**对文件内容进行修改**：设计必须覆盖完整读写（新建/编辑/删除/保存），
      并遵守写入纪律。
    在可能存在**游戏内设计器**（如编制/舰艇/飞机/坦克/国策等）时，
    **主动要求开发者提供游戏内 UI 的文字描述**（或确认使用已有识图规格），
    不得仅凭猜测设计。
    检测 UI 是否覆盖全部内容时，参考目录：游戏根目录（settings.json 的 HOI4_path）、
    mod 目录（settings.json 的 mod_path）、`E:\SteamLibrary\steamapps\workshop\content\394360`；
    可用 `tools/check_ui_coverage.py` 扫描未覆盖词条；
    **根目录 `ui_gap_probe.py`** 是更细粒度缺口探针：对已有专用 UI 的类型，
    按“UI 覆盖规格（UI_COVERAGE_SPECS）”比对真实文件，输出
    “树形编辑器有、专用 UI 无展示/编辑”的顶层键与嵌套路径报告。
    新增/修改专用 UI 后，必须同步更新该规格并运行 `ui_gap_probe.py` 验证缺口收敛。

## 5. 给 AI 代理的踩坑清单（环境/技术事实）

- **当前模型无法读图**：`read_image` 会失败（模型不支持图像输入）——验证界面效果
  用"截图 + 统计颜色数"间接确认（PIL `getcolors`），或直接让用户看截图。
- **控制台是 GBK**：print emoji（✅❌✋）会 UnicodeEncodeError。
  跑脚本加 `python -X utf8`，或在代码里 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`。
- **GUI 测试用 offscreen**：`QT_QPA_PLATFORM=offscreen`（字体缺失警告可忽略）；
  需要真实字体渲染的截图用 `QT_QPA_PLATFORM=windows`（窗口会短暂闪现）。
- **沙箱无外网直连**：访问 GitHub 需经 Clash 代理 `http://127.0.0.1:7890`
  （`git -c http.proxy=...` / `curl -x`）；**curl.exe 的 schannel 在沙箱会失败**，
  python urllib 设 `HTTP_PROXY`/`HTTPS_PROXY` 可用。
- **PyQt6 枚举位置**：`RenderHint` 在 `QPainter`；`QLineF` 在 `QtCore`；`QGraphicsItem.CacheMode`。
- **HOI4 文件事实**：高度图文件名是 **`heightmap.bmp`**（不是 heights.bmp）；
  本地化 yml 带 BOM 是惯例；`terrain.bmp` 是地形类型图。
- **`np.save` 会自动补 `.npy` 后缀**：临时文件名必须带 `.npy` 结尾（如 `fp + ".tmp.npy"`）。
- **数据单例**：`oob_map_editor.get_map_data / get_state_data`（按 mod+game 键缓存）。
  `owner_province_map()` 返回 **tag→pids**；`country_overlay_pixmap` 需要 **pid→tag**——转换别搞反。
- **测试素材**：`E:\mods\3350890356`（542 科技、1493 州文件、完整地图）、
  `E:\mods\3228475937`（88 科技、无 states）、游戏本体 `E:\SteamLibrary\steamapps\common\Hearts of Iron IV`。
- **调试配置在 settings.json**：根目录 `settings.json` 是用户运行配置（mod_path /
  HOI4_path / mod_folder_path / mod_file_path / ui_mode 等，另有
  map_zoom_threshold / map_zoom_settle_ms 等可选键，经 `read_map_settings()`
  读取）。调试定位问题时**先读 settings.json 的当前值**（它反映用户真实
  环境）；**如无必要不要修改 settings.json**——改动会直接影响用户的启动
  状态与运行环境；确需修改（如临时切换 mod 路径）时先备份原内容，并在
  最终交付时说明改动或还原。
- **Windows 只读目录测试跳过**：契约测试里 POSIX 权限用例在 Windows skip。

## 6. 当前进行中的工作与遗留问题（截至 2026-08-15）

### 6.1 已完成：地图编辑器体验改进（用户要求 4 项，2026-08-15 全部落地）
1. ✅ `map_canvas.py`：滚轮缩放防抖（滑动挂起重绘，停止 1 秒后统一重绘，
   `_zoom_timer` + `setUpdatesEnabled`）、`MinimalViewportUpdate` 区域重绘、
   选区系统（`set_selection`/`toggle_province_selection`/`clear_selection` +
   `selection_changed` 信号，统一黄色 `SELECTION_COLOR`）、
   新增 **`MODE_MULTI` 点选多选模式**、框选结果自动进入选区。
2. ✅ `map_editor_dialog.py`：默认尺寸 1180×780 → 1440×900（减少留白）、
   模式按钮组加「☑ 多选」、`selection_changed` 显示"已选 N 个地块｜涉及 N 个州"、
   「✕ 清空选区」按钮、复制按钮改为"复制选区 id 列表"。
3. ✅ `region_editor_dialog.py`：尺寸 → 1440×900、加多选按钮、
   选区反馈（框选/多选统一黄色高亮 + 数量提示）、「✕ 清空选区」按钮、
   操作按钮文案"用选区"。
4. ✅ 验证：offscreen 冒烟（多选 toggle/框选进选区/防抖挂起与恢复）+ 契约测试双版本全绿。
   ⚠️ 注意：`QWidget.updatesEnabled` 在 PyQt6 是**方法**不是属性（`c.updatesEnabled()`）。

### 6.2 已完成：遗留问题 4 项（2026-08-15 本轮全部落地）

1. ✅ **地图矢量轮廓填充（v2）**：`map_fill.py` —— 从省 ID 矩阵全局提取闭合
   轮廓多边形（有向单位边 + 左转规则链接 = Marching Squares 等价实现，
   正确处理鞍点/孔洞/多连通）+ Douglas-Peucker 简化（批量向量化，
   全图 15120 环构建 2.7s）+ 磁盘缓存（`.runtime/map_fill/`，同 map_vector 键）。
   `map_canvas.py` 的 **`VectorBaseItem`** 在缩放 ≥ 阈值时用矢量多边形填充
   替代位图底图（省内部与边界都锐利），叠加层/高亮/选区语义不变；
   实测 30× 视口 11.7ms/帧、90× 5.7ms/帧。⚠️ item paint 里
   `painter.clipBoundingRect()` / `option.exposedRect` 在 grab 场景不可靠，
   `_paint_fill` 用设备尺寸反变换算可见范围。
2. ✅ **初始部队放置窗口迁移 MapCanvas**：`oob_map_editor.py` 移除自绘
   MapView，改用可复用画布。为此给 `map_canvas.py` 加了 4 个通用扩展点：
   `left_clicked` / `right_clicked` / `hover_moved` 信号（近距点击检测区分
   拖拽）+ `add_painter` 前景绘制钩子（drawForeground 末尾恒执行，与矢量
   边界开关无关）。兵牌/国家标签在钩子里 `setWorldTransform(QTransform())`
   切视口坐标绘制（恒定屏幕大小）。
   ⚠️ PyQt6 `QPainter.drawPixmap` **没有 (float, float, QPixmap) 重载**，
   必须用 `drawPixmap(QPointF(...), pixmap)`（旧实现此路径一直会抛错，
   真实数据渲染才暴露）。
3. ✅ **阈值/防抖可调**：settings.json 新增 `map_zoom_threshold`（默认 2.5）
   与 `map_zoom_settle_ms`（默认 300，早期为 1000），`read_map_settings()` 读取，
   MapCanvas 构造参数可覆盖。
4. ✅ **Scenario Forge 移植 4 子项**：
   - **规则分层 + delta 增量模型** `overlay_rules.py`：显式规则链
     （vanilla 只读层 + mod 覆盖层，include/exclude 模式）+ 文件级增量报告
     （new/override/identical + 质量分级 direct_copy/manual_reviewed/approx/
     blocker + difflib 行级 added/removed）；对话框「覆盖规则与增量报告…」，
     JSON 导出走原子写；`/api/overlay_report` + MCP `get_overlay_report`。
   - **图标库 manifest** `icon_manifest.py`：扫描 mod+游戏**整棵树**的
     *.gfx（部分安装把定义放 dlc/，只扫 gfx/ 会漏）的 spriteType →
     sprite 名/贴图/来源/尺寸/md5/存在性；对话框「图标库 manifest…」、
     `/api/icon_manifest`（ApiCore 实例级缓存）+ MCP `get_icon_manifest`。
   - **单位标牌库** `unit_counter_library.py`：从游戏
     `gfx/interface/counters/*/onmap_*.dds` 提取转 PNG（PIL）+ manifest.json；
     `tools/import_unit_counter_library.py --game`、对话框「单位标牌库…」
     （搜索/类别过滤/双击复制路径）。真实游戏 448 个标牌 2.6s 导入。
   - 测试：OverlayRulesTest / IconManifestTest / UnitCounterLibraryTest /
     MapCanvasExtensionsTest / OobMapEditorSmokeTest 全绿，契约双版本通过。

### 6.3 已完成：地图画布渲染缓存优化（2026-08-15 本轮，用户拍板「不牺牲锐利度」）

针对「高倍缩放矢量填充/边界每帧重绘」的效率问题，纯缓存优化（视觉效果不变）：

1. ✅ **省级 QPainterPath LRU 缓存**（`map_canvas.py` `VectorBaseItem`）：
   `_path_cache`（OrderedDict，上限 `_PATH_CACHE_MAX=2048`）+ `_pid_loop_off`
   环索引（set_fill 时一次 argsort 分组）。每省一条 path（even-odd 多环，
   孔洞/多连通语义保留），只在首次绘制时构建；旧实现每帧为每个可见环
   重建 QPolygonF + drawPolygon。
2. ✅ **视口栅格瓦片缓存**：矢量填充按（缩放档 `TILE_ZOOM_EPS=1e-4` 容差 +
   可见区域）渲染一次到离屏位图（区域 = 视口外扩 `TILE_MARGIN_FRAC=0.5`，
   上限 `TILE_MAX_SIDE=4096` 防爆内存），平移落在缓存区内时整帧纯 blit
   （不再逐省重绘）；缩放变化/移出缓存区才重渲染。瓦片**设备像素对齐**
   （blit 把瓦片场景区原点经 `painter.worldTransform().map()` 投影到当前
   视图设备位置并四舍五入，1:1 拷贝无重采样模糊——见第 7 点位置跟随修复）。
3. ✅ **边界线烘焙进瓦片 + numpy 像素混合**（本轮真凶）：
   - **根因**：`map_vector` 合并后的边界线段横跨整幅地图（数千像素），
     Qt 光栅器对长线段描边 ~1ms/千像素——旧 drawForeground **每帧**
     整条绘制，实测 30× 平移单帧 **3.7~8.5 秒**（「绘图效率低」的本体）。
   - **修复**：`_select_borders`（相交筛选 + **轴对齐几何裁剪**到目标矩形）+
     `_bake_borders`（同列/同行**相接段 numpy 归并**后，逐段把 1px 描边
     以预乘 alpha 直接混合进瓦片像素缓冲，`_blend_border` 小端
     0xAARRGGBB；大端回退 QPainter）。bake 实测 **7.9ms**（原 2.8s）。
   - `drawForeground` 在 `base_item.tile_valid(zoom)` 时跳过边界线；
     无填充时也走 `_select_borders` 几何裁剪版（`enable_vector_borders`
     会 `set_border_provider` 接线）。
4. ✅ 验证：新增 10 个契约测试（瓦片命中计数 / blit 与重渲染采样一致 /
   缩放变化失效 / 关闭填充清空缓存 / even-odd 规则 / 边界烘焙有深色描边 /
   _blend_border 混合数学 / 预览模式 3 项）；
   `tools/bench_map_render.py` 基准脚本（offscreen，各缩放档 + 平移模拟，
   输出瓦片命中率）。**真实地图（3350890356）实测**：
   缩放档位 4.95~6.96ms/帧（瓦片命中 20/20），30× 平移模拟
   **21.7ms/帧**（旧实现 3.7~8.5s/帧，~300 倍；真实小步平移大部分帧为
   ~5ms blit，每半屏一次 ~20ms 瓦片重渲染）。
   ⚠️ QTransform 组合语义：`scale(s,s).translate(-rx0,-ry0)` = 点先平移后缩放
   （`(p-r)*s`），写反会整体错位数百像素；⚠️ 瓦片尺寸必须按**设备像素**
   计算（w×dpr），否则高分屏（dpr>1）下缓存区小于视口会缺画面；
   ⚠️ `_blend_border` 依赖小端 0xAARRGGBB 布局（大端回退 QPainter）。
5. ✅ **滚轮预览缩放**（2026-08-15 追加）：滚轮滚动期间**不再挂起重绘**，
   而是进入预览模式（`MapCanvas._preview_active` + `VectorBaseItem.set_preview_mode`）：
   把已渲染好的瓦片当位图按当前变换实时缩放显示（零矢量重绘，实测
   4.8~5.4ms/帧，画面实时跟随缩放）；放大时可见区缩小落在瓦片内 → 纯
   blit；缩小超界时底图位图补全（`_preview_blit`）；预览期间
   `drawForeground` 跳过边界线（瓦片里已有）；停止
   `map_zoom_settle_ms`（默认 **1000→300**，重渲染已毫秒级，settings.json
   可覆盖）后 `_flush_zoom` 退出预览、invalidate_tile 并重渲染一次高质量
   瓦片（实测 ~10ms）。`_updates_disabled`/`setUpdatesEnabled` 挂起机制
   保留为兼容路径（wheelEvent 不再使用）。
6. ✅ **手型合并点选语义**（2026-08-15 追加）：`MODE_PAN`（手型）现在同时
   具备点选能力——非拖拽时悬停发 `province_hovered`（`event.buttons()` 含
   左键 = 拖拽中，不发），近距单击（press/release < 5px，复用通用点击
   检测）发 `province_clicked`；`left_clicked` 照发（OOB 不受影响）。
   `MODE_POINT` 保留（兼容旧调用/测试，功能与 PAN 单击一致）。
   两个对话框（map_editor_dialog / region_editor_dialog）去掉「👆 点选」
   按钮，手型 tip 改为「拖拽平移；单击/悬停查看地块信息」。
   新增 4 个契约测试（PAN 单击报告 / PAN 拖拽不报告 / PAN 悬停报告 /
   PAN 拖拽中不悬停）。⚠️ **QTest.mouseMove 不可靠**：构造的事件不带按键
   状态（模拟拖拽中移动须手工构造 QMouseEvent 带 buttons=LeftButton），
   且存在第二个未关闭窗口（offscreen 多窗口测试）时事件根本不投递
   （测试顺序敏感，曾致 SmokeTest+ExtensionsTest 合跑偶发失败）——
   悬停模拟统一用 `_send_move` helper（app.sendEvent + QMouseEvent）。
7. ✅ **瓦片位置跟随修复**（2026-08-15 追加）：`_blit_tile` 原先把瓦片画死
   在固定设备偏移 `(-mx,-my)`——视图平移/缩放后变换已变，瓦片（内容 =
   渲染时视图下的设备像素）必须把**场景区原点投影到当前视图的设备位置**
   再 1:1 拷贝，否则小幅平移（瓦片缓存命中，<半视口）时色块钉在原地
   不随地图移动。修复：`painter.worldTransform().map(rx0, ry0)` +
   设备像素四舍五入对齐。滚轮预览缩放的位置错误（同一根因）一并修复。
   回归测试：`test_tile_follows_pan`（pan 后中心颜色应为目标省色且瓦片
   未重渲染）、`test_tile_follows_preview_zoom`；真实地图验证 blit 帧与
   重渲染帧采样零差异。
8. ✅ **初始视野放大去留白**（2026-08-15 追加）：全景适配后地图只占视口
   ~60% 高度（宽高比 2.75:1 vs 视口 1.6:1），初次打开上下留白严重。
   `MapCanvas.fit_map(factor=1.0)` 加可选放大系数（全景按钮不传 = 完整
   视野不变）；`read_map_settings` 新增 `map_initial_zoom`（默认 1.3，
   clamp 1.0~4.0，settings.json 可覆盖）；map_editor_dialog /
   region_editor_dialog 初始 `fit_map(factor=initial_zoom)`（region 编辑器
   原先甚至没有初始视野、只显示地图左上角，一并修复）。OOB 编辑器已有
   `DEFAULT_ZOOM` 初始放大逻辑，未动。测试：settings 默认/自定义/clamp
   3 项断言 + `test_fit_map_factor`。
9. ✅ **两层醒目选中高亮 + 删除悬停信息展示**（2026-08-15 追加）：
   - **层1 目标省份**（鼠标悬停）：`MapCanvas` 新增 `hover_item`
     （z=40，青色 `HOVER_COLOR=(80,200,255)` alpha 130，LRU 缓存 16），
     `_set_hover(pid)`（pid 变化才重算，pid<=0 清除）、
     `set_hover_highlight_enabled()`（默认关闭，其他使用方不受影响；
     地图编辑器开启）/ `clear_hover()`；鼠标移动（非拖拽）自动更新。
   - **层2 选中地块**：原有黄色选中层（z=50，SELECTION_COLOR）不变；
     `_mask_overlay` 抽公共掩码合成（highlight_pids 与 _set_hover 共用）。
   - **悬停不再刷新右侧信息**：map_editor_dialog 移除
     `province_hovered` 连接（信号保留兼容），信息只在点选/操作后展示。
   - **点选 = 单选**：`_on_province_clicked` 先 `set_selection([pid])`
     （替换选中集，黄色层；多选/框选流程不变）再刷新详情（顺序保证
     详情文本覆盖 selection_changed 的「已选 N 个地块」提示）。
   - 测试：3 个 hover 高亮（开启显示青色系/默认关闭/移出清除）+ 2 个
     对话框（点选替换选中、悬停不更新信息）。⚠️ 采样黄色条件要放宽
     （(255,200,90)@150 叠深色省色后红通道可能 <200）。

### 6.4 已完成：建筑系统/国家颜色/三栏信息面板（2026-08-15 本轮）

1. ✅ **数据层扩展**：
   - `state_loader.py`：州解析新增 `state_category` / `manpower` /
     `buildings`（顶层键）/ `buildings_pid`（锚定地块）/ `victory_points`
     （pid-points 配对序列）/ `src`（源文件，mod 优先）；`reload()` 写后
     重载；`load_state_categories`（common/state_category 的
     local_building_slots）+ `slots_of` / `buildings_of`。
   - `building_lib.py`（新）：`load_building_types`（common/buildings
     整树扫描，**province_max 递归检测**——部分 mod 嵌套在子块；
     同名定义合并属性，mod 优先）+ `load_country_colors`
     （common/countries 的 color，0-255 整数与 0-1 浮点兼容；
     country_tag 匹配优先，文件名兜底）。
   - `map_loader.country_overlay_pixmap` 加 `tag_colors` 参数（文件色，
     缺省色环兼容）。
2. ✅ **写入层 `state_build_ops.py`**（新，全部原子写 + 撤销快照）：
   - `set_state_building`（顶层键 = 州级；`pid = {type = level}` 锚定 =
     省级；level<=0 移除，键删光自动删空块；单行内联块 `10 = { naval_base
     = 3 }` 用非行首匹配替换）
   - `set_state_category` / `set_country_color`（country_tag→文件映射）
   - **原版自动复制到 mod**：`ensure_file_in_mod`（HOI4 state/countries
     是整文件覆盖语义，复制全文安全；返回 copied_written 提示）
3. ✅ **UI 三栏重构**（`map_editor_dialog.py`）：左=建筑类型列表（59 项，
   省/州级标注）；中=画布；右=地块信息面板（地块/州/类别/建筑位/人力/
   建筑/归属/国家颜色）+ 操作按钮（🏗 放置选中建筑 → 等级输入 →
   省级锚定地块/州级写顶层；🔄 改变归属；🎨 修改国家颜色 →
   QColorDialog）；底部信息栏移除。涂色模式复用「改变归属」流程。
4. ✅ 验证：4 个新测试类（StateExtLoaderTest / BuildingLibTest /
   StateBuildOpsTest / MapEditorDialogSmokeTest）共 14 用例，真实数据
   冒烟（3350890356 + 游戏本体：59 建筑/38 省级/694 国家色/州信息完整）。
   ⚠️ 踩坑：tree_node 把块内裸值解析为 **key（value 为空）**——
   `51 204 51` 是三个 key；`victory_points = { 10 2 11 1 }` 需按
   pid-points 配对；⚠️ 测试断言删除不存在建筑返回 None 而非原内容。
5. ✅ **建筑类型图标按钮**（2026-08-15 追加）：左侧从文本列表改为
   **QToolButton 按钮组**（QButtonGroup exclusive）：
   - **可建造 vs 不可建造**：`building_lib` 解析 `is_buildable = no`
     （递归 `_has_flag`）→ `buildable` 字段（缺省可建造）。
     **可建造建筑 → 上方 4 列纯图标网格**（ToolButtonIconOnly，40×40）；
     **不可建造（地标/水坝等）→ 下方文本按钮**（图标+中文名，一行一个，
     带「不可建造（地标/设施）」分组标题）。真实环境：32 可建 / 27 不可建。
   - **图标**：`gfx/interface/buildings/building_icon_strip.dds` 图集
     **按建筑定义来源选择对应图集**（`building_lib` 记录 `src`=mod/game）：
     帧宽 = strip 宽 / `GFX_buildings_strip` 的 `noOfFrames`
     （`strip_frame_count` 解析 interface/*.gfx；游戏 1426x46/31 帧=46px，
     **3350890356 mod 1170x45/26 帧=45px**——硬编码帧宽会错位！）；
     `icon_frame` 递归查找，frame 超界跳过。修复后真实环境 55 图标。
   - **中文名**：`buildings_l_english.yml`（中文包同理）的键 = 建筑键
     （`infrastructure: "基础设施"`）→ loc_manager.get_name(key)。
   - **悬停描述**：`<key>_desc` 键（中文优先，回退英语 yml 逐行正则，
     再回退空）→ 按钮 tooltip = `中文名（省/州级）\n\n描述`（纯图标按钮
     同样有 tooltip；**右侧地块信息的建筑列表同样用中文名**）。
   - **游戏内效果**：`building_lib` 解析 `state_modifiers` /
     `country_modifiers`（兼容 `{ modifiers = { key = val } }` 嵌套与
     直接键值）→ `modifiers` 字段；tooltip 追加
     「效果（州/国）: 名 值」段落——修饰名查找链
     `MODIFIER_<KEY大写>` → raw key → 英语 modifiers_l_english.yml
     （键格式不统一，两种都匹配），值显示 |v|<1 为百分比、整数原值。
     真实环境 38/59 建筑有效果段。
   - **选中醒目**：`_mask_overlay` 高亮覆盖层加 **1px 白色不透明边缘描边**
     （4 邻域异或），`SELECTION_ALPHA` 150→180——选中/悬停省在浅色地形
     上也醒目。
   - 右侧面板 `setFixedWidth(330)`：信息内容变化不再影响布局宽度。
   - 真实环境：59 按钮 / 55 图标 / 中文名+中文描述生效。
   ⚠️ **QGraphicsView 默认 QFrame 边框 ~2px**：grab() 图像坐标 ≠ viewport
   坐标（单像素采样会偏移到白边）——hover 高亮测试直接断言
   hover_item.pixmap() 内容而非 grab 像素。

### 6.5 已完成：编制编辑器 v2（参考游戏内 Division Designer，2026-08-15 本轮）

用户用外部多模态模型识图（`docs/识图提示词.md` 第五节）产出游戏内编制编辑器设计规格，
拍板：**亮色主题 + 顶部下拉切换 + 完整三组数据 + 只要地形矩阵**。全部落地：

1. ✅ 数据层扩展（`oob_loader.py`）：
   - `load_sub_units` 扩展解析营属性（combat_width/max_strength/max_organisation/
     maximum_speed/manpower/training_time/suppression/weight/supply_consumption/
     fuel_consumption/reliability/攻击类字段）+ `need{}`（装备需求）+ `terrain{}`
     （地形 movement）；旧调用方兼容（新增键不破坏）。
   - `load_equipment_stats`（新）：扫描 common/units/equipment/*.txt 的装备块
     （**equipments = {} 包裹一层，部分文件直接顶层——`_collect_equip_blocks`
     对 node 自身先检查再递归**），按 (mod_path, hoi4_path) 模块级缓存；
     真实环境 354 个装备。
   - `division_stats`（新）：基础值汇总（宽度 Σ/人力 Σ/速度 min/org 平均/
     攻击类**营字段优先 → 主装备回退**/need 聚合/terrain 平均）。主装备按
     **类别前缀匹配**（need 写 `infantry_equipment`，定义是 `infantry_equipment_1`，
     `_find_equip`：精确 → `_0` → 变体号最小）。
2. ✅ UI 重构（`division_editor.py` v2）：
   - 顶部标题栏：标题 + **QComboBox 模板下拉**（含部署数）+ 改名 QLineEdit +
     🔒 is_locked + ＋新建/⧉复制/🗑删除 + 🗺地图放置 + 💾保存（去掉左侧模板列表）。
   - 中部 QSplitter：左=编制网格（提示行 + `_grid_holder` 容器，`_clear_grid`
     只清容器，提示/拉伸保留）；右=**数据面板 setFixedWidth(330)**：基础数据 12 行/
     战斗数据 8 行（QGridLayout 两列，标签灰、数值主色粗体右对齐）+ 装备花费
     （多行 QLabel，数量降序前 8 项）+ 地形适应性（8 徽章卡片 2×4，显示平均
     移动修正 %）。
   - 底部操作栏：⟲ 重置（**从文件原始 content 重新解析同名模板替换**，丢弃
     未保存修改）+ 装备需求汇总（N 种 · 合计 X 件）。
   - 数值格式化：`_fmt_num`（整数去 .0）/`_fmt_pct`（±%）；速度带 km/h 单位。
3. ✅ 验证：8 个新契约测试（SubUnitStatsTest 4 + DivisionEditorSmokeTest 4），
   全量 115 测试绿 + 真实数据冒烟（354 装备 / terrain 解析 / 真实模板统计）。
   ⚠️ 踩坑：QComboBox.addItem 在 blockSignals 期间自动选中第 0 项，随后
   setCurrentIndex(0) 索引未变不触发信号 → 初始化需手动补 `_on_combo_changed(0)`。
   ⚠️ `_collect_equip_blocks` 早期版本只查子块，直接顶层装备块漏解析（测试捕获）。
   数值均为**基础值估算**（未含科技/将领修正），UI 提示行已标注。

### 6.6 已完成：舰艇设计器（参考游戏内 Ship Designer，2026-08-15 本轮）

用户识图（`docs/识图提示词.md` 第五节）产出游戏内舰艇设计器规格，拍板：
**完整读写 + 亮色主题 + 只加 OOB 按钮**。全部落地：

1. ✅ 数据层 `ship_design.py`（新）：
   - `load_ship_hulls`：equipment/ship_hull_*.txt 的 archetype（is_archetype，
     基础属性 naval_speed/naval_range/max_strength/build_cost_ic… + module_slots
     槽位表 + default_modules）与变体（archetype 字段/parent/module_slots=
     inherit → 继承 archetype 槽位与属性）。**文件顶层是 `equipments = {}`
     包裹 → 必须 `_iter_blocks` 递归节点树**（parse_pdx_text_to_nodes 只返回
     顶层！）；真实环境 56 船体。⚠️ 战列舰 = ship_hull_heavy 系（没有
     ship_hull_battleship 键），舰型中文映射按前缀。
   - `load_ship_modules`：equipment/modules/00_ship_modules.txt（add_stats /
     multiply_stats + category；特征过滤 abbreviation/category 非空排除容器块）；
     真实环境 120 模块。
   - `load_ship_variants`：history/countries/*.txt 的 create_equipment_variant
     （type 含 ship_hull 才收）。⚠️ **国家文件是展开式**——顶层直接
     capital/create_equipment_variant 等，无 TAG 包裹；TAG 从**文件名前缀**
     取（"JAP - Japan.txt" → JAP），异常文件名回退内容正则。真实环境：
     mod 0 个舰艇设计、游戏 JAP 38 个（初始设计在 countries 文件，AI 预设
     在 common/ai_equipment）。
   - `ship_design_stats`：hull 基础 + 模块 add Σ + multiply 累积乘
     （(1+v) 乘）；cost = build_cost_ic（hull + 模块，⚠️ add 循环已计入，
     不要再加一遍）。
   - 写回：`apply_variant_upgrades`（upgrades 子块级替换，多行/单行块跳过）、
     `insert_variant`（TAG 块内插入，_block_ranges 定位）、`remove_variant`、
     `rename_variant`（块内 name 正则替换）。
2. ✅ UI `ship_design_dialog.py`（新）：顶部国家/设计下拉 + 改名 + 新建/复制/
   删除 + 保存；左侧船体信息 + 槽位网格（固定槽中文名/模块缩写/空槽＋/必装
   空槽🔒，点击槽位 → ModulePickerDialog 按 allowed categories 过滤，含移除）；
   右侧数据面板 setFixedWidth(330) 三组（基础/战斗/其他 8+8+8 项）+ 制海权
   徽章；底部 ⟲ 重置（清模块缓存重载）+ 生产花费。保存 = 读文件 → 块级写回 →
   atomic_write_text（mod 内容文件纪律）；改名保存会替换块内 name（OOB
   version_name 引用需用户自行处理，未做联动校验）。
   ⚠️ ModulePickerDialog 用 exec() 模态——**测试不得直接调用**（offscreen
   阻塞），直接改 upgrades + _rebuild_editor。
3. ✅ 入口：initial_oob_editor 加「🚢 舰艇设计」按钮（用户拍板不加工具菜单）。
4. ✅ **原版自动落 mod（安全修复）**：初版 `_save` 直接用 `_country_file`
   定位文件（mod 优先，否则游戏本体）→ 会**直接写游戏 countries 文件**。
   已修：新增 `_save_path`（复用 `state_build_ops.ensure_file_in_mod`），
   保存目标永远落在 mod 内，游戏原版文件自动复制到 mod 再写；成功提示会
   注明「已自动复制到 mod」。回归测试 `test_save_original_copies_to_mod`
   （mod 无该国家文件 → 写 mod 且游戏本体字节不变）。
5. ✅ 验证：9 个新契约测试（ShipDesignLoaderTest 5 + ShipDesignDialogSmokeTest
   4），全量 124 测试绿 + 真实数据冒烟（56 船体/120 模块/JAP 38 设计/
   Akagi Class 属性估算）。

### 6.7 已完成：飞机设计器（参考游戏内 Plane Designer，2026-08-15 本轮）

用户识图（`docs/识图提示词.md` 第五节）产出游戏内飞机设计器规格，沿用已拍板偏好：
**完整读写 + 亮色主题 + 只加 OOB 按钮**。全部落地：

1. ✅ 数据层 `plane_design.py`（新，结构同 ship_design 但 **modules 块**）：
   - `load_plane_airframes`：plane_airframes.txt 等 6 个 airframe 文件的
     archetype/变体（module_slots inherit + stats + **derived_variant_name**）；
     真实环境 118 airframe。⚠️ 文件内混有派生装备块（CAS_equipment 等），
     用特征过滤（abbreviation/is_archetype/module_slots/archetype/module_slots
     value）。
   - `load_plane_modules`：00_plane_modules.txt（add_stats/multiply_stats）；
     真实环境 101 模块。
   - `load_plane_variants`：type 过滤 = airframe 键集合 ∪ derived_names ∪
     含 "airframe"；真实环境 95 国家 / 449 设计。⚠️ **国家文件解析必须用
     字符级 `_block_ranges`**（`parse_pdx_text_to_nodes` 对 GER 等大文件会
     提前截断，He 111 直接漏掉——已通过 `parse_equipment_variants` 统一修复，
     **舰艇设计器同隐患一并修复**）。
   - `plane_design_stats`：airframe 基础 + 模块 add Σ + multiply 累积乘；
     He 111 实测 344.6km/h/900km/防御22/对空3/机动30/重量14/花费52，与游戏内
     识图数值高度吻合（351/900/22/3/35.5/14/52）。
   - 写回：`apply_variant_modules`（modules 块）/insert/remove/rename_variant。
2. ✅ UI `plane_design_dialog.py`（新）：顶部国家/设计下拉 + 改名 + 新建/复制/
   删除 + 保存；左侧机型信息 + 槽位网格（固定槽中文名/模块缩写/空槽＋/必装🔒）；
   右侧数据面板 setFixedWidth(330) 三组（基础 12/战斗 9/其他 2）+ 底部
   ⟲ 重置 + 生产/改装花费。保存 = **原版自动落 mod**（`_save_path` 复用
   `ensure_file_in_mod`，游戏本体只读）。
   ⚠️ 部分设计引用**未定义的 airframe**（如 ALG small_plane_cas_airframe_0，
   mod/游戏均无 `= {` 定义）——UI 容错显示「机体定义未找到」，槽位区为空，
   属性仅显示模块贡献部分。
3. ✅ 入口：initial_oob_editor 加「✈ 飞机设计」按钮（与舰艇并列）。
4. ✅ 验证：8 个新契约测试（PlaneDesignLoaderTest 5 + PlaneDesignDialogSmokeTest
   3），全量 132 测试绿 + 真实数据冒烟。

### 6.8 已完成：坦克设计器（参考游戏内 Tank Designer，2026-08-15 本轮）

用户识图（`docs/识图提示词.md` 第五节）产出游戏内坦克设计器规格，沿用已拍板偏好：
**完整读写 + 亮色主题 + 只加 OOB 按钮**。全部落地：

1. ✅ 数据层 `tank_design.py`（新，结构同 plane_design，复用其 modules 写回）：
   - `load_tank_chassis`：tank_chassis.txt 等 8 个 chassis 文件（archetype/
     变体/module_slots inherit + derived_variant_name）；真实环境 108 chassis。
   - `load_tank_modules`：00_tank_modules.txt（add/multiply）；真实 116 模块。
   - `load_tank_variants`：type 过滤 = chassis 键 ∪ derived_names ∪ 含
     "chassis"；真实环境 72 国家 / 197 设计。
   - `tank_design_stats`：chassis 基础 + 模块修正；Leichttraktor 实测
     6.1km/h/可靠70%/软攻10/硬攻6/穿甲25/装甲10/突破13.8/防御2.4/花费5.8。
   - 写回：直接复用 `plane_design.apply_variant_modules` 等（modules 块
     逻辑完全一致）。
2. ✅ UI `tank_design_dialog.py`（由 plane_design_dialog.py 复制改造）：
   顶部国家/设计下拉 + 改名 + 新建/复制/删除 + 保存；左侧底盘信息 + 槽位
   网格（主炮/炮塔/悬挂/装甲/引擎/特殊）；右侧数据面板三组（基础 5/战斗 8/
   其他 7）+ 底部重置 + 生产/改装花费。保存 = **原版自动落 mod**。
3. ✅ 入口：initial_oob_editor 加「🛡 坦克设计」按钮（与舰艇/飞机并列）。
4. ✅ 验证：8 个新契约测试（TankDesignLoaderTest 5 + TankDesignDialogSmokeTest
   3），全量 140 测试绿 + 真实数据冒烟。

### 6.9 已完成：设计器模板 + 无文件模式/工具菜单入口（2026-08-15 本轮）

用户要求：①无文件模式也提供四个设计器；②设计器支持「保存为模板」；
③模板不被普通模板搜索器搜到。全部落地：

1. ✅ 模板存储 `design_template.py`（新）：
   - 模板放**独立目录 `design_templates/`**（项目根，**不在 templates/**）
     → TemplateScheduler/TemplateDialog（扫 templates/）**天然搜不到**，
     测试 `test_not_found_by_regular_template_search` 验证隔离。
   - 目录按种类：`design_templates/division|ship|plane|tank/*.txt`
   - `save_design_template`（原子写 + 重名自动加序号）/`list_design_templates`/
     `load_design_template`。
2. ✅ 四个设计器各加「💾 存为模板」「📥 模板新建」按钮：
   - 舰艇（upgrades 块）/飞机（modules 块）/坦克（modules 块）：序列化为
     `create_equipment_variant` 文本，加载用 `parse_equipment_variants`
     解析回内存（未保存，需再点保存写文件）；模板名冲突自动加 Copy。
   - 编制：序列化用 `DivisionTemplate.to_pdx()`，加载用
     `parse_division_templates` 加入当前 OOB（未保存）。
3. ✅ 无文件模式/工具菜单入口（main_window 工具菜单新增 4 项）：
   - `🎖️ 师编制编辑器（选择 OOB 文件）…`：先列 mod+game 的 history/units/*.txt
     让用户选，再开 InitialOobEditor。
   - `🚢 舰艇设计…` / `✈ 飞机设计…` / `🛡 坦克设计…`：直接打开（跨国家浏览，
     天然适合无文件模式）。统一走 `_require_mod`（要求已打开 mod 目录）。
   - 菜单常驻 → 无文件模式（工作台 nofile）同样可用。
4. ✅ 验证：4 个新契约测试（DesignTemplateTest 3 + DesignTemplateDialogSmokeTest
   1），全量 144 测试绿 + 编制/舰艇模板 roundtrip 冒烟。
   ⚠️ 测试 patch QInputDialog 需指向 `PyQt6.QtWidgets.QInputDialog`
   （对话框内是方法级 import，模块级无该名字）。

### 6.10 已完成：无文件模式国家选择优化（2026-08-15 本轮）

用户反馈：①无文件模式国家选择要优化，下方展示当前选择的国家；
②当时「点击国家选择后无论如何都会修改 mod 内文件」。全部落地：

1. ✅ **纯选择与写操作分离（修复误写 bug）**：
   - workbench 无文件模式国家栏从顶部**移到内容区下方**，当前国家显示在下方。
   - 新增「🔍 选择国家…」按钮 → `_on_select_country`：**仅切换浏览国家，
     不修改任何文件**（QInputDialog 列出国家 tag + 名 + [mod 已接管]，含
     「全部」；不再走 CountrySetupDialog）。
   - 「🌐 国家设置…」改文案为「🌐 国家设置（复制/创建）…」并加 tooltip
     提示：这是**显式写操作**（复制原版/创建空覆盖），需用户主动点并确认
     才会写 mod 文件。回归测试 `test_pure_select_does_not_write_files`
     （选择后 mod 目录字节级快照不变）。
2. ✅ **下方展示当前选择的国家**：
   - `set_current_country` 增强：显示 `当前国家：GER（Germany）`（国家名从
     country_tags/countries 或 history/countries 文件名推断）；全部时显示
     「当前国家：全部」。
   - `_load_country_names` / `_on_select_country` 合并 history/countries
     文件名前缀国家（`scan_vanilla_countries` 本身不扫该目录，已补全）。
3. ✅ 验证：2 个新契约测试（WorkbenchNofileCountryTest），全量 146 测试绿。
   ⚠️ 测试构造国家名需在 game/common/country_tags 写 `TAG = "countries/…"`
   （scan_vanilla_countries 只扫 country_tags/countries，不扫 history）。

### 6.11 已完成：打开 OOB 文件直接进入师编制设计器（2026-08-15 本轮）

用户要求：打开 OOB 文件直接打开设计器，顶部加地编。全部落地：

1. ✅ `initial_oob_editor.open_oob_designer`（新工厂）：加载 OobFile/sub_units/
   gfx_map → 直接创建并显示 **DivisionEditor（师编制设计器）**，不再经过
   InitialOobEditor 小中间页。
2. ✅ main_window 三处 OOB 入口（文件树双击两处 + 工具菜单「师编制编辑器」）
   统一改为 `open_oob_designer`。
3. ✅ DivisionEditor 顶部工具栏：
   - 「🗺 地图放置陆军…」改名为「🗺 地编（地图放置）…」并加 tooltip
     （打开 OobMapEditor 选择当前编制点击地块放置部队）。
   - 新增「🛠 设计器 ▾」菜单按钮：🚢 舰艇设计 / ✈ 飞机设计 / 🛡 坦克设计
     （QToolButton InstantPopup）。
4. ✅ 验证：6 个新契约测试（OobOpenDesignerTest 2 + **OobFileModeOpenTest 2 +
   WorkbenchOobDoubleClickTest 2**），全量 152 测试绿。
   - OobFileModeOpenTest 锁定**非无文件模式路由**：`_open_tree_editor`
     （工作台/经典共用分发）与 `load_txt_pdx_to_memory`（经典文件树双击）
     对 history/units 文件必须调用 `open_oob_designer`，防止回退到通用
     树形编辑器。
   - ⚠️ **关键修复**：workbench 文件模式双击 OOB 文件原本因
     `_file_has_entities` 为 True 只 emit `entity_gallery_requested`
     （只展示实体画廊，不弹编辑器）——已改为 `initial_oob` 或路径含
     `history/units` 时直接 `generic_file_selected`（→ open_oob_designer）；
     无文件模式双击 OOB 实体同样直接弹设计器。
     WorkbenchOobDoubleClickTest 锁定这两种双击路由（不得只进画廊）。
5. ✅ **军种识别自动拉起对应面板**（用户反馈海军/空军 OOB 未拉起设计面板）：
   - `oob_loader.detect_oob_kinds(content)`：按 `_block_ranges` 识别
     army（division_template/division）/ navy（ship）/ air（air_wing）。
   - `open_oob_designer` 改为按军种拉起：含 navy → ShipDesignDialog；
     含 air → PlaneDesignDialog；含 army 或无法识别 → DivisionEditor；
     混合同时拉起多个（非模态）。
   - ShipDesignDialog / PlaneDesignDialog 新增 `country_tag` 参数：打开时
     优先选中调用方指定国家（`find_oob_country` 从 OOB 文件识别）。
   - 验证：OobKindDetectTest 4 个测试（识别 3 类 + 打开对应面板），
     全量 158 测试绿。

### 6.12 已完成：工作台类型列表分组（2026-08-15 本轮）

用户要求：已明确制作功能的类型统一放列表上方，暂未专门制作的部分放分界线下方。

1. ✅ `workbench.SPECIAL_TYPE_KEYS = ("focus", "tech", "initial_oob")`：
   有专门编辑器（国策树画布/科技树画布/师编制设计器）的类型置顶。
2. ✅ type_list 填充改为分组：先填充专门类型，再插入不可选分隔线
   「────────── 通用类型（树形编辑）──────────」，最后填充其余通用类型。
   ⚠️ `_on_type_clicked` 增加 `key` 为空防护（分隔线无 UserRole data）。
3. ✅ 验证：2 个新契约测试（WorkbenchTypeListGroupTest），全量 154 测试绿。

### 6.13 已完成：动态修正模板（2026-08-15 本轮）

用户要求为动态修正做模板。已按官方机制重做：

1. ✅ 重写 `templates/系统模板/动态修正/基础模板.txt`（file 用途）：
   完整字段骨架（icon/enable/remove_trigger/attacker_modifier + 国家级/州级
   常用修正键）+ 头部注释（add_dynamic_modifier 触发示例）。旧模板写死
   `sabotaged_resources`、字段臆造（industrial_capacity_factory 等），已替换。
2. ✅ 重写 `templates/系统模板/动态修正/项目模板.txt`（node 用途）：单个
   动态修正块，缩进一级，字段同基础版。
3. ✅ `template_dialog.CATEGORIES` 新增 `("动态修正", "动态修正")`——
   模板搜索对话框可按「动态修正」类型筛选（此前无该分类）。
4. ✅ 验证：2 个新契约测试（DynamicModifierTemplateTest）：
   `TemplateScheduler.search_templates(template_type="动态修正")` 返回
   基础(file)+项目(node) 且内容含关键字段；CATEGORIES 含该项。
   全量 160 测试绿。

### 6.14 已完成：飞机/舰艇设计器修正（2026-08-15 本轮）

用户反馈多项修正，研究结论 + 实现：

1. ✅ **槽位布局**：飞机槽位网格 5 列（PLANE_SLOT_COLS）、舰艇 6 列
   （SHIP_SLOT_COLS），视觉上「飞机上5下6 / 舰艇上6下6」；槽位卡片为
   垂直 label+按钮，自动换行。
2. ✅ **锁定槽位**：`allowed_module_categories` 为空且非必装的槽显示 🔒
   灰色禁用（此前会显示可点的空槽＋，但无模块可选）。
3. ✅ **空配件设计**：modules/upgrades 为空的设计（舰艇 97% 是默认设计、
   飞机 4%）在槽位区顶部显示橙色提示「该设计未配置模块，游戏使用默认配置」，
   槽位仍可点击添加模块后保存。
4. ✅ **同款跨国家编辑**：顶部显示「同款 N 国: …」标签 + 「🔄 同步到所有
   同款」按钮——把当前配置写回所有使用**同名设计**的国家（原子写，逐国
   apply/insert）。真实数据：飞机 42 组同名（F-4EJ Kai 15 国、Su-25 14 国）、
   舰艇 125 组同名。
5. ✅ **两个底层 bug 修复**：
   - `_block_map` 支持单行内联 `modules = { slot = mod }`（之前只匹配多行，
     行尾带 `}` 会漏解析）。
   - `_tag_of` / `_save_path` 支持纯 `AAA.txt` 文件名（之前只认
     `TAG - Name.txt`，纯 TAG.txt 的国家设计会漏加载/找不到保存路径）。
6. ✅ 验证：3 个新契约测试（DesignLayoutSyncTest：5/6 列常量+锁定槽、
   空提示+同款标签、同步写回），全量 163 测试绿。
   ⚠️ 研究结论（回答用户）：ARG FMA D.21 的 `light_mg_2x`+`engine_1_1x`
   是间战基础战斗机 small_plane_airframe_0 的标准初始配置；大量空配件设计
   是「默认设计」（只写 type、引擎用 default_modules），非解析问题。

### 6.15 已完成：地编州轮廓提示 + 建筑图标区放大（2026-08-16）

用户反馈：地编选中地块后缺少醒目的“省份”提示；建筑图标要放大、左侧加宽、
底部不出滚动条、右侧滚动条不遮挡按钮。全部落地：

1. ✅ **州轮廓高亮**（`map_canvas.py` + `map_editor_dialog.py`）：
   - `MapCanvas._state_outline_overlay`：按州地块集合生成**外扩 2px 黄色描边**
     （只描边不填充，numpy 4 邻域膨胀，alpha=255）。
   - `MapCanvas.set_state_outlines / clear_state_outlines`：每个州一个独立
     QGraphicsPixmapItem（z=55，在选中层之上），QPixmap 按州集合缓存。
   - 地图编辑器 `_update_state_outline`：点选/框选/多选/定位时自动圈出
     选中地块涉及的全部州边界；清空选区时清除。
2. ✅ **建筑图标区布局**（`map_editor_dialog.py`）：
   - 纯图标按钮 40×40 → **56×56**，图标缩放 32 → **48**；
     设置 `iconSize=52×52` + `padding:0`，图标在按钮内占比接近满格；
     可建造网格 4 列 → **5 列**，左侧滚动区最小宽 260 → **320**（最大 360）。
   - 隐藏水平滚动条（底部不再出现）；垂直滚动条按需显示且保留在内容区右侧，
     加宽面板补偿滚动条宽度，不遮挡按钮。
3. ✅ 验证：新增 4 个契约测试（州轮廓纯函数/设置清除、建筑面板布局/选中显示州轮廓），
   全量 167 测试绿。

### 6.16 已完成：力量平衡（Balance of Power）专用工作台（2026-08-16）

用户要求：把工作台中的「力量平衡」从通用树形编辑器升级为仿游戏内 BOP 弹窗，
并适配有文件/无文件模式。全部落地：

1. ✅ **数据层 `bop_loader.py`**：
   - `load_bop_definitions`：扫描 `common/bop/*.txt`（mod 优先），解析
     initial_value / left_side / right_side / decision_category / range / side。
   - `load_bop_actions`：定位 `common/decisions/*.txt` 中与 decision_category
     同名的**分类块**，取其深度 1 子块作为动作（过滤 DEBUG_*），提取
     cost / add_power_balance_value 或 *_increase/decrease_effect 方向。
2. ✅ **深色工作台 `bop_editor_dialog.py`**：
   - 黑绿历史政治军事 UI：米白标题/副标题、金色棕色描边、深橄榄绿动作行、
     绿色状态圆点、右上角关闭按钮；中央 QSlider 展示/编辑初始值。
   - 动作列表展示决议图标（emoji 猜测）、名称、费用与增减方向。
   - 保存 `initial_value`：`ensure_file_in_mod` 原版自动复制到 mod + 原子写。
3. ✅ **文件模式/无文件模式适配**：
   - workbench 文件模式双击 `common/bop/*.txt` → 直接弹 BOP 编辑器；
   - 无文件模式双击力量平衡实体 → 同样弹 BOP 编辑器；
   - `main_window._open_tree_editor` 按路径识别 `common/bop/` 分发；
   - `SPECIAL_TYPE_KEYS` 加入 `"bop"`（专用类型置顶）。
4. ✅ 验证：新增 3 个测试类（BopLoaderTest / BopEditorDialogSmokeTest /
   BopWorkbenchRouteTest）共 6 个用例，全量 173 测试绿。
5. ✅ **用户反馈补强（2026-08-16）**：
   - **本地化**：BOP 名称 / 势力 / 区间 / 动作 / 修正名自动显示中文
     （mod 优先；自动去除 `£BoP_*` 图标 token、解析 `$KEY$` 引用）；
     编辑器构造时自动补加载 mod/game 本地化目录。
   - **修正展示**：滑块下方实时显示当前区间修正（中文修饰名 + 百分比值）；
     新增「势力与修正」页列出全部 side/range/modifier。
   - **编辑功能**：新增左势力/右势力/决策分类输入框，保存走
     `ensure_file_in_mod` + 原子写；「✏ 编辑定义」打开 BOP 文件树编辑器
     （势力/区间/修正完整编辑）；每个动作行「✏」打开对应决策文件树编辑器
     并定位动作节点。
   - **验证**：新增 `find_active_range` 及本地化/修正/保存/编辑入口回归测试
     共 6 个用例，全量 179 测试绿。

### 6.18 已完成：AI 内容编辑器（2026-08-16）

用户要求为游戏 AI 内容制作完整编辑器，全量落地：

1. ✅ **AI 数据层 `ai_loader.py`**：
   - 统一解析 `common/ai_*`：战略计划、战略倾向、师模板、装备、海军、
     区域、科研权重、派系战区；mod 优先 + 缓存。
   - 写回辅助：计划国策顺序/字段、战略倾向条目、师模板 target_template、
     装备 target_variant、海军目标字段等。
2. ✅ **工作台路由与无文件模式**：
   - `CONTENT_TYPES` 拆分 `ai_strategy_plans` / `ai_strategy`；
   - `SPECIAL_TYPE_KEYS` 加入全部 AI 类型置顶；
   - 文件/无文件双击均直接 `generic_file_selected`，由主窗口分发到专用编辑器。
3. ✅ **AI 战略计划编辑器 `ai_plan_editor_dialog.py`**：
   - 计划列表 + 名称/描述编辑 + 保存；
   - 「🎯 编辑国策顺序」调用 `focus_order_picker.py`：
     - 国策绘图点选、黑框红底白字顺序角标；
     - 点击已选无效；右键「从该国策开始顺序/退出该状态/删除该顺序」；
     - 删除时同时删除后续依赖国策顺序。
4. ✅ **AI 战略倾向编辑器 `ai_strategy_editor_dialog.py`**：
   - 策略组列表 + type/id/value 表格增删改，保存写回。
5. ✅ **AI 师模板编辑器 `ai_template_editor_dialog.py`**：
   - 角色/目标模板列表；「✏ 编辑目标编制」调用师编制编辑器；
   - 保存写回 `target_template`。
6. ✅ **AI 装备编辑器 `ai_equipment_editor_dialog.py`**：
   - 设计组/变体列表；按 category 调用飞机/坦克/舰艇设计器；
   - 保存写回 `target_variant` 的 modules。
7. ✅ **AI 海军编辑器 `ai_navy_editor_dialog.py`**：
   - 三页签：目标/舰队/特遣队；目标页可编辑，复杂块走树编辑器。
8. ✅ **AI 派系战区地图联动**：
   - `map_loader.theater_outline_pixmap` 红色描边；
   - 地图编辑器新增「AI派系战区」图层与「战区列表」；
   - 双击战区打开树形编辑器并定位。
9. ✅ **内容少的 AI 类型模板**：
   - 新增 `templates/系统模板/AI区域|AI科研权重|AI态度|AI人格|AI派系战区`
     基础/项目模板；`template_dialog.CATEGORIES` 注册。
10. ✅ 验证：新增 AiLoaderTest / AiWorkbenchRouteTest / FocusOrderPickerTest /
    AiPlanEditorTest / AiStrategyEditorTest / AiTemplateEditorTest /
    AiEquipmentEditorTest / AiNavyEditorTest / AiFactionTheaterTest，
    全量 206 测试绿，`verify_contracts.py` 退出码 0。

### 6.19 已完成：AI 内容编辑器改造为完全专用 UI + 固定侧边栏（2026-08-16 追加）

用户要求 AI 内容专用界面不要再依赖树形编辑器页面，且 UI 需要固定侧边栏、避免
侧边栏横向滚动。全部落地：

1. ✅ **公共 UI 组件 `ai_ui_common.py`**：
   - `EntityListSidebar`：固定 300px 侧边栏（搜索 + 列表省略号/tooltip + 新建/
     复制/重命名/删除），`QListWidget` 横向滚动条强制关闭。
   - `KeyValueTableEditor`：两列键值表（research / taskforces/mission 等映射）。
   - `ScriptBlockEditorDialog`：单个高级脚本块编辑器（非树形页面），复用
     `NodeEditDialog`（词条/模板/自定义语句搜索 + 原始 PDX 高级模式）、
     `TemplateDialog`、`CustomStatementDialog`、`TermDialog`，支持面包屑进入子块、
     添加/编辑/删除/排序/存为模板。
2. ✅ **`ai_loader.py` 实体级 CRUD**：
   - 全部 AI 类型补 `insert / delete / rename / duplicate` 写回；
   - 通用顶层/嵌套块替换与 upsert（`replace_top_block_child` /
     `upsert_top_block_child` / `replace_or_upsert_nested_child` /
     `replace_top_block_field` / `replace_ai_area_regions` 等）；
   - 未知字段保留；全走 `ensure_file_in_mod` + 原子写。
3. ✅ **AI 类型全部改为专用 UI，移除 GenericTreeEditor 页面依赖**：
   - 战略计划 / 战略倾向 / 师模板 / 装备 / 海军 / 派系战区 / **区域** /
     **科研权重** 均有固定侧边栏专用编辑器；
   - 高级脚本块统一用 `ScriptBlockEditorDialog`；
   - 原「✏ 编辑定义（树编辑器）」入口已移除。
4. ✅ **测试**：新增 AiCrudWriteTest（各类型 CRUD roundtrip）、
   AiSimpleEditorSmokeTest（固定侧边栏 300px + 无横向滚动断言 + 各区打开）、
   AiUiCommonTest（ScriptBlockEditor roundtrip / EntityListSidebar 无横向滚动）。
   全量 `verify_contracts.py` 退出码 0。

### 6.20 已完成：四层分离分层重构（2026-08-16 立项，2026-08-18 落地）

开发规范已写入 §4 第 9 条；详细执行计划见 **`docs/分层重构计划.md`**。
当前状态：**已完成（跳过未制作专属 UI 的工作台）**。要点：

1. ✅ 四层分离开发规范已写入 AGENTS.md §4.9（算法 ← 绘图 ← UI ← 信号槽，单向依赖）。
2. ✅ `docs/分层重构计划.md` 已创建，按工作台逐个定位（focus_view 试点 → 全工作台收敛 → 自动化门禁）。
3. ✅ P1 `focus_view.py` 拆分：
   - 2476 行 → **1188 行**；
   - 科技树 → `TechTreeControllerMixin`（focus_view_ctrl.py）+ `focus_render.render_tech_tree`；
   - 实体画廊 → `EntityGalleryControllerMixin`（focus_view_ctrl.py）；
   - 算法纯函数 → `focus_algo.py`（坐标/块查找/文本构建/实体块边界等，FocusView 保留薄委托）；
   - 绘图 → `focus_render.py`。
4. ✅ P2 工作台收敛：
   - `workbench.py` 纯数据 → `content_types.py`；实体扫描 → `entity_scanner.py`（WorkbenchDock 保留薄委托）；
   - `main_window.py` 路由 → `app_routes.py`；工具菜单构建 → `menu_factory.py`；
   - `division_editor.py` 格式化 → `oob_format.py`；
   - 设计器三件套公共 `ModulePickerDialog` → `designer_common.py`；
   - 地图编辑器检查：未发现需下沉的内嵌纯算法（已由 map_*_ops / state_* 承担）；
   - AI/BOP/翻译/模板/图标库等已有专属 UI 工作台维持现状，通过契约测试。
5. ✅ P3 自动化门禁：
   - 新增 `tools/check_layer_deps.py`（算法/绘图层禁止反向依赖 UI/信号槽层）；
   - 已并入 `tools/verify_contracts.py`（第 4 步）；
   - 新增 `.github/workflows/verify.yml`（CI 跑 `verify_contracts.py`）。
6. ✅ 全量 `verify_contracts.py` 退出码 0（语法编译 / 契约测试 / 写入纪律扫描 / 四层依赖检查）。
7. ⚠️ 未处理：未制作专属 UI 的通用内容类型工作台（仍走 GenericTreeEditor），按用户要求跳过。

### 6.21 已完成：项目文件整理归档 + src/ 包化（2026-08-18）

用户要求整理归档并执行方案 B 代码包化。全部落地：

1. ✅ **启动脚本**：`启动.bat` 与 `启动.sh` 已改为运行 `src/main.py`（修复路径指向）。
2. ✅ **`.gitignore` 补充**：新增 `.venv*/`、`.idea/`、`.jspace/`、`.opensquilla*`、
   `settings.json`、`*.log`、`*.tmp`、`build/`/`dist/` 等；并执行
   `git rm --cached settings.json` 与 `.idea` 下文件（保留本地文件，停止版本跟踪）。
3. ✅ **缓存与空目录清理**：删除 `.runtime/`、全项目 `__pycache__/`（不含 `.venv`）、
   空目录 `.agents/`、`.codex/`。测试/运行后缓存会按需重建，已被 gitignore。
4. ✅ **方案 B `src/` 包化**：
   - 全部 110 个 Python 源码移入 `src/`；
   - 新增 `src/project_paths.py`（`PROJECT_ROOT` / `project_path()`），统一修正
     基于 `__file__` 的资源定位（settings.json / templates / translations /
     unit_counter_library / .runtime 等），避免 src/ 后路径错位；
   - `tools/*.py` 与 `tests/test_contracts.py` 已把 `src/` 加入 `sys.path`；
   - `api_server.py` / `mcp_server.py` 的 ROOT/sys.path 适配；
   - 写入纪律豁免表 `tools/write_discipline_allowlist.json` 已更新为 `src/` 前缀；
   - README / AGENTS 已更新启动命令与架构说明。
5. ✅ 全量 `verify_contracts.py` 退出码 0（语法编译 / 契约测试 / 写入纪律扫描 / 四层依赖检查）。

### 6.22 已完成：本地化 + QIUQI 词条库 + 实体资源工作台 + 工具复刻 + RHoiScribe 吸收（2026-08-19 批次）

本批成果摘要；逐项细节见 `docs/QIUQI-LIBRARY映射与复刻矩阵.md` 状态表与 `docs/RHoiScribe知识映射与补全.md`：

1. ✅ 本地化编辑器（全量/修正词条/搜索增删改）、批量补写缺失 + 多语言（默认中文、英文仅选择才显示）、
   各编辑器右键快速本地化（BOP 含名称+描述）、词条分类筛选。
2. ✅ QIUQI 词条库整合：`tools/import_qiqi_terms.py` + `src/qiqi_term_import.py` →
   `translations/qiqi_terms.json`(1887) + modcode(939)/diplo(11)/tfr(50)/tno(210)；
   `term_registry.TERM_FILES` 末尾加载、同键冲突 QIUQI 胜出（`translate_key` 里为最低回退）。
3. ✅ 实体配套资源工作台（`entity_resource_data.py` / `entity_resource_dialog.py`）：
   批量本地化 + 图标上传 + 一键补全缺失光效 GFX（已有不改，游戏内素材）。
4. ✅ 第一、二批工具复刻：event_gen / pdx_format / icon_batch / state_batch / dds_convert / vp_loc /
   pdx_sorter / interface_reg / error_log（含子系统归类）/ idea / ideology / character / general /
   country_boot / focus_package 生成器。
5. ✅ 角色专用编辑器（`character_editor_dialog.py`：只替换 name/portraits 区，保留 roles）；
   内容生成器工作台（`content_generator_dialog.py`）+ 独立工具对话框。
6. ✅ RHoiScribe 吸收：ApiCore 新增 format_pdx / vp_loc_dry_run / analyze_error_log / register_icon_batch；
   知识映射进 `docs/RHoiScribe知识映射与补全.md`（A~M 补全）；错误日志子系统归类。
7. ✅ 本地化 wiki → `docs/游戏文件内容详解.md` §17.1；QIUQI 映射矩阵同步。
8. ✅ 全量 `verify_contracts.py` 退出码 0，已 commit + push（f0395c1）。

### 6.23 已完成：MCP 补充计划 142 个新增工具（2026-08-22）

按 `docs/mcp补充计划与执行方式.md` 一次性全部落地：

1. ✅ **ApiCore 域扩展包 `src/api_core_ext/`**：9 个 Mixin（states/designers/ai_content/bop/
   loc_tools/health/media/generators/project），ApiCore 多重继承组合，全部接口与 MCP 同源。
2. ✅ **MCP 159 工具注册**（`src/mcp_tools.py`）：现有 17 + 新增 142，名称唯一、schema 合法，
   覆盖州/区域、三军设计器+模板、OOB、AI 8 类、BOP、本地化/词条、健康/撤销/覆盖、
   图标/媒体、7 类生成器、项目级。
3. ✅ **HTTP 同源桥**：`/api/mcp/<tool_name>` 可调用全部 159 工具；docstring/help 已同步。
4. ✅ **逻辑下沉**：BOP 保存写入 `bop_loader.set_bop_initial_value/set_bop_fields`；
   `mod_creator.py` 纯函数生成新建 mod 骨架，ModCreatorDialog 改为调用。
5. ✅ **写入纪律**：新 mixin 无直接写文件（全部走已有原子写/数据层），AST 扫描通过；
   四层依赖检查通过。
6. ✅ **测试**：新增 `McpRegistrationTest` / `McpDomainSmokeTest`（状态/AI/BOP/设计器/区域/
   生成器 dry_run roundtrip），全量契约待双版本验证。

### 6.17 遗留/可选后续

> **遗留/未完成条目的唯一总表 = `docs/整合计划.md`**（按 P0~P4 批次，含需用户拍板清单）。
> 下方为历史摘要，具体状态以该文档与 `QIUQI-LIBRARY映射与复刻矩阵.md` 为准。

- 兵牌图标可考虑接入单位标牌库（当前 OOB 用 GFX_unit_<type>_icon_medium
  解析，失败回退黑底占位）
- Scenario Forge 移植剩余方向（§9 报告 B/C/D 部分条目）：导出前校验面板
  产品化、build_snapshot 溯源台账、关键地区高危 id 清单
- 编制编辑器：模板名改名后部署引用不一致的提示、装备 IC 花费估算（当前只统计
  装备件数）、OOB 海军/空军 version_name 设计解析（调研完成未实现）

### 6.22 已完成：UI 修复与建构（2026-08-22 批次1-9）

> 执行依据：`docs/整合计划.md`（用户已拍板的唯一执行文档）。
> 本轮完成 UI 修复与建构，覆盖批次 1~9；`verify_contracts.py` 双版本全绿。

1. ✅ **批次1 设计器三件套**：`src/designer_slots.py`（槽位/数量上限/默认模块/升级定义）、
   舰/机/坦数据层 modules/upgrades 分离、槽位分区布局、船体/机体/底盘选择器、
   保存校验条、升级加点区、槽位摘要/同类上限、变体中文名；测试
   `DesignerSlotsTest` / `VariantTypeConflictTest` / `DerivedNameFallbackTest` 等。
2. ✅ **批次2 角色编辑器收尾**：`common/characters` 路由、工作台双击分发、
   `open_character_editor(file_path, entity_id)`、顶层 desc 提取/写回、肖像预览/上传；
   测试 `CharacterDescTest` / `CharacterRouteTest` / `CharacterPortraitPreviewTest`。
3. ✅ **批次3 科技树画布修复**：tidy-tree 布局（子继承父中位、同层避让）、
   `GRID_X/GRID_Y` 间距加大、跨 folder 边不再丢弃（灰色虚线）、子科技 48×48 图标；
   测试 `TechLayoutTest`。
4. ✅ **批次4 事件+科技专用编辑器**：`event_data.py` + `event_editor_dialog.py`、
   `tech_data.py` + `tech_editor_dialog.py`（最小可用版）；`events` 路由、
   `SPECIAL_TYPE_KEYS` 加入 event；测试 `EventDataTest` / `EventEditorSmokeTest` /
   `TechDataTest` / `TechEditorSmokeTest`。
5. ✅ **批次5 地图州字段**：`state_loader` 解析 resources；`state_build_ops`
   写回 resources/VP/manpower/name；`map_editor_dialog` 州数据表单；测试 `StateResTest`。
6. ✅ **批次6 力量平衡编辑增强**：BOP 亮色化、`set_bop_range` / `set_bop_side_fields` /
   `insert_bop_decision` / `delete_bop_decision`；测试 `BopEditDataTest` / `BopDecisionCrudTest`。
7. ✅ **批次7 编制补充件**：地形三项（movement/attack/defence）、
   兵种编辑器 `sub_unit_editor_dialog.py`（完整表单）、命名组
   `names_group_dialog.py`（名称条目结构化）、OOB 地编 `showEvent` 初始视野。
8. ✅ **批次8 raw 兜底降级**：`ScriptBlockEditorDialog` 默认键值表+子块列表、
   原始 PDX 移入「高级 ▾」菜单；AI 7 编辑器 raw 文案统一
   「高级：原始 PDX（兜底）」；advisor traits 多选/字段化；ai_plan desc 双行。
9. ✅ **批次9 文档同步**：`docs/整合计划.md` 状态表、
   `docs/整合计划.md` 3d 表、`docs/UI评估报告.md` 批次表已同步；
   `verify_contracts.py` 双版本全绿、`ui_gap_probe` 相关类型缺口已收敛。

### 6.23 已完成：第一份执行文档剩余源码缺口 + §0.x 补充（2026-08-23）

> 按 `docs/整合计划.md` 开工，先补 `docs/整合计划.md` 中批次 4~8 的 🔶 差距、
> §0.x 四条补充项，并完成批次 9 收尾。7 个并行子代理实现 + 监督整合。

1. ✅ **批次4 完整版**：事件/科技编辑器从最小可用补到完整版：事件支持
   `unit_leader_event`、文件级其他字段表（`@常量`/`add_namespace`/非事件键）；
   科技支持 `technologies` 包装与零散 folder 顶层、allow/ai_will_do/加成块结构化、
   画布双击/右键联动；测试 `tests/test_batch4_event_tech.py`。
2. ✅ **批次5 完整版**：地图州字段 resources/VP/manpower/州名/state_category 改
   键值表/两列表/双行表单；写回封装与 StateData.reload；测试
   `tests/test_batch5_state.py`。
3. ✅ **批次6 完整版**：BOP 区间卡（min/max + modifier 键值表）、势力卡、
   决议新建/编辑/删除/结构化效果块；测试 `tests/test_batch6_bop.py`。
4. ✅ **批次7 完整版**：兵种编辑器完整表单（22 属性/need/terrain 三列/OtherFields）、
   division_names_group 命名组对话框、OOB 初始视野最大连通区；
   测试 `tests/test_batch7_oob.py`。
5. ✅ **批次8 完整版**：ScriptBlockEditorDialog 默认键值表+子块列表、AI 七编辑器
   raw 统一高级菜单、advisor traits 多选/字段化/available 结构化、ai_plan desc
   双行+focus_order；测试 `tests/test_batch8_ai_structured.py`。
6. ✅ **§0.x-1 设计器变体高级字段**：三设计器变体表单补 design_team（mio:）/
   parent_version/obsolete/icon；不臆造 desc/自定义 stats；测试
   `tests/test_batch0x1_variant_fields.py`。
7. ✅ **§0.x-2 角色未知块结构化**：未知块改 ScriptBlockEditorDialog 可编辑，
   解析 `instance = { ... }` 包装；测试 `tests/test_batch0x2_character_unknown.py`。
8. ✅ **ui_gap_probe specs 更新**：event/tech/character/state/bop/country_history
   均已同步；`event/tech/character/bop --max-files 0` 缺口为 0；
   state/country_history 按长期豁免说明记录。
9. ✅ **全量验证**：`verify_contracts.py` 双版本全绿（Python 3.14；
   子进程已固定 UTF-8 环境，规避 Windows GBK 解码噪音）。

### 6.24 已完成：Python 升级到 3.14（2026-08-23）

> 用户指示「先进行 python 升级评估，将项目内 python 升级到当前环境的 python」。
> 已按 F9 完成评估并执行升级：`.venv` 从 Python 3.8.10 → **Python 3.14.5**（Windows）。

1. ✅ **兼容性评估**：WSL 3.14.4（`/root/hoi4_builder_venv`）与 Windows 3.14.5
   （新建 `.venv`）双版本 `verify_contracts.py` 均退出码 0；契约测试约 395 全绿。
2. ✅ **旧环境保留**：原 `.venv`（3.8.10）已改名 `.venv_py38_backup`，回滚只需
   把目录名换回（`启动.bat` 无需改动）。
3. ✅ **工具修复**：
   - `check_write_discipline.py` / `verify_contracts.py` 跳过所有 `.venv*`，
     避免新 venv 的 site-packages 被当成项目源码扫描；
   - `verify_contracts.py` 子进程显式注入 `PYTHONIOENCODING=utf-8` +
     `PYTHONUTF8=1`，并 `encoding="utf-8", errors="replace"`，根治 Windows
     中文 GBK 输出导致的 UnicodeDecodeError。
4. ✅ **依赖**：Windows `.venv` 安装 PyQt6 6.11.0（Qt 6.11.1）、numpy 2.5.2、
   Pillow 12.3.0、mcp 2.0.0；新增根目录 `requirements.txt`（Windows 同源依赖）。
5. ✅ **文档同步**：AGENTS §2/§4.5、README、`docs/整合计划.md` P9、`docs/整合计划.md` F9
   已更新为 3.14 事实；3.8 语法限制解除（新代码可用 walrus/match/list[str] 等）。

> 当前状态：第一份执行文档批次 1~9 全部落地；P10~P39 仍在原型试用拍板阶段，
> 后续按 `docs/AI与通用UI执行方法.md` 推进（尚未创建）。

## 7. 项目周边参考

- **Scenario Forge**（分析对象，克隆在 `E:\scenario-forge-main`）：
  浏览器端 HOI4 地图编辑器，分析报告 `scenario_forge分析报告.md`；
  本项目移植了它的工程方法论（原子写/健康检查/可执行契约/主题令牌）。
  它的 `AGENTS.md`（SF-ATS 验证契约）是本文档的参考模板。
- 关键文档：`docs/验证契约.md`（写入纪律/契约清单）、`docs/科技图标存储规则.md`、
  `README.md`（功能全览）、`docs/接口复现报告.md`。
- 按 §4.10 规范，不再产出/提交 UI 预览截图。
