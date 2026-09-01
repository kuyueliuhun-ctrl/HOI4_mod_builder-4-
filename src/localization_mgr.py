"""
本地化管理器 — 管理HOI4游戏的本地化文本缓存
负责加载游戏和mod的 *_l_simp_chinese.yml 文件，提取翻译文本，
并提供 key 查询接口（名称、描述、提示文本）。

与 gui_translator.py 的区别：
  - gui_translator: 翻译PDX脚本关键字（如 completion_reward → 完成奖励）
  - localization_mgr: 管理游戏本地化文本（如 GER_democratic → 德意志民主国）
"""

import os
import re


# YML行解析正则：key:数字 "value" 或 key: "value"
LOC_PATTERN = re.compile(
    r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:"([^"]*)"|0\s*"([^"]*)"|\d+\s*"([^"]*)")'
)


def parse_loc_yml_file(filepath, cache, section="l_simp_chinese"):
    """解析单个本地化 YML 文件，将键值对写入 cache 字典。

    Args:
        filepath: YML 文件路径
        cache: 写入目标字典（key -> 翻译文本）
        section: 语言节名（如 "l_simp_chinese" / "l_english"）
    """
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            in_section = False  # 标记是否进入目标语言节
            marker = section + ":"
            for line in f:
                stripped = line.strip()
                # 进入目标语言节
                if stripped == marker:
                    in_section = True
                    continue
                if not in_section:
                    continue
                # 跳过注释行和空行
                if stripped.startswith("#") or not stripped:
                    continue
                m = LOC_PATTERN.match(stripped)
                if m:
                    key = m.group(1)
                    val = m.group(2) or m.group(3) or m.group(4)
                    if key and val:
                        cache[key] = val
    except Exception:
        pass  # 忽略无法读取的文件


def load_loc_yml_dir(loc_dir, cache, suffix="_l_simp_chinese.yml",
                     section="l_simp_chinese"):
    """加载目录下所有指定语言后缀的本地化 YML 文件到 cache。

    Args:
        loc_dir: 本地化语言目录
        cache: 写入目标字典
        suffix: 文件名后缀（如 *_l_simp_chinese.yml / *_l_english.yml）
        section: 语言节名

    Returns:
        list[str]: 已加载的文件路径列表
    """
    loaded = []
    try:
        names = os.listdir(loc_dir)
    except Exception:
        return loaded
    for filename in sorted(names):
        if not filename.endswith(suffix):
            continue
        filepath = os.path.join(loc_dir, filename)
        parse_loc_yml_file(filepath, cache, section=section)
        loaded.append(filepath)
    return loaded


class LocalizationManager:
    """
    本地化管理器
    从 HOI4 游戏目录和 mod 目录中加载简体中文翻译文件，
    为其他模块提供本地化文本查询功能。

    加载优先级：mod 文件覆盖游戏原始文件（后加载的覆盖先加载的）
    """

    def __init__(self):
        # key -> 中文翻译文本 的映射缓存
        self.loc_cache = {}
        # 已加载的目录路径列表（防止重复加载同一目录）
        self._load_paths = []
        # 参考语言缓存（P2-6 多语言回退）：简中缺失时回退显示，只读
        self.ref_caches = {}
        self._ref_loaded = []

    # 参考语言：简中键缺失时按顺序回退（保证多语言 mod 名称/描述可见）
    REF_LANGUAGES = ("english",)

    def add_game_path(self, hoi4_path):
        """
        加载HOI4游戏的本地化文件
        Args:
            hoi4_path: HOI4游戏根目录路径
        """
        if not hoi4_path or not os.path.isdir(hoi4_path):
            return
        # 游戏本地化目录：HOI4_path/localisation/simp_chinese
        loc_dir = os.path.join(hoi4_path, "localisation", "simp_chinese")
        self._load_localisation_dir(loc_dir)
        # 参考语言（P2-6）：如 localisation/english，简中缺失时回退显示
        for lang in self.REF_LANGUAGES:
            ref_dir = os.path.join(hoi4_path, "localisation", lang)
            self._load_ref_dir(lang, ref_dir)

    def add_mod_path(self, mod_path):
        """
        加载mod的本地化文件
        支持多种目录命名方式：localisation 和 localization 两种拼写
        Args:
            mod_path: mod目录路径
        """
        if not mod_path or not os.path.isdir(mod_path):
            return

        # 标准目录：mod/localisation/simp_chinese
        loc_dir = os.path.join(mod_path, "localisation", "simp_chinese")
        self._load_localisation_dir(loc_dir)

        # 也检查备用的拼写变体 (localization 是美式拼写)
        for sub in ("localization", "localisation"):
            alt_dir = os.path.join(mod_path, sub, "simp_chinese")
            if os.path.isdir(alt_dir) and alt_dir != loc_dir:
                self._load_localisation_dir(alt_dir)

    def clear(self):
        """清空所有缓存和加载记录"""
        self.loc_cache.clear()
        self._load_paths.clear()
        self.ref_caches.clear()
        self._ref_loaded.clear()

    def reload(self, game_path=None, mod_path=None):
        """
        重新加载所有本地化数据
        先清空缓存，再按顺序加载游戏和mod
        """
        self.clear()
        if game_path:
            self.add_game_path(game_path)
        if mod_path:
            self.add_mod_path(mod_path)

    def get_name(self, focus_id):
        """
        获取本地化名称（简中优先，缺失时回退参考语言，见 P2-6）
        Args:
            focus_id: 本地化键名（如 GER_democratic_party）
        Returns:
            翻译文本，无匹配时返回空字符串
        """
        v = self.loc_cache.get(focus_id, "")
        if v:
            return v
        return self._ref_get(focus_id)

    def get_desc(self, focus_id):
        """
        获取本地化描述（简中优先，缺失时回退参考语言）
        HOI4惯例：描述键名为 原key + "_desc"
        Args:
            focus_id: 本地化键名
        """
        v = self.loc_cache.get(focus_id + "_desc", "")
        if v:
            return v
        return self._ref_get(focus_id + "_desc")

    def _ref_get(self, key):
        """参考语言回退查询：按 REF_LANGUAGES 顺序取第一个非空值。"""
        for lang in self.REF_LANGUAGES:
            cache = self.ref_caches.get(lang)
            if cache:
                v = cache.get(key, "")
                if v:
                    return v
        return ""

    def _load_ref_dir(self, lang, loc_dir):
        """加载参考语言目录（只读回退用）；目录缺失或已加载则跳过。"""
        if not os.path.isdir(loc_dir):
            return
        key = (lang, loc_dir)
        if key in self._ref_loaded:
            return
        self._ref_loaded.append(key)
        cache = self.ref_caches.setdefault(lang, {})
        load_loc_yml_dir(loc_dir, cache, suffix="_l_%s.yml" % lang,
                         section="l_%s" % lang)

    def _load_localisation_dir(self, loc_dir):
        """
        加载指定目录下的所有 *_l_simp_chinese.yml 文件
        Args:
            loc_dir: 包含翻译文件的目录路径
        """
        # 目录不存在或已加载过则跳过（防止重复加载）
        if not os.path.isdir(loc_dir) or loc_dir in self._load_paths:
            return
        # 记录该目录已加载
        self._load_paths.append(loc_dir)
        load_loc_yml_dir(loc_dir, self.loc_cache)


# 全局本地化管理器单例
_manager = None


def get_localization_manager():
    """
    获取本地化管理器单例
    使用单例模式确保整个应用使用同一份翻译缓存
    """
    global _manager
    if _manager is None:
        _manager = LocalizationManager()
    return _manager
