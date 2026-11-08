# 변경 이력

## v10 아이콘 예시 추가

실제 조작 예시 38개의 GIF·VP9 WebM·PNG, 툴팁 재생과 GIF 다운로드, 모션 감소 PNG 대체를 추가한다.

## v10.0.0 추가 보완

관리/진료 모드 분리와 관리 모드 원본 픽셀 차단, 전경·배경 Seed 지도학습 분할, 실행 대체 없는 38개 아이콘 검증을 추가한다.

## v10.0.0 — 2026-11-08

권한과 자료 소유권, 원본·파생 자료 연결, Registration 3×3 / Segmentation 2×3, 단일 Image 분할, 측정 기록 저장, 공통 초기화와 아이콘 전면 검토를 반영한다. 상세 내용과 제한은 [V10_CHANGES.md](V10_CHANGES.md)를 참조한다.

## 9.0.0 — 2026-11-07

사용자 제공 개정 v8을 기반으로 메뉴·Deep Learning·Layer Inspector·평가 기능을 반영한다. HD95/ASSD 정의를 현재 MedPy 구현과 맞추고, OASIS 0001/0010 테스트 쌍과 `/data` 실행 환경을 지정한다. 세부 검증과 변경은 [V9_CHANGES.md](V9_CHANGES.md)에 기록한다. 적용 대상은 GitHub `white`와 Ubuntu `/data`이며 다른 원격 브랜치는 변경하지 않는다.

## 8.0.0 — 2026-11-07

### 저장소 기록 시작

- `medical-web-v7.zip`의 소스·테스트·문서를 v8의 기준으로 가져왔다.
- 저장소: https://github.com/Yoonguu/deepbrain-web
- `VERSION`과 이 문서를 추가하고, 커밋·태그로 이후 변경을 추적한다.
- 실행 데이터, 업로드 영상, 인증키, 환경 파일, 로그를 `.gitignore`에 등록했다. 기존 합성 예시 DB는 소스 자료로 유지한다.
- Devstream 실행 위치와 버전 관리 절차를 문서에 기록했다.
- 이번 버전은 저장소 관리의 시작점이며 영상 처리와 화면 동작은 v7 소스를 유지한다.

### 기준 소스와 검증

- 입력 ZIP SHA-256: `317e7b3fe57b160d7b0471af8665333782e9e3d2329c72e0490624afdfd2496c`
- Python 3.12, `requirements.txt`의 고정 버전으로 컨테이너 환경 구성.
- 컨테이너에서 `python -m unittest discover -s tests -v`: 15개 통과.
- Devstream 공개 주소 HTTP 200 및 공개 데모 관리자 로그인 확인.
- 선택 의존성인 PyTorch는 아직 설치하지 않아 C2AMorph 모델 추론은 미검증이다.

## 이전 버전

v7 변경은 [V7_CHANGES.md](V7_CHANGES.md), v4 변경은 [V4_CHANGES.md](V4_CHANGES.md)를 참조한다. 이전 버전의 문서는 가져온 시점의 기록으로 보관한다.

## v9 외부 채점 자료 추가 — 2026-11-07

사용자 승인으로 공개 데모와 동일한 OASIS 영상·라벨 4개를 white 브랜치에 포함한다. tests/data/oasis/README.md에 역할과 채점 명령을 기록하고 검증기에 --selected-only 옵션을 추가한다.
