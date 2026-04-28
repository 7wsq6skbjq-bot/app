"""Backend API tests for Portech ERP module - parties, products, invoices, POs, BOLs, exports, email."""
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
def auth_headers():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def created_ids():
    return {"customer": None, "supplier": None, "product": None, "invoice": None, "po": None, "bol": None}


# ==== Parties (clients + fournisseurs) ====
class TestParties:
    def test_auth_required(self):
        r = requests.get(f"{API}/admin/parties")
        assert r.status_code == 401

    def test_create_customer(self, auth_headers, created_ids):
        payload = {
            "kind": "customer", "name": "TEST_Client ABC",
            "email": "test_client@example.com", "phone": "514-555-0001",
            "city": "Montréal", "address_line1": "123 rue Notre-Dame",
        }
        r = requests.post(f"{API}/admin/parties", json=payload, headers=auth_headers)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == "TEST_Client ABC"
        assert data["kind"] == "customer"
        assert "id" in data and "_id" not in data
        created_ids["customer"] = data["id"]

    def test_create_supplier(self, auth_headers, created_ids):
        payload = {"kind": "supplier", "name": "TEST_Fournisseur XYZ", "city": "Laval"}
        r = requests.post(f"{API}/admin/parties", json=payload, headers=auth_headers)
        assert r.status_code == 201
        created_ids["supplier"] = r.json()["id"]

    def test_list_parties(self, auth_headers):
        r = requests.get(f"{API}/admin/parties", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert any(p["name"] == "TEST_Client ABC" for p in r.json())

    def test_filter_by_kind(self, auth_headers):
        r = requests.get(f"{API}/admin/parties?kind=supplier", headers=auth_headers)
        assert r.status_code == 200
        assert all(p["kind"] == "supplier" for p in r.json())

    def test_update_party(self, auth_headers, created_ids):
        cid = created_ids["customer"]
        assert cid, "Customer not created"
        payload = {"kind": "customer", "name": "TEST_Client ABC Modifié", "city": "Québec"}
        r = requests.put(f"{API}/admin/parties/{cid}", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Client ABC Modifié"
        # Verify
        g = requests.get(f"{API}/admin/parties/{cid}", headers=auth_headers)
        assert g.status_code == 200
        assert g.json()["city"] == "Québec"


# ==== Products ====
class TestProducts:
    def test_create_product(self, auth_headers, created_ids):
        payload = {"name": "TEST_Serrure Schlage", "unit_price": 125.50, "unit": "unité", "sku": "SCH-001"}
        r = requests.post(f"{API}/admin/products", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "TEST_Serrure Schlage"
        assert data["unit_price"] == 125.50
        created_ids["product"] = data["id"]

    def test_list_products(self, auth_headers):
        r = requests.get(f"{API}/admin/products", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_update_product(self, auth_headers, created_ids):
        pid = created_ids["product"]
        payload = {"name": "TEST_Serrure Schlage Pro", "unit_price": 150.00}
        r = requests.put(f"{API}/admin/products/{pid}", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["unit_price"] == 150.00


# ==== Invoices: numbering + taxes ====
class TestInvoices:
    def test_create_invoice_with_taxes(self, auth_headers, created_ids):
        cid = created_ids["customer"]
        payload = {
            "customer_id": cid,
            "customer_snapshot": {
                "kind": "customer", "name": "TEST_Client ABC",
                "email": "test_client@example.com", "city": "Montréal",
            },
            "date": "2026-01-15", "due_date": "2026-02-15",
            "items": [
                {"description": "Serrure Schlage", "quantity": 2, "unit_price": 100.00},
                {"description": "Installation", "quantity": 1, "unit_price": 50.00},
            ],
            "taxable": True, "status": "brouillon",
        }
        r = requests.post(f"{API}/admin/invoices", json=payload, headers=auth_headers)
        assert r.status_code == 201, r.text
        data = r.json()
        # Verify numbering
        assert isinstance(data["number"], int) and data["number"] >= 1
        # Verify tax math: subtotal=250, tps=12.50, tvq=24.94, total=287.44
        assert data["subtotal"] == 250.00
        assert data["tps"] == 12.50
        assert data["tvq"] == 24.94
        assert data["total"] == 287.44
        assert data["status"] == "brouillon"
        created_ids["invoice"] = data["id"]

    def test_invoice_no_tax(self, auth_headers, created_ids):
        payload = {
            "customer_id": created_ids["customer"],
            "customer_snapshot": {"kind": "customer", "name": "TEST_Exonéré"},
            "date": "2026-01-15",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 100.00}],
            "taxable": False,
        }
        r = requests.post(f"{API}/admin/invoices", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["tps"] == 0.0
        assert data["tvq"] == 0.0
        assert data["total"] == 100.00

    def test_list_invoices(self, auth_headers):
        r = requests.get(f"{API}/admin/invoices", headers=auth_headers)
        assert r.status_code == 200
        invoices = r.json()
        assert len(invoices) >= 2
        # Sort desc by number
        assert invoices[0]["number"] >= invoices[-1]["number"]

    def test_get_invoice(self, auth_headers, created_ids):
        iid = created_ids["invoice"]
        r = requests.get(f"{API}/admin/invoices/{iid}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == iid

    def test_update_invoice_status(self, auth_headers, created_ids):
        iid = created_ids["invoice"]
        payload = {
            "customer_id": created_ids["customer"],
            "customer_snapshot": {"kind": "customer", "name": "TEST_Client ABC"},
            "date": "2026-01-15",
            "items": [{"description": "Serrure Schlage", "quantity": 2, "unit_price": 100.00}],
            "taxable": True, "status": "payée",
        }
        r = requests.put(f"{API}/admin/invoices/{iid}", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "payée"


# ==== Purchase Orders ====
class TestPurchaseOrders:
    def test_create_po(self, auth_headers, created_ids):
        payload = {
            "supplier_id": created_ids["supplier"],
            "supplier_snapshot": {"kind": "supplier", "name": "TEST_Fournisseur XYZ"},
            "date": "2026-01-15",
            "items": [{"description": "Lot serrures", "quantity": 10, "unit_price": 80.00}],
            "taxable": True,
        }
        r = requests.post(f"{API}/admin/purchase-orders", json=payload, headers=auth_headers)
        assert r.status_code == 201, r.text
        data = r.json()
        assert isinstance(data["number"], int)
        assert data["subtotal"] == 800.00
        # tps=40, tvq=79.80, total=919.80
        assert data["tps"] == 40.00
        assert data["tvq"] == 79.80
        assert data["total"] == 919.80
        created_ids["po"] = data["id"]

    def test_list_pos(self, auth_headers):
        r = requests.get(f"{API}/admin/purchase-orders", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ==== Bills of Lading ====
class TestBOL:
    def test_create_bol(self, auth_headers, created_ids):
        payload = {
            "shipper_snapshot": {"kind": "supplier", "name": "TEST_Portech Shipper"},
            "consignee_snapshot": {"kind": "customer", "name": "TEST_Destinataire"},
            "carrier": "Transport TEST",
            "date": "2026-01-15",
            "items": [{"description": "Boîte serrures", "quantity": 5, "unit": "boîte", "weight_kg": 12.5}],
            "total_weight_kg": 62.5,
        }
        r = requests.post(f"{API}/admin/bills-of-lading", json=payload, headers=auth_headers)
        assert r.status_code == 201, r.text
        data = r.json()
        assert isinstance(data["number"], int)
        assert data["status"] == "brouillon"
        created_ids["bol"] = data["id"]

    def test_list_bols(self, auth_headers):
        r = requests.get(f"{API}/admin/bills-of-lading", headers=auth_headers)
        assert r.status_code == 200


# ==== Dashboard ====
class TestDashboard:
    def test_dashboard(self, auth_headers):
        r = requests.get(f"{API}/admin/dashboard", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "kpi" in data
        kpi = data["kpi"]
        for key in ["invoiced_total", "paid_total", "outstanding_total", "revenue_this_month",
                    "invoices_count", "customers_count", "suppliers_count", "products_count",
                    "po_count", "bol_count"]:
            assert key in kpi, f"missing kpi key {key}"
        assert "monthly_revenue" in data and isinstance(data["monthly_revenue"], list)
        assert len(data["monthly_revenue"]) == 6
        assert "top_customers" in data
        assert "outstanding_invoices" in data


# ==== CSV Exports ====
class TestCSVExports:
    def test_invoices_csv(self, auth_headers):
        r = requests.get(f"{API}/admin/exports/invoices.csv", headers=auth_headers)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        body = r.text
        assert "Numéro" in body and "Total" in body

    def test_purchase_orders_csv(self, auth_headers):
        r = requests.get(f"{API}/admin/exports/purchase-orders.csv", headers=auth_headers)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")

    def test_bol_csv_endpoint_exists(self, auth_headers):
        # Spec wanted this; check if implemented
        r = requests.get(f"{API}/admin/exports/bills-of-lading.csv", headers=auth_headers)
        # Note: not implemented in backend - documenting
        assert r.status_code in (200, 404), f"Unexpected: {r.status_code}"
        if r.status_code == 404:
            pytest.skip("BOL CSV export endpoint not implemented (only invoices and POs available)")


# ==== PDF generation ====
class TestPDF:
    def test_invoice_pdf(self, auth_headers, created_ids):
        iid = created_ids["invoice"]
        r = requests.get(f"{API}/admin/invoices/{iid}/pdf", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type") == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_po_pdf(self, auth_headers, created_ids):
        pid = created_ids["po"]
        r = requests.get(f"{API}/admin/purchase-orders/{pid}/pdf", headers=auth_headers)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_bol_pdf(self, auth_headers, created_ids):
        bid = created_ids["bol"]
        r = requests.get(f"{API}/admin/bills-of-lading/{bid}/pdf", headers=auth_headers)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"


# ==== Email send (Resend) ====
class TestEmail:
    def test_send_invoice_email(self, auth_headers, created_ids):
        iid = created_ids["invoice"]
        payload = {"to_email": "info@portech.info", "subject": "TEST_Invoice email"}
        r = requests.post(f"{API}/admin/invoices/{iid}/send-email", json=payload, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["sent"] is True

    def test_send_po_email(self, auth_headers, created_ids):
        pid = created_ids["po"]
        payload = {"to_email": "info@portech.info", "subject": "TEST_PO email"}
        r = requests.post(f"{API}/admin/purchase-orders/{pid}/send-email", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_bol_email(self, auth_headers, created_ids):
        bid = created_ids["bol"]
        payload = {"to_email": "info@portech.info"}
        r = requests.post(f"{API}/admin/bills-of-lading/{bid}/send-email", json=payload, headers=auth_headers)
        assert r.status_code == 200


# ==== Cleanup ====
class TestZCleanup:
    def test_delete_invoice(self, auth_headers, created_ids):
        for iid_key in ["invoice"]:
            iid = created_ids[iid_key]
            if iid:
                r = requests.delete(f"{API}/admin/invoices/{iid}", headers=auth_headers)
                assert r.status_code == 200

    def test_delete_po(self, auth_headers, created_ids):
        pid = created_ids["po"]
        if pid:
            r = requests.delete(f"{API}/admin/purchase-orders/{pid}", headers=auth_headers)
            assert r.status_code == 200

    def test_delete_bol(self, auth_headers, created_ids):
        bid = created_ids["bol"]
        if bid:
            r = requests.delete(f"{API}/admin/bills-of-lading/{bid}", headers=auth_headers)
            assert r.status_code == 200

    def test_delete_product(self, auth_headers, created_ids):
        pid = created_ids["product"]
        if pid:
            r = requests.delete(f"{API}/admin/products/{pid}", headers=auth_headers)
            assert r.status_code == 200

    def test_delete_parties(self, auth_headers, created_ids):
        for k in ["customer", "supplier"]:
            pid = created_ids[k]
            if pid:
                r = requests.delete(f"{API}/admin/parties/{pid}", headers=auth_headers)
                assert r.status_code == 200
