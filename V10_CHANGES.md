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

- 부서장은 부서 자료의 관리와 진료를 수행한다. 원본 익명화와 관리자 영상 열람 금지는 별개이며, v10은 파일명 익명화를 적용한다.
- 공개 데모의 공유 권한은 보존한다. 기존 작성자를 확인할 수 없는 자료는 관리자에게만 제공한다.
- Region Growing은 SimpleITK Confidence Connected이며 학습 기반 분할은 아니다. 제공되지 않은 Brain/Vessel 학습 가중치를 구현했다고 표시하지 않는다.
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
