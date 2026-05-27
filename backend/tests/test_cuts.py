"""Tests for the Cut List feature: optimizer math, DXF parser, API endpoints."""
import io
import math
import os
import tempfile

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


# ---------------------------------------------------------------------------
# Optimizer pure-function tests
# ---------------------------------------------------------------------------
def test_optimizer_ffd_kerf_math():
    from cut_optimizer import optimize_group
    # 5 cuts: 2400×2, 2150×2, 1100×1, stock 6800, kerf 10
    plan = optimize_group(
        cuts=[2400, 2400, 2150, 2150, 1100],
        candidate_stocks=[6800, 7000, 7315],
        kerf=10,
    )
    # 6800 is the best (smallest stock that fits well)
    assert plan["bars_count"] == 2
    # 2 bars of stock, each ~3370 mm total waste split between them
    # Bar 1: 2400+2400+1100 + 2×10 kerf = 5920 → waste 880
    # Bar 2: 2150+2150 + 1×10 kerf = 4310 → waste 2490
    assert plan["total_waste_mm"] == 880 + 2490


def test_optimizer_picks_lowest_waste_stock():
    """Stock 6800 wins: 3500 + 10 + 3000 = 6510 → 290mm waste vs 7315's 805."""
    from cut_optimizer import optimize_group
    plan = optimize_group(
        cuts=[3500, 3000],
        candidate_stocks=[6800, 7000, 7315],
        kerf=10,
    )
    assert plan["bars_count"] == 1
    assert plan["stock_length_mm"] == 6800
    assert plan["total_waste_mm"] == 6800 - 3500 - 10 - 3000  # = 290


def test_optimizer_handles_oversize_cut():
    """A 7500 cut > all stocks: marks as oversize but does not crash."""
    from cut_optimizer import optimize_group
    plan = optimize_group(
        cuts=[7500, 1000],
        candidate_stocks=[6800, 7000, 7315],
        kerf=10,
    )
    # 7500 is oversize → 1 bar with that cut + 1 bar with 1000
    # All stocks fail similarly, returns the best of them
    assert plan["bars_count"] == 2


def test_optimizer_groups_by_profile_and_material():
    from cut_optimizer import optimize_cut_list
    items = [
        {"item_type": "frame", "profile": "CS68", "material": "Alu",
         "length_mm": 2000, "qty": 2},
        {"item_type": "frame", "profile": "CS68", "material": "Alu",
         "length_mm": 1500, "qty": 1},
        {"item_type": "frame", "profile": "Sapa5500", "material": "Alu",
         "length_mm": 1800, "qty": 3},
        {"item_type": "glass", "label": "V1",
         "length_mm": 1980, "width_mm": 1100, "thickness_mm": 6,
         "qty": 2},
        {"item_type": "hardware", "label": "Charnière", "qty": 6},
    ]
    out = optimize_cut_list(items, [6800, 7000, 7315], 10)
    assert len(out["groups"]) == 2
    profiles = {g["profile"] for g in out["groups"]}
    assert profiles == {"CS68", "Sapa5500"}
    assert out["glass_summary"]["count"] == 2
    assert out["hardware_count"] == 6
    # Efficiency must be in 0..100
    assert 0 <= out["efficiency_pct"] <= 100


def test_optimizer_empty():
    from cut_optimizer import optimize_cut_list
    out = optimize_cut_list([], [6800], 10)
    assert out["total_bars"] == 0
    assert out["total_waste_mm"] == 0
    assert out["efficiency_pct"] == 0


def test_optimizer_merges_synonym_profiles():
    """'Tube à ailette 1¾"x4"' + 'Tube de tête 1¾x4' + 'Tube 1.75 x 4'
       must all collapse into ONE cutting group (same canonical dimensions)."""
    from cut_optimizer import optimize_cut_list
    items = [
        {"item_type": "frame", "profile": 'Tube à ailette 1¾" x 4"',
         "material": "Aluminium anodisé bronze",
         "length_mm": 2721, "qty": 2},
        {"item_type": "frame", "profile": "Tube de tête 1 3/4 x 4",
         "material": "Aluminium anodisé bronze",
         "length_mm": 914, "qty": 1},
        {"item_type": "frame", "profile": "Tube 1.75 x 4",
         "material": "Aluminium anodisé bronze",
         "length_mm": 600, "qty": 1},
    ]
    out = optimize_cut_list(items, [6800, 7000, 7315], 10)
    # All 3 synonyms must merge → exactly ONE group
    assert len(out["groups"]) == 1, f"Expected 1 merged group, got {[g['profile'] for g in out['groups']]}"


def test_optimizer_keeps_distinct_profiles_separate():
    """Different dimensions stay in different groups."""
    from cut_optimizer import optimize_cut_list
    items = [
        {"item_type": "frame", "profile": "Tube 1¾ x 4", "material": "Alu",
         "length_mm": 2000, "qty": 2},
        {"item_type": "frame", "profile": "Tube 2 x 4", "material": "Alu",
         "length_mm": 2000, "qty": 2},
    ]
    out = optimize_cut_list(items, [6800], 10)
    assert len(out["groups"]) == 2


def test_normalize_profile_handles_unicode_fractions():
    from cut_optimizer import normalize_profile_key
    a = normalize_profile_key('tube à ailette 1¾" x 4"', "alu bronze")
    b = normalize_profile_key("tube de tête 1 3/4 x 4", "alu bronze")
    c = normalize_profile_key("Tube 1.75x4", "Alu Bronze")
    # All three should produce the same normalized key
    assert a == b == c


