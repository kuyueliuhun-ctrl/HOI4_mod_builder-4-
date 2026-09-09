# HOI4 Mod 制作 · 历次踩坑大全

> 汇总 2026-08 ~ 2026-09 历次制作 mod（中共加强 PRC_jiaqiang / 日共 CJC SubMod / 通用加强 general_enhancement / 帝国雄心 SubMod / lishilingtu）亲手踩过的真实坑与验证结论。
> 游戏基准版本：**v1.19.2.0 Operation Postern**（原版为基底）。
> 最后更新：2026-09-09

---

## 一、编码与文件格式（血泪铁律，违反即整文件失效）

| 文件 | 规则 | 后果 |
| --- | --- | --- |
| `.txt` 脚本（决议/国策/事件/state 等） | **UTF-8 无 BOM** | 加 BOM → `Unexpected token` → **整文件解析失败、内容全部消失** |
| `.yml` 本地化 | **UTF-8 带 BOM**（utf-8-sig） | 无 BOM 部分键读取异常 |
| `buildings.txt` | 行首 = 州 id，7 列；**尾部单个换行、无空行** | 多一个尾部空行报 EOF boundary 错 |
| `definition.csv` | 0 行 = 占位行 | 无 SR 归属属合法 |
| SR 文件 | 原版用 `#` 注释保留旧省份清单 | **解析/审计前必须先剥注释**，否则把注释数字当省份 → 误报跨 SR 重复 |

**实战衍生教训：**
- 写回前先判断原文件 BOM 状态；本地化 yml 写入一律 `encoding="utf-8-sig", allow_bom=True`（普通 `write_text` 会写成无 BOM）。
- **命令行/heredoc 传输会把源码里的 `\n` 转义悄悄改成 `/n`** → 国名/描述出现裸 `/n`。凡是含 `\n` 的写文件脚本，**一律用 Write 工具落盘成 .py 再执行**，不要用 heredoc。
- 行尾 CRLF/LF 混合（历次补丁造成）引擎无碍，可暂不处理；但用基于 `\n` 的文本替换工具改 CRLF 文件时锚点会静默不命中。

---

## 二、决议 / 国策 / 事件语法

1. **决议文件无 `decisions = {}` 外壳**，分类 id 直接顶格（`political_actions = { ... }`）。放错/不存在的分类 = 决议不显示。原版可用分类清单见 `common/decisions/categories/00_decision_categories.txt`。
2. **国策时长用 `cost = N`**（×7 天/点）：cost=5→35 天、cost=10→70 天；新版没有 `duration` 字段。
3. **比较运算符铁律：HOI4 触发器里没有 `>=` / `<=`**，只有 `>`、`<`、`=`。写 `>=` 会报 `Malformed token: =` 并让**整个文件解析崩溃**（决议文件后半全失效、on_actions 全废）。等效写法：`x >= 5` → `x > 4`。⚠️ validate 查不出此类错误，**必须看游戏 error.log**。
4. **州核心写法**：`if = { limit = { owns_state = 527 } 527 = { add_core_of = ROOT } }`。⚠️ **数字州块内不能直接放 `limit`**（报 `Invalid effect 'limit'`）。
5. **战争目标**：`create_wargoal = { type = annex_everything target = TAG expire = 0 }`。
6. **省略"黄字"长叙述**：把 completion_reward 里的长效果段（add_core/remove_core/claim 列表、create_wargoal、every_controlled_state 等）整体包进 `hidden_effect = { ... }`（在保留 `custom_effect_tooltip` 短描述之后插入）。效果照常执行，仅 tooltip 不显示。
7. **民族精神三种机制**：① 纯 idea（modifier）；② 动态修正+变量（`common/dynamic_modifiers/` 引用变量，国策 `add_to_variable` 累加）；③ fake idea + name。
8. **1.19 特殊项目/地图外建筑（实证）**：
   - 加突破点用 **`add_breakthrough_progress = { specialization = specialization_land/naval/air value = N }`**（value=1=1 突破点）；
   - ❌ `add_breakthrough_points` **无效**（本体 0 命中）；
   - 地图外（离场）建筑用 **`add_offsite_building = { type = industrial_complex/arms_factory/dockyard level = N }`**（支持负数移除）。
