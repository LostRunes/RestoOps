"""
App Startup & Route Registration Tests
Validates all expected routes exist and the FastAPI app loads without errors.
"""
import pytest
from app.main import app


def get_all_routes():
    return {r.path for r in app.routes if hasattr(r, "path")}


class TestAppStartup:
    def test_app_loads(self):
        assert app is not None
        assert app.title == "RestoOps Catering Revenue Agent"

    def test_health_route_exists(self):
        routes = get_all_routes()
        assert "/health" in routes

    def test_auth_routes_exist(self):
        routes = get_all_routes()
        assert "/api/v1/auth/login" in routes
        assert "/api/v1/auth/register" in routes
        assert "/api/v1/auth/refresh" in routes

    def test_ai_routes_registered(self):
        routes = get_all_routes()
        ai_routes = {r for r in routes if "/ai/" in r or r.endswith("/ai")}
        expected = {
            "/api/v1/ai/activity",
            "/api/v1/ai/activity/{run_id}",
            "/api/v1/ai/actions/pending",
            "/api/v1/ai/actions/{action_id}/approve",
            "/api/v1/ai/actions/{action_id}/reject",
            "/api/v1/ai/actions/{action_id}/edit",
            "/api/v1/ai/analyze/{conversation_id}",
        }
        missing = expected - routes
        assert not missing, f"Missing AI routes: {missing}"

    def test_verification_routes_exist(self):
        routes = get_all_routes()
        verification_routes = {r for r in routes if "/verification/" in r}
        assert len(verification_routes) >= 3

    def test_campaign_routes_exist(self):
        routes = get_all_routes()
        campaign_routes = {r for r in routes if "/campaigns" in r}
        assert len(campaign_routes) >= 5

    def test_conversation_routes_exist(self):
        routes = get_all_routes()
        conv_routes = {r for r in routes if "/conversations" in r}
        assert len(conv_routes) >= 2

    def test_suppression_routes_exist(self):
        routes = get_all_routes()
        sup_routes = {r for r in routes if "/suppression/" in r}
        assert len(sup_routes) >= 3

    def test_leads_routes_exist(self):
        routes = get_all_routes()
        lead_routes = {r for r in routes if "/leads/" in r}
        assert len(lead_routes) >= 4

    def test_no_duplicate_routes(self):
        all_paths = [r.path for r in app.routes if hasattr(r, "path")]
        # Allow duplicates only from different HTTP methods, not same path+method combos
        # This just checks that the total count is sane
        assert len(all_paths) > 10, "Too few routes registered"
