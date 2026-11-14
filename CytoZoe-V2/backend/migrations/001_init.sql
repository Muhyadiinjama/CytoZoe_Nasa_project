-- CytoZoe schema v1. Public research data and local reviewer notes live in separate tables.
CREATE TABLE datasets (
  id             TEXT PRIMARY KEY,               -- e.g. OSD-575-CMP:5eb1e7f025dd
  kind           TEXT NOT NULL CHECK (kind IN ('HEALTH_CMP','ENV_RADIATION')),
  title          TEXT NOT NULL,
  file_name      TEXT NOT NULL,
  source_url     TEXT NOT NULL,
  fetched_at     TEXT,
  imported_at    TEXT NOT NULL,
  sha256         TEXT NOT NULL,
  license_note   TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  parser_version TEXT NOT NULL,
  quality_json   TEXT NOT NULL,
  is_active      INTEGER NOT NULL DEFAULT 0,
  UNIQUE (kind, sha256)
);

CREATE TABLE health_observations (
  id            TEXT PRIMARY KEY,                -- stable: dataset sha + sample id + marker
  dataset_id    TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  source_row    INTEGER NOT NULL,                -- line number in the source file (header = line 1)
  participant_id TEXT NOT NULL,
  sample_id     TEXT NOT NULL,
  specimen      TEXT NOT NULL,
  phase         TEXT NOT NULL CHECK (phase IN ('PREFLIGHT','POSTFLIGHT')),
  visit         TEXT NOT NULL,
  relative_day  INTEGER NOT NULL,
  visit_order   INTEGER NOT NULL,
  marker        TEXT NOT NULL,
  value         REAL,
  raw_value     TEXT NOT NULL,
  unit          TEXT NOT NULL,
  range_low     REAL,
  range_high    REAL,
  UNIQUE (dataset_id, sample_id, marker)
);
CREATE INDEX ix_health_lookup ON health_observations(dataset_id, participant_id, marker);

CREATE TABLE radiation_observations (
  id               TEXT PRIMARY KEY,
  dataset_id       TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  source_row       INTEGER NOT NULL,
  instrument_id    TEXT NOT NULL,
  source_timestamp TEXT NOT NULL,                -- kept exactly as provided by the source
  epoch_ms         INTEGER,                      -- arithmetic only; the source states no timezone
  rate             REAL,
  raw_rate         TEXT NOT NULL,
  unit             TEXT NOT NULL,
  quality_status   TEXT NOT NULL CHECK (quality_status IN
                    ('ACCEPTED','DUPLICATE_CONFLICT','DUPLICATE_IDENTICAL','INVALID_TIMESTAMP','INVALID_RATE','MISSING_VALUE'))
);
CREATE INDEX ix_rad_lookup ON radiation_observations(dataset_id, instrument_id, epoch_ms);

CREATE TABLE findings (
  id             TEXT PRIMARY KEY,               -- evidence id; stable for the same source bytes + rule version
  kind           TEXT NOT NULL CHECK (kind IN ('HEALTH_OBSERVATION','DATA_QUALITY','ENV_OBSERVATION')),
  observation_id TEXT,
  dataset_id     TEXT NOT NULL REFERENCES datasets(id),
  rule_version   TEXT NOT NULL,
  evidence_json  TEXT NOT NULL,                  -- frozen at first review so later changes never rewrite past reports
  created_at     TEXT NOT NULL
);

CREATE TABLE reviews (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  finding_id     TEXT NOT NULL UNIQUE REFERENCES findings(id),
  status         TEXT NOT NULL CHECK (status IN ('OPEN','FOLLOW_UP_REQUESTED','REVIEWED')),
  note           TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 4000),
  follow_up_date TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  version        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE review_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id   INTEGER NOT NULL REFERENCES reviews(id),
  action      TEXT NOT NULL,
  before_json TEXT,
  after_json  TEXT,
  timestamp   TEXT NOT NULL
);

CREATE TABLE import_runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind        TEXT NOT NULL,
  file_name   TEXT NOT NULL,
  sha256      TEXT,
  status      TEXT NOT NULL CHECK (status IN ('IMPORTED','ALREADY_IMPORTED','FAILED')),
  report_json TEXT NOT NULL,
  created_at  TEXT NOT NULL
);
