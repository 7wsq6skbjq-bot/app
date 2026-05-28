"""Tests for the door breakdown module — INPUT = leaf dimensions (battant fini).

Reference values (Portech 2026-05, AT Fabrication shop drawings) :
  - AT1000 standard leaf (36"×84" opening) = 799.30 × 2111.40 mm
  - AT2000 standard leaf                  = 723.10 × 2111.40 mm
  - AT2000 with user-supplied leaf        = 723.10 × 2114.50 mm (user's BMO example)

Parclose carrée ¼" face width = 13.48 mm.
Moulures mitred 45° at corners → moulure_H = leaf_width (full width).
Moulure_V = leaf_height - top_rail - base - 2 × 13.48.
"""
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
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_decompose_at1000_standard_leaf():
    """AT1000 leaf 799.30 × 2111.40 (= rough opening 36"×84" → leaf)."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(799.30, 2111.40, series="AT1000",
                                glass_thickness_mm=6.0)
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    assert abs(top["length_mm"] - 799.30) < 0.1
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(bottom["length_mm"] - 799.30) < 0.1
    # AT1000 base is 3⅞" (98.425 mm) — same extrusion as AT2000 head (part "AT1000")
    # Stiles = leaf height directly
    stiles = [i for i in result.items if "Montant" in i["label"]]
    assert all(abs(s["length_mm"] - 2111.40) < 0.1 for s in stiles)
    assert len(stiles) == 2
    # Parclose V = 2111.40 - 55.5 (top) - 98.425 (base 3⅞") - 2×13.48 = 1930.515
    pv = next(i for i in result.items if "Parclose verticale" in i["label"])
    assert abs(pv["length_mm"] - 1930.52) < 0.05
    assert pv["qty"] == 4
    # Parclose H = leaf width (mitred)
    ph = next(i for i in result.items if "Parclose horizontale" in i["label"])
    assert abs(ph["length_mm"] - 799.30) < 0.1
    assert ph["qty"] == 4


def test_at1000_part_numbers_and_glass6mm_parclose():
    """AT1000 with 6mm glass must carry the exact AT Fabrication part numbers
    and use the carrée 13.48 mm parclose."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(799.30, 2111.40, series="AT1000",
                                glass_thickness_mm=6.0)
    by_label = {i["label"]: i for i in result.items}
    top = next(v for k, v in by_label.items() if "Traverse haute" in k)
    base = next(v for k, v in by_label.items() if "Traverse basse" in k)
    hinge = next(v for k, v in by_label.items() if "charnière" in k.lower() and "Montant" in k)
    lock = next(v for k, v in by_label.items() if "serrure" in k.lower() and "Montant" in k)
    assert top["part_number"] == "ATT1005"
    assert base["part_number"] == "AT1000"     # 3⅞" base (same as AT2000 head)
    assert hinge["part_number"] == "AT1025"    # 2" hinge stile
    assert lock["part_number"] == "AT1020"     # 2⅛" lock stile
    # Parclose 6 mm → carrée 13.48
    pv = next(v for k, v in by_label.items() if "Parclose verticale" in k)
    assert "carrée" in pv["profile"]
    assert "13.48" in pv["profile"]


def test_at2000_part_numbers():
    """AT2000 — top = AT1000 (3⅞ extrusion shared), base = AT2000, hinge = AT2025, lock = AT2020."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(723.10, 2114.50, series="AT2000",
                                glass_thickness_mm=6.0)
    by_label = {i["label"]: i for i in result.items}
    top = next(v for k, v in by_label.items() if "Traverse haute" in k)
    base = next(v for k, v in by_label.items() if "Traverse basse" in k)
    hinge = next(v for k, v in by_label.items() if "charnière" in k.lower() and "Montant" in k)
    lock = next(v for k, v in by_label.items() if "serrure" in k.lower() and "Montant" in k)
    assert top["part_number"] == "AT1000"      # AT2000 head = AT1000 part (3⅞")
    assert base["part_number"] == "AT2000"     # 6⅞"
    assert hinge["part_number"] == "AT2025"    # 3½"
    assert lock["part_number"] == "AT2020"     # 3⅝"


def test_ati2000_part_numbers_and_thermos_parclose():
    """ATi2000 with 25.4 mm thermos glass → plate 14.3 mm parclose
    and cladding parts ATV2030 / ATCHA2025."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(723.10, 2111.40, series="ATi2000",
                                glass_thickness_mm=25.4)
    by_label = {i["label"]: i for i in result.items}
    # Parclose plate 14.3 for thermos 25.4
    pv = next(v for k, v in by_label.items() if "Parclose verticale" in k)
    assert "plate" in pv["profile"]
    assert "14.3" in pv["profile"]
    # Verify recomputed length with 14.3 mm face:
    # 2111.40 - 98.425 (head 3⅞) - 174.625 (base 6⅞) - 2×14.3 = 1809.75
    assert abs(pv["length_mm"] - 1809.75) < 0.1
    # Cladding part numbers
    clad_v = next(v for k, v in by_label.items() if "Cladding vertical" in k)
    clad_h = next(v for k, v in by_label.items() if "Cladding horizontal" in k)
    assert clad_v["part_number"] == "ATV2030"
    assert clad_h["part_number"] == "ATCHA2025"


