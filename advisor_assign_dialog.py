"""顾问分配（generic_advisors.txt）识别与编辑模块

generic_advisors.txt 格式（游戏 history/general 目录）：
    every_possible_country = {
        limit = { ... 国家条件 ... }
        generate_character = {
            token_base = generic_communist_revolutionary
            advisor = {
                slot = political_advisor
                traits = { communist_revolutionary }
                available = { ... }
                ai_will_do = { factor = 1 }
            }
            portraits = { ... }
        }
    }

功能：
- 识别解析：提取 every_possible_country 块、limit 条件、角色（token_base）
- 判断"某角色会给谁"：limit 中的排除国家（NOT/OR/tag）、动态国家等条件摘要
- 编辑：在树形编辑器中提供顾问分配对话框（国家条件 + 顾问参数）
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QMessageBox, QComboBox, QSplitter, QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

from tree_node import TreeNode, tree_from_pdx_text


# ────────────── 纯逻辑：国家 tag 收集 ──────────────

def collect_country_tags(mod_path="", game_path="") -> list:
    """收集 mod 与游戏中的国家 tag 列表（排序去重）。

    数据源：
    - common/countries/ 下裸 tag 文件名（如 14K.txt → 14K）
    - common/country_tags/ 下 TAG = "path" 赋值文件（游戏/扩展国家）

    国家 tag 是全局命名空间，始终保持完整（mod 屏蔽的是该国的原版内容，
    而非标签本身，见 country_filter）。
    """
    tags = set()
    tag_pat = None
    for base in (mod_path, game_path):
        if not base:
            continue
        for sub in ("common/countries", "common/country_tags"):
            d = os.path.join(base, sub)
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                path = os.path.join(d, fn)
                if sub == "common/country_tags" and fn.lower().endswith(".txt"):
                    # TAG = "countries/xxx.txt" 赋值解析
                    if tag_pat is None:
                        import re
                        tag_pat = re.compile(
                            r'^\s*([A-Za-z0-9]{1,4})\s*=\s*"', re.IGNORECASE)
                    try:
                        with open(path, "r", encoding="utf-8-sig") as f:
                            for line in f:
                                m = tag_pat.match(line)
                                if m:
                                    tags.add(m.group(1).upper())
                    except Exception:
                        pass
                else:
                    name, ext = os.path.splitext(fn)
                    if ext.lower() not in (".txt", ""):
                        continue
                    tag = name.strip().upper()
                    if tag and len(tag) <= 4 and not tag.startswith("."):
                        tags.add(tag)
    return sorted(tags)


# ────────────── 纯逻辑：解析与条件提取 ──────────────

def iter_assign_blocks(root_node: TreeNode):
    """遍历树中的 every_possible_country 块（含 shared 变体）。"""
    for child in getattr(root_node, "children", []):
        if child.node_type == "block" and child.key in (
                "every_possible_country", "every_other_country"):
            yield child


def get_character_nodes(block_node: TreeNode):
    """获取块中的 generate_character 节点列表。"""
    return [c for c in block_node.children
            if c.node_type == "block" and c.key == "generate_character"]


def get_token_base(char_node: TreeNode) -> str:
    """获取角色的 token_base（角色令牌）。"""
    for c in char_node.children:
        if c.key == "token_base":
            return c.value
    return ""


def get_advisor_node(char_node: TreeNode) -> TreeNode:
    """获取角色 advisor 子块。"""
    for c in char_node.children:
        if c.key == "advisor" and c.node_type == "block":
            return c
    return None


def _is_exclusion_tag(node: TreeNode) -> bool:
    """判断值节点是否为排除国家的 tag（tag / original_tag，位于顶层 NOT 之下）。"""
    return node.key in ("tag", "original_tag") and node.node_type == "value"


def extract_excluded_tags(limit_node: TreeNode) -> list:
    """提取 limit 中排除的国家 tag（顶层 NOT 块内，不深入 IF 块）。

    支持形式：
    - NOT = { OR = { tag = A tag = B } }
    - NOT = { tag = A }
    - NOT = { OR = { tag = A } OR = { tag = B } }
    original_tag 与 tag 同样视为排除。
    返回 tag 列表（按出现顺序去重）。
    """
    if limit_node is None:
        return []
    result = []
    seen = set()
    for child in limit_node.children:
        if child.key != "NOT" or child.node_type != "block":
            continue
        # NOT 下的 tag 收集（允许一层 OR 包裹）
        for sub in child.children:
            if _is_exclusion_tag(sub):
                tag = sub.value.strip().upper()
                if tag and tag not in seen:
                    seen.add(tag)
                    result.append(tag)
            elif sub.key == "OR" and sub.node_type == "block":
                for t in sub.children:
                    if _is_exclusion_tag(t):
                        tag = t.value.strip().upper()
                        if tag and tag not in seen:
                            seen.add(tag)
                            result.append(tag)
    return result


def remove_exclusion_blocks(limit_node: TreeNode):
    """移除 limit 中顶层 NOT 排除块（NOT 内的 tag/OR 结构）。"""
    keep = []
    for child in limit_node.children:
        if child.key == "NOT" and child.node_type == "block":
            # 检查该 NOT 块是否"纯排除"（不含其他结构）
            if all(_is_exclusion_tag(c) or (c.key == "OR" and c.node_type == "block"
                                            and all(_is_exclusion_tag(t) for t in c.children))
                   for c in child.children):
                continue  # 删除纯排除 NOT 块
        keep.append(child)
    limit_node.children = keep


def rebuild_exclusions(limit_node: TreeNode, tags: list):
    """重建 limit 的排除国家块（返回是否发生变更）。

    先移除旧的顶层 NOT 排除块，再按新列表插入：
    - tags 非空：插入 NOT = { OR = { tag = A tag = B ... } }
    - tags 为空：不插入（表示不排除）
    """
    remove_exclusion_blocks(limit_node)
    tags = [t.upper() for t in tags if t]
    if not tags:
        return
    or_node = TreeNode("block", "OR")
    for t in tags:
        or_node.add_child(TreeNode("value", "tag", t))
    not_node = TreeNode("block", "NOT")
    not_node.add_child(or_node)
    limit_node.add_child(not_node, 0)


def summarize_assign(block_node: TreeNode, excluded_tags=None) -> str:
    """生成角色的分配摘要（中文可读）。

    摘要内容：排除国家、动态国家限制。
    """
    if excluded_tags is None:
        limit = None
        for c in block_node.children:
            if c.key == "limit" and c.node_type == "block":
                limit = c
                break
        excluded_tags = extract_excluded_tags(limit) if limit else []
    parts = ["角色将分配给所有符合条件的国家"]
    if excluded_tags:
        parts.append("排除: " + ", ".join(excluded_tags))
    return "；".join(parts) if parts else "无信息"


def summarize_character(char_node: TreeNode, excluded_tags: list) -> str:
    """单个角色（generate_character）的分配摘要。"""
    token = get_token_base(char_node)
    advisor = get_advisor_node(char_node)
    slot = ""
    if advisor:
        for c in advisor.children:
            if c.key == "slot":
                slot = c.value
                break
    text = f"[{token or '?'}]"
    if slot:
        text += f" 顾问位: {slot}"
    if excluded_tags:
        text += f" 排除: {', '.join(excluded_tags)}"
    return text


# ────────────── 纯逻辑：角色文件 ↔ 顾问分配文件关联 ──────────────

def parse_top_level_blocks(lines):
    """按大括号匹配解析顶层块，返回 [(块首行索引, 块末行索引), ...]（0-based）。

    行级定位，用于在不重写整个文件的情况下替换目标块。
    块文本范围包含完整的 "key = {" 到 "}"。
    """
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        # 顶层块起始：key = { 或 key={
        if "=" in stripped and "{" in stripped and not stripped.startswith("#"):
            key_part = stripped.split("=", 1)[0].strip()
            if key_part and not any(ch in key_part for ch in ('"', "'")):
                start = i
                depth = 0
                j = i
                opened = False
                while j < n:
                    depth += lines[j].count("{") - lines[j].count("}")
                    if "{" in lines[j]:
                        opened = True
                    if opened and depth <= 0:
                        blocks.append((start, j))
                        i = j + 1
                        break
                    j += 1
                else:
                    i += 1
                continue
        i += 1
    return blocks


def block_text(lines, start, end):
    """提取块的行文本（用于判断是否含目标角色）。"""
    return "\n".join(lines[start:end + 1])


def find_character_block(lines, char_name):
    """在文件中定位包含指定角色的 generate_character 顶层块。

    匹配方式：块内 generate_character 的 name = 角色名 或 token_base = 角色名。
    Returns:
        (start, end) 行索引（0-based）；未找到返回 None
    """
    for start, end in parse_top_level_blocks(lines):
        text = block_text(lines, start, end)
        if "generate_character" not in text:
            continue
        for needle in ("name = " + char_name, "name=" + char_name,
                       "token_base = " + char_name, "token_base=" + char_name):
            if needle in text:
                return (start, end)
    return None


def build_assign_block(char_name, excluded_tags, params):
    """构建顾问分配块文本（every_possible_country + generate_character）。

    Args:
        char_name: 角色 ID（generate_character.name）
        excluded_tags: 排除国家列表
        params: 顾问参数 dict（slot/cost/traits/available/ai_will_do_factor）
    """
    lines = ["every_possible_country = {"]
    if excluded_tags:
        lines.append("\tlimit = {")
        lines.append("\t\tNOT = {")
        lines.append("\t\t\tOR = {")
        for tag in excluded_tags:
            lines.append(f"\t\t\t\ttag = {tag}")
        lines.append("\t\t\t}")
        lines.append("\t\t}")
        lines.append("\t}")
    lines.append("\tgenerate_character = {")
    lines.append(f"\t\tname = {char_name}")
    lines.append("\t\tadvisor = {")
    slot = (params or {}).get("slot", "").strip()
    if slot:
        lines.append(f"\t\t\tslot = {slot}")
    cost = (params or {}).get("cost", "").strip()
    if cost:
        lines.append(f"\t\t\tcost = {cost}")
    traits = (params or {}).get("traits", "").strip()
    if traits:
        lines.append("\t\t\ttraits = {")
        for t in traits.splitlines():
            t = t.strip()
            if t:
                lines.append(f"\t\t\t\t{t}")
        lines.append("\t\t\t}")
    avail = (params or {}).get("available", "").strip()
    if avail:
        lines.append("\t\t\tavailable = {")
        for l in avail.splitlines():
            lines.append("\t\t\t\t" + l.strip())
        lines.append("\t\t\t}")
    factor = (params or {}).get("ai_will_do_factor", "").strip()
    if factor:
        lines.append("\t\t\tai_will_do = {")
        lines.append(f"\t\t\t\tfactor = {factor}")
        lines.append("\t\t\t}")
    lines.append("\t\t}")
    lines.append("\t}")
    lines.append("}")
    return "\n".join(lines)


def write_character_assign(filepath, char_name, excluded_tags, params, indent="\t"):
    """将角色的顾问分配写回指定文件（行级替换，保留注释与其他内容）。

    Args:
        filepath: 目标 advisors 文件路径
        char_name: 角色 ID
        excluded_tags: 排除国家列表
        params: 顾问参数 dict
        indent: 缩进单位（按原文件检测或默认 tab）
    Returns:
        bool: 成功 True；失败 False
    """
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            content = f.read()
    except Exception:
        content = ""
    newline = "\r\n" if "\r\n" in content else "\n"
    lines = content.splitlines()
    block = build_assign_block(char_name, excluded_tags, params)

    loc = find_character_block(lines, char_name)
    if loc is not None:
        start, end = loc
        lines = lines[:start] + block.split("\n") + lines[end + 1:]
    else:
        # 追加到文件末尾（保留原有结尾空行数）
        while lines and not lines[-1].strip():
            lines.pop()
        lines.extend(block.split("\n"))
    output = newline.join(lines).rstrip() + newline
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            f.write(output)
        return True
    except Exception:
        return False


def collect_advisor_files(mod_path="", game_path="") -> list:
    """收集顾问分配文件：mod 与游戏的 history/general/*advisors*.txt（存在才加入）。

    mod 已定义的国家，其游戏侧原版顾问分配文件不读取（见 country_filter）。
    """
    from country_filter import find_defined_countries, _file_country_tag
    defined = find_defined_countries(mod_path)
    result = []
    for base in (mod_path, game_path):
        if not base:
            continue
        d = os.path.join(base, "history", "general")
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(".txt") and "advis" in fn.lower():
                if base == game_path:
                    tag = _file_country_tag(fn)
                    if tag and tag in defined:
                        continue  # mod 已接管，屏蔽原版
                result.append(os.path.join(d, fn))
    return result


def load_character_assignments(mod_path="", game_path="") -> dict:
    """扫描所有顾问分配文件，构建 角色名 -> 分配信息 映射。

    Returns:
        {char_name: {"filepath": str, "excluded": [tag], "slot": str}}
    """
    result = {}
    for fp in collect_advisor_files(mod_path, game_path):
        try:
            with open(fp, "r", encoding="utf-8-sig", newline="") as f:
                lines = f.read().splitlines()
        except Exception:
            continue
        for start, end in parse_top_level_blocks(lines):
            text = block_text(lines, start, end)
            if "generate_character" not in text:
                continue
            # 提取角色名（name = X 或 token_base = X，剔除行内注释）
            char_name = ""
            for line in text.split("\n"):
                s = line.strip()
                if s.startswith("name =") or s.startswith("name="):
                    char_name = s.split("=", 1)[1].strip()
                    break
                if s.startswith("token_base =") or s.startswith("token_base="):
                    char_name = s.split("=", 1)[1].strip()
                    break
            if char_name and "#" in char_name:
                char_name = char_name.split("#", 1)[0].strip()
            if not char_name:
                continue
            # 提取该块的国家排除与 slot
            root = tree_from_pdx_text(text)
            block_node = None
            for child in root.children:
                if child.node_type == "block" and child.key in (
                        "every_possible_country", "every_other_country"):
                    block_node = child
                    break
            if block_node is None:
                continue
            limit = None
            for c in block_node.children:
                if c.key == "limit" and c.node_type == "block":
                    limit = c
                    break
            excluded = extract_excluded_tags(limit) if limit else []
            slot = ""
            for c in block_node.children:
                if c.key == "generate_character" and c.node_type == "block":
                    advisor = get_advisor_node(c)
                    if advisor:
                        for a in advisor.children:
                            if a.key == "slot":
                                slot = a.value
                                break
                    break
            result[char_name] = {"filepath": fp, "excluded": excluded, "slot": slot}
    return result


# ────────────── UI：角色顾问分配对话框（角色树编辑器入口） ──────────────

class CharacterAdvisorDialog(QDialog):
    """角色顾问分配编辑对话框 - 非模态

    在角色树编辑器中打开：编辑某角色"给哪些国家"（排除多选）与顾问参数，
    保存时写回对应的顾问分配文件（history/general/*advisors*.txt）。

    Attributes:
        char_name (str): 角色 ID
        advisor_file (str): 目标分配文件路径
        mod_path / game_path: 用于收集国家 tag 与扫描分配文件
    """

    saved = pyqtSignal()

    def __init__(self, char_name, advisor_file="", mod_path="", game_path="",
                 loc_manager=None, parent=None):
        super().__init__(parent)
        self.char_name = char_name
        self.advisor_file = advisor_file
        self.mod_path = mod_path
        self.game_path = game_path
        self.loc_manager = loc_manager
        self._country_tags = collect_country_tags(mod_path, game_path)

        self.setWindowTitle(f"顾问分配编辑 - {char_name}")
        self.setMinimumSize(560, 540)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._load_current()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info_row = QHBoxLayout()
        self.file_label = QLabel()
        self.file_label.setWordWrap(True)
        info_row.addWidget(self.file_label)
        info_row.addStretch()
        layout.addLayout(info_row)

        layout.addWidget(QLabel("排除国家（勾选后这些国家不获得该角色）:"))
        cond_row = QHBoxLayout()
        cond_row.addStretch()
        sel_all = QPushButton("全选")
        sel_all.clicked.connect(self._select_all)
        sel_none = QPushButton("清空")
        sel_none.clicked.connect(self._clear_all)
        cond_row.addWidget(sel_all)
        cond_row.addWidget(sel_none)
        layout.addLayout(cond_row)
        self.country_list = QListWidget()
        self.country_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for tag in self._country_tags:
            item = QListWidgetItem(self._country_label(tag))
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.country_list.addItem(item)
        layout.addWidget(self.country_list, 1)

        slot_row = QHBoxLayout()
        slot_row.addWidget(QLabel("顾问位 slot:"))
        self.slot_combo = QComboBox()
        self.slot_combo.setEditable(True)
        self.slot_combo.addItems(SLOT_CHOICES)
        slot_row.addWidget(self.slot_combo)
        slot_row.addWidget(QLabel("cost:"))
        self.cost_edit = QLineEdit()
        self.cost_edit.setPlaceholderText("如 100（可空）")
        self.cost_edit.setMaximumWidth(90)
        slot_row.addWidget(self.cost_edit)
        layout.addLayout(slot_row)

        layout.addWidget(QLabel("特质 traits（每行一个）:"))
        self.traits_edit = QTextEdit()
        self.traits_edit.setMaximumHeight(60)
        layout.addWidget(self.traits_edit)

        layout.addWidget(QLabel("available 条件（PDX 块文本，可空）:"))
        self.available_edit = QTextEdit()
        self.available_edit.setMaximumHeight(90)
        layout.addWidget(self.available_edit)

        factor_row = QHBoxLayout()
        factor_row.addWidget(QLabel("ai_will_do factor:"))
        self.factor_edit = QLineEdit()
        self.factor_edit.setPlaceholderText("如 1（可空）")
        factor_row.addWidget(self.factor_edit)
        factor_row.addStretch()
        layout.addLayout(factor_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        save_btn = QPushButton("💾 保存到分配文件")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

    def _country_label(self, tag):
        cn = ""
        if self.loc_manager is not None:
            try:
                cn = self.loc_manager.get_name(tag)
            except Exception:
                cn = ""
        return f"{tag}  {cn}" if cn else tag

    def _load_current(self):
        """加载当前角色在分配文件中的配置（排除国家与参数）。"""
        if self.advisor_file:
            self.file_label.setText(f"分配文件: {self.advisor_file}")
        else:
            self.file_label.setText("分配文件: （将新建到 mod 的 history/general/generic_advisors.txt）")
        try:
            with open(self.advisor_file, "r", encoding="utf-8-sig", newline="") as f:
                lines = f.read().splitlines()
        except Exception:
            lines = []
        loc = find_character_block(lines, self.char_name) if lines else None
        if loc is None:
            self.status_label.setText("该角色尚未配置顾问分配，保存后将新增条目。")
            return
        text = block_text(lines, *loc)
        root = tree_from_pdx_text(text)
        block_node = None
        for child in root.children:
            if child.node_type == "block" and child.key in (
                    "every_possible_country", "every_other_country"):
                block_node = child
                break
        if block_node is None:
            return
        limit = None
        for c in block_node.children:
            if c.key == "limit" and c.node_type == "block":
                limit = c
                break
        excluded = extract_excluded_tags(limit) if limit else []
        self._apply_exclusions(excluded)
        advisor = None
        for c in block_node.children:
            if c.key == "generate_character" and c.node_type == "block":
                advisor = get_advisor_node(c)
                break
        if advisor is not None:
            for a in advisor.children:
                if a.key == "slot":
                    self.slot_combo.setCurrentText(a.value)
                elif a.key == "cost":
                    self.cost_edit.setText(a.value)
                elif a.key == "traits" and a.node_type == "block":
                    self.traits_edit.setPlainText("\n".join(t.value for t in a.children))
                elif a.key == "available" and a.node_type == "block":
                    self.available_edit.setPlainText(a.to_pdx(0))
                elif a.key == "ai_will_do" and a.node_type == "block":
                    for sub in a.children:
                        if sub.key == "factor":
                            self.factor_edit.setText(sub.value)
        n = len(excluded)
        self.status_label.setText(f"已配置，当前排除 {n} 个国家。")

    def _apply_exclusions(self, tags):
        self.country_list.clearSelection()
        for i in range(self.country_list.count()):
            item = self.country_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in tags:
                item.setSelected(True)

    def _selected_exclusions(self):
        return [self.country_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.country_list.count())
                if self.country_list.item(i).isSelected()]

    def _select_all(self):
        for i in range(self.country_list.count()):
            self.country_list.item(i).setSelected(True)

    def _clear_all(self):
        self.country_list.clearSelection()

    def _on_save(self):
        """保存：写回目标分配文件。"""
        params = {
            "slot": self.slot_combo.currentText(),
            "cost": self.cost_edit.text(),
            "traits": self.traits_edit.toPlainText(),
            "available": self.available_edit.toPlainText(),
            "ai_will_do_factor": self.factor_edit.text(),
        }
        filepath = self.advisor_file
        if not filepath:
            # 默认写到 mod 的 generic_advisors.txt（不存在则创建）
            base = self.mod_path or self.game_path
            filepath = os.path.join(base, "history", "general", "generic_advisors.txt")
        ok = write_character_assign(filepath, self.char_name,
                                    self._selected_exclusions(), params)
        if ok:
            self.status_label.setText(f"已保存到: {filepath}")
            self.saved.emit()
            QMessageBox.information(self, "成功", f"已保存：\n{filepath}")
        else:
            QMessageBox.warning(self, "错误", "保存失败")

SLOT_CHOICES = [
    "political_advisor", "military_advisor", "navy_advisor",
    "army_advisor", "air_advisor", "high_command",
]


class AdvisorAssignDialog(QDialog):
    """顾问分配编辑对话框 - 非模态

    左侧：角色列表（当前块中的 generate_character）
    右侧：国家条件（排除国家多选 + limit 原文）与顾问参数（slot/traits/available/ai_will_do）

    保存时直接修改传入的树节点，并发出树变更信号。
    """

    tree_changed = pyqtSignal()

    def __init__(self, root_node, file_path="", mod_path="", game_path="",
                 loc_manager=None, parent=None):
        """Args:
            root_node (TreeNode): 树根节点（编辑后直接改此树）
            file_path: 当前编辑文件路径（用于判断块归属）
            mod_path: mod 目录（收集国家 tag）
            game_path: 游戏目录（收集国家 tag）
            loc_manager: 本地化管理器（显示国家中文名，可选）
        """
        super().__init__(parent)
        self.root_node = root_node
        self.mod_path = mod_path
        self.game_path = game_path
        self.loc_manager = loc_manager

        self.setWindowTitle("顾问分配编辑")
        self.setMinimumSize(760, 560)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._blocks = list(iter_assign_blocks(root_node))
        self._current_block = self._blocks[0] if self._blocks else None
        self._characters = (get_character_nodes(self._current_block)
                            if self._current_block else [])
        self._current_char = None
        self._country_tags = collect_country_tags(mod_path, game_path)

        self._setup_ui()
        self._load_blocks()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：块 + 角色列表 ──
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(QLabel("角色（generate_character）:"))
        self.char_list = QListWidget()
        self.char_list.currentItemChanged.connect(self._on_char_selected)
        left.addWidget(self.char_list)
        left_widget = QWidget()
        left_widget.setLayout(left)

        # ── 右侧：条件与参数 ──
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)

        self.summary_label = QLabel("未选择角色")
        self.summary_label.setWordWrap(True)
        right.addWidget(self.summary_label)

        # 国家条件
        cond_group = QWidget()
        cond_layout = QVBoxLayout(cond_group)
        cond_layout.setContentsMargins(0, 0, 0, 0)
        cond_row = QHBoxLayout()
        cond_row.addWidget(QLabel("排除国家（勾选后这些国家不获得该角色）:"))
        cond_row.addStretch()
        sel_all_btn = QPushButton("全选")
        sel_all_btn.clicked.connect(self._select_all_exclusions)
        sel_none_btn = QPushButton("清空")
        sel_none_btn.clicked.connect(self._clear_exclusions)
        cond_row.addWidget(sel_all_btn)
        cond_row.addWidget(sel_none_btn)
        cond_layout.addLayout(cond_row)
        self.country_list = QListWidget()
        self.country_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for tag in self._country_tags:
            item = QListWidgetItem(self._country_label(tag))
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.country_list.addItem(item)
        cond_layout.addWidget(self.country_list, 1)
        right.addWidget(cond_group, 3)

        # 顾问参数
        param_group = QWidget()
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(0, 0, 0, 0)
        slot_row = QHBoxLayout()
        slot_row.addWidget(QLabel("顾问位 slot:"))
        self.slot_combo = QComboBox()
        self.slot_combo.setEditable(True)
        self.slot_combo.addItems(SLOT_CHOICES)
        slot_row.addWidget(self.slot_combo)
        param_layout.addLayout(slot_row)

        traits_row = QHBoxLayout()
        traits_row.addWidget(QLabel("特质 traits（每行一个）:"))
        param_layout.addLayout(traits_row)
        self.traits_edit = QTextEdit()
        self.traits_edit.setMaximumHeight(60)
        param_layout.addWidget(self.traits_edit)

        avail_row = QHBoxLayout()
        avail_row.addWidget(QLabel("available 条件（PDX 块文本，可空）:"))
        param_layout.addLayout(avail_row)
        self.available_edit = QTextEdit()
        self.available_edit.setMaximumHeight(90)
        self.available_edit.setPlaceholderText("如:\nIF = {\n\tlimit = { has_dlc = \"Man the Guns\" }\n\tNOT = { has_autonomy_state = autonomy_supervised_state }\n}")
        param_layout.addWidget(self.available_edit)

        factor_row = QHBoxLayout()
        factor_row.addWidget(QLabel("ai_will_do factor:"))
        self.factor_edit = QLineEdit()
        self.factor_edit.setPlaceholderText("如 1")
        factor_row.addWidget(self.factor_edit)
        factor_row.addStretch()
        param_layout.addLayout(factor_row)
        right.addWidget(param_group, 2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        save_btn = QPushButton("保存（更新树）")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        right.addLayout(btn_row)

        right_widget = QWidget()
        right_widget.setLayout(right)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 520])
        layout.addWidget(splitter)

    # ────────────── 数据加载 ──────────────

    def _country_label(self, tag):
        """国家 tag 显示文本（含本地化中文名）。"""
        cn = ""
        if self.loc_manager is not None:
            try:
                cn = self.loc_manager.get_name(tag)
            except Exception:
                cn = ""
        return f"{tag}  {cn}" if cn else tag

    def _load_blocks(self):
        """加载当前块中的角色列表并选中第一个。"""
        self.char_list.blockSignals(True)
        self.char_list.clear()
        for char in self._characters:
            token = get_token_base(char)
            slot = ""
            advisor = get_advisor_node(char)
            if advisor:
                for c in advisor.children:
                    if c.key == "slot":
                        slot = c.value
                        break
            label = f"[{token or '?'}]"
            if slot:
                label += f"  {slot}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, char)
            self.char_list.addItem(item)
        self.char_list.blockSignals(False)
        if self.char_list.count():
            self.char_list.setCurrentRow(0)

    def _on_char_selected(self, current, previous):
        """切换角色时加载其条件与参数。"""
        if current is None:
            self._current_char = None
            return
        self._current_char = current.data(Qt.ItemDataRole.UserRole)
        block = self._current_block
        excluded = extract_excluded_tags(self._get_limit_node(block))
        self._load_exclusions(excluded)
        self._load_params(self._current_char)
        self.summary_label.setText("当前块：" + summarize_assign(block, excluded))

    def _get_limit_node(self, block_node):
        for c in block_node.children:
            if c.key == "limit" and c.node_type == "block":
                return c
        return None

    def _load_exclusions(self, tags):
        """按排除列表勾选国家。"""
        self.country_list.clearSelection()
        if not tags:
            return
        for i in range(self.country_list.count()):
            item = self.country_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in tags:
                self.country_list.itemWidget(item) if False else None
                item.setSelected(True)

    def _load_params(self, char_node):
        """加载角色的顾问参数。"""
        advisor = get_advisor_node(char_node)
        self.slot_combo.setCurrentText("")
        self.traits_edit.setPlainText("")
        self.available_edit.setPlainText("")
        self.factor_edit.setText("")
        if advisor is None:
            return
        for c in advisor.children:
            if c.key == "slot":
                self.slot_combo.setCurrentText(c.value)
            elif c.key == "traits" and c.node_type == "block":
                self.traits_edit.setPlainText("\n".join(t.value for t in c.children))
            elif c.key == "available" and c.node_type == "block":
                self.available_edit.setPlainText(c.to_pdx(0))
            elif c.key == "ai_will_do" and c.node_type == "block":
                for sub in c.children:
                    if sub.key == "factor":
                        self.factor_edit.setText(sub.value)

    # ────────────── 操作 ──────────────

    def _selected_exclusions(self) -> list:
        """收集当前勾选的排除国家。"""
        return [self.country_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.country_list.count())
                if self.country_list.item(i).isSelected()]

    def _select_all_exclusions(self):
        for i in range(self.country_list.count()):
            self.country_list.item(i).setSelected(True)

    def _clear_exclusions(self):
        self.country_list.clearSelection()

    def _on_save(self):
        """保存：更新当前块 limit 排除国家与角色参数。"""
        if self._current_block is None or self._current_char is None:
            QMessageBox.warning(self, "提示", "未选择角色")
            return

        # 1) 国家排除条件
        limit = self._get_limit_node(self._current_block)
        if limit is None:
            limit = TreeNode("block", "limit")
            self._current_block.add_child(limit, 0)
        rebuild_exclusions(limit, self._selected_exclusions())

        # 2) 顾问参数
        advisor = get_advisor_node(self._current_char)
        if advisor is None:
            advisor = TreeNode("block", "advisor")
            self._current_char.add_child(advisor)

        # slot
        self._set_value(advisor, "slot", self.slot_combo.currentText().strip())

        # traits
        trait_text = self.traits_edit.toPlainText().strip()
        old_traits = None
        for c in advisor.children:
            if c.key == "traits":
                old_traits = c
                break
        if trait_text:
            traits = TreeNode("block", "traits")
            for line in trait_text.splitlines():
                line = line.strip()
                if line:
                    traits.add_child(TreeNode("value", "", line))
            if old_traits is not None:
                advisor.children[advisor.children.index(old_traits)] = traits
            else:
                advisor.add_child(traits)
        elif old_traits is not None:
            advisor.children.remove(old_traits)

        # available（PDX 块文本）
        avail_text = self.available_edit.toPlainText().strip()
        old_avail = None
        for c in advisor.children:
            if c.key == "available":
                old_avail = c
                break
        if avail_text:
            from tree_node import parse_pdx_text_to_nodes
            nodes = parse_pdx_text_to_nodes(avail_text)
            if nodes:
                avail = nodes[0] if len(nodes) == 1 else TreeNode("block", "available")
                if avail.key != "available":
                    avail.key = "available"
                if old_avail is not None:
                    advisor.children[advisor.children.index(old_avail)] = avail
                else:
                    advisor.add_child(avail)
        elif old_avail is not None:
            advisor.children.remove(old_avail)

        # ai_will_do factor
        factor_text = self.factor_edit.text().strip()
        old_awd = None
        for c in advisor.children:
            if c.key == "ai_will_do":
                old_awd = c
                break
        if factor_text:
            awd = TreeNode("block", "ai_will_do")
            awd.add_child(TreeNode("value", "factor", factor_text))
            if old_awd is not None:
                advisor.children[advisor.children.index(old_awd)] = awd
            else:
                advisor.add_child(awd)
        elif old_awd is not None:
            advisor.children.remove(old_awd)

        self.summary_label.setText("当前块：" + summarize_assign(
            self._current_block, self._selected_exclusions()))
        self.tree_changed.emit()
        QMessageBox.information(self, "成功", "已更新树节点（在树编辑器中保存文件后生效）")

    @staticmethod
    def _set_value(parent: TreeNode, key: str, value: str):
        """设置或移除父节点下的值节点。"""
        old = None
        for c in parent.children:
            if c.key == key:
                old = c
                break
        if value:
            if old is not None:
                old.value = value
            else:
                parent.add_child(TreeNode("value", key, value))
        elif old is not None:
            parent.children.remove(old)
