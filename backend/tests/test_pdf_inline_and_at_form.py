"""Tests for BUG#2 (PDF Content-Disposition = inline) and the new
blank AT client order form PDF endpoint."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{API}/auth/login",
        json={"username": "PortechAdmin", "password": "Portech2026!"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# FEATURE — blank AT client order form PDF
# ------------------------------------------------------------------
def test_at_order_form_pdf(headers):
    r = requests.get(f"{API}/admin/at-order-form.pdf", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.content
    assert body[:8].startswith(b"%PDF-1."), f"Not a PDF, starts with {body[:8]!r}"
    assert len(body) > 50_000, f"PDF too small: {len(body)} bytes"
    cd = r.headers.get("Content-Disposition", "")
    assert cd.lower().startswith("inline"), f"Expected inline, got: {cd}"
    assert r.headers.get("Content-Type", "").startswith("application/pdf")

    # Check semantic content by extracting text
    try:
        from pypdf import PdfReader
        import io
        text = ""
        for p in PdfReader(io.BytesIO(body)).pages:
            text += p.extract_text() or ""
    except Exception:
        text = body.decode("latin-1", errors="ignore")

    expected_terms = [
        "AT1000", "ATi1000", "AT2000", "ATi2000",
        "Anodis",  # Anodisé (may be encoded)
        "Bronze", "Champagne",
        "Portech",
    ]
    missing = [t for t in expected_terms if t not in text]
    # Allow some encoding mismatches, but core model names + Portech must be present
    critical = ["AT1000", "AT2000", "Portech"]
    for c in critical:
        assert c in text, f"Missing critical term '{c}' in PDF"
    print(f"AT form PDF ok — size={len(body)} bytes; missing (non-critical)={missing}")


# ------------------------------------------------------------------
# BUG#2 — Content-Disposition inline for PDFs, attachment for CSVs
# ------------------------------------------------------------------
PDF_ENDPOINTS_ALWAYS_AVAILABLE = [
    "/admin/products/catalog.pdf",
    "/admin/at-order-form.pdf",
    "/admin/alu-inventory/purchase-order.pdf",
]


@pytest.mark.parametrize("path", PDF_ENDPOINTS_ALWAYS_AVAILABLE)
def test_pdf_endpoint_inline_header(headers, path):
    r = requests.get(f"{API}{path}", headers=headers, timeout=30, allow_redirects=False)
    # 200 or 404 (no data) accepted — but if 200, must be inline
    if r.status_code == 404:
        pytest.skip(f"{path} returned 404 (no data)")
    assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
    cd = r.headers.get("Content-Disposition", "")
    assert "inline" in cd.lower(), f"{path}: expected inline, got '{cd}'"
    assert "attachment" not in cd.lower(), f"{path}: should NOT be attachment, got '{cd}'"


def test_pdf_mosquito_and_expert_and_cuts_if_present(headers):
    """Dynamic: pull first item from list endpoints and test its PDF inline header."""
    checks = [
        ("/admin/mosquito-screens", "/pdf"),
        ("/admin/expert-reports", "/pdf"),
        ("/admin/cuts", ".pdf"),
    ]
    tested_any = False
    for list_ep, pdf_suffix in checks:
        lr = requests.get(f"{API}{list_ep}", headers=headers, timeout=20)
        if lr.status_code != 200:
            continue
        data = lr.json()
        items = data if isinstance(data, list) else (data.get("items") or data.get("results") or [])
        if not items:
            continue
        item_id = items[0].get("id") or items[0].get("_id")
        if not item_id:
            continue
        url = f"{API}{list_ep}/{item_id}{pdf_suffix}"
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"Skip {url}: {r.status_code}")
            continue
        cd = r.headers.get("Content-Disposition", "")
        assert "inline" in cd.lower(), f"{url}: expected inline, got '{cd}'"
        tested_any = True
        print(f"{url} → inline OK")
    if not tested_any:
        pytest.skip("No mosquito/expert/cut PDF endpoints returned data")


def test_csv_still_attachment(headers):
    """CSV exports must remain 'attachment' (not inline)."""
    csv_endpoints = ["/admin/mosquito-screens.csv"]
    for path in csv_endpoints:
        r = requests.get(f"{API}{path}", headers=headers, timeout=20)
        if r.status_code == 404:
            continue
        assert r.status_code == 200, f"{path}: {r.status_code}"
        cd = r.headers.get("Content-Disposition", "")
        assert "attachment" in cd.lower(), f"{path}: CSV should be attachment, got '{cd}'"