9. **决议 7 天自动循环模式**：点击设 country_flag → `activate_decision = <循环决议>`；循环决议 `days_remove = 7` + `visible = { has_country_flag = X }` + `cancel_trigger = { not = { has_country_flag = X } }`，在 `remove_effect` 里执行动作并再次 `activate_decision` 自身续期；停止决议 clr flag 即可（cancel **不触发** remove_effect）。
10. **删国策后的悬挂引用**：不要自作主张清掉其他国策里的 `relative_position_id` / `mutually_exclusive` / `prerequisite` 悬挂引用——**列出来问用户再决定**。
11. **热重载不重载 ideas**：民族精神 / 动态修正改动必须**完全重启游戏**才生效；热重载 ideas 会对 `_economic.txt` 等法系文件报错（怪癖，无害）。
12. **国策树坐标被 GUI 误动**：从原版复制该文件重新应用修改即可恢复。

---

## 三、加载与覆盖语义（mod 层叠，理解错必出诡异 bug）

三层加载顺序：**原版 < base mod < submod**（后加载者覆盖先加载者）。

| 机制 | 语义 | 后果/教训 |
| --- | --- | --- |
| `replace_path="history/states"` | submod 的 states 目录是**唯一来源** | base mod 的州文件在启用 submod 时**不被加载** |
| 同名文件（strategicregions、buildings.txt…） | 非 replace_path → **后加载整文件覆盖**（文件级替换，**不是合并**） | 想改某个 SR 必须带上整份 SR 文件 |
| `adjacencies.csv` | 整文件替换 | 179 行 = 生效全集 |
| `.disabled_*` 点目录 | 手术中间产物，引擎行为不确定 | **必须移出 mod**，避免被加载成幽灵州/干扰判断 |
| 国策/科技同名 id | 后加载覆盖先加载 | 同内容两个 mod 同时启用 = 重复定义冲突 |

**实战结论：**
- 要改写**游戏本体**的文件 → 通过 submod **新增同名文件**即可（submod 文件天然覆盖本体，这是规范做法）。
- **同内容勿同时启用多个 mod**：workshop「国家工业排名」「Auto medal」并入 general_enhancement 后必须取消勾选原 mod，否则 scripted_effects / defines 重复定义冲突；CJC 同理是"base mod（不可改动，改了会复原）+ overlay submod（一切改动只落在 submod）"结构。
- **整树替换自开局即生效**（焦点树按 tag 开局评分一次，无法"战后再换树"）；原树的 `has_completed_focus = XXX_*` 引用会自然失效且**无报错**。
- **define 增量覆盖**：`common/defines/` 下用自定义文件名（如 `zz_ge_defines.lua`）写 `NDefines.NCategory.KEY = value` 即可覆盖单键，未提及键保留原版——**不必复制 4712 行 `00_defines.lua`**。只有提供**同名 `00_defines.lua`** 才是整文件替换（那种情况才需全量复制）。
- **unit_leader 技能覆盖**：`common/unit_leader/` 按文件名字典序加载，用 `99_*.txt` 前缀覆盖原版 `00_*.txt` 的同 id 技能（将领 9~10 级→20 级就是这么实现的）。**移植此类 mod 必须保留 `99_` 前缀**。

---

## 四、州号连续性铁律（CJC 六连崩的根因，最高危）

> 2026-09-03 实测：日共 1090 州确定版。6 连崩（23:30–04:43）唯一根因 = **州号不连续**。

1. **HOI4 州号必须完全连续 1…N，零空洞**。原版 1–1081 零空洞、从不崩。
2. 引擎按州号建索引；id 空洞 → 生成"无省份的空州对象（幽灵州）"→ 1936.01.01 开局 `strategicair.cpp` 给空州生成机场/火箭/炮台位点 → `EXCEPTION_ACCESS_VIOLATION (C0000005)` @ `PHYSFS_swapULE64` 崩溃。
3. **error.log 特征**：载入期 `Missing State ID 1085…1099`；崩溃前一刻刷 45 行 `strategicair.cpp MAP_ERROR … no air base site defined for state …`（时间戳停在 1936.01.01）。
4. **新增州规则：从当前最大州号 +1 开始排，绝不跳号**；中间留空号段 = 定时炸弹。
5. ⚠️ 引擎报 `Missing State ID` **不代表**有文件引用它（穷举 7 个启用 mod 全部内容文件对空号段零引用，空洞本身就是死因）。判断依据 = **号段是否存在文件**，不是"有没有人引用"。

