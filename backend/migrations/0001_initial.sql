-- CytoZoe schema v1. Public research data and local reviewer notes are kept in separate tables.
CREATE TABLE datasets (
  id              TEXT PRIMARY KEY,
  kind            TEXT NOT NULL CHECK (kind IN ('HEALTH_CMP', 'ENV_RADIATION')),
  title           TEXT NOT NULL,
  provider        TEXT NOT NULL,
  source_url      TEXT NOT NULL,
  download_url    TEXT NOT NULL,
  file_name       TEXT NOT NULL,
  fetched_at      TEXT,
  imported_at     TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  byte_count      INTEGER NOT NULL,
  license_note    TEXT NOT NULL,
  citation        TEXT NOT NULL,
  schema_version  TEXT NOT NULL,
  parser_version  TEXT NOT NULL,
  quality_json    TEXT NOT NULL
);

CREATE TABLE import_runs (
  id          TEXT PRIMARY KEY,
  dataset_id  TEXT,
  sha256      TEXT NOT NULL,
  status      TEXT NOT NULL,
  report_json TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE TABLE health_observations (
  id             TEXT PRIMARY KEY,
  dataset_id     TEXT NOT NULL REFERENCES datasets(id),
  source_row     INTEGER NOT NULL,
  participant_id TEXT NOT NULL,
  sample_id      TEXT NOT NULL,
  visit          TEXT NOT NULL,
  phase          TEXT NOT NULL CHECK (phase IN ('PREFLIGHT', 'POSTFLIGHT')),
  relative_day   INTEGER NOT NULL,
  visit_order    INTEGER NOT NULL,
  marker         TEXT NOT NULL,
  value          REAL,
  value_raw      TEXT NOT NULL,
  unit           TEXT NOT NULL,
  source_unit    TEXT NOT NULL,
  source_column  TEXT NOT NULL,
  range_low      REAL,
  range_high     REAL,
  UNIQUE (dataset_id, sample_id, marker)
);
CREATE INDEX idx_health_participant ON health_observations (participant_id, marker);

CREATE TABLE radiation_observations (
  id               TEXT PRIMARY KEY,
  dataset_id       TEXT NOT NULL REFERENCES datasets(id),
  source_row       INTEGER NOT NULL,
  instrument_id    TEXT NOT NULL,
  source_timestamp TEXT NOT NULL,
  rate             REAL,
  rate_raw         TEXT NOT NULL,
  unit             TEXT NOT NULL,
  quality_status   TEXT NOT NULL CHECK (quality_status IN
    ('ACCEPTED', 'DUPLICATE_CONFLICT', 'DUPLICATE_IDENTICAL', 'INVALID_TIMESTAMP', 'INVALID_RATE', 'MISSING_VALUE')),
  quality_detail   TEXT
);
CREATE INDEX idx_radiation_dataset ON radiation_observations (dataset_id, source_row);

CREATE TABLE findings (
  id             TEXT PRIMARY KEY,
  kind           TEXT NOT NULL CHECK (kind IN ('HEALTH_OBSERVATION', 'ENV_OBSERVATION', 'DATA_QUALITY')),
  observation_id TEXT,
  dataset_id     TEXT NOT NULL REFERENCES datasets(id),
  dataset_sha256 TEXT NOT NULL,
  rule_version   TEXT NOT NULL,
  evidence_json  TEXT NOT NULL,
  created_at     TEXT NOT NULL
);

CREATE TABLE reviews (
  id             TEXT PRIMARY KEY,
  finding_id     TEXT NOT NULL UNIQUE REFERENCES findings(id),
  case_kind      TEXT NOT NULL CHECK (case_kind IN ('health', 'environment')),
  participant_id TEXT,
  instrument_id  TEXT,
  title          TEXT NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('OPEN', 'FOLLOW_UP_REQUESTED', 'REVIEWED')),
  note           TEXT NOT NULL,
  follow_up_date TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  version        INTEGER NOT NULL DEFAULT 1,
  -- Cross-case guard: an environment review can never carry a health participant.
  CHECK (case_kind = 'health' OR participant_id IS NULL),
  CHECK (case_kind = 'environment' OR instrument_id IS NULL)
);

CREATE TABLE review_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id   TEXT NOT NULL REFERENCES reviews(id),
  action      TEXT NOT NULL,
  before_json TEXT,
  after_json  TEXT NOT NULL,
  timestamp   TEXT NOT NULL
);
CREATE INDEX idx_review_events ON review_events (review_id, id);
