"""Backend smoke tests for AI OCR receipt scan flow (Gemini Vision).

Covers:
- POST /api/admin/expenses/ocr-scan (synthetic PNG, returns temp_filename + extracted keys)
- POST /api/admin/expenses/{id}/receipt/attach-temp (moves temp to permanent)
- POST /api/admin/expenses/{id}/receipt/ocr (re-scan existing attached receipt)
- POST /api/admin/expenses/{id}/receipt (legacy direct upload still works)
- Auth guards on all OCR endpoints
"""
import io
import os
from pathlib import Path

import pytest
import requests
from PIL import Image, ImageDraw, ImageFont

# Resolve backend URL
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"
ADMIN_USER = "PortechAdmin"
ADMIN_PASS = "Portech2026!"


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_receipt_png() -> bytes:
    """Generate a synthetic receipt JPEG with PIL."""
    img = Image.new("RGB", (480, 360), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    y = 20
    for line in [
        "BOUTIQUE TEST",
        "123 rue Principale, Montreal",
        "Date: 2026-01-15",
        "Facture: TEST-0001",
        "",
        "Sous-total: 100.00",
        "TPS:         5.00",
        "TVQ:         9.98",
        "Total:     114.98",
    ]:
        d.text((20, y), line, fill="black", font=font)
        y += 32
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---- Auth guards ----
class TestAuthGuards:
    def test_ocr_scan_requires_auth(self):
        r = requests.post(f"{API}/admin/expenses/ocr-scan",
                          files={"file": ("r.png", b"x", "image/png")})
        assert r.status_code in (401, 403)

    def test_attach_temp_requires_auth(self):
        r = requests.post(f"{API}/admin/expenses/abc/receipt/attach-temp",
                          params={"temp_filename": "_tmp_x.png"})
        assert r.status_code in (401, 403)

    def test_existing_receipt_ocr_requires_auth(self):
        r = requests.post(f"{API}/admin/expenses/abc/receipt/ocr")
        assert r.status_code in (401, 403)


# ---- Full OCR flow ----
class TestOcrFlow:
    @pytest.fixture(scope="class")
    def receipt_bytes(self):
        return _make_receipt_png()

    @pytest.fixture(scope="class")
    def scan_result(self, auth_headers, receipt_bytes):
        files = {"file": ("synth_receipt.png", receipt_bytes, "image/png")}
        r = requests.post(f"{API}/admin/expenses/ocr-scan",
                          headers=auth_headers, files=files, timeout=90)
        assert r.status_code == 200, f"ocr-scan failed: {r.status_code} {r.text}"
        return r.json()

    def test_ocr_scan_contract(self, scan_result):
        # temp_filename always returned
        assert "temp_filename" in scan_result
        assert scan_result["temp_filename"].startswith("_tmp_")
        # Required keys present (values may be null per spec)
        for k in ("subtotal", "tps", "tvq", "total", "suggested_category"):
            assert k in scan_result, f"missing key {k} in {scan_result}"
        # suggested_category must be a known string (or 'Autre')
        assert isinstance(scan_result["suggested_category"], str)

    def test_ocr_scan_extracts_values_if_confident(self, scan_result):
        """Soft assertion — log values, don't fail on low confidence."""
        print(f"OCR result: {scan_result}")
        # If confidence is provided and high, values should be numeric
        conf = scan_result.get("confidence")
        if conf and conf > 0.5:
            for k in ("subtotal", "tps", "tvq", "total"):
                v = scan_result.get(k)
                if v is not None:
                    assert isinstance(v, (int, float))

    def test_create_expense_then_attach_temp(self, auth_headers, scan_result):
        # Create expense
        payload = {
            "date": "2026-01-15",
            "supplier_name": "BOUTIQUE TEST",
            "category": scan_result.get("suggested_category") or "Autre",
            "subtotal": scan_result.get("subtotal") or 100.0,
            "tps": scan_result.get("tps") or 5.0,
            "tvq": scan_result.get("tvq") or 9.98,
            "total": scan_result.get("total") or 114.98,
            "payment_method": "Carte crédit",
            "status": "Payée",
            "description": "TEST_OCR synthetic receipt",
        }
        r = requests.post(f"{API}/admin/expenses",
                          headers={**auth_headers, "Content-Type": "application/json"},
                          json=payload)
        assert r.status_code == 201, f"create expense failed: {r.text}"
        exp = r.json()
        exp_id = exp["id"]

        # Attach temp
        temp_fn = scan_result["temp_filename"]
        r2 = requests.post(
            f"{API}/admin/expenses/{exp_id}/receipt/attach-temp",
            headers=auth_headers,
            params={"temp_filename": temp_fn},
        )
        assert r2.status_code == 200, f"attach-temp failed: {r2.text}"
        body = r2.json()
        assert "receipt_filename" in body
        assert body["receipt_filename"].startswith(exp_id + "_")

        # GET expense → receipt_filename persisted
        r3 = requests.get(f"{API}/admin/expenses", headers=auth_headers)
        assert r3.status_code == 200
        match = next((e for e in r3.json() if e["id"] == exp_id), None)
        assert match is not None
        assert match.get("receipt_filename") == body["receipt_filename"]

        # Re-OCR the attached receipt
        r4 = requests.post(f"{API}/admin/expenses/{exp_id}/receipt/ocr",
                           headers=auth_headers, timeout=90)
        assert r4.status_code == 200, f"rescan failed: {r4.text}"
        rescan = r4.json()
        # Same contract as ocr-scan (minus temp_filename)
        for k in ("subtotal", "tps", "tvq", "total", "suggested_category"):
            assert k in rescan

        # Cleanup
        requests.delete(f"{API}/admin/expenses/{exp_id}", headers=auth_headers)

    def test_attach_temp_rejects_bad_filename(self, auth_headers):
        # Create dummy expense
        payload = {
            "date": "2026-01-15",
            "supplier_name": "TEST_BAD",
            "description": "TEST_BAD",
            "category": "Autre",
            "subtotal": 1.0, "tps": 0.05, "tvq": 0.10, "total": 1.15,
        }
        r = requests.post(f"{API}/admin/expenses",
                          headers={**auth_headers, "Content-Type": "application/json"},
                          json=payload)
        assert r.status_code == 201
        exp_id = r.json()["id"]
        # Bad temp_filename
        bad = requests.post(
            f"{API}/admin/expenses/{exp_id}/receipt/attach-temp",
            headers=auth_headers, params={"temp_filename": "evil.png"})
        assert bad.status_code == 400
        # Nonexistent temp_filename (valid prefix)
        missing = requests.post(
            f"{API}/admin/expenses/{exp_id}/receipt/attach-temp",
            headers=auth_headers, params={"temp_filename": "_tmp_doesnotexist.png"})
        assert missing.status_code == 404
        requests.delete(f"{API}/admin/expenses/{exp_id}", headers=auth_headers)

    def test_ocr_scan_rejects_bad_extension(self, auth_headers):
        r = requests.post(f"{API}/admin/expenses/ocr-scan",
                          headers=auth_headers,
                          files={"file": ("x.exe", b"abc", "application/octet-stream")})
        assert r.status_code == 400


# ---- Legacy direct upload path still works ----
class TestLegacyUpload:
    def test_direct_receipt_upload(self, auth_headers):
        # Create expense
        payload = {
            "date": "2026-01-15", "supplier_name": "TEST_LEGACY",
            "description": "TEST_LEGACY direct upload",
            "category": "Autre",
            "subtotal": 10.0, "tps": 0.5, "tvq": 1.0, "total": 11.5,
        }
        r = requests.post(f"{API}/admin/expenses",
                          headers={**auth_headers, "Content-Type": "application/json"},
                          json=payload)
        assert r.status_code == 201
        exp_id = r.json()["id"]
        # Upload receipt directly (no OCR)
        png = _make_receipt_png()
        r2 = requests.post(f"{API}/admin/expenses/{exp_id}/receipt",
                           headers=auth_headers,
                           files={"file": ("rec.png", png, "image/png")})
        assert r2.status_code == 201
        assert r2.json()["receipt_filename"].startswith(exp_id + "_")
        # Cleanup
        requests.delete(f"{API}/admin/expenses/{exp_id}", headers=auth_headers)
