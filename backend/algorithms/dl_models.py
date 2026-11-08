"""Registration Deep Learning 모델 목록과 LFCAMorph 추론.

모델 목록
- lfcamorph-oasis: 사용자 제공 LFCAMorph(HMCN) OASIS 학습 가중치 MRD_FD_BD_l3_30000.pth. 실행 가능(torch 필요).
- 나머지 항목은 가중치를 아직 받지 않아 목록에만 표시하고 실행하지 않는다.

LFCAMorph 구현 근거
- 구조: LapIRN(Mok & Chung, MICCAI 2020)의 3단계 Laplacian pyramid와 scaling-and-squaring(7단계) diffeomorphic 적분.
- 세부 구성: 학습 경로 MRD_FD_BD / MA_bT_m / mid6_2 / S0.1C0.001 / range_flow 0.1과 Test_LFCAMorph_OASIS.py의 설정(concat='e0').
- 전처리·후처리: Test_LFCAMorph_OASIS.py와 같다. 원 해상도 영상을 144×160×192로 trilinear 축소해 추론하고,
  변형장을 align_corners=True로 원 해상도에 되돌린 뒤 원본 Moving을 warp한다.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from backend.algorithms.common import ProgressCallback, report, validate_scalar_volume
from backend.algorithms.geometry import displacement_to_physical, jacobian_determinant, unit_flow_to_voxel

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    name: str
    dataset: str
    weights_env: str
    weights_file: str
    runnable: bool
    description: str


MODELS: dict[str, ModelSpec] = {
    spec.model_id: spec
    for spec in (
        ModelSpec("lfcamorph-oasis", "LFCAMorph", "OASIS", "LFCAMORPH_OASIS_WEIGHTS",
                  "lfcamorph/MRD_FD_BD_l3_30000.pth", True,
                  "LapIRN 계열 3단계 diffeomorphic 정합. OASIS aligned 160×192×224 영상으로 학습."),
        ModelSpec("lfcamorph-lpba40", "LFCAMorph", "LPBA40", "LFCAMORPH_LPBA40_WEIGHTS",
                  "lfcamorph/lpba40.pth", False, "LPBA40 학습 가중치 미수신."),
        ModelSpec("voxelmorph-oasis", "VoxelMorph", "OASIS", "VOXELMORPH_OASIS_WEIGHTS",
                  "voxelmorph/oasis.pth", False, "가중치와 추론 코드 미수신."),
        ModelSpec("voxelmorph-lpba40", "VoxelMorph", "LPBA40", "VOXELMORPH_LPBA40_WEIGHTS",
                  "voxelmorph/lpba40.pth", False, "가중치와 추론 코드 미수신."),
        ModelSpec("hypermorph-oasis", "HyperMorph", "OASIS", "HYPERMORPH_OASIS_WEIGHTS",
                  "hypermorph/oasis.pth", False, "가중치와 추론 코드 미수신."),
    )
}

TRAINED_SHAPE = (160, 192, 224)  # OASIS aligned_norm, nibabel(i, j, k) 순서
NETWORK_SHAPE = (144, 160, 192)
LFCAMORPH_CONFIG = dict(
    ch_start=6,
    ch_start_magnitude=2,
    n_classes=3,
    range_flow=0.1,
    model_name_front="MRD_diff",
    model_name_back="both",
    doubleF=True,
    doubleB=True,
    batchsize=1,
    attn="multi_attn",
    attn_batch=True,
    attn_modi_multiple=True,
    concat="e0",
)

_lock = threading.Lock()
_cache: dict = {}


def weights_path(spec: ModelSpec) -> Path:
    return Path(os.getenv(spec.weights_env, str(MODEL_DIR / spec.weights_file)))


def status(model_id: str) -> dict:
    """torch 설치, 가중치 파일, 장치 상태를 확인한다. 모델은 불러오지 않는다."""
    spec = MODELS.get(model_id)
    if spec is None:
        return {"model_id": model_id, "available": False, "reason": "등록되지 않은 모델입니다."}
    base = {"model_id": spec.model_id, "name": spec.name, "dataset": spec.dataset, "description": spec.description}
    if not spec.runnable:
        return {**base, "available": False, "reason": "준비 중: " + spec.description}
    path = weights_path(spec)
    try:
        import torch
    except ImportError:
        return {**base, "available": False, "reason": "PyTorch가 설치되지 않았습니다. 서버 venv에 torch를 설치하세요."}
    if not path.is_file():
        return {**base, "available": False, "reason": f"가중치 파일이 없습니다: {path.name}"}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return {**base, "available": True, "reason": "", "weights": path.name, "device": device, "torch": torch.__version__}


def catalog() -> list[dict]:
    return [status(model_id) for model_id in MODELS]


def _build_lfcamorph(torch, device, path: Path):
    from backend.algorithms import lfcamorph_net as net

    net.set_device(device)
    c = LFCAMORPH_CONFIG
    common = dict(model_name_front=c["model_name_front"], model_name_back=c["model_name_back"],
                  doubleF=c["doubleF"], doubleB=c["doubleB"], batchsize=c["batchsize"], attn=c["attn"],
                  attn_batch=c["attn_batch"], attn_modi_multiple=c["attn_modi_multiple"], concat=c["concat"])
    shape = NETWORK_SHAPE
    shape_2 = tuple(s // 2 for s in shape)
    shape_4 = tuple(s // 4 for s in shape)
    lvl1 = net.model_diff_l1(2, c["ch_start"], c["ch_start_magnitude"], c["n_classes"], is_train=True,
                             imgshape=shape_4, range_flow=c["range_flow"], **common).to(device)
    lvl2 = net.model_diff_l2(2, c["ch_start"], c["ch_start_magnitude"], c["n_classes"], is_train=True,
                             imgshape=shape_2, range_flow=c["range_flow"], model_lvl1=lvl1, **common).to(device)
    model = net.model_diff_l3(2, c["ch_start"], c["ch_start_magnitude"], c["n_classes"], is_train=False,
                              imgshape=shape, range_flow=c["range_flow"], model_lvl2=lvl2, **common).to(device)
    state = torch.load(str(path), map_location=device, weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, net


def _load(spec: ModelSpec):
    with _lock:
        if spec.model_id in _cache:
            return _cache[spec.model_id]
        info = status(spec.model_id)
        if not info["available"]:
            raise ValueError(info["reason"])
        import torch

        device = torch.device(info["device"])
        path = weights_path(spec)
        model, net = _build_lfcamorph(torch, device, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        _cache[spec.model_id] = (torch, model, net, device, digest)
        return _cache[spec.model_id]


def _minmax(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        raise ValueError("밝기 변화가 없는 영상입니다.")
    return (a - lo) / (hi - lo)


class DeepLearningRegistration:
    """선택한 학습 모델로 Moving을 Fixed에 맞추는 변형장을 한 번의 추론으로 계산한다."""

    def __init__(self, model_id: str):
        if model_id not in MODELS:
            raise ValueError("등록되지 않은 모델입니다.")
        self.spec = MODELS[model_id]

    def predict(
        self,
        fixed_path: Path,
        moving_path: Path,
        output_path: Path,
        field_path: Path,
        progress: ProgressCallback = None,
    ) -> dict:
        started = time.perf_counter()
        label = f"{self.spec.name}({self.spec.dataset})"
        report(progress, 0.05, f"{label} 모델 준비 중")
        torch, model, net, device, digest = _load(self.spec)
        F = torch.nn.functional

        report(progress, 0.2, "입력 영상 읽는 중")
        fixed = sitk.ReadImage(str(fixed_path), sitk.sitkFloat32)
        moving = sitk.ReadImage(str(moving_path), sitk.sitkFloat32)
        validate_scalar_volume(fixed, "Fixed")
        validate_scalar_volume(moving, "Moving")
        notes = []
        same_grid = (fixed.GetSize() == moving.GetSize()
                     and np.allclose(fixed.GetSpacing(), moving.GetSpacing())
                     and np.allclose(fixed.GetOrigin(), moving.GetOrigin())
                     and np.allclose(fixed.GetDirection(), moving.GetDirection()))
        if not same_grid:
            moving = sitk.Resample(moving, fixed, sitk.Transform(), sitk.sitkLinear, 0.0, sitk.sitkFloat32)
            notes.append("Moving을 Fixed 격자로 옮겨 담았습니다. 두 영상이 같은 물리 공간에 미리 정렬되어 있어야 합니다.")
        # SimpleITK 배열 (k, j, i)를 학습 때 쓰인 nibabel 순서 (i, j, k)로 바꾼다.
        fixed_ijk = sitk.GetArrayFromImage(fixed).transpose(2, 1, 0)
        moving_ijk = sitk.GetArrayFromImage(moving).transpose(2, 1, 0)
        shape = fixed_ijk.shape
        if shape != TRAINED_SHAPE:
            notes.append(f"학습 영상 크기 {TRAINED_SHAPE}와 다른 {shape}입니다. OASIS aligned 영상이 아니면 정확도를 보장하지 않습니다.")

        report(progress, 0.35, f"추론 중 ({device.type})")
        with torch.no_grad():
            to_t = lambda a: torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32))[None, None].to(device)
            x = to_t(_minmax(moving_ijk))
            y = to_t(_minmax(fixed_ijk))
            x_ip = F.interpolate(x, size=NETWORK_SHAPE, mode="trilinear")
            y_ip = F.interpolate(y, size=NETWORK_SHAPE, mode="trilinear")
            flow = model(x_ip, y_ip)
            flow = F.interpolate(flow, size=shape, mode="trilinear", align_corners=True)

            report(progress, 0.8, "Moving 영상 warp 중")
            grid = torch.from_numpy(net.generate_grid_unit(shape)[None]).float().to(device)
            warped = net.SpatialTransform_unit()(to_t(moving_ijk), flow.permute(0, 2, 3, 4, 1), grid)
            warped_ijk = warped[0, 0].cpu().numpy()
            flow_unit = flow[0].cpu().numpy().astype(np.float64)

        report(progress, 0.9, "결과 저장 중")
        out = sitk.GetImageFromArray(warped_ijk.transpose(2, 1, 0).astype(np.float32))
        out.CopyInformation(fixed)
        sitk.WriteImage(out, str(output_path), useCompression=True)

        disp_ijk = unit_flow_to_voxel(flow_unit)  # 배열 축 (i, j, k) 순서 voxel 변위
        jac = jacobian_determinant(disp_ijk)
        disp_kji = np.stack([disp_ijk[2], disp_ijk[1], disp_ijk[0]]).transpose(0, 3, 2, 1)
        physical = displacement_to_physical(disp_kji, fixed.GetSpacing(), fixed.GetDirection())
        field = sitk.GetImageFromArray(physical.astype(np.float64), isVector=True)
        field.CopyInformation(fixed)
        sitk.WriteImage(field, str(field_path), useCompression=True)
        magnitude = np.linalg.norm(physical, axis=-1)
        return {
            "method": f"Deep Learning · {label}",
            "model_id": self.spec.model_id,
            "weights": f"{weights_path(self.spec).name} (sha256 {digest})",
            "device": device.type,
            "input_shape_ijk": list(shape),
            "network_shape": list(NETWORK_SHAPE),
            "runtime_s": round(time.perf_counter() - started, 2),
            "displacement_max_mm": float(magnitude.max()),
            "displacement_mean_mm": float(magnitude.mean()),
            "jacobian_nonpositive_percent": float(np.mean(jac <= 0) * 100.0),
            "notes": notes,
        }
