"""SimpleITK·torch 없이 numpy만으로 계산하는 기하 함수.

영상 방향, slice 보간, 변형장 품질처럼 단위 테스트가 필요한 계산을 모은다.
"""

from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

SignedDistance2D = Callable[[np.ndarray, tuple[float, float]], np.ndarray]


def axial_index_axis(direction: Sequence[float]) -> int:
    """ITK direction(행 우선 3×3, LPS)에서 Superior 방향에 가장 가까운 index 축(0=i, 1=j, 2=k)을 반환한다."""
    d = np.asarray(direction, dtype=float).reshape(3, 3)
    return int(np.argmax(np.abs(d[2, :])))


def numpy_axis_from_index_axis(index_axis: int) -> int:
    """SimpleITK의 GetArrayFromImage 배열은 (k, j, i) 순서이므로 index 축을 numpy 축으로 바꾼다."""
    return 2 - index_axis


def interpolate_mask_slices(
    binary: np.ndarray,
    numpy_axis: int,
    spacing_xyz: Sequence[float],
    signed_distance: SignedDistance2D,
) -> tuple[np.ndarray, list[int]]:
    """지정 축의 비어 있지 않은 slice 사이를 signed distance 선형 보간으로 채운다.

    signed_distance(slice2d, (spacing_cols, spacing_rows))는 내부가 양수인 거리 지도를 반환해야 한다.
    반환값은 보간된 mask(uint8, 입력과 같은 축 순서)와 원래 그려진 slice 번호 목록이다.
    """
    moved = np.moveaxis(binary.astype(np.uint8) > 0, numpy_axis, 0).astype(np.uint8)
    remaining = [a for a in range(3) if a != numpy_axis]
    # numpy 축 a는 index 축 2-a에 대응하므로 spacing도 그 축 값을 쓴다.
    row_spacing = float(spacing_xyz[2 - remaining[0]])
    col_spacing = float(spacing_xyz[2 - remaining[1]])
    drawn = [i for i in range(moved.shape[0]) if moved[i].any()]
    if len(drawn) < 2:
        raise ValueError("두 개 이상의 Axial slice에 수동 Mask가 필요합니다.")
    for left, right in zip(drawn, drawn[1:]):
        if right - left < 2:
            continue
        dl = signed_distance(moved[left], (col_spacing, row_spacing))
        dr = signed_distance(moved[right], (col_spacing, row_spacing))
        for k in range(left + 1, right):
            t = (k - left) / (right - left)
            moved[k] = ((1.0 - t) * dl + t * dr) > 0
    return np.moveaxis(moved, 0, numpy_axis).copy(), drawn


def geodesic_sigmoid_parameters(seed_gradient: np.ndarray, foreground_gradient: np.ndarray) -> tuple[float, float]:
    """Geodesic active contour의 speed image용 sigmoid (alpha, beta)를 영상 gradient 분포로 정한다.

    ITK Software Guide의 기준을 따른다. K1은 구조 내부 gradient(seed 주변 중앙값), K2는 경계 gradient
    (전경 90 percentile)이며 alpha = -(K2 - K1) / 6, beta = (K1 + K2) / 2로 두어 내부는 1, 경계는 0에 가깝게 만든다.
    """
    k1 = float(np.median(seed_gradient)) if seed_gradient.size else 0.0
    k2 = float(np.percentile(foreground_gradient, 90)) if foreground_gradient.size else k1
    if not np.isfinite(k1) or not np.isfinite(k2):
        raise ValueError("Gradient 값이 유효하지 않습니다.")
    if k2 <= k1:
        k2 = k1 + max(abs(k1), 1e-6)
    return -(k2 - k1) / 6.0, (k1 + k2) / 2.0


def sigmoid(values: np.ndarray, alpha: float, beta: float, out_max: float = 1.0, out_min: float = 0.0) -> np.ndarray:
    """ITK SigmoidImageFilter와 같은 식. 테스트에서 speed image 방향을 확인하는 데 쓴다."""
    return (out_max - out_min) / (1.0 + np.exp(-(values - beta) / alpha)) + out_min


def unit_flow_to_voxel(flow_unit: np.ndarray) -> np.ndarray:
    """LapIRN 계열의 정규화 변형장 (3, D, H, W)을 배열 축(D, H, W) 순서의 voxel 변위로 바꾼다.

    grid_sample 규약상 채널 0은 마지막 축(W), 채널 2는 첫 축(D) 방향이며 align_corners=True이므로
    voxel 변위 = 정규화 변위 × (축 길이 - 1) / 2 이다. LapIRN Functions.transform_unit_flow_to_flow와 같다.
    """
    _, d, h, w = flow_unit.shape
    return np.stack(
        [
            flow_unit[2] * (d - 1) / 2.0,
            flow_unit[1] * (h - 1) / 2.0,
            flow_unit[0] * (w - 1) / 2.0,
        ]
    )


def jacobian_determinant(displacement_vox: np.ndarray) -> np.ndarray:
    """배열 축 순서 voxel 변위 (3, D, H, W)에서 변환 x + u(x)의 Jacobian determinant를 계산한다."""
    grads = [np.gradient(displacement_vox[c], axis=(0, 1, 2)) for c in range(3)]
    j = np.empty((3, 3) + displacement_vox.shape[1:], dtype=np.float64)
    for c in range(3):
        for a in range(3):
            j[c, a] = grads[c][a] + (1.0 if c == a else 0.0)
    return (
        j[0, 0] * (j[1, 1] * j[2, 2] - j[1, 2] * j[2, 1])
        - j[0, 1] * (j[1, 0] * j[2, 2] - j[1, 2] * j[2, 0])
        + j[0, 2] * (j[1, 0] * j[2, 1] - j[1, 1] * j[2, 0])
    )


def displacement_to_physical(
    displacement_vox: np.ndarray, spacing_xyz: Sequence[float], direction: Sequence[float]
) -> np.ndarray:
    """배열 축 순서 voxel 변위 (3, D, H, W)를 ITK 물리 좌표(LPS, mm) 변위 (D, H, W, 3)로 바꾼다.

    배열 축 (D, H, W)는 index 축 (k, j, i)이므로 index 순서로 뒤집은 뒤 spacing과 direction을 곱한다.
    """
    d = np.asarray(direction, dtype=float).reshape(3, 3)
    s = np.asarray(spacing_xyz, dtype=float)
    index_disp = np.stack([displacement_vox[2], displacement_vox[1], displacement_vox[0]], axis=-1)
    return (index_disp * s) @ d.T
