"""
翻译编辑器逻辑 — 核心翻译管理系统
从 HOI4_path 和 mod_path 中读取 YML 翻译文件，
支持查看、修改、保存翻译（只写入 mod_path，不修改游戏原始文件）。

架构说明：
  - TranslationEditor: 核心编辑器，读取游戏和mod的本地化文件，合并优先级
  - get_translation_editor(): 全局单例工厂函数
  - YML 解析逻辑复用 localization_mgr 中的共享函数
"""

import os
from typing import Dict, List

from localization_mgr import LOC_PATTERN, load_loc_yml_dir, parse_loc_yml_file


# 结构体类型 -> 保存到 mod 时使用的翻译文件名
MOD_LOC_FILE_TYPES = {
    "focus_tree": "focus_mod_l_simp_chinese.yml",
    "ideas": "ideas_mod_l_simp_chinese.yml",
}


def get_mod_loc_file_name(root_type: str) -> str:
    """根据结构体根类型获取对应的 mod 翻译文件名，未知类型默认使用国策文件。"""
    return MOD_LOC_FILE_TYPES.get(root_type, "focus_mod_l_simp_chinese.yml")


class TranslationEditor:
    """
    翻译编辑器逻辑 — 核心翻译管理系统
    从 HOI4_path 和 mod_path 中读取 YML 翻译文件，
    支持查看、修改、保存翻译（只写入 mod_path，不修改游戏原始文件）。

    工作流程：
    1. 读取游戏原始翻译 (hoi4_cache)
    2. 读取mod已有翻译 (mod_cache，优先级更高)
    3. 编辑时写入 mod_cache
    4. 保存时写入 mod 的 YML 文件
    """

    def __init__(self, hoi4_loc_path: str = "", mod_loc_path: str = "",
                 mod_file_name: str = "focus_mod_l_simp_chinese.yml"):
        # 游戏本地化目录: game/localisation/simp_chinese/
        self.hoi4_loc_path = hoi4_loc_path
        # mod 本地化目录: mod/localisation/simp_chinese/
        self.mod_loc_path = mod_loc_path
        # 保存到 mod 时使用的翻译文件名（如 focus_mod_l_simp_chinese.yml / ideas_mod_l_simp_chinese.yml）
        self.mod_file_name = mod_file_name
        # 游戏原始翻译缓存（只读参考）
        self.hoi4_cache: Dict[str, str] = {}
        # mod翻译缓存（可编辑，优先级更高）
        self.mod_cache: Dict[str, str] = {}
        # 已加载的文件路径列表
        self._loaded_files: List[str] = []

    def set_paths(self, hoi4_loc_path: str, mod_loc_path: str, mod_file_name: str = None):
        """更新翻译文件搜索路径"""
        self.hoi4_loc_path = hoi4_loc_path
        self.mod_loc_path = mod_loc_path
        if mod_file_name:
            self.mod_file_name = mod_file_name

    def reload(self):
        """
        重新加载所有翻译文件
        先加载游戏原始文件，再加载mod文件（mod的同key值会覆盖游戏值）。
        mod目录中目标文件（self.mod_file_name）最后加载，
        确保用户编辑保存的目标文件拥有最高优先级，
        避免同目录其他 *_l_simp_chinese.yml 的同 key 覆盖用户已保存的修改。
        """
        # 清空所有缓存
        self.hoi4_cache.clear()
        self.mod_cache.clear()
        self._loaded_files.clear()

        # 先加载游戏原始文件（优先级较低）
        if self.hoi4_loc_path and os.path.isdir(self.hoi4_loc_path):
            self._load_dir(self.hoi4_loc_path, self.hoi4_cache)

        # 再加载mod文件（优先级较高，会覆盖同key）
        if self.mod_loc_path and os.path.isdir(self.mod_loc_path):
            self._load_dir(self.mod_loc_path, self.mod_cache)
            # 目标文件最后重载一次，确保其值优先显示
            target_path = os.path.join(self.mod_loc_path, self.mod_file_name)
            if os.path.isfile(target_path):
                parse_loc_yml_file(target_path, self.mod_cache)
        # 兼容使用美式拼写 "localization" 的 mod（读取，不用于保存）
        if self.mod_loc_path:
            alt = self.mod_loc_path.replace("localisation", "localization")
            if alt != self.mod_loc_path and os.path.isdir(alt):
                self._load_dir(alt, self.mod_cache)
                target_path = os.path.join(alt, self.mod_file_name)
                if os.path.isfile(target_path):
                    parse_loc_yml_file(target_path, self.mod_cache)

    def get_effective(self, key: str) -> str:
        """
        获取有效翻译（mod优先，然后游戏原始）
        这是最终的翻译结果，遵循mod覆写原则
        """
        if key in self.mod_cache:
            return self.mod_cache[key].replace('\\n', '\n')
        if key in self.hoi4_cache:
            return self.hoi4_cache[key].replace('\\n', '\n')
        # 两者都没有返回空字符串
        return ""

    def get_name(self, focus_id: str) -> str:
        """获取名称翻译（直接用focus_id作为key）"""
        return self.get_effective(focus_id)

    def get_desc(self, id_key: str) -> str:
        """
        获取 _desc 翻译
        HOI4惯例：描述键名为 id_key_desc
        """
        return self.get_effective(f"{id_key}_desc")

    def set_name(self, focus_id: str, value: str):
        """设置名称翻译（写入mod缓存，待保存）"""
        self.mod_cache[focus_id] = value

    def set_desc(self, id_key: str, value: str):
        """设置描述翻译（写入mod缓存，待保存）"""
        self.mod_cache[f"{id_key}_desc"] = value

    def has_in_hoi4(self, key: str) -> bool:
        """检查游戏原始文件中是否有此key的翻译"""
        return key in self.hoi4_cache

    def has_in_mod(self, key: str) -> bool:
        """检查mod中是否已有此key的翻译"""
        return key in self.mod_cache

    def _load_dir(self, loc_dir: str, cache: Dict[str, str]):
        """
        从目录加载所有 *_l_simp_chinese.yml 文件
        遍历目录中所有匹配的YML文件，解析后存入指定缓存
        """
        self._loaded_files.extend(load_loc_yml_dir(loc_dir, cache))

    def save_to_mod(self, filename: str = None,
                     keys_to_write: Dict[str, str] = None) -> bool:
        """
        将翻译写入 mod 路径的类型对应 YML 文件
        有对应词条直接修改，无对应词条则追加，文件不存在则新建。
        文件格式：l_simp_chinese: 后每行一个词条，格式为 " key: \"value\""。

        Args:
            filename: 目标文件名（None 使用 self.mod_file_name）
            keys_to_write: 指定要写入的key-value字典，为None则写入全部mod_cache
        Returns:
            bool: 保存是否成功
        """
        if not self.mod_loc_path:
            return False

        filename = filename or self.mod_file_name or "focus_mod_l_simp_chinese.yml"
        filepath = os.path.join(self.mod_loc_path, filename)

        try:
            # 读取目标文件中现有的翻译，保留未修改的条目及顺序
            existing = {}  # 现有翻译 key -> value
            existing_order = []  # 保持原有顺序
            in_section = False

            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped == "l_simp_chinese:":
                            in_section = True
                            continue
                        if not in_section:
                            if stripped.startswith("l_"):
                                in_section = False
                            continue
                        if stripped.startswith("#") or not stripped:
                            continue
                        m = LOC_PATTERN.match(stripped)
                        if m:
                            key = m.group(1)
                            val = m.group(2) or m.group(3) or m.group(4)
                            if key and val is not None:
                                existing[key] = val
                                existing_order.append(key)

            # 确定本次要更新的数据
            update_data = keys_to_write if keys_to_write else self.mod_cache

            # 合并现有条目和更新条目，保持原有顺序
            new_content = {}
            new_order = []
            for key in existing_order:
                if key in update_data:
                    new_content[key] = update_data[key]
                else:
                    new_content[key] = existing[key]
                new_order.append(key)

            # 追加新增的key（不在原有顺序中的）
            for key, val in update_data.items():
                if key not in new_content:
                    new_content[key] = val
                    new_order.append(key)

            # 也追加mod_cache中未在update_data中的其他key（保持完整性）
            for key, val in self.mod_cache.items():
                if key not in new_content and key not in update_data:
                    new_content[key] = val
                    new_order.append(key)

            # 同步到 mod 缓存（供界面刷新显示）
            for key, val in new_content.items():
                self.mod_cache[key] = val

            # 写入文件（l_simp_chinese 头 + " key: \"value\"" 每行一条）
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                f.write("l_simp_chinese:\n")
                for key in new_order:
                    val = new_content[key]
                    # 转义：反斜杠、双引号、换行（保证多行描述仍为单行 YML 条目）
                    escaped_val = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                    f.write(f' {key}: "{escaped_val}"\n')

            return True

        except Exception as e:
            return False

    def save_single_entry(self, key: str, name_value: str, desc_value: str,
                           filename: str = None) -> bool:
        """
        保存单个条目（名称+描述）到mod翻译文件
        这是用户编辑单个翻译时的便捷入口
        Args:
            key: 条目键名
            name_value: 名称翻译
            desc_value: 描述翻译
            filename: 目标文件（None 使用 self.mod_file_name）
        """
        update = {key: name_value, f"{key}_desc": desc_value}
        return self.save_to_mod(filename, update)

    def save_name(self, key: str, name_value: str, filename: str = None) -> bool:
        """仅保存名称翻译，保留文件中已有的描述翻译（不会写入空描述）。"""
        return self.save_to_mod(filename, {key: name_value})

    def save_desc(self, key: str, desc_value: str, filename: str = None) -> bool:
        """仅保存描述翻译，保留文件中已有的名称翻译（不会写入空名称）。"""
        return self.save_to_mod(filename, {f"{key}_desc": desc_value})


# 全局编辑器单例
_editor = None


def get_translation_editor(hoi4_loc_path: str = "", mod_loc_path: str = "",
                           mod_file_name: str = None) -> TranslationEditor:
    """
    获取翻译编辑器单例
    首次调用时创建实例，后续调用可以更新路径
    使用单例模式确保整个应用中使用同一份编辑器状态
    """
    global _editor
    if _editor is None:
        if mod_file_name:
            _editor = TranslationEditor(hoi4_loc_path, mod_loc_path, mod_file_name)
        else:
            # 未指定文件名时使用类默认（focus_mod_l_simp_chinese.yml），避免 None 导致保存失败
            _editor = TranslationEditor(hoi4_loc_path, mod_loc_path)
    else:
        # 如果传入了新路径，更新已有的编辑器实例
        if hoi4_loc_path or mod_loc_path or mod_file_name:
            _editor.set_paths(
                hoi4_loc_path or _editor.hoi4_loc_path,
                mod_loc_path or _editor.mod_loc_path,
                mod_file_name,
            )
    return _editor
