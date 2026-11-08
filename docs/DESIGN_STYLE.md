# Medical Web Prototype 디자인 스타일 고정 규격 v2.2

## 0. 이 문서의 지위

이 문서는 frontend/index.html과 frontend/auth.html의 시각 스타일과 상호작용을 고정하는 기준이다. v1(2026-11-07)의 색상·글꼴·간격 규칙을 그대로 이어받고, v3 구현에서 추가된 화면과 사용자가 확정한 상단 메뉴, 아이콘 그룹, 툴팁, 방사형 메뉴 규칙을 더했다. 문서와 코드가 다르면 문서가 기준이며 코드를 문서에 맞춰 되돌린다. 문서에 없는 수치가 필요하면 코드보다 문서를 먼저 개정한다.

| 항목 | 규칙 |
|---|---|
| 변경 허용 | 문서에 정의된 컴포넌트를 재사용한 항목 추가, 문구 수정, JS 로직 수정, 미리보기 영상 파일 추가 |
| 변경 금지 | 색상 토큰 값, 글꼴, 크기 단계, 간격, 테두리·모서리 규칙, 시간 토큰 값, 요소 ID, 메뉴·섹션·아이콘 순서, 툴팁 타이밍, 방사형 메뉴 기하 수치 |
| 도입 금지 | CSS 프레임워크, 외부 웹폰트, 외부 아이콘 세트(Font Awesome, Material Icons 등), 상용 소프트웨어의 아이콘·화면 도안, 그림자, 그라디언트, 이모지, 카드형 박스 디자인. 예외는 15장 Layer Inspector의 colormap 막대와 미리보기 canvas 하나뿐이며, 이 색은 장식이 아니라 영상 표시 데이터다 |
| 파일 구성 | 화면마다 단일 HTML 파일, CSS는 `<style>` 하나, JS는 `<script type="module">` 하나. 아이콘은 HTML 안의 inline SVG로 직접 그린다 |

| 버전 | 변경 |
|---|---|
| v1 | 최초 고정. 단일 작업 화면, 애니메이션 금지 |
| v2 | 애니메이션 허용과 시간 규칙, 상단 메뉴, 화면별 아이콘 그룹, 미리보기 툴팁, 방사형 메뉴, 고정 아이콘, 공개 인증 화면, 표·입력·textarea 컴포넌트, 고정 높이 계산식 폐지 |
| v2.1 | C2AMorph 실행 상태 표시, Active contour 반복 입력, MIP slab 축 안내 요소 추가. 아이콘 hover 움직임을 선 그리기로 통일 |
| v2.2 | header 부제 삭제. 메뉴별 섹션 표시(4.4), Segmentation 하위 메뉴 Brain·Vessel, C2AMorph 삭제와 F. Deep Learning 모델 선택, 평가 지표 체크박스, Mask 도구 섹션, 떠 있는 Layer Inspector 창(15장), 아이콘 33개 |

## 1. 디자인 원칙

| 원칙 | 구현 방식 |
|---|---|
| 도구형 화면 | 장식 없이 1px 구분선과 여백만으로 영역을 나눈다 |
| 영상 우선 | viewer가 화면 대부분을 차지한다. 자주 쓰는 도구는 viewer 위 방사형 메뉴로 불러 시선 이동을 줄인다 |
| 저채도 | 강조색은 `--accent` 하나다. 실행 버튼, 현재 메뉴, 선택된 도구, 강조 연결선, 툴팁 속 개념 용어에만 쓴다 |
| 움직임은 설명용 | 애니메이션은 기능을 알려 주거나 상태 변화를 보여 줄 때만 쓴다. 대기 상태의 화면은 움직이지 않는다 |
| 라이트·다크 동일 구조 | `prefers-color-scheme`로 토큰 값만 바뀌고 구조는 같다 |

## 2. 토큰

### 2.1 색상

모든 색은 `:root` 변수로만 참조한다. 컴포넌트 CSS와 SVG에 hex 값을 직접 쓰지 않는다. SVG 아이콘은 `currentColor`로 칠한다.

| 토큰 | 라이트 | 다크 | 용도 |
|---|---|---|---|
| `--bg` | `#f5f6f8` | `#0f1115` | 페이지 배경, 입력창·일반 버튼·결과 상자 배경 |
| `--panel` | `#ffffff` | `#171a20` | header, 상단 메뉴, 아이콘 줄, 왼쪽 패널, toolbar, status bar, 툴팁, 방사형 메뉴 아이콘 배경 |
| `--text` | `#1f2328` | `#e6e8eb` | 본문 글자, 아이콘 선 |
| `--muted` | `#656d76` | `#9aa3ad` | 보조 설명, tag 글자, 방사형 메뉴 연결선 |
| `--line` | `#d8dee4` | `#2a3038` | 모든 구분선과 테두리, tag 배경 |
| `--accent` | `#2f6feb` | `#4c8dff` | primary 버튼, 현재 메뉴 표시, 선택 도구 테두리, 강조 연결선, 개념 용어 |
| `--accent-text` | `#ffffff` | `#ffffff` (재정의 없음) | primary 버튼 글자 |
| `--ok` | `#1a7f37` | `#3fb950` | 성공 상태 문구 |
| `--err` | `#cf222e` | `#f85149` | 실패 문구, 툴팁 조건 블록 |
| `--viewer` | `#14171c` | `#0b0d10` | viewer 캔버스 영역 배경 |

NiiVue 캔버스 배경은 `backColor: [0.08, 0.09, 0.11, 1]`로 고정한다.

### 2.2 시간

애니메이션과 지연 시간은 아래 토큰만 쓴다. 토큰은 CSS 변수와 JS 상수 양쪽에 같은 값으로 정의한다.

| 토큰 | 값 | 용도 |
|---|---|---|
| `--t-show-delay` | 100ms | 아이콘·개념 용어에 머문 뒤 툴팁 표시까지 |
| `--t-hide-delay` | 1000ms | 아이콘·툴팁·창에서 벗어난 뒤 툴팁 삭제까지 |
| `--t-fade` | 120ms | 툴팁 나타남(opacity 0→1) |
| `--t-radial-hold` | 250ms | 오른쪽 버튼 길게 누르기 판정 |
| `--t-radial-open` | 200ms | 방사형 메뉴 펼침 |
| `--t-icon-loop` | 1200ms | 아이콘 hover 애니메이션 한 주기 |
| `--t-denied` | 220ms | 거부 흔들림 |

