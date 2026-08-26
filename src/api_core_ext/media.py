"""ApiCore 扩展：图标 / 媒体（域 8）"""
from __future__ import annotations

import base64
import io
import os
import re

import path_safety


class MediaMixin:
    """图标上传、DDS 转换、单位标牌。"""

    def upload_entity_icon(self, data=None):
        data = data or {}
        type_key = (data.get("type") or "").strip()
        entity_id = (data.get("id") or "").strip()
        image_b64 = data.get("image_base64") or ""
        slot = (data.get("slot") or "").strip()
        if not type_key or not entity_id or not image_b64:
            raise ValueError("需要 type/id/image_base64")
        from content_types import ICON_RULES
        cfg = ICON_RULES.get(type_key)
        if not cfg:
            raise ValueError("该内容类型不支持图标上传: %s" % type_key)
        upload = cfg.get("upload") or {}
        try:
            raw = base64.b64decode(image_b64)
        except Exception as e:
            raise ValueError("image_base64 解码失败: %s" % e)
        from PIL import Image
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception as e:
            raise ValueError("图片解析失败: %s" % e)

        # 确定图标字段与上传名
        field_path = slot or (cfg.get("field") or "")
        if isinstance(field_path, list):
            field_path = field_path[0] if field_path else ""
        icon_base = path_safety.validate_component(
            (data.get("icon_base") or entity_id).strip(), "icon_base")
        subdir = upload.get("subdir", "gfx/interface/goals").strip("/")
        target_dir = os.path.join(self.mod_path, subdir.replace("/", os.sep))
        os.makedirs(target_dir, exist_ok=True)
        ref_mode = upload.get("ref_mode", "sprite")
        if ref_mode == "path":
            # 直接路径模式（角色头像等）
            rel_file = "%s/%s.png" % (subdir, icon_base)
            img.save(os.path.join(target_dir, icon_base + ".png"), format="PNG")
            icon_value = rel_file
            gfx_file = ""
            sprite_name = rel_file
        else:
            # 精灵模式：等比缩放至 128x128 PNG，并注册 sprite
            img = img.resize((128, 128), Image.Resampling.LANCZOS)
            img.save(os.path.join(target_dir, icon_base + ".png"), format="PNG")
            pattern = upload.get("gfx_name_pattern", "GFX_goal_{name}")
            sprite_name = pattern.format(name=icon_base)
            rel_file = "%s/%s.png" % (subdir, icon_base)
            gfx_file = upload.get("gfx_file", "goals_mod.gfx")
            gfx_path = os.path.join(self.mod_path, "interface", gfx_file)
            from tech_icon_ops import ensure_sprite_in_gfx_file
            ensure_sprite_in_gfx_file(gfx_path, sprite_name, rel_file)
            icon_value = sprite_name

        # 写入实体字段
        fp, content, rng = self._find_entity(type_key, entity_id)
        if fp and rng and rng[0] >= 0:
            from icon_ops import apply_icon_to_entity
            new_content = apply_icon_to_entity(
                content, rng[0], rng[1], field_path, icon_value)
            if new_content and new_content != content:
                from icon_ops import write_file_utf8
                write_file_utf8(fp, new_content)
                self._notify_change(fp)
        elif fp:
            # 实体定位失败但文件存在：不阻塞上传
            pass

        return {"ok": True, "type": type_key, "id": entity_id,
                "icon_value": icon_value, "sprite_name": sprite_name,
                "image_file": os.path.join(target_dir, icon_base + ".png"),
                "gfx_file": gfx_file}

    def generate_gui_gfx_asset(self, data=None):
        """程序化 GUI/GFX 资产生成（B3 批二③）。

        {name, size?, colors?, gui?, output_root?, dry_run?, approved?}
        - dry_run=true 返回计划文件清单；写盘需 approved=true 且 dry_run=false。
        - 生成 PNG（PIL 渐变圆角）+ .gfx spriteType 注册 + 可选 .gui 骨架。
        """
        data = data or {}
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("缺少 name")
        name = path_safety.validate_component(name, "name")
        approved = bool(data.get("approved", False))
        dry_run = bool(data.get("dry_run", True))
        make_gui = bool(data.get("gui", False))
        raw_size = data.get("size") or (64, 64)
        if isinstance(raw_size, (list, tuple)) and len(raw_size) == 2:
            size = (int(raw_size[0]), int(raw_size[1]))
        else:
            size = (64, 64)
        colors = data.get("colors") or ["#3b82f6", "#1d4ed8"]
        output_root = (data.get("output_root") or "").strip().strip("/")
        subdir = output_root or "gfx/interface/procedural"
        png_rel = "%s/%s.png" % (subdir, name)
        gfx_rel = "%s/%s.gfx" % (subdir, name)
        gui_rel = "interface/%s.gui" % name if make_gui else ""
        plans = [{"file": png_rel, "kind": "png"},
                 {"file": gfx_rel, "kind": "gfx"}]
        if gui_rel:
            plans.append({"file": gui_rel, "kind": "gui"})
        # 输出路径必须落在 mod 根内（防 output_root/name 越界）
        if not self._safe_join(png_rel):
            raise ValueError("非法输出路径（仅允许 mod 内相对路径）")
        if dry_run:
            return {"ok": True, "dry_run": True,
                    "approved_required": not approved,
                    "name": name, "sprite_name": "GFX_%s" % name,
                    "files": plans}
        if not approved:
            raise ValueError("程序化生成需显式 approved=true（避免覆盖已有素材）")
        from procedural_assets import generate_asset_png
        png_abs = os.path.join(self.mod_path, *png_rel.split("/"))
        os.makedirs(os.path.dirname(png_abs), exist_ok=True)
        generate_asset_png(png_abs, name, size=size, colors=colors)
        gfx_abs = os.path.join(self.mod_path, *gfx_rel.split("/"))
        os.makedirs(os.path.dirname(gfx_abs), exist_ok=True)
        from tech_icon_ops import ensure_sprite_in_gfx_file
        ensure_sprite_in_gfx_file(gfx_abs, "GFX_%s" % name, png_rel)
        written = [png_rel, gfx_rel]
        if make_gui:
            gui_abs = os.path.join(self.mod_path, *gui_rel.split("/"))
            os.makedirs(os.path.dirname(gui_abs), exist_ok=True)
            gui_text = (
                'windowType = {\n'
                '\tname = "%s_window"\n'
                '\tposition = { x = 0 y = 0 }\n'
                '\tsize = { width = %d height = %d }\n'
                '\ticonButton = {\n'
                '\t\tname = "%s_icon"\n'
                '\t\tquadTextureSprite = "GFX_%s"\n'
                '\t}\n'
                '}\n') % (name, size[0], size[1], name, name)
            from write_utils import atomic_write_text
            atomic_write_text(gui_abs, gui_text, encoding="utf-8")
            written.append(gui_rel)
        self._notify_change(png_abs)
        return {"ok": True, "dry_run": False, "name": name,
                "sprite_name": "GFX_%s" % name, "written": written}

    def convert_dds(self, data=None):
        data = data or {}
        path = (data.get("path") or "").strip()
        direction = (data.get("direction") or "dds2png").strip()
        recursive = bool(data.get("recursive", False))
        if not path:
            raise ValueError("缺少 path")
        # 只允许 mod 内相对路径（防任意文件读/写；游戏素材需先复制到 mod）
        fp = self._safe_join(path)
        if not fp:
            raise ValueError("path 必须为 mod 内相对路径（不允许绝对路径或 .. 越界）")
        if not os.path.exists(fp):
            raise ValueError("路径不存在: %s" % path)
        from dds_convert import dds_to_png, png_to_dds, convert_dir
        if os.path.isdir(fp):
            rel_dir = os.path.relpath(fp, self.mod_path)
            out_rel = data.get("output_dir") or (rel_dir + "_out")
            out_fp = self._safe_join(out_rel)
            if not out_fp:
                raise ValueError("output_dir 必须为 mod 内相对路径")
            convert_dir(fp, out_fp, recursive=recursive,
                        direction=direction)
            return {"ok": True, "direction": direction, "dir": fp,
                    "out_dir": out_fp}
        if direction == "dds2png":
            out = dds_to_png(fp)
        elif direction == "png2dds":
            out = png_to_dds(fp)
        else:
            raise ValueError("direction 必须为 dds2png 或 png2dds")
        return {"ok": True, "direction": direction, "output": out}

    def import_unit_counters(self, data=None):
        data = data or {}
        dry_run = bool(data.get("dry_run", True))
        from unit_counter_library import import_unit_counter_library
        out_dir = data.get("output_dir") or ""
        out_abs = ""
        if out_dir:
            out_abs = self._safe_join(out_dir)
            if not out_abs:
                raise ValueError("output_dir 必须为 mod 内相对路径")
        if dry_run:
            return {"ok": True, "dry_run": True, "files": [
                {"path": out_dir or "unit_counter_library/",
                 "summary": "从游戏 counters/ 导入 onmap_*.dds 生成 PNG + manifest"}
            ]}
        if not self.game_path:
            raise ValueError("需要 game_path 才能导入单位标牌")
        r = import_unit_counter_library(self.game_path, out_dir=out_abs or None)
        return {"ok": True, "dry_run": False,
                "library_dir": r.get("out_dir", out_dir),
                "count": r.get("total", 0), "skipped": r.get("skipped", 0),
                "categories": r.get("categories", [])}

    def list_unit_counters(self, data=None):
        data = data or {}
        from unit_counter_library import UnitCounterLibrary
        lib = UnitCounterLibrary()
        items = lib.search(keyword=data.get("keyword", ""),
                           category=data.get("category", ""))
        return {"ok": True, "count": len(items), "items": items}