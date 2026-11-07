# v9 변경 사항

## 기준과 적용 범위

- 입력: 사용자 제공 `medical-web-v8.zip` (SHA-256 `17eee980689c89a286cad18602f4f4a15fb301ca717a759229560b05993022db`).
- 버전: `9.0.0`. 원격에는 `white` 브랜치만 푸시한다. 다른 브랜치와 기존 태그는 유지한다.
- 스타일: `DESIGN_STYLE.md` v2.2. 추가 제공된 텍스트와 ZIP의 규격은 마지막 줄바꿈을 제외하면 동일하다.
- 개정 v8의 메뉴, Deep Learning 모델 선택, Layer Inspector, 평가 지표와 사용자 preset을 반영한다. 세부 변경은 [V8_CHANGES.md](V8_CHANGES.md)에 보존한다.

## 검토 후 수정

- HD95는 양방향 표면 거리 표본을 합친 뒤 95 백분위수를 계산한다. 방향별 백분위수의 최댓값을 쓰던 구현을 수정했다.
- ASSD도 양방향 표본을 합친 평균으로 계산한다. 양쪽 표면 크기가 다르면 방향별 평균을 다시 평균하는 방식과 값이 달라진다.
- 위 두 정의는 [현재 MedPy 공식 구현](https://github.com/loli/medpy/blob/master/medpy/metric/binary.py)을 기준으로 하며, 비대칭 표면의 독립적인 수치 예제를 회귀 테스트에 추가했다. v8 변경 문서의 수식은 입력 버전의 역사적 기록이다.
- 모델 가중치는 `torch.load(..., weights_only=True)`로 읽는다.
- 실행 환경과 소스를 `/data/medical-web-v9`에 배치한다. 기존 실행 DB와 영상의 위치는 유지한다.

## 지정 테스트 자료

| 역할 | OASIS 대상 | 기본 영상 | 평가 라벨 |
|---|---|---|---|
| Fixed | OAS1_0001_MR1 | `aligned_norm.nii.gz` | `aligned_seg35.nii.gz` |
| Moving | OAS1_0010_MR1 | `aligned_norm.nii.gz` | `aligned_seg35.nii.gz` |

- 서버 위치: `/data/test-data/oasis-0001-0010`. 두 대상의 원본·정규화·라벨·단면 파일 24개를 보관한다.
- 기본 정합 영상은 160×192×224, 1mm 격자다. 정합 후 라벨에는 nearest-neighbor 보간을 사용한다.
- Git에는 영상 대신 `tests/data/oasis_pair.json`의 파일명·크기·SHA-256만 기록한다.
- `scripts/verify_oasis_pair.py`는 임시 DB에서 실제 영상 API와 모델을 검증한다. 실제 OASIS 자료를 공개 데모 부서에 등록하지 않는다.

## 검증

- `python -m unittest discover -s tests -v`: 22개 통과. 비대칭 표면 회귀 테스트는 수정 전 HD95 3.8mm로 실패한 뒤, 수정 후 기대값 3.7mm로 통과했다.
- `python scripts/verify_oasis_pair.py --deep-learning`: 통과, 전체 18.42초. 원본 24개 파일의 크기와 SHA-256, 4개 기본 영상의 좌표계, 인증된 영상 API, 정합·변형장·라벨 평가를 검사했다.
- GPU: NVIDIA B200 MIG 1g.45gb, PyTorch 2.7.1+cu128. 모델 실행 7.9초, 입력 160×192×224, 모델 입력 144×160×192. 35개 라벨 모두 지표가 정의됐다.
- 이 한 쌍의 라벨 평균 Dice: 0.609304 → 0.822300, HD95: 3.577671 → 1.810847mm, ASSD: 1.432871 → 0.633988mm. 원본 라벨은 nearest-neighbor로 변형했다. 수치와 범위는 [실행 결과 JSON](docs/verification/v9-oasis.json)에 보관한다.
- 실제 NiiVue 0.42.0 화면: 합성 영상 로드, Registration 모델 상태(cuda), Brain/Vessel 분리, Layer Inspector의 키보드 대비 입력과 잘못된 범위 거부, Jet 컬러맵, 창 이동·Reset 확인. 1440×900에서 문서 높이 900px, JS 오류 0. [검증 화면](docs/verification/v9-ui.jpg).
- Python·JavaScript·셸 문법 및 `git diff --check` 통과. `pip check`: No broken requirements found. 검증 환경은 `requirements-runtime.lock`에 기록한다.
- 추가 제공된 스타일 규격과 ZIP 규격의 차이는 마지막 줄바꿈뿐이었다. 화면 규격 v2.2는 유지했다.

위 영상 결과는 지정된 한 연구용 영상 쌍의 소프트웨어 동작 확인이며, 임상 성능이나 다른 자료에서의 정확도를 검증한 결과가 아니다.
