"""
模板调度器 — 管理 HOI4 模组模板文件的检测与使用
模板存放在项目根目录/templates文件夹中，按类型分目录管理。

支持的模板类型：
  - focus_tree:  国策树模板（文件级）
  - focus:       单个国策模板（节点级）
  - ideas_file:  国家理念文件模板（文件级/节点级）
  - event:       事件模板（文件级/节点级）
  - decision:    决议模板（文件级/节点级）
  - law:         法案模板（文件级）
  - character:   角色模板（文件级/节点级）
  - bookmark:    剧本模板（文件级）
  - country_history: 国家历史文件模板（文件级）
  - scripted:    脚本化效果/触发器模板（文件级/节点级）
  - gui:         界面机制模板（文件级）
  - ai_strategy: AI战略编写模板（文件级/节点级）
  - unit:        兵种模板（文件级）
  - equipment:   装备模板（文件级）
  - tech:        科技模板（文件级）
  - opinion_modifier: 关系修正模板（文件级）
  - effect:      效果器模板（节点级）
  - trigger:     触发器模板（节点级）
  - custom:      自定义模板

模板用途（usage）分类：
  - file:  创建文件时所需的模板（工作台新建文件、从模板新建文件）
  - node:  用户可调用的模板（树编辑器添加节点）
  - both:  两者皆可
  类型默认用途见 TEMPLATE_TYPES；可在 templates/usage.json 中按文件覆写。

功能：
  - 检测并搜索模板（支持用途过滤）
  - 从现有文件创建模板
  - 使用模板生成新文件（支持变量替换）
"""

import json
import os
import re
from typing import Dict, List, Optional


# 模板类型定义 — 每种类型对应HOI4 mod的一种常见文件
TEMPLATE_TYPES = {
    "focus_tree": {
        "name": "国策树",
        "extension": ".txt",
        "usage": "file",
    },
    "focus": {
        "name": "单个国策",
        "extension": ".txt",
        "usage": "node",
    },
    "ideas_file": {
        "name": "国家理念文件",
        "extension": ".txt",
        "usage": "both",
    },
    "event": {
        "name": "事件",
        "extension": ".txt",
        "usage": "both",
    },
    "decision": {
        "name": "决议",
        "extension": ".txt",
        "usage": "both",
    },
    "law": {
        "name": "法案",
        "extension": ".txt",
        "usage": "file",
    },
    "character": {
        "name": "角色",
        "extension": ".txt",
        "usage": "both",
    },
    "bookmark": {
        "name": "剧本",
        "extension": ".txt",
        "usage": "file",
    },
    "country_history": {
        "name": "国家历史文件",
        "extension": ".txt",
        "usage": "file",
    },
    "scripted": {
        "name": "脚本化效果/触发器",
        "extension": ".txt",
        "usage": "both",
    },
    "gui": {
        "name": "界面机制",
        "extension": ".txt",
        "usage": "file",
    },
    "ai_strategy": {
        "name": "AI战略编写",
        "extension": ".txt",
        "usage": "both",
    },
    "unit": {
        "name": "兵种",
        "extension": ".txt",
        "usage": "file",
    },
    "equipment": {
        "name": "装备",
        "extension": ".txt",
        "usage": "file",
    },
    "tech": {
        "name": "科技",
        "extension": ".txt",
        "usage": "file",
    },
    "opinion_modifier": {
        "name": "关系修正",
        "extension": ".txt",
        "usage": "file",
    },
    "effect": {
        "name": "效果器",
        "extension": ".txt",
        "usage": "node",
    },
    "trigger": {
        "name": "触发器",
        "extension": ".txt",
        "usage": "node",
    },
    "custom": {
        "name": "自定义模板",
        "extension": ".txt",
        "usage": "both",
    },
}


