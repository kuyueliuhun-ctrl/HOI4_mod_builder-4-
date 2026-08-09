"""词条注册表模块

加载翻译文件夹中的词条文件（自动整理词条 + 用户自定义词条），
为语句搜索、AI 提示词生成、树编辑器节点创建提供统一数据源。

词条数据结构（每个词条）：
- key        英文命令名
- cn         中文翻译
- node_type  节点类型："block"（块节点，key = { ... }）或 "value"（值节点，key = value）
- tags       标签列表（分类标签，如 政治/经济/陆军/海军/空军/科技/外交/修正…）
- description 可选描述
- source     来源："common_code"（自动整理）或 "user"（用户自定义）

词条文件位置（均位于 translations/ 文件夹，独立于翻译文件）：
- effect_terms.json  自动整理词条（由常用代码整理而来）
- custom_terms.json  用户自定义词条（词条管理对话框读写）
"""

import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSLATIONS_DIR = os.path.join(_BASE_DIR, "translations")

TERM_FILES = [
    os.path.join(TRANSLATIONS_DIR, "effect_terms.json"),
    os.path.join(TRANSLATIONS_DIR, "custom_terms.json"),
]

NODE_TYPE_NAMES = {
    "block": "块",
    "value": "值",
}


class TermRegistry:
    """词条注册表：加载并搜索词条。"""

    def __init__(self, term_files=None):
        self.term_files = term_files or TERM_FILES
        self.terms = []        # 全部词条 dict 列表
        self.by_key = {}       # key -> term
        self._loaded = False

    def load(self):
        """加载全部词条文件（可重复调用）。"""
        self.terms = []
        self.by_key = {}
        for path in self.term_files:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            for term in data.get("terms", []):
                key = term.get("key", "")
                if not key:
                    continue
                term.setdefault("cn", key)
                term.setdefault("node_type", "value")
                term.setdefault("tags", [])
                term.setdefault("description", "")
                term.setdefault("source", "user")
                self.by_key[key] = term
                self.terms.append(term)
        self._loaded = True

    def ensure_loaded(self):
        if not self._loaded:
            self.load()

    def get(self, key):
        """按命令名获取词条。"""
        self.ensure_loaded()
        return self.by_key.get(key)

    def get_cn(self, key):
        """获取命令的中文翻译。"""
        self.ensure_loaded()
        term = self.by_key.get(key)
        return term.get("cn", key) if term else key

    def get_node_type(self, key):
        """获取命令的节点类型（block/value）。"""
        self.ensure_loaded()
        term = self.by_key.get(key)
        return term.get("node_type", "value") if term else "value"

    def get_tags(self, key):
        """获取命令的标签列表。"""
        self.ensure_loaded()
        term = self.by_key.get(key)
        return list(term.get("tags", [])) if term else []

    def search(self, keyword="", node_type=None, tag=None, limit=300):
        """按关键词/节点类型/标签搜索词条。

        关键词匹配：英文命令名、中文翻译、标签、描述。
        节点类型匹配：block / value / None（全部）。
        标签匹配：标签子串。
        """
        self.ensure_loaded()
        kw = (keyword or "").strip().lower()
        results = []
        for term in self.terms:
            if node_type and term.get("node_type") != node_type:
                continue
            if tag:
                tags = term.get("tags", [])
                if not any(tag in t for t in tags):
                    continue
            if kw:
                haystack = " ".join([
                    term.get("key", ""),
                    term.get("cn", ""),
                    " ".join(term.get("tags", [])),
                    term.get("description", ""),
                ]).lower()
                if kw not in haystack:
                    continue
            results.append(term)
            if limit and len(results) >= limit:
                break
        return results

    def counts(self):
        """返回各节点类型词条数量统计。"""
        self.ensure_loaded()
        n_block = sum(1 for t in self.terms if t.get("node_type") == "block")
        n_value = sum(1 for t in self.terms if t.get("node_type") == "value")
        return {"block": n_block, "value": n_value, "total": len(self.terms)}

    def add_user_term(self, key, cn, node_type="value", tags=None, description=""):
        """新增用户自定义词条（立即写入 custom_terms.json）。"""
        self.ensure_loaded()
        term = {
            "key": key,
            "cn": cn,
            "node_type": node_type,
            "tags": tags or [],
            "description": description,
            "source": "user",
        }
        # 若已存在自动整理词条，覆盖为新用户词条
        if key in self.by_key:
            self.terms = [t for t in self.terms if t.get("key") != key]
        self.by_key[key] = term
        self.terms.append(term)
        self._save_user_terms()

    def update_user_term(self, key, cn=None, node_type=None, tags=None, description=None):
        """更新用户自定义词条并保存。"""
        self.ensure_loaded()
        term = self.by_key.get(key)
        if not term or term.get("source") != "user":
            return False
        if cn is not None:
            term["cn"] = cn
        if node_type is not None:
            term["node_type"] = node_type
        if tags is not None:
            term["tags"] = tags
        if description is not None:
            term["description"] = description
        self._save_user_terms()
        return True

    def remove_user_term(self, key):
        """删除用户自定义词条并保存。"""
        self.ensure_loaded()
        term = self.by_key.get(key)
        if not term or term.get("source") != "user":
            return False
        del self.by_key[key]
        self.terms = [t for t in self.terms if t.get("key") != key]
        self._save_user_terms()
        return True

    def _save_user_terms(self):
        """将全部用户词条写回 custom_terms.json（不覆盖自动整理词条）。"""
        user_terms = [t for t in self.terms if t.get("source") == "user"]
        custom_path = os.path.join(TRANSLATIONS_DIR, "custom_terms.json")
        os.makedirs(TRANSLATIONS_DIR, exist_ok=True)
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "terms": user_terms}, f, ensure_ascii=False, indent=1)


_default_registry = None


def get_term_registry():
    """获取全局单例词条注册表。"""
    global _default_registry
    if _default_registry is None:
        _default_registry = TermRegistry()
        _default_registry.load()
    return _default_registry

