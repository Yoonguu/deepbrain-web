# deepbrain-web 작업 지침

- 소스와 변경 이력의 기준 저장소는 `https://github.com/Yoonguu/deepbrain-web`이다. 버전 기록은 8.0.0부터 시작한다.
- 현재 버전은 `VERSION`, 변경 내용과 검증 결과는 `CHANGELOG.md`에 기록한다. 실제 검증한 결과만 통과로 적는다.
- 커밋 메시지는 `feat:`, `fix:`, `docs:`, `chore:` 등 Conventional Commits 형식으로 작성한다. 릴리스 태그는 `v8.0.0`처럼 `v`와 VERSION 값을 조합한다.
- 소스 변경 시 해당 변경에 필요한 검증을 수행한다. 기본 검증 명령은 `python -m unittest discover -s tests -v`이다.
- 실행 중인 컨테이너의 소스 경로는 `/data/medical-web-v7/medical-web`이다. 폴더 이름이 v7이어도 실제 버전은 `VERSION`으로 판단한다. 환경 정보는 `DEPLOYMENT.md`를 참조한다.
- 실행 DB와 업로드 영상은 `MEDICAL_DATA_DIR`에 보관한다. 실행 데이터·개인정보·인증키·환경 파일·로그를 Git에 추가하지 않는다. `examples/medical_web_example.sqlite3`만 기존 합성 설계 예시로 추적한다.
- 원격의 기존 커밋과 로컬 변경을 확인하고 작업한다. 사용자 요청 없이 강제 푸시하거나 기존 이력을 덮어쓰지 않는다.