easing은 펼침과 나타남에 `ease-out`, 아이콘 반복에 `ease-in-out`만 쓴다.

## 3. 타이포그래피

| 대상 | 크기 | 기타 |
|---|---|---|
| 본문 기본(body) | 14px | line-height 1.45 |
| header 제목 h1 | 16px | margin 0 |
| 섹션 제목 h2 | 13px | margin 0 0 8px |
| label, button, select, 상단 메뉴, 표 | 13px | |
| 툴팁 기능 이름 | 13px | h2와 같은 굵기 |
| `.muted`, status bar, 툴팁 설명, 조건 블록 | 12px | |
| file input | 12px | |
| tag, 툴팁 파라미터 표, 클릭 동작 안내 | 11px | |
| id 표시 `.ids`, 결과 상자 | 11px | monospace |
| seed 목록 | 12px | monospace |

```css
font-family: system-ui, -apple-system, "Segoe UI", "Noto Sans KR", sans-serif;  /* 본문 */
font-family: ui-monospace, monospace;                                          /* 수치·id */
```

font-weight는 따로 지정하지 않는다. h1, h2, 툴팁 기능 이름만 브라우저 기본 bold를 쓴다.

## 4. 레이아웃

### 4.1 전체 구조

```
┌ header ────────────────────────────────────────────────────────────┐  auto
├ 상단 메뉴 nav ─────────────────────────────────────────────────────┤  auto
├ 아이콘 줄 (현재 화면의 아이콘 그룹, 그룹이 없는 화면에서는 숨김) ──┤  auto
├ 화면 main (자료 관리자 / 작업 화면 / 영상 비교) ───────────────────┤  1fr
│  aside 360px  │  viewer: toolbar / canvas-wrap / status bar        │
└────────────────────────────────────────────────────────────────────┘
```

| 영역 | 규칙 |
|---|---|
| body | `display: grid; grid-template-rows: auto auto auto 1fr; height: 100vh; overflow: hidden` |
| header | padding 12px 16px, 하단 1px `--line`, flex baseline, gap 12px. 제목 h1만 둔다. 기능 목록 부제는 v2.2에서 삭제했다 |
| 상단 메뉴 | padding 6px 12px, 하단 1px `--line`, flex, gap 4px, 세로 가운데 정렬. 사용자 이름과 로그아웃은 `margin-left: auto`로 오른쪽 끝 |
| 아이콘 줄 | padding 6px 12px, 하단 1px `--line`, flex, gap 4px, wrap |
| main | `min-height: 0`, `grid-template-columns: 360px 1fr` |
| aside | padding 12px 16px, 오른쪽 1px `--line`, `overflow-y: auto` |
| viewer | `grid-template-rows: auto 1fr auto`, `min-width: 0`, `min-height: 0` |
| toolbar | padding 8px 12px, 하단 1px `--line`, flex, gap 6px, wrap |
| canvas | width·height 100%, display block |
| status bar | padding 8px 12px, 상단 1px `--line` |

`calc(100vh - Npx)` 형태의 고정 높이 계산식은 금지한다. v3에서 header 48.2px와 nav 50px의 합 98.2px를 92px로 고정해 1440×900 화면에서 문서 높이가 906px가 되고 페이지 스크롤이 생겼다. 높이는 위의 grid 행 구성으로만 나눈다.

### 4.2 반응형

| 조건 | 변경 |
|---|---|
| `max-width: 860px` | body `height: auto; overflow: visible`, main 1열, aside 오른쪽 테두리 제거, canvas-wrap 높이 70vh, 비교 패널 세로 배치(각 55vh) |

### 4.3 화면 구성

| 화면 | main ID | 내용 |
|---|---|---|
| 공개 인증 | auth.html | header와 로그인·회원가입 폼만 표시. 상단 메뉴, 아이콘 줄, 작업 기능 이름을 포함하지 않는다 |
| 자료 관리자 | `manager` | 로그인 후 초기 화면. 왼쪽에 자료 분류·업로드·검색·부서 계정·작업 이력, 오른쪽에 자료 표와 소견서·메모 |
| 작업 화면 | `workspace` | 영상 보기, Registration, Segmentation-Brain, Segmentation-Vessel, 측정·도구 메뉴가 공유하는 화면. 메뉴를 바꾸면 아이콘 줄이 바뀌고 aside에는 4.4 표의 섹션만 보인다 |
| 영상 비교 | `compare` | Fixed·Moving·결과 세 패널 |

### 4.4 메뉴별 섹션

aside의 각 섹션은 `data-menus` 속성에 보일 메뉴 이름을 공백으로 나열한다. 메뉴를 바꾸면 목록에 없는 섹션은 `hidden`이 되고 aside 스크롤은 맨 위로 돌아간다. DOM 순서는 아래 표의 위에서 아래 순서다.

| 섹션 ID | 제목 | 영상 보기 | Registration | Seg-Brain | Seg-Vessel | 측정·도구 |
|---|---|---|---|---|---|---|
| `loadSection` | 영상 불러오기 | 표시 | 표시 | 표시 | 표시 | |
| `registrationSection` | A. Registration (Rigid, Deformable, Overlay) | | 표시 | | | |
| `dlSection` | F. Deep Learning | | 표시 | | | |
| `segmentationSection` | D. Vessel enhancement | | | | 표시 | |
| `regionSection` | E. Region growing | | | 표시 | 표시 | |
| `maskSection` | Mask 도구 (Threshold, Active contour, Mask 그리기, 보간) | | | 표시 | 표시 | |
| `evalSection` | 평가 | | 표시 | 표시 | 표시 | |
| `toolsSection` | 영상 도구 | | | | | 표시 |
| `layerSection` | Layer Inspector 열기 | | | | | 표시 |
| `resultSection` | 결과 | 표시 | 표시 | 표시 | 표시 | 표시 |

측정·도구는 영상 불러오기를 두지 않고 현재 열린 Fixed·Moving과 viewer 영상을 대상으로 한다. 대상은 `toolTarget` 한 줄에 표시한다. Registration·Segmentation 섹션의 실행 결과와 거부 사유는 status bar(`statusText`)에, 측정·도구의 사유는 `toolStatus`에 표시한다.

