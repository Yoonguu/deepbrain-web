"""정량 평가: label별 Dice와 표면 거리 지표(HD, HD95, ASD, ASSD).

표면 거리 정의는 medpy.metric.binary와 같다.
- 표면: mask에서 6-이웃 1회 erosion을 뺀 voxel. 영상 밖은 배경으로 본다.
- d(A→B): A 표면 voxel마다 B 표면까지의 최소 Euclidean 거리(mm, voxel spacing 반영).
- HD = max(max d(P→R), max d(R→P))
- HD95 = percentile(concatenate(d(P→R), d(R→P)), 95)
- ASD = mean d(P→R)   (P: 예측, R: 기준)
- ASSD = mean(concatenate(d(P→R), d(R→P)))
한쪽 mask가 비어 있으면 표면 거리를 정의할 수 없어 None과 사유를 돌려준다.

이 모듈은 numpy만 쓴다. 거리 변환 함수는 호출하는 쪽에서 넣는다(scipy 또는 SimpleITK).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

METRICS = ("dice", "hd", "hd95", "asd", "assd")
SURFACE_METRICS = ("hd", "hd95", "asd", "assd")

# edt(binary_zero_is_target, spacing_numpy_order) -> 각 voxel에서 0인 voxel까지의 거리
DistanceTransform = Callable[[np.ndarray, tuple], np.ndarray]


def _erode6(mask: np.ndarray) -> np.ndarray:
    """6-이웃(면 연결) 구조 요소로 1회 erosion. 영상 경계 밖은 0."""
    padded = np.pad(mask, 1, constant_values=False)
    core = padded[1:-1, 1:-1, 1:-1].copy()
    for axis in range(3):
        for shift in (-1, 1):
            core &= np.roll(padded, shift, axis=axis)[1:-1, 1:-1, 1:-1]
    return core


def surface(mask: np.ndarray) -> np.ndarray:
    mask = mask.astype(bool)
    return mask & ~_erode6(mask)


def _crop_pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """두 mask를 합집합 bounding box로 잘라 1 voxel 0 테두리를 붙인다.

    두 표면은 모두 box 안에 있고 Euclidean 거리는 영역 모양과 무관하므로 거리값은 바뀌지 않는다.
    테두리는 원 영상 경계에 닿은 mask를 경계 밖 배경 규칙과 같게 다루기 위한 것이다.
    """
    union = a | b
    idx = [np.flatnonzero(union.any(axis=tuple(j for j in range(3) if j != i))) for i in range(3)]
    box = tuple(slice(v[0], v[-1] + 1) for v in idx)
    return np.pad(a[box], 1), np.pad(b[box], 1)


def directed_surface_distances(a: np.ndarray, b: np.ndarray, spacing: tuple, edt: DistanceTransform) -> np.ndarray:
    """A 표면 voxel에서 B 표면까지의 거리 배열. spacing은 numpy 축 순서(z, y, x)."""
    a, b = _crop_pair(a.astype(bool), b.astype(bool))
    sa, sb = surface(a), surface(b)
    return edt(~sb, spacing)[sa]


def surface_metrics(pred: np.ndarray, ref: np.ndarray, spacing: tuple, edt: DistanceTransform) -> dict:
    if not pred.any() or not ref.any():
        reason = "두 mask가 모두 비어 있습니다." if not pred.any() and not ref.any() else \
            ("예측 mask가 비어 있습니다." if not pred.any() else "기준 mask가 비어 있습니다.")
        return {m: None for m in SURFACE_METRICS} | {"undefined_reason": reason}
    pr = directed_surface_distances(pred, ref, spacing, edt)
    rp = directed_surface_distances(ref, pred, spacing, edt)
    pooled = np.concatenate((pr, rp))
    return {
        "hd": float(max(pr.max(), rp.max())),
        "hd95": float(np.percentile(pooled, 95)),
        "asd": float(pr.mean()),
        "assd": float(pooled.mean()),
    }


def dice(pred: np.ndarray, ref: np.ndarray) -> float | None:
    den = int(pred.sum() + ref.sum())
    return float(2.0 * np.logical_and(pred, ref).sum() / den) if den else None


class SegmentationEvaluator:
    """예측과 기준 label 영상의 label별 지표를 계산한다.

    한쪽에만 있는 label은 Dice 0, 표면 거리 None(정의되지 않음)으로 넣는다. 정합 후 구조가 사라진 경우를
    건너뛰면 평균 점수가 실제보다 좋게 나오기 때문이다.
    """

    def __init__(self, edt: DistanceTransform | None = None):
        self.edt = edt

    def evaluate(
        self,
        prediction: np.ndarray,
        reference: np.ndarray,
        metrics: tuple | list = ("dice",),
        spacing: tuple = (1.0, 1.0, 1.0),
        labels: list[int] | None = None,
    ) -> dict:
        if prediction.shape != reference.shape:
            raise ValueError("두 label 영상의 크기가 같아야 합니다.")
        metrics = [m for m in METRICS if m in set(metrics)]
        if not metrics:
            raise ValueError("평가 지표를 하나 이상 선택하세요.")
        wants_surface = any(m in SURFACE_METRICS for m in metrics)
        if wants_surface and (prediction.ndim != 3 or self.edt is None):
            raise ValueError("표면 거리 지표는 3D 영상과 거리 변환 함수가 필요합니다.")
        if labels is None:
            labels = sorted(int(v) for v in np.union1d(np.unique(prediction), np.unique(reference)) if v != 0)

        def measure(p: np.ndarray, r: np.ndarray) -> dict:
            row = {}
            if "dice" in metrics:
                row["dice"] = dice(p, r)
            if wants_surface:
                row.update({k: v for k, v in surface_metrics(p, r, spacing, self.edt).items()
                            if k in metrics or k == "undefined_reason"})
            return row

        per_label = {}
        for label in labels:
            p, r = prediction == label, reference == label
            if not p.any() and not r.any():
                continue
            per_label[str(label)] = measure(p, r)
        foreground = measure(prediction > 0, reference > 0)

        summary = {}
        for m in metrics:
            values = [row[m] for row in per_label.values() if row.get(m) is not None]
            summary[m] = {"mean": float(np.mean(values)) if values else None,
                          "defined_labels": len(values), "labels": len(per_label)}
        return {
            "metrics": metrics,
            "labels": len(per_label),
            "per_label": per_label,
            "foreground": foreground,
            "summary": summary,
            "both_empty": not prediction.any() and not reference.any(),
            "units": {"dice": "0~1", "hd": "mm", "hd95": "mm", "asd": "mm", "assd": "mm"},
        }


class DiceEvaluator:
    """v7 호환: label별 Dice만 계산한다."""

    def evaluate(self, prediction: np.ndarray, reference: np.ndarray, labels: list[int] | None = None) -> dict:
        r = SegmentationEvaluator().evaluate(prediction, reference, ("dice",), labels=labels)
        per_label = {k: v["dice"] for k, v in r["per_label"].items()}
        fg = r["foreground"]["dice"]
        return {
            "labels": len(per_label),
            "dice_mean": r["summary"]["dice"]["mean"],
            "dice_per_label": per_label,
            "dice_foreground": 1.0 if fg is None else fg,
            "both_empty": r["both_empty"],
        }
