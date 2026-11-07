"""정량 평가: label별 Dice."""

from __future__ import annotations

import numpy as np


class DiceEvaluator:
    """두 label 영상의 label별 Dice를 계산한다.

    한쪽에만 있는 label은 0점으로 넣는다. 정합 후 구조가 사라진 경우를 건너뛰면 점수가 실제보다 높게 나오기 때문이다.
    """

    def evaluate(self, prediction: np.ndarray, reference: np.ndarray, labels: list[int] | None = None) -> dict:
        if prediction.shape != reference.shape:
            raise ValueError("두 label 영상의 크기가 같아야 합니다.")
        if labels is None:
            labels = sorted(int(v) for v in np.union1d(np.unique(prediction), np.unique(reference)) if v != 0)
        per_label = {}
        for label in labels:
            p, r = prediction == label, reference == label
            den = int(p.sum() + r.sum())
            if den == 0:
                continue
            per_label[str(label)] = float(2.0 * np.logical_and(p, r).sum() / den)
        binary_p, binary_r = prediction > 0, reference > 0
        den = int(binary_p.sum() + binary_r.sum())
        return {
            "labels": len(per_label),
            "dice_mean": float(np.mean(list(per_label.values()))) if per_label else None,
            "dice_per_label": per_label,
            "dice_foreground": float(2.0 * np.logical_and(binary_p, binary_r).sum() / den) if den else 1.0,
            "both_empty": den == 0,
        }
