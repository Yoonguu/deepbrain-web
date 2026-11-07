# MRI 후처리 프로그램 기능 정리와 설명용 애니메이션 설계

## 1. 문제 인식

현재 보유한 화면 자료는 6개이며 기호 A부터 F로 구분한다. A는 3DReg, B는 MRI_MRAVisualization, C는 ExpectedImage, D는 vesselseg, E는 tumorseg, F는 RegDL이다. 각 자료는 Registration, Segmentation, Visualization 중 일부만 보여 주므로 기능 전체와 사용 흐름이 한눈에 드러나지 않는다. 이 때문에 각 기능이 무엇이며 어떤 입력과 출력을 갖는지 설명하는 그림 자료가 필요하다.

기능 이름과 실제 구현 알고리즘은 구분해야 한다. Registration이라는 작업 이름이 같아도 Transformation model, Similarity metric, Optimizer 조합에 따라 알고리즘이 달라진다. F의 C2AMorph1은 화면 표기만으로 원 논문을 확정할 수 없다. 설명 자료는 기능의 입력과 출력을 보여 주는 수준으로 제한해야 한다.

## 2. 현재의 가정

화면 자료는 JPG 정지 이미지이며 GIF 원본의 모든 frame을 확인한 것이 아니다. 제조사 소프트웨어 사례는 Siemens syngo.via 공식 교육 자료이고, 오픈소스 사례는 Weasis, ITK-SNAP, MITK 문서이다. 제조사 소프트웨어에 같은 작업 범주의 기능이 있다는 사실은 확인되지만 개별 알고리즘의 동일성은 확인되지 않았다. 아이콘 도안은 표준이 정해져 있지 않으므로 아래 도안은 의미 전달 기준의 제안이다.

용어는 다음과 같이 통일한다.

| 용어 | 사용 의미 |
|---|---|
| 아이콘 | 도구 버튼에 표시되는 작은 그림 |
| 이모티콘 | 문자와 기호를 조합한 감정 표현. 본 문서에서는 사용하지 않음 |
| Animated GIF | 설명용 움직이는 그림 파일 |
| Moving image | Registration에서 변형되는 영상 |
| Fixed image | Registration에서 기준이 되는 영상 |

## 3. 문제 해결 방법

### 3.1 기능 목록

| 번호 | 기능 | 하는 일 | 대응 자료 | 설명 그림 유형 |
|---|---|---|---|---|
| F1 | MPR | Axial, Coronal, Sagittal 단면 재구성 | B, E | 3분할 캡처 |
| F2 | MIP | 시선 방향 최대 밝기 투영으로 혈관 강조 | B, D | 전후 비교 |
| F3 | Volume rendering | Volume의 입체 표시 | B | 회전 Animated GIF |
| F4 | Registration | Moving image를 Fixed image에 정렬 | A, C, F | 3영상 비교 Animated GIF |
| F5 | Fusion, Overlay | 정렬된 두 영상을 색상과 투명도로 겹침 | A | 투명도 변화 Animated GIF |
| F6 | Segmentation | 관심 구조 영역 분리와 Mask 생성 | D, E | 원본 대 Mask 중첩 |
| F7 | Linked crosshair | 한 단면의 위치 이동이 다른 단면에 연동 | 신규 | 십자선 이동 Animated GIF |
| F8 | Zoom, Pan, Window/Level 동기화 | 세 단면의 확대, 이동, 밝기 대비를 함께 변경 | 신규 | 동기화 Animated GIF |
| F9 | 패널 확대 | 분할 화면 중 하나를 크게 표시하고 복귀 | 신규 | 더블클릭 Animated GIF |
| F10 | Layout 변경 | 패널 수와 배치 조절 | 신규 | 배치 전환 Animated GIF |
| F11 | MIP 두께 조절 | Slab thickness 변경 | 신규 | 두께 변화 Animated GIF |
| F12 | 측정 | 거리, 각도, ROI 통계, Segmentation 부피 | 신규 | 측정 과정 캡처 |
| F13 | Semi-automatic segmentation | Seed 지정 후 Active contour 진행 | 신규 | contour 진행 Animated GIF |
| F14 | Slice 간 보간 | 일부 Slice의 수동 Mask로 나머지 보간 | 신규 | 전후 비교 |
| F15 | 다중 Modality 입력 | T1, T2, FLAIR 등을 함께 사용 | 신규 | Tiled 배치 캡처 |

우선 적용 후보는 F7, F8, F5의 투명도 조절, F12이다. 이 네 기능은 공통 좌표계만 확보되면 기존 화면에 추가하기 쉽다. F4의 Deformable registration, F13, 4D 처리는 알고리즘 구현이 필요하므로 별도 모듈로 분리하는 편이 적합하다. 이 우선순위는 자료의 기능 범위에 근거한 추론이며 실제 난이도는 GUI 프레임워크와 Volume 표현 방식에 따라 달라진다.

### 3.2 아이콘 도안

