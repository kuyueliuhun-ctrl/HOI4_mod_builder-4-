"""国家选择/创建对话框 —— 无文件模式的国家流程入口

功能：
1. 从游戏目录（common/country_tags + common/countries）扫描已有国家，
   也列出 mod 中已定义/覆盖的国家。
2. 用户选择一个已有国家，或输入新 TAG + 名称创建一个新国家。
3. 列出该国家在原版中存在的相关内容目录（checkbox 多选）。
4. 选择操作模式：
   - 「复制原版到 mod」：把勾选目录的原版文件复制到 mod 同路径（同名覆盖）
   - 「同名空文件覆盖」：对勾选目录在 mod 中创建与原版同名的空文件（另起炉灶）
"""

import os
import re

import path_safety

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QMessageBox, QRadioButton, QButtonGroup,
    QCheckBox, QGroupBox, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt


# 该国家可能涉及的常见内容目录（相对游戏根目录）。按键对的形式给出（显示名, 相对目录）
# 只包含「国家专属」文件类型；多国共享的全局目录（如 common/national_focus 的单一大文件）
# 需按文件名匹配规则单独判断。
COUNTRY_DIR_CANDIDATES = [
    ("国家定义 common/countries", "common/countries"),
    ("国家标签 common/country_tags", "common/country_tags"),
    ("角色 common/characters", "common/characters"),
    ("民族精神 common/ideas", "common/ideas"),
    ("国策 common/national_focus", "common/national_focus"),
    ("事件 events", "events"),
    ("国家历史 history/countries", "history/countries"),
    ("初始部队 history/units", "history/units"),
    ("顾问分配 history/general", "history/general"),
    ("决策 common/decisions", "common/decisions"),
    ("AI战略 common/ai_strategy", "common/ai_strategy"),
    ("AI战略计划 common/ai_strategy_plans", "common/ai_strategy_plans"),
    ("AI师模板 common/ai_templates", "common/ai_templates"),
    ("MIO common/military_industrial_organization", "common/military_industrial_organization"),
    ("脚本触发 common/scripted_triggers", "common/scripted_triggers"),
    ("舰船命名 common/units/names_ships", "common/units/names_ships"),
    ("地块 history/states", "history/states"),
    ("科技 common/technologies", "common/technologies"),
    ("自治状态 common/autonomous_states", "common/autonomous_states"),
]

# 文件名匹配规则：用于在目录中挑出属于某国家的文件。
# 每种 (目录, 规则名)。规则名见 _file_matches。
COUNTRY_DIR_MATCHERS = {
    "common/countries": "exact_tag",
    "common/country_tags": "tag_assign",
    "common/characters": "tag_file",
    "common/ideas": "tag_lower",
    "common/national_focus": "tag_lower",
    "events": "event_name",
    "history/countries": "history_countries",
    "history/units": "tag_prefix",
    "history/general": "tag_prefix",
    "common/decisions": "tag_prefix",
    "common/ai_strategy": "tag_prefix",
    "common/ai_strategy_plans": "tag_prefix",
    "common/ai_templates": "tag_prefix",
    "common/military_industrial_organization": "tag_prefix",
    "common/scripted_triggers": "tag_prefix",
    "common/units/names_ships": "tag_prefix",
    "history/states": "state_files",
    "common/technologies": "tag_prefix",
    "common/autonomous_states": "tag_prefix",
}


