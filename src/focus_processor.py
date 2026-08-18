class FocusProcessor:
    """
    国策数据处理器。
    负责将 pdx_parser 解析出的原始字典数据提取为结构化的 focus_data，
    并递归计算每个国策在画布上的绝对像素坐标。
    """

    def __init__(self):
        self.focus_data = {}
        self.GRID_X = 90
        self.GRID_Y = 130

    def process(self, raw_data):
        """
        全面提取国策数据，兼容 shared_focus 和列表嵌套格式。
        raw_data: pdx_parser.parse_pdx_script() 返回的嵌套字典
        返回: {focus_id: {basic, draw, conditions, rewards, abs_x, abs_y, ...}, ...}
        """
        self.focus_data = {}
        all_focuses = []

        focus_trees = raw_data.get('focus_tree', [])
        if isinstance(focus_trees, dict):
            focus_trees = [focus_trees]

        for tree in focus_trees:
            focuses = tree.get('focus', [])
            if isinstance(focuses, dict):
                focuses = [focuses]
            all_focuses.extend(focuses)

        shared = raw_data.get('shared_focus', [])
        if isinstance(shared, dict):
            shared = [shared]
        all_focuses.extend(shared)

        for f in all_focuses:
            fid = f.get('id', 'unknown_focus')
            if isinstance(fid, list):
                fid = fid[0]

            x_val = f.get('x', 0)
            y_val = f.get('y', 0)
            if isinstance(x_val, list):
                x_val = float(x_val[0])
            else:
                x_val = float(x_val)

            if isinstance(y_val, list):
                y_val = float(y_val[0])
            else:
                y_val = float(y_val)

            icon_val = f.get('icon', '')
            if isinstance(icon_val, list):
                icon_val = icon_val[0]

            rel_id = f.get('relative_position_id', None)
            if isinstance(rel_id, list):
                rel_id = rel_id[0]

            node = {
                'basic': {
                    'id': fid,
                    'icon': icon_val,
                    'x': x_val,
                    'y': y_val,
                    'cost': f.get('cost', 10),
                    'ai_will_do': f.get('ai_will_do', {}),
                    'search_filters': f.get('search_filters', {})
                },
                'draw': {
                    'relative_position_id': rel_id,
                    'prerequisite': self._extract_refs(f.get('prerequisite', [])),
                    'mutually_exclusive': self._extract_refs(f.get('mutually_exclusive', []))
                },
                'conditions': {
                    'available': f.get('available', {}),
                    'bypass': f.get('bypass', {})
                },
                'rewards': {
                    'completion_reward': f.get('completion_reward', {}),
                    'hidden_effect': f.get('completion_reward', {}).get('hidden_effect', {})
                },
                'abs_x': 0.0,
                'abs_y': 0.0,
                '_abs_calculated': False
            }

            for category in node.values():
                if isinstance(category, dict) and category is not node['draw']:
                    keys_to_del = [k for k, v in category.items() if not v and v != 0]
                    for k in keys_to_del:
                        del category[k]

            self.focus_data[fid] = node

        self._calculate_absolute_positions()
        return self.focus_data

    def _extract_refs(self, ref_data):
        """从 prerequisite/mutually_exclusive 数据中提取所有引用的 focus ID 列表"""
        refs = []
        if not isinstance(ref_data, list):
            ref_data = [ref_data]

        for item in ref_data:
            if isinstance(item, dict) and 'focus' in item:
                focus_val = item['focus']
                if isinstance(focus_val, list):
                    refs.extend(focus_val)
                elif isinstance(focus_val, str):
                    refs.append(focus_val)
        return refs

    def _calculate_absolute_positions(self):
        """将国策坐标转换为像素坐标。

        HOI4 焦点定位语义：
        - 无 relative_position_id 的焦点：x/y 为绝对网格坐标（缺省 0）
        - 有 relative_position_id 的焦点：x/y 为相对其引用焦点的偏移，
          引用焦点自身也可能带 relative_position_id，需沿链递归解析
        - 引用目标不存在或引用成环时，退化为绝对坐标处理
        """
        grid = {}
        pending = dict(self.focus_data)
        while pending:
            progress = False
            for fid in list(pending):
                node = pending[fid]
                rel = node['draw'].get('relative_position_id')
                dx, dy = node['basic']['x'], node['basic']['y']
                if not rel:
                    grid[fid] = (dx, dy)
                    del pending[fid]
                    progress = True
                elif rel in grid:
                    px, py = grid[rel]
                    grid[fid] = (px + dx, py + dy)
                    del pending[fid]
                    progress = True
                elif rel not in self.focus_data:
                    grid[fid] = (dx, dy)
                    del pending[fid]
                    progress = True
            if not progress:
                for fid, node in pending.items():
                    grid[fid] = (node['basic']['x'], node['basic']['y'])
                break
        for fid, node in self.focus_data.items():
            gx, gy = grid.get(fid, (node['basic']['x'], node['basic']['y']))
            node['abs_x'] = (gx + 0.5) * self.GRID_X
            node['abs_y'] = (gy + 0.5) * self.GRID_Y