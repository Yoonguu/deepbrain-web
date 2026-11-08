"""SimpleITK 기반 고전 처리: MIP, Threshold, Active contour, Slice 보간, Deformable(Rigid + Demons)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import SimpleITK as sitk

from backend.algorithms.common import ProgressCallback, report, validate_scalar_volume
from backend.algorithms.geometry import (
    axial_index_axis,
    geodesic_sigmoid_parameters,
    interpolate_mask_slices,
    numpy_axis_from_index_axis,
)
from backend.algorithms.region_growing import ConfidenceConnectedSegmentation
from backend.algorithms.registration import RegistrationParams, RigidRegistration


def axial_axis_info(image: sitk.Image) -> dict:
    """영상 방향에서 Axial(S축) index 축과 slice 수를 구한다."""
    index_axis = axial_index_axis(image.GetDirection())
    return {"axial_index_axis": "ijk"[index_axis], "axial_slices": int(image.GetSize()[index_axis])}


def maximum_intensity_projection(image: sitk.Image, start: int, end: int) -> tuple[sitk.Image, dict]:
    """Axial 방향 slab [start, end]의 최대값 투영. 파일 저장 축이 아니라 영상 방향으로 Axial 축을 고른다."""
    index_axis = axial_index_axis(image.GetDirection())
    count = image.GetSize()[index_axis]
    if start < 0 or start > end or end >= count:
        raise ValueError(f"Slab 범위를 확인하세요. Axial slice는 0~{count - 1}입니다.")
    region = [slice(None)] * 3
    region[index_axis] = slice(start, end + 1)
    projected = sitk.MaximumProjection(image[tuple(region)], index_axis)
    return projected, {"axial_index_axis": "ijk"[index_axis], "slab": [start, end], "axial_slices": count}


def binary_threshold(image: sitk.Image, lower: float, upper: float) -> sitk.Image:
    """lower ≤ 값 ≤ upper 영역을 1로 하는 binary mask."""
    if lower > upper:
        raise ValueError("Threshold 하한이 상한보다 큽니다.")
    return sitk.BinaryThreshold(image, lower, upper, 1, 0)


def label_threshold(image: sitk.Image, lower: float, upper: float) -> tuple[sitk.Image, dict]:
    """Label each face-connected component separately for editable region colors."""
    components = sitk.ConnectedComponent(binary_threshold(image, lower, upper))
    labels = sitk.RelabelComponent(components, sortByObjectSize=True)
    count = int(sitk.GetArrayViewFromImage(labels).max())
    if count > 65535:
        raise ValueError("영역이 65,535개를 초과합니다. Threshold 범위를 조정하세요.")
    return labels, {"label_count": count, "label_mode": "connected_components"}


def geodesic_active_contour(
    image: sitk.Image,
    seed_ras_mm: list[float],
    radius_vox: int,
    iterations: int,
    progress: ProgressCallback = None,
) -> tuple[sitk.Image, dict]:
    """Seed 주변 공에서 시작하는 Geodesic active contour. speed image는 영상 gradient 분포로 정한다."""
    seed = ConfidenceConnectedSegmentation._seed_index(image, seed_ras_mm)
    arr = sitk.GetArrayViewFromImage(image)
    zz, yy, xx = np.ogrid[: arr.shape[0], : arr.shape[1], : arr.shape[2]]
    r = max(2, int(radius_vox))
    ball = ((xx - seed[0]) ** 2 + (yy - seed[1]) ** 2 + (zz - seed[2]) ** 2) <= r**2
    mask = sitk.GetImageFromArray(ball.astype(np.uint8))
    mask.CopyInformation(image)
    initial = sitk.SignedMaurerDistanceMap(mask, insideIsPositive=False, squaredDistance=False, useImageSpacing=True)

    report(progress, 0.2, "Gradient와 speed image 계산 중")
    gradient = sitk.GradientMagnitudeRecursiveGaussian(image, 1.0)
    g = sitk.GetArrayViewFromImage(gradient)
    foreground = g[arr > 0] if np.any(arr > 0) else g.ravel()
    alpha, beta = geodesic_sigmoid_parameters(g[ball], foreground)
    speed = sitk.Sigmoid(gradient, alpha, beta, 1.0, 0.0)

    report(progress, 0.35, f"Active contour 진행 중 (최대 {iterations}회)")
    gac = sitk.GeodesicActiveContourLevelSetImageFilter()
    gac.SetPropagationScaling(1.0)
    gac.SetCurvatureScaling(1.0)
    gac.SetAdvectionScaling(1.0)
    gac.SetMaximumRMSError(0.01)
    gac.SetNumberOfIterations(int(iterations))
    level_set = gac.Execute(sitk.Cast(initial, sitk.sitkFloat32), sitk.Cast(speed, sitk.sitkFloat32))
    result = sitk.Cast(level_set <= 0, sitk.sitkUInt8)
    voxels = int(sitk.GetArrayViewFromImage(result).sum())
    sx, sy, sz = image.GetSpacing()
    return result, {
        "seed_index": list(seed),
        "initial_radius_vox": r,
        "sigmoid_alpha": alpha,
        "sigmoid_beta": beta,
        "elapsed_iterations": int(gac.GetElapsedIterations()),
        "rms_change": float(gac.GetRMSChange()),
        "volume_mm3": voxels * sx * sy * sz,
        "voxels": voxels,
    }


def _signed_distance_2d(slice2d: np.ndarray, spacing_cols_rows: tuple[float, float]) -> np.ndarray:
    img = sitk.GetImageFromArray(slice2d.astype(np.uint8))
    img.SetSpacing(spacing_cols_rows)
    dist = sitk.SignedMaurerDistanceMap(img, insideIsPositive=True, squaredDistance=False, useImageSpacing=True)
    return sitk.GetArrayFromImage(dist)


def interpolate_axial_mask(image: sitk.Image) -> tuple[sitk.Image, dict]:
    """Axial slice 일부에 그린 mask 사이를 signed distance 보간으로 채운다."""
    index_axis = axial_index_axis(image.GetDirection())
    arr = sitk.GetArrayFromImage(image) > 0
    filled, drawn = interpolate_mask_slices(
        arr, numpy_axis_from_index_axis(index_axis), image.GetSpacing(), _signed_distance_2d
    )
    out = sitk.GetImageFromArray(filled.astype(np.uint8))
    out.CopyInformation(image)
    return out, {"axial_index_axis": "ijk"[index_axis], "drawn_slices": drawn}


def deformable_registration(
    fixed_path: Path,
    moving_path: Path,
    output_path: Path,
    transform_path: Path,
    iterations: int,
    progress: ProgressCallback = None,
) -> dict:
    """Rigid 정합으로 초기 정렬한 뒤 histogram matching과 Diffeomorphic Demons를 적용한다.

    최종 영상은 원본 Moving을 Rigid와 변위장을 합성한 transform으로 한 번만 resample해 보간 손실을 줄인다.
    """
    fixed = sitk.ReadImage(str(fixed_path), sitk.sitkFloat32)
    moving = sitk.ReadImage(str(moving_path), sitk.sitkFloat32)
    validate_scalar_volume(fixed, "Fixed")
    validate_scalar_volume(moving, "Moving")

    versor, rigid = RigidRegistration(RegistrationParams(iterations_per_level=min(150, iterations))).register(
        fixed, moving, progress, (0.05, 0.45)
    )
    sitk.WriteTransform(versor, str(transform_path))
    rigid_moved = sitk.Resample(moving, fixed, versor, sitk.sitkLinear, 0.0, sitk.sitkFloat32)

    report(progress, 0.5, "Histogram matching 중")
    matched = sitk.HistogramMatching(rigid_moved, fixed, numberOfHistogramLevels=1024, numberOfMatchPoints=7,
                                     thresholdAtMeanIntensity=True)

    demons = sitk.DiffeomorphicDemonsRegistrationFilter()
    demons.SetNumberOfIterations(int(iterations))
    demons.SetStandardDeviations(1.0)

    def on_iteration() -> None:
        done = demons.GetElapsedIterations()
        report(progress, 0.5 + 0.4 * min(done, iterations) / iterations,
               f"Demons iteration {done}/{iterations}, metric {demons.GetMetric():.6g}")

    demons.AddCommand(sitk.sitkIterationEvent, on_iteration)
    field = demons.Execute(fixed, matched)
    field = sitk.Cast(field, sitk.sitkVectorFloat64)

    jacobian = sitk.GetArrayFromImage(sitk.DisplacementFieldJacobianDeterminant(field))
    folding = float(np.mean(jacobian <= 0) * 100.0)
    magnitude = np.linalg.norm(sitk.GetArrayViewFromImage(field), axis=-1)

    report(progress, 0.93, "Rigid와 변위장을 합성해 resample 중")
    composite = sitk.CompositeTransform([versor, sitk.DisplacementFieldTransform(field)])
    warped = sitk.Resample(moving, fixed, composite, sitk.sitkLinear, 0.0, sitk.sitkFloat32)
    sitk.WriteImage(warped, str(output_path), useCompression=True)
    return {
        "method": "Rigid(VersorRigid3D) → Histogram matching → Diffeomorphic Demons",
        "rigid": rigid,
        "demons_iterations": int(demons.GetElapsedIterations()),
        "demons_metric": float(demons.GetMetric()),
        "demons_rms_change": float(demons.GetRMSChange()),
        "displacement_max_mm": float(magnitude.max()),
        "displacement_mean_mm": float(magnitude.mean()),
        "jacobian_nonpositive_percent": folding,
    }
