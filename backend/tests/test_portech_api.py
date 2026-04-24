"""Backend API tests for Portech - contact, status, root endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Try loading from frontend/.env
    from pathlib import Path
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ==== Root ====
class TestRoot:
    def test_root_message(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("message") == "Portech API — online"


# ==== Contact ====
class TestContact:
    def test_post_valid(self, client):
        payload = {
            "name": "TEST_Jean Dupont",
            "phone": "+1 514-555-1234",
            "email": "test_jean@example.com",
            "message": "Besoin d'une soumission pour 3 portes.",
        }
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["email"] == payload["email"]
        assert data["phone"] == payload["phone"]
        assert data["message"] == payload["message"]
        assert isinstance(data["id"], str) and len(data["id"]) >= 32
        assert "created_at" in data
        # Ensure ISO format
        from datetime import datetime
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        assert "_id" not in data

    def test_post_with_project_type(self, client):
        payload = {
            "name": "TEST_Marie Curie",
            "phone": "514-555-0000",
            "email": "test_marie@example.com",
            "message": "Projet commercial",
            "project_type": "Barres antipaniques",
        }
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 201
        assert r.json()["project_type"] == "Barres antipaniques"

    def test_post_invalid_email(self, client):
        payload = {
            "name": "TEST_X",
            "phone": "555-1234",
            "email": "not-an-email",
            "message": "hi",
        }
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 422

    @pytest.mark.parametrize("missing", ["name", "phone", "email", "message"])
    def test_post_missing_field(self, client, missing):
        payload = {
            "name": "TEST_X",
            "phone": "555-1234",
            "email": "test_x@example.com",
            "message": "hi",
        }
        payload.pop(missing)
        r = client.post(f"{API}/contact", json=payload)
        assert r.status_code == 422

    def test_get_list_no_mongo_id(self, client):
        r = client.get(f"{API}/contact")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Should have at least the ones we created
        assert len(data) >= 1
        for item in data:
            assert "_id" not in item
            assert "id" in item
            assert "email" in item
            assert "created_at" in item


# ==== Status (regression) ====
class TestStatus:
    def test_post_status(self, client):
        r = client.post(f"{API}/status", json={"client_name": "TEST_client"})
        assert r.status_code == 200
        data = r.json()
        assert data["client_name"] == "TEST_client"
        assert "id" in data and "timestamp" in data

    def test_get_status(self, client):
        r = client.get(f"{API}/status")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for item in data:
            assert "_id" not in item
