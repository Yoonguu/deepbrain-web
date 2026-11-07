"""E: Confidence Connected Region Growing.

seed는 NiiVue가 주는 RAS mm 좌표로 받고, ITK의 LPS 좌표로 바꾼 뒤 voxel index로 변환한다.
출력은 label 0/1 binary mask(uint8).
"""

from __future__ import annotations

from pathlib import Path

import SimpleITK as sitk

from backend.algorithms.common import ProgressCallback, report, validate_scalar_volume


class ConfidenceConnectedSegmentation:
    def __init__(self, multiplier: float = 2.5, iterations: int = 4, radius: int = 1) -> None:
        if not (0 < multiplier <= 20):
            raise ValueError("multiplier는 0 초과 20 이하여야 합니다.")
        if not (0 <= iterations <= 100):
            raise ValueError("iterations는 0 이상 100 이하여야 합니다.")
        if not (0 <= radius <= 10):
            raise ValueError("radius는 0 이상 10 이하여야 합니다.")
        self.multiplier = multiplier
        self.iterations = iterations
        self.radius = radius

    @staticmethod
    def _seed_index(image: sitk.Image, ras_mm: list[float]) -> tuple[int, int, int]:
        lps = (-float(ras_mm[0]), -float(ras_mm[1]), float(ras_mm[2]))
        index = image.TransformPhysicalPointToIndex(lps)
        if any(i < 0 or i >= s for i, s in zip(index, image.GetSize())):
            raise ValueError(f"Seed가 영상 밖에 있습니다: RAS {ras_mm[:3]} mm")
        return tuple(int(i) for i in index)

    def run(
        self,
        input_path: Path,
        seeds_ras_mm: list[list[float]],
        output_path: Path,
        progress: ProgressCallback = None,
    ) -> dict:
        if not seeds_ras_mm:
            raise ValueError("유효한 seed를 1개 이상 추가하세요.")
        report(progress, 0.05, "입력 영상 읽는 중")
        image = sitk.ReadImage(str(input_path), sitk.sitkFloat32)
        validate_scalar_volume(image, "Input")

        seeds: list[tuple[int, int, int]] = []
        for mm in seeds_ras_mm:
            index = self._seed_index(image, mm)
            if index not in seeds:
                seeds.append(index)

        report(progress, 0.3, f"Region growing 실행 중 (seed {len(seeds)}개)")
        mask = sitk.ConfidenceConnected(
            image,
            seedList=seeds,
            numberOfIterations=self.iterations,
            multiplier=self.multiplier,
            initialNeighborhoodRadius=self.radius,
            replaceValue=1,
        )
        mask = sitk.Cast(mask, sitk.sitkUInt8)

        foreground = int(sitk.GetArrayViewFromImage(mask).sum())
        total = int(image.GetNumberOfPixels())
        report(progress, 0.9, "결과 저장 중")
        sitk.WriteImage(mask, str(output_path), useCompression=True)
        return {
            "multiplier": self.multiplier,
            "iterations": self.iterations,
            "radius": self.radius,
            "seeds_index": [list(s) for s in seeds],
            "foreground_voxels": foreground,
            "total_voxels": total,
            "foreground_percent": 100.0 * foreground / total,
            "empty_mask": foreground == 0,
            "entire_image": foreground == total,
        }
