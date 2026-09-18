"""
Database Connectivity & Schema Tests
Requires PostgreSQL to be running.

Uses psycopg2 (sync) for schema inspection to avoid asyncpg pool conflicts
with pytest-asyncio. The actual application code uses asyncpg correctly —
these tests are only querying catalog tables to verify schema integrity.
"""
import psycopg2
import pytest

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "dbname": "restoops_db",
    "user": "restoops_user",
    "password": "restoops_password_dev_123",
    "connect_timeout": 5,
}

EXPECTED_TABLES = [
    # Phase 1/2 core
    "organizations", "users", "roles", "restaurants", "refresh_tokens",
    # Phase 3
    "leads", "lead_contacts", "lead_verifications", "lead_activities",
    "suppression_list",
    # Phase 4
    "campaigns", "campaign_steps", "campaign_leads",
    "conversations", "messages",
    # Phase 5
    "ai_runs", "ai_actions", "audit_logs",
]


@pytest.fixture(scope="module")
def pg():
    """Module-scoped psycopg2 connection — one connection for all DB tests."""
    conn = psycopg2.connect(**DB_PARAMS)
    conn.autocommit = True
    yield conn
    conn.close()


def _query(pg, sql, params=None):
    cur = pg.cursor()
    cur.execute(sql, params)
    return [row for row in cur.fetchall()]


def test_database_connection(pg):
    """Verify PostgreSQL is reachable."""
    result = _query(pg, "SELECT 1")
    assert result[0][0] == 1


def test_all_expected_tables_exist(pg):
    """Verify all expected tables have been created by migrations."""
    rows = _query(pg, "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    existing = {row[0] for row in rows}
    missing = [t for t in EXPECTED_TABLES if t not in existing]
    assert not missing, f"Missing tables: {missing}"


def test_ai_runs_table_columns(pg):
    """Validate ai_runs has all required columns."""
    rows = _query(pg,
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'ai_runs'"
    )
    columns = {row[0] for row in rows}
    required = {
        "id", "organization_id", "agent", "model",
        "conversation_id", "lead_id",
        "input", "output", "structured_output",
        "latency_ms", "tokens_used", "status", "error",
        "created_at",
    }
    missing = required - columns
    assert not missing, f"ai_runs missing columns: {missing}"


def test_ai_actions_table_columns(pg):
    """Validate ai_actions has all required columns."""
    rows = _query(pg,
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'ai_actions'"
    )
    columns = {row[0] for row in rows}
    required = {
        "id", "ai_run_id", "organization_id",
        "tool", "arguments", "result", "status",
        "approved_by", "approved_at", "executed_at",
        "rejection_reason", "created_at",
    }
    missing = required - columns
    assert not missing, f"ai_actions missing columns: {missing}"


def test_audit_logs_table_columns(pg):
    """Validate audit_logs has all required columns."""
    rows = _query(pg,
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'audit_logs'"
    )
    columns = {row[0] for row in rows}
    required = {
        "id", "organization_id", "user_id",
        "action", "entity_type", "entity_id",
        "old_value", "new_value",
        "ip_address", "user_agent", "created_at",
    }
    missing = required - columns
    assert not missing, f"audit_logs missing columns: {missing}"


def test_alembic_migrations_current(pg):
    """Verify the latest migration (Phase 5) has been applied."""
    rows = _query(pg, "SELECT version_num FROM alembic_version")
    assert rows, "No alembic migration version found"
    version = rows[0][0]
    assert version == "bcc92846d4c6", (
        f"Unexpected alembic version: {version}. "
        f"Expected bcc92846d4c6 (Phase 5). Run: alembic upgrade head"
    )


def test_ai_runs_indexes_exist(pg):
    """Verify important indexes on ai_runs were created."""
    rows = _query(pg,
        "SELECT indexname FROM pg_indexes WHERE tablename = 'ai_runs'"
    )
    index_names = {row[0] for row in rows}
    # At minimum organization_id and id should be indexed
    assert any("organization_id" in n for n in index_names), \
        f"No organization_id index on ai_runs. Found: {index_names}"


def test_ai_actions_status_index_exists(pg):
    """Verify the status index on ai_actions (used for listing pending actions)."""
    rows = _query(pg,
        "SELECT indexname FROM pg_indexes WHERE tablename = 'ai_actions'"
    )
    index_names = {row[0] for row in rows}
    assert any("status" in n for n in index_names), \
        f"No status index on ai_actions. Found: {index_names}"
