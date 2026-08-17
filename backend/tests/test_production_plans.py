"""Tests for Production Plans module — hardware catalog CRUD, plan persistence, PDF."""
import os
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api/admin"

USERNAME = "PortechAdmin"
PASSWORD = "Portech2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": USERNAME, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}",
                      "Content-Type": "application/json"})
    return s


# ── Hardware catalog CRUD ──────────────────────────────────────
class TestHardwareCatalog:
    created_ids: list[str] = []

    def test_create_and_list(self, client):
        payload = {"name": "TEST_HW_Poignee_ABC", "part_number": "PN-001", "category": "poignee"}
        r = client.post(f"{API}/production-hardware", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["part_number"] == "PN-001"
        assert "id" in data
        TestHardwareCatalog.created_ids.append(data["id"])

        # list
        r = client.get(f"{API}/production-hardware")
        assert r.status_code == 200
        names = [x["name"] for x in r.json()]
        assert payload["name"] in names

    def test_upsert_on_duplicate_name(self, client):
        payload = {"name": "TEST_HW_Poignee_ABC", "part_number": "PN-999", "category": "poignee"}
        r = client.post(f"{API}/production-hardware", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        # Same id as originally created
        assert data["id"] == TestHardwareCatalog.created_ids[0]
        assert data["part_number"] == "PN-999"

    def test_update(self, client):
        item_id = TestHardwareCatalog.created_ids[0]
        r = client.put(f"{API}/production-hardware/{item_id}",
                       json={"name": "TEST_HW_Poignee_ABC", "part_number": "PN-777", "category": "poignee"})
        assert r.status_code == 200, r.text
        assert r.json()["part_number"] == "PN-777"

    def test_delete(self, client):
        item_id = TestHardwareCatalog.created_ids[0]
        r = client.delete(f"{API}/production-hardware/{item_id}")
        assert r.status_code == 204
        # verify gone
        r = client.get(f"{API}/production-hardware")
        ids = [x["id"] for x in r.json()]
        assert item_id not in ids
        TestHardwareCatalog.created_ids.clear()


# ── Plan persistence + auto-sync of hardware ──────────────────
class TestProductionPlan:
    plan_id: str | None = None
    autoname = "TEST_AutoAddSerrure"

    def test_create_plan_with_new_fields_and_hw(self, client):
        door = {
            "tag": "P-101", "series": "AT1000", "config": "simple",
            "opening_width_in": 36, "opening_height_in": 84, "qty": 1,
            "no_hardware": False, "show_handle": True, "show_lock": True,
            "lever": True, "lever_height_in": 41.5,
            "push_paddle": True, "paddle_height_in": 42,
            "protection_plate": True, "plate_height_in": 12,
            "flush_bolt": True,
            "leaf_active_width_in": 34.5, "leaf_inactive_width_in": 12,
            "hardware": [{"qty": "1", "description": TestProductionPlan.autoname,
                          "part_number": "SR-42", "note": ""}],
        }
        payload = {"project_name": "TEST_PP", "client_name": "TEST_Client",
                   "doors": [door]}
        r = client.post(f"{API}/production-plans", json=payload)
        assert r.status_code == 201, r.text
        plan = r.json()
        assert plan["plan_number"].startswith("PLAN-")
        TestProductionPlan.plan_id = plan["id"]

        # Round-trip: verify persistence of all new fields
        r = client.get(f"{API}/production-plans/{plan['id']}")
        assert r.status_code == 200
        d0 = r.json()["doors"][0]
        for k, expected in [
            ("no_hardware", False), ("show_handle", True), ("show_lock", True),
            ("lever", True), ("lever_height_in", 41.5),
            ("push_paddle", True), ("paddle_height_in", 42),
            ("protection_plate", True), ("plate_height_in", 12),
            ("flush_bolt", True),
            ("leaf_active_width_in", 34.5), ("leaf_inactive_width_in", 12),
        ]:
            assert d0[k] == expected, f"{k}: {d0[k]} != {expected}"

    def test_hardware_auto_added_to_catalog(self, client):
        r = client.get(f"{API}/production-hardware")
        assert r.status_code == 200
        names = [x["name"] for x in r.json()]
        assert TestProductionPlan.autoname in names, f"{TestProductionPlan.autoname} not auto-added"

    def test_preview_pdf(self, client):
        door = {"tag": "P-1", "series": "AT1000", "config": "simple",
                "opening_width_in": 36, "opening_height_in": 84, "qty": 1,
                "hardware": []}
        payload = {"project_name": "TEST_Preview", "doors": [door]}
        r = client.post(f"{API}/production-plans/preview-pdf", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_download_saved_pdf(self, client, token):
        assert TestProductionPlan.plan_id
        # token query param OR Bearer header — try Bearer via session
        r = client.get(f"{API}/production-plans/{TestProductionPlan.plan_id}/pdf", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_cleanup_plan(self, client):
        if TestProductionPlan.plan_id:
            r = client.delete(f"{API}/production-plans/{TestProductionPlan.plan_id}")
            assert r.status_code == 204
        # cleanup auto-added hw
        r = client.get(f"{API}/production-hardware")
        for item in r.json():
            if item["name"] == TestProductionPlan.autoname:
                client.delete(f"{API}/production-hardware/{item['id']}")
