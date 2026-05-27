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
    """Insulated AT2000 with thermos 25.4mm glass — shorter stile cut."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6, series="ATi2000",
                                glass_thickness_mm=25.4)
    stiles = [i for i in result.items if "Montant" in i["label"]]
    # Insulated height offset = 27.90 → 2105.70
    assert all(abs(s["length_mm"] - 2105.7) < 0.1 for s in stiles)
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    # 2105.7 - 295.90 = 1809.80
    assert abs(mv["length_mm"] - 1809.8) < 0.1


def test_series_normalization_handles_user_variants():
    """User may type 'ATI-2000', 'ati 1000', 'at_i2000' etc."""
    from cut_door_breakdown import _normalize_series
    assert _normalize_series("ATi2000") == "ATI2000"
    assert _normalize_series("ATI-1000") == "ATI1000"
    assert _normalize_series("at i 2000") == "ATI2000"
    assert _normalize_series("AT 2000") == "AT2000"
    assert _normalize_series("at1000") == "AT1000"
    assert _normalize_series("unknown junk") == "AT1000"  # safe fallback


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
    # Expected: 4 frame pieces (2 rails + 2 stiles) + 2 moulure lines + 1 glass
    # + 4 hardware = 11
    assert types.count("frame") == 6
    assert types.count("glass") == 1
    assert "notes" in body


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
