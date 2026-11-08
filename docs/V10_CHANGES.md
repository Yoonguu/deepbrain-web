# v10 변경 및 검증

## 요구사항 적용

| 요구사항 | 변경 |
|---|---|
| 1·2 권한·자료 구조 | 파일 소유권, 의사 본인 자료와 부서장 전체 조회, 본인 삭제, 원본 익명 표시, 입력 관계 저장, 관리자/진료 기능 분리 |
| 3 초기화·선택·휠 | 공통 보기 초기화, 비동기 메뉴 전환 수정, 선택 파일 별도 표시, Zoom 휠 반전 |
| 4 아이콘·표기 | 실제 모드에 따른 neon, 측정 종류 분리, 그리기/지우개/종료 분리, 단일 단면/분할 복귀 분리, A~F 접두어 제거 |
| 5 Mask·Threshold | 지우개·전체 지우기·되돌리기, 연결 영역 라벨과 색상 저장, 합성 추가 비활성화 |
| 6·12 측정·연동 | 현재 영상 인계, 첫 클릭부터 거리선 미리보기, 거리·각도·구형 ROI 저장, 실제 교차 거리선 각도, contrast 연동 |
| 7 워크플로 | 등록→검색→열람→분석→측정→소견→보관 시나리오를 기준으로 검증 |
| 8·9 Registration | 동일 높이 3×3, Fixed/Moving/Warped, 실제 실행 결과에 별도 색상 |
| 10·11 Segmentation | 단일 Image, 원본/결과 2×3, 기존 Brain/Vessel Region Growing 구현 확인 |

## 해석 및 제한

- 부서장은 부서 자료의 관리와 진료를 수행한다. 관리 모드에서는 원본 픽셀 다운로드와 원본 기반 분석을 차단한다. 관리자가 진료하려면 명시적으로 진료 모드로 전환한다. 공개 데모는 기존 공유 승인에 따른 예외다.
- 공개 데모의 공유 권한은 보존한다. 기존 작성자를 확인할 수 없는 자료는 관리자에게만 제공한다.
- 통계적 Region Growing 외에 Seed 기반 지도학습 Logistic Regression을 제공한다. Brain/Vessel 사전 학습 가중치를 사용하는 방식은 아니다.
- Threshold 연결 영역 색상은 원본 intensity를 바꾸지 않는다. 수동 Mask 편집은 255개 라벨 이하로 제한한다.
- 거리선이 화면 투영에서만 겹치면 교차각을 표시하지 않는다. 실제 3D 선분이 0.1mm 이내에서 교차할 때 작은 각도를 표시한다.
- 측정은 영상별로 저장한다. 초기화는 저장된 측정·소견·Mask를 삭제하지 않는다.

## 검증 기록

검증 결과 JSON은 `docs/verification/v10-*.json`에 기록한다. 실행 DB와 브라우저 검증용 로그인 정보는 Git에 넣지 않는다.

- 2026-11-08: Python unittest 30개 통과(17.495초), 선분 교차 기하 검증 5개 통과.
- 실제 NiiVue/FastAPI 브라우저에서 Registration·Region Growing·Threshold, 색상 저장, Mask 편집·되돌리기, 거리·각도·ROI 저장/재조회, 초기화, 비교 화면, 파일 선택창을 확인했다. 브라우저 예외 0개.
- 아이콘 38개를 전수 점검했다. 실행 연결 전수 점검에서는 대상 콜백만 대체하여 연결을 분리 검증했다. 실제 알고리즘 실행은 별도 API·OASIS 검증으로 확인했다.
- OASIS 4개 파일의 크기·SHA-256, 좌표 격자, 인증 다운로드, 실제 라벨 지표, GPU LFCAMorph API 추론·변형장·라벨 변형 검증 통과(19.26초).

## 브라우저 검증 재실행

빈 임시 데이터 디렉터리를 사용하는 `scripts/ui_verification_server.py`로 127.0.0.1:8502에 검증 서버를 실행한다. 운영 DB는 사용하지 않는다.

