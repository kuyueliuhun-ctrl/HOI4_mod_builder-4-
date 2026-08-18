"""
翻译文件自动加载模块 — 扫描 translations 目录，自动识别并加载翻译文件。

支持的文件格式：
- *.json          → 翻译对文件（键值对）或自定义语句文件
- *_l_simp_chinese.yml → HOI4 本地化文件
- translations_bundle.json → 完整翻译包

使用方法：
1. 将翻译文件拖入 translations/ 文件夹
2. 程序启动时自动加载
3. 调用 reload() 可重新扫描文件夹

架构说明：
  TranslationLoader 是一个翻译文件扫描器，负责自动识别 translations/ 目录中的
  各种翻译文件格式，并将解析后的翻译数据注入到 GuiTranslator 实例中。
  TRANSLATIONS_DIR 是项目根目录下的 translations 文件夹的绝对路径。
"""
from project_paths import PROJECT_ROOT

import os
import re
import json


# 翻译文件默认存放目录：项目根目录/translations
TRANSLATIONS_DIR = os.path.join(PROJECT_ROOT, "translations")


class TranslationLoader:
    """
    翻译文件扫描器 — 自动识别并加载 translations 目录中的翻译文件。
    支持的格式：
      - translations_bundle.json: 完整翻译包（含builtin_dict, loc_cache, custom_statements）
      - *_l_simp_chinese.yml: HOI4标准的简体中文本地化文件
      - *.json: 翻译对文件（键值对）或自定义语句文件
    """

    def __init__(self, translator=None):
        # 关联的翻译器实例，用于注入翻译数据
        self.translator = translator
        # 已成功加载的文件名列表
        self.loaded_files = []

    def scan_and_load(self) -> dict:
        """
        扫描 translations 目录并加载所有翻译文件。
        遍历目录中的所有文件，根据文件扩展名和名称选择对应的加载方法。

        Returns:
            加载结果 {"files_loaded": N, "keys_added": N, "errors": [...]}
        """
        # 清空已加载列表
        self.loaded_files = []
        result = {"files_loaded": 0, "keys_added": 0, "errors": []}

        # translations 目录不存在则直接返回
        if not os.path.isdir(TRANSLATIONS_DIR):
            return result

        # 遍历目录中所有文件
        for filename in os.listdir(TRANSLATIONS_DIR):
            filepath = os.path.join(TRANSLATIONS_DIR, filename)
            # 跳过目录（只处理文件）
            if not os.path.isfile(filepath):
                continue

            try:
                # 根据文件类型调用对应的加载方法
                added = self._load_file(filepath, filename)
                if added > 0:
                    # 加载成功，记录统计信息
                    result["files_loaded"] += 1
                    result["keys_added"] += added
                    self.loaded_files.append(filename)
            except Exception as e:
                result["errors"].append(f"{filename}: {str(e)}")

        return result

    def _load_file(self, filepath: str, filename: str) -> int:
        """
        根据文件类型选择加载方式
        Returns: 成功加载的键数量
        """
        # 完整翻译包（优先级最高）
        if filename == "translations_bundle.json":
            return self._load_bundle(filepath)
        # HOI4本地化YML文件
        elif filename.endswith("_l_simp_chinese.yml"):
            return self._load_yml_file(filepath)
        # 普通JSON文件
        elif filename.endswith(".json"):
            return self._load_json_file(filepath)
        # 无法识别的文件格式
        return 0

    def _load_bundle(self, filepath: str) -> int:
        """
        加载翻译包文件（translations_bundle.json）
        翻译包可以包含 builtin_dict（内置字典扩展）、loc_cache（本地化缓存扩展）
        和 custom_statements（自定义语句），全部合并到关联的 translator 中。
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        added = 0  # 计数器：成功添加的条目数

        # 加载内置字典扩展
        if "builtin_dict" in data and isinstance(data["builtin_dict"], dict):
            for key, val in data["builtin_dict"].items():
                # 不覆盖已有的键
                if key not in self.translator.command_dict:
                    self.translator.command_dict[key] = val
                    added += 1

        # 加载本地化缓存扩展
        if "loc_cache" in data and isinstance(data["loc_cache"], dict):
            for key, val in data["loc_cache"].items():
                if key not in self.translator.loc_cache:
                    self.translator.loc_cache[key] = val
                    added += 1

        # 加载自定义语句
        if "custom_statements" in data:
            statements = data["custom_statements"].get("statements", [])
            for stmt in statements:
                key = stmt.get("key", "")
                if key and key not in self.translator.custom_statements:
                    self.translator.custom_statements[key] = stmt
                    added += 1

        return added

    def _load_yml_file(self, filepath: str) -> int:
        """
        加载 HOI4 本地化 YAML 文件
        解析 l_simp_chinese: 节中的翻译条目，格式：key:数字 "value"
        """
        # YML行匹配模式
        pattern = re.compile(
            r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:"([^"]*)"|0\s*"([^"]*)"|\d+\s*"([^"]*)")'
        )
        added = 0

        with open(filepath, "r", encoding="utf-8-sig") as f:
            in_section = False  # 标记是否进入翻译节
            for line in f:
                stripped = line.strip()
                # 进入 l_simp_chinese 翻译节
                if stripped == "l_simp_chinese:":
                    in_section = True
                    continue
                # 尚未进入翻译节，跳过
                if not in_section:
                    continue
                # 跳过注释行和空行
                if stripped.startswith("#") or not stripped:
                    continue
                m = pattern.match(stripped)
                if m:
                    key = m.group(1)
                    val = m.group(2) or m.group(3) or m.group(4)
                    if key and val:
                        # 不覆盖已有的本地化缓存条目
                        if key not in self.translator.loc_cache:
                            self.translator.loc_cache[key] = val
                            added += 1
        return added

    def _load_json_file(self, filepath: str) -> int:
        """
        加载 JSON 翻译文件。自动识别以下格式：
        - 自定义语句格式（含 statements 数组）
        - 简单键值对格式: {"key": "中文值"}
        - PDX翻译格式（含 format/regex 字段）: {"key": {"format": "中文值", "regex": "..."}}
        """
        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return 0

        # 自定义语句格式：包含 "statements" 数组
        if "statements" in data and isinstance(data["statements"], list):
            return self._load_custom_statements(data["statements"])

        # 简单键值对格式或PDX翻译格式
        added = 0
        for key, val in data.items():
            if not isinstance(val, str):
                # PDX翻译格式: {"key": {"format": "中文翻译", "regex": "正则"}}
                if isinstance(val, dict) and "format" in val:
                    cn = val["format"]
                else:
                    continue  # 跳过无法识别格式的值
            else:
                cn = val  # 简单键值对，val就是翻译文本

            # 不覆盖已有的本地化缓存
            if key not in self.translator.loc_cache:
                self.translator.loc_cache[key] = cn
                added += 1

        return added

    def _load_custom_statements(self, statements: list) -> int:
        """
        加载自定义语句列表
        自定义语句格式：[{key: str, cn_name: str, node_type: str, ...}]
        """
        added = 0
        for stmt in statements:
            key = stmt.get("key", "")
            if key and key not in self.translator.custom_statements:
                self.translator.custom_statements[key] = stmt
                added += 1
        return added

    def get_loaded_files(self) -> list:
        """返回已加载的文件名列表（不含路径）"""
        return self.loaded_files.copy()

    def get_available_files(self) -> list:
        """
        返回 translations 目录中所有可识别的文件列表
        用于UI显示可供加载的文件
        """
        if not os.path.isdir(TRANSLATIONS_DIR):
            return []
        files = []
        for fn in os.listdir(TRANSLATIONS_DIR):
            fp = os.path.join(TRANSLATIONS_DIR, fn)
            # 只统计可识别的文件格式
            if os.path.isfile(fp) and (fn.endswith(".json") or fn.endswith(".yml")):
                files.append(fn)
        return sorted(files)


def get_translations_dir() -> str:
    """返回翻译文件存放目录的绝对路径"""
    return TRANSLATIONS_DIR
