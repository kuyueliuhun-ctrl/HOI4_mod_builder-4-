# 多 Mod 冲突检查 与 子 Mod 制作 —— 设计计划

> 状态：计划（待评审）
> 提出时间：6.89 之后（commit `8e70484`）
> 关联：`docs/现状评估报告.md`（性能/解析底座已就绪）、`docs/踩坑索引.md` PIT-PARSE-010（原版个别文件严格解析失败——冲突扫描必须用 quick-scan 容错口径）

---

## 0. 现状基础（实测确认）

设计前对真实环境做了探查，以下事实直接决定方案形态：

### 0.1 播放集数据源（全部实测可读）

| 数据源 | 位置 | 内容 | 可靠性 |
| --- | --- | --- | --- |
| `launcher-v2.sqlite` | HOI4 用户文档目录 | `playsets(id,name,isActive)`、`playsets_mods(playsetId,modId,enabled,position)`、`mods(id,gameRegistryId,dirPath,source,status)`、`mods_dependencies` | 播放集的**权威来源**；游戏运行中可能被锁，须只读打开 |
| `dlc_load.json` | HOI4 用户文档目录 | `{"enabled_mods":["mod/ugc_…mod",…],"disabled_dlcs":[]}` | **游戏实际加载顺序的 ground truth**（启动器启动播放集时写入） |
| `.mod` 描述文件 | `mod_file_path`（settings.json） | `name/path/replace_path/dependencies/supported_version/tags/remote_file_id` | `src/mod_descriptor_loader.py` 已有完整解析/序列化 |

实测样例（本机）：
- `dlc_load.json`：`enabled_mods` 顺序即加载顺序，**数组越靠后越晚加载、越晚的覆盖越早的**。
- sqlite `mods` 表：本地 mod `dirPath` 指向 `E:\mods\…`，创意工坊 mod 指向 `E:\SteamLibrary\…\workshop\content\394360\<id>`（`source='steam'`）。
- `.mod` 中 `replace_path` 既有目录级（`common/abilities`）也有单文件级（`common/ai_equipment/FRA_naval.txt`）。
- `dependencies` 按 **mod name（字符串）** 匹配，不是路径。

### 0.2 HOI4 的 mod 加载语义（冲突判定口径）

1. 加载链：原版 → 播放集 mods 按 `position`/数组顺序依次叠加。
2. **整文件覆盖**：两个 mod 存在同相对路径文件（如都有 `common/national_focus/xxx.txt`）→ 只有**加载顺序靠后者**生效，靠前者整文件被屏蔽（shadowing）。
3. **同目录不同文件名都加载**：跨文件的同 id 实体（focus/idea/tech/character/event…）由游戏按加载顺序**后者覆盖前者**（event 等特殊域表现为重复注册）。
4. **`replace_path`**：声明后该目录（或单文件）的**原版内容与其他 mod 内容全部清空**，只保留声明者的；这是最常见的"隐形冲突"来源。
5. 本地化：`localisation/<lang>/` 下同名键跨 mod 后者覆盖。
6. 依赖：descriptor `dependencies` 用 name 匹配，缺失依赖 mod 时游戏仍可加载但行为未定义。

### 0.3 可复用的既有设施

| 设施 | 复用点 |
| --- | --- |
| `mod_descriptor_loader.extract_fields` | .mod 解析（name/path/replace_path/dependencies） |
| `entity_scanner`（6.89 后 O(n) quick-scan） | 实体扫描；`_scan_files` 已是「mod 优先、原版回退」的 2 层读 |
| `unique_id_scanner._scan_focus/_scan_event/…` | 各实体域的 id 提取规则 |
| `export_health.HealthIssue/HealthReport` | 冲突报告的数据结构与导出模式 |
| `state_build_ops.ensure_file_in_mod`（72 处调用） | 写路由唯一汇聚点（功能二的关键接入点） |
| `ai_loader._scan_files` / `localization_mgr.load_loc_yml_dir` | 分层读取模式的两个样板 |
| `workbench._iter_rel_files` + `main_window_docks` 文件树 | 子 mod 模式的合并树挂载点 |
| `write_utils.atomic_write_text`、`pdx_span.find_block_range` | 原子写、块定位 |

