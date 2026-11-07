# Deepbrain Web v9 · 디자인 규격 v2.2

버전은 `9.0.0`이며, 제공된 `medical-web-v8.zip`을 검토·수정한 버전입니다. 변경과 검증은 [V9_CHANGES.md](V9_CHANGES.md)에 기록합니다. GitHub 적용 브랜치는 `white`이며, 실제 테스트 영상은 Ubuntu `/data/test-data/oasis-0001-0010`에 보관합니다.

v8 변경과 검증 결과는 [V8_CHANGES.md](V8_CHANGES.md)를 참조하세요. 이전 변경은 V7_CHANGES.md 이하 문서에 남아 있습니다.

Devstream 공개 주소에서 실행하는 방법은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참조하세요.

로그인 화면에 공개 데모 관리자·의사 계정을 표시합니다. 두 계정은 `공개 데모` 부서에만 접근하며 실제 부서 계정·자료와 분리됩니다. 공개 데모 부서에는 환자 자료를 올리지 마세요. 계정 생성·초기화는 `python -m backend.demo_accounts`로 수행합니다.

로컬 실행용 프로토타입입니다. 임상 진료의 정확성·안전성을 검증한 상용 의료기기는 아닙니다. 실제 환자 자료를 넣기 전에 운영 인증·보관 정책과 임상 검증이 필요합니다.

## 실행

Python 3.12 환경에서 실행합니다.

