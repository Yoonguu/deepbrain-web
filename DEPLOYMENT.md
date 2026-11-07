# Devstream 접속

## v9 실행 환경

- GitHub 대상: `white` 브랜치.
- 소스: `/data/medical-web-v9/medical-web`
- Python: `/data/medical-web-v9/.venv/bin/python`
- 기존 실행 데이터: `/data/medical-web-v7/medical-web/data` (`MEDICAL_DATA_DIR`로 명시).
- 서버 로그/PID: `/data/medical-web-v9/server.log`, `/data/medical-web-v9/server.pid`.
- 연구용 테스트 파일: `/data/test-data/oasis-0001-0010`. 공개 데모 DB와 분리한다.

```bash
cd /data/medical-web-v9/medical-web
bash scripts/run_persistent_devstream.sh
```

컨테이너 재시작 시 서버 프로세스는 다시 실행해야 한다. 가상환경은 같은 Python 3.12·Ubuntu 컨테이너의 `/data`에 보관하며, 이미지나 Python 버전이 바뀌면 `requirements.txt`와 `requirements-dl.txt`로 재구성한다. NVIDIA B200 환경은 CUDA 12.8용 PyTorch wheel을 사용한다. 검증된 전체 의존성은 `requirements-runtime.lock`에 보관한다. ITK 5.4.7 wheel의 Tag 메타데이터와 최신 pip의 검사 오류를 피하기 위해 패키지 도구는 검증된 pip 24.0을 사용한다.

```bash
/data/medical-web-v9/.venv/bin/python -m pip install pip==24.0
/data/medical-web-v9/.venv/bin/python -m pip install -r requirements-runtime.lock
/data/medical-web-v9/.venv/bin/python -m pip install -r requirements-dl.txt --index-url https://download.pytorch.org/whl/cu128
/data/medical-web-v9/.venv/bin/python -m unittest discover -s tests -v
/data/medical-web-v9/.venv/bin/python scripts/verify_oasis_pair.py --deep-learning
```

아래 안내는 원래 패키지의 프록시 설명과 이전 설치 예시다. 현재 실행은 위 경로를 사용한다.

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