---

## 1. 功能一：多 Mod 冲突检查

### 1.1 目标

选一个播放集（或 `dlc_load.json` 当前集），一次性报告该播放集内的所有冲突，分级输出、可跳转、可导出。**只读功能，不写任何 mod 文件**（导出报告除外）。

### 1.2 模块划分

```
src/playset_loader.py      ← 播放集读取（功能二共用底座）
src/conflict_scan.py       ← 冲突分析（纯函数，不依赖 PyQt）
src/conflict_report_dialog.py ← 报告 UI（树形分组 + 跳转 + 导出）
```

### 1.3 playset_loader.py

```python
@dataclass
class PlaysetMod:
    registry_path: str      # "mod/ugc_3254004005.mod"（相对用户文档目录）
    content_dir: str        # 绝对内容目录
    name: str = ""          # descriptor name
    position: int = 0       # 越大越晚加载
    source: str = ""        # "steam" | "local"
    replace_paths: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    supported_version: str = ""
    descriptor_ok: bool = True

@dataclass
class Playset:
    name: str               # 播放集名 / "dlc_load(最近启动)"
    mods: list[PlaysetMod]  # 已按加载顺序（先→后）排序

def hoi4_user_dir(settings) -> str   # 由 mod_file_path 推断父目录；可被 settings["hoi4_user_path"] 覆盖
def list_playsets(user_dir) -> list[dict]      # sqlite 只读（?mode=ro&immutable=0），失败回退 dlc_load
def load_playset(user_dir, playset_id=None) -> Playset   # None = dlc_load.json 当前集
def resolve_mod_content(user_dir, registry_path, mods_table) -> str
```

要点：
- sqlite3 为标准库，无新依赖；连接串 `file:…launcher-v2.sqlite?mode=ro` 防锁、防写坏。
- mod 路径解析优先 sqlite `mods.dirPath`，缺失时读 `.mod` 的 `path=` 字段（实测两条路径都有）。
- `status='installation_failed'` 但目录在盘上的本地 mod（实测存在）**照常纳入**，在报告元信息里标注状态。
- 用户文档目录自动推断：`mod_file_path` 的父目录；settings.json 增加可选键 `hoi4_user_path`（写入走 main_window，已有 `allow_paths: settings.json` 豁免）。

### 1.4 冲突分析 conflict_scan.py（分级模型）

全部纯函数 + 可注入文件系统根，便于测试用临时目录构造。

**L0 元信息冲突（秒级，只读描述符）**

| 类型 | 判定 | 严重度 |
| --- | --- | --- |
| 版本不兼容 | `supported_version` 与游戏 `launcher-settings.json` 的版本 major.minor 不匹配 | warning |
| 缺失依赖 | descriptor `dependencies` 中的 name 在播放集内找不到对应 mod | error |
| 重复注册 | 同 `content_dir`（realpath）或同 `remote_file_id` 出现多个条目 | error |
| 循环依赖 | dependencies 图成环（拓扑排序检出） | error |

**L1 文件级 shadowing（O(播放集总文件数)，一遍 os.walk）**

- 对每个相对路径收集 `[(mod_position, mod_name), …]`；长度 ≥2 即冲突，**取最大 position 为胜者**。
- `replace_path` 处理：先收集声明者；其余 mod / 原版在 replace 目录（或单文件）下的文件标记为 `replaced`（"被 replace_path 清空"），**这类冲突优先级最高**——被屏蔽者往往完全不知情。
- 输出维度双索引：按「冲突路径」和按「mod 对 (victim, winner)」。
- 默认不含原版层（原版被 mod 覆盖是正常行为）；对话框提供「含原版层」开关。

**L2 实体级 id 冲突（复用 quick-scan，容错口径）**

- 域清单（首版）：`common/national_focus`、`common/ideas`、`common/technologies`、`common/characters`、`common/decisions`+`decisions/categories`、`common/dynamic_modifiers`、`common/opinion_modifiers`、`events/*`、`common/units`、`history/countries`（状态/ OOB 引用键）。
- 判定：**同目录、不同文件**（同文件多定义已有单文件重复检测，不属跨 mod 冲突）中出现同 id → 后加载者覆盖前者，报告 `id / 各定义位置 / 胜者`。
- 解析用 `entity_scanner` quick-scan（6.89 已线性化，530KB 文件 0.083s），**解析失败的文件按 PIT-PARSE-010 口径跳过并计数**，不让单个坏文件拖垮整个扫描。
- events 域单独标注"重复注册（都会加载，后者先生效）"语义。