## 5. 간격과 형태

| 항목 | 값 |
|---|---|
| 섹션 padding | 10px 0 14px, 섹션 사이 하단 1px `--line`, 마지막 섹션은 테두리 없음 |
| `.row` | flex, gap 6px, wrap, margin-top 6px |
| label | `grid-template-columns: 120px 1fr`, gap 8px, margin 4px 0 |
| 테두리 두께 | 1px. 예외는 현재 메뉴 하단 표시와 강조 연결선의 2px 두 가지뿐이다 |
| 모서리 반경 | 입력·tag·결과 상자·툴팁 4px, 버튼·아이콘 버튼 5px, 방사형 메뉴 아이콘 50%(원). 그 외 값 금지 |

## 6. 컴포넌트

### 6.1 기본 컴포넌트 (v1 유지)

| 컴포넌트 | 스타일 |
|---|---|
| 섹션 제목 h2 | flex, gap 8px, 세로 가운데. 형식은 `기호. 이름` 뒤에 tag 1개 |
| tag `.tag` | padding 1px 6px, radius 4px, 배경 `--line`, 글자 `--muted`, 11px |
| 입력 number·select | width 100%, padding 4px 6px, 1px `--line`, radius 4px, 배경 `--bg` |
| 일반 버튼 | padding 6px 10px, 1px `--line`, radius 5px, 배경 `--bg`, 13px |
| primary 버튼 `.primary` | 배경·테두리 `--accent`, 글자 `--accent-text`. 섹션마다 실행 버튼 1개에만 사용 |
| 비활성 | opacity 0.45, cursor not-allowed. 숨기지 않고 비활성으로 남긴다 |
| 결과 상자 `pre.result` | max-height 160px, overflow auto, 배경 `--bg`, 1px `--line`, radius 4px, padding 6px, 11px, pre-wrap |
| progress | width 220px, 브라우저 기본 모양 |
| 상태 문구 | 기본 `--text`, 성공 `.ok`, 실패 `.err` |

### 6.2 v2 추가 컴포넌트

| 컴포넌트 | 스타일 |
|---|---|
| 입력 text·password·email | 입력 number와 동일. `font: inherit` |
| textarea | 입력 number와 동일, min-height 100px, `font: inherit` |
| 표 table | width 100%, border-collapse collapse, 13px. 셀 padding 6px, 하단 1px `--line`, 왼쪽 정렬 |
| 상단 메뉴 버튼 | 일반 버튼과 같은 크기. 테두리 없음, 배경 투명. 현재 메뉴는 글자 `--accent`, 하단 2px `--accent` |
| 아이콘 버튼 | 32×32px, 1px `--line`, radius 5px, 배경 `--bg`, 안에 24px SVG. 선택된 도구는 테두리 `--accent`. 비활성은 6.1 규칙 |
| 아이콘 그룹 구분 | 그룹 사이 1px `--line` 세로선, 높이 24px, 좌우 margin 4px |
| 툴팁 | 7장 |
| 방사형 메뉴 | 8장 |
| 하위 메뉴 `.subnav` | 상단 메뉴 안 Segmentation 바로 뒤. 왼쪽 1px `--line`, padding-left 4px, gap 4px. 버튼은 상단 메뉴 버튼과 같다. Segmentation 메뉴일 때만 보인다 |
| 체크박스 묶음 `fieldset.checks` | 테두리·padding 없음, flex wrap, gap 4px 12px. 항목은 `label.check`(inline-flex, gap 4px). legend는 `.muted` |
| 평가 표 `#evalTable` | 표 컴포넌트, 11px monospace, 셀 padding 4px 6px. 감싸는 `#evalScroll` 최대 높이 240px, 넘치면 스크롤. 값이 없으면 `정의되지 않음` |
| 떠 있는 창 `.floating` | 15장 |
| 탭 `[role=tab]` | 상단 메뉴 버튼과 같은 모양. 선택 탭은 글자 `--accent`, 하단 2px `--accent` |

### 6.3 아이콘 도안

아이콘은 직접 그린 inline SVG만 쓴다. viewBox `0 0 24 24`, `fill: none`, `stroke: currentColor`, stroke-width 1.5, 선 끝 round. 글자를 넣지 않는다. 대기 상태에서는 정지해 있고, 마우스를 올리거나 키보드 포커스를 받은 동안에만 `--t-icon-loop` 주기로 반복하며, 벗어나면 첫 프레임으로 돌아간다. 움직임은 도안 일부의 이동·회전·선 그리기(stroke-dashoffset)로만 만들고 색은 바꾸지 않는다. v2.2 구현은 33개 모두 선 그리기(`pathLength="1"`, dashoffset 1→0)를 쓴다.

## 7. 미리보기 툴팁

### 7.1 구성

유로파 5(CK3 계열 중첩 툴팁)의 구성을 차용한다. 위에서부터 아래 순서로 배치한다. 해당 내용이 없는 칸은 생략한다.

| 순서 | 칸 | 규칙 |
|---|---|---|
| 1 | 예시 영상 | 320×180, 툴팁이 뜰 때 처음부터 재생, 사라지면 정지 후 처음으로 되돌림 |
| 2 | 기능 이름 | 13px |
| 3 | 설명 | 12px, 한두 문장. 개념 용어는 `--accent` 색과 1px 점선 밑줄 |
| 4 | 파라미터 표 | 11px, 이름과 기본값 두 열 |
| 5 | 클릭 동작 안내 | 11px `--muted`, 형식 `좌클릭: 실행 · 우클릭 드래그: Window/Level` |
| 6 | 조건 블록 | 12px `--err`. 비활성 아이콘일 때 미충족 조건을 한 줄씩 표시 |
| 7 | 고정 토글 | 일반 버튼. `자주 쓰는 도구에 고정` 또는 `고정 해제` |

