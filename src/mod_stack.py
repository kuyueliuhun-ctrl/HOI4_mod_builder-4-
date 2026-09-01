"""Mod 层栈（ModStack）—— 子 mod 模式的读写路由底座。

概念模型（与 HOI4 加载语义对齐）：
  层栈 = [子mod(可写), 底层mod们(只读, 播放集顺序), 原版(只读)]
  - 读取：自上而下取第一个命中层（高层遮蔽低层 = 整文件覆盖语义）；
  - 写入：一律落 layers[0]（子 mod）；从低层打开的文件经 copy_up
    在子 mod 生成覆盖副本后再写；
  - 传统单 mod 模式 = 2 层栈 [mod, 原版] 的退化形式，旧调用方零改动。

接入点（唯一写路由汇聚处，调用方无感）：
  - state_build_ops.ensure_file_in_mod → mod_stack.route_existing
    （返回值语义与旧实现逐一对齐：(abs_path, copied)）。
  - ai_loader._scan_files / localization_mgr → scan_rel（合并视图）。

本模块无 PyQt 依赖；copy_up 用 shutil.copyfile（二进制安全，
写入纪律扫描归入「二进制」提示类，非违规）。
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

SUBMOD = "submod"
MOD = "mod"
VANILLA = "vanilla"


@dataclass
class ModLayer:
    """栈中的一层：一个 mod 内容目录（或原版根目录）。"""

    name: str                    # 显示名（descriptor name / "原版"）
    path: str                    # 内容目录绝对路径
    writable: bool = False       # 仅子 mod 层为 True
    kind: str = MOD              # "submod" | "mod" | "vanilla"


@dataclass
class ResolvedFile:
    """scan_rel 结果项：一个文件 + 来源层。"""

    rel_path: str                # posix 相对路径（"common/xxx/a.txt"）
    path: str                    # 绝对路径
    layer_index: int             # 所属层下标（0 = 子 mod）
    layer_name: str


_active_stack = None   # type: ModStack | None

# copy_up 确认钩子（用户策略：低层文件复制覆盖前弹窗确认）。
# None = 自动复制（默认；测试/算法层/无 UI 场景向后兼容）。
# 由 UI 层（main_window）注册：cb(rel_path, src_path, target_path) -> bool
_copy_up_confirm = None


def set_copy_up_confirm(cb):
    """注册 copy_up 确认回调（None = 恢复自动复制）。"""
    global _copy_up_confirm
    _copy_up_confirm = cb


def _confirm_copy_up(rel_path, src, target):
    if _copy_up_confirm is None:
        return True
    try:
        return bool(_copy_up_confirm(rel_path, src, target))
    except Exception:
        return False


class ModStack:
    """有序 mod 层：index 0 = 顶部（写层），越靠后优先级越低。"""

    def __init__(self, layers):
        self.layers = [l for l in (layers or [])
                       if l is not None and l.path and os.path.isdir(l.path)]

    def __len__(self):
        return len(self.layers)

    @property
    def submod_layer(self):
        for l in self.layers:
            if l.kind == SUBMOD and l.writable:
                return l
        return None

    @property
    def submod_path(self):
        layer = self.submod_layer
        return layer.path if layer else ""

    # ---------- 读取 ----------

    @staticmethod
    def _norm_rel(rel_path):
        """相对路径归一：'/' 按平台转 os.sep（Windows 下 common/a → common\\a）。

        scan_rel 输出恒为 posix 风格；resolve/write_target 入口统一归一，
        保证返回路径与 os.path.join(root, 'a', 'b') 逐字符一致。
        """
        return os.path.normpath(str(rel_path))

    def scan_rel(self, rel_dir, ext=".txt", include_shadowed=False):
        """合并视图扫描某相对目录。

        Args:
            rel_dir: 相对目录（"" = 根）。
            ext: 后缀过滤（大小写不敏感）；None/"" = 不过滤。
            include_shadowed: True 返回各层全部命中（冲突分析用，
              同 rel_path 多条目按 (rel_path, layer_index) 排序，高层在前）；
              False 只返回每个 rel_path 的最高层命中。

        Returns:
            list[ResolvedFile]，按 rel_path 大小写不敏感排序，稳定可测。
        """
        out = []
        seen = {}
        for idx, layer in enumerate(self.layers):
            d = os.path.join(layer.path, rel_dir) if rel_dir else layer.path
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                fp = os.path.join(d, name)
                if not os.path.isfile(fp):
                    continue
                if ext and not name.lower().endswith(str(ext).lower()):
                    continue
                rel = os.path.join(rel_dir, name) if rel_dir else name
                rel = rel.replace(os.sep, "/")
                rf = ResolvedFile(rel, fp, idx, layer.name)
                if include_shadowed:
                    out.append(rf)
                elif rel not in seen:
                    seen[rel] = rf
        if include_shadowed:
            out.sort(key=lambda r: (r.rel_path.lower(), r.layer_index))
            return out
        return sorted(seen.values(), key=lambda r: r.rel_path.lower())

    def resolve(self, rel_path):
        """顶层命中：返回绝对路径，无命中返回 None。"""
        rel = self._norm_rel(rel_path)
        for layer in self.layers:
            cand = os.path.join(layer.path, rel)
            if os.path.isfile(cand):
                return cand
        return None

    def resolve_all(self, rel_path):
        """各层命中（自上而下），用于层间差异/冲突展示。"""
        rel = self._norm_rel(rel_path)
        out = []
        for idx, layer in enumerate(self.layers):
            cand = os.path.join(layer.path, rel)
            if os.path.isfile(cand):
                out.append((idx, layer.name, cand))
        return out

    def layer_index_of(self, abs_path):
        """绝对路径所属层下标（含子目录归属）；不属于任何层返回 None。"""
        if not abs_path:
            return None
        real = os.path.realpath(abs_path)
        for idx, layer in enumerate(self.layers):
            root = os.path.realpath(layer.path)
            if real == root:
                return idx
            try:
                if os.path.commonpath([real, root]) == root:
                    return idx
            except ValueError:      # 跨盘符等不可比较情形
                continue
        return None

    def rel_path_of(self, abs_path):
        """绝对路径 → 相对某层的 posix 相对路径；不属于任何层返回 None。"""
        idx = self.layer_index_of(abs_path)
        if idx is None:
            return None
        root = os.path.realpath(self.layers[idx].path)
        real = os.path.realpath(abs_path)
        rel = os.path.relpath(real, root).replace(os.sep, "/")
        return rel

    # ---------- 写入 ----------

    def write_target(self, rel_path):
        """写入目标（恒为子 mod）。无可用写层抛 RuntimeError。"""
        if not self.layers or not self.layers[0].writable:
            raise RuntimeError("ModStack 无可写顶层（子 mod）")
        return os.path.join(self.layers[0].path, self._norm_rel(rel_path))

    def copy_up(self, rel_path):
        """从命中层复制覆盖副本到子 mod。

        已在子 mod 顶层时原样返回目标路径（不复制）；
        各层均无该文件返回 None；
        确认钩子（set_copy_up_confirm）拒绝时返回 None（不复制）。
        """
        target = self.write_target(rel_path)
        src = self.resolve(rel_path)
        if src is None:
            return None
        if os.path.realpath(src) == os.path.realpath(target):
            return target
        if not _confirm_copy_up(rel_path, src, target):
            return None
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        shutil.copyfile(src, target)
        return target

    def route_existing(self, rel_path):
        """与 state_build_ops.ensure_file_in_mod 返回值语义对齐的路由。

        Returns:
            (abs_path, copied)：abs_path 为调用方应编辑/保存的绝对路径；
            copied=True 表示本次刚从低层复制上来。
            确认钩子拒绝复制时返回 (None, False)——调用方按「文件缺失」
            自行中止，与旧实现缺失语义一致。
        """
        if not self.layers or not self.layers[0].writable:
            return None, False
        rel_path = str(rel_path)
        target = self.write_target(rel_path)
        if os.path.isfile(target):
            return target, False
        src = self.resolve(rel_path)
        if src is None:
            return None, False
        if not _confirm_copy_up(rel_path, src, target):
            return None, False
        try:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            shutil.copyfile(src, target)
            return target, True
        except Exception:
            return None, False


# ---------- 模块级激活上下文 ----------

def set_active_stack(stack):
    """激活全局层栈（None = 退出子 mod 模式，恢复传统两层语义）。"""
    global _active_stack
    if stack is not None:
        if not isinstance(stack, ModStack) or not stack.layers \
                or not stack.layers[0].writable:
            raise ValueError(
                "set_active_stack 需要 layers[0].writable 的 ModStack")
    _active_stack = stack


def active_stack():
    """当前激活层栈；未激活返回 None。"""
    return _active_stack


def clear_active_stack():
    set_active_stack(None)


def from_paths(sub_mod="", mod_paths=(), vanilla="", submod_name="") -> ModStack:
    """由路径列表构建层栈。子 mod 层可写，其余只读；无效目录自动丢弃。"""
    layers = []
    if sub_mod and os.path.isdir(sub_mod):
        layers.append(ModLayer(submod_name or os.path.basename(
            os.path.normpath(sub_mod)), sub_mod, True, SUBMOD))
    for p in mod_paths or ():
        if p and os.path.isdir(p):
            layers.append(ModLayer(os.path.basename(os.path.normpath(p)),
                                   p, False, MOD))
    if vanilla and os.path.isdir(vanilla):
        layers.append(ModLayer("原版", vanilla, False, VANILLA))
    return ModStack(layers)


# ---------- 传统两层语义（ensure_file_in_mod 的原始实现，保持逐字节等价） ----------

def route_existing(mod_path, hoi4_path, rel_path):
    """ensure_file_in_mod 的层栈感知入口。

    - 子 mod 模式激活：走 ModStack.route_existing（文件在子 mod → 直接用；
      在底层/原版 → 复制上来）；
    - 未激活：与旧实现完全一致（mod 内直接用，仅从原版复制）。

    Returns:
        (abs_path, copied)
    """
    st = _active_stack
    if st is not None:
        return st.route_existing(rel_path)
    return _legacy_route(mod_path, hoi4_path, rel_path)


def _legacy_route(mod_path, hoi4_path, rel_path):
    if not mod_path or not os.path.isdir(mod_path):
        return None, False
    mod_fp = os.path.join(mod_path, rel_path)
    if os.path.isfile(mod_fp):
        return mod_fp, False
    game_fp = None
    if hoi4_path:
        cand = os.path.join(hoi4_path, rel_path)
        if os.path.isfile(cand):
            game_fp = cand
    if game_fp is None:
        return None, False
    try:
        os.makedirs(os.path.dirname(mod_fp), exist_ok=True)
        shutil.copyfile(game_fp, mod_fp)
        return mod_fp, True
    except Exception:
        return None, False
