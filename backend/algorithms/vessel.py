"""D: Hessian 기반 혈관 강조 (Sato 방식, 단일 scale).

원본과 같은 itk.Hessian3DToVesselnessMeasureImageFilter를 쓰기 위해 itk 패키지를 사용한다.
SimpleITK에는 이 필터가 없다. 출력은 threshold를 거치지 않은 float vesselness.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from backend.algorithms.common import ProgressCallback, report


class HessianVesselness:
    def __init__(self, sigma: float = 0.7, alpha1: float = 0.3, alpha2: float = 3.0) -> None:
        for name, value in (("sigma", sigma), ("alpha1", alpha1), ("alpha2", alpha2)):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name}는 유한한 양수여야 합니다.")
        self.sigma = sigma
        self.alpha1 = alpha1
        self.alpha2 = alpha2

    def run(self, input_path: Path, output_path: Path, progress: ProgressCallback = None) -> dict:
        import itk  # import 시간이 길어서 실행 시점에 로드한다.

        report(progress, 0.05, "입력 영상 읽는 중")
        image = itk.imread(str(input_path), itk.F)
        if image.GetImageDimension() != 3:
            raise ValueError("3D 영상만 지원합니다.")
        size = [int(s) for s in itk.size(image)]
        if any(s < 4 for s in size):
            raise ValueError("Hessian은 각 축에 4개 이상의 복셀이 필요합니다.")
        if not np.isfinite(itk.array_view_from_image(image)).all():
            raise ValueError("입력에 유효하지 않은 복셀 값이 있습니다.")

        report(progress, 0.2, f"Hessian 계산 중 (sigma={self.sigma})")
        hessian = itk.HessianRecursiveGaussianImageFilter.New(Input=image)
        hessian.SetSigma(self.sigma)

        report(progress, 0.5, f"Vesselness 계산 중 (alpha1={self.alpha1}, alpha2={self.alpha2})")
        vesselness = itk.Hessian3DToVesselnessMeasureImageFilter[itk.F].New(Input=hessian.GetOutput())
        vesselness.SetAlpha1(self.alpha1)
        vesselness.SetAlpha2(self.alpha2)
        vesselness.Update()
        output = vesselness.GetOutput()

        values = itk.array_view_from_image(output)
        if not np.isfinite(values).all():
            raise RuntimeError("Vesselness 결과에 유효하지 않은 값이 있습니다.")

        report(progress, 0.9, "결과 저장 중")
        itk.imwrite(output, str(output_path), compression=True)
        return {
            "sigma": self.sigma,
            "alpha1": self.alpha1,
            "alpha2": self.alpha2,
            "size": size,
            "vesselness_min": float(values.min()),
            "vesselness_max": float(values.max()),
            "vesselness_p99": float(np.percentile(values, 99)),
        }