**崩溃排查三步取证法**：① 基线对照（原版连续=健康）→ ② 引用穷举（grep 全部启用 mod 内容文件对可疑号段，排除悬挂引用）→ ③ 唯一变量（只剩空洞本身 → 实锤）。

**州手术的"4+1 文件同步"**：state 文件 ↔ `map/buildings.txt`（行首州号）↔ strategicregions 归属 ↔ 内容文件引用（决议/事件/本地化键）。**动州必查全部，只改一个必出问题。**

---

## 五、建筑 / defines / 数值机制

1. 州建筑槽 = `common/state_category/*.txt` 的 `local_building_slots`（原版 13 类别 0~12）。
2. **每州共享（工厂类）建筑槽上限 = `NBuildings.MAX_SHARED_SLOTS = 25`**——把 local_building_slots 改大时必须同步调大它，否则工厂每州最多 25 槽（帝国雄心即同步改 45/100）。
3. **单个建造项目民用工厂上限 = `NProduction.MAX_CIV_FACTORIES_PER_LINE = 15`**（00_defines.lua:613，defines 可改、非硬编码）。
4. 用户版州类别 = 原版 ×2：megalopolis 24 / metropolis 20 / large_city 16 / city 12 / large_town 10 / town 8 / large_island 6 / rural 4 / pastoral 2 / small_island 2 / 其余 0。
5. **游戏显示 ≠ 代码值**（2026-08-25 实测）：HOI4 对某些修正值的游戏内百分比显示与代码值不一致（如 `*_intel_to_others = -0.2` 显示成 -0.02%，要显示 -20% 必须写 `-20`）。**遇到值/显示不符或不确定时，先问用户实际想达到的显示效果**，不要自行按"小数=百分数"换算。
6. **PRC 阵营/统一战线事件链**定义在游戏本体 `events/SEA_Communist_China.txt`；阵营模板 `faction_template_chinese_united_front` / `faction_template_PRC_the_peoples_front` 在 `common/factions/templates/unique_minor_factions.txt`。

---

## 六、游戏内行为 / 可见性细节

- **傀儡国策树**：本体 CHI **看不到**傀儡 tag 的国策树，切到该 tag 后才显示（调试别误判为丢失）。
- **角色时序坑**：某国（BAN）1936 时不存在 → base mod 的 `recruit_character + set_oob` 历史**不会执行**；但 `common/characters/BAN.txt` 里的角色会在该国创建时自动加载。
- **终局才激活**：某些内容只在终局事件（如 IAR_World_Domination.5 世界主宰收尾）激活；开新局不触发该事件 → 表现为"永远无法激活"。
- **全局影响要标注**：清 `impassable = yes` 之类改动**影响全图**（不只是目标战场），且只清 state 级字段；地形层（terrain.bmp 荒漠/山脉）不受影响，改了仍不可通行需另议。
- **"转移州可多于前置州"** 是帝国雄心惯例（决议 available 不必包含全部目标州），可沿用。
- **州号笔误检测**：发现离奇归属（如太平洋军管领控到 Western Macedonia/YUG、Northern Dobruja/ROM）→ 大概率源文件州号笔误。
- **同名实体冲突**：一个实体无法同时叫多个名字——越南/暹罗/缅甸/马来西亚人民共和国 4 决议若并入同一 VIN 实体，只有一层"皮"能生效。
- 游戏不显示内容 → 先查 `Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log`（**唯一权威**），写完文件用编辑器接口回读确认。

---

## 七、版本 / 路径 / 基准（搜错=白忙）