def _country_tag_from_line(line):
    """从 `TAG = "xxx"` 行提取 TAG。"""
    m = re.match(r'^\s*([A-Z0-9]{2,4})\s*=\s*"', line, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def _looks_like_tag(name):
    """名称是否为合法国家 tag（2-4 位字母数字，至少含一个字母）。"""
    return bool(re.fullmatch(r"[A-Z0-9]{2,4}", name.upper())) and \
        any(c.isalpha() for c in name)


def scan_vanilla_countries(game_path):
    """扫描游戏目录中的国家列表。

    Returns:
        dict: {TAG: 国家文件相对路径或 ""}，来自 common/country_tags 赋值与 common/countries 文件名。
    """
    countries = {}
    if not game_path or not os.path.isdir(game_path):
        return countries

    # 1) common/country_tags/*.txt：TAG = "countries/xxx.txt"
    tags_dir = os.path.join(game_path, "common", "country_tags")
    if os.path.isdir(tags_dir):
        for fn in os.listdir(tags_dir):
            if not fn.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(tags_dir, fn), "r", encoding="utf-8-sig",
                          errors="ignore") as f:
                    for line in f:
                        tag = _country_tag_from_line(line)
                        m = re.search(r'=\s*"([^"]+)"', line)
                        if tag and m:
                            countries[tag] = m.group(1)
            except Exception:
                continue

    # 2) common/countries/*.txt：裸国家标签文件名
    cnt_dir = os.path.join(game_path, "common", "countries")
    if os.path.isdir(cnt_dir):
        for fn in os.listdir(cnt_dir):
            if not fn.lower().endswith(".txt"):
                continue
            stem = os.path.splitext(fn)[0]
            if _looks_like_tag(stem):
                countries.setdefault(stem.upper(), "countries/" + fn)

    return countries


def scan_mod_countries(mod_path):
    """扫描 mod 中已定义/覆盖的国家标签集合。"""
    tags = set()
    if not mod_path or not os.path.isdir(mod_path):
        return tags
    for sub in ("common/countries", "common/country_tags", "history/countries"):
        d = os.path.join(mod_path, sub.replace("/", os.sep))
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.lower().endswith(".txt"):
                continue
            stem = os.path.splitext(fn)[0]
            if sub == "common/countries":
                if _looks_like_tag(stem):
                    tags.add(stem.upper())
            elif sub == "common/country_tags":
                try:
                    with open(os.path.join(d, fn), "r", encoding="utf-8-sig",
                              errors="ignore") as f:
                        for line in f:
                            t = _country_tag_from_line(line)
                            if t:
                                tags.add(t)
                except Exception:
                    continue
            else:  # history/countries："CHL - Chile.txt" → CHL
                m = re.match(r"^([A-Z]{2,4})(?=[\s_\-])", stem)
                if m:
                    tags.add(m.group(1).upper())
    return tags


def _file_matches(rel, rule, tag, countries=None):
    """判断文件（相对路径）是否属于某国家。

    rel: 相对游戏根目录的路径（如 common/countries/Chile.txt）
    rule: 匹配规则名
    tag: 大写国家 tag
    countries: 国家 tag → 国家文件路径映射（供 tag_lower 等规则用）
    """
    base = os.path.basename(rel)
    stem = os.path.splitext(base)[0]

    if rule == "exact_tag":
        # common/countries：文件名为该 tag 对应的国家文件主干（如 Chile.txt ← CHL）
        ref = countries if countries is not None else _country_tags_ref()
        rel_cf = (ref.get(tag) or "").replace("\\", "/")
        if rel_cf:
            nm = os.path.splitext(os.path.basename(rel_cf))[0]
            if stem.lower() == nm.lower():
                return True
        # 兜底：裸 tag 文件名（无 country_tags 映射的国家）
        return _looks_like_tag(stem) and stem.upper() == tag
    if rule == "tag_assign":
        # country_tags：行内 TAG = "..."
        try:
            with open(rel, "r", encoding="utf-8-sig", errors="ignore") as f:
                for line in f:
                    if _country_tag_from_line(line) == tag:
                        return True
        except Exception:
            return False
        return False
    if rule == "history_countries":
        m = re.match(r"^([A-Z]{2,4})(?=[\s_\-])", stem)
        return bool(m and m.group(1).upper() == tag)
    if rule == "tag_file":
        # common/characters：TAG.txt 或 TAG_xxx.txt（大写 tag 前缀）
        return bool(re.match(r"^" + tag + r"(?=[_\-\.]|$)", stem))
    if rule == "tag_prefix":
        return bool(re.match(r"^" + tag + r"(?=[_\-\.(（]|$)", stem, re.IGNORECASE))
    if rule == "event_name":
        # 事件文件命名：`国家名.txt` / `DLC前缀_国家名.txt`（如 TOA_Chile、WTT_Germany、MTG_Britain）。
        # 取国家名别名集合（来自 country_tags 映射），判断文件主干（去 DLC 前缀后）是否等于国家名。
        ref = countries if countries is not None else _country_tags_ref()
        rel_cf = (ref.get(tag) or "").replace("\\", "/")
        if not rel_cf:
            return False
        nm = os.path.splitext(os.path.basename(rel_cf))[0].lower()
        # 去掉常见 DLC/共享前缀后对比（下划线分隔的首段或末段）
        parts = [p.lower() for p in stem.split("_")]
        if not parts:
            return False
        tail = parts[-1].lower()
        return tail == nm or stem.lower() == nm
    if rule == "tag_lower":
        # ideas/focus 等以国家名小写命名（chile.txt），需通过 country_tags 映射
        return stem.lower() in _tag_name_aliases(tag, countries)
    if rule == "state_files":
        # history/states：`数字-国家名.txt`。国家名来自 country_tags 映射的 countries/xxx.txt 主干。
        # 匹配规则：主干名去掉常见国家名停用词后出现在文件名中。
        ref = countries if countries is not None else _country_tags_ref()
        names = []
        for t, rel in ref.items():
            if t == tag and rel:
                nm = os.path.splitext(os.path.basename(rel.replace("\\", "/")))[0]
                if nm:
                    names.append(nm.lower())
        low = stem.lower()
        return any(nm and len(nm) >= 3 and nm in low for nm in names)
    return False


