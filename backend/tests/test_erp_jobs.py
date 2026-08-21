"""Backend API tests for Suivi des jobs (Brique 1) — /api/admin/jobs* endpoints."""
import os
from pathlib import Path

import pytest
import requests

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

STAGES = ["a_approuver", "depot_recu", "en_fabrication", "pret",
          "livre", "facture", "paye", "annule"]


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{API}/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if r.status_code != 200:
        pytest.fail(f"Admin login failed: {r.status_code} {r.text[:300]}")
    return {"Authorization": f"Bearer {r.json()['access_token']}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def created_job_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup(auth_headers, created_job_ids):
    yield
    for jid in created_job_ids:
        requests.delete(f"{API}/admin/jobs/{jid}", headers=auth_headers)


# ==== Auth / meta ====
class TestJobsMeta:
    def test_auth_required(self):
        assert requests.get(f"{API}/admin/jobs").status_code == 401

    def test_stages_endpoint(self, auth_headers):
        r = requests.get(f"{API}/admin/jobs/stages", headers=auth_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["stages"] == STAGES
        assert d["labels"]["a_approuver"] == "À approuver"
        assert d["labels"]["depot_recu"] == "Dépôt reçu (50%)"
        assert "quote" in d["doc_types"] and "invoice" in d["doc_types"]

    def test_list_jobs(self, auth_headers):
        r = requests.get(f"{API}/admin/jobs", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        for j in data:
            assert "_id" not in j
            assert j["stage"] in STAGES


# ==== CRUD manual jobs ====
class TestJobsCrud:
    def test_create_job_and_persist(self, auth_headers, created_job_ids):
        payload = {"title": "TEST_Portes entrée QA", "client_name": "TEST_Client QA",
                   "client_email": "qa@example.test", "total": 4800.0,
                   "priority": "urgent", "target_date": "2026-08-15",
                   "notes": "TEST note"}
        r = requests.post(f"{API}/admin/jobs", json=payload, headers=auth_headers)
        assert r.status_code == 201, r.text
        j = r.json()
        created_job_ids.append(j["id"])
        assert j["job_number"].startswith("JOB-")
        assert j["title"] == payload["title"]
        assert j["stage"] == "a_approuver"
        assert j["total"] == 4800.0
        assert j["deposit_expected"] == 2400.0  # 50% auto
        assert j["priority"] == "urgent"
        assert isinstance(j["history"], list) and len(j["history"]) == 1

        g = requests.get(f"{API}/admin/jobs/{j['id']}", headers=auth_headers)
        assert g.status_code == 200
        assert g.json()["title"] == payload["title"]
        assert g.json()["deposit_expected"] == 2400.0

    def test_create_job_validation(self, auth_headers):
        r = requests.post(f"{API}/admin/jobs", json={"title": ""}, headers=auth_headers)
        assert r.status_code == 422, r.text
        r2 = requests.post(f"{API}/admin/jobs",
                           json={"title": "TEST_bad", "priority": "super-urgent"},
                           headers=auth_headers)
        assert r2.status_code == 422, r2.text

    def test_update_job_and_persist(self, auth_headers, created_job_ids):
        jid = created_job_ids[0]
        r = requests.put(f"{API}/admin/jobs/{jid}",
                         json={"title": "TEST_Portes MAJ", "total": 6000.0},
                         headers=auth_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["title"] == "TEST_Portes MAJ"
        assert d["deposit_expected"] == 3000.0

        g = requests.get(f"{API}/admin/jobs/{jid}", headers=auth_headers).json()
        assert g["title"] == "TEST_Portes MAJ"
        assert g["total"] == 6000.0
        assert g["client_name"] == "TEST_Client QA"  # untouched

    def test_stage_transitions_and_history(self, auth_headers, created_job_ids):
        jid = created_job_ids[0]
        for stage in ["depot_recu", "en_fabrication", "pret", "depot_recu"]:
            r = requests.patch(f"{API}/admin/jobs/{jid}/stage",
                               json={"stage": stage, "note": "QA"}, headers=auth_headers)
            assert r.status_code == 200, r.text
            assert r.json()["stage"] == stage
        g = requests.get(f"{API}/admin/jobs/{jid}", headers=auth_headers).json()
        assert g["stage"] == "depot_recu"
        assert len(g["history"]) >= 5

    def test_stage_invalid(self, auth_headers, created_job_ids):
        r = requests.patch(f"{API}/admin/jobs/{created_job_ids[0]}/stage",
                           json={"stage": "nope"}, headers=auth_headers)
        assert r.status_code == 422, r.text

    def test_404_unknown_job(self, auth_headers):
        assert requests.get(f"{API}/admin/jobs/does-not-exist",
                            headers=auth_headers).status_code == 404
        assert requests.put(f"{API}/admin/jobs/does-not-exist", json={"title": "x"},
                            headers=auth_headers).status_code == 404
        assert requests.delete(f"{API}/admin/jobs/does-not-exist",
                               headers=auth_headers).status_code == 404

    def test_delete_job(self, auth_headers):
        j = requests.post(f"{API}/admin/jobs", json={"title": "TEST_to delete"},
                          headers=auth_headers).json()
        d = requests.delete(f"{API}/admin/jobs/{j['id']}", headers=auth_headers)
        assert d.status_code == 200, d.text
        assert requests.get(f"{API}/admin/jobs/{j['id']}",
                            headers=auth_headers).status_code == 404


# ==== Linked documents ====
class TestJobLinks:
    def test_add_remove_link(self, auth_headers, created_job_ids):
        jid = created_job_ids[0]
        payload = {"doc_type": "invoice", "doc_id": "ref:TEST-INV-1",
                   "number": "TEST-INV-1", "label": "Facture TEST-INV-1"}
        r = requests.post(f"{API}/admin/jobs/{jid}/links", json=payload,
                          headers=auth_headers)
        assert r.status_code == 200, r.text
        links = r.json()["links"]
        assert any(l["doc_id"] == "ref:TEST-INV-1" for l in links)

        # idempotent add
        r2 = requests.post(f"{API}/admin/jobs/{jid}/links", json=payload,
                           headers=auth_headers)
        assert r2.status_code == 200
        assert len([l for l in r2.json()["links"]
                    if l["doc_id"] == "ref:TEST-INV-1"]) == 1

        # invalid doc type
        bad = requests.post(f"{API}/admin/jobs/{jid}/links",
                            json={"doc_type": "banana", "doc_id": "x"},
                            headers=auth_headers)
        assert bad.status_code == 400, bad.text

        rem = requests.delete(
            f"{API}/admin/jobs/{jid}/links/invoice/ref%3ATEST-INV-1",
            headers=auth_headers)
        assert rem.status_code == 200, rem.text
        assert not any(l["doc_id"] == "ref:TEST-INV-1" for l in rem.json()["links"])


# ==== From quote (idempotency) ====
class TestJobFromQuote:
    def test_from_quote_idempotent(self, auth_headers, created_job_ids):
        quotes = requests.get(f"{API}/admin/quotes", headers=auth_headers)
        assert quotes.status_code == 200, quotes.text
        qs = quotes.json()
        if not qs:
            pytest.skip("No quotes available in DB")
        q = qs[0]
        r1 = requests.post(f"{API}/admin/jobs/from-quote/{q['id']}", headers=auth_headers)
        assert r1.status_code == 200, r1.text
        j1 = r1.json()
        created_job_ids.append(j1["id"])
        assert f"SO-{int(q['number']):04d}" in j1["title"]
        assert any(l["doc_type"] == "quote" and l["doc_id"] == q["id"]
                   for l in j1["links"])
        assert j1["total"] == pytest.approx(float(q.get("total") or 0))
        assert j1["deposit_expected"] == pytest.approx(round(j1["total"] * 0.5, 2))

        r2 = requests.post(f"{API}/admin/jobs/from-quote/{q['id']}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == j1["id"]
        assert r2.json()["job_number"] == j1["job_number"]

    def test_from_quote_404(self, auth_headers):
        r = requests.post(f"{API}/admin/jobs/from-quote/nope-nope", headers=auth_headers)
        assert r.status_code == 404, r.text


# ==== Daily briefing ====
class TestBriefing:
    def test_preview(self, auth_headers, created_job_ids):
        r = requests.get(f"{API}/admin/jobs-briefing/preview", headers=auth_headers)
        assert r.status_code == 200, r.text
        b = r.json()
        for key in ("date", "total_active", "counts", "awaiting", "in_fab",
                    "ready", "soon", "overdue", "html", "to"):
            assert key in b, f"missing {key}"
        assert set(b["counts"].keys()) == set(STAGES)
        assert "Briefing" in b["html"] or "briefing" in b["html"]
        assert "@" in b["to"]

    def test_preview_requires_auth(self):
        assert requests.get(f"{API}/admin/jobs-briefing/preview").status_code == 401

    @pytest.mark.order(-1)
    def test_send(self, auth_headers):
        r = requests.post(f"{API}/admin/jobs-briefing/send", headers=auth_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("sent") is True, f"Email not sent: {d.get('error')}"
        assert "@" in d["to"]
