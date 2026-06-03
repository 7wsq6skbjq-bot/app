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


# =================================================================
# Iteration 9 — PATCH /meta + 3-section purchase-order PDF
# =================================================================

META_KEY = "TEST_META_AT #ZZMETA001"


class TestInventoryMetaEdit:
    """PATCH /admin/alu-inventory/{id}/meta — label/profile_key editing only.
    Must NOT touch qty / finish / length / chute. 404 on unknown id, 401 unauth."""

    def test_meta_unauth_blocked(self, client, created_ids):
        # need an existing row to target
        if not created_ids:
            pytest.skip("no row to target")
        rid = created_ids[0]
        r = requests.patch(
            f"{BASE_URL}/api/admin/alu-inventory/{rid}/meta",
            json={"label": "hack"}, timeout=10)
        # FastAPI returns 401 or 403 when no token; both are acceptable
        assert r.status_code in (401, 403), r.status_code

    def test_meta_404_on_unknown_id(self, client):
        r = client.patch(
            f"{BASE_URL}/api/admin/alu-inventory/nonexistent-id-12345/meta",
            json={"label": "doesnt matter"}, timeout=15)
        assert r.status_code == 404

    def test_meta_updates_label_only(self, client, created_ids):
        rid = created_ids[0]  # clair row, qty=8 from earlier merge test
        # Snapshot state before
        before_list = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15).json()["bars"]
        before = next(b for b in before_list if b["id"] == rid)
        new_label = "TEST clair RENAMED"
        r = client.patch(
            f"{BASE_URL}/api/admin/alu-inventory/{rid}/meta",
            json={"label": new_label}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        # label updated
        assert body["label"] == new_label
        # immutable fields preserved
        assert body["qty_available"] == before["qty_available"]
        assert body["finish"] == before["finish"]
        assert body["bar_length_mm"] == before["bar_length_mm"]
        assert body["profile_key"] == before["profile_key"]
        # normalized fields present
        assert "restock_min" in body
        assert "restock_max" in body
        # Verify persisted
        again = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15).json()["bars"]
        row = next(b for b in again if b["id"] == rid)
        assert row["label"] == new_label

    def test_meta_updates_profile_key(self, client, created_ids):
        rid = created_ids[0]
        before = next(b for b in client.get(
            f"{BASE_URL}/api/admin/alu-inventory", timeout=15
        ).json()["bars"] if b["id"] == rid)
        old_key = before["profile_key"]
        r = client.patch(
            f"{BASE_URL}/api/admin/alu-inventory/{rid}/meta",
            json={"profile_key": META_KEY}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["profile_key"] == META_KEY
        # immutable
        assert body["qty_available"] == before["qty_available"]
        assert body["finish"] == before["finish"]
        # Restore the old key so subsequent tests / cleanup keep working
        client.patch(
            f"{BASE_URL}/api/admin/alu-inventory/{rid}/meta",
            json={"profile_key": old_key}, timeout=15)

    def test_meta_empty_profile_key_kept(self, client, created_ids):
        """Empty profile_key string must NOT wipe the existing key (kept or rejected)."""
        rid = created_ids[0]
        before = next(b for b in client.get(
            f"{BASE_URL}/api/admin/alu-inventory", timeout=15
        ).json()["bars"] if b["id"] == rid)
        old_key = before["profile_key"]
        r = client.patch(
            f"{BASE_URL}/api/admin/alu-inventory/{rid}/meta",
            json={"profile_key": ""}, timeout=15)
        # Either rejected (422) or accepted but old key preserved (200)
        assert r.status_code in (200, 422), r.status_code
        if r.status_code == 200:
            assert r.json()["profile_key"] == old_key


# -----------------------------------------------------------------
# Purchase-order PDF — 3 sections layout
# -----------------------------------------------------------------

def _pdf_text(content: bytes) -> str:
    """Extract text from a PDF byte buffer with pypdf (graceful fallback)."""
    try:
        from io import BytesIO
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(content))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        return f"__PDF_EXTRACT_ERR__:{e}"


