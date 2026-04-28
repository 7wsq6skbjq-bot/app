"""Tests for the calendrier (appointments) CRUD endpoints."""
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    env = Path("/app/frontend/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(
        f"{API}/auth/login",
        json={"username": "PortechAdmin", "password": "Portech2026!"},
        timeout=10,
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def appt(auth_headers):
    payload = {
        "title": "TEST_RDV — visite chantier",
        "start": (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat(),
        "end": (datetime.now() + timedelta(days=1, hours=2)).replace(microsecond=0).isoformat(),
        "location": "123 rue Sainte-Catherine, Montréal",
        "notes": "Mesures à prendre",
        "status": "prévu",
    }
    r = requests.post(f"{API}/admin/appointments", json=payload, headers=auth_headers, timeout=10)
    assert r.status_code == 201, r.text
    a = r.json()
    yield a
    requests.delete(f"{API}/admin/appointments/{a['id']}", headers=auth_headers, timeout=10)


def test_create_returns_id_and_status_default(auth_headers):
    payload = {
        "title": "TEST_create",
        "start": (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat(),
    }
    r = requests.post(f"{API}/admin/appointments", json=payload, headers=auth_headers, timeout=10)
    assert r.status_code == 201
    a = r.json()
    assert a["id"]
    assert a["status"] == "prévu"
    requests.delete(f"{API}/admin/appointments/{a['id']}", headers=auth_headers, timeout=10)


def test_list_with_date_range_filter(auth_headers, appt):
    today_iso = date.today().isoformat()
    far = (date.today() + timedelta(days=365)).isoformat()
    r = requests.get(
        f"{API}/admin/appointments?start_from={today_iso}&start_to={far}",
        headers=auth_headers, timeout=10,
    )
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert appt["id"] in ids


def test_get_by_id(auth_headers, appt):
    r = requests.get(f"{API}/admin/appointments/{appt['id']}", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["title"] == appt["title"]


def test_update_changes_status(auth_headers, appt):
    payload = {**appt, "status": "fait"}
    # The PUT body uses AppointmentIn shape — strip server-only fields
    payload.pop("id", None)
    payload.pop("created_at", None)
    r = requests.put(
        f"{API}/admin/appointments/{appt['id']}",
        json=payload, headers=auth_headers, timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "fait"


def test_delete_then_404(auth_headers):
    payload = {
        "title": "TEST_to_delete",
        "start": (datetime.now() + timedelta(days=3)).replace(microsecond=0).isoformat(),
    }
    a = requests.post(f"{API}/admin/appointments", json=payload, headers=auth_headers, timeout=10).json()
    r = requests.delete(f"{API}/admin/appointments/{a['id']}", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    r2 = requests.get(f"{API}/admin/appointments/{a['id']}", headers=auth_headers, timeout=10)
    assert r2.status_code == 404


def test_create_rejects_missing_title(auth_headers):
    payload = {
        "start": (datetime.now() + timedelta(days=4)).replace(microsecond=0).isoformat(),
    }
    r = requests.post(f"{API}/admin/appointments", json=payload, headers=auth_headers, timeout=10)
    assert r.status_code == 422


def test_invalid_status_rejected(auth_headers):
    payload = {
        "title": "TEST_bad_status",
        "start": (datetime.now() + timedelta(days=5)).replace(microsecond=0).isoformat(),
        "status": "weird",
    }
    r = requests.post(f"{API}/admin/appointments", json=payload, headers=auth_headers, timeout=10)
    assert r.status_code == 422


def test_unauthorized_rejected():
    r = requests.get(f"{API}/admin/appointments", timeout=10)
    assert r.status_code == 401
