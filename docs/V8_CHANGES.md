# v8 변경 사항

피드백 4개 항목과 C2AMorph 삭제 요청을 반영했다. 디자인 규격은 DESIGN_STYLE.md v2.2로 개정했다.

## 1. 화면 구성

| 피드백 | v8 반영 |
|---|---|
| header 부제 삭제 | `A Registration · B Viewer · D Vessel · E Region growing · F C2AMorph(미수신)` 문구와 CSS 삭제 |
| Registration에서 D, E 제거 | Registration 메뉴는 영상 불러오기, A. Registration, F. Deep Learning, 평가, 결과만 표시 |
| F C2AMorph → Deep Learning | `dlSection`에 모델 선택(`dlModel`), 모델 설명, 상태, `Run Deep Learning` |
| 평가 지표 선택 | Dice, HD, HD95, ASD, ASSD 체크박스. 예측·기준 영상(Fixed, Moving, 마지막 결과) 선택. label별 표 |
| Segmentation 하위 메뉴 | 상단 메뉴 Segmentation 뒤에 Brain, Vessel 하위 메뉴. Brain은 E, Mask 도구, 평가. Vessel은 D, E, Mask 도구, 평가 |
| D는 Vessel에만 | D 섹션과 `icon-seg-vessel`은 Seg-Vessel에서만 보이며 방사형 메뉴에서도 Seg-Vessel에서만 후보가 된다 |
| 측정·도구 정리 | 영상 불러오기, A, D, E, F, 평가 제거. 영상 도구, Layer Inspector, 결과만 표시. 대상 영상은 `toolTarget`에 표시 |
| ITK-SNAP Colormap·Contrast | 떠 있는 Layer Inspector 창(Contrast, Color Map, Info 탭) |
| C2AMorph 삭제 | 화면, API(`/api/c2amorph`, `/api/c2amorph/status`), 아이콘 `icon-reg-c2amorph`, 모듈 이름 모두 삭제 |

메뉴별로 섹션을 나누면서 기존에 측정·도구 섹션에 있던 버튼의 위치를 옮겼다. Deformable과 Moving 겹쳐 보기는 아이콘 그룹이 reg이므로 A. Registration으로, Threshold, Active contour, Mask 그리기, 보간은 아이콘 그룹이 seg이므로 Segmentation의 Mask 도구 섹션으로 옮겼다. 요소 ID는 유지했다.

## 2. Deep Learning

| 항목 | 내용 |
|---|---|
| 모듈 | `backend/algorithms/dl_models.py`(모델 목록, 상태, 추론), `backend/algorithms/lfcamorph_net.py`(v7 `c2amorph_net.py`의 이름만 바꾼 네트워크 정의) |
| 가중치 | `backend/models/lfcamorph/MRD_FD_BD_l3_30000.pth`, 환경 변수 `LFCAMORPH_OASIS_WEIGHTS` |
| 목록 | LFCAMorph(OASIS) 실행 가능(torch 필요). LFCAMorph(LPBA40), VoxelMorph(OASIS, LPBA40), HyperMorph(OASIS)는 가중치 미수신이라 `준비 중`으로 선택 불가 |
| API | `GET /api/dl/models`, `POST /api/deep-learning` 본문 `{fixed_id, moving_id, model_id}`. 미등록 모델 400, 사용 불가 모델 503 |
| 검증 | 가짜 torch 구조 검사에서 모델 tensor 573개와 checkpoint tensor 573개의 이름·shape 일치(누락 0, 초과 0, shape 불일치 0) |

## 3. 평가 지표

| 지표 | 정의(medpy.metric.binary와 동일) |
|---|---|
| Dice | 2|P∩R| / (|P| + |R|) |
| HD | max(max d(P→R), max d(R→P)) |
| HD95 | max(95 percentile d(P→R), 95 percentile d(R→P)) |
| ASD | mean d(P→R) |
| ASSD | (mean d(P→R) + mean d(R→P)) / 2 |

d(A→B)는 A 표면 voxel에서 B 표면까지의 최소 Euclidean 거리이며 voxel spacing을 반영한 mm 단위다. 표면은 6-이웃 erosion 1회를 뺀 voxel이고 영상 밖은 배경이다. 계산은 두 mask 합집합의 bounding box에 0 테두리 1 voxel을 붙여 잘라서 한다. 두 표면이 모두 box 안에 있으므로 거리값은 자르기 전과 같다. 한쪽 mask가 빈 label은 Dice 0, 거리 지표 None(화면 표기 `정의되지 않음`)과 사유를 돌려준다.

