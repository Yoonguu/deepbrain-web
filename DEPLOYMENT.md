# Devstream 접속

## 현재 설치 상태 (2026-11-07)

- SSH 별칭: `ff9ebb72-6ae84c0c.hackathon`, 사용자: `ubuntu`
- 소스: `/data/medical-web-v7/medical-web`
- Python: `/home/ubuntu/venvs/medical-web-v7/bin/python`
- 실행 데이터: `/data/medical-web-v7/medical-web/data`
- 현재 서버 로그: `/data/medical-web-v7/server.log`
- 현재 서버 PID 기록: `/data/medical-web-v7/server.pid`

기존 설치 폴더 이름을 유지하며, 버전은 `VERSION`으로 관리합니다. SSH 키는 로컬 SSH 설정에서만 관리하고 저장소에 넣지 않습니다.

서버가 중지되어 8501 포트를 사용하지 않을 때, 컨테이너 터미널에서 다음 명령으로 실행합니다. 실행 중인 서버가 있다면 중복 실행하지 않습니다.

```bash
cd /data/medical-web-v7/medical-web
export PYTHON_BIN=/home/ubuntu/venvs/medical-web-v7/bin/python
export MEDICAL_DATA_DIR=/data/medical-web-v7/medical-web/data
bash run_devstream.sh
```

`/data`의 프로젝트와 데이터는 보존할 저장 위치이며, 홈 디렉터리의 Python 가상환경은 컨테이너 재생성 시 다시 구성해야 할 수 있습니다. GitHub에는 소스·문서·테스트와 명시된 합성 예시만 기록합니다.

## 프록시와 기존 실행 안내

이 버전은 이 Ubuntu 컨테이너의 8501 포트로 연결되는 공개 경로에서 실행합니다.

**접속 주소:** https://devopen-gpu.jntp-ax.or.kr/i/AIe6VDTVQZhnrMam/

컨테이너에서 환경 변수 `DEVSTREAM_BASE_URL_8501`과 `DEVSTREAM_EXTERNAL_ORIGIN_8501`이 제공됩니다. 해당 경로가 프록시에서 그대로 전달되므로 `backend.devstream:application`이 경로 앞부분을 제거한 뒤 FastAPI에 전달합니다. Uvicorn의 `--root-path` 옵션을 추가하지 않습니다.

```bash
cd /home/ubuntu/medical-web/v5/medical-web
export PYTHON_BIN=/home/ubuntu/venvs/medical-web/bin/python
./run_devstream.sh
```

이 실행에서는 `data/`에 계정 DB와 영상이 보관됩니다. `MEDICAL_DATA_DIR`을 설정하면 저장 위치를 바꿀 수 있습니다. 최초 부서장 계정은 같은 저장 위치를 지정해 다음 명령으로 생성합니다. 기본 계정과 비밀번호는 포함하지 않았습니다.

```bash
cd /home/ubuntu/medical-web/v5/medical-web
MEDICAL_DATA_DIR="$PWD/data" /home/ubuntu/venvs/medical-web/bin/python -m backend.bootstrap
```

공개 페이지에서는 로그인·회원가입만 보입니다. 가입한 의사는 부서장이 소속을 승인한 후 같은 부서 자료를 열 수 있습니다. HTTPS에서 세션 쿠키는 Secure로 발급됩니다. 컨테이너가 다시 시작되면 실행 명령을 다시 호출해야 합니다. 실제 환자 자료를 운영 환경에 넣기 전에는 인증 체계, 접근 기록, 데이터 백업·암호화 및 의료기기 검증이 필요합니다.
