"""算法层：编制/装备展示格式化纯函数（无 Qt 控件）。

四层分离规范见 PROJECT_DOC.md §1.4：
- 本模块只做数值/百分比/文本格式化；
- 不依赖 QWidget、QPainter、connect。
"""


def fmt_num(v, nd=1):
    """数值格式化：None → "—"；整数去小数；否则保留 nd 位。"""
    if v is None:
        return "—"
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%." + str(nd) + "f") % f


def fmt_pct(v, nd=1):
    """比例格式化（0.2 → "+20%"）：None → "—"。"""
    if v is None:
        return "—"
    p = v * 100.0
    sign = "+" if p > 0 else ""
    if abs(p - round(p)) < 1e-9:
        return "%s%d%%" % (sign, int(round(p)))
    return "%s%.*f%%" % (sign, nd, p)
