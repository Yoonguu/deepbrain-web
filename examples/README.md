# 예시 SQLite DB

`medical_web_example.sqlite3`는 설계를 설명하기 위한 가상 데이터입니다. 환자 영상 파일이나 실제 계정 비밀번호는 없습니다. 현재 웹 앱은 이 DB에 연결되어 있지 않으며 로그인 기능도 구현되지 않았습니다.

## 테이블 관계

```text
users ─ memberships ─ departments ─ studies ─ study_assets
                                      ├─ reports ─ report_versions
                                      ├─ notes
                                      └─ audit_events
```

- `memberships`: 의사의 부서·직무·부서장 역할과 확인 시각. `verified_at`이 없으면 해당 부서 자료에 접근할 수 없습니다.
- `studies`: 부서가 공동으로 보는 MRI 검사. `patient_pseudonym`은 가상 식별자입니다.
- `study_assets`: 원본·분석 결과의 메타데이터. `storage_key`는 비어 있으므로 실제 파일은 없습니다.
- `reports`와 `report_versions`: 같은 부서 의사가 공동으로 수정한 소견서의 버전 이력.
- `notes`: 작성자별 메모. 같은 부서 의사는 모두 열람할 수 있다는 설계입니다.
- `audit_events`: 누가 어떤 작업을 했는지 남기는 기록의 예시입니다.

## 권한 확인 예시

아래 쿼리에서 `:user_id`와 `:study_id`를 바꾸어 결과를 비교합니다. 결과가 `1`이면 허용, `0`이면 거부입니다.

```sql
SELECT EXISTS (
  SELECT 1 FROM users u
  JOIN memberships m ON m.user_id = u.id
  JOIN studies s ON s.department_id = m.department_id
  WHERE u.id = :user_id AND s.id = :study_id
    AND u.active = 1 AND m.job_code = 'physician'
    AND m.verified_at IS NOT NULL AND s.deleted_at IS NULL
) AS can_view;
```

예시 결과: 의사 B(`2`)와 영상의학과 검사(`101`)는 `1`, 신경과 의사 D(`4`)와 검사 `101`은 `0`, 소속 미확인 가입자 E(`5`)와 검사 `101`은 `0`입니다.

삭제 권한은 같은 부서의 `head` 역할까지 확인합니다.

```sql
SELECT EXISTS (
  SELECT 1 FROM users u
  JOIN memberships m ON m.user_id = u.id
  JOIN studies s ON s.department_id = m.department_id
  WHERE u.id = :user_id AND s.id = :study_id
    AND u.active = 1 AND m.role = 'head'
    AND m.job_code = 'physician' AND m.verified_at IS NOT NULL
    AND s.deleted_at IS NULL
) AS can_delete;
```

예시 결과: 영상의학과 부서장 A(`1`)와 검사 `101`은 `1`, 의사 B(`2`)와 검사 `101`은 `0`입니다. 실제 서비스에서는 이 검사를 브라우저 표시뿐 아니라 서버의 모든 관련 요청에서 수행해야 합니다.

## 선택 이유와 한계

SQLite 본체는 퍼블릭 도메인으로, 공식 문서에 따르면 상업적 사용에도 별도 라이선스가 필요하지 않습니다. 이 DB는 구조 검토용입니다. 여러 서버나 동시 쓰기가 많은 운영 환경의 DB 선택은 별도로 검토해야 합니다.

- 라이선스: https://www.sqlite.org/copyright.html
- 적합한 사용 사례: https://www.sqlite.org/whentouse.html
