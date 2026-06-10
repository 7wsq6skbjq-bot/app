"""Backend tests for AT Fabrication orders module.

Covers:
- Admin login
- POST /api/admin/at-orders/to-cut-list  (per-door breakdown into cut list)
- POST /api/admin/at-orders/shop-drawing.pdf  (PDF with profile cross-section pages)
- POST /api/admin/at-orders (save) and GET /api/admin/at-orders/{id} (hardware nested in doors)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://dev-retrieval.preview.emergentagent.com").rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "PortechAdmin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "Portech2026!")


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS},
                      timeout=20)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def sample_order():
    return {
        "client": "TEST_Client",
        "order_number": "TEST-AT-001",
        "project_name": "TEST_Project",
        "finish_exterior": "Noir mat",
        "doors": [
            {
                "tag": "P-100",
                "series": "AT1000",
                "width_in": 36.0,
                "height_in": 84.0,
                "qty": 1,
                "hand": "DE",
                "glazing": "thermos",
                "hardware": {"hinge_continuous": True, "pull_12_back_to_back": True},
            },
            {
                "tag": "P-101",
                "series": "ATi2000",
                "width_in": 35.5,
                "height_in": 83.0,
                "qty": 1,
                "hand": "GE",
                "glazing": "simple",
                "hardware": {"hinge_4_5x4": True, "lock_4510_ar": True},
            },
        ],
    }


# -----------------------------------------------------------------------
# AT Order → Cut List
# -----------------------------------------------------------------------
class TestAtOrderToCutList:
    def test_create_cut_list_from_at_order(self, auth_headers, sample_order):
        r = requests.post(f"{BASE_URL}/api/admin/at-orders/to-cut-list",
                          json=sample_order, headers=auth_headers, timeout=30)
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        assert "id" in data and isinstance(data["id"], str) and data["id"]
        assert "name" in data and "AT" in data["name"]
        assert "items_count" in data
        # 2 doors → many items each (head, base, hinge stile, lock stile, V & H parclose, glass...)
        assert data["items_count"] >= 5, f"items_count too low: {data['items_count']}"

    def test_create_cut_list_empty_doors_returns_400(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/admin/at-orders/to-cut-list",
                          json={"client": "X", "doors": []}, headers=auth_headers, timeout=15)
        assert r.status_code == 400

    def test_unauthenticated_returns_401(self, sample_order):
        r = requests.post(f"{BASE_URL}/api/admin/at-orders/to-cut-list",
                          json=sample_order, timeout=15)
        assert r.status_code in (401, 403)


# -----------------------------------------------------------------------
# Shop drawing PDF
# -----------------------------------------------------------------------
class TestShopDrawingPDF:
    def test_shop_drawing_pdf_has_profile_pages(self, auth_headers, sample_order):
        r = requests.post(f"{BASE_URL}/api/admin/at-orders/shop-drawing.pdf",
                          json=sample_order, headers=auth_headers, timeout=60)
        assert r.status_code == 200, f"Status {r.status_code}: {r.text[:300]}"
        ctype = r.headers.get("content-type", "")
        assert "application/pdf" in ctype, f"Wrong content-type: {ctype}"
        body = r.content
        assert body[:4] == b"%PDF", "Body doesn't start with %PDF"
        assert len(body) > 5000, f"PDF too small: {len(body)} bytes"
        # Try to extract text to verify Phase 2 profile pages were added
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(body))
            assert len(reader.pages) >= 4, f"PDF too few pages: {len(reader.pages)}"
            all_text = ""
            for p in reader.pages:
                try:
                    all_text += (p.extract_text() or "") + "\n"
                except Exception:
                    pass
            lt = all_text.lower()
            # Should mention "Profilés" (heading) or "coupes transversales" or AT profile codes
            has_marker = (
                "profil" in lt
                or "coupes transversales" in lt
                or "att1005" in lt
                or "atb1000" in lt
            )
            assert has_marker, f"PDF missing Phase 2 profile marker. Text sample: {all_text[:500]}"
        except ImportError:
            pytest.skip("pypdf not installed - skipping content check (body looks valid)")


# -----------------------------------------------------------------------
# Save + retrieve (hardware nested in doors)
# -----------------------------------------------------------------------
class TestSaveAndRetrieve:
    def test_save_and_get_keeps_hardware_in_doors(self, auth_headers, sample_order):
        s = requests.post(f"{BASE_URL}/api/admin/at-orders",
                          json=sample_order, headers=auth_headers, timeout=15)
        assert s.status_code == 201, f"Save failed: {s.status_code} {s.text}"
        saved = s.json()
        oid = saved["id"]

        g = requests.get(f"{BASE_URL}/api/admin/at-orders/{oid}",
                         headers=auth_headers, timeout=15)
        assert g.status_code == 200
        row = g.json()
        assert row["id"] == oid
        assert len(row["doors"]) == 2
        # Hardware must be nested per door
        assert "hardware" in row["doors"][0]
        assert row["doors"][0]["hardware"]["hinge_continuous"] is True
        assert row["doors"][0]["hardware"]["pull_12_back_to_back"] is True
        assert row["doors"][1]["hardware"]["hinge_4_5x4"] is True
        # P-100 must NOT have leaked P-101 hardware
        assert row["doors"][0]["hardware"].get("hinge_4_5x4", False) is False
        # Cleanup
        requests.delete(f"{BASE_URL}/api/admin/at-orders/{oid}", headers=auth_headers, timeout=10)

    def test_legacy_v1_order_top_level_hardware_still_loads(self, auth_headers):
        """A v1-style order with top-level hardware should still POST and GET successfully
        (top-level hardware kept as optional field; doors retain their own)."""
        v1 = {
            "client": "TEST_Legacy",
            "order_number": "TEST-LEGACY-1",
            "hardware": {"hinge_continuous": True},  # legacy top-level
            "doors": [{"tag": "P-1", "series": "AT1000",
                       "width_in": 36, "height_in": 84,
                       "hardware": {}}],
        }
        s = requests.post(f"{BASE_URL}/api/admin/at-orders",
                          json=v1, headers=auth_headers, timeout=15)
        assert s.status_code == 201, f"Save failed: {s.status_code} {s.text}"
        oid = s.json()["id"]
        g = requests.get(f"{BASE_URL}/api/admin/at-orders/{oid}", headers=auth_headers, timeout=10)
        assert g.status_code == 200
        row = g.json()
        # doors[0] hardware exists (even if empty defaults applied)
        assert "hardware" in row["doors"][0]
        requests.delete(f"{BASE_URL}/api/admin/at-orders/{oid}", headers=auth_headers, timeout=10)
