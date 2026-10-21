# Iteration 21 — structured door_* fields on contact + ERP /admin/door-requests + WebP images
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DOOR = {"door_gamme": "AT2000 (robuste, fort trafic)", "door_config": "Double", "door_qty": "3",
        "door_width": "72\"", "door_height": "84\"", "door_finish": "Noir mat"}


def _payload(**kw):
    p = {"name": "TEST_Iter21 Lead", "phone": "514 555-0000", "email": "test_iter21@example.com",
         "work_location": "Montréal", "project_type": "Porte en aluminium", "message": "Bonjour TEST"}
    p.update(kw)
    return p


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": "PortechAdmin", "password": "Portech2026!"})
    if r.status_code != 200:
        pytest.skip("login failed")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


@pytest.fixture(scope="module")
def created():
    door = requests.post(f"{BASE_URL}/api/contact", json=_payload(**DOOR))
    plain = requests.post(f"{BASE_URL}/api/contact", json=_payload(name="TEST_Iter21 Plain", project_type=None))
    return door, plain


# POST /contact stores structured door fields
def test_contact_door_fields_201(created):
    door, _ = created
    assert door.status_code == 201, door.text
    d = door.json()
    for k, v in DOOR.items():
        assert d[k] == v
    assert "_id" not in d


def test_contact_plain_201_no_door(created):
    _, plain = created
    assert plain.status_code == 201, plain.text
    assert plain.json()["door_gamme"] is None


def test_door_field_too_long_422():
    assert requests.post(f"{BASE_URL}/api/contact", json=_payload(door_qty="x" * 30)).status_code == 422


# ERP door-requests endpoint
def test_door_requests_requires_auth():
    assert requests.get(f"{BASE_URL}/api/admin/door-requests").status_code in (401, 403)


def test_door_requests_filters(admin, created):
    door, plain = created
    r = admin.get(f"{BASE_URL}/api/admin/door-requests")
    assert r.status_code == 200
    rows = r.json()
    ids = {x["id"] for x in rows}
    assert door.json()["id"] in ids
    assert plain.json()["id"] not in ids
    keys = ["door_gamme", "door_config", "door_qty", "door_width", "door_height", "door_finish"]
    for x in rows:
        assert any(x.get(k) for k in keys), x
        assert "_id" not in x
    row = next(x for x in rows if x["id"] == door.json()["id"])
    assert row["door_width"] == "72\"" and row["door_finish"] == "Noir mat"


# WebP images served
@pytest.mark.parametrize("img", ["alu-hero", "alu-home", "alu-at1000", "alu-at2000", "alu-isolee", "alu-double",
                                 "alu-surmesure", "alu-gal1", "alu-gal2", "alu-cta", "alu-finis"])
def test_webp_served(img):
    r = requests.get(f"{BASE_URL}/generated/aluminium/{img}.webp", timeout=20)
    assert r.status_code == 200
    assert r.content[:4] == b"RIFF" and r.content[8:12] == b"WEBP"
    png = requests.get(f"{BASE_URL}/generated/aluminium/{img}.png", timeout=20)
    print(img, len(r.content), len(png.content))
    assert len(r.content) < len(png.content)