# 国家 tag → 可能的文件短名（小写）。用于 common/ideas、common/national_focus 等
# 以国家名命名的文件。主映射来自 country_tags 的 "countries/xxx.txt"。
_TAG_NAME_CACHE = {}


def _tag_name_aliases(tag, countries=None):
    """返回某 tag 可能的文件名主干（小写）别名集合。"""
    cache_key = tag + ("|" + str(id(countries or {})) if countries else "")
    if cache_key in _TAG_NAME_CACHE:
        return _TAG_NAME_CACHE[cache_key]
    aliases = {tag.lower()}
    ref = countries if countries is not None else _country_tags_ref()
    for t, rel in ref.items():
        if t == tag and rel:
            stem = os.path.splitext(os.path.basename(rel.replace("\\", "/")))[0]
            if stem:
                aliases.add(stem.lower())
    _TAG_NAME_CACHE[cache_key] = aliases
    if len(_TAG_NAME_CACHE) > 4096:
        for k in list(_TAG_NAME_CACHE)[:2048]:
            del _TAG_NAME_CACHE[k]
    return aliases


# 全局国家 tag → 国家文件路径映射（由 scan_vanilla_countries 填充，供名称匹配用）
_GLOBAL_COUNTRIES = {}


def _country_tags_ref():
    return _GLOBAL_COUNTRIES


def find_country_files(game_path, tag, countries=None):
    """列出游戏目录中属于某国家的文件。

    Args:
        game_path: 游戏根目录
        tag: 国家标签
        countries: 国家映射 {TAG: 国家文件路径}；不传则内部扫描
    Returns:
        dict: {相对目录: [文件绝对路径, ...]}
    """
    if not game_path or not os.path.isdir(game_path):
        return {}
    tag = tag.upper()
    if countries is None:
        countries = scan_vanilla_countries(game_path)
    found = {}
    for _label, rel_dir in COUNTRY_DIR_CANDIDATES:
        rule = COUNTRY_DIR_MATCHERS.get(rel_dir, "tag_prefix")
        d = os.path.join(game_path, rel_dir.replace("/", os.sep))
        if not os.path.isdir(d):
            continue
        hits = []
        for root, _dirs, names in os.walk(d):
            for fn in names:
                if not fn.lower().endswith(".txt"):
                    continue
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, game_path).replace("\\", "/")
                if _file_matches(rel, rule, tag, countries):
                    hits.append(fp)
        if hits:
            found.setdefault(rel_dir, []).extend(sorted(hits))
    return found


def copy_country_files(game_path, mod_path, tag, dirs, countries=None):
    """把游戏中原版某国家的勾选目录文件复制到 mod 同路径。

    Returns:
        list[str]: 复制成功的相对路径列表
    """
    if not game_path or not os.path.isdir(game_path) or not mod_path:
        return []
    copied = []
    files = find_country_files(game_path, tag, countries)
    for rel_dir in dirs:
        for fp in files.get(rel_dir, []):
            rel = os.path.relpath(fp, game_path).replace("\\", "/")
            dest = os.path.join(mod_path, rel.replace("/", os.sep))
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                # 复制并去除 BOM（游戏脚本要求 UTF-8 无 BOM）
                with open(fp, "rb") as src:
                    data = src.read()
                if data.startswith(b"\xef\xbb\xbf"):
                    data = data[3:]
                with open(dest, "wb") as out:
                    out.write(data)
                copied.append(rel)
            except Exception:
                continue
    return copied


