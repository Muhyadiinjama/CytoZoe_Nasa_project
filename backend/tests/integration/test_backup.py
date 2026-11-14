"""Release check: backup → change → immediate restore round-trip (regression for same-second filename collision)."""
from __future__ import annotations

import importlib.util
import sys

from conftest import ROOT, needs_raw

pytestmark = needs_raw


def _load_script():
    spec = importlib.util.spec_from_file_location("backup_db", ROOT / "scripts" / "backup_db.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["backup_db"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_backup_restore_round_trip_same_second(loaded_client, data_dir):
    bk = _load_script()
    rid = loaded_client.post("/api/reviews", json={"finding_id": "osd575-cmp:C001_serum_L-3:creatinine",
                                                   "note": "before backup"}).json()["review"]["id"]
    saved = bk.backup(data_dir / "backups")
    loaded_client.patch(f"/api/reviews/{rid}", json={"version": 1, "note": "changed after backup"})
    bk.restore(saved)  # runs within the same second as the backup
    assert loaded_client.get(f"/api/reviews/{rid}").json()["note"] == "before backup"
    files = sorted(p.name for p in (data_dir / "backups").iterdir())
    assert saved.name in files and any(n.startswith("pre-restore-") for n in files)
