# HOI4 模组编辑器

一个面向《钢铁雄心4》（Hearts of Iron IV）MOD 作者的桌面编辑器，基于 Python + PyQt6 开发。
提供从「创建 Mod」到「编写国策 / 角色 / 事件 / 决议 / 理念 / 科技」的完整可视化编辑工具链，
并内置 PDX 脚本解析、多源翻译、图标管理与 AI 辅助创作能力。

## 主要功能

### 工作台（默认界面）

左侧按内容类型分类（角色、民族精神、国策、事件、决议、科技、地块、剧本、MIO、装备、兵种、历史档、GUI 等 90+ 类型），右侧列出对应文件：

- **双击文件**：国策进入设计视图；`history/units` 初始部队直接进入师编制设计器（按军种自动拉起舰艇/飞机设计器）；图标型内容展示实体图标画廊；其余进入树形编辑器
- **类型分组**：已制作专门编辑器的类型（国策/科技/初始部队/力量平衡）固定在列表上方，其余通用类型用分隔线分组，便于快速定位
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

模板存放在项目根目录 `templates/` 中，按类型分目录管理（国策、事件、决议、角色、科技、AI 战略、触发动作、意识形态、占领法、**动态修正**等 50+ 类，分文件级/节点级）：

- 工作台与文件树均可「从模板新建文件」，支持变量替换
- 可将任意文件/块一键存为模板复用
- **设计器模板**独立存放在 `design_templates/`（编制/舰艇/飞机/坦克），
  由设计器「💾 存为模板 / 📥 模板新建」使用，普通模板搜索器不会搜到

### 文件类型覆盖与覆盖报告

- 工作台内容类型覆盖游戏 `common/` 全部 78 个子目录 + 顶层目录（93 种类型，含 `.lua/.yml/.gfx/.mod` 扩展名）
- 菜单「工具 → 文件类型覆盖报告…」：查看每种类型的打开方式（设计视图/图标画廊/专用编辑器/树形编辑器）、模板与当前 mod 文件数，可一键复制 Markdown 报告
- 仍直接使用树形编辑器打开的类型清单见项目根目录 `覆盖检查报告.md`

### 无文件模式

无文件模式（视图菜单开关）：不直接操作文件，而是对「实体/项目」操作，程序自动完成相关文件编写：

- **国策树图形化**：切到「国策」类型时先选择国家，跨文件合并绘制该国策树（标题显示「正在设计：XXX」），编辑/移动/删除/图标操作自动定位到国策所在文件
- 跨文件实体画廊（按国家分组）、国家筛选与「国家设置…」（复制/创建国家全套文件）
- **纯选择国家不写文件**：「🔍 选择国家…」仅切换浏览国家并显示「当前国家：GER（Germany）」，不会修改任何文件；「🌐 国家设置（复制/创建）…」才是显式写操作
- **设计器入口**：无文件模式同样可从工具菜单打开师编制/舰艇/飞机/坦克设计器（需先打开 mod 目录）
- 实体搜索（id/中文名/国家 tag）、统计信息（实体数/文件数）
- 新建实体：自动选择目标文件（当前国家文件优先）、模板骨架、**自动补本地化词条**
- 编辑/删除实体、选择/上传/拖拽图标（自动写 `.gfx`）
- **跨文件移动/复制实体**（自动提取块、写入目标文件、源文件同步清理）
- **本地化编辑**（名称/描述直接写 mod 翻译文件，画廊中文名即时刷新）

### 普通模式（文件模式）

- 双击任何类型文件：国策→设计视图；`history/units` OOB → 直接打开师编制设计器（按军种自动拉起对应设计器）；其余类型**先展示该文件实体画廊**（含图标值探测），再进树形编辑器；无实体概念的文件直接树形编辑
- **图标广泛搜索**：全局 gfx 纹理索引（mod+游戏全部 gfx 目录）兜底解析，科技/占领法/行动/意识形态等图标均可显示；支持 `GFX_xxx:帧号` strip 引用

### 翻译与本地化

- 读取游戏 `localisation` 与 mod 本地化文件，支持查看、修改、覆盖保存（只写 mod，不改游戏原始文件）
- 中英翻译编辑器、翻译文件自动加载（支持 JSON / YML / bundle）
- 词条注册表（自动整理 + 自定义词条）为搜索与 AI 提示词提供数据源

### 校验体系（工具菜单 → 校验 mod）

