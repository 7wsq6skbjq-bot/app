"""Integration test for the Gemini Vision plan extraction endpoint /api/admin/cuts/extract.

This complements test_cuts.py (which covers optimizer/DXF/CRUD) by exercising the
real Gemini Vision call with a synthetic PNG plan. Item extraction may be empty
on a poor synthetic input; we only require HTTP 200 + the documented response
shape.
"""
import io
import os

import pytest
import requests

BACKEND_INTERNAL_URL = os.environ.get("BACKEND_INTERNAL_URL", "http://localhost:8001")
API = f"{BACKEND_INTERNAL_URL}/api"


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(
        f"{API}/auth/login",
        json={"username": "PortechAdmin", "password": "Portech2026!"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _build_synthetic_plan_png() -> bytes:
    """Draw a plan-like image with two dimensioned items."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
        ft = f
    d.text((40, 40), "PLAN ATELIER — PROJET TEST", fill="black", font=f)
    d.rectangle([80, 140, 1120, 360], outline="black", width=3)
    d.text((90, 100), "CADRE alu CS68 — 2400mm × 2", fill="black", font=ft)
    d.line([(80, 380), (1120, 380)], fill="black", width=2)
    d.text((90, 400), "Linteau 2150mm × 2 (profil CS68)", fill="black", font=ft)
    d.rectangle([200, 460, 720, 720], outline="blue", width=2)
    d.text((210, 730), "VITRAGE 1980 × 1100 ép 6mm × 2", fill="blue", font=ft)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# /extract endpoint — auth guard
def test_extract_requires_auth():
    r = requests.post(f"{API}/admin/cuts/extract")
    assert r.status_code in (401, 403)


# /extract endpoint — bad extension
def test_extract_rejects_bad_extension(auth_headers):
    r = requests.post(
        f"{API}/admin/cuts/extract",
        headers=auth_headers,
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert r.status_code == 400


# /extract endpoint — happy path returns documented schema
def test_extract_plan_synthetic_png(auth_headers):
    png = _build_synthetic_plan_png()
    r = requests.post(
        f"{API}/admin/cuts/extract",
        headers=auth_headers,
        files={"file": ("plan.png", png, "image/png")},
        timeout=60,
    )
    # Gemini may rate-limit or partial-respond, but on success must be 200
    assert r.status_code == 200, f"status={r.status_code} body={r.text[:500]}"
    body = r.json()
    # Documented contract (new multi-elevation schema)
    for key in ("elevations", "unit_detected", "confidence", "warnings",
                "source_filename", "source_type"):
        assert key in body, f"missing key '{key}' in response: {body.keys()}"
    assert isinstance(body["elevations"], list)
    assert len(body["elevations"]) >= 1, "must always return at least 1 elevation"
    assert body["source_type"] in ("image", "pdf")
    assert isinstance(body["warnings"], list)
    # Each elevation must have an id, code, type, and a list of items.
    for ev in body["elevations"]:
        assert ev.get("id")
        assert ev.get("code")
        assert ev.get("elevation_type") in ("door", "flush_glaze", "curtain_wall", "mixed")
        assert isinstance(ev.get("items"), list)
        for it in ev["items"]:
            assert it.get("id")
            assert it.get("item_type") in (
                "frame", "glass", "panel", "hardware", "hole", "other",
            )
            assert isinstance(it.get("qty", 1), int)
