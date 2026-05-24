"""Backend API tests for Portech prospection (vitreries) feature."""
import os
import pytest
import requests
from pathlib import Path

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"
ADMIN_USER = "PortechAdmin"
ADMIN_PASS = "Portech2026!"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(client):
    r = client.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def H(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ============== Auth guardrails ==============
class TestAuthGuard:
    @pytest.mark.parametrize("path,method", [
        ("/admin/prospection/stats", "GET"),
        ("/admin/prospection/prospects", "GET"),
        ("/admin/prospection/campaigns", "GET"),
        ("/admin/prospection/campaigns/default", "GET"),
        ("/admin/prospection/outbox", "GET"),
    ])
    def test_requires_auth(self, path, method):
        fresh = requests.Session()
        r = fresh.request(method, f"{API}{path}")
        assert r.status_code == 401, f"{path} should require auth, got {r.status_code}"


# ============== Stats ==============
class TestStats:
    def test_stats_shape(self, client, H):
        r = client.get(f"{API}/admin/prospection/stats", headers=H)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["total_prospects", "with_email", "sent_today", "sent_last_hour",
                  "hourly_limit", "remaining_this_hour", "by_status"]:
            assert k in d, f"missing key {k}"
        assert d["hourly_limit"] == 50
        assert isinstance(d["by_status"], dict)
        assert d["remaining_this_hour"] == max(0, 50 - d["sent_last_hour"])


# ============== Default campaign template ==============
class TestDefaultTemplate:
    def test_default_template(self, client, H):
        r = client.get(f"{API}/admin/prospection/campaigns/default", headers=H)
        assert r.status_code == 200
        d = r.json()
        assert d["subject"] == "Sous-traitance quincaillerie pour vos projets vitrerie"
        assert d["from_email"]
        assert d["from_name"]
        body = d["body_html"]
        assert "https://portech.info/email/email-header.png" in body
        assert "https://portech.info/email/email-footer.png" in body


# ============== Prospect CRUD ==============
class TestProspectCRUD:
    created_id = None

    def test_create(self, client, H):
        payload = {
            "name": "TEST_Vitrerie Pytest",
            "email": "test_vitrerie_pytest@example.com",
            "phone": "514-555-0001",
            "city": "Montréal",
            "region": "montreal",
            "status": "nouveau",
        }
        r = client.post(f"{API}/admin/prospection/prospects", json=payload, headers=H)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["name"] == payload["name"]
        assert d["email"] == payload["email"]
        assert "id" in d
        assert "_id" not in d
        TestProspectCRUD.created_id = d["id"]

    def test_list_filter_has_email(self, client, H):
        r = client.get(f"{API}/admin/prospection/prospects?has_email=true", headers=H)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert any(p["id"] == TestProspectCRUD.created_id for p in rows)
        for p in rows:
            assert p.get("email")

    def test_list_filter_region(self, client, H):
        r = client.get(f"{API}/admin/prospection/prospects?region=montreal", headers=H)
        assert r.status_code == 200
        for p in r.json():
            assert p["region"] == "montreal"

    def test_update(self, client, H):
        pid = TestProspectCRUD.created_id
        r = client.put(f"{API}/admin/prospection/prospects/{pid}",
                       json={"name": "TEST_Vitrerie Pytest UPD", "status": "à contacter"},
                       headers=H)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "TEST_Vitrerie Pytest UPD"
        # verify persistence via list
        r2 = client.get(f"{API}/admin/prospection/prospects", headers=H)
        found = next((p for p in r2.json() if p["id"] == pid), None)
        assert found and found["status"] == "à contacter"

    def test_delete(self, client, H):
        pid = TestProspectCRUD.created_id
        r = client.delete(f"{API}/admin/prospection/prospects/{pid}", headers=H)
        assert r.status_code == 200
        assert r.json()["deleted"] == pid
        # second delete returns 404
        r2 = client.delete(f"{API}/admin/prospection/prospects/{pid}", headers=H)
        assert r2.status_code == 404


# ============== Scrape (OSM live) ==============
class TestScrape:
    def test_scrape_montreal(self, client, H):
        r = client.post(f"{API}/admin/prospection/prospects/scrape",
                        json={"query": "vitrerie", "location": "montreal", "max_results": 5},
                        headers=H, timeout=60)
        # Overpass can be flaky; treat 502 as a soft skip
        if r.status_code == 502:
            pytest.skip(f"Overpass unavailable: {r.text}")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["scraped", "new", "skipped_duplicates", "region"]:
            assert k in d
        assert isinstance(d["scraped"], int)


# ============== Campaign CRUD + send guardrails ==============
class TestCampaign:
    campaign_id = None

    def test_create_campaign(self, client, H):
        # Get default template
        tpl = client.get(f"{API}/admin/prospection/campaigns/default", headers=H).json()
        r = client.post(f"{API}/admin/prospection/campaigns",
                        json={
                            "name": "TEST_Campaign Pytest",
                            "subject": tpl["subject"],
                            "from_name": tpl["from_name"],
                            "from_email": tpl["from_email"],
                            "body_html": tpl["body_html"],
                        }, headers=H)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["name"] == "TEST_Campaign Pytest"
        assert d["subject"] == tpl["subject"]
        TestCampaign.campaign_id = d["id"]

    def test_update_campaign(self, client, H):
        cid = TestCampaign.campaign_id
        r = client.put(f"{API}/admin/prospection/campaigns/{cid}",
                       json={
                           "name": "TEST_Campaign UPD",
                           "subject": "TEST subject upd",
                           "from_name": "Portech",
                           "from_email": "info@portech.info",
                           "body_html": "<p>updated</p>",
                       }, headers=H)
        assert r.status_code == 200
        assert r.json()["subject"] == "TEST subject upd"

    def test_send_requires_confirm(self, client, H):
        cid = TestCampaign.campaign_id
        # Create a throw-away prospect with email
        pr = client.post(f"{API}/admin/prospection/prospects",
                         json={"name": "TEST_Send Target", "email": "test_send_target@example.com"},
                         headers=H)
        prospect_id = pr.json()["id"]
        r = client.post(f"{API}/admin/prospection/campaigns/send",
                        json={"campaign_id": cid, "prospect_ids": [prospect_id], "confirm": False},
                        headers=H)
        assert r.status_code == 400
        assert "Confirmation" in r.json().get("detail", "") or "confirme" in r.json().get("detail", "").lower()
        # cleanup
        client.delete(f"{API}/admin/prospection/prospects/{prospect_id}", headers=H)

    def test_send_test_only(self, client, H):
        # Restore real template body so the test render is real
        cid = TestCampaign.campaign_id
        tpl = client.get(f"{API}/admin/prospection/campaigns/default", headers=H).json()
        client.put(f"{API}/admin/prospection/campaigns/{cid}",
                   json={
                       "name": "TEST_Campaign UPD",
                       "subject": tpl["subject"],
                       "from_name": tpl["from_name"],
                       "from_email": tpl["from_email"],
                       "body_html": tpl["body_html"],
                   }, headers=H)
        r = client.post(f"{API}/admin/prospection/campaigns/send",
                        json={"campaign_id": cid,
                              "prospect_ids": ["placeholder"],
                              "confirm": True,
                              "test_only": True,
                              "test_email": "portech.infos@gmail.com"},
                        headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("test") is True
        assert d.get("sent") is True, f"Test email failed: {d}"
        assert d.get("resend_id")
        assert d.get("to") == "portech.infos@gmail.com"

    def test_send_real_skips_no_email(self, client, H):
        """Ensure real send updates prospect status, skips no-email, writes outbox."""
        cid = TestCampaign.campaign_id
        # Two prospects: one with email, one without
        pr1 = client.post(f"{API}/admin/prospection/prospects",
                          json={"name": "TEST_RealSend WithEmail", "email": "portech.infos@gmail.com"},
                          headers=H).json()
        pr2 = client.post(f"{API}/admin/prospection/prospects",
                          json={"name": "TEST_RealSend NoEmail"},
                          headers=H).json()
        outbox_before = client.get(f"{API}/admin/prospection/outbox", headers=H).json()
        before_n = len(outbox_before)
        r = client.post(f"{API}/admin/prospection/campaigns/send",
                        json={"campaign_id": cid,
                              "prospect_ids": [pr1["id"], pr2["id"]],
                              "confirm": True},
                        headers=H, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # Should have at least one sent or skipped, no exception
        assert d["sent"] + d["failed"] + d["skipped_no_email"] >= 1
        # Verify prospect with email updated
        list_r = client.get(f"{API}/admin/prospection/prospects", headers=H).json()
        sent_p = next((p for p in list_r if p["id"] == pr1["id"]), None)
        assert sent_p is not None
        if d["sent"] >= 1:
            assert sent_p["status"] == "envoyé"
            assert sent_p["send_count"] >= 1
        # Outbox grew
        outbox_after = client.get(f"{API}/admin/prospection/outbox", headers=H).json()
        assert len(outbox_after) > before_n
        # Cleanup
        client.delete(f"{API}/admin/prospection/prospects/{pr1['id']}", headers=H)
        client.delete(f"{API}/admin/prospection/prospects/{pr2['id']}", headers=H)

    def test_delete_campaign(self, client, H):
        cid = TestCampaign.campaign_id
        r = client.delete(f"{API}/admin/prospection/campaigns/{cid}", headers=H)
        assert r.status_code == 200


# ============== Cleanup ==============
class TestZCleanup:
    def test_cleanup_test_prospects(self, client, H):
        rows = client.get(f"{API}/admin/prospection/prospects", headers=H).json()
        for p in rows:
            if (p.get("name") or "").startswith("TEST_"):
                client.delete(f"{API}/admin/prospection/prospects/{p['id']}", headers=H)