- 未知引用校验（特质/意识形态/GFX/理念，对照游戏数据字典）
- 重复 ID 检测（跨文件）
- **本地化缺失检测**：实体（国策/事件/决议/理念/角色等）在 mod 与游戏词条中均无翻译时报告
- **国策引用完整性**：prerequisite 悬空引用检测
- **一键补写本地化**：批量把缺失词条写入 mod 翻译文件（值取游戏英文原文，无原文用 id 占位）

### 导出前健康检查（工具菜单 → 导出前健康检查…）

发布 mod 前对 mod 目录做确定性检查（error / warning / info 三级清单，
error 级应修复后再发布；对话框可导出 JSON 报告、双击行定位文件）：

- **描述文件**：.mod 存在、path 指向目录存在、name 字段
- **编码契约**：非法 UTF-8（error）、BOM（warning）、CRLF（info）、空文件
- **括号配对**：引号/注释感知扫描全部脚本文件，抓缺 `}` / 多 `}`（真实 mod 已抓出 2 处）
- **引用完整性**：interface/*.gfx 定义的 sprite 贴图必须存在（mod 内或游戏本体回退）、
  悬空前置国策、科技图标 sprite 注册
- **本地化缺失**（复用校验体系）+ **重复 id**（focus/tech error、character warning）

### 写入纪律与可执行契约

- **原子写**：全部 mod 内容写入统一走 `write_utils.atomic_write_text`（临时文件 +
  `os.replace` 原子替换，写失败不破坏原文件；默认 UTF-8 无 BOM + LF；写前自动
  撤销快照）。本地化 `.yml` 保持 HOI4 BOM 惯例（`utf-8-sig` + `allow_bom=True`）
- **静态扫描**：`python tools/check_write_discipline.py` 用 AST 检出绕过原子写的
  新增直写（豁免登记在 `tools/write_discipline_allowlist.json`）
- **契约验证**：`python tools/verify_contracts.py` 一键运行——全模块语法编译
  （Python 3.8/3.13 双版本）+ 206 个契约单元测试（`tests/test_contracts.py`：
  原子写/BOM 拒绝/撤销恢复/健康检查检出/扫描器检出/地图渲染/地图编辑/建筑系统/
  编制/舰艇/飞机/坦克设计器/设计器模板/OOB 路由/工作台分组/动态修正模板/
  力量平衡数据与编辑器/AI 数据层与编辑器等 41 个测试类）+ 写入纪律扫描
- 详细规范见 验证契约.md

### 全局主题（亮色专业工具风，对齐 Scenario Forge 设计令牌）
- `theme.py` 集中设计令牌（背景 `#e7edf2` / 主色 `#1f4f7e` / 地图强调 `#b05b2d` /
  柔和语义色 / 圆角体系），`main.py` 启动时全局应用 QSS（失败静默回退默认样式）
- 覆盖：工具栏/菜单/按钮（默认/主/危险/成功/勾选态）/输入控件/表格/树/选项卡/
  停靠面板/滚动条/勾选/单选/分组框/提示/进度条；语义属性类
  （`setProperty("class", ...)`：card/title/sev_*/map_accent）
- 全项目内联颜色已统一到主题色阶（21 处次要色 + 师编制按钮/树编辑器标签/
  图标上传预览等暗色样式改为亮色）；画布内部绘制色（国策树/科技树/兵牌）保留
- 主题预览：`python tools/preview_theme.py` 生成「主题预览.png」

### 编制与装备设计器（师编制 / 舰艇 / 飞机 / 坦克）

参考游戏内设计器实现，亮色主题、完整读写（原版文件自动复制到 mod）、属性估算：

- **师编制编辑器**（打开 OOB 文件直接进入；无文件模式经工具菜单选择 OOB 文件）：
  顶部模板下拉 + 改名/锁定/新建/复制/删除 + 「🗺 地编（地图放置）」+「🛠 设计器 ▾」；
  左侧编制网格，右侧数据面板（基础/战斗数据/装备花费/地形适应性 8 徽章）
- **舰艇设计器**：读取 ship_hull 船体/模块/国家舰艇设计，槽位网格 + 模块选择，
  支持 upgrades 块写回、新建/复制/删除/改名、生产花费估算
- **飞机设计器**：读取 airframe/飞机模块/国家设计，modules 块写回；真实数据
  95 国 / 449 设计，He 111 等机型属性与游戏内高度吻合
- **坦克设计器**：读取 chassis/坦克模块/国家设计，modules 块写回；真实数据
  72 国 / 197 设计
