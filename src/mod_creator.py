"""新建 mod 项目骨架生成（纯函数 + 可写回）

从 ModCreatorDialog 下沉：
  - .mod 描述文件（mod_file_path/<folder>.mod）
  - descriptor.mod（mod 内容目录）
  - gfx/ 空目录
  - interface/<folder>.gfx 空白 spriteTypes
  - localisation/simp_chinese/<folder>_l_simp_chinese.yml 空白本地化
"""
from __future__ import annotations

import os


def build_mod_files(name, folder_name, version, tags=None,
                    mod_folder_path="", mod_file_path="", tag=""):
    """生成新建 mod 项目的文件清单。

    Returns:
        list[dict]: [{"path": absolute, "content": str, "bom": bool}]
    """
    tags = tags or []
    full_folder = os.path.join(mod_folder_path, folder_name)
    mod_file_full_path = os.path.join(mod_file_path, folder_name + ".mod")
    tags_str = "\n".join('    "%s"' % t for t in tags)
    mod_content = (
        'name = "%s"\npath = "%s/%s"\nsupported_version = "%s"\ntags = {\n%s\n}\n'
        % (name, mod_folder_path.replace("\\", "/"), folder_name, version, tags_str))
    files = [
        {"path": mod_file_full_path, "content": mod_content, "bom": False},
        {"path": os.path.join(full_folder, "descriptor.mod"),
         "content": mod_content, "bom": False},
        {"path": os.path.join(full_folder, "interface", folder_name + ".gfx"),
         "content": "spriteTypes = {\n\n}\n", "bom": False},
        {"path": os.path.join(full_folder, "localisation", "simp_chinese",
                              folder_name + "_l_simp_chinese.yml"),
         "content": "l_simp_chinese:\n", "bom": True},
    ]
    if tag:
        files.append({
            "path": os.path.join(full_folder, "common", "country_tags",
                                 "00_countries.txt"),
            "content": '%s:0 "countries/%s.txt"\n' % (tag.upper(), tag.upper()),
            "bom": False,
        })
        files.append({
            "path": os.path.join(full_folder, "common", "countries",
                                 tag.upper() + ".txt"),
            "content": "country_tag = %s\ncolor = { 128 128 128 }\n" % tag.upper(),
            "bom": False,
        })
    return files


def write_mod_files(files):
    """按清单原子写文件；返回写入路径列表。"""
    from write_utils import atomic_write_text
    written = []
    # 保持旧对话框行为：创建 gfx 空目录
    for f in files:
        if os.path.basename(f["path"]) == "descriptor.mod":
            os.makedirs(os.path.join(os.path.dirname(f["path"]), "gfx"),
                        exist_ok=True)
        os.makedirs(os.path.dirname(f["path"]), exist_ok=True)
        atomic_write_text(f["path"], f["content"],
                          encoding="utf-8-sig" if f.get("bom") else "utf-8",
                          allow_bom=bool(f.get("bom")), undo=False)
        written.append(f["path"])
    return written
