"""SimpleITK·torch 없이 실행되는 기하 계산 테스트: python -m unittest tests.test_geometry"""
import importlib.util
import math
import pathlib
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'backend' / 'algorithms' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


geometry = _load('geometry')
evaluation = _load('evaluation')


def brute_signed_distance(mask, spacing_cols_rows):
    """작은 2D mask용 signed distance(내부 양수). 테스트 전용."""
    sx, sy = spacing_cols_rows
    inside = np.argwhere(mask > 0)
    outside = np.argwhere(mask == 0)
    out = np.zeros(mask.shape)
    for r in range(mask.shape[0]):
        for c in range(mask.shape[1]):
            other = outside if mask[r, c] else inside
            d = np.sqrt(((other[:, 0] - r) * sy) ** 2 + ((other[:, 1] - c) * sx) ** 2).min()
            out[r, c] = d if mask[r, c] else -d
    return out


class AxisTest(unittest.TestCase):
    def test_identity_direction_is_k(self):
        self.assertEqual(geometry.axial_index_axis([1, 0, 0, 0, 1, 0, 0, 0, 1]), 2)

    def test_oasis_direction_is_j(self):
        # OASIS aligned: i→-R, j→-S, k→+A (RAS). LPS로 바꾼 direction 열은 (1,0,0), (0,0,-1), (0,-1,0).
        direction = [1, 0, 0, 0, 0, -1, 0, -1, 0]
        self.assertEqual(geometry.axial_index_axis(direction), 1)
        self.assertEqual(geometry.numpy_axis_from_index_axis(1), 1)


class InterpolationTest(unittest.TestCase):
    def test_fills_between_drawn_slices_on_chosen_axis(self):
        mask = np.zeros((12, 10, 16), dtype=np.uint8)
        mask[:, 2, :][3:9, 3:13] = 1      # numpy 축 1의 2번 slice
        mask[:, 8, :][5:7, 6:10] = 1      # numpy 축 1의 8번 slice
        filled, drawn = geometry.interpolate_mask_slices(mask, 1, (1.0, 1.0, 1.0), brute_signed_distance)
        self.assertEqual(drawn, [2, 8])
        areas = [int(filled[:, k, :].sum()) for k in range(2, 9)]
        self.assertEqual(areas[0], 60)
        self.assertEqual(areas[-1], 8)
        self.assertTrue(all(a >= b for a, b in zip(areas, areas[1:])), areas)
        self.assertEqual(int(filled[:, 0, :].sum()), 0)

    def test_requires_two_slices(self):
        mask = np.zeros((4, 4, 4), dtype=np.uint8)
        mask[1, 1, 1] = 1
        with self.assertRaises(ValueError):
            geometry.interpolate_mask_slices(mask, 0, (1, 1, 1), brute_signed_distance)


class SpeedImageTest(unittest.TestCase):
    def test_speed_is_high_inside_and_low_at_edges(self):
        inside = np.full(100, 0.02)
        foreground = np.concatenate([np.full(900, 0.03), np.full(100, 0.6)])
        alpha, beta = geometry.geodesic_sigmoid_parameters(inside, foreground)
        self.assertLess(alpha, 0)
        self.assertGreater(float(geometry.sigmoid(np.array([0.02]), alpha, beta)[0]), 0.95)
        self.assertLess(float(geometry.sigmoid(np.array([0.6]), alpha, beta)[0]), 0.05)

    def test_previous_fixed_parameters_were_inverted(self):
        # v6까지의 Sigmoid(gradient, -1, 5, 0, 1) = 출력 최대 0, 최소 1: 평탄한 곳 speed가 0에 가깝다.
        flat = geometry.sigmoid(np.array([0.05]), -1.0, 5.0, 0.0, 1.0)[0]
        self.assertLess(flat, 0.01)


class FlowTest(unittest.TestCase):
    def test_unit_flow_matches_lapirn_convention(self):
        d, h, w = 6, 7, 9
        flow = np.zeros((3, d, h, w))
        flow[0] = 2.0 / (w - 1)          # 채널 0 = 마지막 축(W) 방향 1 voxel
        flow[2] = -2.0 / (d - 1) * 2     # 채널 2 = 첫 축(D) 방향 -2 voxel
        vox = geometry.unit_flow_to_voxel(flow)
        np.testing.assert_allclose(vox[2], 1.0)
        np.testing.assert_allclose(vox[0], -2.0)
        np.testing.assert_allclose(vox[1], 0.0)

    def test_physical_conversion_uses_spacing_and_direction(self):
        disp_kji = np.zeros((3, 4, 5, 6))
        disp_kji[2] = 1.0                 # 배열 마지막 축 = index i 방향 1 voxel
        disp_kji[0] = 2.0                 # 배열 첫 축 = index k 방향 2 voxel
        direction = [1, 0, 0, 0, 0, -1, 0, -1, 0]
        phys = geometry.displacement_to_physical(disp_kji, (1.5, 2.0, 0.5), direction)
        np.testing.assert_allclose(phys[0, 0, 0], [1.5, -1.0, 0.0])

    def test_jacobian(self):
        zero = np.zeros((3, 5, 5, 5))
        np.testing.assert_allclose(geometry.jacobian_determinant(zero), 1.0)
        squeeze = np.zeros((3, 5, 5, 5))
        squeeze[0] = -0.5 * np.arange(5)[:, None, None]
        np.testing.assert_allclose(geometry.jacobian_determinant(squeeze), 0.5)
        fold = np.zeros((3, 5, 5, 5))
        fold[0] = -1.5 * np.arange(5)[:, None, None]
        self.assertTrue((geometry.jacobian_determinant(fold) < 0).all())


class DiceTest(unittest.TestCase):
    def test_missing_label_counts_as_zero(self):
        ref = np.zeros((4, 4), dtype=np.uint8); ref[0, :2] = 1; ref[3, :2] = 2
        pred = np.zeros((4, 4), dtype=np.uint8); pred[0, :2] = 1
        r = evaluation.DiceEvaluator().evaluate(pred, ref)
        self.assertEqual(r['dice_per_label'], {'1': 1.0, '2': 0.0})
        self.assertAlmostEqual(r['dice_mean'], 0.5)


if __name__ == '__main__':
    unittest.main()