- **共同能力**：
  - 空配件设计提示「游戏使用默认配置」；锁定槽位 🔒 禁用
  - 「同款 N 国」标签 + 「🔄 同步到所有同款」跨国家批量写回
  - 「💾 存为模板」「📥 模板新建」：模板存独立 `design_templates/` 目录，
    不会被普通模板搜索器搜到
- **入口**：OOB 文件按军种自动拉起对应设计器（陆军→编制、海军→舰艇、空军→飞机，
  混合同时打开多个）；工具菜单提供四个设计器入口；师编制编辑器顶部也可一键打开
  舰艇/飞机/坦克设计器

### 力量平衡工作台（Balance of Power）

工作台「力量平衡」类型已从通用树形编辑器升级为**仿游戏内 BOP 弹窗**：

- 数据层 `bop_loader.py`：解析 `common/bop/*.txt`（mod 优先）的 initial_value /
  left_side / right_side / decision_category / range / side；并关联
  `common/decisions/*.txt` 中对应分类块内的决议动作（过滤 DEBUG_*）
- 深色历史政治军事 UI（`bop_editor_dialog.py`）：黑绿配色、米白文字、
  中央滑块展示/编辑初始值、下方「动作」与「势力与修正」双页
- **本地化**：BOP 名称 / 势力 / 区间 / 动作 / 修正名自动显示中文
  （mod 优先；自动去除 `£BoP_*` 图标 token、解析 `$KEY$` 引用）
- **修正展示**：滑块下方实时显示当前区间修正；「势力与修正」页列出全部
  势力的每个区间与修正（含中文修饰名和百分比值）
- **编辑**：
  - 滑块 + 左势力/右势力/决策分类输入框，保存后原版自动复制到 mod 后原子写
  - 「✏ 编辑定义」打开 BOP 文件树编辑器，可完整编辑势力/区间/修正
  - 每个动作行「✏」打开对应决策文件树编辑器并定位该动作
- **文件模式**：双击 `common/bop/*.txt` 直接打开；**无文件模式**：双击力量平衡
  实体同样打开；工作台类型列表已将该类型置顶

### AI 内容编辑器（AI 战略计划 / 战略倾向 / 师模板 / 装备 / 海军 / 派系战区）

工作台 AI 类型已从通用树形编辑器升级为专用编辑器，并支持文件模式/无文件模式：

- **AI 战略计划 `ai_strategy_plans`**：`ai_plan_editor_dialog.py`
  - 左侧计划列表，右侧名称/描述/国策顺序
  - 「🎯 编辑国策顺序」打开**国策绘图点选器** `focus_order_picker.py`
    - 点击未选国策追加顺序；点击已选国策无动作
    - 右键已选国策：从该国策开始顺序 / 退出该状态 / 删除该顺序（含后续依赖国策）
    - 国策图标右下角黑框红底白字数字角标
  - 保存写回 `ai_national_focuses`、name、desc
- **AI 战略倾向 `ai_strategy`**：`ai_strategy_editor_dialog.py`
  - 策略组列表 + `ai_strategy` 表格（type/id/value），支持增删改
- **AI 师模板 `ai_templates`**：`ai_template_editor_dialog.py`
  - 角色模板/目标模板列表
  - 「✏ 编辑目标编制」调用现有**师编制编辑器**，保存写回 `target_template`
- **AI 装备 `ai_equipment`**：`ai_equipment_editor_dialog.py`
  - 设计组/变体列表
  - 「✏ 编辑设计」按 category 调用**飞机/坦克/舰艇设计器**，保存写回 `target_variant`
- **AI 海军 `ai_navy`**：`ai_navy_editor_dialog.py`
  - 三页签：目标 / 舰队 / 特遣队
  - 目标页可编辑 objective_type/min/max priority；复杂块走树编辑器
- **AI 派系战区 `ai_faction_theaters`**：地图红色描边 + 战区列表
  - 地图编辑器新增「AI派系战区」图层，红色描边标出覆盖区域
  - 「战区列表」双击战区打开树形编辑器并定位
- **内容少的 AI 类型**：AI区域/科研权重/态度/人格
  - 不建专用界面，提供系统模板 + 通用树形编辑器

### 地图编辑与区域划分（工具菜单 → 地图编辑… / 区域编辑…）

