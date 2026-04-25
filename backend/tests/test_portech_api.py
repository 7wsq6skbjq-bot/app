"""Backend API tests for Portech iteration 2 - auth, admin, contact, status."""
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
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ==== Root ====
class TestRoot:
    def test_root_message(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("message") == "Portech API — online"


# ==== Auth ====
class TestAuth:
    def test_login_success(self, client):
        r = client.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["username"] == ADMIN_USER
        assert data["role"] == "admin"
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 20
        # Cookie should be set
        assert "access_token" in r.cookies or any(
            c.name == "access_token" for c in r.cookies
        )

    def test_login_wrong_password(self, client):
        r = client.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": "wrong"})
        assert r.status_code == 401

    def test_login_wrong_username(self, client):
        r = client.post(f"{API}/auth/login", json={"username": "nobody", "password": "x"})
        assert r.status_code == 401

    def test_me_with_bearer(self, client, auth_headers):
        r = client.get(f"{API}/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == ADMIN_USER
        assert data["role"] == "admin"

    def test_me_without_token(self, client):
        # fresh session — no auth header, no cookie
        fresh = requests.Session()
        r = fresh.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_logout_clears_cookie(self, client):
        # login with this session first to set cookie
        sess = requests.Session()
        sess.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        r = sess.post(f"{API}/auth/logout")
        assert r.status_code == 200
        # After logout, /auth/me should fail
        r2 = sess.get(f"{API}/auth/me")
        assert r2.status_code == 401


# ==== Contact + email ====
class TestContact:
    def test_post_valid_with_company_and_work_location(self, client):
        payload = {
            "name": "TEST_Jean Dupont",
            "phone": "+1 514-555-1234",
            "email": "test_jean@example.com",
            "message": "Besoin d'une soumission pour 3 portes.",
            "project_type": "Barres antipaniques",
            "company": "TEST_ABC Construction Inc.",
            "work_location": "1234 rue Notre-Dame, Montréal, QC",
        }
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["email"] == payload["email"]
        assert data["project_type"] == "Barres antipaniques"
        assert data["company"] == payload["company"]
        assert data["work_location"] == payload["work_location"]
        assert "id" in data and "created_at" in data
        assert "_id" not in data
        # Resend is live — expect email_sent True
        assert data.get("email_sent") == True, f"email_sent should be True, got {data.get('email_sent')}"  # noqa: E712

    def test_post_valid_without_company(self, client):
        # company is optional, work_location is required
        payload = {
            "name": "TEST_Sans Compagnie",
            "phone": "+1 514-555-9999",
            "email": "test_nocompany@example.com",
            "message": "Demande sans nom d'entreprise.",
            "work_location": "5678 boul. René-Lévesque, Montréal",
        }
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["company"] in (None, "")
        assert data["work_location"] == payload["work_location"]

    def test_post_missing_work_location_returns_422(self, client):
        # work_location is required — missing should fail validation
        payload = {
            "name": "TEST_NoLocation",
            "phone": "555-0000",
            "email": "test_noloc@example.com",
            "message": "Lieu manquant",
        }
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 422, r.text

    def test_post_invalid_email(self, client):
        r = client.post(f"{API}/contact", json={
            "name": "TEST_X", "phone": "555-1234", "email": "not-an-email",
            "message": "hi", "work_location": "Montréal",
        })
        assert r.status_code == 422

    @pytest.mark.parametrize("missing", ["name", "phone", "email", "message", "work_location"])
    def test_post_missing_field(self, client, missing):
        payload = {
            "name": "TEST_X", "phone": "555-1234", "email": "test_x@example.com",
            "message": "hi", "work_location": "Montréal",
        }
        payload.pop(missing)
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 422


# ==== Admin ====
class TestAdmin:
    def test_submissions_requires_auth(self, client):
        fresh = requests.Session()
        r = fresh.get(f"{API}/admin/submissions")
        assert r.status_code == 401

    def test_submissions_with_auth(self, client, auth_headers):
        r = client.get(f"{API}/admin/submissions", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # from TestContact
        for item in data:
            assert "_id" not in item
            assert "id" in item and "email" in item and "created_at" in item
        # Should be sorted by created_at desc
        if len(data) >= 2:
            assert data[0]["created_at"] >= data[1]["created_at"]

    def test_stats_requires_auth(self, client):
        fresh = requests.Session()
        r = fresh.get(f"{API}/admin/stats")
        assert r.status_code == 401

    def test_stats_with_auth(self, client, auth_headers):
        r = client.get(f"{API}/admin/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data and "last_30_days" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["last_30_days"], int)
        assert data["total"] >= 1

    def test_delete_submission(self, client, auth_headers):
        # create first
        payload = {
            "name": "TEST_ToDelete", "phone": "555-0001",
            "email": "test_delete@example.com", "message": "delete me",
            "work_location": "Montréal",
        }
        cr = client.post(f"{API}/contact", json=payload)
        assert cr.status_code == 201
        sub_id = cr.json()["id"]

        # delete without auth
        fresh = requests.Session()
        r_na = fresh.delete(f"{API}/admin/submissions/{sub_id}")
        assert r_na.status_code == 401

        # delete with auth
        r = client.delete(f"{API}/admin/submissions/{sub_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] == sub_id

        # verify gone: delete again -> 404
        r2 = client.delete(f"{API}/admin/submissions/{sub_id}", headers=auth_headers)
        assert r2.status_code == 404


# ==== Status regression ====
class TestStatus:
    def test_post_status(self, client):
        r = client.post(f"{API}/status", json={"client_name": "TEST_client"})
        assert r.status_code == 200
        assert r.json()["client_name"] == "TEST_client"

    def test_get_status(self, client):
        r = client.get(f"{API}/status")
        assert r.status_code == 200
        for item in r.json():
            assert "_id" not in item
