# 변경 이력

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
