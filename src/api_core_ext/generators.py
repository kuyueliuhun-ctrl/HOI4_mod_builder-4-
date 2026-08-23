"""ApiCore 扩展：内容生成器 7 种（域 9）

全部默认 dry_run=true：只返回将写入文件清单；显式 dry_run=false 才原子写。
"""
from __future__ import annotations

import os


class GeneratorsMixin:
    """内容生成器。"""

    # ---------- 内部 ----------

    def _gen_files(self, kind, data, result):
        """把生成器 result 转为 files 列表。"""
        kind = (kind or "").strip()
        filename = (data.get("filename") or "generated").strip()
        files = []
        # 脚本文本
        text = result.get("text")
        if text:
            rel = {
                "ideas": "common/ideas/%s.txt" % filename,
                "ideologies": "common/ideologies/%s.txt" % filename,
                "characters": "common/characters/%s.txt" % filename,
                "generals": "common/characters/generals_%s.txt" % filename,
                "event": "events/%s.txt" % filename,
                "focus_package": "common/national_focus/%s.txt" % filename,
                "country_bootstrap": "history/countries/%s.txt" % filename,
            }.get(kind, "generated/%s.txt" % filename)
            files.append({"path": rel, "content": text})
        # 多文件（country_bootstrap histories）
        for fn, content in (result.get("histories") or {}).items():
            files.append({"path": "history/countries/" + fn, "content": content})
        # 本地化
        loc = result.get("loc") or []
        if loc:
            loc_text = "l_simp_chinese:\n"
            for item in loc:
                val = str(item.get("value", "")).replace('"', '\\"')
                loc_text += ' %s: "%s"\n' % (item.get("key", ""), val)
            loc_rel = "localisation/simp_chinese/%s_l_simp_chinese.yml" % filename
            files.append({"path": loc_rel, "content": loc_text, "bom": True})
        return files

    def _gen_write(self, files):
        from write_utils import atomic_write_text
        written = []
        for f in files:
            fp = os.path.join(self.mod_path, f["path"].replace("/", os.sep))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            atomic_write_text(fp, f["content"],
                              encoding="utf-8-sig" if f.get("bom") else "utf-8",
                              allow_bom=bool(f.get("bom")))
            self._notify_change(fp)
            written.append(f["path"])
        return written

    def _run_generator(self, kind, data):
        data = data or {}
        dry_run = bool(data.get("dry_run", True))
        if kind == "ideas":
            from idea_gen import generate_ideas
            result = generate_ideas(data.get("ideas") or [])
        elif kind == "ideologies":
            from ideology_gen import generate_ideologies
            result = generate_ideologies(data.get("ideologies") or [])
        elif kind == "characters":
            from character_gen import generate_characters
            result = generate_characters(data.get("groups") or [])
        elif kind == "generals":
            from general_gen import generate_leader_blocks
            result = generate_leader_blocks(
                data.get("leaders") or [],
                character_id=data.get("character_id", "leader"))
        elif kind == "country_bootstrap":
            from country_boot import generate_country_bootstrap
            result = generate_country_bootstrap(data.get("countries") or [])
        elif kind == "focus_package":
            from focus_package_gen import generate_package
            result = generate_package(
                data.get("focuses") or [],
                tree_id=data.get("tree_id", "PROJECT"),
                with_icon_gfx=bool(data.get("with_icon_gfx", True)))
            # 补充图标 GFX 文件
            if data.get("with_icon_gfx", True):
                gfx = "spriteTypes = {\n}\n"
                files_extra = [{"path": "interface/%s.gfx" % filename(data, "focus_package"),
                                "content": gfx}]
                result["_extra_files"] = files_extra
        elif kind == "event":
            from event_gen import generate_event_namespace_block, generate_event
            event_ids = data.get("event_ids") or []
            if event_ids:
                result = generate_event_namespace_block(
                    event_ids, data.get("namespace", ""))
            else:
                result = generate_event(
                    data.get("event_id", ""),
                    title_placeholder=data.get("title", ""),
                    desc_placeholder=data.get("desc", ""),
                    option_placeholder=data.get("option", ""),
                    namespace=data.get("namespace", ""))
        else:
            raise ValueError("未知生成器: %s" % kind)
        files = self._gen_files(kind, data, result)
        extra = result.get("_extra_files") or []
        if extra:
            files.extend(extra)
        if dry_run:
            return {"ok": True, "dry_run": True, "kind": kind,
                    "count": len(files), "files": files}
        written = self._gen_write(files)
        return {"ok": True, "dry_run": False, "kind": kind,
                "count": len(written), "files": files, "written": written}

    def generate_ideas(self, data=None):
        return self._run_generator("ideas", data)

    def generate_ideologies(self, data=None):
        return self._run_generator("ideologies", data)

    def generate_characters(self, data=None):
        return self._run_generator("characters", data)

    def generate_generals(self, data=None):
        return self._run_generator("generals", data)

    def generate_country_bootstrap(self, data=None):
        return self._run_generator("country_bootstrap", data)

    def generate_focus_package(self, data=None):
        return self._run_generator("focus_package", data)

    def generate_event(self, data=None):
        return self._run_generator("event", data)


def filename(data, kind):
    return (data.get("filename") or "generated").strip()