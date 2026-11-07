from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import SimpleITK as sitk

ProgressCallback = Optional[Callable[[float, str], None]]


def report(progress: ProgressCallback, fraction: float, message: str) -> None:
    if progress is not None:
        progress(fraction, message)


def validate_scalar_volume(image: sitk.Image, label: str, min_voxels_per_axis: int = 2) -> None:
    if image.GetDimension() != 3 or image.GetNumberOfComponentsPerPixel() != 1:
        raise ValueError(f"{label}: 단일 성분 3D 볼륨만 지원합니다.")
    if any(s < min_voxels_per_axis for s in image.GetSize()):
        raise ValueError(f"{label}: 각 축에 {min_voxels_per_axis}개 이상의 복셀이 필요합니다.")
    if any(not np.isfinite(s) or s <= 0 for s in image.GetSpacing()):
        raise ValueError(f"{label}: 유효하지 않은 spacing입니다.")
    array = sitk.GetArrayViewFromImage(image)
    if not np.isfinite(array).all():
        raise ValueError(f"{label}: 유효하지 않은 복셀 값이 있습니다.")
    if float(array.min()) == float(array.max()):
        raise ValueError(f"{label}: 밝기 변화가 없는 영상입니다.")