API는 `POST /api/tools/evaluate` 본문 `{prediction_id, reference_id, metrics}`다. v7의 `POST /api/tools/dice`는 같은 계산의 Dice 전용 경로로 남겼다. 거리 변환은 scipy `distance_transform_edt`를 쓰며 `requirements.txt`에 `scipy>=1.11`을 추가했다. scipy가 없으면 SimpleITK SignedMaurerDistanceMap으로 대신 계산한다.

## 4. Layer Inspector

| 탭 | 항목 |
|---|---|
| Contrast | Min, Max, Level, Window, Reset(전체 범위), Auto(1~99 percentile), histogram(Bins, Cutoff, Log), 끌 수 있는 곡선 control point, Point·x·y 입력, +/− |
| Color Map | Preset(Gray, Jet, Hot, Cool, 사용자 저장), 체크무늬 위 colormap 미리보기, opacity 선, Point·Position·Opacity·Color·Style(Regular, Two-sided)·Side(Left, Right), +/− |
| Info | Size, Spacing, Origin, Direction, Data type, 밝기 범위, 표시 범위, NaN voxel 수 |

곡선과 colormap을 256칸 LUT 하나로 합쳐 NiiVue custom colormap으로 등록하고 cal_min·cal_max에 Min·Max를 넣는다. NiiVue 0.42.0 태그가 저장소에 없어 앞뒤 버전 0.41.1과 0.43.2 소스에서 `addColormap`, `setColormap`, `onIntensityChange`, `updateGLVolume`, `NVImage.colormap` 동작을 확인했다. 두 버전 모두 colormap을 지정하면 `calMinMax()`가 cal 범위를 다시 계산하므로 지정 뒤 Min·Max를 다시 넣는다. NaN voxel 색은 NiiVue가 지원하지 않아 입력을 비활성으로 두고 사유를 표시한다.

사용자 preset은 `GET/PUT/DELETE /api/preferences/colormaps/{이름}`으로 서버 DB `colormap_presets` 표에 저장한다.

## 5. 아이콘과 고정 설정

아이콘은 33개다. reg에 `icon-reg-dl`, `icon-reg-eval`, tool에 `icon-tool-contrast`, `icon-tool-colormap`을 추가하고 `icon-reg-c2amorph`를 삭제했으며 `icon-seg-dice`는 `icon-seg-eval`로 바꿨다. v7에서 저장한 고정·사용 횟수에 삭제된 id가 있으면 `GET /api/preferences`가 걸러서 돌려준다.

## 6. 검증

| 검사 | 결과 |
|---|---|
| `python -m unittest tests.test_geometry` | 15개 통과. 표면 거리 지표를 정의 그대로 쓴 전수 비교 구현과 scipy·전수 거리 변환 두 경로로 비교, 3 voxel 이동(x spacing 1.5mm) HD 4.5mm·Dice 0.7 확인 |
| 가짜 NiiVue·가짜 API Playwright 점검 | 메뉴별 섹션, Seg-Brain에서 vessel 제외(아이콘 줄, 방사형 메뉴), Deep Learning 목록, 평가 표, Inspector LUT 값(직선 128→128, 곡선 점 (0.5, 0.8)에서 64·128·192칸 103·205·230, Jet 0칸 투명·255칸 (128,0,0)), Max ≤ Min 거부, 우클릭 W/L 동기화, preset 저장·삭제, 창 이동, 보기 초기화, 재로드 시 설정 유지 확인. JS 오류 0, 1440×900 문서 높이 900px |
| v7 툴팁·방사형 메뉴 회귀 점검 | 표시 100ms, 중첩 툴팁 유지, 1000ms 삭제, 방사형 메뉴 16칸·모서리 15칸 모두 통과 |
| `tests/test_v3.py` | `test_v8_features` 추가(모델 목록, 503·400·404, 평가 5지표, preferences 정리, preset API). 작업 환경에 fastapi·SimpleITK가 없어 이 파일은 실행하지 못했다. 서버 venv에서 `python -m unittest discover -s tests -v`로 확인해야 한다 |

실제 NiiVue WebGL 화면에서의 표시와 실제 MRI의 지표 값은 이 환경에서 확인하지 못했다.