| 항목 | 값 |
|---|---|
| 크기 | 폭 344px(영상 320px + 좌우 padding 12px), 높이는 내용에 맞춤 |
| 모양 | 배경 `--panel`, 1px `--line`, radius 4px, padding 12px, 그림자 없음 |
| 위치 | 아이콘 줄의 아이콘은 아래쪽 8px, 방사형 메뉴 아이콘은 펼침 방향 바깥쪽 8px. 창 밖으로 나가면 반대쪽으로 뒤집고, 그래도 넘치면 창 안으로 밀어 넣는다 |
| 나타남 | opacity 0→1, `--t-fade` |
| 개념 용어 하위 툴팁 | 영상 없이 이름과 설명만, 폭 240px. 하위 툴팁이 열려 있는 동안 상위 툴팁도 유지한다 |
| 쌓임 순서 | 방사형 메뉴 z-index 900, Layer Inspector 창 950, 툴팁 1000, 하위 툴팁 1001 |

### 7.2 타이밍

| 상황 | 동작 |
|---|---|
| 아이콘·개념 용어 위에 `--t-show-delay`(100ms) 머묾 | 툴팁 표시. 그 전에 벗어나면 표시하지 않음 |
| 툴팁이 열린 상태에서 다른 아이콘으로 이동 | 지연 없이 바로 교체 |
| 아이콘에서 벗어남 | `--t-hide-delay`(1000ms) 뒤 삭제하는 타이머 시작 |
| 타이머가 도는 중 툴팁이나 원래 아이콘으로 들어옴 | 타이머 취소, 유지 |
| 툴팁에서 벗어남 | 다시 1000ms 타이머 시작 |
| 창 이탈 판정(7.3) | 마지막 마우스 이동 시각에서 1000ms 뒤 삭제. 그 사이 창 안에서 다시 움직이면 취소 |
| Esc 키 | 즉시 삭제 |
| 스크롤, 창 크기 변경 | 즉시 삭제. 위치 기준이 바뀌기 때문 |
| 키보드 포커스 | 포커스를 받으면 100ms 뒤 표시, 포커스를 잃으면 1000ms 뒤 삭제 |
| 터치 입력 | 500ms 길게 누르면 표시, 다른 곳을 누르면 삭제 |

### 7.3 창 이탈 판정

아래 세 신호 중 하나라도 발생하면 창 이탈로 본다. 세 신호 모두 같은 1000ms 지연 삭제로 이어진다.

| 신호 | 조건 |
|---|---|
| 가장자리 정지 | 마지막 `pointermove` 위치가 창 가장자리 4px 안에 있고 1000ms 동안 추가 이동이 없음 |
| 이동 방향 연장 | 마지막 두 `pointermove` 기록의 속도로 계산한 16.7ms 뒤 위치가 창 밖 |
| 브라우저 신호 | `document`의 `mouseout`에서 `relatedTarget`이 null, `window` `blur`, `document.visibilityState`가 hidden |

가장자리 정지 하나만 쓰지 않는 이유는 기록 간격 때문이다. 60Hz에서는 16.7ms마다 한 번 기록되므로, 3,000px/s로 빠져나간 커서의 마지막 기록은 가장자리에서 약 50px 안쪽에 남는다. 이동 방향 연장 신호가 이 경우를 잡고, 가장자리 정지 신호는 브라우저 이벤트가 오지 않는 경우를 잡는다.

### 7.4 예시 영상 자리

기능 구현이 끝난 뒤 별도 작업으로 영상을 만들어 넣는다. 파일이 없어도 툴팁은 정상 동작해야 한다.

| 항목 | 규격 |
|---|---|
| 위치와 이름 | `frontend/previews/<아이콘 id>.webm`, 정지 이미지 `frontend/previews/<아이콘 id>.png` |
| 형식 | WebM(VP9), 320×180, 3~6초 반복, 무음, 파일당 1MB 이하 |
| 재생 속성 | `muted loop playsinline`, 툴팁이 열릴 때만 `play()` |
| 파일이 없을 때 | 영상 칸에 `예시 준비 중`(12px `--muted`)만 표시하고 나머지 칸은 그대로 |
| 모션 감소 설정 | 영상 대신 정지 이미지 표시 |
| 제작 방식 | 완성된 앱을 Playwright로 실행해 OASIS 또는 합성 영상으로 실제 조작을 녹화한다. 별도로 그린 애니메이션은 쓰지 않는다 |

## 8. 방사형 메뉴

### 8.1 열기와 선택

viewer 캔버스(`gl`, `compareFixed`, `compareMoving`, `compareResult`) 위에서만 동작한다. 브라우저 기본 오른쪽 클릭 메뉴는 이 캔버스들 안에서만 막는다. 판정은 NiiVue보다 먼저 받도록 capture 단계에서 처리한다.

| 오른쪽 버튼 동작 | 판정 | 결과 |
|---|---|---|
| 누른 뒤 `--t-radial-hold`(250ms) 안에 5px 이상 이동 | 드래그 | NiiVue의 기존 오른쪽 드래그(Window/Level, Pan/Zoom)로 넘김 |
| 누른 채 250ms 동안 5px 미만으로 머묾 | 길게 누르기 | 방사형 메뉴 펼침 |
| 펼친 상태에서 아이콘 칸으로 끌고 가서 놓기 | 선택 | 해당 아이콘의 동작 실행, 사용 횟수 1 증가 |
| 중심에서 48px 안 또는 칸 밖에서 놓기 | 취소 | 닫힘 |
| Esc 키 | 취소 | 닫힘 |

펼친 상태에서 커서가 가리키는 칸의 아이콘은 테두리를 `--accent`로 바꾸고, 7장 규칙대로 툴팁을 띄운다. 비활성 아이콘도 표시하지만 선택되지 않으며 툴팁에 조건 블록을 보여 준다.

### 8.2 기하

| 항목 | 값 |
|---|---|
| 시작 지점 표시 | 오른쪽 버튼을 누른 위치에 지름 6px 원, 색 `--muted` |
| 아이콘 | 지름 40px 원, 배경 `--panel`, 1px `--line`, 안에 24px SVG |
| 아이콘 간격 | 호 길이 기준 48px |
| 줄 반지름 | 1열 96px, 2열 160px, 3열 224px |
| 줄 수용 개수 | `floor(반지름 × 펼침 각(rad) / 48)` |
| 칸 배치 | 펼침 각을 줄 수용 개수로 나눈 칸의 가운데. i번째 각 = 시작 각 + (i + 0.5) × 펼침 각 / 개수 |
| 선택 칸 | 각 아이콘 각도를 중심으로 칸 폭만큼의 부채꼴, 반지름 방향은 줄 반지름 ±32px |

