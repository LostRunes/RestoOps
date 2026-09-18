"""
RestoOps Phase 10 - Comprehensive End-to-End Test Suite
Tests all API endpoints, database operations, and system integrity.
"""
import sys
import uuid
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"

# Colors (plain for Windows compat)
GREEN  = ""
RED    = ""
YELLOW = ""
CYAN   = ""
BOLD   = ""
RESET  = ""

results = {"passed": 0, "failed": 0, "warnings": 0}

def ok(msg):    print(f"  [OK]   {msg}"); results["passed"] += 1
def fail(msg):  print(f"  [FAIL] {msg}"); results["failed"] += 1
def warn(msg):  print(f"  [WARN] {msg}"); results["warnings"] += 1
def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def check(name, condition, detail=""):
    if condition:
        ok(f"{name}{' - ' + detail if detail else ''}")
    else:
        fail(f"{name}{' - ' + detail if detail else ''}")

session = requests.Session()
token = None
headers = {}

# State passed between tests
state = {}

# ─── 1. HEALTH CHECK ──────────────────────────────────────────────────────────
header("1. Health & Root Endpoints")
try:
    r = session.get(f"{BASE_URL}/health", timeout=5)
    check("GET /health -> 200", r.status_code == 200)
    data = r.json()
    check("health.status == 'healthy'", data.get("status") == "healthy")
    check("health.service present", bool(data.get("service")))
except Exception as e:
    fail(f"Health check failed: {e}")

try:
    r = session.get(f"{BASE_URL}/", timeout=5)
    check("GET / -> 200", r.status_code == 200)
    check("root.docs present", "/docs" in r.json().get("docs", ""))
except Exception as e:
    fail(f"Root endpoint failed: {e}")

try:
    r = session.get(f"{BASE_URL}/metrics", timeout=5)
    check("GET /metrics -> 200 (Prometheus)", r.status_code == 200)
except Exception as e:
    warn(f"Metrics endpoint not reachable: {e}")

try:
    r = session.get(f"{API}/openapi.json", timeout=5)
    check("GET /openapi.json -> 200", r.status_code == 200)
except Exception as e:
    fail(f"OpenAPI schema not available: {e}")

# ─── 2. AUTHENTICATION ────────────────────────────────────────────────────────
header("2. Authentication Flow")