class TestPurchaseOrderPDFSections:
    """Verify the 3-section layout (FINI CLAIR / FINI NOIR / MILL FINISH recap)
    via text extraction. Also check filtered scope hides the other sections."""

    @pytest.fixture(scope="class")
    def below_min_setup(self, client, auth_token):
        """Make BOTH the clair and noir test rows be below their restock_min so
        they appear in the PO and trigger the MILL FINISH recap line."""
        # Get the current rows for our PROFILE_KEY
        bars = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15).json()["bars"]
        rows = [b for b in bars if b["profile_key"] == PROFILE_KEY]
        clair = next((b for b in rows if b["finish"] == "clair"), None)
        noir = next((b for b in rows if b["finish"] == "noir"), None)
        if not (clair and noir):
            pytest.skip("Setup rows missing — earlier tests skipped/failed.")
        # Set qty=0 for noir (test_patch_delta_clamps_zero already did this)
        # Force clair qty low (1) and very high min so it's below
        client.patch(f"{BASE_URL}/api/admin/alu-inventory/{clair['id']}",
                     json={"delta": -clair["qty_available"] + 1}, timeout=15)
        client.patch(f"{BASE_URL}/api/admin/alu-inventory/{clair['id']}/thresholds",
                     json={"restock_min": 10, "restock_max": 20}, timeout=15)
        client.patch(f"{BASE_URL}/api/admin/alu-inventory/{noir['id']}/thresholds",
                     json={"restock_min": 5, "restock_max": 10}, timeout=15)
        return {"clair_id": clair["id"], "noir_id": noir["id"]}

    def test_pdf_full_has_3_sections(self, auth_token, below_min_setup):
        url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}"
        r = requests.get(url, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        text = _pdf_text(r.content)
        # Headers must show the 3 distinct sections + grand total
        assert "FINI CLAIR" in text, f"Missing FINI CLAIR; got: {text[:500]!r}"
        assert "FINI NOIR" in text, f"Missing FINI NOIR; got: {text[:500]!r}"
        assert "MILL FINISH" in text, f"Missing MILL FINISH; got: {text[:500]!r}"
        # Grand total footer mentions clair + noir = total
        assert "clair" in text.lower() and "noir" in text.lower()
        assert "TOTAL" in text

    def test_pdf_filter_clair_only(self, auth_token, below_min_setup):
        url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}&finish=clair"
        r = requests.get(url, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        text = _pdf_text(r.content)
        assert "FINI CLAIR" in text
        # No NOIR section header and no MILL FINISH recap when filtered
        assert "FINI NOIR" not in text
        assert "MILL FINISH" not in text

    def test_pdf_filter_noir_only(self, auth_token, below_min_setup):
        url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}&finish=noir"
        r = requests.get(url, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        text = _pdf_text(r.content)
        assert "FINI NOIR" in text
        assert "FINI CLAIR" not in text
        assert "MILL FINISH" not in text

    def test_pdf_size_ordering(self, auth_token, below_min_setup):
        """Fallback structural check: full PDF must be >= each single-section PDF."""
        def _size(qs: str) -> int:
            url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}{qs}"
            return len(requests.get(url, timeout=30).content)
        size_full = _size("")
        size_clair = _size("&finish=clair")
        size_noir = _size("&finish=noir")
        # Full PDF has CLAIR + NOIR + MILL FINISH so must exceed either single
        assert size_full >= size_clair, (size_full, size_clair)
        assert size_full >= size_noir, (size_full, size_noir)


class TestPurchaseOrderEmpty:
    """When the inventory has no row below its min (i.e., after our cleanup or
    when nothing is configured), the PDF should still return 200 with the
    'Aucune commande necessaire' message."""

    def test_pdf_empty_returns_200_with_message(self, client, auth_token, created_ids):
        # Make sure NO test row triggers a restock: clear thresholds + add qty
        for rid in created_ids:
            try:
                client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}/thresholds",
                             json={"restock_min": None, "restock_max": None}, timeout=15)
                client.patch(f"{BASE_URL}/api/admin/alu-inventory/{rid}",
                             json={"delta": 100}, timeout=15)
            except Exception:
                pass
        url = f"{BASE_URL}/api/admin/alu-inventory/purchase-order.pdf?token={auth_token}"
        r = requests.get(url, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        text = _pdf_text(r.content)
        # The empty-inventory message (ASCII-folded inside the renderer)
        assert "Aucune commande" in text, f"Expected empty msg, got: {text[:500]!r}"


class TestCleanup:
    def test_zzz_cleanup_created_rows(self, client, created_ids):
        for rid in created_ids:
            r = client.delete(f"{BASE_URL}/api/admin/alu-inventory/{rid}", timeout=15)
            assert r.status_code in (204, 404), f"delete {rid}: {r.status_code}"
        # Verify gone
        r2 = client.get(f"{BASE_URL}/api/admin/alu-inventory", timeout=15)
        remaining = [b for b in r2.json()["bars"] if b["profile_key"] == PROFILE_KEY]
        assert remaining == []
        # Also drop any META_KEY leftover if a re-keyed row escaped cleanup
        for b in r2.json()["bars"]:
            if b.get("profile_key") == META_KEY:
                client.delete(f"{BASE_URL}/api/admin/alu-inventory/{b['id']}", timeout=15)
