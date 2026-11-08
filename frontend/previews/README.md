# 아이콘 예시

아이콘 38개의 실제 NiiVue/FastAPI 조작 화면이다. OASIS 공개 연구용 테스트 영상과 별도 검증 DB를 사용했으며 운영 부서 자료는 촬영하지 않았다.

- `<아이콘 ID>.webm`: 320×180, VP9, 무음, 4초 반복, 1MiB 미만. 툴팁에서 재생한다.
- `<아이콘 ID>.png`: 같은 예시의 정지 화면. 모션 감소 설정에서 사용한다.
- `<아이콘 ID>.gif`: 같은 실제 화면의 GIF. 툴팁의 ‘GIF 내려받기’로 저장한다.

긴 계산은 실제 촬영 프레임을 시간 압축해 4초로 표시한다. 정합·분할 결과와 측정선은 실제 앱이 계산한 것이며 별도로 그린 기능 애니메이션은 사용하지 않았다. 아래쪽 기능명은 예시를 식별하는 자막이다.

## 재생성

Playwright/Chromium, Pillow와 VP9를 지원하는 ffmpeg가 필요하다. 빈 임시 DB로 `scripts/ui_verification_server.py`를 실행한다.

```bash
python scripts/ui_verification_server.py --session-file /tmp/icon-session.json
MEDICAL_UI_SESSION=/tmp/icon-session.json ICON_CAPTURE_DIR=/tmp/icon-capture node scripts/capture_icon_previews.cjs
ICON_CAPTURE_DIR=/tmp/icon-capture python scripts/encode_icon_previews.py
```

`MEDICAL_UI_BASE_URL`은 localhost SSH 터널 주소, `NIIVUE_ESM_PATH`는 공식 NiiVue ESM 캐시, `ICON_FFMPEG`는 ffmpeg 실행 파일 경로다. 촬영기는 완료된 항목부터 재개하며 `CAPTURE_FORCE`에 쉼표로 구분한 아이콘 ID를 지정하면 재촬영한다. 로그인 정보와 원본 촬영 프레임은 Git에 포함하지 않는다.