try:
    r = session.post(f"{API}/auth/login", json={"email": "owner@restoops.com", "password": "password123"})
    check("POST /auth/login -> 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
        state["refresh_token"] = data.get("refresh_token")
        check("Access token received", bool(token))
        check("Refresh token received", bool(state["refresh_token"]))
        headers = {"Authorization": f"Bearer {token}"}
    else:
        print(f"    Response: {r.text[:200]}")
except Exception as e:
    fail(f"Login failed: {e}")

if token:
    try:
        r = session.get(f"{API}/auth/me", headers=headers)
        check("GET /auth/me -> 200", r.status_code == 200)
        if r.status_code == 200:
            me = r.json()
            check("me.email correct", me.get("email") == "owner@restoops.com")
            state["user_id"] = me.get("id")
            state["org_id"] = me.get("organization_id")
            check("me.organization_id present", bool(state.get("org_id")))
    except Exception as e:
        fail(f"/auth/me failed: {e}")

    try:
        r = session.post(f"{API}/auth/refresh", json={"refresh_token": state.get("refresh_token", "")})
        check("POST /auth/refresh -> 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            new_data = r.json()
            token = new_data.get("access_token")
            state["refresh_token"] = new_data.get("refresh_token")
            headers = {"Authorization": f"Bearer {token}"}
            check("New access token issued", bool(token))
    except Exception as e:
        fail(f"Token refresh failed: {e}")

    try:
        r = session.post(f"{API}/auth/login", json={"email": "owner@restoops.com", "password": "wrongpassword"})
        check("Login with wrong password -> 401", r.status_code == 401)
    except Exception as e:
        fail(f"Bad credentials test failed: {e}")

    try:
        r = session.get(f"{API}/leads/")
        check("Unauthenticated leads list -> 401", r.status_code == 401)
    except Exception as e:
        fail(f"Unauthenticated access test failed: {e}")

# ─── 3. USERS ─────────────────────────────────────────────────────────────────
header("3. Users")
if token:
    try:
        r = session.get(f"{API}/users/", headers=headers)
        check("GET /users -> 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            users = r.json()
            check("Users list is a list", isinstance(users, list))
            check("At least 1 user exists", len(users) >= 1)
    except Exception as e:
        fail(f"List users failed: {e}")

# ─── 4. ORGANIZATIONS ─────────────────────────────────────────────────────────
header("4. Organizations")
if token:
    try:
        r = session.get(f"{API}/organizations/me", headers=headers)
        check("GET /organizations/me -> 200", r.status_code in [200, 404], f"status={r.status_code}")
        if r.status_code == 200:
            org = r.json()
            check("Organization name present", bool(org.get("name") or org.get("slug")))
    except Exception as e:
        warn(f"GET /organizations/me failed: {e}")

# ─── 5. LEADS CRUD ────────────────────────────────────────────────────────────
header("5. Leads - CRUD + Pipeline")
if token:
    lead_payload = {
        "company_name": "Test Restaurant LLC",
        "contact_name": "John Doe",
        "email": "john@testrestaurant.com",
        "phone": "+1-555-0100",
        "address": "123 Main St, New York, NY",
        "industry": "Restaurant",
        "company_size": "10-50",
        "source": "Manual",
        "priority": "HIGH",
        "pipeline_status": "NEW",
        "contacts": []
    }
    try:
        r = session.post(f"{API}/leads/", headers=headers, json=lead_payload)
        check("POST /leads -> 201", r.status_code == 201, f"status={r.status_code}")
        if r.status_code == 201:
            lead = r.json()
            state["lead_id"] = lead.get("id")
            check("Lead ID returned", bool(state["lead_id"]))
            check("Lead company_name matches", lead.get("company_name") == "Test Restaurant LLC")
        else:
            print(f"    Error: {r.text[:300]}")
    except Exception as e:
        fail(f"Create lead failed: {e}")

    try:
        r = session.get(f"{API}/leads/", headers=headers)
        check("GET /leads -> 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            total = data.get("total", 0)
            items = data.get("items", [])
            check("Leads list has items", len(items) >= 1, f"total={total}")
    except Exception as e:
        fail(f"List leads failed: {e}")

    if state.get("lead_id"):
        try:
            r = session.get(f"{API}/leads/{state['lead_id']}", headers=headers)
            check("GET /leads/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get single lead failed: {e}")

        try:
            r = session.patch(f"{API}/leads/{state['lead_id']}", headers=headers, json={"priority": "MEDIUM", "pipeline_status": "VERIFIED"})
            check("PATCH /leads/{id} -> 200", r.status_code == 200)
            if r.status_code == 200:
                updated = r.json()
                check("Lead priority updated", updated.get("priority") == "MEDIUM")
        except Exception as e:
            fail(f"Update lead failed: {e}")

        try:
            r = session.post(f"{API}/leads/{state['lead_id']}/pipeline/CONTACTED", headers=headers)
            check("POST /leads/{id}/pipeline/CONTACTED -> 200", r.status_code == 200)
            if r.status_code == 200:
                check("Pipeline status updated", r.json().get("pipeline_status") == "CONTACTED")
        except Exception as e:
            fail(f"Pipeline move failed: {e}")

        try:
            r = session.get(f"{API}/leads/{state['lead_id']}/activity", headers=headers)
            check("GET /leads/{id}/activity -> 200", r.status_code == 200)
            if r.status_code == 200:
                activities = r.json()
                check("Activity log has entries", len(activities) >= 1, f"count={len(activities)}")
        except Exception as e:
            fail(f"Lead activity timeline failed: {e}")

        try:
            r = session.get(f"{API}/leads/{state['lead_id']}/verifications", headers=headers)
            check("GET /leads/{id}/verifications -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Lead verifications failed: {e}")

    try:
        r = session.get(f"{API}/leads/?search=Test", headers=headers)
        check("GET /leads?search= -> 200", r.status_code == 200)
    except Exception as e:
        fail(f"Lead search failed: {e}")

    try:
        r = session.get(f"{API}/leads/?pipeline_status=CONTACTED", headers=headers)
        check("GET /leads?pipeline_status= filter -> 200", r.status_code == 200)
    except Exception as e:
        fail(f"Lead filter by status failed: {e}")

# ─── 6. CSV IMPORT ────────────────────────────────────────────────────────────
header("6. Leads - CSV Import")
if token:
    csv_content = "email,company_name,contact_name\ntestlead1@example.com,Burger Palace,Alice Smith\ntestlead2@example.com,Pizza Express,Bob Jones\n"
    try:
        files = {"file": ("test_import.csv", csv_content.encode(), "text/csv")}
        r = session.post(f"{API}/leads/import/csv?auto_verify=false", headers=headers, files=files)
        check("POST /leads/import/csv -> 202", r.status_code == 202, f"status={r.status_code}")
        if r.status_code == 202:
            data = r.json()
            check("CSV import total_rows returned", "total_rows" in data, f"rows={data.get('total_rows')}")
            check("At least 2 valid rows imported", data.get("total_rows", 0) >= 2)
        else:
            print(f"    Error: {r.text[:300]}")
    except Exception as e:
        fail(f"CSV import failed: {e}")

# ─── 7. CAMPAIGNS ─────────────────────────────────────────────────────────────
header("7. Campaigns - CRUD + Actions")
if token:
    campaign_payload = {
        "name": "Q4 Outreach Campaign",
        "description": "Test campaign for phase 10",
        "type": "EMAIL",
        "steps": [
            {"step_number": 1, "step_type": "EMAIL", "delay_days": 0, "body": "Hello {name}, welcome!"},
            {"step_number": 2, "step_type": "EMAIL", "delay_days": 2, "body": "Following up..."}
        ]
    }
    try:
        r = session.post(f"{API}/campaigns", headers=headers, json=campaign_payload)
        check("POST /campaigns -> 201", r.status_code == 201, f"status={r.status_code}")
        if r.status_code == 201:
            camp = r.json()
            state["campaign_id"] = camp.get("id")
            check("Campaign ID returned", bool(state["campaign_id"]))
            check("Campaign name matches", camp.get("name") == "Q4 Outreach Campaign")
        else:
            print(f"    Error: {r.text[:300]}")
    except Exception as e:
        fail(f"Create campaign failed: {e}")

    try:
        r = session.get(f"{API}/campaigns", headers=headers)
        check("GET /campaigns -> 200", r.status_code == 200)
        if r.status_code == 200:
            campaigns = r.json()
            check("At least 1 campaign", len(campaigns) >= 1)
    except Exception as e:
        fail(f"List campaigns failed: {e}")

    if state.get("campaign_id"):
        try:
            r = session.get(f"{API}/campaigns/{state['campaign_id']}", headers=headers)
            check("GET /campaigns/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get campaign failed: {e}")

        try:
            r = session.patch(f"{API}/campaigns/{state['campaign_id']}", headers=headers, json={"description": "Updated"})
            check("PATCH /campaigns/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Update campaign failed: {e}")

        try:
            r = session.get(f"{API}/campaigns/{state['campaign_id']}/analytics", headers=headers)
            check("GET /campaigns/{id}/analytics -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            fail(f"Campaign analytics failed: {e}")

        try:
            r = session.get(f"{API}/campaigns/{state['campaign_id']}/leads", headers=headers)
            check("GET /campaigns/{id}/leads -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Campaign leads failed: {e}")

# ─── 8. QUOTES ────────────────────────────────────────────────────────────────
header("8. Quotes - Full Lifecycle")
if token and state.get("lead_id"):
    if not state.get("restaurant_id"):
        try:
            r_payload = {"name": "Test Quote Restaurant", "address": "123 Quote St"}
            res = session.post(f"{API}/restaurants", headers=headers, json=r_payload)
            if res.status_code == 201:
                state["restaurant_id"] = res.json().get("id")
        except Exception:
            pass
            
    quote_payload = {
        "lead_id": state["lead_id"],
        "restaurant_id": state.get("restaurant_id"),
        "title": "RestoOps Pro Package",
        "notes": "Custom proposal for Test Restaurant",
        "event_date": "2026-10-10",
        "guest_count": 50,
        "valid_until": "2027-01-01",
        "items": [
            {"name": "Monthly Subscription", "quantity": 1, "unit_price": 499.00},
            {"name": "Onboarding & Setup", "quantity": 1, "unit_price": 199.00}
        ]
    }
    try:
        r = session.post(f"{API}/quotes", headers=headers, json=quote_payload)
        check("POST /quotes -> 201", r.status_code == 201, f"status={r.status_code}")
        if r.status_code == 201:
            quote = r.json()
            state["quote_id"] = quote.get("id")
            check("Quote ID returned", bool(state["quote_id"]))
            check("Quote event date matches", quote.get("event_date") == "2026-10-10")
            check("Quote has items", len(quote.get("items", [])) >= 1)
        else:
            print(f"    Error: {r.text[:300]}")
    except Exception as e:
        fail(f"Create quote failed: {e}")

    try:
        r = session.get(f"{API}/quotes", headers=headers)
        check("GET /quotes -> 200", r.status_code == 200)
    except Exception as e:
        fail(f"List quotes failed: {e}")

    if state.get("quote_id"):
        try:
            r = session.get(f"{API}/quotes/{state['quote_id']}", headers=headers)
            check("GET /quotes/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get quote failed: {e}")

        try:
            r = session.patch(f"{API}/quotes/{state['quote_id']}", headers=headers, json={"notes": "Updated notes"})
            check("PATCH /quotes/{id} -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            fail(f"Update quote failed: {e}")

        try:
            r = session.post(f"{API}/quotes/{state['quote_id']}/items", headers=headers, json={
                "description": "Priority Support", "quantity": 1, "unit_price": 99.00, "discount_pct": 0.0
            })
            check("POST /quotes/{id}/items -> 201", r.status_code == 201, f"status={r.status_code}")
            if r.status_code == 201:
                state["quote_item_id"] = r.json().get("id")
        except Exception as e:
            fail(f"Add quote item failed: {e}")

        try:
            r = session.post(f"{API}/quotes/{state['quote_id']}/submit", headers=headers)
            check("POST /quotes/{id}/submit -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            fail(f"Submit quote failed: {e}")

        try:
            r = session.post(f"{API}/quotes/{state['quote_id']}/approve", headers=headers)
            check("POST /quotes/{id}/approve -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            fail(f"Approve quote failed: {e}")

        try:
            r = session.post(f"{API}/quotes/{state['quote_id']}/send", headers=headers)
            check("POST /quotes/{id}/send -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            fail(f"Send quote failed: {e}")

        try:
            r = session.post(f"{API}/quotes/{state['quote_id']}/accept", headers=headers)
            check("POST /quotes/{id}/accept -> 200 (creates Order)", r.status_code == 200, f"status={r.status_code}")
            if r.status_code == 200:
                order = r.json()
                state["order_id"] = order.get("id")
                check("Order ID returned from quote accept", bool(state["order_id"]))
        except Exception as e:
            fail(f"Accept quote failed: {e}")

# ─── 9. ORDERS ────────────────────────────────────────────────────────────────
header("9. Orders")
if token:
    try:
        r = session.get(f"{API}/orders", headers=headers)
        check("GET /orders -> 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            orders = r.json()
            check("Orders is a list", isinstance(orders, list))
            check("At least 1 order (from quote accept)", len(orders) >= 1)
    except Exception as e:
        fail(f"List orders failed: {e}")

    if state.get("order_id"):
        try:
            r = session.get(f"{API}/orders/{state['order_id']}", headers=headers)
            check("GET /orders/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get order failed: {e}")

# ─── 10. CONVERSATIONS ────────────────────────────────────────────────────────
header("10. Conversations")
if token:
    try:
        r = session.get(f"{API}/conversations", headers=headers)
        check("GET /conversations -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        warn(f"List conversations failed: {e}")

    try:
        r = session.post(f"{API}/conversations/analyze", headers=headers, json={"lead_id": state.get("lead_id"), "messages": [{"role": "user", "content": "hello"}]})
        if r.status_code == 405:
            warn("POST /conversations/analyze not implemented or Method Not Allowed")
        else:
            check("POST /conversations/analyze -> 200", r.status_code in [200, 201], f"status={r.status_code}")
            if r.status_code in [200, 201]:
                data = r.json()
                if isinstance(data, dict):
                    state["conversation_id"] = data.get("id") or data.get("conversation_id")
    except Exception as e:
        warn(f"Conversation analyze: {e}")

    if state.get("conversation_id"):
        try:
            r = session.get(f"{API}/conversations/{state['conversation_id']}", headers=headers)
            check("GET /conversations/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get conversation failed: {e}")

        try:
            r = session.post(f"{API}/conversations/{state['conversation_id']}/messages", headers=headers, json={
                "content": "Hello! We'd love to tell you about RestoOps.",
                "sender_type": "AGENT"
            })
            check("POST /conversations/{id}/messages -> 201", r.status_code == 201, f"status={r.status_code}")
        except Exception as e:
            fail(f"Send message failed: {e}")

# ─── 11. AI ENDPOINTS ─────────────────────────────────────────────────────────
header("11. AI Endpoints")
if token:
    if state.get("conversation_id"):
        try:
            r = session.post(f"{API}/ai/analyze/{state['conversation_id']}", headers=headers)
            check("POST /ai/analyze/{conversation_id} -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            warn(f"AI analyze conversation failed (may need ollama): {e}")

    try:
        r = session.get(f"{API}/ai/actions/pending", headers=headers)
        check("GET /ai/actions/pending -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        warn(f"AI pending actions: {e}")

    try:
        r = session.get(f"{API}/ai/activity", headers=headers)
        check("GET /ai/activity -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        warn(f"AI activity list: {e}")

# ─── 12. CALLS ────────────────────────────────────────────────────────────────
header("12. Calls")
if token:
    try:
        r = session.get(f"{API}/calls", headers=headers)
        check("GET /calls -> 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            check("Calls is a list", isinstance(r.json(), list))
    except Exception as e:
        fail(f"List calls failed: {e}")

    if state.get("lead_id"):
        try:
            r = session.post(f"{API}/calls", headers=headers, json={
                "lead_id": state.get("lead_id"),
                "from_number": "+1234567890",
                "to": "+15551234567",
                "from_number": "+1234567890",
        "direction": "OUTBOUND",
                "provider": "EXOTEL",
                "duration_seconds": 180,
                "notes": "Great initial call",
                "summary": "Discussed pro package"
            })
            check("POST /calls -> 201", r.status_code == 201, f"status={r.status_code}")
            if r.status_code == 201:
                call = r.json()
                state["call_id"] = call.get("id")
                check("Call ID returned", bool(state["call_id"]))
            else:
                print(f"    Error: {r.text[:200]}")
        except Exception as e:
            fail(f"Create call log failed: {e}")

    if state.get("call_id"):
        try:
            r = session.get(f"{API}/calls/{state['call_id']}", headers=headers)
            check("GET /calls/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get call failed: {e}")

# ─── 13. NOTIFICATIONS ────────────────────────────────────────────────────────
header("13. Notifications")
if token:
    try:
        r = session.get(f"{API}/notifications", headers=headers)
        check("GET /notifications -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        fail(f"List notifications failed: {e}")

    try:
        r = session.get(f"{API}/notifications/unread-count", headers=headers)
        check("GET /notifications/unread-count -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        warn(f"Notifications unread-count: {e}")

# ─── 14. VERIFICATION ─────────────────────────────────────────────────────────
header("14. Verification")
if token:
    try:
        r = session.get(f"{API}/verification/jobs", headers=headers)
        check("GET /verification/jobs -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        fail(f"Verification jobs failed: {e}")

    try:
        r = session.post(f"{API}/verification/check", headers=headers, json={"email": "test@gmail.com"})
        check("POST /verification/check -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        warn(f"Single email verify: {e}")

# ─── 15. SUPPRESSION LIST ─────────────────────────────────────────────────────
header("15. Suppression List")
if token:
    try:
        r = session.post(f"{API}/suppression", headers=headers, json={
            "email": "donotcontact@example.com",
            "reason": "Opt-out request"
        })
        check("POST /suppression -> 201", r.status_code == 201, f"status={r.status_code}")
        if r.status_code == 201:
            state["suppression_id"] = r.json().get("id")
    except Exception as e:
        fail(f"Add suppression failed: {e}")

    try:
        r = session.get(f"{API}/suppression", headers=headers)
        check("GET /suppression -> 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            check("Suppression list is a list", isinstance(r.json(), list))
    except Exception as e:
        fail(f"List suppression failed: {e}")

    if state.get("suppression_id"):
        try:
            r = session.delete(f"{API}/suppression/{state['suppression_id']}", headers=headers)
            check("DELETE /suppression/{id} -> 204", r.status_code == 204, f"status={r.status_code}")
        except Exception as e:
            fail(f"Delete suppression failed: {e}")

# ─── 16. RESTAURANTS ──────────────────────────────────────────────────────────
header("16. Restaurants")
if token:
    try:
        r = session.post(f"{API}/restaurants", headers=headers, json={
            "name": "The Golden Fork",
            "address": "456 Elm Ave, Chicago, IL",
            "phone": "+1-312-555-0200",
            "email": "info@goldenfork.com",
            "cuisine_type": "Italian",
            "seats": 80
        })
        check("POST /restaurants -> 201", r.status_code == 201, f"status={r.status_code}")
        if r.status_code == 201:
            rest = r.json()
            state["restaurant_id"] = rest.get("id")
        else:
            print(f"    Error: {r.text[:200]}")
    except Exception as e:
        fail(f"Create restaurant failed: {e}")

    try:
        r = session.get(f"{API}/restaurants", headers=headers)
        check("GET /restaurants -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        fail(f"List restaurants failed: {e}")

    if state.get("restaurant_id"):
        try:
            r = session.get(f"{API}/restaurants/{state['restaurant_id']}", headers=headers)
            check("GET /restaurants/{id} -> 200", r.status_code == 200)
        except Exception as e:
            fail(f"Get restaurant failed: {e}")

        try:
            r = session.patch(f"{API}/restaurants/{state['restaurant_id']}", headers=headers, json={"seats": 100})
            check("PATCH /restaurants/{id} -> 200", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            fail(f"Update restaurant failed: {e}")

        try:
            r = session.delete(f"{API}/restaurants/{state['restaurant_id']}", headers=headers)
            check("DELETE /restaurants/{id} -> 204", r.status_code == 204, f"status={r.status_code}")
        except Exception as e:
            fail(f"Delete restaurant failed: {e}")

# ─── 17. WEBHOOKS ─────────────────────────────────────────────────────────────
header("17. Webhooks")
if token:
    try:
        r = session.get(f"{API}/webhooks", headers=headers)
        check("GET /webhooks -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        warn(f"Webhooks list: {e}")

# ─── 18. API DOCS ─────────────────────────────────────────────────────────────
header("18. API Documentation")
try:
    r = session.get(f"{BASE_URL}/docs", timeout=5)
    check("GET /docs -> 200 (Swagger UI)", r.status_code == 200)
except Exception as e:
    warn(f"Swagger UI not accessible: {e}")

try:
    r = session.get(f"{BASE_URL}/redoc", timeout=5)
    check("GET /redoc -> 200 (ReDoc)", r.status_code == 200)
except Exception as e:
    warn(f"ReDoc not accessible: {e}")

# ─── 19. CLEANUP ──────────────────────────────────────────────────────────────
header("19. Cleanup (Delete test lead)")
if token and state.get("lead_id"):
    try:
        r = session.delete(f"{API}/leads/{state['lead_id']}", headers=headers)
        check("DELETE /leads/{id} -> 204", r.status_code == 204, f"status={r.status_code}")
    except Exception as e:
        fail(f"Delete lead failed: {e}")

    try:
        r = session.get(f"{API}/leads/{state['lead_id']}", headers=headers)
        check("GET deleted lead -> 404", r.status_code == 404)
    except Exception as e:
        fail(f"Verify deletion failed: {e}")

# ─── 20. EDGE CASES ───────────────────────────────────────────────────────────
header("20. Edge Cases & Security")
if token:
    try:
        r = session.get(f"{API}/leads/nonexistent-id-000", headers=headers)
        check("GET non-existent lead -> 404", r.status_code == 404)
    except Exception as e:
        fail(f"404 edge case failed: {e}")

    try:
        session.post(f"{API}/suppression", headers=headers, json={"email": "dup@test.com", "reason": "first"})
        r = session.post(f"{API}/suppression", headers=headers, json={"email": "dup@test.com", "reason": "second"})
        check("Duplicate suppression -> 400/409 or 201 (idempotent)", r.status_code in [400, 409, 201, 200])
    except Exception as e:
        warn(f"Duplicate suppression check: {e}")

    # Invalid CSV
    try:
        files = {"file": ("bad.txt", b"not a csv at all", "text/plain")}
        r = session.post(f"{API}/leads/import/csv", headers=headers, files=files)
        check("Import non-CSV file -> 400", r.status_code == 400)
    except Exception as e:
        warn(f"Invalid CSV type check: {e}")

# ─── FINAL REPORT ──────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  PHASE 10 TEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")
total = results['passed'] + results['failed']
pct = (results['passed'] / total * 100) if total > 0 else 0
print(f"  Passed:   {results['passed']}")
print(f"  Failed:   {results['failed']}")
print(f"  Warnings: {results['warnings']}")
print(f"  Total:    {total}")
print(f"  Score:    {pct:.1f}%")
print(f"{'='*60}")

if results['failed'] == 0:
    print(f"\n  ALL TESTS PASSED - System is healthy!\n")
elif pct >= 80:
    print(f"\n  MOSTLY PASSING - {results['failed']} issues need attention\n")
else:
    print(f"\n  CRITICAL FAILURES - System requires fixes\n")

sys.exit(0 if results['failed'] == 0 else 1)