| 펼침 각 | 1열 | 2열 | 3열 | 합계 |
|---|---|---|---|---|
| 180° | 6 | 10 | 사용 안 함 | 16 |
| 90° | 3 | 5 | 7 | 15 |

### 8.3 연결선

| 항목 | 규칙 |
|---|---|
| 선 | 시작 지점에서 각 아이콘까지 1px 직선, 색 `--muted` |
| 선 끝 | 아이콘 가장자리(중심에서 20px 앞)에서 멈춤 |
| 강조 | 커서가 가리키는 아이콘의 선만 `--accent` 2px |
| 그리기 | SVG 한 장에 모든 선을 그리고 방사형 메뉴와 함께 열고 닫음 |

### 8.4 펼침 방향과 가장자리 처리

부채꼴 전체(가장 바깥 줄 반지름 + 20px)가 viewer 캔버스 경계에서 8px 안쪽에 들어와야 한다. 아래 순서로 처음 들어맞는 배치를 쓴다.

| 순서 | 배치 | 각도 |
|---|---|---|
| 1 | 위쪽 | 180° |
| 2 | 아래쪽 (위쪽 경계 근처) | 180° |
| 3 | 오른쪽 (왼쪽 경계 근처) | 180° |
| 4 | 왼쪽 (오른쪽 경계 근처) | 180° |
| 5 | 여유 공간이 가장 큰 안쪽 대각선 (모서리 근처) | 90°, 3열 사용 |
| 6 | 5도 들어맞지 않으면 | 90° 배치를 유지한 채 중심을 가장 가까운 들어맞는 위치로 옮기고, 시작 지점 표시도 함께 옮긴다 |

펼침 각을 좁힐 때 반지름은 바꾸지 않고 줄 수용 개수만 줄인다. 반지름을 키우면 모서리에서 부채꼴이 더 밖으로 나가기 때문이다.

### 8.5 펼침 애니메이션

`--t-radial-open`(200ms) 동안 연결선이 중심에서 바깥으로 그려지고 아이콘이 뒤따라 scale 0.6→1, opacity 0→1로 나타난다. 줄마다 40ms씩 늦게 시작한다. 닫을 때는 애니메이션 없이 즉시 사라진다. 모션 감소 설정이면 펼칠 때도 즉시 표시한다.

## 9. 고정 아이콘과 사용 횟수

| 항목 | 규칙 |
|---|---|
| 고정 단위 | 아이콘. 상단 메뉴는 고정·재배치하지 않는다 |
| 고정 방법 | 툴팁의 고정 토글 |
| 고정 최대 개수 | 6개 |
| 배치 | 고정 아이콘이 고정한 순서대로 1열을 먼저 채운다. 남은 칸은 고정하지 않은 아이콘을 사용 횟수 내림차순으로 채우고, 횟수가 같으면 10장 표의 순서를 따른다 |
| 넘침 | 수용 개수를 넘으면 자동으로 채운 아이콘 중 사용 횟수가 가장 적은 것부터 뺀다. 고정 아이콘은 빼지 않는다 |
| 위치 고정성 | 같은 펼침 각에서는 같은 아이콘이 같은 칸에 놓인다. 사용 횟수에 따른 재배치는 메뉴를 열 때만 계산하고, 펼친 상태에서는 바꾸지 않는다 |
| 저장 | 서버 DB에 사용자별로 저장한다. 브라우저 저장소에 두지 않는다 |

저장 API 계약은 다음과 같다. 모든 요청은 기존 세션과 CSRF 검사를 따른다.

| Method | Path | 본문·응답 |
|---|---|---|
| GET | `/api/preferences` | `{"pinned": ["icon-view-wl", ...], "usage": {"icon-view-wl": 12, ...}}` |
| PUT | `/api/preferences/pinned` | `{"pinned": [...]}`, 최대 6개, 존재하는 아이콘 id만 허용 |
| POST | `/api/preferences/usage` | `{"icon_id": "icon-view-wl"}`, 해당 횟수 1 증가 |

## 10. 상단 메뉴와 아이콘 그룹

### 10.1 상단 메뉴

순서는 고정이다. 로그인 후 초기 화면은 자료 관리자다.

| 순서 | 메뉴 | `data-nav` | 화면 | 아이콘 그룹 |
|---|---|---|---|---|
| 1 | 자료 관리자 | `manager` | `manager` | 없음 |
| 2 | 영상 보기 | `viewer` | `workspace` | view |
| 3 | Registration | `registration` | `workspace` | reg |
| 4 | Segmentation | `segmentation` | `workspace` | seg. 누르면 마지막으로 쓴 하위 메뉴(처음은 Brain)로 이동 |
| 4-1 | Brain | `seg-brain` | `workspace` | seg, Vesselness 제외 |
| 4-2 | Vessel | `seg-vessel` | `workspace` | seg 전체 |
| 5 | 측정·도구 | `tools` | `workspace` | tool |
| 6 | 영상 비교 | `compare` | `compare` | cmp |
| 7 | 소견서·메모 | `records` | `manager` | 없음 |

### 10.2 아이콘 그룹

아이콘은 기존 컨트롤을 대신 누르는 바로가기다. 파라미터 입력은 계속 왼쪽 패널에서 한다. 아래 순서가 아이콘 줄의 표시 순서이자 사용 횟수가 같을 때의 방사형 메뉴 정렬 순서다.

