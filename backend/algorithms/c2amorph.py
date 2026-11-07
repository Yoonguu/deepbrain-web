"""F: C2AMorph 추론.

구현 근거
- 구조: LapIRN(Mok & Chung, MICCAI 2020)의 3단계 Laplacian pyramid와 scaling-and-squaring(7단계) diffeomorphic 적분.
- 가중치와 세부 구조: 사용자 제공 LFCAMorph(HMCN) OASIS 학습 결과 MRD_FD_BD_l3_30000.pth.
  학습 경로 MRD_FD_BD / MA_bT_m / mid6_2 / S0.1C0.001 / range_flow 0.1과 Test_LFCAMorph_OASIS.py의 설정(concat='e0')을 따른다.
- 전처리·후처리: Test_LFCAMorph_OASIS.py와 같다. 원 해상도 영상을 144×160×192로 trilinear 축소해 추론하고,
  변형장을 align_corners=True로 원 해상도에 되돌린 뒤 원본 Moving을 warp한다.

torch는 선택 의존성이다. 설치되지 않았으면 status()가 사유를 돌려주고 predict()는 ValueError로 알린다.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from backend.algorithms.common import ProgressCallback, report, validate_scalar_volume
from backend.algorithms.geometry import displacement_to_physical, jacobian_determinant, unit_flow_to_voxel

MODEL_NAME = "C2AMorph (LapIRN 계열 3단계 diffeomorphic, LFCAMorph OASIS 가중치)"
DEFAULT_WEIGHTS = Path(__file__).resolve().parent.parent / "models" / "c2amorph" / "MRD_FD_BD_l3_30000.pth"
TRAINED_SHAPE = (160, 192, 224)  # OASIS aligned_norm, nibabel(i, j, k) 순서
NETWORK_SHAPE = (144, 160, 192)
CONFIG = dict(
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


def weights_path() -> Path:
    return Path(os.getenv("C2AMORPH_WEIGHTS", str(DEFAULT_WEIGHTS)))


def status() -> dict:
    """torch 설치, 가중치 파일, 장치 상태를 확인한다. 모델은 불러오지 않는다."""
    path = weights_path()
    try:
        import torch
    except ImportError:
        return {"available": False, "reason": "PyTorch가 설치되지 않았습니다. 서버 venv에 torch를 설치하세요.",
                "weights": path.name}
    if not path.is_file():
        return {"available": False, "reason": f"가중치 파일이 없습니다: {path}", "weights": path.name}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return {"available": True, "reason": "", "weights": path.name, "device": device, "torch": torch.__version__}


def _build_model(torch, device):
    from backend.algorithms import c2amorph_net as net

    net.set_device(device)
    c = CONFIG
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
    state = torch.load(str(weights_path()), map_location=device)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, net


def _load():
    with _lock:
        if "model" in _cache:
            return _cache["torch"], _cache["model"], _cache["net"], _cache["device"]
        info = status()
        if not info["available"]:
            raise ValueError(info["reason"])
        import torch

        device = torch.device(info["device"])
        model, net = _build_model(torch, device)
        digest = hashlib.sha256(weights_path().read_bytes()).hexdigest()[:12]
        _cache.update(torch=torch, model=model, net=net, device=device, digest=digest)
        return torch, model, net, device


def _minmax(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        raise ValueError("밝기 변화가 없는 영상입니다.")
    return (a - lo) / (hi - lo)


class C2AMorph:
    """Moving을 Fixed에 맞추는 diffeomorphic 변형장을 한 번의 추론으로 계산한다."""

    def predict(
        self,
        fixed_path: Path,
        moving_path: Path,
        output_path: Path,
        field_path: Path,
        progress: ProgressCallback = None,
    ) -> dict:
        started = time.perf_counter()
        report(progress, 0.05, "C2AMorph 모델 준비 중")
        torch, model, net, device = _load()
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
            "method": MODEL_NAME,
            "weights": f"{weights_path().name} (sha256 {_cache.get('digest', '')})",
            "device": device.type,
            "input_shape_ijk": list(shape),
            "network_shape": list(NETWORK_SHAPE),
            "runtime_s": round(time.perf_counter() - started, 2),
            "displacement_max_mm": float(magnitude.max()),
            "displacement_mean_mm": float(magnitude.mean()),
            "jacobian_nonpositive_percent": float(np.mean(jac <= 0) * 100.0),
            "notes": notes,
        }
