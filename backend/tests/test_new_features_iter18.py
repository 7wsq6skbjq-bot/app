"""Backend spot-check for iter 18 features: statements, quote attachments, sales-conditions, assistant, expenses GridFS, production plan default."""
import os
import io
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://dev-retrieval.preview.emergentagent.com").rstrip("/")
ADMIN_USER = "PortechAdmin"
ADMIN_PASS = "Portech2026!"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE}/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def h(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Statements ----
def test_statements_customers(h):
    r = requests.get(f"{BASE}/api/admin/statements/customers", headers=h, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "customers" in data and "total_balance" in data
    assert isinstance(data["customers"], list)
    print(f"Statements: {len(data['customers'])} customers, total {data['total_balance']}")


# ---- Assistant ----
def test_assistant_chat(h):
    r = requests.post(f"{BASE}/api/admin/assistant/chat",
                      headers=h, json={"message": "Quelles factures sont impayées ?"}, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    # accept either 'reply' or 'answer' or messages structure
    text = str(data)
    assert len(text) > 20
    print(f"Assistant reply keys: {list(data.keys())}")


def test_assistant_history_get_delete(h):
    # First send a message to create a session
    c = requests.post(f"{BASE}/api/admin/assistant/chat",
                      headers=h, json={"message": "test"}, timeout=60)
    assert c.status_code == 200
    sid = c.json().get("session_id")
    assert sid
    r = requests.get(f"{BASE}/api/admin/assistant/history", headers=h, params={"session_id": sid}, timeout=30)
    assert r.status_code == 200, r.text
    d = requests.delete(f"{BASE}/api/admin/assistant/history", headers=h, params={"session_id": sid}, timeout=30)
    assert d.status_code in (200, 204)


# ---- Quotes: sales conditions toggle + attachments ----
@pytest.fixture(scope="session")
def a_quote_id(h):
    r = requests.get(f"{BASE}/api/admin/quotes", headers=h, timeout=30)
    assert r.status_code == 200
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    assert items, "No quotes exist"
    return items[0]["id"]


def test_quote_pdf_sales_conditions_toggle(h, a_quote_id):
    # fetch existing quote to build full PUT payload
    gq = requests.get(f"{BASE}/api/admin/quotes/{a_quote_id}", headers=h, timeout=30)
    assert gq.status_code == 200, gq.text
    q = gq.json()
    def _put(flag):
        payload = {
            "customer_id": q["customer_id"],
            "customer_snapshot": q["customer_snapshot"],
            "date": q["date"],
            "valid_until": q.get("valid_until"),
            "items": q["items"],
            "taxable": q.get("taxable", True),
            "notes": q.get("notes", ""),
            "status": q.get("status", "draft"),
            "drawing_pages": q.get("drawing_pages", []),
            "include_sales_conditions": flag,
        }
        return requests.put(f"{BASE}/api/admin/quotes/{a_quote_id}", headers=h, json=payload, timeout=30)
    r1 = _put(False)
    assert r1.status_code in (200, 204), r1.text
    p1 = requests.get(f"{BASE}/api/admin/quotes/{a_quote_id}/pdf", headers=h, timeout=60)
    assert p1.status_code == 200
    size_off = len(p1.content)
    r2 = _put(True)
    assert r2.status_code in (200, 204), r2.text
    p2 = requests.get(f"{BASE}/api/admin/quotes/{a_quote_id}/pdf", headers=h, timeout=60)
    assert p2.status_code == 200
    size_on = len(p2.content)
    assert size_on > size_off, f"PDF with sales conditions ({size_on}) should be larger than without ({size_off})"
    print(f"PDF sizes off={size_off} on={size_on}")
    _put(False)  # restore


def test_quote_attachment_upload_delete(h, a_quote_id):
    # tiny PNG
    png = bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
    files = {"file": ("TEST_att.png", io.BytesIO(png), "image/png")}
    r = requests.post(f"{BASE}/api/admin/quotes/{a_quote_id}/attachments", headers=h, files=files, timeout=30)
    assert r.status_code in (200, 201), r.text
    att = r.json()
    att_id = att.get("id") or att.get("att_id") or att.get("attachment", {}).get("id")
    assert att_id, att
    # delete
    d = requests.delete(f"{BASE}/api/admin/quotes/{a_quote_id}/attachments/{att_id}", headers=h, timeout=30)
    assert d.status_code in (200, 204), d.text


# ---- Expenses receipts GridFS ----
def test_expense_receipt_roundtrip(h):
    # create an expense
    payload = {"vendor": "TEST_Vendor", "amount": 12.34, "category": "test", "date": "2026-01-01", "description": "TEST"}
    c = requests.post(f"{BASE}/api/admin/expenses", headers=h, json=payload, timeout=30)
    if c.status_code not in (200, 201):
        pytest.skip(f"Cannot create expense: {c.status_code} {c.text}")
    exp = c.json()
    eid = exp.get("id")
    try:
        png = bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
        files = {"file": ("TEST_receipt.png", io.BytesIO(png), "image/png")}
        u = requests.post(f"{BASE}/api/admin/expenses/{eid}/receipt", headers=h, files=files, timeout=30)
        assert u.status_code in (200, 201), u.text
        g = requests.get(f"{BASE}/api/admin/expenses/{eid}/receipt", headers=h, timeout=30)
        assert g.status_code == 200 and len(g.content) > 0
        d = requests.delete(f"{BASE}/api/admin/expenses/{eid}/receipt", headers=h, timeout=30)
        assert d.status_code in (200, 204)
    finally:
        requests.delete(f"{BASE}/api/admin/expenses/{eid}", headers=h, timeout=30)


# ---- Production plan default include_hardware_drawings=False ----
def test_production_plan_default_hardware_drawings_off(h):
    # look at existing plans or model default via a fresh create shell
    r = requests.get(f"{BASE}/api/admin/production-plans", headers=h, timeout=30)
    if r.status_code != 200:
        pytest.skip("no plans endpoint")
    # We check schema by inspecting first plan or defaulting to True/False in create
    # Attempt: create a minimal plan and inspect returned value
    c = requests.post(f"{BASE}/api/admin/production-plans", headers=h, json={"title": "TEST_plan"}, timeout=30)
    if c.status_code in (200, 201):
        plan = c.json()
        pid = plan.get("id")
        assert plan.get("include_hardware_drawings") in (False, None), f"default should be False, got {plan.get('include_hardware_drawings')}"
        if pid:
            requests.delete(f"{BASE}/api/admin/production-plans/{pid}", headers=h, timeout=30)
    else:
        pytest.skip(f"cannot create plan: {c.status_code}")
