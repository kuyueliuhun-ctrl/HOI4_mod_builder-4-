# UI 回归验证结果（F3-3a）

> 日期：2026-08-23
> 目的：对 2026-08 用户低分 UI（科技树 4 分 / 飞机设计器 2 分 / 坦克设计器 2 分 /
> BOP 4 分 / 角色编辑器 4 分）做**离线回归验证**，替代"看截图"。
> 方法：①全量契约测试（约 395 用例，双版本绿）②真实数据加载计数
> ③`ui_gap_probe --max-files 0` 缺口核对。涉及字段化/结构化的修复对应
> `AGENTS.md §6.22/§6.23` 与 `docs/整合计划.md` 批次 A/B/C/D/E。

## 结论总表

| UI | 历史评分 | 回归证据（测试） | 真实数据计数 | 缺口（`--max-files 0`） | 结论 |
| --- | --- | --- | --- | --- | --- |
| 科技树 | 4 分 | `TechLayoutTest` + `TechEditorSmokeTest` 绿 | 科技实体 776 | tech 0 / 0 | 已解决：画布双击/右键、folder 顶层、allow/ai_will_do/加成块结构化、其他字段表 |
| 飞机设计器 | 2 分 | `PlaneDesignLoaderTest` + `PlaneDesignDialogSmokeTest` 绿 | airframes 118 / modules 101 / variants 94 | —（设计器） | 已解决：5 列槽位、空配件提示、同款同步、未定义机体容错、原版自动落 mod |
| 坦克设计器 | 2 分 | `TankDesignLoaderTest` + `TankDesignDialogSmokeTest` 绿 | chassis 114 / modules 116 / variants 71 | —（设计器） | 已解决：完整底盘/模块/变体读写，复用 modules 链路 |
| BOP | 4 分 | `BopLoaderTest` + `BopEditorDialogSmokeTest` + `BopEditDataTest` + `BopDecisionCrudTest` 绿 | BOP 定义 26 | bop 0 / 0 | 已解决：区间/势力/决议 CRUD、本地化、修正实时展示、深色工作台 |
| 角色编辑器 | 4 分 | `CharacterDataTest` + `CharacterEditorSmokeTest` + `CharacterStructuredDataTest` + `CharacterEditorStructSmokeTest` 绿 | 角色文件 378，缺口 0/0 | character 0 / 0 | 已解决：roles/portraits 结构化 + 未知块经 ScriptBlockEditorDialog 编辑，无 raw 兜底 |

## 验证方式说明

- **测试**：全部来自拆分后的 `tests/` 按域文件（`test_designers.py` / `test_bop.py` /
  `test_contracts.py` 核心等），offscreen 冒烟 + 写回 roundtrip，双版本
  `verify_contracts.py` 退出码 0。
- **真实数据**：`E:/mods/3350890356`（mod）+ 游戏本体，加载计数均为 >0 且与
  UI 可呈现对象数一致；保存链路 dry-run（临时 mod）已验证。
- **缺口**：`ui_gap_probe.py --types focus,tech,event,character,bop,state,country_history
  --max-files 0` 中 tech/event/character/bop 为 0/0；state/country_history/focus
  的剩余缺口在 spec `note` 中登记为长期收敛项（见 F3-3c）。

## 仍有差距项

- 无新增差距；登记在 `docs/整合计划.md` P2.5 的已知限制（数值估算、未定义
  airframe 容错等）属诚实取舍，非本次回归范围。
