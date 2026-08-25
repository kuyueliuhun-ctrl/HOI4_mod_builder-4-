"""算法/数据层：实体扫描/提取纯逻辑（无 Qt 控件）。

四层分离规范见 PROJECT_DOC.md §1.4：
- 本模块只做 PDX 文件扫描、实体提取、国家标签识别、块范围计算等纯逻辑；
- WorkbenchDock 保留同名薄包装（delegate），外部调用方无需改动。
"""

import os
import re

from content_types import ICON_RULES, TOP_LEVEL_ENTITY_TYPES


class EntityScanner:
    """实体扫描器：与 WorkbenchDock 原 classmethod 逻辑等价，供 UI 层委托。"""

    # 国家 tag：2-4 位大写字母/数字，至少含一个字母
    _TAG_RE = re.compile(r'(?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,4}')

    @classmethod
    def _collect_file_entities(cls, content_type, content, fp):
        """提取单个文件内的实体并附带 file/tags 信息（无文件模式与画廊重载复用）。"""
        file_tags = cls._detect_country_tags(fp, content)
        if content_type == "character":
            es = cls._extract_character_entities(content, file_tags)
            for e in es:
                e["tags"] = [e["tag"]] if e.get("tag") else []
        elif content_type == "country_history":
            # 国家设置：文件即实体（文件名前缀即国家）
            es = [{"name": os.path.splitext(os.path.basename(fp))[0], "key": "",
                   "icon": "", "range": (0, len(content))}]
        elif content_type in TOP_LEVEL_ENTITY_TYPES:
            # 顶层块即实体（如力量平衡/限时活动：`name = { ... }` 不做单包装块下沉）
            es = cls._extract_top_entities(content)
        elif content_type in ICON_RULES:
            es = cls._extract_entities(content_type, content)
            for e in es:
                e["icon"] = e.get("icon", "")
        else:
            es = cls._extract_generic_entities(content)
        for e in es:
            e["file"] = fp
            if not e.get("tags"):
                e["tags"] = list(file_tags)
            if not e.get("name"):
                e["name"] = os.path.splitext(os.path.basename(fp))[0]
        return es


    @classmethod
    def _extract_top_entities(cls, content):
        """顶层块即实体：不做「单包装块取直接子块」的下沉。"""
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return []
        md = min(s[1] for s in spans) if spans else 0
        return [cls._make_generic_entity(content, s[2], s[3], s[0])
                for s in spans if s[1] == md]


    @classmethod
    def _extract_character_entities(cls, content, file_tags):
        """角色文件实体提取：TAG 分组层下沉为角色实体。

        - characters = { TAG = { 角色ID = {...} } }：角色实体 tag=TAG
        - characters = { 角色ID = {...} }：角色实体 tag=文件级 tag
        """
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return []
        entities = []
        file_tag = file_tags[0] if file_tags else ""
        for key, bdepth, bpos, bend in spans:
            if key != "characters":
                continue
            children = [s for s in spans
                        if s[2] > bpos and s[3] <= bend and s[1] == bdepth + 1]
            for ckey, cd, cstart, cend in children:
                if cls._TAG_RE.fullmatch(ckey):
                    subs = [s for s in spans
                            if s[2] > cstart and s[3] <= cend and s[1] == cd + 1]
                    for skey, _d, sstart, send in subs:
                        entities.append({"name": skey, "key": skey, "icon": "",
                                         "range": (sstart, send), "tag": ckey})
                else:
                    entities.append({"name": ckey, "key": ckey, "icon": "",
                                     "range": (cstart, cend), "tag": file_tag})
        return entities


    @classmethod
    def _extract_generic_entities(cls, content):
        """通用实体提取：单顶层包装块取其直接子块；多顶层块时顶层块即实体；无块时整个文件视为一个实体。

        实体附带 icon/picture 字段探测（顶层字段中取 icon 或 picture），
        供全局图标索引渲染科技/占领法/建筑等类型的图标。
        """
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return []
        if not spans:
            return [{"name": "", "key": "", "icon": "",
                     "range": (0, len(content))}]
        md = min(s[1] for s in spans)
        tops = [s for s in spans if s[1] == md]
        entities = []
        if len(tops) == 1:
            key, bd, bpos, bend = tops[0]
            children = [s for s in spans
                        if s[2] > bpos and s[3] <= bend and s[1] == bd + 1]
            for c in children:
                entities.append(cls._make_generic_entity(content, c[2], c[3], c[0]))
        if not entities:
            for s in tops:
                entities.append(cls._make_generic_entity(content, s[2], s[3], s[0]))
        return entities


    @classmethod
    def _make_generic_entity(cls, content, start, end, key):
        """构造通用实体字典：提取顶层 icon/picture 字段作为图标值。"""
        import math
        if math.isinf(end):
            end = len(content)
        block = content[start:end]
        fields = cls._top_level_fields(block)
        icon = fields.get("icon") or fields.get("picture") or ""
        return {"name": key, "key": key, "icon": icon, "range": (start, end)}


    @classmethod
    def _quick_focus_scan(cls, content):
        """轻量国策扫描：快速提取绘制所需字段（id/x/y/icon/cost/relative/prerequisite）。

        无文件模式跨文件合并绘制国策树时使用（完整 parse_pdx_script 解析
        整文件过慢，60 文件需数十秒）；编辑仍走 parse_focus_file 精确定位。

        Returns:
            dict: {focus_id: node}，node 结构与 FocusProcessor.process 输出兼容
                （basic/draw/abs_x/abs_y/_abs_calculated）。
        """
        import math
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return {}
        result = {}
        n = len(content)

        def _fnum(v, default=0.0):
            try:
                return float(v)
            except Exception:
                return default

        for key, _depth, start, end in spans:
            if key not in ("focus", "shared_focus", "joint_focus"):
                continue
            if math.isinf(end):
                end = n
            block = content[start:end]
            fields = cls._top_level_fields(block)
            fid = fields.get("id") or ""
            if not fid:
                continue
            # prerequisite 引用：定位实体内的 prerequisite 块（括号配对），提取其中的 focus 值
            refs = []
            pm = re.search(r'\bprerequisite\s*=\s*\{', block)
            if pm:
                inner = block[pm.end():]
                depth = 1
                j = 0
                while j < len(inner) and depth > 0:
                    if inner[j] == '{':
                        depth += 1
                    elif inner[j] == '}':
                        depth -= 1
                    j += 1
                seg = inner[:max(j - 1, 0)]
                refs = re.findall(r'\bfocus\s*=\s*([\w\.\-]+)', seg)
            node = {
                'basic': {
                    'id': fid,
                    'icon': fields.get("icon", ""),
                    'x': _fnum(fields.get("x")),
                    'y': _fnum(fields.get("y")),
                    'cost': fields.get("cost", 10),
                    'ai_will_do': {},
                    'search_filters': {},
                },
                'draw': {
                    'relative_position_id': fields.get("relative_position_id") or None,
                    'prerequisite': refs,
                    'mutually_exclusive': [],
                },
                'conditions': {},
                'rewards': {},
                'abs_x': 0.0,
                'abs_y': 0.0,
                '_abs_calculated': False,
            }
            result[fid] = node
        return result

    # ---------- 科技扫描（科技树视图用） ----------


    @classmethod
    def _quick_tech_scan(cls, content):
        """轻量科技扫描：快速提取绘制科技树所需字段。

        科技文件结构：technologies = { tech_id = { ... } }。
        提取：folder（树归属 + 锚点网格坐标）、path 连线（leads_to_tech）、
        sub_technologies（子科技列表）、allow 获取方式标注、cost/start_year。

        Returns:
            dict: {tech_id: node}
        """
        import math
        try:
            spans = cls._block_spans(cls._scan_blocks(content))
        except Exception:
            return {}
        result = {}
        n = len(content)
        found_wrapper = False
        for key, _depth, start, end in spans:
            if key != "technologies":
                continue
            found_wrapper = True
            if math.isinf(end):
                end = n
            outer = content[start:end]
            try:
                inner = cls._block_spans(cls._scan_blocks(outer))
            except Exception:
                continue
            for tid, d2, s2, e2 in inner:
                # 只取包装块的直接子块（深度 1）；enable_equipments/allow 等
                # 科技内部子块深度 >= 2，会被跳过
                if d2 != 1:
                    continue
                if math.isinf(e2):
                    e2 = len(outer)
                node = cls._tech_node_from_block(tid, outer[s2:e2])
                if node:
                    result[tid] = node
        if not found_wrapper:
            # 无 technologies 包装的旧式文件：直接以顶层块作为科技
            for tid, bdepth, s2, e2 in spans:
                if bdepth != 0:
                    continue
                if math.isinf(e2):
                    e2 = n
                node = cls._tech_node_from_block(tid, content[s2:e2])
                if node:
                    result[tid] = node
        return result


    @staticmethod
    def _scan_blocks(text):
        """轻量扫描：返回所有 `key = {` 块的 (key, 深度, 起始位置) 列表。

        单遍正则扫描，同时跟踪括号深度；注释与引号内容已原地替换为空格
        （保持位置不变），避免误匹配且结果可直接索引原文本。
        深度为块自身所处的层级（顶层块为 0）。
        """
        import re
        clean = EntityScanner._blank_pdx(text)
        pattern = re.compile(r'(\{|\})|([\w\.\-]+)\s*=\s*\{')
        blocks = []
        depth = 0
        for m in pattern.finditer(clean):
            brace = m.group(1)
            if brace == "{":
                depth += 1
            elif brace == "}":
                depth -= 1
            else:
                blocks.append((m.group(2), depth, m.start()))
                depth += 1
        return blocks

    # ---------- 实体提取 ----------


    @staticmethod
    def _block_spans(blocks):
        """为 blocks 中每个 `key = {` 计算 (key, depth, start, end)。

        块结束位置 = 其后首个深度 <= 当前块深度的块位置；否则取到内容末尾。
        使用单调栈从右向左 O(n) 求解。
        """
        import math
        n = len(blocks)
        ends = [math.inf] * n
        stack = []
        for i in range(n - 1, -1, -1):
            depth = blocks[i][1]
            while stack and blocks[stack[-1]][1] > depth:
                stack.pop()
            if stack:
                ends[i] = blocks[stack[-1]][2]
            stack.append(i)
        return [(key, depth, start, ends[i]) for i, (key, depth, start) in enumerate(blocks)]


    @classmethod
    def _extract_entities(cls, content_type, content):
        """按图标配置提取实体列表。

        Returns:
            list[dict]: [{name, key, icon, range:(start,end)}, ...]
            非图标型类型或提取失败返回 []。
        """
        cfg = ICON_RULES.get(content_type)
        if not cfg:
            return []
        try:
            blocks = cls._scan_blocks(content)
            spans = cls._block_spans(blocks)
        except Exception:
            return []
        entities = []
        locate = cfg.get("locate")
        if not locate:
            return entities

        # locate 可为单个规则或规则列表（按顺序尝试，首个非空生效）
        rules = locate if isinstance(locate, list) and isinstance(locate[0], (tuple, list)) else [locate]
        for rule in rules:
            entities = cls._apply_locate_rule(rule, content, spans, cfg)
            if entities:
                break
        return entities


    @staticmethod
    def _top_level_fields(body):
        """返回实体块顶层（括号深度1）的 key=value 映射（首次出现的值）。

        使用词法 token 扫描，忽略嵌套块与注释，仅取块直接层级的键值对。
        """
        token_pattern = r'("[^"]*"|#.*|\{|\}|=|[\w\.\-]+)'
        toks = list(re.finditer(token_pattern, body))
        depth = 0
        fields = {}
        i = 0
        while i < len(toks):
            t = toks[i].group(0)
            if t == '{':
                depth += 1
                i += 1
                continue
            if t == '}':
                depth -= 1
                i += 1
                continue
            if t.startswith('#') or t == '=':
                i += 1
                continue
            if depth == 1 and i + 2 < len(toks):
                eq = toks[i + 1].group(0)
                val = toks[i + 2].group(0)
                if (eq == '=' and val not in ('=', '{', '}') and not val.startswith('#')
                        and t not in fields):
                    fields[t] = val.strip('"')
            i += 1
        return fields


    @staticmethod
    def _detect_country_tags(file_path, content):
        """检测文件关联的国家 tag，返回去重后的列表；无则返回空列表。

        检测来源（按优先级）：
          1. history/countries 文件名前缀（"A24 - Civil War.txt" → A24）
          2. common/countries 文件名为裸 tag（"14K.txt" → 14K）
          3. 文件名末尾大写标记（TFR_characters_A24.txt / TFR_ideas_APA.txt → A24/APA）
          4. common/country_tags 顶层 TAG = "..." 赋值（该文件夹专属）
          5. 内容模式：country = TAG / ideas = { TAG = {
        """
        import re
        rel = (file_path or "").replace("\\", "/")
        base = os.path.basename(file_path or "")
        stem = os.path.splitext(base)[0]
        # 国家 tag：2-4 位大写字母/数字，至少含一个字母
        tag = r'((?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,4})'

        # 1) history/countries / history/units：文件名前缀即 tag
        #    "A24 - Civil War.txt" → A24；"APA_2020.txt" → APA（取下划线/连字符前的首段）
        if "/history/countries/" in rel or "/history/units/" in rel:
            m = re.match(tag + r'\b', stem)
            if m:
                return [m.group(1)]
            first = re.split(r'[-_]', stem, maxsplit=1)[0]
            if re.fullmatch(tag, first):
                return [first]

        # 2) common/countries：文件名为裸 tag
        if "/common/countries/" in rel:
            m = re.fullmatch(tag, stem)
            if m:
                return [m.group(1)]

        # 3) 文件名末尾大写标记
        m = re.search(r'_' + tag + r'$', stem)
        if m:
            return [m.group(1)]

        # 3.5) 文件名前缀 tag（内容目录通用）：TAG_xxx / TAG(xxx) / TAG-xxx / 裸 TAG
        #      "ALS_ideas.txt" → ALS；"AFA(Ethiopia liberalism).txt" → AFA；"BDY_.txt" → BDY
        m = re.match(r'^' + tag + r'(?=[_\-\.(（]|$)', stem)
        if m:
            return [m.group(1)]

        if not content:
            return []

        tags = []
        # 4) country_tags：顶层 TAG = "..." 赋值
        if "/common/country_tags/" in rel:
            for m in re.finditer(r'^\s*' + tag + r'\s*=', content, re.M):
                tags.append(m.group(1))
            return tags
        # 5) 内容模式
        for m in re.finditer(r'\bcountry\s*=\s*' + tag + r'\b', content):
            tags.append(m.group(1))
        for m in re.finditer(r'\bideas\s*=\s*\{\s*' + tag + r'\s*=\s*\{', content):
            tags.append(m.group(1))

        seen = set()
        result = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result


    @staticmethod
    def _read_file(fp):
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    # ---------- 交互 ----------


    @staticmethod
    def _pair_block(content, brace_pos):
        """从 '{' 位置做括号配对，返回 (内部文本, 结束位置)。"""
        depth = 0
        i = brace_pos
        n = len(content)
        while i < n:
            c = content[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return content[brace_pos + 1:i], i
            i += 1
        return content[brace_pos + 1:], n


    @staticmethod
    def _tech_node_from_block(tid, block):
        """从单个科技块提取绘制科技树所需字段。"""
        fields = EntityScanner._top_level_fields(block)
        node = {
            "id": tid,
            "folder": "",
            "folder_x": None,
            "folder_y": None,
            "leads_to": [],
            "sub_techs": [],
            "allow_tags": [],
            "unresearchable": False,
            "cost": fields.get("research_cost") or fields.get("cost") or "",
            "start_year": fields.get("start_year") or "",
            "hidden": bool(fields.get("hidden")),
        }
        fm = re.search(r'\bfolder\s*=\s*\{', block)
        if fm:
            inner, _ = EntityScanner._pair_block(block, fm.end() - 1)
            nm = re.search(r'\bname\s*=\s*([\w\.\-]+)', inner)
            if nm:
                node["folder"] = nm.group(1)
            px = re.search(r'\bposition\s*=\s*\{[^}]*?\bx\s*=\s*(-?[\d\.]+)', inner)
            py = re.search(r'\bposition\s*=\s*\{[^}]*?\by\s*=\s*(-?[\d\.]+)', inner)
            if px:
                node["folder_x"] = float(px.group(1))
            if py:
                node["folder_y"] = float(py.group(1))
        for pm in re.finditer(r'\bpath\s*=\s*\{', block):
            inner, _ = EntityScanner._pair_block(block, pm.end() - 1)
            node["leads_to"].extend(
                re.findall(r'\bleads_to_tech\s*=\s*([\w\.\-]+)', inner))
        sm = re.search(r'\bsub_technologies\s*=\s*\{', block)
        if sm:
            inner, _ = EntityScanner._pair_block(block, sm.end() - 1)
            node["sub_techs"] = re.findall(r'[\w\.\-]+', inner)
        am = re.search(r'\ballow\s*=\s*\{', block)
        if am:
            inner, _ = EntityScanner._pair_block(block, am.end() - 1)
            compact = re.sub(r'\s+', ' ', inner)
            if re.search(r'\balways\s*=\s*no\b', compact):
                node["unresearchable"] = True
            for kw, label in (
                    ("has_completed_focus", "国策解锁"),
                    ("has_any_global_flag", "全局flag"),
                    ("has_any_country_flag", "国家flag"),
                    ("has_global_flag", "全局flag"),
                    ("has_country_flag", "国家flag"),
                    ("has_war", "战争条件"),
                    ("has_government", "政体条件"),
                    ("has_idea", "理念条件"),
                    ("has_trait", "特质条件"),
                    ("has_any_idea", "理念条件")):
                if re.search(r'\b' + kw + r'\b', compact) and label not in node["allow_tags"]:
                    node["allow_tags"].append(label)
        return node


    @classmethod
    def _apply_locate_rule(cls, rule, content, spans, cfg):
        """应用单条实体定位规则，返回实体列表。"""
        kind = rule[0]
        entities = []
        if kind == "keys":
            keys = set(rule[1])
            cand = [s for s in spans if s[0] in keys]
            kept = []
            for s in cand:
                # 跳过被已保留实体块包含的块（避免嵌套同名块重复计数）
                if any(o[2] <= s[2] and s[3] <= o[3] for o in kept):
                    continue
                kept.append(s)
            for key, _d, start, end in kept:
                entities.append(cls._make_entity(content, start, end, key, cfg))
        elif kind == "wrap":
            for wrap_key, depth_n in rule[1]:
                for key, bdepth, bpos, bend in spans:
                    if key != wrap_key:
                        continue
                    children = [s for s in spans
                                if s[2] > bpos and s[3] <= bend and s[1] == bdepth + depth_n]
                    for ckey, _cd, cstart, cend in children:
                        entities.append(cls._make_entity(content, cstart, cend, ckey, cfg))
        elif kind == "top_children":
            # 未包裹的文件（如 decisions 顶层直接为类别块）：实体 = 顶层块直接子块
            md = min(s[1] for s in spans) if spans else 0
            for key, bdepth, bpos, bend in spans:
                if bdepth != md:
                    continue
                children = [s for s in spans
                            if s[2] > bpos and s[3] <= bend and s[1] == bdepth + 1]
                for ckey, _cd, cstart, cend in children:
                    entities.append(cls._make_entity(content, cstart, cend, ckey, cfg))
        return entities


    @classmethod
    def _make_entity(cls, content, start, end, block_key, cfg):
        """从实体块范围构造实体信息字典。"""
        import math
        if math.isinf(end):
            end = len(content)
        block = content[start:end]
        fields = cls._top_level_fields(block)
        name = fields.get("id") or fields.get("name") or block_key

        field = cfg.get("field", "icon")
        if isinstance(field, (list, tuple)) or ">" in field:
            from icon_ops import get_entity_icon_field
            icon = get_entity_icon_field(content, start, end, field)
        else:
            icon = fields.get(field, "")
        return {"name": name, "key": block_key, "icon": icon, "range": (start, end)}

    # ---------- 文件扫描与列表刷新 ----------


    @staticmethod
    def _blank_pdx(text):
        """将注释与引号字符串原地替换为空格（保持字符位置不变）。

        用于 _scan_blocks 定位块范围时，保证扫描结果位置与原文一致。
        """
        chars = list(text)
        n = len(chars)
        in_str = False
        i = 0
        while i < n:
            c = chars[i]
            if in_str:
                if c == '"':
                    in_str = False
                chars[i] = ' '
                i += 1
                continue
            if c == '"':
                in_str = True
                chars[i] = ' '
                i += 1
                continue
            if c == '#':
                while i < n and chars[i] != '\n':
                    chars[i] = ' '
                    i += 1
                continue
            i += 1
        return ''.join(chars)

