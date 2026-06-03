"""Backend tests for /admin/alu-inventory endpoints (2-finish + thresholds + PO PDF).

Covers:
- list (normalized rows with finish/restock_min/restock_max defaults)
- POST creates separate rows for different finishes (same key+length)
- POST merges qty when same key+length+finish+is_chute
- PATCH /thresholds sets and unsets restock_min/max
- PATCH delta adjusts qty (clamped at 0)
- DELETE
- GET purchase-order.pdf with token query param (Bearer-less downloads)
"""
import os
import pytest
import requests


def _read_env_file(path: str) -> dict:
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


_FE_ENV = _read_env_file("/app/frontend/.env")
_BE_ENV = _read_env_file("/app/backend/.env")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE_ENV.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
ADMIN_USER = _BE_ENV.get("ADMIN_USERNAME") or os.environ.get("ADMIN_USERNAME", "PortechAdmin")
ADMIN_PASS = _BE_ENV.get("ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD", "Portech2026!")
assert BASE_URL.startswith("http"), f"BASE_URL not set: {BASE_URL!r}"


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS},
                      timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Auth failed: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def client(auth_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {auth_token}",
                      "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_ids():
    ids = []
    yield ids
    # No teardown via client here — done in dedicated cleanup test at end.


PROFILE_KEY = "TEST_AT_Fab #ZZTEST001"
BAR_LEN = 6800.0


# ---------------- Tests ----------------

class TestInventoryBasics:
    def test_health_list(self, client):
        r = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for key in ("bars", "chutes", "total_rows", "finishes_count", "below_min"):
            assert key in data, f"missing {key}"
        assert "clair" in data["finishes_count"]
        assert "noir" in data["finishes_count"]
        # Legacy rows should be normalized with finish="clair"
        for r0 in data["bars"]:
            assert r0.get("finish") in ("clair", "noir")
            assert "restock_min" in r0
            assert "restock_max" in r0

    def test_unauth_blocked(self):
        r = requests.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=10)
        assert r.status_code == 401


class TestInventoryCRUD:
    def test_create_clair(self, client, created_ids):
        payload = {
            "profile_key": PROFILE_KEY, "label": "TEST clair",
            "bar_length_mm": BAR_LEN, "qty_available": 3,
            "is_chute": False, "finish": "clair",
            "restock_min": 2, "restock_max": 8,
        }
        r = client.post(f"{BASE_URL}/api/admin/alu-inventory", json=payload, timeout=15)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["finish"] == "clair"
        assert body["qty_available"] == 3
        assert body["restock_min"] == 2
        assert body["restock_max"] == 8
        assert body["profile_key"] == PROFILE_KEY
        created_ids.append(body["id"])

    def test_create_noir_same_key_creates_separate_row(self, client, created_ids):
        payload = {
            "profile_key": PROFILE_KEY, "label": "TEST noir",
            "bar_length_mm": BAR_LEN, "qty_available": 1,
            "is_chute": False, "finish": "noir",
        }
        r = client.post(f"{BASE_URL}/api/admin/alu-inventory", json=payload, timeout=15)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["finish"] == "noir"
        assert body["qty_available"] == 1
        assert body["id"] not in created_ids  # different doc
        created_ids.append(body["id"])

        # Verify both exist in list
        r2 = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15)
        bars = r2.json()["bars"]
        matching = [b for b in bars if b["profile_key"] == PROFILE_KEY and b["bar_length_mm"] == BAR_LEN]
        assert len(matching) == 2
        finishes = sorted(b["finish"] for b in matching)
        assert finishes == ["clair", "noir"]

    def test_create_same_finish_merges_qty(self, client, created_ids):
        # Add another 5 clair → should merge with existing clair row
        payload = {
            "profile_key": PROFILE_KEY, "label": "TEST clair",
            "bar_length_mm": BAR_LEN, "qty_available": 5,
            "is_chute": False, "finish": "clair",
        }
        r = client.post(f"{BASE_URL}/api/admin/alu-inventory", json=payload, timeout=15)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["qty_available"] == 8  # 3 + 5
        assert body["finish"] == "clair"
        # Should be the SAME id as first clair row
        assert body["id"] == created_ids[0]

        # Verify still only 2 rows total
        r2 = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15)
        bars = r2.json()["bars"]
        matching = [b for b in bars if b["profile_key"] == PROFILE_KEY and b["bar_length_mm"] == BAR_LEN]
        assert len(matching) == 2

    def test_patch_delta_increments(self, client, created_ids):
        rid = created_ids[1]  # noir row, qty=1
        r = client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}",
                         json={"delta": 4}, timeout=15)
        assert r.status_code == 200
        assert r.json()["qty_available"] == 5

    def test_patch_delta_clamps_zero(self, client, created_ids):
        rid = created_ids[1]
        r = client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}",
                         json={"delta": -999}, timeout=15)
        assert r.status_code == 200
        assert r.json()["qty_available"] == 0  # clamped

    def test_patch_thresholds_set(self, client, created_ids):
        rid = created_ids[1]
        r = client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}/thresholds",
                         json={"restock_min": 4, "restock_max": 12}, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["restock_min"] == 4
        assert body["restock_max"] == 12

        # Verify persisted via GET-list
        r2 = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15)
        match = [b for b in r2.json()["bars"] if b["id"] == rid]
        assert len(match) == 1
        assert match[0]["restock_min"] == 4
        assert match[0]["restock_max"] == 12

    def test_patch_thresholds_unset(self, client, created_ids):
        rid = created_ids[1]
        r = client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}/thresholds",
                         json={"restock_min": None, "restock_max": None}, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["restock_min"] is None
        assert body["restock_max"] is None


class TestPurchaseOrderPDF:
    def test_pdf_with_token_query(self, client, auth_token, created_ids):
        # Make the noir row need a restock so it appears in PO
        rid = created_ids[1]
        client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}/thresholds",
                     json={"restock_min": 5, "restock_max": 10}, timeout=15)
        # Use raw requests with ?token= (NO Authorization header) to mimic
        # the new tab download behavior
        url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}"
        r = requests.get(url, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-", f"Magic not PDF: {r.content[:20]!r}"
        assert len(r.content) > 500

    def test_pdf_with_finish_filter(self, auth_token):
        for finish in ("clair", "noir"):
            url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}&finish={finish}"
            r = requests.get(url, timeout=30)
            assert r.status_code == 200
            assert r.content[:5] == b"%PDF-"

    def test_pdf_no_token_401(self):
        url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf"
        r = requests.get(url, timeout=15)
        assert r.status_code == 401


class TestCleanup:
    def test_zzz_cleanup_created_rows(self, client, created_ids):
        for rid in created_ids:
            r = client.delete(f"{BASE_URL}/api/admin/alu-inventory/{rid}", timeout=15)
            assert r.status_code in (204, 404), f"delete {rid}: {r.status_code}"
        # Verify gone
        r2 = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15)
        remaining = [b for b in r2.json()["bars"] if b["profile_key"] == PROFILE_KEY]
        assert remaining == []