**L3 本地化键冲突**

- `localization_mgr.parse_loc_yml_file` 逐文件提键；同语言 section 内跨 mod 重复键 → 后者覆盖。文件量可能很大，按 mtime 缓存（沿用 `ai_loader._cached` 模式）。

**L4 悬空引用联动（P2，报告性）**

- 被屏蔽文件（L1 loser / replace_path 受害者）中定义的实体，被**存活文件**引用（focus prerequisite、idea 引用等）→ "引用失效"提示。首版只对 focus/idea 两个域做，后续扩。

### 1.5 报告 UI（conflict_report_dialog.py）

- 顶部：播放集选择（`list_playsets` 列表 + "最近启动"项）、「含原版层」「本地化扫描」开关、扫描按钮 + QProgressDialog（分域回调推进）。
- 主体：QTreeWidget 三级分组 `严重度 → 冲突类型 → 具体条目`；每条目列 `victim → winner / 位置 / 说明`；双击跳转文件（复用主窗口打开管线）。
- 底部：统计条（各严重度计数 + 扫描耗时 + 跳过文件数）；「导出 JSON / 导出 HTML」（`export_health.HealthReport.to_json` 模式，HTML 独立自包含页）。
- 入口：菜单「工具 → 多 Mod 冲突检查」；`main_window.on_conflict_check`（要求已配置 `mod_file_path`/游戏目录，不要求打开具体 mod）。

### 1.6 性能预算（与 6.89 性能契约同风格）

| 项 | 预算 | 契约测试 |
| --- | --- | --- |
| L1 shadow 扫描 | 10 个 mod × 2 万文件 < 5s；**翻倍输入耗时比 ≤ 3.0** | min-of-3 计时契约 |
| L2 实体扫描 | 复用 quick-scan 线性口径，禁用严格解析 | 解析失败计数不抛异常 |
| L3 本地化 | mtime 缓存命中后二次扫描 < 1s | 缓存契约 |
| UI | 扫描在分域回调内推进进度条；主线程扫描（PIT-PERF-006 口径：线性化后无感），单域超 3s 才考虑移线程 | — |

### 1.7 测试计划

`tests/test_playset_loader.py`：内存 sqlite fixture 造 playsets/mods 表 → 读取排序/回退 dlc_load/锁库回退/路径推断。
`tests/test_conflict_scan.py`：临时目录多 mod fixture → 整文件覆盖胜者、replace_path 目录级+文件级、跨文件同 id（focus）、本地化键冲突、缺失依赖、重复注册、坏文件跳过、shadow 翻倍计时契约。

---

## 2. 功能二：子 Mod 制作

### 2.1 概念模型

子 mod = **一个真实可玩、可发布的独立 mod**，通过 descriptor `dependencies` 声明依附底层 mod；在编辑器内进入"子 mod 模式"后：

- **读取**：层栈 = `[子mod, 底层mod们（播放集顺序）, 原版]`，自上而下取第一个命中 —— 播放集中**所有** mod 的内容都可见可打开。
- **写入**：一律落子 mod 目录。新建文件、从底层 mod 打开后编辑保存 → 在子 mod 创建覆盖副本（叠加 patch）；底层 mod 与创意工坊目录（只读）永不写入。
- 游戏侧：子 mod 与底层 mod 一起勾进播放集，子 mod 排在**所有底层之后**（加载顺序最末 = 覆盖优先级最高）。

### 2.2 核心抽象 src/mod_stack.py