| 그룹 | 아이콘 id | 이름 | 도안 | 연결 동작 |
|---|---|---|---|---|
| view | `icon-view-mpr` | 3면 보기 | 세 칸으로 나뉜 사각형 | `viewMulti` |
| view | `icon-view-3d` | 3D Render | 정육면체 윤곽 | `viewRender` |
| view | `icon-view-crosshair` | Crosshair | 십자선 | 왼쪽 클릭 위치 이동 모드 |
| view | `icon-view-wl` | Window/Level | 반쪽이 채워진 원 | `dragSelect` = contrast |
| view | `icon-view-panzoom` | Pan / Zoom | 네 방향 화살표와 돋보기 | `dragSelect` = pan |
| view | `icon-view-layout` | Layout | 2×2 격자 | `layoutSelect` 다음 값 |
| view | `icon-view-enlarge` | 패널 확대 | 바깥으로 향한 모서리 화살표 | 현재 단면 확대·복귀 |
| view | `icon-view-reset` | 초기화 | 원형 화살표 | `resetView` |
| reg | `icon-reg-rigid` | Rigid Registration | 어긋난 두 사각형이 맞물림 | `runReg` |
| reg | `icon-reg-deformable` | Deformable | 휘어진 격자 | `runDeformable` |
| reg | `icon-reg-overlay` | Overlay | 겹친 두 사각형 | `overlayMoving` |
| reg | `icon-reg-dl` | Deep Learning | 입력 두 칸에서 출력 한 칸으로 모이는 선 | `runDl` (선택 모델을 쓸 수 없으면 비활성, 조건 블록에 `/api/dl/models`의 사유) |
| reg | `icon-reg-eval` | 평가 | 막대와 꺾은선 | `runEval` |
| seg | `icon-seg-vessel` | Vesselness | 가지가 갈라지는 관 | `runVes` |
| seg | `icon-seg-seed` | Seed 추가 | 핀 | `addSeed` |
| seg | `icon-seg-region` | Region growing | 점에서 퍼지는 동심원 | `runRg` |
| seg | `icon-seg-threshold` | Threshold | 막대와 가로 경계선 | `runThreshold` |
| seg | `icon-seg-contour` | Active contour | 점선 폐곡선 | `runContour` |
| seg | `icon-seg-draw` | Mask 그리기 | 펜 | `drawMask` |
| seg | `icon-seg-interp` | Slice 보간 | 두 단면 사이 점선 | `runInterpolate` |
| seg | `icon-seg-eval` | 평가 | 막대와 꺾은선 | `runEval` |
| tool | `icon-tool-point` | 측정점 기록 | 점과 작은 십자 | `capturePoint` |
| tool | `icon-tool-distance` | 거리 | 양 끝점이 있는 선 | `measure` (2점) |
| tool | `icon-tool-angle` | 각도 | 꺾인 선과 호 | `measure` (3점) |
| tool | `icon-tool-roi` | ROI | 원 | `measure` (1점) |
| tool | `icon-tool-mip` | MIP slab | 겹친 단면과 밝은 선 | `runMip` |
| tool | `icon-tool-modality` | Modality 추가 | 겹친 층과 더하기 | `modalityFile` |
| tool | `icon-tool-contrast` | Contrast | 축과 S자 곡선 | `openContrast` |
| tool | `icon-tool-colormap` | Color Map | 칸이 나뉜 막대와 control point 표시 | `openColormap` |
| cmp | `icon-cmp-load` | 비교 불러오기 | 나란한 세 사각형 | `loadCompare` |
| cmp | `icon-cmp-slice` | 단면 전환 | 세 방향 화살표 | `compareSlice` 다음 값 |
| cmp | `icon-cmp-wl` | 비교 Window/Level | 반쪽이 채워진 원 | `compareDrag` = contrast |
| cmp | `icon-cmp-panzoom` | 비교 Pan / Zoom | 네 방향 화살표와 돋보기 | `compareDrag` = pan |

방사형 메뉴의 후보는 현재 화면에서 쓸 수 있는 그룹의 아이콘 전체다. 작업 화면에서는 view, reg, seg, tool, 영상 비교 화면에서는 cmp와 view다. `icon-seg-vessel`은 Seg-Vessel 메뉴에서만 아이콘 줄과 방사형 메뉴에 나온다. 서버는 등록되지 않은 아이콘 id(예: v7의 `icon-reg-c2amorph`, `icon-seg-dice`)를 preferences 응답에서 걸러 낸다.

## 11. 애니메이션 사용 범위

아래 표에 없는 움직임은 추가하지 않는다. 모든 항목은 `prefers-reduced-motion: reduce`에서 끄며, 이때는 상태만 즉시 바뀐다.

| 대상 | 움직임 | 시간 |
|---|---|---|
| 아이콘 | hover·포커스 동안 도안 반복 | `--t-icon-loop` |
| 툴팁 | opacity 나타남 | `--t-fade` |
| 툴팁 예시 영상 | 영상 재생 | 3~6초 반복 |
| 방사형 메뉴 | 선 그리기와 아이콘 펼침 | `--t-radial-open` |
| 거부 피드백 | 상태 문구 좌우 3px 흔들림 1회 | `--t-denied` |

거부 흔들림은 Web Animations API(`element.animate`) 하나로만 구현한다. 같은 동작을 CSS `@keyframes`로 중복 정의하지 않는다.

## 12. 문구 규칙

| 항목 | 규칙 |
|---|---|
| 언어 | 한국어 문장, 기술 용어는 영어 원문 유지(Registration, Fixed, Moving, Seed 등) |
| 실행 버튼 | `Run <기능명>` 영어 형식 |
| 보조 버튼 | 한국어 동사형(`Fixed 보기`, `Seed 비우기`) |
| 파라미터 요약 | 섹션 안 `.muted` 한 줄, 구분자 ` · ` |
| 상태 문구 | `[job 종류] 메시지`, 완료는 `완료`, 실패는 `실패: 원인`. 원인은 서버가 보낸 구체적 사유를 그대로 표시하고 일반 문구로 바꾸지 않는다 |
| 툴팁 설명 | 기능이 하는 일을 한두 문장으로. 내부 구현 이름보다 결과를 먼저 쓴다 |

## 13. 요소 ID 계약

JS가 아래 ID에 의존하므로 이름 변경과 삭제를 금지한다.