```bash
python scripts/ui_verification_server.py --session-file /tmp/v10-ui-session.json
# 별도 터미널: Playwright와 Chromium 설치 후
MEDICAL_UI_SESSION=/tmp/v10-ui-session.json node tests/ui/v10_ui_check.cjs
node tests/ui/v10_geometry.mjs
```

`MEDICAL_UI_BASE_URL`로 localhost SSH 터널 주소를 지정할 수 있다. `MEDICAL_UI_OUTPUT_DIR`는 스크린샷과 JSON 출력 위치, `NIIVUE_ESM_PATH`는 공식 NiiVue ESM 캐시 경로다. 검증용 로그인 정보는 세션 파일에만 기록한다.


## 추가 요구사항 재검토

- 일반 부서 관리 모드: 원본 파일명 익명 표시, 원본 픽셀 다운로드·원본 기반 분석 차단. 부서장은 진료 모드 전환 후 진료 가능. 모드 전환은 감사 기록에 남긴다. 공개 데모는 기존 공유 승인을 유지한다.
- 전경/배경 Seed로 영상별 Logistic Regression을 학습한 뒤 전경 Seed에 연결된 성분을 추출하는 분할을 추가한다. Brain/Vessel에 같은 Seed 기반 학습 방식을 제공하며 사전 학습된 해부학 모델로 표기하지 않는다.
- 영상 전환 시 기존 수동 측정점 목록을 비워 서로 다른 영상의 좌표가 섞이지 않게 한다.
- 실행 함수를 대체하지 않고 아이콘 38개의 실제 실행을 검증하는 브라우저 검증으로 교체한다. 기존 연결 전수 검사는 역사적 기록이며 최신 검증 범위는 v10-ui.json을 기준으로 한다.

- Deformable의 Jacobian 계산에서 임시 ITK 영상의 해제된 메모리를 참조할 수 있던 부분을 배열 복사로 수정했다. 실제 OASIS 영상의 Deformable 실행으로 서버 생존과 새 결과 생성을 확인했다.
- 관리/진료 모드의 실제 브라우저 검증: 관리 모드 원본 403, 열기 버튼 비활성, 진료 전환 후 200, 관리 복귀 후 다시 403, 브라우저 예외 0개.
- 추가 검증: `node tests/ui/v10_permission_ui.cjs`. 기존 UI 검증과 같은 환경 변수를 사용한다. `MEDICAL_UI_SWEEP_ONLY=1`은 선행 워크플로 시나리오를 생략하고 실제 아이콘 38개와 ML 분할 검증을 실행한다.

- 최신 추가 검증: backend 32개 통과(15.766초), 실제 아이콘 38개 실행과 Seed 학습 분할 통과, 브라우저 예외 0개. OASIS GPU 및 실제 라벨 평가 검증 통과(19.41초).

- Modality 아이콘은 파일 창 표시뿐 아니라 실제 NIfTI 업로드→DB 등록→두 번째 영상 표시→추가 영상 contrast 초기화까지 확인했다. 초기 로딩 중 미완성 제어기에 접근하지 않도록 준비 완료 후 자료 열기 버튼을 활성화한다.


아이콘 예시 38개를 실제 앱에서 촬영했다. `frontend/previews`에 GIF·VP9 WebM·PNG가 각각 38개 있으며, 툴팁에서 재생하고 GIF를 내려받을 수 있다. 상세 제작 규격은 [예시 안내](../frontend/previews/README.md), 무결성과 검증 기록은 `docs/verification/v10-previews.json`을 참조한다. 모션 감소 설정에서는 PNG를 사용한다.

예시 연결 검증 중 확인한 빈 Segmentation 화면의 null 결과 처리와 MIP 결과 로드 시 단면 중심·확대 초기화도 보완했다.

예시 파일 관련 검증을 포함한 backend 33개 테스트 통과(15.725초). 실제 브라우저에서 WebM 38개 재생, GIF 다운로드, 모션 감소 PNG 표시, 예외 0개를 확인했다.
