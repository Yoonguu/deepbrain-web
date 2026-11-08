# Deepbrain Web v10

버전 `10.0.0`. GitHub 대상은 `white`, Ubuntu 소스는 `/data/medical-web-v10/medical-web`이다. 변경 내용은 [V10_CHANGES.md](V10_CHANGES.md), 실행 방법은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참조한다.

## 사용 흐름

1. 자료 관리자에서 NIfTI 영상(.nii/.nii.gz)을 등록한다. 등록된 선택 상태는 파일 선택창과 별도로 유지된다.
2. Registration은 Fixed·Moving을 선택한다. 3행(Fixed/Moving/Warped) × 3열(X/Sagittal, Y/Coronal, Z/Axial)로 표시하며 결과는 다른 colormap으로 구분한다.
3. Segmentation은 Image 하나를 선택한다. 원본과 분할 결과를 2행 × 3열로 표시한다. Brain·Vessel의 분할 방식은 Confidence Connected와 전경·배경 Seed로 학습하는 Logistic Regression 중 선택한다. 사전 학습된 해부학 모델은 아니다. Vesselness는 연속값 혈관 강조 결과다.
4. 측정·도구는 현재 열린 영상을 이어받는다. 거리(두 클릭), 각도(세 클릭), 구형 ROI(한 클릭)를 선택하며 완료한 기록은 영상별로 DB에 저장된다. 거리선이 실제 3D 공간에서 교차하면 작은 교차각을 표시한다. Esc는 진행 중인 측정만 취소한다.
5. 소견 작성 버튼에서 자료에 연결된 소견서·메모를 작성하고 수정 이력을 확인한다.

보기 초기화는 모든 화면의 상단에서 접근하며 이동·확대·단면·배치·contrast·colormap을 최초 로드 상태로 복구한다. Mask 전체 지우기는 별도 동작이며 되돌리기를 지원한다. 합성 영상 추가는 비활성화되어 있다.

## 권한과 자료 관계

| 사용자 | 조회·진료 | 삭제 |
|---|---|---|
| 부서장 | 해당 부서 전체 자료·소견·작업 | 부서 자료를 휴지통으로 이동, 영구 삭제 |
| 승인된 의사 | 본인 자료와 공개 데모 자료 | 본인 자료만 휴지통 이동. 다른 작성자 결과가 연결된 경우 관리자에게 요청 |
| 다른 부서·미승인 사용자 | 접근 불가 | 접근 불가 |

관리 기능과 진료 기능은 별개이며 부서장도 분석·측정·소견 작성을 수행한다. 원본 보기는 원본만, 전체 자료는 원본과 파생 자료의 입력 관계를 표시한다. 정합 결과는 Fixed와 Moving 모두에 연결된다.

새 일반 부서 원본은 `영상-<식별자>.nii.gz`로 표시한다. 기존 파일의 작성자는 업로드 감사 기록으로 복원하고, 확인할 수 없는 기존 자료는 부서장에게만 제공한다. 공개 데모는 기존 공유 범위를 유지한다. 일반 부서의 관리 모드는 원본 픽셀 열람·원본 기반 분석을 차단한다. 관리자는 상단 버튼으로 진료 모드로 전환해 진료를 수행한다. 공개 데모는 공유 예외다.

## 표시·편집

- 활성 아이콘은 실제 도구 상태에 맞춰 파란 neon으로 표시한다. 거리·각도·ROI, 그리기·지우개, 단일 단면·분할 보기 복귀를 각각 구분한다.
- Threshold는 서로 연결된 영역을 별도 라벨로 만들고, 영역별 색상을 저장할 수 있다. 최대 65,535개 영역을 지원한다.
- 수동 Mask 편집은 NiiVue의 8비트 drawing을 사용해 최대 255개 라벨을 지원한다. 초과 시 이유를 표시한다.
- 일반 휠은 단면 이동이다. Pan/Zoom 모드 또는 Ctrl+휠은 방향을 반전한 확대·축소다.
- Contrast·colormap 설정은 동일 영상과 표시 그리드에 연동한다.

## 실행과 검증

Python 3.12 및 `requirements.txt`를 준비한다. GPU 모델은 `requirements-dl.txt`와 환경에 맞는 PyTorch가 필요하다.

```bash
python -m pip install -r requirements.txt
python -m backend.bootstrap
COOKIE_SECURE=0 python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
python -m unittest discover -s tests -v
python scripts/verify_oasis_pair.py --data-root tests/data/oasis --selected-only --deep-learning --output /tmp/oasis-grading.json
```

운영 HTTPS는 기본 Secure 쿠키를 유지한다. 공개 데모 계정은 로그인 화면에 표시한다. 공개 데모와 실제 부서 자료는 분리된다. 프로토타입의 임상 정확성은 별도 검증 대상이다.

외부 채점용 OASIS 영상·라벨 4개는 [tests/data/oasis](tests/data/oasis/README.md)에 있다. 다른 실행 영상·DB·인증 정보는 Git에 포함하지 않는다.

과거 버전 기록: [v9](V9_CHANGES.md), [v8](V8_CHANGES.md), [v7](V7_CHANGES.md).
