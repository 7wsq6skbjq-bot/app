"""Iteration 13 — AT order form: verify Section 7 restructure, threshold label,
and parser mapping hinge_std/hinge_qty_3/thr_supply.
"""
import io
import os
import subprocess
import tempfile

import pytest
import requests
from pypdf import PdfReader, PdfWriter

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "PortechAdmin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "Portech2026!")


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS},
                      timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def blank_form_bytes(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/at-order-form.pdf",
                     headers=auth_headers, timeout=30)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"
    return r.content


class TestFormStructure:
    def test_two_pages(self, blank_form_bytes):
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        assert len(reader.pages) == 2

    def test_field_count_around_90(self, blank_form_bytes):
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        fields = reader.get_fields() or {}
        assert 85 <= len(fields) <= 100, f"Got {len(fields)} fields"

    def test_required_hinge_and_threshold_fields(self, blank_form_bytes):
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        fields = reader.get_fields() or {}
        required = [
            "hinge_std", "hinge_qty_1", "hinge_qty_2", "hinge_qty_3", "hinge_qty_4",
            "hinge_cont", "hinge_cont_hd", "hinge_supply_install",
            "thr_supply",
            "dim_standard_36x84",
            "swing_ge", "swing_de", "swing_pe", "swing_gi", "swing_di", "swing_pi",
            "swing_ge_qty", "swing_de_qty", "swing_pe_qty",
            "swing_gi_qty", "swing_di_qty", "swing_pi_qty",
        ]
        missing = [k for k in required if k not in fields]
        assert not missing, f"Missing fields: {missing}"


class TestBug3ThresholdLabel:
    """BUG #3: 'Fournir (par Portech)' → 'Fournir'."""

    def test_par_portech_removed_from_threshold(self, blank_form_bytes):
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        txt = "".join((p.extract_text() or "") for p in reader.pages)
        # 'par Portech' should not appear near threshold section
        # (it may appear elsewhere as brand mention; verify context around 'Fournir' in Section 11 SEUIL)
        assert "Fournir" in txt, "Expected 'Fournir' option to still be present"
        # Sanity: look for it not being followed by '(par Portech)'
        assert "Fournir (par Portech)" not in txt, \
            "Threshold option must be plain 'Fournir', not 'Fournir (par Portech)'"


class TestSection7HingeQtyLayout:
    """BUG #2: hinge qty boxes 1..4 must be on same y as hinge_std (Charnière 4½),
    and hinge_cont / hinge_cont_hd / hinge_supply_install on a different (lower) row.
    """

    def test_hinge_qty_boxes_align_with_hinge_std_row(self, blank_form_bytes):
        reader = PdfReader(io.BytesIO(blank_form_bytes))
        rects = {}
        for page in reader.pages:
            annots = page.get("/Annots") or []
            for a in annots:
                obj = a.get_object() if hasattr(a, "get_object") else a
                name = obj.get("/T")
                rect = obj.get("/Rect")
                if name and rect:
                    rects[str(name)] = [float(x) for x in rect]

        # y of hinge_std
        y_std = rects["hinge_std"][1]
        for i in range(1, 5):
            y_qty = rects[f"hinge_qty_{i}"][1]
            assert abs(y_qty - y_std) < 6, (
                f"hinge_qty_{i} y={y_qty:.1f} not aligned with hinge_std y={y_std:.1f}"
            )

        y_cont = rects["hinge_cont"][1]
        # Continue row must be BELOW (lower y in PDF coord) hinge_std row
        assert y_cont < y_std - 8, (
            f"hinge_cont y={y_cont:.1f} should be well below hinge_std y={y_std:.1f}"
        )
        y_cont_hd = rects["hinge_cont_hd"][1]
        y_supply = rects["hinge_supply_install"][1]
        # They should be roughly on same row as hinge_cont
        assert abs(y_cont_hd - y_cont) < 6
        assert abs(y_supply - y_cont) < 6


def _fill_form(blank: bytes, values: dict) -> bytes:
    reader = PdfReader(io.BytesIO(blank))
    writer = PdfWriter(clone_from=reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestParserMapping:
    """Regression: hinge_std + hinge_qty_3 → hinge_4_5x4=True, hinge_4_5x4_qty=3;
    thr_supply → sill_supplied=True."""

    def test_hinge_std_qty3_and_thr_supply(self, blank_form_bytes, auth_headers):
        values = {
            "client_1": "TestCo",
            "po_number_2": "PO-13",
            "model_ati2000": "/Yes",
            "dim_standard_36x84": "/Yes",
            "swing_de": "/Yes", "swing_de_qty": "1",
            "hinge_std": "/Yes",
            "hinge_qty_3": "/Yes",
            "thr_supply": "/Yes",
        }
        filled = _fill_form(blank_form_bytes, values)
        r = requests.post(
            f"{BASE_URL}/api/admin/at-orders/parse-portech-form",
            headers=auth_headers,
            files={"file": ("f.pdf", filled, "application/pdf")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        doors = data["doors"]
        assert len(doors) >= 1
        d = doors[0]
        hw = d["hardware"]
        assert hw.get("hinge_4_5x4") is True, hw
        assert hw.get("hinge_4_5x4_qty") == 3, hw
        assert hw.get("sill_supplied") is True, hw


class TestVisualNoOverlap:
    """Best-effort visual check: render pages and eyeball overlap regions.
    We only assert PNG images are generated successfully (rendering does not crash).
    Deep visual assertion is delegated to the main agent."""

    def test_render_both_pages(self, blank_form_bytes):
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "form.pdf")
            with open(pdf_path, "wb") as f:
                f.write(blank_form_bytes)
            out_prefix = os.path.join(td, "page")
            res = subprocess.run(
                ["pdftoppm", "-r", "180", "-png", pdf_path, out_prefix],
                capture_output=True, timeout=60,
            )
            assert res.returncode == 0, res.stderr.decode()
            files = sorted(os.listdir(td))
            pngs = [f for f in files if f.endswith(".png")]
            assert len(pngs) == 2, f"Expected 2 PNGs, got {pngs}"
            # sanity — non-empty
            for name in pngs:
                assert os.path.getsize(os.path.join(td, name)) > 5000