def create_blank_overrides(mod_path, tag, dirs, game_path=None, countries=None):
    """对勾选目录创建同名空文件覆盖 mod 中原版文件名。

    每个目录取该目录下第一个匹配原版文件名为模板，在 mod 同路径创建空壳同名文件。
    若 mod 中已存在同名文件则保留（不覆盖已修改内容）。

    Returns:
        list[str]: 创建的相对路径列表
    """
    if not mod_path:
        return []
    created = []
    files = find_country_files(game_path, tag, countries) if game_path else {}
    for rel_dir in dirs:
        # 取该目录匹配的原版文件名；若无则跳过（无原版对应文件，无法“同名”）
        for fp in files.get(rel_dir, []):
            rel = os.path.relpath(fp, game_path).replace("\\", "/")
            dest = os.path.join(mod_path, rel.replace("/", os.sep))
            if os.path.exists(dest):
                continue
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                from write_utils import atomic_write_text
                atomic_write_text(dest, "", undo=False)
                created.append(rel)
            except Exception:
                continue
    return created


def create_new_country_files(mod_path, tag, dirs, game_path=None):
    """为新建国家创建基础设施文件（无原版对应文件时）。

    支持目录：
      - common/countries：创建 `<TAG>.txt` 空国家定义文件（若不存在）
      - common/country_tags：在 mod 的 country_tags 文件中追加 `TAG = "countries/<TAG>.txt"`
        若 mod 无 country_tags 文件则新建一个。

    Returns:
        list[str]: 创建/修改的相对路径列表
    """
    if not mod_path:
        return []
    tag = tag.upper()
    path_safety.validate_component(tag, "tag")
    created = []
    for rel_dir in dirs:
        if rel_dir == "common/countries":
            dest = os.path.join(mod_path, "common", "countries", f"{tag}.txt")
            if not os.path.exists(dest):
                try:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    from write_utils import atomic_write_text
                    atomic_write_text(dest, "", undo=False)
                    created.append(os.path.relpath(dest, mod_path).replace("\\", "/"))
                except Exception:
                    continue
        elif rel_dir == "common/country_tags":
            dest_dir = os.path.join(mod_path, "common", "country_tags")
            os.makedirs(dest_dir, exist_ok=True)
            target = None
            for fn in os.listdir(dest_dir):
                if fn.lower().endswith(".txt"):
                    target = os.path.join(dest_dir, fn)
                    break
            rel = f"common/country_tags/{os.path.basename(target) if target else 'countries.txt'}"
            try:
                from write_utils import atomic_write_text
                if target is None:
                    target = os.path.join(dest_dir, "countries.txt")
                    atomic_write_text(target, "", undo=False)
                # 追加等价实现：读旧内容 + 新行整体原子写
                old = ""
                try:
                    with open(target, "r", encoding="utf-8-sig", errors="ignore") as f:
                        old = f.read()
                except Exception:
                    old = ""
                atomic_write_text(target, old.rstrip() + "\n"
                                  + f'{tag} = "countries/{tag}.txt"\n',
                                  undo=False)
                created.append(rel)
            except Exception:
                continue
    return created