class TemplateScheduler:
    """
    模板调度器 — 检测并管理模板文件
    目录结构：templates/
                ├── focus_tree/    # 国策树模板
                ├── focus/         # 单个国策模板
                ├── ideas_file/    # 国家理念模板
                ├── event/         # 事件模板
                ├── decision/      # 决议模板
                ├── effect/        # 效果器模板
                ├── trigger/       # 触发器模板
                └── custom/        # 自定义模板
    """

    def __init__(self, templates_dir: str = None):
        # 模板根目录，默认为项目根目录下的 templates
        if templates_dir is None:
            self.templates_dir = os.path.join(os.getcwd(), "templates")
        else:
            self.templates_dir = templates_dir
        self._usage_overrides = self._load_usage_overrides()

    def _load_usage_overrides(self) -> Dict[str, str]:
        """加载 templates/usage.json 中的按文件用途覆写表。

        键为相对 templates 目录的文件路径（如 custom/mod常用代码.txt），
        值为 "file" / "node" / "both"。
        """
        path = os.path.join(self.templates_dir, "usage.json")
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def get_template_usage(self, filepath: str) -> str:
        """获取模板用途：优先 usage.json 覆写，其次类型默认值。

        Returns:
            "file" / "node" / "both"
        """
        rel = os.path.relpath(filepath, self.templates_dir)
        rel = rel.replace(os.sep, "/")
        override = self._usage_overrides.get(rel)
        if override in ("file", "node", "both"):
            return override
        if rel.startswith("custom/"):
            return "both"
        detected_type = rel.split("/")[0]
        return TEMPLATE_TYPES.get(detected_type, {}).get("usage", "both")

    @staticmethod
    def _system_type_map():
        """中文类型名 -> 模板类型 key（来自工作台内容类型定义）。

        类型没有基础模板类型时使用中文名本身作为类型 key。
        """
        try:
            from workbench import CONTENT_TYPES
            return {c[1]: (c[4] or c[1]) for c in CONTENT_TYPES}
        except Exception:
            return {}

    @staticmethod
    def _classify_system_usage(filename):
        """根据文件名推断系统模板用途：基础* = file，项目* = node，其余 both。"""
        if filename.startswith("基础") or "基础" in filename:
            return "file"
        if filename.startswith("项目") or "项目" in filename:
            return "node"
        return "both"

    def _iter_system_dirs(self):
        """迭代 系统模板 下的模板文件。

        目录结构（扁平）：templates/系统模板/<中文类型名>/基础模板.txt（file）
                          templates/系统模板/<中文类型名>/项目模板.txt（node）
        兼容旧结构：templates/系统模板/<中文类型名>/基础模版/ 与 项目模版/ 子目录。
        Yields:
            (文件路径, 模板类型key, 用途, 中文类型标签)
        """
        root = os.path.join(self.templates_dir, "系统模板")
        if not os.path.isdir(root):
            return
        type_map = self._system_type_map()
        for cat_name in sorted(os.listdir(root)):
            cat_dir = os.path.join(root, cat_name)
            if not os.path.isdir(cat_dir):
                continue
            ttype = type_map.get(cat_name, cat_name)
            # 扁平结构：直接放在类型目录下的文件
            for filename in sorted(os.listdir(cat_dir)):
                filepath = os.path.join(cat_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                yield filepath, ttype, self._classify_system_usage(filename), cat_name
            # 兼容旧子目录结构
            for sub, usage in (("基础模版", "file"), ("项目模版", "node")):
                sub_dir = os.path.join(cat_dir, sub)
                if os.path.isdir(sub_dir):
                    for filename in sorted(os.listdir(sub_dir)):
                        filepath = os.path.join(sub_dir, filename)
                        if os.path.isfile(filepath):
                            yield filepath, ttype, usage, cat_name

    def search_templates(self, keyword: str = "", template_type: str = "",
                         usage: str = "", include_system: bool = True) -> List[dict]:
        """
        搜索模板（按文件名模糊匹配）
        Args:
            keyword: 搜索关键字（匹配文件名，不区分大小写）
            template_type: 限定模板类型，空字符串表示搜索所有类型
            usage: 限定模板用途（file/node/both），空字符串表示不限
            include_system: 是否包含 系统模板 文件夹中的内容（默认包含）
        Returns:
            匹配的模板信息列表 [{name, filename, filepath, type, type_label, usage}, ...]
        """
        results = []
        keyword_lower = keyword.lower()

        # 确定搜索范围：指定类型则只搜该类型子目录，否则搜所有
        search_dirs = []
        if template_type and template_type in TEMPLATE_TYPES:
            search_dirs = [os.path.join(self.templates_dir, template_type)]
        else:
            # 搜索所有类型的子目录 + 根目录
            search_dirs = [os.path.join(self.templates_dir, t) for t in TEMPLATE_TYPES]
            search_dirs.append(self.templates_dir)  # 也搜索根目录

        seen = set()  # 去重集合（使用文件真实路径）
        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            for filename in os.listdir(search_dir):
                filepath = os.path.join(search_dir, filename)
                # 跳过子目录
                if os.path.isdir(filepath):
                    continue

                # 按关键字过滤（不区分大小写）
                if keyword_lower and keyword_lower not in filename.lower():
                    continue

                # 按用途过滤
                if usage:
                    file_usage = self.get_template_usage(filepath)
                    if usage == "file" and file_usage not in ("file", "both"):
                        continue
                    if usage == "node" and file_usage not in ("node", "both"):
                        continue

                # 避免重复（通过真实路径去重）
                real_path = os.path.realpath(filepath)
                if real_path in seen:
                    continue
                seen.add(real_path)

                # 从相对路径中提取类型信息
                # 格式: templates/focus_tree/xxx.txt → type = "focus_tree"
                rel_path = os.path.relpath(filepath, self.templates_dir)
                rel_parts = rel_path.split(os.sep)
                detected_type = rel_parts[0] if len(rel_parts) > 1 else "custom"

                # 指定类型时：仅保留类型匹配的模板（支持中文系统类型名）
                if template_type and detected_type != template_type:
                    continue

                # 获取不含扩展名的文件名（用于显示）
                name_without_ext = os.path.splitext(filename)[0]
                # 隐藏 _ 前缀（默认模板标记）
                if name_without_ext.startswith("_"):
                    name_without_ext = name_without_ext[1:]

                results.append({
                    "name": name_without_ext,
                    "filename": filename,
                    "filepath": filepath,
                    "type": detected_type,
                    "type_label": TEMPLATE_TYPES.get(detected_type, {}).get("name", "未知"),
                    "usage": self.get_template_usage(filepath),
                })

        # 扫描系统模板目录（templates/系统模板/<中文类型>/）
        if include_system:
            for filepath, det_type, det_usage, cat_label in self._iter_system_dirs():
                if template_type and det_type != template_type:
                    continue
                filename = os.path.basename(filepath)
                if keyword_lower and keyword_lower not in filename.lower():
                    continue
                if usage and det_usage != usage:
                    continue
                real_path = os.path.realpath(filepath)
                if real_path in seen:
                    continue
                seen.add(real_path)

                name_without_ext = os.path.splitext(filename)[0]
                if name_without_ext.startswith("_"):
                    name_without_ext = name_without_ext[1:]

                results.append({
                    "name": name_without_ext,
                    "filename": filename,
                    "filepath": filepath,
                    "type": det_type,
                    "type_label": cat_label,
                    "usage": det_usage,
                })

        return results

    def create_template(self, name: str, content: str, template_type: str = "custom") -> Optional[str]:
        """
        创建新模板
        Args:
            name: 模板名称
            content: 模板内容
            template_type: 模板类型
        Returns:
            创建的模板文件路径，失败返回 None
        """
        if template_type not in TEMPLATE_TYPES:
            template_type = "custom"

        # 获取该类型的扩展名
        ext = TEMPLATE_TYPES[template_type].get("extension", ".txt")
        # 清理模板名称（移除非法字符）
        safe_name = self._sanitize_filename(name)
        if not ext.startswith("."):
            ext = f".{ext}"

        filename = f"{safe_name}{ext}"
        type_dir = os.path.join(self.templates_dir, template_type)
        os.makedirs(type_dir, exist_ok=True)

        filepath = os.path.join(type_dir, filename)

        # 如果文件已存在，自动添加序号避免覆盖
        counter = 1
        while os.path.exists(filepath):
            filename = f"{safe_name}_{counter}{ext}"
            filepath = os.path.join(type_dir, filename)
            counter += 1

        try:
            # 使用 utf-8 写入（HOI4 脚本解析器拒绝 BOM，BOM 会破坏 ideas 等文件解析）
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return filepath
        except Exception:
            return None

    def get_template_content(self, filepath: str) -> Optional[str]:
        """获取模板文件的文本内容

        自动清除 \\r 行尾符，统一为 \\n，避免 PyQt 显示时出现回车覆盖问题。
        """
        try:
            with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
                content = f.read()
            return content.replace("\r\n", "\n").replace("\r", "\n")
        except Exception:
            return None

    def apply_template(self, template_path: str, target_path: str,
                        replacements: Dict[str, str] = None) -> bool:
        """
        使用模板创建文件（支持变量替换）
        Args:
            template_path: 模板文件路径
            target_path: 目标输出路径
            replacements: 替换字典，如 {"__FOCUS_ID__": "my_focus"}
                          模板中的占位符会被替换为实际值
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 读取模板内容
            content = self.get_template_content(template_path)
            if content is None:
                return False

            # 执行变量替换（如将 __FOCUS_ID__ 替换为实际国策ID）
            if replacements:
                for old, new in replacements.items():
                    content = content.replace(old, new)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # 写入目标文件（无 BOM，HOI4 脚本解析器拒绝 BOM）
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """
        清理文件名，移除非法字符
        Windows/Linux 文件名不允许的字符: < > : " / \\ | ? *
        将它们替换为下划线
        """
        illegal_chars = r'[<>:"/\\|?*]'
        return re.sub(illegal_chars, "_", name).strip()

    # ────────────── 模板变量（占位符）支持 ──────────────

    # 占位符格式：__变量名__（与 apply_template 的 replacements 兼容）
    VAR_PATTERN = re.compile(r"__([A-Za-z0-9_\u4e00-\u9fff]+)__")

    def _rel_key(self, filepath: str) -> str:
        """获取模板文件相对 templates 目录的键（正斜杠分隔）。"""
        try:
            rel = os.path.relpath(filepath, self.templates_dir)
        except Exception:
            rel = os.path.basename(filepath)
        return rel.replace(os.sep, "/")

    def variable_config_path(self) -> str:
        """模板变量配置文件路径（templates/variables.json）。"""
        return os.path.join(self.templates_dir, "variables.json")

    def _load_variable_config(self) -> Dict:
        """读取全部模板的变量配置（filepath -> {variables: [...]}）。"""
        try:
            with open(self.variable_config_path(), "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def scan_template_variables(self, content: str) -> List[str]:
        """扫描模板内容中的占位符变量（按出现顺序去重）。

        Args:
            content: 模板文本内容
        Returns:
            list[str]: 占位符列表，如 ["__BUILDING_TYPE__", "__BUILDING_LEVEL__"]
        """
        if not content:
            return []
        seen = []
        for m in self.VAR_PATTERN.finditer(content):
            token = m.group(0)
            if token not in seen:
                seen.append(token)
        return seen

    def get_template_variables(self, filepath: str) -> List[Dict]:
        """获取模板的变量配置。

        配置项：{"name": 占位符, "label": 中文说明, "enabled": 是否启用填入}
        未配置过时自动扫描内容中的占位符生成默认配置（默认启用）。

        Args:
            filepath: 模板文件路径
        Returns:
            list[dict]: 变量配置列表
        """
        key = self._rel_key(filepath)
        config = self._load_variable_config().get(key, {})
        configured = config.get("variables", []) if isinstance(config, dict) else []

        content = self.get_template_content(filepath) or ""
        tokens = self.scan_template_variables(content)

        # 合并：保留配置中的 label/顺序，内容中消失的变量移除，新出现的变量追加
        result = []
        seen = set()
        for v in configured:
            name = v.get("name", "")
            if name in tokens and name not in seen:
                result.append({
                    "name": name,
                    "label": v.get("label", ""),
                    "enabled": bool(v.get("enabled", True)),
                })
                seen.add(name)
        for tok in tokens:
            if tok not in seen:
                result.append({"name": tok, "label": "", "enabled": True})
                seen.add(tok)
        return result

    def set_template_variables(self, filepath: str, variables: List[Dict]) -> bool:
        """保存模板的变量配置到 variables.json。

        Args:
            filepath: 模板文件路径
            variables: [{"name", "label", "enabled"}, ...]
        Returns:
            成功返回 True
        """
        key = self._rel_key(filepath)
        config = self._load_variable_config()
        config[key] = {"variables": variables}
        try:
            os.makedirs(self.templates_dir, exist_ok=True)
            with open(self.variable_config_path(), "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_enabled_variables(self, filepath: str) -> List[Dict]:
        """获取模板中启用的变量（用于使用时弹出填写框）。"""
        return [v for v in self.get_template_variables(filepath) if v.get("enabled")]

    @staticmethod
    def apply_template_variables(content: str, values: Dict[str, str]) -> str:
        """按填写值替换模板内容中的占位符。

        Args:
            content: 模板文本
            values: 占位符 -> 替换值，如 {"__BUILDING_TYPE__": "arms_factory"}
        Returns:
            替换后的文本（未填写值的占位符保留原样）
        """
        for token, value in values.items():
            if value is not None:
                content = content.replace(token, value)
        return content


# 全局调度器单例
_scheduler = None


def get_template_scheduler(templates_dir: str = None) -> TemplateScheduler:
    """
    获取模板调度器单例
    使用单例模式确保整个应用使用同一份模板缓存
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = TemplateScheduler(templates_dir)
    return _scheduler
