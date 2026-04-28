"""Integration tests for the automatic invoice reminder flow."""
import os
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://dev-retrieval.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_USER = os.environ.get("ADMIN_USERNAME", "PortechAdmin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "Portech2026!")


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(
        f"{API}/auth/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASS},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def overdue_invoice(auth_headers):
    """Create a fresh 'envoyée' invoice whose due_date is 10 days in the past,
    cleaned up after the test."""
    party = {
        "kind": "customer",
        "name": "TEST_Reminder_Client",
        "email": "info@portech.info",
        "city": "Montréal",
        "province": "QC",
    }
    pr = requests.post(f"{API}/admin/parties", json=party, headers=auth_headers, timeout=10)
    assert pr.status_code == 201, pr.text
    client = pr.json()

    snap = {k: v for k, v in client.items() if k not in ("id", "created_at")}
    inv = {
        "customer_id": client["id"],
        "customer_snapshot": snap,
        "date": (date.today() - timedelta(days=30)).isoformat(),
        "due_date": (date.today() - timedelta(days=10)).isoformat(),
        "items": [{"description": "TEST_Reminder_Item", "quantity": 1, "unit_price": 100.0}],
        "taxable": True,
        "status": "envoyée",
    }
    ir = requests.post(f"{API}/admin/invoices", json=inv, headers=auth_headers, timeout=10)
    assert ir.status_code == 201, ir.text
    invoice = ir.json()

    yield invoice

    # Cleanup
    requests.delete(f"{API}/admin/invoices/{invoice['id']}", headers=auth_headers, timeout=10)
    requests.delete(f"{API}/admin/parties/{client['id']}", headers=auth_headers, timeout=10)


def test_run_now_sends_j7_reminder_for_overdue_invoice(auth_headers, overdue_invoice):
    # Running the reminder scan should pick up this invoice at palier 7
    r = requests.post(f"{API}/admin/reminders/run-now", headers=auth_headers, timeout=30)
    assert r.status_code == 200
    body = r.json()
    # At least one reminder should have been sent (ours) but there may be
    # other overdue invoices in DB — check >=1, not exactly 1
    assert body["sent"] >= 1, body

    # Invoice should now have reminder_level_sent = 7
    check = requests.get(
        f"{API}/admin/invoices/{overdue_invoice['id']}", headers=auth_headers, timeout=10,
    )
    assert check.status_code == 200
    assert check.json().get("reminder_level_sent") == 7
    assert check.json().get("last_reminder_sent_at") is not None


def test_run_now_is_idempotent(auth_headers, overdue_invoice):
    # First call triggers the reminder
    requests.post(f"{API}/admin/reminders/run-now", headers=auth_headers, timeout=30)
    # Second call should not resend at level 7
    r2 = requests.post(f"{API}/admin/reminders/run-now", headers=auth_headers, timeout=30)
    assert r2.status_code == 200
    # Invoice should still be at reminder_level_sent = 7, not higher
    check = requests.get(
        f"{API}/admin/invoices/{overdue_invoice['id']}", headers=auth_headers, timeout=10,
    )
    assert check.json().get("reminder_level_sent") == 7


def test_manual_reminder_level_30(auth_headers, overdue_invoice):
    r = requests.post(
        f"{API}/admin/invoices/{overdue_invoice['id']}/send-reminder",
        params={"level": 30}, headers=auth_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sent"] is True
    assert body["level"] == 30


def test_manual_reminder_invalid_level_rejected(auth_headers, overdue_invoice):
    r = requests.post(
        f"{API}/admin/invoices/{overdue_invoice['id']}/send-reminder",
        params={"level": 99}, headers=auth_headers, timeout=10,
    )
    assert r.status_code == 400


def test_manual_reminder_not_found(auth_headers):
    r = requests.post(
        f"{API}/admin/invoices/does-not-exist/send-reminder",
        params={"level": 7}, headers=auth_headers, timeout=10,
    )
    assert r.status_code == 404