class CountrySetupDialog(QDialog):
    """国家选择/创建 + 内容目录勾选 + 操作模式。"""

    def __init__(self, game_path="", mod_path="", parent=None):
        super().__init__(parent)
        self.game_path = game_path
        self.mod_path = mod_path
        self.result_tag = ""
        self.selected_dirs = []
        self.mode = "copy"  # copy=复制原版 / blank=同名空文件覆盖

        self._countries = scan_vanilla_countries(game_path)
        self._mod_tags = scan_mod_countries(mod_path)
        global _GLOBAL_COUNTRIES
        _GLOBAL_COUNTRIES = dict(self._countries)

        self.setWindowTitle("国家设置")
        self.resize(640, 560)
        self._build_ui()
        self._populate_country_list("")

    # ---------- UI ----------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 国家区域
        country_group = QGroupBox("1. 选择或创建国家")
        c_layout = QVBoxLayout(country_group)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入国家名或 TAG 过滤…")
        self.search_edit.textChanged.connect(self._on_search)
        search_row.addWidget(self.search_edit)
        c_layout.addLayout(search_row)

        self.country_list = QListWidget()
        self.country_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection)
        self.country_list.itemSelectionChanged.connect(self._on_country_selected)
        c_layout.addWidget(self.country_list, 1)

        create_row = QHBoxLayout()
        create_row.addWidget(QLabel("创建新国家 TAG:"))
        self.new_tag_edit = QLineEdit()
        self.new_tag_edit.setPlaceholderText("如 CHL")
        self.new_tag_edit.setMaxLength(4)
        create_row.addWidget(self.new_tag_edit)
        self.create_btn = QPushButton("🆕 创建国家")
        self.create_btn.clicked.connect(self._on_create_country)
        create_row.addWidget(self.create_btn)
        c_layout.addLayout(create_row)
        layout.addWidget(country_group)

        # 操作模式
        mode_group = QGroupBox("2. 操作方式")
        m_layout = QVBoxLayout(mode_group)
        self.mode_copy = QRadioButton("📋 复制原版该国家内容到 mod 目录（基于原版修改）")
        self.mode_copy.setChecked(True)
        self.mode_blank = QRadioButton("🧹 另起炉灶：同名空文件覆盖原版内容")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_copy)
        self.mode_group.addButton(self.mode_blank)
        m_layout.addWidget(self.mode_copy)
        m_layout.addWidget(self.mode_blank)
        layout.addWidget(mode_group)

        # 内容目录勾选
        dir_group = QGroupBox("3. 选择内容目录（勾选要处理的目录）")
        dir_layout = QVBoxLayout(dir_group)
        hint = QLabel("提示：仅显示该国家在原版中存在内容的目录。")
        hint.setStyleSheet("color: #5d6b7a;")
        dir_layout.addWidget(hint)
        self.dir_list = QListWidget()
        self.dir_list.setSelectionMode(
            QListWidget.SelectionMode.NoSelection)
        dir_layout.addWidget(self.dir_list)
        self.check_all_btn = QPushButton("全选")
        self.check_all_btn.clicked.connect(lambda: self._set_all_checks(True))
        self.check_none_btn = QPushButton("全不选")
        self.check_none_btn.clicked.connect(lambda: self._set_all_checks(False))
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.check_all_btn)
        btn_row.addWidget(self.check_none_btn)
        btn_row.addStretch()
        dir_layout.addLayout(btn_row)
        layout.addWidget(dir_group)

        # 确认 / 取消
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.ok_btn = QPushButton("✅ 执行")
        self.ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.ok_btn)
        bottom_row.addWidget(cancel_btn)
        layout.addLayout(bottom_row)

        self._update_dir_list()

    # ---------- 国家列表 ----------

    def _populate_country_list(self, keyword):
        keyword = keyword.strip().lower()
        self.country_list.clear()
        mod_tags = self._mod_tags
        items = []
        for tag in sorted(self._countries):
            rel = self._countries.get(tag, "")
            name = os.path.splitext(os.path.basename(rel.replace("\\", "/")))[0] if rel else ""
            if keyword and keyword not in tag.lower() and keyword not in name.lower():
                continue
            marked = " [mod 已接管]" if tag in mod_tags else ""
            items.append((tag, name, marked))
        for tag, name, marked in items:
            text = f"{tag}  {name}{marked}"
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, tag)
            self.country_list.addItem(it)
        if self.country_list.count() == 0:
            it = QListWidgetItem("（无匹配国家）")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.country_list.addItem(it)

    def _on_search(self, text):
        self._populate_country_list(text)

    def _on_country_selected(self):
        items = self.country_list.selectedItems()
        if items and items[0].data(Qt.ItemDataRole.UserRole):
            tag = items[0].data(Qt.ItemDataRole.UserRole)
            self.result_tag = tag
            self.new_tag_edit.setText(tag)
            self._update_dir_list()

    def _on_create_country(self):
        tag = self.new_tag_edit.text().strip().upper()
        if not _looks_like_tag(tag):
            QMessageBox.warning(self, "错误", "请输入合法的国家 TAG（2-4 位字母/数字，含字母）")
            return
        self.result_tag = tag
        # 高亮/选中列表项（若有）
        for i in range(self.country_list.count()):
            it = self.country_list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == tag:
                self.country_list.setCurrentItem(it)
                break
        self._update_dir_list()

    # ---------- 目录勾选 ----------

    def _update_dir_list(self):
        """根据当前国家刷新目录列表（仅显示原版中存在内容的目录）。

        若该国家在原版中无任何内容（新创建国家），提供「国家基础设施」目录项
        （国家定义 common/countries + 国家标签 common/country_tags），
        便于另起炉灶从零搭建。
        """
        tag = self.result_tag
        self.dir_list.clear()
        if not tag:
            return
        files = find_country_files(self.game_path, tag) if self.game_path else {}
        has_any = False
        for label, rel_dir in COUNTRY_DIR_CANDIDATES:
            if rel_dir in files and files[rel_dir]:
                has_any = True
                n = len(files[rel_dir])
                cb = QCheckBox(f"{label}（{n} 个文件）")
                cb.setProperty("rel_dir", rel_dir)
                cb.setChecked(True)
                it = QListWidgetItem()
                it.setSizeHint(cb.sizeHint())
                self.dir_list.addItem(it)
                self.dir_list.setItemWidget(it, cb)
        if not has_any:
            # 新国家：提供国家基础设施文件创建
            known = self._countries if self._countries is not None else {}
            is_new = tag not in known and tag not in self._mod_tags
            if is_new:
                cb = QCheckBox("国家定义 common/countries（创建 TAG 文件）")
                cb.setProperty("rel_dir", "common/countries")
                cb.setChecked(True)
                it = QListWidgetItem()
                it.setSizeHint(cb.sizeHint())
                self.dir_list.addItem(it)
                self.dir_list.setItemWidget(it, cb)
                cb2 = QCheckBox("国家标签 common/country_tags（注册 TAG）")
                cb2.setProperty("rel_dir", "common/country_tags")
                cb2.setChecked(True)
                it2 = QListWidgetItem()
                it2.setSizeHint(cb2.sizeHint())
                self.dir_list.addItem(it2)
                self.dir_list.setItemWidget(it2, cb2)
            else:
                it = QListWidgetItem("（该国家在原版中无匹配目录）")
                it.setFlags(Qt.ItemFlag.NoItemFlags)
                self.dir_list.addItem(it)

    def _set_all_checks(self, checked):
        for i in range(self.dir_list.count()):
            w = self.dir_list.itemWidget(self.dir_list.item(i))
            if isinstance(w, QCheckBox):
                w.setChecked(checked)

    def _checked_dirs(self):
        dirs = []
        for i in range(self.dir_list.count()):
            w = self.dir_list.itemWidget(self.dir_list.item(i))
            if isinstance(w, QCheckBox) and w.isChecked():
                rd = w.property("rel_dir")
                if rd:
                    dirs.append(rd)
        return dirs

    # ---------- 执行 ----------

    def _on_ok(self):
        if not self.result_tag:
            QMessageBox.warning(self, "错误", "请先选择或创建国家")
            return
        dirs = self._checked_dirs()
        if not dirs:
            QMessageBox.warning(self, "错误", "请至少勾选一个内容目录")
            return
        if not self.mod_path:
            QMessageBox.warning(self, "错误", "尚未设置 mod 目录")
            return

        self.selected_dirs = dirs
        self.mode = "copy" if self.mode_copy.isChecked() else "blank"
        self.accept()

    def get_result(self):
        """返回 (tag, mode, dirs)。"""
        return self.result_tag, self.mode, list(self.selected_dirs)


def run_country_setup(game_path, mod_path, parent=None):
    """便捷入口：打开对话框并执行所选操作。

    Returns:
        (tag, mode, dirs) 或 None（取消）
    """
    dlg = CountrySetupDialog(game_path, mod_path, parent)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    tag, mode, dirs = dlg.get_result()
    return tag, mode, dirs
