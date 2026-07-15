"""Tests for the 2 UX bugs + new AT client order form parser.

Iteration 12 (Jan 2026).
"""
import io
import os

import pytest
import requests
from pypdf import PdfReader, PdfWriter

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "PortechAdmin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "Portech2026!")


@pytest.fixture(scope="module")
def token() -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS},
                      timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    return body.get("access_token") or body.get("token")


@pytest.fixture(scope="module")
def auth_headers(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def blank_form_bytes(auth_headers) -> bytes:
    r = requests.get(f"{BASE_URL}/api/admin/at-order-form.pdf",
                     headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.content[:5] == b"%PDF-", "Response is not a PDF"
    return r.content


# ═══ BUG #1 — Section 6 swings AcroForm layout ══════════════════════════════
class TestBlankForm:
    """Verify the blank AT order form structure (BUG #1 and #2 fixes)."""

    def test_pdf_header_and_page_count(self, blank_form_bytes):
        assert blank_form_bytes.startswith(b"%PDF-1.4")
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        assert len(reader.pages) == 2, f"Expected 2 pages, got {len(reader.pages)}"

    def test_form_has_all_required_acroform_fields(self, blank_form_bytes):
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        fields = reader.get_fields() or {}
        assert len(fields) >= 80, f"Expected ~90 fields, got {len(fields)}"

        required = [
            "dim_standard_36x84",
            "swing_ge", "swing_ge_qty",
            "swing_de", "swing_de_qty",
            "swing_pe", "swing_pe_qty",
            "swing_gi", "swing_gi_qty",
            "swing_di", "swing_di_qty",
            "swing_pi", "swing_pi_qty",
        ]
        missing = [k for k in required if k not in fields]
        assert not missing, f"Missing AcroForm fields: {missing}"

    def test_swings_qty_boxes_are_wide_enough(self, blank_form_bytes):
        """BUG #1: check that swing qty fields have a decent width (>=15mm)
        so that the label 'QTÉ' and the value are not overlapping."""
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        fields = reader.get_fields() or {}
        # pypdf exposes /Rect on the annotation via .indirect_reference/get('/Kids')
        # Simpler: iterate raw page annotations
        for page in reader.pages:
            annots = page.get("/Annots") or []
            for a in annots:
                obj = a.get_object() if hasattr(a, "get_object") else a
                name = obj.get("/T")
                if name and str(name).endswith("_qty") and str(name).startswith("swing_"):
                    rect = obj.get("/Rect")
                    if rect:
                        w = float(rect[2]) - float(rect[0])
                        # 15 mm in points = 15 / 25.4 * 72 ≈ 42.5
                        assert w >= 40, f"{name} qty box too narrow ({w:.1f}pt)"


# ═══ FEATURE — AcroForm parser round trip ═══════════════════════════════════
def _fill_form(blank: bytes, values: dict) -> bytes:
    """Populate the AcroForm fields and return the filled bytes."""
    reader = PdfReader(io.BytesIO(blank))
    writer = PdfWriter(clone_from=reader)
    for i, page in enumerate(writer.pages):
        writer.update_page_form_field_values(page, values)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestPortechFormParser:
    """End-to-end: blank form → fill → POST /parse-portech-form."""

    def test_parse_filled_form_returns_expected_payload(
        self, blank_form_bytes, auth_headers,
    ):
        values = {
            "client_1": "Vitrerie ABC",
            "po_number_2": "PO-2026-042",
            "model_ati2000": "/Yes",
            "dim_standard_36x84": "/Yes",
            "finish_ext_2": "/Yes",   # Bronze
            "finish_int_5": "/Yes",   # Mill finish
            "swing_de": "/Yes", "swing_de_qty": "3",
            "swing_pi": "/Yes", "swing_pi_qty": "1",
            "hinge_cont_hd": "/Yes",
            "hinge_qty_3": "/Yes",
            "handle_3": "/Yes",       # pull 12 back-to-back
            "lock_main_5": "/Yes",    # 4510
            "panic_0": "/Yes",        # 8400
            "strike_1": "/Yes",       # electric strike
            "other_0": "/Yes",        # astragal
            "other_3": "/Yes",        # moulure thermo
            "thr_iso": "/Yes",
        }
        filled = _fill_form(blank_form_bytes, values)

        r = requests.post(
            f"{BASE_URL}/api/admin/at-orders/parse-portech-form",
            headers=auth_headers,
            files={"file": ("filled.pdf", filled, "application/pdf")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()

        # Meta
        assert data["client"] == "Vitrerie ABC"
        assert data["order_number"] == "PO-2026-042"
        assert data["finish_exterior"] == "Bronze"
        assert data["finish_interior"] == "Mill finish"

        # Doors
        doors = data["doors"]
        assert len(doors) == 2, f"Expected 2 doors (DE + PI), got {len(doors)}"
        # Locate the DE and PI doors
        by_hand = {d["hand"]: d for d in doors}
        assert "DE" in by_hand and "PI" in by_hand

        de = by_hand["DE"]
        assert de["series"] == "ATi2000"
        assert de["width_in"] == 36.0
        assert de["height_in"] == 84.0
        assert de["qty"] == 3
        assert de["glazing"] == "thermos"

        hw = de["hardware"]
        assert hw["hinge_continuous_hd"] is True
        assert hw["hinge_4_5x4_qty"] == 3
        assert hw["pull_12_back_to_back"] is True
        assert hw["lock_4510_ar"] is True
        assert hw["panic_8400_ar"] is True
        assert hw["strike_electric"] is True
        assert hw["astragal"] is True
        assert hw["moulding_thermo"] is True
        assert hw["sill_type_insulated"] in ("Précisé", "Précisé".strip())

        pi = by_hand["PI"]
        assert pi["qty"] == 1
        assert pi["hand"] == "PI"

    def test_parse_rejects_non_acroform_pdf(self, auth_headers):
        """A plain PDF (no interactive fields) must be rejected with 400 and
        a French message mentioning 'aucun champ interactif'."""
        # Build a tiny blank PDF with no AcroForm
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)

        r = requests.post(
            f"{BASE_URL}/api/admin/at-orders/parse-portech-form",
            headers=auth_headers,
            files={"file": ("plain.pdf", buf.getvalue(), "application/pdf")},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        body = r.json()
        msg = str(body.get("detail") or body).lower()
        assert "aucun champ interactif" in msg, f"Unexpected detail: {msg}"


# ═══ REGRESSION — old Gemini OCR endpoint still exists ══════════════════════
class TestRegressionOldParse:
    def test_old_parse_endpoint_still_routed(self, auth_headers):
        """Just check route exists — may return 502 (Gemini fail) or 200.
        A 404 would mean the endpoint was accidentally removed."""
        # Send an empty PDF; we accept anything except 404/405.
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buf = io.BytesIO()
        writer.write(buf)
        r = requests.post(
            f"{BASE_URL}/api/admin/at-orders/parse",
            headers=auth_headers,
            files={"file": ("empty.pdf", buf.getvalue(), "application/pdf")},
            timeout=60,
        )
        assert r.status_code not in (404, 405), (
            f"/api/admin/at-orders/parse missing (got {r.status_code})"
        )
