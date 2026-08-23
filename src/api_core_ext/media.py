"""ApiCore 扩展：图标 / 媒体（域 8）"""
from __future__ import annotations

import base64
import io
import os
import re


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
        icon_base = (data.get("icon_base") or entity_id).strip()
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

    def convert_dds(self, data=None):
        data = data or {}
        path = (data.get("path") or "").strip()
        direction = (data.get("direction") or "dds2png").strip()
        recursive = bool(data.get("recursive", False))
        if not path:
            raise ValueError("缺少 path")
        # path 可以是 mod 内相对路径或绝对路径
        fp = self._safe_join(path)
        if not fp:
            fp = path
        if not os.path.exists(fp):
            raise ValueError("路径不存在: %s" % path)
        from dds_convert import dds_to_png, png_to_dds, convert_dir
        if os.path.isdir(fp):
            out_dir = data.get("output_dir") or (fp + "_out")
            convert_dir(fp, out_dir, recursive=recursive,
                        direction=direction)
            return {"ok": True, "direction": direction, "dir": fp,
                    "out_dir": out_dir}
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
        if dry_run:
            return {"ok": True, "dry_run": True, "files": [
                {"path": out_dir or "unit_counter_library/",
                 "summary": "从游戏 counters/ 导入 onmap_*.dds 生成 PNG + manifest"}
            ]}
        if not self.game_path:
            raise ValueError("需要 game_path 才能导入单位标牌")
        r = import_unit_counter_library(self.game_path, out_dir=out_dir or None)
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