**可复用地图画布 `map_canvas.py`**：基于 2^24 LUT 地块矩阵的 QGraphicsView 组件——
底图 + 多层可替换叠加层 + 工具模式（手型平移/点选/涂色/矩形框选/**多选**）+ 地块高亮
（numpy 掩码合成，LRU 缓存 + 白色描边）+ 框选矩形（框内地块 O(1) 集合）；信号
province_clicked/hovered/paint_province/rect_selected，供编辑/点选/框选共用。

**高性能渲染（不牺牲锐利度）**：
- **矢量边界 + 多边形填充**：从省 ID 矩阵向量化提取边界线段（磁盘缓存后 7ms），
  `map_fill.py` 用 Marching Squares 等价轮廓 + Douglas-Peucker 简化，高倍缩放时
  底图切换为矢量多边形填充，省内部与边界都锐利不模糊
- **瓦片缓存 + 边界烘焙**：按缩放档和可见区域渲染一次到离屏位图，平移命中缓存时
  整帧纯 blit；边界线直接烘焙进瓦片像素，实测 30× 平移约 21ms/帧（旧实现 3.7~8.5s/帧）
- **滚轮预览缩放**：滚动期间用已有瓦片实时预览，停止后（默认 300ms）重渲染高质量帧
- 阈值与间隔可调：settings.json 的 `map_zoom_threshold`（默认 2.5）、
  `map_zoom_settle_ms`（默认 300）、`map_initial_zoom`（默认 1.3）

**地图编辑界面**（工具菜单 → 地图编辑…）：
- 三栏布局：左=建筑类型图标按钮区（可建造纯图标网格 + 不可建造地标列表），
  中=画布，右=地块信息面板（地块/州/建筑/归属/国家颜色等，固定宽度）
- 模式：手型平移（兼点选）/ 点选 / 涂色 / 框选 / **多选**；悬停省份青色高亮，
  选中省份黄色高亮 + 白色描边，**选中地块所属州以黄色粗描边圈出**（州轮廓提示）
- 图层开关：国家色（按州归属着色 + 边界线 + 国界线）/ 地块边界 / 地形类型
  （terrain.bmp）/ 地形立体感（heightmap.bmp → hillshade 伪 3D，取巧零生成成本）
- **建筑系统**：59 种建筑类型（中文名/图标/悬停描述/效果），图标放大、
  左侧面板加宽、底部无水平滚动条；可放置省/州级建筑，原版州文件自动复制到 mod 后原子写回
- **国家颜色**：读取 mod+游戏 common/countries 的 color，可修改并写回 mod
- 涂色改归属：点击地块 → 选择国家 → 块级写回 mod 州文件（原子写 + 撤销快照，
  州在游戏本体时自动复制到 mod）
- 框选/多选：列出地块数 + 涉及州 + 一键复制 id 列表；输入 TAG/地块 id 定位

**区域编辑（框选划分）**（工具菜单 → 区域编辑…）：
- 识别定义区域的 mod/游戏文件：strategicregions / supplyareas / states
  （mod 优先，游戏文件只读不写）
- 地图框选地块 → 新建区域（自动/手动 id）｜追加到选中区域｜从选中区域移除｜删除区域
- 块级写回（保留注释与其他块），原子写 + 撤销；契约测试覆盖解析/写回/优先规则

**Scenario Forge 移植（工具菜单三项）**：
- **覆盖规则与增量报告…**（`overlay_rules.py`）：mod 覆盖原版的**显式规则链**
  （vanilla 只读层 + mod 覆盖层，include/exclude + 质量分级 direct_copy/
  manual_reviewed/approx/blocker）+ **文件级 delta 增量模型**（每个 mod 文件
  分类 new/override/identical，difflib 行级增删统计），可导出 JSON（原子写）
- **图标库 manifest…**（`icon_manifest.py`）：扫描 mod+游戏全部 spriteType
  定义 → sprite 名/贴图路径/来源/尺寸/md5/贴图存在性，可导出 JSON；
  API/MCP 同步暴露（`/api/icon_manifest`、`get_icon_manifest`）
- **单位标牌库…**（`unit_counter_library.py`）：从游戏本体
  `gfx/interface/counters/` 提取各军种地图兵牌（onmap_*.dds → PNG +
  manifest.json），浏览/搜索/双击复制路径；命令行导入：
  `python tools/import_unit_counter_library.py --game <游戏目录>`

### 项目级联动（无文件模式国策树右键 → 新建国策项目）

填一个表单（国家 / 国策 id / 中文名 / 坐标 / 勾选项），程序自动完成：

- 国策块写入该国国策文件（自动关联完成事件）
- 触发事件 `events/<TAG>_events.txt`
- 决议 `common/decisions/<TAG>_decisions.txt`
- 图标占位（130×130 PNG + `.gfx` 精灵定义）
- 本地化词条（名称/描述，中英原文）

### AI 集成（工具菜单 → AI 创作助手 / AI 设置）

- OpenAI 兼容接口直连（DeepSeek/OpenAI/通义千问等，标准库 urllib，无额外依赖）
- 创作助手流程：选择内容类型 → 输入需求 → 后台线程生成 → 解析代码块预览 →
  选择写入目标文件（国策自动插入 focus_tree 包装块，其余追加）→ 落盘并刷新
- AI 设置：API 地址 / Key / 模型 / 温度（仅存本地 settings.json）

### 体验与架构补强

- **撤销文件写入**：画布 Ctrl+Z 或「工具 → 撤销上次文件写入…」恢复上次写入前内容
- **实体收集增量缓存**：文件 (mtime, size) 未变时跳过解析，切换类型提速约 10 倍
- **配置向导**：文件菜单「配置向导…」，首次启动未配置时自动弹出
- **游戏数据参考**：工具菜单「游戏数据参考…」，浏览/搜索/复制游戏国家 tag 与中文名
- **科技树画布（与国策树同一画布）**：工作台选中「科技」类型后——文件模式双击
  科技文件、右键「🔬 打开（科技树画布）」，或无文件模式自动绘制——在右侧画布
  按国策树风格绘制科技树（folder 分组、path 连线为边、BFS 分层并行铺开、
  多棵 folder 树瀑布流排列），非树科技（由国策/事件/决议等解锁，无 folder
  无连线的科技）在下方网格分散展示，子科技画在父节点槽位；节点显示科技图标
  （dds/png 均可，无图标显示占位）；右键节点可上传科技图标（程序自动编写
  gfx sprite 注册），双击节点打开定义文件树编辑器
- **科技图标上传（自动编写 gfx）**：科技树视图右键节点 →「上传科技图标…」，
  图片等比缩放存入 `gfx/interface/technologies/<科技id>.png`，程序自动注册/更新
  `GFX_<科技id>_medium` sprite 到 `interface/*.gfx`（已有 sprite 原位更新、
  保留文件其余内容；无则新建 `technologies_mod.gfx`），科技定义文件无需修改
  （引擎按 sprite 名约定解析，规则详见 科技图标存储规则.md）

### 外置 Agent 接口（工具菜单 → 外部接口）

让外部程序 / AI Agent 直接驱动本软件制作 mod，两种方式共用同一套操作核心：

**1. 本地 HTTP API**（零依赖，任意语言可调）
- GUI 内嵌：工具菜单「外部接口…」启动/停止，改动自动刷新界面
- 独立进程：`python api_server.py --mod <mod目录> [--game <游戏目录>] [--port 8765]`
- 仅绑定 127.0.0.1 + 随机 Bearer token 鉴权
- 端点：`/api/status` `/api/types` `/api/entities`（增删改查）
  `/api/files`（文件列表/整文件读写，含路径越界防护）
  `/api/project`（项目级联动）`/api/localisation` `/api/validate` `/api/templates`
  `/api/tech_icon`（POST：`{tech_id, image_base64}` 上传科技图标，自动注册
  `GFX_<科技id>_medium` sprite 并编写 gfx 文件）
  `/api/icon_manifest`（图标库清单：sprite 名/贴图/来源/尺寸/md5/存在性）
  `/api/overlay_report`（mod 覆盖原版的规则分层 + 文件级增量报告）

**2. MCP Server**（AI Agent 原生标准，如 Claude Code / Cline / DSH）
- `python mcp_server.py --mod <mod目录>`（stdio 传输）
- 17 个工具：get_status / list_types / list_entities / get_entity /
  create_entity / update_entity / delete_entity / create_focus_project /
  write_localisation / validate_mod / list_templates /
  **list_files / read_file / write_file**（文件级操作）/
  **upload_tech_icon**（`{tech_id, image_base64}` 上传科技图标 + 自动 gfx）/
  **get_icon_manifest**（图标库清单查询）/ **get_overlay_report**（覆盖增量报告）
- 优先用官方 `mcp` 库（pip install mcp）；未安装时自动回退到内置零依赖
  stdio 实现（协议 2024-11-05，标准库即可，无新依赖）

Agent 配置示例（Claude Code）：
```json
{ "mcpServers": { "hoi4-mod-builder": {
    "command": "python",
    "args": ["E:/hearts_of_iron_builder/mcp_server.py", "--mod", "E:/mods/my_mod"] } } }
```

### AI 效果提示词助手

- 基于效果器/触发器词条生成带格式的 AI 创作提示词，可复制到任意 AI（ChatGPT/Gemini/DeepSeek 等）
- 粘贴 AI 回复后自动解析标记块并预览，确认后自动回填到树编辑器

### Mod 创建与管理

- 一键创建 Mod 工程：生成 `.mod` 描述文件、`descriptor.mod`、GFX 骨架与本地化骨架
- 路径配置持久化（游戏目录、mod 目录、`.mod` 文件目录）

## 运行环境

- Python 3.8+（启动器使用 `.venv` = Python 3.8.10；开发/测试同时验证 3.8 与 3.13 兼容）
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

菜单栏「文件 → 配置向导…」引导完成全部路径配置（首次启动未配置时自动弹出）：

1. **选择 HOI4 目录**：游戏根目录（用于读取本地化与图标资源）
2. **选择默认 mod 目录**：存放 mod 内容子文件夹的目录
3. **选择 .mod 文件目录**：存放 `.mod` 描述文件的目录
4. **打开 Mod**：选择要编辑的 mod 内容目录

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
├── map_loader.py           # 地图数据（省 ID 矩阵/底图/国家色/地形）
├── map_canvas.py           # 可复用地图画布（模式/选区/矢量渲染/扩展点）
├── map_vector.py           # 矢量边界线段提取（磁盘缓存）
├── map_fill.py             # 矢量多边形填充（Marching Squares + DP + 缓存）
├── map_editor_dialog.py    # 地图编辑界面
├── map_region_ops.py       # 区域文件解析/写回
├── region_editor_dialog.py # 区域编辑界面
├── state_loader.py / state_edit_ops.py  # 州数据与归属写回
├── state_build_ops.py      # 州建筑/国家颜色写回（原版自动落 mod）
├── building_lib.py         # 建筑类型/国家颜色数据（图标/描述/效果）
├── oob_loader.py           # OOB/装备/师属性数据（含 detect_oob_kinds）
├── division_editor.py      # 师编制编辑器（v2）
├── initial_oob_editor.py   # OOB 入口工厂（按军种自动拉起设计器）
├── ship_design.py / ship_design_dialog.py    # 舰艇设计器
├── plane_design.py / plane_design_dialog.py  # 飞机设计器
├── tank_design.py / tank_design_dialog.py    # 坦克设计器
├── design_template.py      # 设计器模板（独立 design_templates/）
├── oob_map_editor.py       # 初始部队地图放置（基于 MapCanvas）
├── overlay_rules.py        # 覆盖规则链 + 增量报告（SF 移植）
├── overlay_report_dialog.py# 覆盖规则与增量报告对话框
├── icon_manifest.py        # 图标库 manifest（SF 移植）
├── icon_manifest_dialog.py # 图标清单对话框
├── unit_counter_library.py # 单位标牌库提取/加载（SF 移植）
├── unit_counter_library_dialog.py  # 标牌库浏览对话框
├── settings.json           # 运行时配置
├── templates/              # 模板库（按类型分目录）
├── design_templates/       # 设计器模板（编制/舰艇/飞机/坦克）
├── translations/           # 外部翻译包 / 词条文件
├── bop_loader.py           # 力量平衡数据层（common/bop + 决策动作）
├── bop_editor_dialog.py    # 力量平衡专用工作台（深色历史政治军事 UI）
├── tests/test_contracts.py # 契约测试（206 个用例）
└── unit_counter_library/   # 从游戏导入的单位标牌库（icon/ + manifest.json）
```

## 数据目录说明

- `settings.json`：路径与界面模式配置，首次运行自动生成
- `templates/`：模板库，按类型分目录，`usage.json` 可覆盖类型默认用途
- `design_templates/`：设计器模板（division/ship/plane/tank 四个子目录）
- `translations/`：自动加载的外部翻译包，以及 `effect_terms.json` / `custom_terms.json` 词条文件

## 技术栈

- **GUI**：PyQt6
- **图像**：Pillow + numpy（DDS 纹理解码）
- **配置**：JSON 持久化
- **解析**：自研 PDX 脚本解析器 / 国策解析器