```python
@dataclass
class ModLayer:
    name: str          # 显示名
    path: str          # 内容目录绝对路径
    writable: bool     # 仅 index 0 为 True
    kind: str          # "submod" | "mod" | "vanilla"

class ModStack:
    def __init__(self, layers: list[ModLayer]): ...
    def scan_rel(self, rel_dir, ext=".txt") -> list[ResolvedFile]
        # 合并视图：每个文件标注来源层；同 rel_path 高层遮蔽低层
    def resolve(self, rel_path) -> str | None       # 顶层命中
    def resolve_all(self, rel_path) -> list[str]    # 各层命中（冲突检查联动用）
    def write_target(self, rel_path) -> str         # 恒为 layers[0].path
    def copy_up(self, rel_path) -> str              # 从命中层复制覆盖副本到子 mod

# 模块级激活上下文
def set_active_stack(stack: ModStack | None)   # None = 传统模式
def active_stack() -> ModStack | None
def from_paths(sub_mod="", mod_paths=(), vanilla="") -> ModStack
```

**向后兼容关键**：传统模式 = 2 层栈 `[mod(writable), vanilla(ro)]`。`from_paths` 提供适配，旧调用方零改动即可获得同一语义。

### 2.3 接线策略（控制侵入面，三个汇聚点优先）

| 汇聚点 | 调用面 | 改法 |
| --- | --- | --- |
| `state_build_ops.ensure_file_in_mod` | **72 个文件** | 内部首行委托 `mod_stack`：激活时 `copy_up` 语义（文件在子 mod → 直接用；在底层/原版 → 复制到子 mod）；未激活走原实现，行为逐字节不变 |
| `ai_loader._scan_files` | 全部 AI/通用加载器 | 改调 `active_stack().scan_rel(rel_dir)`（回退：无栈时保持 (mod, hoi4) 两层） |
| `localization_mgr.load_loc_yml_dir` | 本地化全局 | 多目录层栈扫描 + ref 层 |

剩余 ~29 个直接 `os.path.join(mod_path, …)` 的文件（多为独立对话框）**不在首批铺开**：子 mod 模式下这些对话框照常工作（它们打开的文件路径来自合并树，天然已指向正确来源层），只有"新建"场景需接入 `ensure_file_in_mod` 的已覆盖路径。逐个接入列入阶段 D。

### 2.4 子 Mod 向导 src/submod_wizard.py

1. **选播放集**：`playset_loader.list_playsets` 列表（+「最近启动」）；默认取 `dlc_load.json` 当前集。
2. **勾选底层 mod**：列出该播放集全部 enabled mod（名称/来源/内容目录/版本），勾选 1..n 个作为依附对象；**读取范围 = 整个播放集**（用户明确要求），勾选项仅决定 `dependencies` 声明与树中标记；提供「仅读取勾选项」开关（默认关）。
3. **填子 mod 信息**：名称/文件夹名（默认 `submod_<底层名>`）/版本（默认 `1.19.*`）/tags；落位：内容目录 = `mod_folder_path/<folder>`，`.mod` 文件 = `mod_file_path/<folder>.mod`。
4. **生成**：复用 `mod_creator.build_mod_files` 思路 + `dependencies` 块（`mod_descriptor_loader.format_mod_entries` 负责引号转义）→ `descriptor.mod` + `.mod` + `interface/<folder>.gfx` + 空白本地化；**不**生成 country_tags。
5. **激活**：写入 settings（`submod_active=true`、`submod_path`、`submod_bases=[…]`），`apply_path_settings` 走 `ModStack.from_paths` 激活；状态栏常驻徽标「子mod：<名> ← <底层1> + <底层2>」，点击弹层栈详情。
6. **退出模式**：恢复原 `mod_path`，栈置空。再次进入可从 settings 快速恢复上次子 mod。

写 settings 只发生在 `main_window`（allow_paths 已豁免 `settings.json`）；向导本体通过信号回调主窗口落盘，自身不碰 settings.json，避免新增写规范豁免。

### 2.5 UI 表现

- **workbench / 文件树**：合并视图 = 各层 `scan_rel` 结果；子 mod 文件正常显示，底层/原版文件节点加浅色「层标」（tooltip 显示来源层与是否被子 mod 覆盖）；被覆盖的低层文件加删除线样式（仅标识，可打开只读）。
- **标题/状态栏**：子 mod 模式激活时全局徽标；`main_window._require_mod` 在子 mod 模式下返回子 mod 路径（写目标），所有 72 处调用方无感。
- **新建文件**：`_create_new_file` 目标目录 = 子 mod 对应相对目录；从底层文件上下文菜单新建 → `copy_up` 后打开副本。
- **保存防呆**：generic_tree_editor 保存路径来自打开时的来源层；激活栈时 `_save` 前 `mod_stack.write_target` 重定向到子 mod（`state_edit_ops` 已有严格重读 + mtime 防护，沿用）。

