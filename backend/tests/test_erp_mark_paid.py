"""Test for the one-click 'mark invoice as paid' endpoint."""
import os
from datetime import date, timedelta
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
def fresh_invoice(auth_headers):
    party = {"kind": "customer", "name": "TEST_MarkPaid", "email": "info@portech.info"}
    pr = requests.post(f"{API}/admin/parties", json=party, headers=auth_headers, timeout=10)
    assert pr.status_code == 201
    client = pr.json()
    snap = {k: v for k, v in client.items() if k not in ("id", "created_at")}
    inv_payload = {
        "customer_id": client["id"],
        "customer_snapshot": snap,
        "date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
        "items": [{"description": "TEST", "quantity": 1, "unit_price": 100.0}],
        "taxable": True,
        "status": "envoyée",
    }
    ir = requests.post(f"{API}/admin/invoices", json=inv_payload, headers=auth_headers, timeout=10)
    assert ir.status_code == 201
    invoice = ir.json()
    yield invoice
    requests.delete(f"{API}/admin/invoices/{invoice['id']}", headers=auth_headers, timeout=10)
    requests.delete(f"{API}/admin/parties/{client['id']}", headers=auth_headers, timeout=10)


def test_mark_paid_changes_status(auth_headers, fresh_invoice):
    r = requests.post(
        f"{API}/admin/invoices/{fresh_invoice['id']}/mark-paid",
        headers=auth_headers, timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "payée"


def test_mark_paid_idempotent(auth_headers, fresh_invoice):
    requests.post(
        f"{API}/admin/invoices/{fresh_invoice['id']}/mark-paid",
        headers=auth_headers, timeout=10,
    )
    r = requests.post(
        f"{API}/admin/invoices/{fresh_invoice['id']}/mark-paid",
        headers=auth_headers, timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "payée"


def test_mark_paid_404(auth_headers):
    r = requests.post(
        f"{API}/admin/invoices/does-not-exist/mark-paid",
        headers=auth_headers, timeout=10,
    )
    assert r.status_code == 404
