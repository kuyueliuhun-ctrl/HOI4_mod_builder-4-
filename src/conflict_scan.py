"""多 mod 冲突扫描（播放集级，纯算法层，无 PyQt）。

分级模型（与 HOI4 实际加载语义对齐，见 docs/多mod冲突检查与子mod制作_设计计划.md §0.2/§1.4）：
  L0 元信息：重复注册 / 缺失依赖 / 循环依赖 / 版本不匹配
  L1 文件遮蔽：同相对路径整文件覆盖（后者胜）+ replace_path 清空语义
  L2 实体 id：同域不同文件跨 mod 同 id（后者覆盖；events 为重复注册语义）
  L3 本地化键：同语言节内跨 mod 同 key（后者覆盖）

口径约定：
  - PlaysetMod.position 越大越晚加载、覆盖优先级越高（playset_loader 保序）；
  - L1 的「原版层」仅在 include_vanilla=True 时参与（原版被 mod 覆盖是正常
    modding 行为，默认不算冲突）；L2/L3 恒不扫原版；
  - 解析失败的文件按 PIT-PARSE-010 口径跳过并计数（skipped），不中断扫描；
  - 每类条目上限 MAX_ITEMS_PER_KIND，超出截断并在 detail 注明。

本模块零写入、零 Qt 依赖。
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

from unique_id_scanner import (
    _scan_dynamic_modifier,
    _scan_event,
    _scan_focus,
    _scan_focus_tree,
    _scan_character,
)

MAX_ITEMS_PER_KIND = 500
SHOW_PATHS_CAP = 12          # 单条目最多展示的位置数
SEV_ERROR = "error"
SEV_WARN = "warning"
SEV_INFO = "info"


@dataclass
class ConflictItem:
    """一条冲突记录。"""

    severity: str               # "error" | "warning" | "info"
    kind: str                   # 见 KIND_*
    title: str
    detail: str = ""
    victim: str = ""            # 被覆盖/受害 mod 名
    winner: str = ""            # 覆盖方/胜者 mod 名
    rel_path: str = ""
    entity_id: str = ""
    domain: str = ""            # 实体域 key（L2 用）
    locations: list = field(default_factory=list)   # ["mod名: 相对路径", …]

    def to_dict(self):
        return {
            "severity": self.severity, "kind": self.kind, "title": self.title,
            "detail": self.detail, "victim": self.victim,
            "winner": self.winner, "rel_path": self.rel_path,
            "entity_id": self.entity_id, "domain": self.domain,
            "locations": list(self.locations),
        }


@dataclass
class ConflictReport:
    """一次完整扫描的结果。"""

    playset_name: str = ""
    include_vanilla: bool = False
    duration_ms: int = 0
    scanned_files: int = 0
    skipped_files: int = 0
    items: list = field(default_factory=list)
    truncated_kinds: list = field(default_factory=list)

    def counts(self):
        """按严重度与类别计数：{"by_severity": {...}, "by_kind": {...}}。"""
        by_sev, by_kind = {}, {}
        for it in self.items:
            by_sev[it.severity] = by_sev.get(it.severity, 0) + 1
            by_kind[it.kind] = by_kind.get(it.kind, 0) + 1
        return {"by_severity": by_sev, "by_kind": by_kind}

    def to_dicts(self):
        return [it.to_dict() for it in self.items]


# ---------- 基础工具 ----------

def _walk_rel(root):
    """递归产出 (posix_rel_path, abs_path)，跳过 descriptor.mod；root 缺失不产出。"""
    if not root or not os.path.isdir(root):
        return
    stack = [""]
    while stack:
        rel_dir = stack.pop()
        d = os.path.join(root, rel_dir) if rel_dir else root
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            rel = (rel_dir + "/" + e.name) if rel_dir else e.name
            if e.is_dir(follow_symlinks=False):
                stack.append(rel)
            elif e.name.lower() != "descriptor.mod":
                yield rel, os.path.join(root, rel)


def game_version(hoi4_path):
    """从游戏根 launcher-settings.json 读版本号；失败返回 ""。"""
    if not hoi4_path:
        return ""
    fp = os.path.join(hoi4_path, "launcher-settings.json")
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return ""
    for key in ("rawVersion", "version"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _norm_version_prefix(v):
    """取版本 major.minor 前缀（"1.19.*" → "1.19"；解析失败 ""）。"""
    m = re.match(r"(\d+)\.(\d+)", (v or "").strip())
    return "%s.%s" % (m.group(1), m.group(2)) if m else ""


def _cap(kind_items, kind, truncated):
    if len(kind_items) > MAX_ITEMS_PER_KIND:
        truncated.append(kind)
        return kind_items[:MAX_ITEMS_PER_KIND]
    return kind_items


# ---------- L0 元信息 ----------

def scan_meta(playset, game_version_str=""):
    """L0：重复注册 / 缺失依赖 / 循环依赖 / 版本不匹配。"""
    items, truncated = [], []
    mods = list(playset.mods)

    # 重复注册：同 content_dir（realpath）或同 remote_file_id
    by_dir, by_remote = {}, {}
    for m in mods:
        if m.content_dir:
            key = os.path.realpath(m.content_dir)
            by_dir.setdefault(key, []).append(m)
        if m.remote_file_id:
            by_remote.setdefault(m.remote_file_id, []).append(m)
    kind_items = []
    for key, group in by_dir.items():
        if len(group) > 1:
            names = [g.name for g in group]
            kind_items.append(ConflictItem(
                severity=SEV_ERROR, kind="duplicate_mod",
                title="重复注册：%s" % " / ".join(names),
                detail="多个条目指向同一内容目录（互相覆盖，仅生效一次）",
                locations=["%s: %s" % (g.name, g.content_dir) for g in group]))
    for rid, group in by_remote.items():
        if len(group) > 1:
            kind_items.append(ConflictItem(
                severity=SEV_ERROR, kind="duplicate_mod",
                title="重复注册（同创意工坊 ID %s）" % rid,
                detail="remote_file_id 相同的条目只会加载一次",
                locations=["%s: %s" % (g.name, g.registry_path)
                           for g in group]))
    items.extend(_cap(kind_items, "duplicate_mod", truncated))

    # 缺失依赖（descriptor dependencies 按 name 匹配）
    names = {m.name for m in mods if m.name}
    kind_items = []
    for m in mods:
        missing = [d for d in m.dependencies if d and d not in names]
        if missing:
            kind_items.append(ConflictItem(
                severity=SEV_ERROR, kind="missing_dependency",
                title="%s 缺失依赖" % m.name,
                detail="声明依赖: %s" % "、".join(missing),
                victim=m.name,
                locations=["%s: %s" % (m.name, m.registry_path)]))
    items.extend(_cap(kind_items, "missing_dependency", truncated))

    # 循环依赖（仅在播放集内部名上的环；自环=依赖自己也算）
    graph = {m.name: [d for d in m.dependencies if d in names and d != m.name]
             for m in mods if m.name}
    for cyc in _find_cycles(graph):
        items.append(ConflictItem(
            severity=SEV_ERROR, kind="dependency_cycle",
            title="依赖环：%s" % " → ".join(cyc),
            detail="环上 mod 的依赖关系无法满足",
            locations=["%s: 依赖 %s" % (cyc[i], cyc[(i + 1) % len(cyc)])
                       for i in range(len(cyc))]))

    # 版本不匹配
    gv = _norm_version_prefix(game_version_str)
    if gv:
        kind_items = []
        for m in mods:
            mv = _norm_version_prefix(m.supported_version)
            if mv and mv != gv:
                kind_items.append(ConflictItem(
                    severity=SEV_WARN, kind="version_mismatch",
                    title="%s 版本不匹配" % m.name,
                    detail="supported_version=%s，游戏=%s"
                           % (m.supported_version, game_version_str),
                    victim=m.name))
        items.extend(_cap(kind_items, "version_mismatch", truncated))
    return items, truncated


def _find_cycles(graph):
    """有向图找全部基本环（Johnson 简化版：逐点 DFS，结果去重）。"""
    cycles, seen = [], set()
    def dfs(start, node, path, visited):
        for nxt in sorted(graph.get(node, ())):
            if nxt == start:
                cyc = path + [start]
                key = tuple(sorted(set(cyc)))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cyc + [start])
            elif nxt not in visited and len(path) < 12:
                dfs(start, nxt, path + [nxt], visited | {nxt})
    for start in sorted(graph):
        dfs(start, start, [start], {start})
    return cycles


# ---------- L1 文件遮蔽 / replace_path ----------

# 游戏实际加载的顶层内容目录。其余顶层文件/目录（thumbnail.png、
# .gitignore、README 等元数据）根本不会被游戏读取，不存在遮蔽语义。
LOADABLE_TOP_DIRS = frozenset({
    "common", "events", "history", "interface", "localisation", "map",
    "gfx", "sound", "music", "fonts", "tutorials",
})


def _loadable(rel):
    return rel.split("/", 1)[0] in LOADABLE_TOP_DIRS


def _covered(replace_path, rel):
    """rel 是否被 replace_path 声明覆盖（目录级前缀 / 单文件级全等）。"""
    r = replace_path.strip().strip('"').replace("\\", "/").rstrip("/")
    if not r:
        return False
    return rel == r or rel.startswith(r + "/")


def build_rel_map(mods, include_vanilla=False, hoi4_path="", progress=None):
    """一遍遍历所有层，构建 rel -> [(pos, name, rel)]（position 升序填入）。

    include_vanilla 时原版以 position=-1、name="原版" 作为最低层参与。
    Returns:
        (rel_map, scanned_files)
    """
    rel_map = {}
    scanned = 0
    layers = [(int(m.position), m.name, m.content_dir)
              for m in mods if m.content_dir and os.path.isdir(m.content_dir)]
    if include_vanilla and hoi4_path and os.path.isdir(hoi4_path):
        layers.append((-1, "原版", hoi4_path))
    for pos, name, root in sorted(layers, key=lambda l: l[0]):
        for rel, _fp in _walk_rel(root):
            if not _loadable(rel):
                continue
            rel_map.setdefault(rel, []).append((pos, name, rel))
            scanned += 1
        if progress:
            progress("L1 文件遍历: %s" % name, scanned, scanned + 1)
    return rel_map, scanned


def scan_file_layer(mods, include_vanilla=False, hoi4_path="", progress=None):
    """L1：整文件覆盖 + replace_path 清空（单遍构建 rel map 后双分析）。

    Returns:
        (shadow_items, replace_items, truncated, scanned_files)
    """
    rel_map, scanned = build_rel_map(mods, include_vanilla, hoi4_path,
                                     progress)
    truncated = []

    # --- 整文件覆盖 ---
    kind_items = []
    for rel, hits in rel_map.items():
        if len(hits) < 2:
            continue
        hits_sorted = sorted(hits, key=lambda h: h[0])
        winner = hits_sorted[-1][1]
        victim = hits_sorted[0][1]
        kind_items.append(ConflictItem(
            severity=SEV_WARN, kind="file_shadow",
            title=rel,
            detail="%s 覆盖 %s（同路径整文件只加载一份，靠后者胜）"
                   % (winner, victim),
            victim=victim, winner=winner, rel_path=rel,
            locations=["%s: %s" % (n2, rel) for _p, n2, _r in hits_sorted]))
    shadow_items = _cap(kind_items, "file_shadow", truncated)

    # --- replace_path ---
    replace_items = []
    declarations = []            # (pos, name, replace_path)
    for m in mods:
        for rp in (m.replace_paths or []):
            declarations.append((int(m.position), m.name, rp))
    if declarations:
        # 每个文件记录其全部属主（含原版层）
        rel_owner = {}
        for rel, hits in rel_map.items():
            rel_owner[rel] = [(h[0], h[1]) for h in hits]
        grouped = {}
        for pos, name, rp in declarations:
            for rel, owners in rel_owner.items():
                if not _covered(rp, rel):
                    continue
                covering = [d for d in declarations if _covered(d[2], rel)]
                if not covering:
                    continue
                winner = max(covering, key=lambda d: d[0])[1]
                for vpos, vname in owners:
                    if vname == winner:
                        continue   # 胜者自己的文件（或同为覆盖声明者）不受影响
                    grouped.setdefault((vname, rp, winner), []).append(rel)
            if progress:
                progress("L1 replace_path", len(grouped),
                         max(len(grouped), 1))
        kind_items = []
        for (vname, rp, winner), rels in sorted(grouped.items()):
            rels = sorted(set(rels))
            shown = rels[:SHOW_PATHS_CAP]
            more = len(rels) - len(shown)
            kind_items.append(ConflictItem(
                severity=SEV_ERROR, kind="replaced_by_replace_path",
                title="%s 清空 %s（replace_path=%s，%d 个文件失效）"
                      % (winner, vname, rp, len(rels)),
                detail="；".join(shown)
                       + ("（另有 %d 个…）" % more if more > 0 else ""),
                victim=vname, winner=winner, rel_path=rp,
                locations=["%s: %s" % (vname, r) for r in shown]))
        replace_items = _cap(kind_items, "replaced_by_replace_path", truncated)
    return shadow_items, replace_items, truncated, scanned


# ---------- L2 实体 id ----------

def _scan_ideas(text):
    """idea id = ideas = { TAG = { <idea> = {…} } } 的深度 2 块键。"""
    from tree_node import parse_pdx_text_to_nodes
    try:
        nodes = parse_pdx_text_to_nodes(text)
    except Exception:
        return []
    out = []
    for top in nodes:
        if top.node_type == "block" and top.key == "ideas":
            for country in top.children:
                if country.node_type != "block":
                    continue
                out.extend(c.key for c in country.children
                           if c.node_type == "block")
    return out


# 决议块内嵌属性键（不是决议 id）——unique_id_scanner._scan_decision 的
# 「少量嵌套块误报」在单 mod 口径可接受，在播放集口径会全量误报，故过滤。
_DECISION_PROP_KEYS = frozenset({
    "available", "visible", "ai_will_do", "complete_effect",
    "remove_effect", "cancel_effect", "activation", "cost",
    "days_re_enable", "days_mission_timeout", "timeout_effect",
    "modifiers", "icon", "picture", "name", "desc", "is_good",
    "highlight", "custom_icon", "selectable_mission",
    "targeted_modifier", "allowed", "fire_only_once",
    "cancel_if_not_visible", "modifier", "targets", "state_target",
})

_DECISION_PROP_TOP = frozenset({
    "available", "visible", "allowed", "icon", "picture", "name",
    "modifier", "ai_will_do", "cancel_if_not_visible",
})


def _scan_decision_ids(text):
    """播放集口径的决议 id：`容器.决议` 复合键。

    HOI4 决议文件结构：容器/分类块（深度1）→ 决议块（深度2）。
    游戏按 容器+决议 id 合并，跨 mod 同容器同名决议才是真冲突；
    同容器名本身是正常合并行为，不报告。深度2 的属性块
    （available/ai_will_do 等）由 _DECISION_PROP_KEYS 排除。
    """
    from tree_node import parse_pdx_text_to_nodes
    try:
        nodes = parse_pdx_text_to_nodes(text)
    except Exception:
        return []
    out = []
    for top in nodes:
        if top.node_type != "block":
            continue
        container = top.key
        for child in top.children:
            if child.node_type != "block":
                continue
            if child.key in _DECISION_PROP_TOP and not child.children:
                continue
            if child.key in _DECISION_PROP_KEYS:
                continue
            out.append("%s.%s" % (container, child.key))
    return out


def _scan_technologies(text):
    """technology id = technologies = { <tech> = {…} } 的深度 1 块键。"""
    from tree_node import parse_pdx_text_to_nodes
    try:
        nodes = parse_pdx_text_to_nodes(text)
    except Exception:
        return []
    out = []
    for top in nodes:
        if top.node_type == "block" and top.key == "technologies":
            out.extend(c.key for c in top.children if c.node_type == "block")
    return out


# 域配置：key → (相对目录们, 提取器, 语义)
#   semantic: "override" = 后者覆盖前者（error）；"duplicate" = 重复注册（warning）
DOMAINS = [
    ("focus", ("common/national_focus",), _scan_focus, "override"),
    ("focus_tree", ("common/national_focus",), _scan_focus_tree, "override"),
    ("idea", ("common/ideas",), _scan_ideas, "override"),
    ("technology", ("common/technologies",), _scan_technologies, "override"),
    ("character", ("common/characters",), _scan_character, "override"),
    ("decision", ("common/decisions",), _scan_decision_ids, "override"),
    ("event", ("events",), _scan_event, "duplicate"),
    ("dynamic_modifier", ("common/dynamic_modifiers",),
     _scan_dynamic_modifier, "override"),
]

_TXT_RE = re.compile(r"\.txt$", re.I)


def scan_entity_ids(mods, domains=None, progress=None):
    """L2：跨 mod 同域同 id（不同文件）冲突。

    Returns:
        (items, truncated, scanned_files, skipped_files)
    """
    domains = domains or DOMAINS
    items, truncated = [], []
    scanned = skipped = 0
    # id 表：domain -> id -> {(rel_path): (pos, name)}
    tables = {d[0]: {} for d in domains}
    for m in sorted(mods, key=lambda x: int(x.position)):
        if not m.content_dir or not os.path.isdir(m.content_dir):
            continue
        pos, name = int(m.position), m.name
        for dkey, dirs, extractor, _sem in domains:
            for rel_dir in dirs:
                base = os.path.join(m.content_dir, rel_dir)
                if not os.path.isdir(base):
                    continue
                for rel, fp in _walk_rel(base):
                    if not _TXT_RE.search(rel):
                        continue
                    rel_key = (rel_dir + "/" + rel).replace(os.sep, "/")
                    scanned += 1
                    try:
                        with open(fp, "r", encoding="utf-8-sig",
                                  errors="replace") as f:
                            text = f.read()
                    except OSError:
                        skipped += 1
                        continue
                    ids = []
                    try:
                        ids = extractor(text)
                    except Exception:
                        skipped += 1
                    for ident in ids:
                        if not ident:
                            continue
                        tables[dkey].setdefault(str(ident), {})[rel_key] = \
                            (pos, name)
                if progress:
                    progress("L2 实体 id:%s" % dkey, scanned, scanned + 1)

    for dkey, dirs, _ex, sem in domains:
        table = tables[dkey]
        kind_items = []
        for ident, by_rel in table.items():
            mods_hit = {(rel, hit) for rel, hit in by_rel.items()}
            distinct_mods = {hit[1] for hit in mods_hit}
            if len(distinct_mods) < 2:
                continue
            # 同 rel_path 已由 L1 报告（整文件遮蔽），此处只看跨文件
            if len({rel for rel, _h in mods_hit}) < 2:
                continue
            ordered = sorted(mods_hit, key=lambda rh: rh[1][0])
            victim = ordered[0][1][1]
            winner = ordered[-1][1][1]
            sev = SEV_WARN if sem == "duplicate" else SEV_ERROR
            kind_items.append(ConflictItem(
                severity=sev, kind="entity_id", domain=dkey,
                entity_id=ident,
                title="%s：同 id 定义于 %d 个 mod 的不同文件"
                      % (ident, len(distinct_mods)),
                detail="加载顺序靠后者生效" if sem == "override"
                       else "重复注册：两个定义都会加载（后者先生效）",
                victim=victim, winner=winner,
                locations=["%s: %s" % (hit[1], rel)
                           for rel, hit in ordered[:SHOW_PATHS_CAP]]))
        items.extend(_cap(kind_items, "entity_id:" + dkey, truncated))
    return items, truncated, scanned, skipped


# ---------- L3 本地化键 ----------

_LOC_KEY_RE = re.compile(
    r'^\s*([a-zA-Z0-9_.\-]+)\s*:\s*(?:\d+\s*)?"')


def scan_loc_keys(mods, progress=None):
    """L3：同语言节内跨 mod 同 key。

    Returns:
        (items, truncated, scanned_files)
    """
    items, truncated, scanned = [], [], 0
    # (lang, key) -> {rel: (pos, name)}
    table = {}
    for m in sorted(mods, key=lambda x: int(x.position)):
        if not m.content_dir or not os.path.isdir(m.content_dir):
            continue
        loc_root = os.path.join(m.content_dir, "localisation")
        if not os.path.isdir(loc_root):
            continue
        for lang in sorted(os.listdir(loc_root)):
            lang_dir = os.path.join(loc_root, lang)
            if not os.path.isdir(lang_dir):
                continue
            for fn in sorted(os.listdir(lang_dir)):
                if not fn.lower().endswith(".yml"):
                    continue
                scanned += 1
                try:
                    with open(os.path.join(lang_dir, fn), "r",
                              encoding="utf-8-sig", errors="replace") as f:
                        for line in f:
                            mt = _LOC_KEY_RE.match(line)
                            if mt and not line.lstrip().startswith("#"):
                                table.setdefault((lang, mt.group(1)),
                                                 {})[fn] = \
                                    (int(m.position), m.name)
                except OSError:
                    continue
        if progress:
            progress("L3 本地化", scanned, scanned + 1)

    kind_items = []
    for (lang, key), by_rel in sorted(table.items(),
                                      key=lambda kv: (kv[0][0], kv[0][1])):
        distinct_mods = {hit[1] for hit in by_rel.values()}
        if len(distinct_mods) < 2:
            continue
        ordered = sorted(by_rel.items(), key=lambda kv: kv[1][0])
        kind_items.append(ConflictItem(
            severity=SEV_WARN, kind="loc_key",
            title="%s（%s）：同 key 多个翻译" % (key, lang),
            detail="加载顺序靠后的 mod 覆盖前面的翻译",
            victim=ordered[0][1][1], winner=ordered[-1][1][1],
            locations=["%s: localisation/%s/%s"
                       % (hit[1], lang, fn)
                       for fn, hit in ordered[:SHOW_PATHS_CAP]]))
    items.extend(_cap(kind_items, "loc_key", truncated))
    return items, truncated, scanned


# ---------- 汇总入口 ----------

def scan_conflicts(playset, hoi4_path="", include_vanilla=False,
                   scan_entities=True, scan_loc=True, progress=None):
    """完整冲突扫描。

    Args:
        playset: playset_loader.Playset
        hoi4_path: 游戏根目录（版本比对；include_vanilla 时参与 L1）
        include_vanilla: L1 是否纳入原版层
        scan_entities / scan_loc: L2 / L3 开关
        progress: 可选回调 progress(stage, done, total)

    Returns:
        ConflictReport
    """
    t0 = time.perf_counter()
    report = ConflictReport(playset_name=playset.name,
                            include_vanilla=include_vanilla)
    mods = list(playset.mods)
    _add = report.items.extend

    items, tr = scan_meta(playset, game_version(hoi4_path))
    _add(items)
    report.truncated_kinds.extend(tr)

    shadow_items, replace_items, tr, scanned = scan_file_layer(
        mods, include_vanilla=include_vanilla, hoi4_path=hoi4_path,
        progress=progress)
    report.scanned_files += scanned
    _add(shadow_items)
    _add(replace_items)
    report.truncated_kinds.extend(tr)

    if scan_entities:
        items, tr, scanned, skipped = scan_entity_ids(mods, progress=progress)
        report.scanned_files += scanned
        report.skipped_files += skipped
        _add(items)
        report.truncated_kinds.extend(tr)

    if scan_loc:
        items, tr, scanned = scan_loc_keys(mods, progress=progress)
        report.scanned_files += scanned
        _add(items)
        report.truncated_kinds.extend(tr)

    report.duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
    return report
