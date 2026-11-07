"""A: 3D Rigid Registration.

DeepBrain Basic 0.1.0-ui 바이너리에서 확인한 설정을 SimpleITK로 옮긴 구현.
VersorRigid3D, Mattes MI(32 bins) 또는 MeanSquares, RegularStepGradientDescent,
2-level pyramid(shrink 2,1 / sigma 1,0 mm), PhysicalShift scale, moments 초기화.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import SimpleITK as sitk

from backend.algorithms.common import ProgressCallback, report, validate_scalar_volume


@dataclass(frozen=True)
class RegistrationParams:
    metric: str = "mattes"
    iterations_per_level: int = 150
    learning_rate: float = 0.2
    min_step: float = 1e-4
    relaxation_factor: float = 0.8
    gradient_tolerance: float = 1e-6
    histogram_bins: int = 32
    shrink_factors: tuple[int, ...] = (2, 1)
    smoothing_sigmas: tuple[float, ...] = (1.0, 0.0)
    sampling_threshold_voxels: int = 250_000
    sampling_percentage: float = 0.2
    random_seed: int = 42


def _extract_versor(transform: sitk.Transform) -> sitk.VersorRigid3DTransform:
    if transform.GetName() == "CompositeTransform":
        composite = sitk.CompositeTransform(transform)
        transform = composite.GetNthTransform(composite.GetNumberOfTransforms() - 1)
    return sitk.VersorRigid3DTransform(transform)


def _euler_zyx(matrix: tuple[float, ...]) -> tuple[float, float, float]:
    """R = Rz Ry Rx 분해. 반환 순서 (rx, ry, rz), 단위 radian."""
    m = matrix
    ry = math.asin(max(-1.0, min(1.0, -m[6])))
    rx = math.atan2(m[7], m[8])
    rz = math.atan2(m[3], m[0])
    return rx, ry, rz


class RigidRegistration:
    def __init__(self, params: RegistrationParams | None = None) -> None:
        self.params = params or RegistrationParams()
        if self.params.metric not in ("mattes", "meansquares"):
            raise ValueError("metric은 mattes 또는 meansquares만 지원합니다.")
        if len(self.params.shrink_factors) != len(self.params.smoothing_sigmas):
            raise ValueError("shrink_factors와 smoothing_sigmas의 level 수가 다릅니다.")

    def run(
        self,
        fixed_path: Path,
        moving_path: Path,
        output_path: Path,
        transform_path: Path,
        progress: ProgressCallback = None,
    ) -> dict:
        report(progress, 0.02, "입력 영상 읽는 중")
        fixed = sitk.ReadImage(str(fixed_path), sitk.sitkFloat32)
        moving = sitk.ReadImage(str(moving_path), sitk.sitkFloat32)
        validate_scalar_volume(fixed, "Fixed")
        validate_scalar_volume(moving, "Moving")
        versor, info = self.register(fixed, moving, progress)

        report(progress, 0.92, "Fixed grid로 resample 중")
        resampled = sitk.Resample(moving, fixed, versor, sitk.sitkLinear, 0.0, sitk.sitkFloat32)
        if float(sitk.GetArrayViewFromImage(resampled).max()) == 0.0:
            raise RuntimeError("정합 결과가 비어 있습니다.")
        sitk.WriteImage(resampled, str(output_path), useCompression=True)
        sitk.WriteTransform(versor, str(transform_path))
        return info

    def register(
        self,
        fixed: sitk.Image,
        moving: sitk.Image,
        progress: ProgressCallback = None,
        progress_span: tuple[float, float] = (0.05, 0.9),
    ) -> tuple[sitk.VersorRigid3DTransform, dict]:
        """Fixed·Moving 영상(float32)을 받아 정합 transform과 결과 정보를 반환한다."""
        p = self.params
        lo, hi = progress_span

        initial = sitk.CenteredTransformInitializer(
            fixed,
            moving,
            sitk.VersorRigid3DTransform(),
            sitk.CenteredTransformInitializerFilter.MOMENTS,
        )

        reg = sitk.ImageRegistrationMethod()
        if p.metric == "mattes":
            reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=p.histogram_bins)
        else:
            reg.SetMetricAsMeanSquares()

        if fixed.GetNumberOfPixels() > p.sampling_threshold_voxels:
            reg.SetMetricSamplingStrategy(reg.RANDOM)
            reg.SetMetricSamplingPercentage(p.sampling_percentage, p.random_seed)
        else:
            reg.SetMetricSamplingStrategy(reg.NONE)

        reg.SetInterpolator(sitk.sitkLinear)
        reg.SetOptimizerAsRegularStepGradientDescent(
            learningRate=p.learning_rate,
            minStep=p.min_step,
            numberOfIterations=p.iterations_per_level,
            relaxationFactor=p.relaxation_factor,
            gradientMagnitudeTolerance=p.gradient_tolerance,
        )
        reg.SetOptimizerScalesFromPhysicalShift()
        reg.SetShrinkFactorsPerLevel(list(p.shrink_factors))
        reg.SetSmoothingSigmasPerLevel(list(p.smoothing_sigmas))
        reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
        reg.SetInitialTransform(initial, inPlace=False)

        levels = len(p.shrink_factors)

        def on_iteration() -> None:
            level = reg.GetCurrentLevel()
            iteration = reg.GetOptimizerIteration()
            fraction = lo + (hi - lo) * (level + min(iteration, p.iterations_per_level) / p.iterations_per_level) / levels
            report(
                progress,
                min(fraction, hi),
                f"Level {level + 1}/{levels}, iteration {iteration}, metric {reg.GetMetricValue():.6g}",
            )

        reg.AddCommand(sitk.sitkIterationEvent, on_iteration)

        report(progress, lo, "Rigid 정합 실행 중")
        final = reg.Execute(fixed, moving)

        metric_value = reg.GetMetricValue()
        if not math.isfinite(metric_value):
            raise RuntimeError("정합 점수가 유효하지 않습니다.")
        versor = _extract_versor(final)
        parameters = versor.GetParameters()
        if not all(math.isfinite(v) for v in parameters):
            raise RuntimeError("Transform parameter가 유효하지 않습니다.")

        rx, ry, rz = _euler_zyx(versor.GetMatrix())
        return versor, {
            "metric": p.metric,
            "metric_value": metric_value,
            "stop_condition": reg.GetOptimizerStopConditionDescription(),
            "last_level_iterations": reg.GetOptimizerIteration(),
            "versor": list(parameters[:3]),
            "translation_mm": list(parameters[3:6]),
            "euler_rad_xyz": [rx, ry, rz],
            "euler_deg_xyz": [math.degrees(v) for v in (rx, ry, rz)],
            "center_mm": list(versor.GetCenter()),
        }