def test_ati1000_cladding_part_numbers():
    """ATi1000 cladding pieces = ATV1030 / ATCHA1035."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(799.30, 2111.40, series="ATi1000",
                                glass_thickness_mm=25.4)
    clad_v = next(i for i in result.items if "Cladding vertical" in i["label"])
    clad_h = next(i for i in result.items if "Cladding horizontal" in i["label"])
    assert clad_v["part_number"] == "ATV1030"
    assert clad_h["part_number"] == "ATCHA1035"


def test_decompose_at2000_user_supplied_leaf_bmo():
    """User's exact BMO example : AT2000 leaf 723.1 × 2114.5 must give
    parclose V ≈ 1814.49 and parclose H = 723.10 (mitred)."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(723.10, 2114.50, series="AT2000",
                                glass_thickness_mm=6.0)
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    assert abs(top["length_mm"] - 723.10) < 0.1
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(bottom["length_mm"] - 723.10) < 0.1
    # AT2000 stile widths
    hinge = next(i for i in result.items if "charnière" in i["label"].lower())
    lock = next(i for i in result.items if "serrure" in i["label"].lower() and "Montant" in i["label"])
    assert abs(hinge["length_mm"] - 2114.50) < 0.1
    assert abs(lock["length_mm"] - 2114.50) < 0.1
    # Parclose V = 2114.5 - 98.425 - 174.625 - 2 × 13.48 = 1814.49
    pv = next(i for i in result.items if "Parclose verticale" in i["label"])
    assert abs(pv["length_mm"] - 1814.49) < 0.05
    # Parclose H = leaf width directly
    ph = next(i for i in result.items if "Parclose horizontale" in i["label"])
    assert abs(ph["length_mm"] - 723.10) < 0.1


def test_decompose_ati2000_insulated_with_cladding():
    """ATi2000 leaf 723.10 × 2111.40 + cladding pieces (5.7 mm shorter)."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(723.10, 2111.40, series="ATi2000",
                                glass_thickness_mm=25.4)
    stiles = [i for i in result.items if "Montant" in i["label"]]
    assert all(abs(s["length_mm"] - 2111.40) < 0.1 for s in stiles)
    # Cladding present (ATi only)
    cladding_v = next(i for i in result.items if "Cladding vertical" in i["label"])
    cladding_h = next(i for i in result.items if "Cladding horizontal" in i["label"])
    # Cladding V = stile - 5.7
    assert abs(cladding_v["length_mm"] - (2111.40 - 5.7)) < 0.1
    # Cladding H = rail - 5.7
    assert abs(cladding_h["length_mm"] - (723.10 - 5.7)) < 0.1
    assert cladding_v["qty"] == 2
    assert cladding_h["qty"] == 2


def test_non_insulated_at_has_no_cladding():
    """Standard AT1000/AT2000 must NOT produce cladding pieces."""
    from cut_door_breakdown import decompose_at_door
    for series in ("AT1000", "AT2000"):
        result = decompose_at_door(799.30 if series == "AT1000" else 723.10,
                                    2111.40, series=series,
                                    glass_thickness_mm=6.0)
        cladding = [i for i in result.items if "Cladding" in i["label"]]
        assert len(cladding) == 0, f"{series} should not have cladding"


def test_series_normalization_handles_user_variants():
    from cut_door_breakdown import _normalize_series
    assert _normalize_series("ATi2000") == "ATI2000"
    assert _normalize_series("ATI-1000") == "ATI1000"
    assert _normalize_series("at i 2000") == "ATI2000"
    assert _normalize_series("AT 2000") == "AT2000"
    assert _normalize_series("at1000") == "AT1000"
    assert _normalize_series("unknown junk") == "AT1000"
    # Hybrid
    assert _normalize_series("AT1000-base-AT2000") == "AT1000-BASE-AT2000"
    assert _normalize_series("AT1000 AT2000") == "AT1000-BASE-AT2000"


def test_decompose_hybrid_at1000_base_at2000():
    """Hybrid : AT1000 body + AT2000 base 6⅞". Leaf = 799.30 × 2111.40."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(799.30, 2111.40, series="AT1000-base-AT2000",
                                glass_thickness_mm=6.0)
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(top["length_mm"] - 799.30) < 0.1
    assert abs(bottom["length_mm"] - 799.30) < 0.1
    assert "6⅞" in bottom["profile"] or "AT2000" in bottom["profile"]
    # Parclose V = 2111.40 - 55.5 (AT1000 top) - 174.625 (AT2000 base) - 26.96 = 1854.315
    pv = next(i for i in result.items if "Parclose verticale" in i["label"])
    assert abs(pv["length_mm"] - 1854.32) < 0.05