### 2.6 边界与风险

| 风险 | 对策 |
| --- | --- |
| 底层 mod 为创意工坊目录（只读/更新即失效） | 所有写恒定重定向子 mod；报告里对 workshop 层标注「勿直接编辑」 |
| `dependencies` 用 name 匹配 | 生成时逐字使用底层 mod descriptor 的 `name` 字段（非文件夹名）；`_needs_quote` 处理空格/中文 |
| sqlite 被游戏锁 | 只读 URI + dlc_load.json 回退（已在 1.3） |
| 子 mod 与底层同装时加载顺序错误 | 向导完成页给出文字指引（子 mod 需排在最末），并在 .mod 注释中说明；launcher 顺序不可编程改，不做自动写播放集 |
| 播放集含大量 mod 时合并树卡顿 | `scan_rel` 全量一次 O(Σ文件)，UI 分类型目录懒加载（沿用 `_type_folders_ext` 分组） |
| `check_layer_deps` / 文件预算 | 新模块各自 <1200 行；mod_stack 为公共底座层，依赖方向与既有契约一致（UI → 业务 → 底座） |

### 2.7 测试计划

`tests/test_mod_stack.py`：三层临时目录 fixture → `scan_rel` 遮蔽/来源标注、`resolve` 顶层命中、`write_target` 恒指子 mod、`copy_up` 内容复制 + 目录创建、未激活等价旧 (mod,hoi4) 行为（对拍 `ensure_file_in_mod` 旧实现）、空栈/缺层健壮性。
`tests/test_submod_wizard.py`：生成文件清单（descriptor dependencies 转义、中文 name 引号）、激活/退出 settings 往返（mock 主窗口）、从底层文件 copy_up 新建、保存重定向（generic_tree_editor `_save` 栈激活路径）。

---

## 3. 实施阶段（每阶段独立交付：测试 + 冒烟 + 双端 verify + 提交推送）

| 阶段 | 内容 | 交付物 |
| --- | --- | --- |
| **A 共用底座** | `playset_loader.py` + `mod_stack.py` + 真实数据冒烟（本机 `dlc_load.json`：cheat_mio/日共重置等 3 个 mod 的读取与排序；2 层栈对拍 `ensure_file_in_mod`） | 2 模块 + 2 测试文件 |
| **B 冲突检查** | `conflict_scan.py`（L0–L3，L4 视进度） + `conflict_report_dialog.py` + 菜单入口 + 真实播放集全量冒烟（计时） | 报告 UI 可用 |
| **C 子 mod** | `submod_wizard.py` + `ensure_file_in_mod` 委托 + `ai_loader._scan_files`/`localization_mgr` 接栈 + 合并树 + 模式徽标 | 子 mod 模式端到端可用 |
| **D 收尾铺开** | 29 个直连路径文件逐个接栈（新建场景）、MCP 工具（`playset_list/conflict_scan/submod_create`，可选）、`docs/`（功能文档 + 踩坑 + 迭代日志） | 全量绿 |

验收口径（沿用现有门禁）：
- 新增契约测试全绿；全套测试数 ≥ 838 + 新增量；
- `launcher.py --verify` **WSL + Windows 便携双端 8 契约全 OK**；
- 规范扫描 `违规 0`（新豁免仅限确需项，逐条写明理由）；
- 真实数据冒烟：本机播放集冲突报告零崩溃、子 mod 创建 → 激活 → 从底层 mod copy_up 编辑 → 保存落子 mod → 退出恢复，全链路走通。

---

## 4. 明确不做（本期）

- 不改写播放集/`dlc_load.json`（启动器职责，只读）。
- 不做 mod 内容合并写回底层 mod（子 mod 永远只叠加）。
- 不做创意工坊下载/更新管理。
- L4 引用失效分析首版只覆盖 focus/idea 两域。
