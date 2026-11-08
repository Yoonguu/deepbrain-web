# deepbrain-web 작업 지침

- 소스와 변경 이력의 기준 저장소는 `https://github.com/Yoonguu/deepbrain-web`이다. 버전 기록은 8.0.0부터 시작한다.
- 현재 버전은 `VERSION`, 변경 내용과 검증 결과는 `CHANGELOG.md`에 기록한다. 실제 검증한 결과만 통과로 적는다.
- 커밋 메시지는 `feat:`, `fix:`, `docs:`, `chore:` 등 Conventional Commits 형식으로 작성한다. 릴리스 태그는 `v8.0.0`처럼 `v`와 VERSION 값을 조합한다.
- 소스 변경 시 해당 변경에 필요한 검증을 수행한다. 기본 검증 명령은 `python -m unittest discover -s tests -v`이다.
- 사용자가 승인한 변경만 수행한다. 이번 v10 작업은 사용자의 1회 권한으로 진행한다. 후속 작업은 새 요청의 권한 범위를 확인한다.
- v10의 원격 대상은 `white` 브랜치뿐이다. `main`, `deep-learning` 및 다른 원격 브랜치를 변경하지 않는다. 승인 없이 새 원격 브랜치나 태그를 만들지 않는다.
- 실행 중인 컨테이너의 v10 소스 경로는 `/data/medical-web-v10/medical-web`이다. 버전은 `VERSION`으로 판단한다. GitHub의 white 브랜치와 Ubuntu /data에 같은 소스를 적용하고 기존 실행 데이터는 보존한다. 환경 정보는 `DEPLOYMENT.md`를 참조한다.
- 테스트 자료는 `/data/test-data/oasis-0001-0010` 아래 OASIS 0001(Fixed), 0010(Moving)이다. 기본 영상은 `aligned_norm.nii.gz`, 평가 라벨은 `aligned_seg35.nii.gz`다. 파일 무결성 목록은 `tests/data/oasis_pair.json`을 참조한다.
- 실행 DB와 업로드 영상은 `MEDICAL_DATA_DIR`에 보관한다. 실행 데이터·개인정보·인증키·환경 파일·로그를 Git에 추가하지 않는다. `examples/medical_web_example.sqlite3`만 기존 합성 설계 예시로 추적한다.
- 원격의 기존 커밋과 로컬 변경을 확인하고 작업한다. 사용자 요청 없이 강제 푸시하거나 기존 이력을 덮어쓰지 않는다.

- 사용자가 외부 채점용으로 승인한 예외: `tests/data/oasis`의 0001·0010 대상별 aligned_norm.nii.gz와 aligned_seg35.nii.gz, 총 4개 파일은 Git에 추적한다. 그 밖의 영상과 실행 DB는 계속 제외한다.
