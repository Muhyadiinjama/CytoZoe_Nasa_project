"""Bundled landing imagery is served locally with correct image types (nosniff would block text/plain)."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("name,ctype", [("hero.webp", "image/webp"), ("hero.avif", "image/avif"),
                                        ("font.woff2", "font/woff2"), ("mark.svg", "image/svg+xml")])
def test_media_served_with_image_content_type(tmp_path, monkeypatch, data_dir, name, ctype):
    from fastapi.testclient import TestClient

    from app import config
    from app.main import create_app

    dist = tmp_path / "dist"
    (dist / "media").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>t</title>", encoding="utf-8")
    (dist / "media" / name).write_bytes(b"\x00binary")
    monkeypatch.setattr(config, "FRONTEND_DIST", dist)
    res = TestClient(create_app()).get(f"/media/{name}")
    assert res.status_code == 200
    assert res.headers["content-type"].split(";")[0] == ctype
    assert res.headers["x-content-type-options"] == "nosniff"


def test_media_path_traversal_still_falls_back_to_index(tmp_path, monkeypatch, data_dir):
    from fastapi.testclient import TestClient

    from app import config
    from app.main import create_app

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>index</title>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    monkeypatch.setattr(config, "FRONTEND_DIST", dist)
    res = TestClient(create_app()).get("/media/../../secret.txt")
    assert "nope" not in res.text
