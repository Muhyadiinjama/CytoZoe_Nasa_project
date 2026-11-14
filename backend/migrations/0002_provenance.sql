-- v2: explicit provenance class per dataset. Rows are reconciled against the manifest at startup:
-- NASA_PINNED_VERIFIED only when the stored SHA-256 is registered as a reviewed NASA snapshot.
ALTER TABLE datasets ADD COLUMN provenance TEXT NOT NULL DEFAULT 'UNVERIFIED_LEGACY'
  CHECK (provenance IN ('NASA_PINNED_VERIFIED', 'RESEARCH_IMPORTED_UNVERIFIED', 'MISSION_ADAPTER_TEST', 'UNVERIFIED_LEGACY'));
CREATE INDEX idx_datasets_kind_provenance ON datasets (kind, provenance)