```bash
python -m pip install -r requirements.txt
python -m backend.bootstrap
# 개발용 localhost HTTP에서만:
COOKIE_SECURE=0 python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Uvicorn은 worker 1개로 실행합니다. 여러 worker의 작업 큐를 공유하는 구성은 지원하지 않습니다.

브라우저에서 http://localhost:8000 에 접속합니다. bootstrap은 최초 부서장 계정을 생성하며 기본 비밀번호를 배포하지 않습니다. 다른 의사는 회원가입 후 부서장이 `자료 관리자 → 부서 계정`에서 소속을 확인해야 자료를 볼 수 있습니다. 부서 이름은 동일하게 입력합니다. 다른 부서 부서장은 bootstrap으로 추가합니다.

운영 HTTPS에서는 `COOKIE_SECURE=0`을 사용하지 않습니다. 기본은 Secure 쿠키입니다. 프록시를 사용할 때 Host 및 전달 헤더를 올바르게 구성해야 합니다. 현재 로그인은 최대 7일 유지되며 로그아웃·승인 취소 시 서버에서 세션이 폐기됩니다.

## 사용 순서

1. 로그인 → 자료 관리자에서 `합성 영상 추가` 또는 NIfTI 파일 업로드.
2. 자료를 Fixed/Moving으로 열기 → 상단 영상 보기·Registration·Segmentation(Brain/Vessel)·측정·도구 메뉴.
3. 자료의 `기록` 버튼 → 소견서 공동 수정, 메모 작성. 수정 충돌 시 기존 입력을 남겨 최신 기록과 비교할 수 있습니다.
4. 같은 부서 의사는 공동 열람·작성하고 해당 부서장만 자료를 삭제 목록으로 이동할 수 있습니다. 부서장은 삭제 목록에서 원본 파일과 연결된 결과·소견서·메모를 영구 삭제할 수 있습니다.

권한 거부 사유는 동작 영역 아래에 표시합니다. 220ms 흔들림은 한 번만 실행하며 모션 감소 설정에서는 실행하지 않습니다. 로그인 전에는 업무 화면 HTML·자료 API가 제공되지 않습니다.

## 영상 기능

| 문서 번호 | v3 구현 |
|---|---|
| F1 | NiiVue MPR: Axial / Coronal / Sagittal |
| F2 / F11 | Axial slab 범위 선택 후 실제 최대값 투영 작업 |
| F3 | Volume rendering, 마우스로 회전 |
| F4 | VersorRigid3D + Diffeomorphic Demons, Deep Learning 모델 선택(LFCAMorph OASIS) |
| F5 | Fixed/Moving Overlay, 불투명도 조절 |
| F6 | Hessian/Sato vesselness, Confidence Connected, Threshold, 수동 Mask |
| F7 | 동일 영상의 세 단면 Linked crosshair |
| F8 | 같은 MPR volume과 비교 패널의 위치·Pan/Zoom·Window/Level 동기화 |
| F9 | 단면 더블클릭 확대 및 MPR 복귀 |
| F10 | 자동 / 세로 / 가로 / 2×2 / 3×3 Axial mosaic |
| F12 | 거리, 세 점 각도, 구형 ROI 평균·표준편차·부피, 비영점 Mask 부피 |
| F13 | Seed 초기화 Geodesic Active Contour |
| F14 | 양수 수동 Mask의 Axial slice 간 signed-distance 보간 |
| F15 | 여러 NIfTI modality Overlay + Fixed/Moving/마지막 결과 독립 패널 비교 |

Deep Learning 목록의 LFCAMorph(LPBA40), VoxelMorph, HyperMorph는 가중치를 받지 않아 준비 중으로 표시됩니다. 실제 제조사 알고리즘과 같은 구현이라는 의미는 아닙니다. 임의 oblique slab, 4D 처리, PACS/DICOM 직접 수신은 아직 포함하지 않았습니다. 비교 화면은 Fixed/Moving/마지막 결과의 최대 세 패널입니다. 첨부 문서의 설명용 GIF는 제작하지 않았습니다.

Mask 보간은 일부 Axial slice만 그린 binary mask를 대상으로 합니다. Mask 그리기 → Mask 저장 → 자료 관리자에서 Mask를 Fixed로 열기 → Run Interpolation 순서입니다. Active Contour는 첫 Seed와 Radius/Iterations를 사용합니다. 측정은 Fixed에 표시된 점만 기록하며 ROI는 구형입니다. 비영점 부피를 원본 강도 영상에서 병변 부피로 해석하지 마세요.

NiiVue 0.42.0은 기존과 동일하게 jsDelivr에서 로드하므로 브라우저 인터넷/WebGL2가 필요합니다. 입력은 256MiB 이하의 단일 성분 3D NIfTI입니다. 장비가 내보낸 DICOM 입력과 PACS 자동 연결은 후속 작업입니다.

## DB 및 보관

실행 DB는 `data/medical.sqlite3`, 영상은 `data/images/`입니다. `MEDICAL_DATA_DIR`로 위치를 바꿀 수 있습니다. DB는 서버만 열며 웹에 직접 제공하지 않습니다. 승인된 부서 소속과 역할을 요청마다 검사합니다. SQLite 본체는 퍼블릭 도메인이며 상업적 사용에 별도 라이선스가 필요하지 않습니다: https://www.sqlite.org/copyright.html

`examples/`의 가상 DB는 구조 설명용이며 실제 계정·영상은 아닙니다. 실행 DB와 분리되어 있습니다. 운영에서는 가입 검증, 백업·암호화, 복구, 세션 정책과 동시 쓰기 규모에 맞는 DB 운용을 추가 검토해야 합니다.

## 디자인 규격 v2 적용

DESIGN_STYLE.md가 기준입니다. body grid가 header·메뉴·아이콘 줄·main 높이를 나눕니다. 상단 메뉴 순서와 기존 요소 ID를 유지하고 30개 inline SVG 도구, 중첩 툴팁, 우클릭 250ms 방사형 메뉴를 추가했습니다. 오른쪽 버튼을 누른 뒤 250ms 이내 5px 이상 이동하면 기존 NiiVue 드래그로 전달합니다. Esc로 메뉴와 툴팁을 닫습니다.

고정 최대 6개와 도구 사용 횟수는 세션 사용자별 SQLite preferences에 저장됩니다. 예시 영상은 별도 제작 대상입니다. frontend/previews/<아이콘 id>.webm 또는 .png 파일을 배치하면 인증된 사용자에게만 제공되며, 없는 경우 '예시 준비 중'을 표시합니다. 모션 감소 설정에서는 아이콘·툴팁·메뉴·거부 효과를 끕니다.

자료 관리자 왼쪽 `작업 이력 → 상태 확인`에서 최근 100개 부서 작업을 확인합니다. 서버 재시작 당시 실행 중이던 작업은 실패와 재시작 사유로 표시되며 자동 재실행하지 않습니다.

## 검증

```bash
python -m unittest discover -s tests -v
```

합성 영상으로 인증/CSRF/부서 격리/소견서 버전 충돌/삭제 권한과 영상 처리 API를 검사합니다. 실제 MRI의 알고리즘 정확성을 증명하는 검사가 아닙니다.


## Deep Learning 실행

Registration 메뉴의 F. Deep Learning에서 모델을 고릅니다. 실행 가능한 모델은 LFCAMorph(OASIS)이며 LapIRN 계열 3단계 diffeomorphic 정합입니다. PyTorch가 있어야 동작합니다. 가중치 경로는 `backend/models/lfcamorph/MRD_FD_BD_l3_30000.pth`이며 환경 변수 `LFCAMORPH_OASIS_WEIGHTS`로 바꿀 수 있습니다.

```bash
/home/ubuntu/venvs/medical-web/bin/python -m pip install -r requirements-dl.txt
# GPU가 없으면: /home/ubuntu/venvs/medical-web/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

입력 두 영상은 같은 물리 공간에 정렬되어 있어야 하며, 학습 데이터는 OASIS aligned_norm(160×192×224)입니다. 다른 크기나 다른 전처리의 영상은 결과 notes에 경고가 표시되고 정확도를 보장하지 않습니다.

## 평가 지표

Registration과 Segmentation의 평가 섹션에서 Dice, HD, HD95, ASD, ASSD를 체크박스로 고릅니다. 표면 거리 정의는 medpy.metric.binary와 같고 단위는 voxel spacing을 반영한 mm입니다. 거리 변환은 scipy(`requirements.txt`)를 쓰며, scipy가 없으면 SimpleITK SignedMaurerDistanceMap으로 대신 계산합니다. 한쪽 Mask가 빈 label은 Dice 0, 거리 지표는 정의되지 않음으로 표시합니다.