| 기능 | 도안 | 툴팁 문구 |
|---|---|---|
| Zoom | 돋보기 | 확대, 축소 |
| Pan | 네 방향 화살표 | 이동 |
| Window/Level | 반쪽이 어두운 원 | 밝기, 대비 |
| Crosshair | 십자선 | 단면 위치 연동 |
| 초기화 | 원형 화살표 | Zoom, Pan, Window/Level 초기화 |
| 거리 측정 | 양 끝점이 있는 선 | 거리 |
| 면적 측정 | 타원 | ROI 면적 |
| Registration | 어긋난 두 사각형이 맞물리는 그림 | 영상 정렬 |
| Layout | 격자 | 화면 배치 |
| Overlay | 겹쳐진 두 사각형 | 겹쳐 보기 |

아이콘은 단색 윤곽선으로 통일하고 크기는 24 px와 32 px 두 종류로 제작한다. Registration, Segmentation, Fusion은 단일 아이콘으로 의미가 모호하므로 아이콘과 별도로 전후 비교 그림을 함께 제공한다.

### 3.3 설명용 Animated GIF 사양

공통 사양은 다음과 같다.

| 항목 | 값 |
|---|---|
| 해상도 | 800 x 450 px |
| frame rate | 10 fps |
| 길이 | 3 s 이상 6 s 이하 |
| 반복 | 무한 반복 |
| 파일 용량 | 2 MB 이하 |
| 색상 | 최대 256색 |
| 자막 | 화면 상단에 기능 이름, 하단에 한 줄 설명 |

각 Animated GIF의 frame 구성은 다음과 같다.

| 번호 | 파일명 | frame 구성 | 길이 |
|---|---|---|---|
| G1 | reg_moving_fixed.gif | Moving, Fixed 나란히 표시. Moving이 Fixed 위치로 이동. 마지막에 Registered 패널 표시 | 5 s |
| G2 | fusion_alpha.gif | 정렬된 두 영상을 붉은색과 파란색으로 겹침. 투명도를 0에서 100 사이로 왕복 | 4 s |
| G3 | crosshair_link.gif | Axial 단면에서 십자선 이동. Coronal, Sagittal 단면의 십자선이 같은 3D 위치로 이동 | 5 s |
| G4 | sync_zoom_wl.gif | 한 패널에서 Zoom 후 Window/Level 변경. 나머지 패널이 동시에 변화 | 5 s |
| G5 | panel_enlarge.gif | 3분할 화면에서 패널 더블클릭. 크게 확대된 뒤 다시 더블클릭하여 복귀 | 4 s |
| G6 | layout_change.gif | 1x3, 2x2, 3x3 배치로 순차 전환 | 6 s |
| G7 | mip_slab.gif | Slab thickness를 얇게에서 두껍게 변경. 혈관 연결이 점진적으로 드러남 | 4 s |
| G8 | seg_overlay.gif | 원본 단면 위에 Mask를 겹침. 라벨별 표시 전환과 투명도 조절 | 5 s |
| G9 | snake_evolution.gif | Seed 지정. Contour가 병변 경계로 확장. 마지막에 최종 Mask 표시 | 6 s |
| G10 | measure_roi.gif | 두 점 클릭으로 거리 표시. ROI 지정 후 통계값 표시 | 5 s |

G1은 Moving, Fixed, Registered 세 패널의 레이블을 고정하고 변형 전후의 윤곽선을 겹쳐 표시한다. 이 구성은 F의 Moving, Fixed, 출력 비교 구성과 같다. G3와 G4는 세 단면이 같은 좌표계에 있음을 보여야 하므로 3분할 화면을 유지한 채 하나의 패널만 조작한다.

### 3.4 제작 절차

제작은 화면 녹화 기반과 합성 기반 두 방식으로 나뉜다. 기존 프로그램에서 구현된 기능은 화면 녹화로 얻는다. 아직 구현되지 않은 기능은 같은 데이터로 frame을 합성하여 제작한다.

1. 공통 샘플 영상 1세트를 고정한다. T1, MRA, Mask를 같은 좌표계로 정렬한 NIfTI 또는 MHA 파일을 사용한다.
2. 기능별 시나리오를 3 s 이상 6 s 이하로 설계한다.
3. 화면 녹화 또는 Python 합성으로 frame을 생성한다.
4. 자막과 번호 표시를 추가한다.
5. 10 fps, 256색 조건으로 Animated GIF를 출력한다.
6. 2 MB를 초과하면 해상도를 줄이거나 frame 수를 줄인다.

### 3.5 근거 자료

| 구분 | 자료 | 근거 내용 |
|---|---|---|
| 제조사 | Siemens Healthineers Academy, Essentials Part 2: MM Reading | 패널 더블클릭 확대와 복귀, Zoom, Pan |
| 제조사 | Siemens Healthineers Academy, Physician's Quick Reference Guide syngo.via VB60 | Pan, Zoom 조작 방식 |
| 제조사 | Siemens Healthineers Academy, Layout Editor Overview | 패널 수와 배치 조절 |
| 제조사 | Siemens Healthineers Academy, syngo Fusion | Registration 후 색상과 혼합 비율 조절 |
| 오픈소스 | Weasis 문서 | MPR, 동기화, Oblique 단면, MIP 두께, Fusion, 측정 |
| 오픈소스 | ITK-SNAP 논문과 문서 | 다중 Modality 표시, Active contour, 수동 및 자동 선형 Registration |
| 오픈소스 | MITK 사이트 | Rigid, Deformable registration, 시각화, Segmentation |
