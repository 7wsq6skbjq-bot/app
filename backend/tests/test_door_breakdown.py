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
    """AT1000 36"x84" door (914.4 × 2133.6 mm) — verify standard cut formulas."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6, series="AT1000",
                                glass_thickness_mm=6.0)
    # Top rail + bottom rail length = 914.4 - 50.8 - 53.975 = 809.625
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    assert abs(top["length_mm"] - 809.6) < 0.1
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(bottom["length_mm"] - 809.6) < 0.1
    # Stiles full height
    stiles = [i for i in result.items if "Montant" in i["label"]]
    assert all(s["length_mm"] == 2133.6 for s in stiles)
    assert len(stiles) == 2
    # Moulures (4 of each)
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    mh = next(i for i in result.items if "Moulure horizontale" in i["label"])
    assert mv["qty"] == 4
    assert mh["qty"] == 4
    # H moulure = horiz cut - 2*0.25" = 809.625 - 12.7 = 796.925
    assert abs(mh["length_mm"] - 796.9) < 0.1
    # V moulure = door_height - 2*2.25" - 2*0.25" = 2133.6 - 2*57.15 - 12.7 = 2006.6
    assert abs(mv["length_mm"] - 2006.6) < 0.5
    # One glass panel sized to moulure dims
    glass = next(i for i in result.items if i["item_type"] == "glass")
    assert abs(glass["width_mm"] - mh["length_mm"]) < 0.1
    assert abs(glass["length_mm"] - mv["length_mm"]) < 0.1


def test_decompose_at1000_with_at2000_base():
    """AT1000-AT2000-base hybrid: bottom rail = 6⅞" instead of 2¼"."""
    from cut_door_breakdown import decompose_at_door
    result = decompose_at_door(914.4, 2133.6,
                                series="AT1000-AT2000-base",
                                glass_thickness_mm=6.0)
    # Top rail unchanged
    top = next(i for i in result.items if "Traverse haute" in i["label"])
    assert abs(top["length_mm"] - 809.6) < 0.1
    # Bottom rail SAME length (cut length identical between top/bottom — the
    # difference is the PROFILE height, which lives in the moulure formula)
    bottom = next(i for i in result.items if "Traverse basse" in i["label"])
    assert abs(bottom["length_mm"] - 809.6) < 0.1
    # Moulure verticale should now subtract 174.6 (6⅞") for bottom rail height
    mv = next(i for i in result.items if "Moulure verticale" in i["label"])
    # = 2133.6 - 57.15 (top) - 174.6 (bottom) - 12.7 (2x offset) = 1889.15
    assert abs(mv["length_mm"] - 1889.1) < 0.5
    # Notes mention AT2000 substitution
    assert any("AT2000" in n for n in result.notes)


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
    # 4 frame + 2 mouldings (vert+horiz, each qty=4) + 1 glass + 4 hardware = 11
    assert types.count("frame") == 6  # 2 horizontaux + 2 verticaux + 2 mouldings (vert/horiz)
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