| 영역 | ID |
|---|---|
| 공개 인증 (auth.html) | `loginTab`, `signupTab`, `form`, `email`, `password`, `signupFields`, `name`, `department`, `submit`, `reason`, `logout` |
| 상단 메뉴 | `who`, `logout`, `data-nav` 속성 7개(10.1) |
| 자료 관리자 | `manager`, `allFiles`, `originalFiles`, `resultFiles`, `demo`, `managerUpload`, `fileSearch`, `searchFiles`, `membersSection`, `memberSearch`, `loadMembers`, `membersList`, `refreshJobs`, `jobList`, `managerStatus`, `managerContent`, `folderPath`, `fileScroll`, `fileRows` |
| 소견서·메모 | `recordsSection`, `recordName`, `reportText`, `saveReport`, `reloadRecords`, `recordStatus`, `noteText`, `addNote`, `notes`, `history` |
| 작업 화면 · 영상 불러오기 | `workspace`, `workspaceAside`, `loadSection`, `fixedFile`, `movingFile`, `idInfo`, `showFixed`, `showMoving` |
| 상단 하위 메뉴 | `segSubnav`, `data-nav` 속성 `seg-brain`, `seg-vessel` |
| A | `registrationSection`, `regMetric`, `regIter`, `runReg`, `runDeformable`, `overlayMoving` |
| F. Deep Learning | `dlSection`, `dlModel`, `dlInfo`, `dlStatus`, `runDl` |
| D | `segmentationSection`, `vesTarget`, `vesSigma`, `vesA1`, `vesA2`, `runVes` |
| E | `regionSection`, `rgTarget`, `rgMult`, `rgIter`, `rgRad`, `seedList`, `addSeed`, `clearSeeds`, `runRg` |
| Mask 도구 | `maskSection`, `thresholdLow`, `thresholdHigh`, `runThreshold`, `contourIter`, `runContour`, `drawMask`, `undoMask`, `saveMask`, `runInterpolate` |
| 평가, 결과 | `evalSection`, `evalPred`, `evalRef`, `evalMetrics`, `runEval`, `evalScroll`, `evalTable`, `resultSection`, `resultBox` |
| 영상 도구 | `toolsSection`, `toolTarget`, `sliceSelect`, `layoutSelect`, `dragSelect`, `resetView`, `modalityFile`, `slabStart`, `slabEnd`, `slabInfo`, `runMip`, `capturePoint`, `clearPoints`, `pointList`, `roiRadius`, `measure`, `toolStatus` |
| Layer Inspector | `layerSection`, `openContrast`, `openColormap`, `openInfo`, `inspector`, `inspectorHead`, `inspectorTitle`, `inspectorClose`, `layerList`, `ctMin`, `ctMax`, `ctLevel`, `ctWindow`, `ctBar`, `ctPlot`, `ctPoint`, `ctX`, `ctY`, `ctAdd`, `ctDel`, `ctReset`, `ctAuto`, `ctBins`, `ctCut`, `ctLog`, `cmPreset`, `cmName`, `cmSave`, `cmRemove`, `cmCanvas`, `cmPlot`, `cmPoint`, `cmPos`, `cmOpacity`, `cmColor`, `cmStyle`, `cmSide`, `cmAdd`, `cmDel`, `cmNan`, `cmNanInfo`, `infoTable`, `inspectorStatus` |
| viewer | `viewMulti`, `viewRender`, `overlayOpacity`, `location`, `gl`, `progress`, `statusText` |
| 영상 비교 | `compare`, `loadCompare`, `compareSlice`, `compareDrag`, `compareStatus`, `comparePanels`, `compareFixed`, `compareMoving`, `compareResult` |
| v2 신규 | `iconBar`(아이콘 줄), `tooltip`, `tooltipNested`, `radialMenu`, `radialLines`(연결선 SVG), 아이콘 id 33개(10.2) |

v2.1까지의 `segmentationSection`은 D 섹션 ID로 유지한다. v2.2에서 삭제한 ID는 `runC2a`, `c2aStatus`, `runDice`다. 왼쪽 패널 섹션 순서는 4.4 표를 따른다.

## 14. 수정 요청 시 AI에게 주는 지시문

아래 문장을 수정 요청과 함께 전달한다.

```
frontend의 HTML을 수정할 때 `docs/DESIGN_STYLE.md` v2.2를 기준으로 한다.
색상·시간 토큰, 글꼴, 크기, 간격, 레이아웃 grid, 테두리·모서리 값, 메뉴·섹션·아이콘 순서, 요소 ID를 바꾸지 않는다.
calc(100vh - Npx) 같은 고정 높이 계산식을 쓰지 않는다.
새 요소는 6장의 컴포넌트만 재사용하고 새 hex 색을 추가하지 않는다. 아이콘은 6.3 규칙의 inline SVG로 직접 그린다.
애니메이션은 11장 표에 있는 것만 쓰고, prefers-reduced-motion에서 끈다.
툴팁 타이밍(100ms 표시, 1000ms 지연 삭제, 창 이탈 판정 3신호)과 방사형 메뉴 수치(250ms, 5px, 반지름 96/160/224px, 간격 48px)를 바꾸지 않는다.
CSS 프레임워크, 웹폰트, 외부 아이콘 세트, 그림자, 그라디언트를 도입하지 않는다. 예외는 Layer Inspector의 colormap 막대와 미리보기 canvas뿐이다.
메뉴별 섹션 표시(4.4)와 Layer Inspector 계산 규칙(15장)을 바꾸지 않는다.
요청받은 기능 범위 밖의 시각 변경을 하지 않는다.
변경 후 문서와 다른 수치가 있으면 문서 값으로 되돌린다.
```
## 15. Layer Inspector

ITK-SNAP Image Layer Inspector의 Contrast·Color Map·Info 탭을 웹 viewer에 옮긴 떠 있는 창이다. 화면 도안은 따라 하지 않고 항목과 계산 규칙만 따른다.

### 15.1 창

| 항목 | 규칙 |
|---|---|
| 형태 | `.floating`: position fixed, z-index 950, 폭 `min(680px, 100vw - 16px)`, 최대 높이 `100vh - 16px`, 넘치면 창 안 스크롤. 배경 `--panel`, 1px `--line`, radius 4px, 그림자 없음 |
| 열기 | `openContrast`, `openColormap`, `openInfo` 버튼 또는 `icon-tool-contrast`, `icon-tool-colormap`. 영상이 없으면 열지 않고 `toolStatus`에 사유 |
| 처음 위치 | 오른쪽 16px, 위 120px. 이후에는 마지막 위치 유지 |
| 이동 | 제목 줄 `inspectorHead`를 끌어 옮긴다. 창 전체가 viewport 안에 남도록 자른다. 창 크기 변경 때도 다시 자른다 |
| 비모달 | 열린 동안에도 viewer 조작, 메뉴 이동, 우클릭 W/L이 동작한다. `닫기` 버튼으로만 닫는다 |
| 구조 | 왼쪽 140px layer 목록(오른쪽 1px `--line`), 오른쪽 탭 영역. 860px 이하에서는 위아래로 쌓는다 |
| layer 목록 | viewer의 volume 순서. 이름은 `역할 · 영상`, 역할은 첫 volume `Main`, 정수형이면서 최대값 255 이하인 volume `Segmentation`, 나머지 `Additional`. 선택 항목은 테두리 `--accent` |
| 상태 문구 | 탭 아래 `inspectorStatus` 한 줄. 다음 편집이 성공하면 지운다 |

