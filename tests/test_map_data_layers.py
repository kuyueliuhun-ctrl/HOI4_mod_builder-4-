"""地图数据层色阶测试（P2 ③）。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def _mkdtemp(prefix):
    root = os.path.join(PROJECT_ROOT, ".runtime", "test_tmp")
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


class RampColorsTest(unittest.TestCase):
    def test_low_blue_high_red(self):
        from map_data_layers import ramp_colors

        c = ramp_colors(np.array([0.0, 0.5, 1.0]))
        self.assertGreater(c[0, 2], c[0, 0])      # 低值偏蓝
        self.assertGreater(c[2, 0], c[2, 2])      # 高值偏红
        self.assertEqual(c.shape, (3, 3))

    def test_clip(self):
        from map_data_layers import ramp_colors

        c = ramp_colors(np.array([-1.0, 2.0]))
        self.assertEqual(c.shape, (2, 3))
        self.assertTrue(np.all(c >= 0) and np.all(c <= 1))


class ValueOverlayTest(unittest.TestCase):
    def _idm(self):
        # 3x3：pid 1 在左上，pid 2 在右下
        return np.array([[1, 1, 0], [0, 0, 2], [0, 2, 2]], dtype=np.int32)

    def test_shape_bbox_alpha(self):
        from map_data_layers import build_value_overlay

        rgba, x0, y0 = build_value_overlay(
            self._idm(), {1: 10.0, 2: 40.0}, alpha=150)
        self.assertIsNotNone(rgba)
        self.assertEqual((rgba.shape[0], rgba.shape[1]), (3, 3))
        self.assertEqual((x0, y0), (0, 0))
        # 覆盖的地块有 alpha
        self.assertEqual(int((rgba[..., 3] > 0).sum()), 5)

    def test_empty_returns_none(self):
        from map_data_layers import build_value_overlay

        rgba, x0, y0 = build_value_overlay(
            self._idm(), {99: 1.0}, alpha=150)
        self.assertIsNone(rgba)


class CategoricalOverlayTest(unittest.TestCase):
    def test_two_categories(self):
        from map_data_layers import build_categorical_overlay

        idm = np.array([[1, 1], [2, 2]], dtype=np.int32)
        rgba, x0, y0 = build_categorical_overlay(
            idm, {1: "a", 2: "b"}, alpha=150)
        self.assertIsNotNone(rgba)
        self.assertEqual(int((rgba[..., 3] > 0).sum()), 4)
        colors = {tuple(rgba[0, 0, :3]), tuple(rgba[1, 0, :3])}
        self.assertEqual(len(colors), 2)


class ParseLoadersTest(unittest.TestCase):
    def test_load_supply_areas(self):
        from map_data_layers import load_supply_areas

        tmp = _mkdtemp("supply_")
        d = os.path.join(tmp, "map", "supplyareas")
        os.makedirs(d)
        with open(os.path.join(d, "1.txt"), "w", encoding="utf-8") as f:
            f.write("""supply_area={
	id=1
	name="SUPPLYAREA_1"
	value=12
	states={
		5 85 763
	}
}
supply_area={
	id=2
	value=3
	states={ 10 }
}
""")
        areas, meta = load_supply_areas(tmp, "")
        self.assertEqual(areas.get(5), 1)
        self.assertEqual(areas.get(763), 1)
        self.assertEqual(areas.get(10), 2)
        self.assertEqual(meta[1]["value"], 12)

    def test_load_railways(self):
        from map_data_layers import load_railways

        tmp = _mkdtemp("rail_")
        d = os.path.join(tmp, "map")
        os.makedirs(d)
        with open(os.path.join(d, "railways.txt"), "w", encoding="utf-8") as f:
            f.write("1 3 100 200 300\n2 2 400 500\n")
        segs = load_railways(tmp, "")
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0]["level"], 1)
        self.assertEqual(segs[0]["pids"], [100, 200, 300])
        self.assertEqual(segs[1]["level"], 2)

    def test_state_vp_and_resources(self):
        from map_data_layers import state_vp_and_resources

        states = {
            1: {"victory_points": [(100, 5), (200, 3)],
                "resources": {"steel": 6, "oil": 4}},
            2: {"victory_points": [], "resources": {}},
        }
        vp, res = state_vp_and_resources(states)
        self.assertEqual(vp[1], 8)
        self.assertEqual(vp[2], 0)
        self.assertEqual(res[1], 10)


class LineAndRiverTest(unittest.TestCase):
    def test_line_overlay(self):
        from map_data_layers import build_line_overlay

        rgba, x0, y0 = build_line_overlay(
            50, 30,
            [{"level": 2, "pids": [1, 2]}],
            lambda pid: {1: (5, 5), 2: (40, 20)}.get(pid), alpha=220)
        self.assertIsNotNone(rgba)
        self.assertEqual(rgba.shape[:2], (30, 50))

    def test_river_overlay(self):
        from PIL import Image
        from map_data_layers import build_river_overlay

        tmp = _mkdtemp("river_")
        fp = os.path.join(tmp, "rivers.bmp")
        im = Image.new("RGB", (10, 10), (122, 122, 122))
        for x in range(2, 8):
            im.putpixel((x, 5), (0, 0, 255))  # 河流像素
        im.save(fp)
        rgba, x0, y0 = build_river_overlay(fp, alpha=170)
        self.assertIsNotNone(rgba)
        self.assertGreater(int((rgba[..., 3] > 0).sum()), 0)


if __name__ == "__main__":
    unittest.main()