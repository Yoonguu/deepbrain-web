# Devstream v10 실행

- GitHub 브랜치: `white`
- 소스: `/data/medical-web-v10/medical-web`
- Python: `/data/medical-web-v10/.venv/bin/python` (검증된 v9의 `/data` 가상환경 재사용)
- 실행 데이터: `/data/medical-web-v7/medical-web/data` (`MEDICAL_DATA_DIR`로 명시)
- 로그·PID: `/data/medical-web-v10/server.log`, `/data/medical-web-v10/server.pid`
- 테스트 자료: 저장소의 `tests/data/oasis` 4개 또는 `/data/test-data/oasis-0001-0010`

```bash
cd /data/medical-web-v10/medical-web
bash scripts/run_persistent_devstream.sh
```

터미널과 독립적으로 실행하려면 동일 서버가 8501 포트에서 실행 중인지 먼저 확인한 뒤 다음 명령을 사용한다.

```bash
cd /data/medical-web-v10/medical-web
nohup bash scripts/run_persistent_devstream.sh > /data/medical-web-v10/server.log 2>&1 < /dev/null &
echo $! > /data/medical-web-v10/server.pid
```

공개 주소: https://devopen-gpu.jntp-ax.or.kr/i/AIe6VDTVQZhnrMam/

컨테이너에서 제공하는 `DEVSTREAM_BASE_URL_8501`, `DEVSTREAM_EXTERNAL_ORIGIN_8501`을 사용한다. `backend.devstream:application`이 프록시 경로를 처리하므로 Uvicorn `--root-path`는 추가하지 않는다. 컨테이너 재시작 후에는 서버 프로세스를 다시 시작해야 한다.

v10 적용 전 SQLite backup API로 실행 DB를 백업한다. 파일 소유권과 입력 관계는 새 테이블에 추가하며 영상 파일은 이동·삭제하지 않는다. 알 수 없는 기존 소유자는 추측해 다른 의사에게 배정하지 않는다. 공개 데모 공유는 유지한다.

## 검증

```bash
cd /data/medical-web-v10/medical-web
/data/medical-web-v10/.venv/bin/python -m unittest discover -s tests -v
/data/medical-web-v10/.venv/bin/python scripts/verify_oasis_pair.py --data-root tests/data/oasis --selected-only --deep-learning --output /tmp/v10-oasis.json
```

기존 가상환경은 같은 Python 3.12/Ubuntu 환경에서 재사용한다. NVIDIA B200의 GPU 추론에는 검증된 PyTorch 2.7.1+cu128을 사용한다. 환경 재구성은 `requirements-runtime.lock`, `requirements-dl.txt`를 참조한다.