### 15.2 Contrast 탭

| 항목 | 규칙 |
|---|---|
| 입력 | Min, Max, Level = (Min + Max) / 2, Window = Max − Min. Level·Window를 고치면 Window·Level을 유지한 채 Min·Max를 다시 계산한다. Max ≤ Min이면 되돌리고 사유를 표시한다 |
| 그림 | SVG 340×184. 가로축은 영상 전체 밝기 범위(global min~max), histogram 막대는 `--line`, 곡선은 `--accent` 1.5px, 점은 지름 10px 원(선택 점 테두리 `--accent` 2px). 왼쪽 12px colormap 막대 |
| 곡선 | control point x는 [Min, Max] 안의 정규화 위치, y는 colormap index 0~1. 첫 점 (Min, 0), 끝 점 (Max, 1) 고정. Min 아래는 0, Max 위는 1. 점 사이 선형 보간, x는 증가, y는 감소하지 않게 이웃 점 사이로 자른다. Min·Max가 바뀌면 중간 점은 정규화 위치를 유지한다 |
| 점 조작 | 중간 점은 끌어서 x·y를 바꾸고, 첫 점과 끝 점은 끌어서 Min·Max를 바꾼다. Point 선택 후 x, y 입력도 같다. `+`는 선택 점과 다음 점의 가운데에 점 추가, `−`는 중간 점 삭제 |
| Reset · Auto | Reset은 Min·Max를 전체 밝기 범위로, 곡선을 직선으로. Auto는 Min·Max를 1·99 percentile로(4096칸 누적 histogram) |
| Histogram | Bins 기본 40(2~1024). Cutoff 기본 10%: 막대 높이 상한을 전체 voxel 수의 해당 비율로 둔다. Log 체크 시 log(1 + 개수) 비례 |
| 우클릭 W/L 동기화 | NiiVue `onIntensityChange`와 `보기 초기화`에서 volume의 cal_min·cal_max를 Min·Max로 다시 읽는다 |

### 15.3 Color Map 탭

| 항목 | 규칙 |
|---|---|
| Preset | 기본 Gray, Jet, Hot, Cool과 사용자 preset. 처음 연 layer는 NiiVue에 지정된 colormap을 position k/8(k = 0~8)의 9개 점으로 옮긴 `직접 편집` 상태다. 점을 고치면 `직접 편집`으로 바뀐다 |
| Jet 정의 | 0: Two-sided, Left (0,0,0, opacity 0), Right (0,0,128, 1). 0.125 (0,0,255), 0.375 (0,255,255), 0.625 (255,255,0), 0.875 (255,0,0), 1 (128,0,0) |
| Hot · Cool · Gray | Hot 0 검정, 0.375 빨강, 0.75 노랑, 1 흰색. Cool 0 cyan, 1 magenta. Gray 0 검정, 1 흰색 |
| 저장 | `+`는 이름 칸의 이름으로 서버에 저장, `−`는 선택한 사용자 preset 삭제. 기본 preset 이름은 쓸 수 없다. 사용자당 32개 |
| 그림 | canvas 340×96에 8px 체크무늬(`--panel`, `--line`)를 깔고 colormap을 opacity 그대로 겹친다. 그 위 SVG에 opacity 선(`--accent`)과 control point 원 |
| 점 항목 | Point(Index), Position 0~1, Opacity 0~1, Color, Style Regular·Two-sided, Side Left·Right. 첫 점과 끝 점은 Position 고정, 삭제 불가. Regular는 양쪽 색이 같고, Two-sided는 Side에서 고른 쪽만 고친다 |
| 색 계산 | 두 점 사이는 앞 점의 Right와 뒤 점의 Left를 RGBA 선형 보간 |
| NaN 색 | NiiVue 0.42는 NaN voxel 색 지정을 지원하지 않는다. NaN 색 입력은 비활성으로 두고 NaN voxel 수와 사유를 표시한다 |

### 15.4 Info 탭

Layer, Size(voxel), Spacing(mm), Origin RAS(mm), Direction(affine 열 정규화, RAS), Data type, 밝기 범위, 표시 범위, NaN voxel 수를 표로 표시한다.

### 15.5 표시 적용

| 단계 | 규칙 |
|---|---|
| LUT | 256칸. k = 1~254는 u = k/255에서 곡선 y를 구하고 colormap(y)를 넣는다. k = 0은 Min 이하 값이 쓰는 칸이라 첫 점의 Left 색, k = 255는 Max 이상 값이 쓰는 칸이라 마지막 점의 Right 색 |
| 등록 | `nv.addColormap('inspector-layer-<index>', {R,G,B,A,I})`, I = 0~255 |
| 범위 | NVImage는 colormap 지정 시 cal 범위를 다시 계산하므로, colormap 지정 뒤 cal_min = Min, cal_max = Max를 다시 넣고 `updateGLVolume()` |
| 빈도 | 입력·끌기 변경은 requestAnimationFrame 한 번으로 모아 적용한다 |
| 유지 | 설정은 volume 이름(영상 id) 기준으로 세션 동안 유지하고, 같은 영상을 다시 불러오면 다시 적용한다 |

### 15.6 Preset API

| Method | Path | 본문·응답 |
|---|---|---|
| GET | `/api/preferences/colormaps` | `{"이름": {"points": [...], "nan": [r,g,b,a]}}` |
| PUT | `/api/preferences/colormaps/{이름}` | `{"points": [{"position": 0, "left": [r,g,b,a], "right": [r,g,b,a], "style": "regular"}, ...], "nan": [0,0,0,0]}`. 점 2~64개, position 0에서 시작해 1에서 끝나고 감소하지 않음, 값 0~255 정수. 응답은 GET과 같음 |
| DELETE | `/api/preferences/colormaps/{이름}` | 응답은 GET과 같음, 없으면 404 |
