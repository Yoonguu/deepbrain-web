# v7 변경·검증 기록

## 수정

| 구분 | 내용 |
|---|---|
| 로그인 제한 | IP 단위 공유 제한을 없애고 계정(email) 단위로 바꿈. 최근 60초 실패 12회 이상일 때만 막고, 성공하면 기록을 지움. 프록시 뒤에서 한 사람의 실패가 다른 사용자를 막지 않음 |
| Active contour | speed image 식 반전 수정. ITK Software Guide 기준대로 seed 주변 gradient 중앙값(K1)과 전경 90 percentile(K2)로 alpha = -(K2-K1)/6, beta = (K1+K2)/2, 출력 1→0. 반복 횟수는 `contourIter`(기본 300)로 분리. Fixed에서 찍은 seed만 허용 |
| MIP·보간 축 | 파일 k축 고정 대신 direction 행렬에서 S축에 가장 가까운 index 축을 Axial로 사용. OASIS aligned는 j축. 2D 거리 지도에 실제 spacing 반영 |
| Deformable | Rigid(VersorRigid3D) → Histogram matching → Diffeomorphic Demons. 최종 영상은 Rigid와 변위장을 합성해 원본에서 한 번만 resample. Jacobian ≤ 0 비율과 변위 크기를 결과에 표시 |
| 실패 원인 | ValueError 사유를 그대로 표시(v6 유지), 실패 시 .tfm·변형장 파일도 정리 |
| 측정·입력 검증 | 좌표 길이 3 고정(어긋나면 422), radius 상한 10으로 통일, Threshold 하한 > 상한 거부 |
| Threshold 기본값 | Fixed를 열 때 영상의 robust 최소~최대 범위로 자동 설정. 사용자가 고친 값은 유지 |
| 보기 초기화 | Pan·Zoom과 함께 Window/Level도 처음 값으로 복원 |
| 파일 | `/api/transforms/{id}.tfm`, `/api/fields/{id}.nii.gz` 다운로드 추가. 영구 삭제 시 .tfm·변형장 파일과 해당 작업 이력도 삭제 |
| Dice | `DiceEvaluator` 구현. 정수 label 영상이면 label별 Dice(한쪽에만 있는 label은 0점), 아니면 전경 Dice |
| 툴팁 | 기능별 개념 용어 30종, 하위 툴팁 유지 오류 수정, 클릭 안내가 현재 조작 모드를 따름, 방사형 메뉴 툴팁을 펼침 바깥쪽에 배치, 존재하는 예시 영상만 요청하고 1시간 캐시 |
| 아이콘 | hover 움직임을 선 그리기(stroke-dashoffset)로 통일 |

## C2AMorph(F)

공개 문헌에서 C2AMorph라는 이름의 모델은 찾지 못했다. 사용자가 제공한 LFCAMorph(HMCN) 코드와 OASIS 가중치를 근거로, LapIRN(Mok & Chung, MICCAI 2020) 계열 3단계 diffeomorphic 정합으로 구현했다.

| 항목 | 내용 |
|---|---|
| 네트워크 | `backend/algorithms/c2amorph_net.py`. LFCAMorph.py에서 `.cuda()` 15곳을 장치 변수로 바꾸고, 누락된 Functions.py의 grid 함수를 LapIRN 공식 코드(commit c17fb75)로 넣음. 구조와 계산식은 원본과 같음 |
| 설정 | MRD_diff, doubleF/B, multi_attn, attn_batch, multiple, concat='e0', ch 6×2, range_flow 0.1, 입력 144×160×192 |
| 가중치 | `backend/models/c2amorph/MRD_FD_BD_l3_30000.pth` (sha256 5ec6f677ae7f…). `C2AMORPH_WEIGHTS`로 경로 변경 가능 |
| 출력 | warp된 Moving(Fixed 격자), 물리 좌표(LPS, mm) 변위장, Jacobian ≤ 0 비율, 변위 크기, 실행 시간 |
| 의존성 | torch(선택). 없으면 `/api/c2amorph/status`가 사유를 알리고 F는 비활성 |

## 검증

| 검증 | 결과 |
|---|---|
| 모델 구조 대조 | 설정대로 만든 모델의 파라미터·버퍼 573개가 체크포인트 573개와 이름·크기까지 일치. concat, 채널 배수, attention 종류를 바꾼 음성 대조 3건에서는 각각 90건, 405건, 150건 불일치 |
| `tests/test_geometry.py` | 10건 통과 (numpy만 사용) |
| 브라우저 시나리오 | NiiVue와 API를 대체한 Chromium 실행에서 16개 항목 통과, JavaScript 오류 0건. 문서 높이 900px, 툴팁 100ms 표시·1000ms 삭제, 하위 툴팁, 방사형 메뉴 16개·모서리 15개 |
| `tests/test_v3.py` | v7 수정 검사 추가. 이 작업 환경에는 fastapi·SimpleITK가 없어 서버에서 실행해야 함 |

C2AMorph의 실제 추론과 SimpleITK 처리 경로는 torch·SimpleITK가 있는 서버에서 `python -m unittest discover -s tests -v`와 OASIS 영상으로 확인해야 한다.
