PRAGMA foreign_keys = ON;

CREATE TABLE departments (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE memberships (
  user_id INTEGER NOT NULL REFERENCES users(id),
  department_id INTEGER NOT NULL REFERENCES departments(id),
  job_code TEXT NOT NULL CHECK (job_code = 'physician'),
  role TEXT NOT NULL CHECK (role IN ('doctor', 'head')),
  verified_at TEXT,
  verified_by_user_id INTEGER REFERENCES users(id),
  PRIMARY KEY (user_id, department_id)
);

CREATE TABLE studies (
  id INTEGER PRIMARY KEY,
  department_id INTEGER NOT NULL REFERENCES departments(id),
  accession_code TEXT NOT NULL UNIQUE,
  patient_pseudonym TEXT NOT NULL,
  modality TEXT NOT NULL CHECK (modality = 'MR'),
  source TEXT NOT NULL CHECK (source IN ('web_upload', 'device_pacs')),
  uploaded_by_user_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  deleted_at TEXT,
  deleted_by_user_id INTEGER REFERENCES users(id)
);

CREATE TABLE study_assets (
  id INTEGER PRIMARY KEY,
  study_id INTEGER NOT NULL REFERENCES studies(id),
  kind TEXT NOT NULL CHECK (kind IN ('original', 'analysis_result')),
  display_name TEXT NOT NULL,
  storage_key TEXT
);

CREATE TABLE reports (
  id INTEGER PRIMARY KEY,
  study_id INTEGER NOT NULL UNIQUE REFERENCES studies(id),
  status TEXT NOT NULL CHECK (status IN ('draft', 'final')),
  current_version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE report_versions (
  id INTEGER PRIMARY KEY,
  report_id INTEGER NOT NULL REFERENCES reports(id),
  version INTEGER NOT NULL,
  body TEXT NOT NULL,
  edited_by_user_id INTEGER NOT NULL REFERENCES users(id),
  edited_at TEXT NOT NULL,
  UNIQUE (report_id, version)
);

CREATE TABLE notes (
  id INTEGER PRIMARY KEY,
  study_id INTEGER NOT NULL REFERENCES studies(id),
  author_user_id INTEGER NOT NULL REFERENCES users(id),
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE audit_events (
  id INTEGER PRIMARY KEY,
  study_id INTEGER REFERENCES studies(id),
  actor_user_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);

CREATE INDEX idx_memberships_department ON memberships(department_id, job_code, verified_at);
CREATE INDEX idx_studies_department ON studies(department_id, deleted_at);
CREATE INDEX idx_report_versions_report ON report_versions(report_id, version);
CREATE INDEX idx_notes_study ON notes(study_id, created_at);

INSERT INTO departments VALUES
  (1, '영상의학과'),
  (2, '신경과');

INSERT INTO users VALUES
  (1, 'head.radiology@example.invalid', '가상 부서장 A', 1),
  (2, 'doctor.b@example.invalid', '가상 의사 B', 1),
  (3, 'doctor.c@example.invalid', '가상 의사 C', 1),
  (4, 'doctor.neuro@example.invalid', '가상 의사 D', 1),
  (5, 'pending@example.invalid', '가상 가입자 E', 1);

INSERT INTO memberships VALUES
  (1, 1, 'physician', 'head', '2026-11-07T00:00:00Z', NULL),
  (2, 1, 'physician', 'doctor', '2026-11-07T00:00:00Z', 1),
  (3, 1, 'physician', 'doctor', '2026-11-07T00:00:00Z', 1),
  (4, 2, 'physician', 'doctor', '2026-11-07T00:00:00Z', NULL),
  (5, 1, 'physician', 'doctor', NULL, NULL);

INSERT INTO studies VALUES
  (101, 1, 'DEMO-MR-001', 'SYNTHETIC-001', 'MR', 'web_upload', 2, '2026-11-07T01:00:00Z', NULL, NULL),
  (102, 2, 'DEMO-MR-002', 'SYNTHETIC-002', 'MR', 'web_upload', 4, '2026-11-07T02:00:00Z', NULL, NULL);

INSERT INTO study_assets VALUES
  (1001, 101, 'original', '가상 MRI 원본 — 파일 없음', NULL),
  (1002, 101, 'analysis_result', '가상 분할 결과 — 파일 없음', NULL),
  (1003, 102, 'original', '가상 MRI 원본 — 파일 없음', NULL);

INSERT INTO reports VALUES (201, 101, 'draft', 2);
INSERT INTO report_versions VALUES
  (2001, 201, 1, '가상 소견서 초안입니다. 실제 진료 정보가 아닙니다.', 2, '2026-11-07T03:00:00Z'),
  (2002, 201, 2, '가상 소견서 수정본입니다. 동료 검토 내용을 반영했습니다.', 3, '2026-11-07T03:30:00Z');

INSERT INTO notes VALUES
  (3001, 101, 2, '가상 메모: 첫 영상 확인.', '2026-11-07T03:10:00Z'),
  (3002, 101, 3, '가상 메모: 추후 비교가 필요합니다.', '2026-11-07T03:20:00Z');

INSERT INTO audit_events VALUES
  (4001, 101, 2, 'study_uploaded', '2026-11-07T01:00:00Z'),
  (4002, 101, 3, 'report_edited', '2026-11-07T03:30:00Z');