- 游戏本体：`D:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV` = **v1.19.2.0 Operation Postern**（2026-08-29 实测）。
- ⚠️ `D:\SteamLibrary\...` 是 **1.16.10 旧版**另一安装，**别搜错**；settings.json 的 HOI4_path（E:/SteamLibrary）、mod_file_path（C:/Users/枯月流魂/...）是**失效旧配置**。
- Workshop mod 在 `...\workshop\content\394360\`。
- **用户游玩基准 = 原版，不带帝国雄心**：3206158781/3672464695 仅作参考存在，**勿以其文件为基底做覆盖**（其 IAR_defines.lua 把 MAX_SHARED_SLOTS 调 100、州类别 45/32/30 等均非用户实际值）。覆盖一律以游戏本体原版文件为基底。
- 启用 ge（general_enhancement）时必须取消勾选并入过的 workshop 原 mod。

---

## 八、手术 SOP 与工具实操

1. **全量备份** → `.runtime/`，目录名含语义与日期（术前版 / 崩溃版存档 / 确定版三版并存，各司其职）。
2. 小步手术 + 每步验证；**重编号 = 先列映射表再动手**。
3. **行替换只改"行首前缀"，绝不用整行正则**：`re.match(r"^(1100);(.*)$", line)` + splitlines(keepends=True) 时 `$` 会吞掉行尾 `\n` → 被替换行**全部行粘连**。✅ 正确：`re.sub(r"^1100;", "1085;", line)`。
4. **`ls` 不带 `-a` 看不到点目录**：移动 `.disabled_states` 后以为失败，实为查看方式问题。
5. **grep 号段残留要精确前缀**：查"1100+ 残留"用 `^1(10|2)[0-9]` 会误伤 120–129 正常州 → 用 `^110[0-9]-` / `^12[0-9]{2}-`。
6. 改后 **diff 验证只应有预期变化**（buildings diff 恰 253 对行首数字，零多余）；事件号/决策键/STATE_xxx 本地化键同步改，改前确认目标号段命名空间空闲。
7. 全模组残留扫描：grep 旧号段 / 旧键名必须为空。

---

## 九、编辑器 / 工具链环境坑（日常使用向）

- **编辑器入口**：`启动.bat` → `.venv\Scripts\python.exe src\main.py`（是 `src\main.py`，**不是根目录 main.py**；AGENTS.md 曾写错）。
- **HTTP API**：`127.0.0.1:8765`，token 由 api_server 启动时随机生成 / `--token` 指定（本机会话值，勿外传）。**API 进程挂起是常态**，需要时主动重启。
- **回收站删除 API**：ctypes 调 `shell32.SHFileOperationW`（FO_DELETE + FOF_ALLOWUNDO）**返回码恒为 2 但实际删除成功** → 判成败必须回查 `os.path.exists`，不能只看返回值（脚本见 `.runtime/recycle_delete.py`）。
- **解压**：系统没装 7-Zip，但 `D:\Program Files\WinRAR\UnRAR.exe` 可用——`p` 输出到 stdout、`l` 列内容、`x <dir>` 解压。⚠️ `reg.exe` 被沙箱安全策略黑名单拦截（查注册表报 PROGRAM BLOCKED，勿重试，换方法）。
- **写 mod 文件纪律**：优先整文件原子写（`write_utils.atomic_write_text`）；`_insert_entity_block` 对块包裹文件是尾追加，会污染文件。
- 控制台是 GBK：跑脚本加 `python -X utf8`；GUI 测试用 `QT_QPA_PLATFORM=offscreen`。
- 数据单例方向别搞反：`owner_province_map()` 返回 **tag→pids**；国家着色 overlay 需要 **pid→tag**。
- `np.save` 自动补 `.npy` 后缀：临时文件名必须带 `.npy` 结尾。
- AI 无法读图时验证界面：截图 + PIL `getcolors` 统计颜色数，或让用户直接看窗口。

---

## 十、一页纸速查

| 场景 | 记住 |
| --- | --- |
| .txt 不显示 / 整文件消失 | 查 BOM（应无）；查 `>=`/`<=`（应无）；查 error.log |
| 本地化不显示 | .yml 必须带 BOM（utf-8-sig） |
| 决议不显示 | 分类 id 必须顶格且分类存在 |
| 游戏开局崩溃 C0000005 | 州号有空洞 → 补连续；查 Missing State ID |
| 工厂每州到 25 就满 | 调 `MAX_SHARED_SLOTS` |
| 单产线民厂到 15 就满 | 调 `MAX_CIV_FACTORIES_PER_LINE` |
| 数值显示和写的不一样 | 先问用户要什么显示效果，别自行换算 |
| 改 SR / state / buildings | 4+1 文件同步 + buildings 行首前缀替换 |
| 想覆盖本体文件 | submod 里新增同名文件即可 |
| 改 ideas 不生效 | 完全重启游戏（热重载不载 ideas） |
| 引用了被删国策 | 列出来问用户，勿自作主张清理 |
