"""Iteration 15 — Production Plans tests
Covers: hardware catalog CRUD + price, plan round-trip (show_costs, mention,
door_closer/closer_leaf/astragal, per-hw unit_price), auto-add-with-price, PDFs.
"""
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


# ── Hardware catalog CRUD (with price) ─────────────────────────
class TestHardwareCatalog:
    created_ids: list[str] = []

    def test_create_with_price_and_list(self, client):
        payload = {"name": "TEST_HW_Poignee_ABC", "part_number": "PN-001",
                   "category": "poignee", "price": 12.5}
        r = client.post(f"{API}/production-hardware", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["part_number"] == "PN-001"
        assert float(data["price"]) == 12.5
        TestHardwareCatalog.created_ids.append(data["id"])

        r = client.get(f"{API}/production-hardware")
        assert r.status_code == 200
        items = {x["name"]: x for x in r.json()}
        assert payload["name"] in items
        assert float(items[payload["name"]]["price"]) == 12.5

    def test_upsert_updates_price(self, client):
        payload = {"name": "TEST_HW_Poignee_ABC", "part_number": "PN-999",
                   "category": "poignee", "price": 22.75}
        r = client.post(f"{API}/production-hardware", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["id"] == TestHardwareCatalog.created_ids[0]
        assert data["part_number"] == "PN-999"
        assert float(data["price"]) == 22.75

    def test_put_updates_price(self, client):
        item_id = TestHardwareCatalog.created_ids[0]
        r = client.put(f"{API}/production-hardware/{item_id}",
                       json={"name": "TEST_HW_Poignee_ABC", "part_number": "PN-777",
                             "category": "poignee", "price": 33.33})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["part_number"] == "PN-777"
        assert float(j["price"]) == 33.33

    def test_delete(self, client):
        item_id = TestHardwareCatalog.created_ids[0]
        r = client.delete(f"{API}/production-hardware/{item_id}")
        assert r.status_code == 204
        r = client.get(f"{API}/production-hardware")
        assert item_id not in [x["id"] for x in r.json()]
        TestHardwareCatalog.created_ids.clear()


# ── Plan persistence (new fields) + PDFs ───────────────────────
class TestProductionPlan:
    plan_id: str | None = None
    plan_id_nocost: str | None = None
    autoname = "TEST_AutoAddSerrure_15"

    def test_create_plan_new_fields(self, client):
        door_pair = {
            "tag": "P-201", "series": "AT1000", "config": "pair",
            "opening_width_in": 72, "opening_height_in": 84, "qty": 1,
            "door_closer": True, "closer_leaf": "inactive",
            "astragal": True,
            "leaf_active_width_in": 34.5, "leaf_inactive_width_in": 34.5,
            "hardware": [
                {"qty": "2", "description": TestProductionPlan.autoname,
                 "part_number": "SR-42", "unit_price": 15.0, "note": ""},
                {"qty": "1", "description": "TEST_Handle_15",
                 "part_number": "HD-1", "unit_price": 40.0, "note": ""},
            ],
        }
        payload = {
            "project_name": "TEST_PP_15", "client_name": "TEST_Client",
            "mention": "Pour approbation", "show_costs": True,
            "doors": [door_pair],
        }
        r = client.post(f"{API}/production-plans", json=payload)
        assert r.status_code == 201, r.text
        plan = r.json()
        TestProductionPlan.plan_id = plan["id"]
        assert plan["plan_number"].startswith("PLAN-")

        # Round-trip
        r = client.get(f"{API}/production-plans/{plan['id']}")
        assert r.status_code == 200
        j = r.json()
        assert j["mention"] == "Pour approbation"
        assert j["show_costs"] is True
        d0 = j["doors"][0]
        assert d0["door_closer"] is True
        assert d0["closer_leaf"] == "inactive"
        assert d0["astragal"] is True
        hws = d0["hardware"]
        assert float(hws[0]["unit_price"]) == 15.0
        assert float(hws[1]["unit_price"]) == 40.0

    def test_auto_add_carries_unit_price(self, client):
        r = client.get(f"{API}/production-hardware")
        assert r.status_code == 200
        by_name = {x["name"]: x for x in r.json()}
        assert TestProductionPlan.autoname in by_name, "auto-add missed"
        # unit_price 15.0 should carry into catalog price for brand-new name
        assert float(by_name[TestProductionPlan.autoname]["price"]) == 15.0

    def test_preview_pdf_show_costs_true(self, client):
        door = {"tag": "P-1", "series": "AT1000", "config": "simple",
                "opening_width_in": 36, "opening_height_in": 84, "qty": 1,
                "hardware": [{"qty": "1", "description": "X", "part_number": "",
                              "unit_price": 5.0, "note": ""}]}
        payload = {"project_name": "TEST_PDFyes", "show_costs": True,
                   "mention": "Pour demande de prix", "doors": [door]}
        r = client.post(f"{API}/production-plans/preview-pdf", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_preview_pdf_show_costs_false(self, client):
        door = {"tag": "P-1", "series": "AT1000", "config": "simple",
                "opening_width_in": 36, "opening_height_in": 84, "qty": 1,
                "hardware": []}
        payload = {"project_name": "TEST_PDFno", "show_costs": False,
                   "mention": "Pour production", "doors": [door]}
        r = client.post(f"{API}/production-plans/preview-pdf", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")

    def test_download_saved_pdf(self, client):
        assert TestProductionPlan.plan_id
        r = client.get(f"{API}/production-plans/{TestProductionPlan.plan_id}/pdf", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_cleanup(self, client):
        if TestProductionPlan.plan_id:
            r = client.delete(f"{API}/production-plans/{TestProductionPlan.plan_id}")
            assert r.status_code == 204
        # cleanup auto-added hw
        r = client.get(f"{API}/production-hardware")
        for item in r.json():
            if item["name"] in (TestProductionPlan.autoname, "TEST_Handle_15"):
                client.delete(f"{API}/production-hardware/{item['id']}")