def test_decompose_hardware_positions():
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(799.30, 2111.40, series="AT1000")
    cyl = next(i for i in result.hardware if "cylindre" in i["label"].lower())
    assert cyl["position_y"] == 1016.0
    strike = next(i for i in result.hardware if "gâche" in i["label"].lower())
    assert abs(strike["position_y"] - (1016.0 + 19.05)) < 0.2
    handle = next(i for i in result.hardware if "poignée" in i["label"].lower())
    assert handle["position_y"] == 876.3


def test_decompose_endpoint_requires_auth():
    r = requests.post(f"{API}/admin/cuts/decompose-door", json={})
    assert r.status_code in (401, 403)


def test_decompose_endpoint_happy_path(auth_headers):
    r = requests.post(
        f"{API}/admin/cuts/decompose-door",
        headers=auth_headers,
        json={
            "door_width_mm": 799.30,    # LEAF dims now
            "door_height_mm": 2111.40,
            "series": "AT1000",
            "glass_thickness_mm": 6.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    types = [i["item_type"] for i in body["items"]]
    # AT1000 non-insulated: 6 frame (2 rails + 2 stiles + V+H parcloses) + 1 glass + 4 hw
    assert types.count("frame") == 6
    assert types.count("glass") == 1
    assert "notes" in body


def test_decompose_endpoint_includes_cladding_for_ati(auth_headers):
    r = requests.post(
        f"{API}/admin/cuts/decompose-door",
        headers=auth_headers,
        json={
            "door_width_mm": 799.30,
            "door_height_mm": 2111.40,
            "series": "ATi1000",
            "glass_thickness_mm": 25.4,
        },
    )
    assert r.status_code == 200
    labels = [i.get("label", "") for i in r.json()["items"]]
    assert sum(1 for L in labels if "Cladding" in L) == 2


def test_decompose_endpoint_invalid_input(auth_headers):
    r = requests.post(
        f"{API}/admin/cuts/decompose-door",
        headers=auth_headers,
        json={"door_width_mm": 0, "door_height_mm": 100},
    )
    assert r.status_code == 400


def test_cuts_csv_includes_part_number(auth_headers):
    """Create a cut with a part_number on an item, export CSV, assert column."""
    payload = {
        "name": "Part number test",
        "items": [
            {"item_type": "hardware", "label": "Charnière HD",
             "part_number": "UH-120-DA", "manufacturer": "AT Fabrication",
             "qty": 1, "length_mm": 0},
        ],
    }
    r = requests.post(f"{API}/admin/cuts", json=payload, headers=auth_headers)
    assert r.status_code == 201
    cid = r.json()["id"]
    try:
        csv = requests.get(f"{API}/admin/cuts/{cid}/export.csv",
                           headers=auth_headers).text
        assert "UH-120-DA" in csv
        assert "AT Fabrication" in csv
        assert "N° pièce" in csv
    finally:
        requests.delete(f"{API}/admin/cuts/{cid}", headers=auth_headers)
