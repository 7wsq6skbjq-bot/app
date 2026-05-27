"""Tests for the door breakdown module (AT1000/AT2000 → 4 frame pieces + mouldings)."""
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


def test_decompose_at1000_standard_36x84_door():
    """AT1000 36"x84" rough opening = 914.4×2133.6 mm. Match official DXF spec."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6, series="AT1000",
                                glass_thickness_mm=6.0)
    # Rail cut = 914.4 - 115.10 = 799.30
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    assert abs(top["length_mm"] - 799.3) < 0.1
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(bottom["length_mm"] - 799.3) < 0.1
    # Stiles cut = 2133.6 - 22.20 = 2111.40
    stiles = [i for i in result.items if "Montant" in i["label"]]
    assert all(abs(s["length_mm"] - 2111.4) < 0.1 for s in stiles)
    assert len(stiles) == 2
    # Vertical moulure (6mm glass) = 2111.4 - 182.5 = 1928.9
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    assert abs(mv["length_mm"] - 1928.9) < 0.1
    assert mv["qty"] == 4
    # Horizontal moulure = 799.3 - 2×6.35 = 786.6
    mh = next(i for i in result.items if "Moulure horizontale" in i["label"])
    assert abs(mh["length_mm"] - 786.6) < 0.2
    assert mh["qty"] == 4


def test_decompose_at2000_standard_36x84_door():
    """AT2000 36"x84": bigger 3-11/16" rails → much shorter rail cuts."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6, series="AT2000",
                                glass_thickness_mm=6.0)
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    # Rail cut = 914.4 - 191.30 = 723.10
    assert abs(top["length_mm"] - 723.1) < 0.1
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    # 2111.4 - 299.70 = 1811.70
    assert abs(mv["length_mm"] - 1811.7) < 0.1


def test_decompose_ati2000_insulated_1inch_glass():
    """ATi2000 — same door leaf as AT2000 + cladding pieces (5.7mm shorter)."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6, series="ATi2000",
                                glass_thickness_mm=25.4)
    stiles = [i for i in result.items if "Montant" in i["label"]]
    # Door leaf SAME as AT2000 — 2111.40, NOT 2105.70
    assert all(abs(s["length_mm"] - 2111.4) < 0.1 for s in stiles)
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    # 2111.4 - 301.60 = 1809.80
    assert abs(mv["length_mm"] - 1809.8) < 0.1
    # CLADDING pieces — present only on ATi
    cladding_v = next(i for i in result.items if "Cladding vertical" in i["label"])
    cladding_h = next(i for i in result.items if "Cladding horizontal" in i["label"])
    # Cladding V = stile - 5.7 = 2105.70
    assert abs(cladding_v["length_mm"] - 2105.7) < 0.1
    # Cladding H = rail - 5.7 = 723.10 - 5.7 = 717.4
    assert abs(cladding_h["length_mm"] - 717.4) < 0.1
    assert cladding_v["qty"] == 2
    assert cladding_h["qty"] == 2


def test_non_insulated_at_has_no_cladding():
    """Standard AT1000/AT2000 must NOT produce cladding pieces."""
    from cut_door_breakdown import decompose_at_door
    for series in ("AT1000", "AT2000"):
        result = decompose_at_door(914.4, 2133.6, series=series,
                                    glass_thickness_mm=6.0)
        cladding = [i for i in result.items if "Cladding" in i["label"]]
        assert len(cladding) == 0, f"{series} should not have cladding"


def test_series_normalization_handles_user_variants():
    """User may type 'ATI-2000', 'ati 1000', 'at_i2000' etc."""
    from cut_door_breakdown import _normalize_series
    assert _normalize_series("ATi2000") == "ATI2000"
    assert _normalize_series("ATI-1000") == "ATI1000"
    assert _normalize_series("at i 2000") == "ATI2000"
    assert _normalize_series("AT 2000") == "AT2000"
    assert _normalize_series("at1000") == "AT1000"
    assert _normalize_series("unknown junk") == "AT1000"
    # Hybrid base
    assert _normalize_series("AT1000-base-AT2000") == "AT1000-BASE-AT2000"
    assert _normalize_series("AT1000 AT2000") == "AT1000-BASE-AT2000"
    assert _normalize_series("at1000-base-at2000") == "AT1000-BASE-AT2000"


def test_decompose_hybrid_at1000_base_at2000():
    """Uniprix-style hybrid: AT1000 door body with AT2000 bottom rail (6⅞")."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6,
                                series="AT1000-base-AT2000",
                                glass_thickness_mm=6.0)
    # Rail cut length unchanged (frame is AT1000)
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(top["length_mm"] - 799.3) < 0.1
    assert abs(bottom["length_mm"] - 799.3) < 0.1
    # But the bottom profile name shows the AT2000 substitution
    assert "6⅞" in bottom["profile"] or "AT2000" in bottom["profile"]
    # Moulure V is shorter than pure AT1000 because the bottom rail is taller
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    # 2111.4 - 301.60 (combined offset) = 1809.80
    assert abs(mv["length_mm"] - 1809.8) < 0.5


def test_decompose_hardware_positions():
    """Hardware positions follow Portech defaults unless overridden."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6, series="AT1000")
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
            "door_width_mm": 914.4,
            "door_height_mm": 2133.6,
            "series": "AT1000",
            "glass_thickness_mm": 6.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    types = [i["item_type"] for i in body["items"]]
    # AT1000 non-insulated: 4 frame (rails + stiles) + 2 moulures + 1 glass + 4 hw
    assert types.count("frame") == 6
    assert types.count("glass") == 1
    assert "notes" in body


def test_decompose_endpoint_includes_cladding_for_ati(auth_headers):
    r = requests.post(
        f"{API}/admin/cuts/decompose-door",
        headers=auth_headers,
        json={
            "door_width_mm": 914.4,
            "door_height_mm": 2133.6,
            "series": "ATi1000",
            "glass_thickness_mm": 25.4,
        },
    )
    assert r.status_code == 200
    labels = [i.get("label", "") for i in r.json()["items"]]
    # ATi adds 2 cladding frame pieces (vertical + horizontal)
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
