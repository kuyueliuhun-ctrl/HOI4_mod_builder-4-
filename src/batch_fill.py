"""批量填鸭（AOR）——列表驱动模板批量生成器。

对应秋起图书馆《批量填鸭工具：AOR自研版（9.22版）.xls》：
- normal：批量生成 idea 图标 spriteType 注册。
- shine：批量生成国策图标 shine SpriteType 注册。
- 将领：批量生成将领/元帅代码。

设计：一行输入 = 一个代码块；模板使用 __占位符__，与 template_scheduler 兼容。
本模块只负责“列表 × 模板 → 文本”，不直接写 mod 文件；需要落盘时由调用方用
write_utils.atomic_write_text 写入。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Union

__all__ = [
    "BATCH_PRESETS",
    "BatchPreset",
    "expand_template",
    "generate_batch",
    "generate_preset",
    "idea_sprite_template",
    "shine_sprite_template",
    "general_template",
]

# ── 模板常数（从 xls 原样抽取，统一改用 __占位符__） ──────────────────────────

IDEA_SPRITE_TEMPLATE = """ spriteType = {
  name = "GFX_idea_%NAME%"
  texturefile = "gfx/interface/ideas/%NAME%.dds"
 }"""

SHINE_SPRITE_TEMPLATE = """SpriteType = {
  name = "GFX_%NAME%_shine"
  texturefile = "gfx/interface/goals/%NAME%.dds"
    effectFile = "gfx/FX/buttonstate.lua"
  animation = {
   animationmaskfile = "gfx/interface/goals/%NAME%.dds"
   animationtexturefile = "gfx/interface/goals/shine_overlay.dds" 
   animationrotation = -90.0  # -90 clockwise 90 counterclockwise(by default)
   animationlooping = no   
   animationtime = 0.75    
   animationdelay = 0   
   animationblendmode = "add"      
   animationtype = "scrolling"      
   animationrotationoffset = { x = 0.0 y = 0.0 }
   animationtexturescale = { x = 1.0 y = 1.0 } 
  }

  animation = {
   animationmaskfile = "gfx/interface/goals/%NAME%.dds"
   animationtexturefile = "gfx/interface/goals/shine_overlay.dds"  
   animationrotation = 90.0 
   animationlooping = no   
   animationtime = 0.75    
   animationdelay = 0   
   animationblendmode = "add"       
   animationtype = "scrolling"      
   animationrotationoffset = { x = 0.0 y = 0.0 }
   animationtexturescale = { x = 1.0 y = 1.0 } 
  }
  legacy_lazy_load = no
 }"""

GENERAL_TEMPLATE = """
%NAME%= { 
		name = %NAME%
		portraits = {
			army = {
				large = GFX_portrait_%NAME%
small = GFX_portrait_%NAME%_small
			}
		}
		%JOB% = {
			traits = { }
			skill = %SKILL%
			attack_skill = %ATTACK%
			defense_skill = %DEFENSE%
			planning_skill = %PLANNING%
			logistics_skill = %LOGISTICS%
			legacy_id = -1
		}
	}"""


@dataclass(frozen=True)
class BatchPreset:
    """批量填鸭预设：名称、说明、模板、必需占位符。"""

    name: str
    label: str
    template: str
    placeholders: tuple[str, ...]


def idea_sprite_template() -> str:
    """normal 预设模板（idea 图标 spriteType 注册）。"""
    return IDEA_SPRITE_TEMPLATE


def shine_sprite_template() -> str:
    """shine 预设模板（国策图标 shine SpriteType 注册）。"""
    return SHINE_SPRITE_TEMPLATE


def general_template() -> str:
    """将领预设模板（将帅代码生成）。"""
    return GENERAL_TEMPLATE


BATCH_PRESETS: Dict[str, BatchPreset] = {
    "idea_sprite": BatchPreset(
        name="idea_sprite",
        label="普通图标注册（GFX_idea_*）",
        template=IDEA_SPRITE_TEMPLATE,
        placeholders=("%NAME%",),
    ),
    "shine_sprite": BatchPreset(
        name="shine_sprite",
        label="国策图标 shine 注册（GFX_*_shine）",
        template=SHINE_SPRITE_TEMPLATE,
        placeholders=("%NAME%",),
    ),
    "general": BatchPreset(
        name="general",
        label="将领/元帅批量生成",
        template=GENERAL_TEMPLATE,
        placeholders=("%NAME%", "%JOB%", "%SKILL%", "%ATTACK%",
                      "%DEFENSE%", "%PLANNING%", "%LOGISTICS%"),
    ),
}


_TOKEN_PATTERN = re.compile(
    r"__([A-Za-z0-9_\u4e00-\u9fff]+)__|%([A-Za-z0-9_\u4e00-\u9fff]+)%"
)


def expand_template(template: str, values: Mapping[str, object]) -> str:
    """把一行输入展开为一段代码。

    支持两种占位符：__NAME__ 和 %NAME%（后者更安全，可紧挨下划线使用）。
    values 的键大小写不敏感，None 不入替换。

    Args:
        template: 模板文本。
        values: 占位符 -> 替换值。

    Returns:
        替换后的文本。
    """
    lookup = {key.strip("_"): str(value) for key, value in values.items()
              if value is not None}

    def _replace(match: "re.Match[str]") -> str:
        token = match.group(0)
        name = match.group(1) or match.group(2)
        value = (lookup.get(name)
                 or lookup.get(name.lower())
                 or lookup.get(name.upper()))
        return value if value is not None else token

    return _TOKEN_PATTERN.sub(_replace, template)


def _normalize_rows(rows: Sequence[Union[str, Mapping[str, object]]],
                    single_field: str = "name") -> List[Dict[str, object]]:
    """把字符串行（仅单列表格）或字典行统一成字典。"""
    normalized: List[Dict[str, object]] = []
    for row in rows:
        if isinstance(row, Mapping):
            normalized.append(dict(row))
        else:
            normalized.append({single_field: row})
    return normalized


def generate_batch(template: str,
                   rows: Sequence[Union[str, Mapping[str, object]]],
                   sep: str = "\n") -> str:
    """按模板批量生成代码。

    Args:
        template: 模板文本。
        rows: 每行一个输入；字符串行自动作为 name，字典行按占位符键替换。
        sep: 代码块之间的分隔符，默认换行。

    Returns:
        多个代码块拼接后的文本（尾部带一个换行）。
    """
    blocks: List[str] = []
    for row in _normalize_rows(rows):
        block = expand_template(template, row)
        if block and not block.endswith("\n"):
            block += "\n"
        blocks.append(block)
    if not blocks:
        return ""
    return sep.join(blocks) + "\n"


def generate_preset(preset_name: str,
                    rows: Sequence[Union[str, Mapping[str, object]]]) -> str:
    """按预设批量生成代码。

    Args:
        preset_name: BATCH_PRESETS 中的键。
        rows: 输入行；字符串行适用于 idea_sprite/shine_sprite/general 的 name。

    Returns:
        生成文本。预设不存在抛 KeyError。
    """
    preset = BATCH_PRESETS[preset_name]
    return generate_batch(preset.template, rows)


def parse_table(text: str, delimiter: str = "\t") -> List[Dict[str, str]]:
    """解析带表头的 TSV/CSV 简易表格。

    首行作为字段名；空行跳过；字段数不足时缺省为空串。
    用于把 xls 复制的表格文本直接喂给 generate_preset。
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = [cell.strip() for cell in lines[0].split(delimiter)]
    rows: List[Dict[str, str]] = []
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.split(delimiter)]
        rows.append({header[i]: cells[i] if i < len(cells) else ""
                     for i in range(len(header))})
    return rows


def format_preset_help() -> str:
    """返回 MCP/CLI 可用的预设清单说明。"""
    lines = ["可用预设："]
    for preset in BATCH_PRESETS.values():
        lines.append(f"- {preset.name}: {preset.label}"
                     f"（占位符：{', '.join(preset.placeholders)}）")
    return "\n".join(lines)