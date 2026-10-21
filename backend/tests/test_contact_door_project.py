# Contact form API — door-project details folded into message (iteration 20)
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _payload(**kw):
    p = {
        "name": "TEST_Door Lead",
        "phone": "514 555-0000",
        "email": "test_door@example.com",
        "work_location": "Montréal",
        "project_type": "Porte en aluminium",
        "message": "Bonjour\n--- Projet de porte en aluminium ---\nGamme : AT2000 (robuste, fort trafic)\n"
                   "Configuration : Double\nNombre de portes : 2\nDimensions (L × H) : 36\" × 84\"\nFini : Noir mat",
    }
    p.update(kw)
    return p


# Successful submission with door details in message
def test_contact_with_door_details_201(client):
    r = client.post(f"{BASE_URL}/api/contact", json=_payload())
    assert r.status_code == 201, r.text
    d = r.json()
    assert isinstance(d["id"], str) and d["id"]
    assert "Projet de porte en aluminium" in d["message"]
    assert "Dimensions (L × H) : 36\" × 84\"" in d["message"]
    assert d["project_type"] == "Porte en aluminium"
    assert "_id" not in d


# Validation errors
def test_contact_missing_work_location_422(client):
    p = _payload()
    p.pop("work_location")
    assert client.post(f"{BASE_URL}/api/contact", json=p).status_code == 422


def test_contact_bad_email_422(client):
    assert client.post(f"{BASE_URL}/api/contact", json=_payload(email="nope")).status_code == 422


def test_contact_empty_message_422(client):
    assert client.post(f"{BASE_URL}/api/contact", json=_payload(message="")).status_code == 422


# Static aluminium images served by frontend
@pytest.mark.parametrize("img", [
    "alu-hero", "alu-home", "alu-at1000", "alu-at2000", "alu-isolee", "alu-double",
    "alu-surmesure", "alu-gal1", "alu-gal2", "alu-cta", "alu-finis",
])
def test_alu_images_served(img):
    r = requests.get(f"{BASE_URL}/generated/aluminium/{img}.png", timeout=20)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 10000
