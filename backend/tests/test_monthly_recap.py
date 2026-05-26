"""Tests for the monthly expense recap module.

Covers: build_recap math, HTML render contract, scheduler skip-if-recent,
auth on admin endpoints, and the audit-log endpoint.
"""
import asyncio
import os
import re
from datetime import datetime, timedelta, timezone

import pytest
import requests

# Live server under test
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


def test_recap_endpoints_require_auth():
    assert requests.get(f"{API}/admin/expenses/recap/preview").status_code in (401, 403)
    assert requests.post(f"{API}/admin/expenses/recap/send").status_code in (401, 403)
    assert requests.get(f"{API}/admin/expenses/recap/log").status_code in (401, 403)


def test_recap_preview_default_month(auth_headers):
    r = requests.get(f"{API}/admin/expenses/recap/preview", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    # YYYY-MM
    assert re.fullmatch(r"\d{4}-\d{2}", body["month"])
    for k in ("count", "subtotal", "tps", "tvq", "total", "by_category", "default_recipient"):
        assert k in body
    assert isinstance(body["by_category"], list)


def test_recap_preview_explicit_month_with_data(auth_headers):
    """Create 2 expenses in a fake month, preview, assert math, cleanup."""
    test_month = "2099-12"
    # Seed
    p1 = {
        "date": f"{test_month}-05", "supplier_name": "FX1",
        "description": "Test 1", "category": "Matériaux",
        "subtotal": 100.0, "tps": 5.0, "tvq": 9.98, "total": 114.98,
        "payment_method": "Carte", "status": "payée",
    }
    p2 = {
        "date": f"{test_month}-18", "supplier_name": "FX2",
        "description": "Test 2", "category": "Carburant",
        "subtotal": 50.0, "tps": 2.5, "tvq": 4.99, "total": 57.49,
        "payment_method": "Carte", "status": "payée",
    }
    r1 = requests.post(f"{API}/admin/expenses", json=p1, headers=auth_headers)
    r2 = requests.post(f"{API}/admin/expenses", json=p2, headers=auth_headers)
    assert r1.status_code == 201 and r2.status_code == 201
    id1, id2 = r1.json()["id"], r2.json()["id"]
    try:
        prev = requests.get(
            f"{API}/admin/expenses/recap/preview?month={test_month}",
            headers=auth_headers,
        )
        assert prev.status_code == 200
        body = prev.json()
        assert body["month"] == test_month
        assert body["count"] == 2
        assert body["subtotal"] == 150.0
        assert body["tps"] == 7.5
        assert round(body["tvq"], 2) == 14.97
        assert round(body["total"], 2) == 172.47
        cats = {c["category"]: c["total"] for c in body["by_category"]}
        assert cats["Matériaux"] == 114.98
        assert cats["Carburant"] == 57.49
    finally:
        requests.delete(f"{API}/admin/expenses/{id1}", headers=auth_headers)
        requests.delete(f"{API}/admin/expenses/{id2}", headers=auth_headers)


def test_recap_log_returns_list(auth_headers):
    r = requests.get(f"{API}/admin/expenses/recap/log", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_build_recap_pure_function():
    """Direct python call — no HTTP — verifies math + CSV bytes shape."""
    from erp_monthly_recap import build_recap
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")

    async def run():
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        try:
            # Use a month we know has zero expenses
            recap = await build_recap(db, "1999-01")
            assert recap["month"] == "1999-01"
            assert recap["count"] == 0
            assert recap["csv_bytes"].startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
            # CSV header line must include the column names
            header_line = recap["csv_bytes"].decode("utf-8").split("\n", 1)[0]
            for col in ("Date", "Fournisseur", "Description", "Catégorie",
                        "Sous-total", "TPS", "TVQ", "Total"):
                assert col in header_line
        finally:
            client.close()

    asyncio.run(run())


def test_render_recap_html_contract():
    """HTML render returns (subject, html) with expected substrings."""
    from erp_monthly_recap import render_recap_html
    fake_recap = {
        "month": "2026-05",
        "count": 3,
        "subtotal": 100.0, "tps": 5.0, "tvq": 9.98, "total": 114.98,
        "by_category": [
            {"category": "Matériaux", "total": 80.0},
            {"category": "Outils", "total": 34.98},
        ],
        "csv_bytes": b"",
    }
    subject, html = render_recap_html(fake_recap)
    assert "mai 2026" in subject.lower()
    assert "récap" in subject.lower()
    # Money formatted FR
    assert "100,00" in html and "5,00" in html and "9,98" in html
    assert "Matériaux" in html and "Outils" in html


def test_scheduler_skip_if_recent():
    """run_scheduled_recap should skip when a log entry was sent < 6 days ago."""
    from erp_monthly_recap import run_scheduled_recap, _current_month_str
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    month = _current_month_str()

    async def run():
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        try:
            # Insert a recent log entry
            recent = datetime.now(timezone.utc) - timedelta(hours=2)
            await db.erp_monthly_recap_log.insert_one({
                "month": month, "to": "test@x", "count": 0,
                "total": 0, "subtotal": 0, "tps": 0, "tvq": 0,
                "sent_at": recent.isoformat(),
            })
            result = await run_scheduled_recap(db)
            assert result.get("sent") is False
            assert result.get("reason") == "already_sent_recently"
        finally:
            await db.erp_monthly_recap_log.delete_many({"to": "test@x"})
            client.close()

    asyncio.run(run())
