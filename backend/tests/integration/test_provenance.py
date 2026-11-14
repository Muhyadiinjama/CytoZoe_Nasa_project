"""M2 — provenance and import integrity (B09–B11, B23; PRD v3 §5.4)."""
from __future__ import annotations

import pytest

from conftest import CMP_FILE, RAD_FILE, needs_raw

pytestmark = needs_raw


def _tampered() -> bytes:
    raw = CMP_FILE.read_bytes()
    out = raw.replace(b",1.37,", b",9.99,", 1)
    assert out != raw
    return out


def test_b10_first_import_of_wrong_hash_is_rejected_on_empty_db(client):
    """The audited hole: a schema-valid but altered file must never become 'NASA' data, even on a fresh DB."""
    r = client.post("/api/import", files={"file": ("cmp.csv", _tampered(), "text/csv")})
    body = r.json()
    assert r.status_code == 422 and body["code"] == "SOURCE_HASH_MISMATCH"
    assert body["details"]["received_sha256"] not in body["details"]["expected_sha256"]
    assert client.get("/api/datasets").json() == []
    assert client.get("/api/participants").json()["code"] == "NO_DATA"
    assert client.get("/api/readyz").json()["state"] == "DATASET_NOT_IMPORTED"
    # Same through the CLI/service path.
    from app.errors import AppError
    from app.services import importer

    with pytest.raises(AppError) as exc:
        importer.import_bytes(_tampered(), allow_new_version=True)
    assert exc.value.code == "SOURCE_HASH_MISMATCH"


def test_pinned_import_is_marked_verified_everywhere(loaded_client):
    ds = {d["id"]: d for d in loaded_client.get("/api/datasets").json()}
    assert {d["provenance"] for d in ds.values()} == {"NASA_PINNED_VERIFIED"}
    ev = loaded_client.get("/api/evidence/osd575-cmp:C001_serum_L-3:creatinine").json()
    assert ev["source"]["provenance"] == "NASA_PINNED_VERIFIED"
    env = loaded_client.get("/api/environment").json()
    assert env["dataset"]["provenance"] == "NASA_PINNED_VERIFIED"


def test_legacy_unverified_rows_are_not_served_as_nasa(loaded_client):
    """A DB created before the trust gate (e.g. holding tampered bytes) is reconciled and blocked."""
    from app import db
    from app.services import importer

    with db.session() as conn:
        conn.execute("UPDATE datasets SET sha256 = 'deadbeef' WHERE kind = 'HEALTH_CMP'")
    importer.reconcile_provenance()
    r = loaded_client.get("/api/health", params={"participant": "C001", "sample": "L-3"})
    assert r.status_code == 409 and r.json()["code"] == "SOURCE_HASH_MISMATCH"
    assert loaded_client.get("/api/readyz").json()["state"] == "SOURCE_HASH_MISMATCH"
    # Radiation (still verified) keeps working — the cases are independent.
    assert loaded_client.get("/api/environment").status_code == 200


def test_b11_registered_new_version_replaces_atomically_and_keeps_frozen_evidence(loaded_client, register_hash):
    from app.engines.quality import sha256_bytes
    from app.services import importer

    new = CMP_FILE.read_bytes().replace(b",1.37,", b",1.38,", 1)
    rid = loaded_client.post("/api/reviews", json={"finding_id": "osd575-cmp:C001_serum_L-3:creatinine",
                                                   "note": "reviewed against original snapshot"}).json()["review"]["id"]
    register_hash("HEALTH_CMP", sha256_bytes(new))
    # Failure mid-transaction: nothing changes.
    with pytest.raises(RuntimeError):
        importer.import_bytes(new, allow_new_version=True, _fail_after_delete=True)
    assert loaded_client.get("/api/evidence/osd575-cmp:C001_serum_L-3:creatinine").json()["measurement"]["value"] == 1.37
    # Deliberate replacement succeeds and is verified.
    res = importer.import_bytes(new, allow_new_version=True)
    assert res["status"] == "IMPORTED_NEW_VERSION" and res["provenance"] == "NASA_PINNED_VERIFIED"
    assert loaded_client.get("/api/evidence/osd575-cmp:C001_serum_L-3:creatinine").json()["measurement"]["value"] == 1.38
    # The saved review still shows the evidence and source hash it was reviewed against.
    detail = loaded_client.get(f"/api/reviews/{rid}").json()
    assert detail["evidence_snapshot"]["measurement"]["value"] == 1.37
    assert detail["dataset_sha256"] == sha256_bytes(CMP_FILE.read_bytes())
    exported = loaded_client.get("/api/export", params={"format": "json"}).json()
    assert exported["health"]["reviews"][0]["evidence_snapshot"]["measurement"]["value"] == 1.37


def test_b09_radlab_wrong_hash_and_idempotence(client):
    from app.services import importer

    assert importer.import_bytes(RAD_FILE.read_bytes())["status"] == "IMPORTED"
    assert importer.import_bytes(RAD_FILE.read_bytes())["status"] == "ALREADY_IMPORTED"
    altered = RAD_FILE.read_bytes() + b'"2022-03-01T23:59:59","DosTel1",1.0\n'
    r = client.post("/api/import", files={"file": ("rad.csv", altered, "text/csv")})
    assert r.status_code == 422 and r.json()["code"] == "SOURCE_HASH_MISMATCH"
    assert client.get("/api/environment").json()["quality"]["raw_rows"] == 1202


def test_b23_abuse_cases(client):
    header = b"timestamp,instrument_id,absorbed_dose_rate\n"
    many = header + b'"2022-03-01T00:00:00","DosTel1",1\n' * 100_001
    r = client.post("/api/import", files={"file": ("big.csv", many, "text/csv")})
    assert r.status_code in (413, 422) and r.json()["code"] in ("TOO_MANY_ROWS", "FILE_TOO_LARGE")
    long_line = header + b'"2022-03-01T00:00:00","DosTel1",' + b"1" * 25_000 + b"\n"
    assert client.post("/api/import", files={"file": ("x.csv", long_line, "text/csv")}).json()["code"] == "LINE_TOO_LONG"
    for name in ("../../etc/passwd.csv", "..\\..\\win.ini.csv"):
        r = client.post("/api/import", files={"file": (name, b"a,b\n1,2\n", "text/csv")})
        assert r.status_code == 422 and "etc" not in r.text and "win.ini" not in r.text
    r = client.post("/api/import", files={"file": ("x.csv", b"Sample Name');DROP TABLE reviews;--\n", "text/csv")})
    assert r.status_code == 422
    assert client.get("/api/reviews").status_code in (200,)