# ---------------------------------------------------------------------------
# DXF parser
# ---------------------------------------------------------------------------
def _build_test_dxf() -> str:
    """Create a minimal DXF in /tmp and return its path."""
    import ezdxf
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 4  # millimeters
    msp = doc.modelspace()
    # 1 horizontal line 2000mm long
    msp.add_line((0, 0), (2000, 0))
    # 1 closed rectangle 1500 × 800 (glass)
    msp.add_lwpolyline([(0, 100), (1500, 100), (1500, 900), (0, 900)],
                       close=True, dxfattribs={"layer": "VERRE"})
    # 1 circle Ø 25mm at (300, 300)
    msp.add_circle((300, 300), 12.5, dxfattribs={"layer": "PERCAGE"})
    path = tempfile.NamedTemporaryFile(suffix=".dxf", delete=False).name
    doc.saveas(path)
    return path


def test_dxf_parser_extracts_line_rectangle_circle():
    from cut_dxf import parse_dxf
    path = _build_test_dxf()
    try:
        result = parse_dxf(path)
        items = result["items"]
        types = [i["item_type"] for i in items]
        assert "frame" in types  # line
        assert "glass" in types  # closed rectangle on VERRE layer
        assert "hole" in types   # circle
        # The line is 2000mm
        line_item = next(i for i in items if i["item_type"] == "frame")
        assert math.isclose(line_item["length_mm"], 2000, abs_tol=0.5)
        # The rectangle is 1500 × 800
        rect = next(i for i in items if i["item_type"] == "glass")
        assert math.isclose(rect["length_mm"], 1500, abs_tol=0.5)
        assert math.isclose(rect["width_mm"], 800, abs_tol=0.5)
        # The circle Ø 25mm
        hole = next(i for i in items if i["item_type"] == "hole")
        assert math.isclose(hole["length_mm"], 25, abs_tol=0.5)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# API endpoints (auth + CRUD + optimize + exports)
# ---------------------------------------------------------------------------
def test_cuts_endpoints_require_auth():
    for path in ("/admin/cuts", "/admin/cuts/meta"):
        assert requests.get(f"{API}{path}").status_code in (401, 403)


def test_cuts_meta(auth_headers):
    r = requests.get(f"{API}/admin/cuts/meta", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["default_stock_lengths_mm"] == [6800, 7000, 7315]
    assert body["default_saw_kerf_mm"] == 10
    assert "frame" in body["item_types"]


def test_cuts_crud_optimize_csv_pdf(auth_headers):
    payload = {
        "name": "Test integration",
        "project_ref": "TI-001",
        "items": [
            {"item_type": "frame", "profile": "CS68",
             "label": "Linteau", "length_mm": 2400, "qty": 2},
            {"item_type": "frame", "profile": "CS68",
             "label": "Montant", "length_mm": 2150, "qty": 2},
            {"item_type": "glass", "label": "V1",
             "length_mm": 1980, "width_mm": 1100,
             "thickness_mm": 6, "qty": 1},
        ],
    }
    r = requests.post(f"{API}/admin/cuts", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    try:
        # GET single
        g = requests.get(f"{API}/admin/cuts/{cid}", headers=auth_headers)
        assert g.status_code == 200
        assert len(g.json()["items"]) == 3

        # Optimize (persisted)
        opt = requests.post(f"{API}/admin/cuts/{cid}/optimize", headers=auth_headers)
        assert opt.status_code == 200
        ob = opt.json()
        assert ob["total_bars"] >= 1
        assert ob["glass_summary"]["count"] == 1

        # Preview (inline payload, no persistence)
        prev = requests.post(f"{API}/admin/cuts/optimize-preview",
                             json=payload, headers=auth_headers)
        assert prev.status_code == 200
        assert prev.json()["total_bars"] == ob["total_bars"]

        # CSV
        csv = requests.get(f"{API}/admin/cuts/{cid}/export.csv",
                           headers=auth_headers)
        assert csv.status_code == 200
        text = csv.text
        assert "Linteau" in text and "2400" in text

        # PDF
        pdf = requests.get(f"{API}/admin/cuts/{cid}/export.pdf",
                           headers=auth_headers)
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        # List
        lst = requests.get(f"{API}/admin/cuts", headers=auth_headers)
        assert lst.status_code == 200
        ids = [c["id"] for c in lst.json()]
        assert cid in ids
    finally:
        requests.delete(f"{API}/admin/cuts/{cid}", headers=auth_headers)


def test_extract_dxf_endpoint(auth_headers):
    path = _build_test_dxf()
    try:
        with open(path, "rb") as f:
            r = requests.post(
                f"{API}/admin/cuts/extract-dxf",
                headers=auth_headers,
                files={"file": ("test.dxf", f, "application/octet-stream")},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source_type"] == "dxf"
        assert len(body["items"]) >= 3
        # Each item should have a generated UUID id
        for it in body["items"]:
            assert it.get("id")
    finally:
        os.unlink(path)


def test_extract_dxf_rejects_non_dxf(auth_headers):
    fake = io.BytesIO(b"not a dxf")
    r = requests.post(
        f"{API}/admin/cuts/extract-dxf",
        headers=auth_headers,
        files={"file": ("bad.txt", fake, "text/plain")},
    )
    assert r.status_code == 400
