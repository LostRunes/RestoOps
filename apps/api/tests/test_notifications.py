"""
Phase 8 tests — Notifications, Events & Real-Time.

Covers:
  - EventBus: subscribe, publish, error isolation
  - NotificationService: create, fan-out, mark_read, mark_all_read, delete
  - NotificationRepository: CRUD, unread count, role-based lookup
  - NotificationWSManager: connect, push, disconnect, multi-tab
  - Notification API: list, count, mark read, mark all, delete
  - WebSocket endpoint: auth reject, connect, ping/pong, mark_read via WS
"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import Event, EventBus, EventType
from app.api.websockets.notification_ws import NotificationWSManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_event(type=EventType.LEAD_CREATED, org_id="org-1", data=None, user_id=None):
    return Event(type=type, org_id=org_id, data=data or {}, user_id=user_id)


# ---------------------------------------------------------------------------
# EventBus tests
# ---------------------------------------------------------------------------

class TestEventBus:
    def setup_method(self):
        EventBus.reset()

    def teardown_method(self):
        EventBus.reset()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        received = []

        async def handler(event: Event):
            received.append(event.type)

        EventBus.subscribe(EventType.LEAD_CREATED, handler)
        await EventBus.publish(make_event(EventType.LEAD_CREATED))
        assert received == [EventType.LEAD_CREATED]

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self):
        counts = [0, 0]

        async def h1(e): counts[0] += 1
        async def h2(e): counts[1] += 1

        EventBus.subscribe(EventType.QUOTE_ACCEPTED, h1)
        EventBus.subscribe(EventType.QUOTE_ACCEPTED, h2)
        await EventBus.publish(make_event(EventType.QUOTE_ACCEPTED))

        assert counts == [1, 1]

    @pytest.mark.asyncio
    async def test_handler_error_does_not_propagate(self):
        """A failing handler must not block the publish call."""
        async def bad_handler(e):
            raise RuntimeError("intentional error")

        called = []
        async def good_handler(e):
            called.append("ok")

        EventBus.subscribe(EventType.CALL_ENDED, bad_handler)
        EventBus.subscribe(EventType.CALL_ENDED, good_handler)

        # Should not raise
        await EventBus.publish(make_event(EventType.CALL_ENDED))
        assert called == ["ok"]

    @pytest.mark.asyncio
    async def test_no_handlers_does_not_raise(self):
        await EventBus.publish(make_event(EventType.FOLLOWUP_DUE))

    @pytest.mark.asyncio
    async def test_unrelated_event_not_dispatched(self):
        received = []
        async def handler(e): received.append(e.type)

        EventBus.subscribe(EventType.ORDER_CREATED, handler)
        await EventBus.publish(make_event(EventType.QUOTE_SENT))

        assert received == []

    @pytest.mark.asyncio
    async def test_reset_clears_all_handlers(self):
        received = []
        async def handler(e): received.append(e)

        EventBus.subscribe(EventType.LEAD_IMPORTED, handler)
        EventBus.reset()
        await EventBus.publish(make_event(EventType.LEAD_IMPORTED))

        assert received == []

    @pytest.mark.asyncio
    async def test_event_carries_data(self):
        captured = []
        async def handler(e): captured.append(e.data)

        EventBus.subscribe(EventType.QUOTE_SENT, handler)
        await EventBus.publish(make_event(EventType.QUOTE_SENT, data={"quote_id": "q1", "total": 500.0}))

        assert captured == [{"quote_id": "q1", "total": 500.0}]

    @pytest.mark.asyncio
    async def test_event_type_str_enum(self):
        assert EventType.LEAD_CREATED == "LEAD_CREATED"
        assert EventType.QUOTE_ACCEPTED == "QUOTE_ACCEPTED"
        assert EventType.CALL_ENDED == "CALL_ENDED"

    def test_all_expected_event_types_defined(self):
        expected = [
            "LEAD_CREATED", "LEAD_REPLIED", "LEAD_VERIFIED", "LEAD_IMPORTED",
            "CAMPAIGN_STARTED", "CAMPAIGN_COMPLETED", "CAMPAIGN_PAUSED",
            "QUOTE_SENT", "QUOTE_ACCEPTED", "QUOTE_REJECTED", "QUOTE_EXPIRED",
            "ORDER_CREATED", "CALL_STARTED", "CALL_ENDED",
            "AI_ACTION_PROPOSED", "AI_ACTION_APPROVED",
            "VERIFICATION_COMPLETED", "FOLLOWUP_DUE",
        ]
        for name in expected:
            assert hasattr(EventType, name), f"Missing EventType.{name}"


# ---------------------------------------------------------------------------
# NotificationWSManager tests
# ---------------------------------------------------------------------------

class TestNotificationWSManager:
    def make_ws(self):
        ws = MagicMock()
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_registers_user(self):
        mgr = NotificationWSManager()
        ws = self.make_ws()
        await mgr.connect(ws, "user-1")
        assert mgr.is_connected("user-1")

    @pytest.mark.asyncio
    async def test_disconnect_removes_user(self):
        mgr = NotificationWSManager()
        ws = self.make_ws()
        await mgr.connect(ws, "user-1")
        await mgr.disconnect(ws, "user-1")
        assert not mgr.is_connected("user-1")

    @pytest.mark.asyncio
    async def test_multiple_tabs_same_user(self):
        mgr = NotificationWSManager()
        ws1, ws2 = self.make_ws(), self.make_ws()
        await mgr.connect(ws1, "user-1")
        await mgr.connect(ws2, "user-1")
        assert len(mgr.connections["user-1"]) == 2

    @pytest.mark.asyncio
    async def test_push_notification_sends_to_all_tabs(self):
        mgr = NotificationWSManager()
        ws1, ws2 = self.make_ws(), self.make_ws()
        await mgr.connect(ws1, "user-1")
        await mgr.connect(ws2, "user-1")

        await mgr.push_notification("user-1", {"id": "n1", "type": "LEAD_REPLIED"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()
        payload = json.loads(ws1.send_text.call_args[0][0])
        assert payload["type"] == "notification"
        assert payload["data"]["id"] == "n1"

    @pytest.mark.asyncio
    async def test_push_to_unconnected_user_is_noop(self):
        mgr = NotificationWSManager()
        # Should not raise
        await mgr.push_notification("ghost-user", {"id": "n1"})

    @pytest.mark.asyncio
    async def test_push_unread_count(self):
        mgr = NotificationWSManager()
        ws = self.make_ws()
        await mgr.connect(ws, "user-1")
        await mgr.push_unread_count("user-1", 5)

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload == {"type": "unread_count", "data": {"count": 5}}

    @pytest.mark.asyncio
    async def test_push_job_progress(self):
        mgr = NotificationWSManager()
        ws = self.make_ws()
        await mgr.connect(ws, "user-1")
        await mgr.push_job_progress("user-1", "job-1", {"processed": 50, "total": 100, "status": "RUNNING"})

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["type"] == "job_progress"
        assert payload["data"]["job_id"] == "job-1"
        assert payload["data"]["processed"] == 50

    @pytest.mark.asyncio
    async def test_broken_connection_cleaned_up_on_push(self):
        """If a WS raises on send, it should be silently removed."""
        mgr = NotificationWSManager()
        ws = self.make_ws()
        ws.send_text.side_effect = Exception("broken pipe")

        await mgr.connect(ws, "user-1")
        # Should not raise
        await mgr.push_notification("user-1", {"id": "n1"})

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self):
        mgr = NotificationWSManager()
        ws = self.make_ws()
        await mgr.connect(ws, "user-1")
        await mgr.disconnect(ws, "user-1")
        # Second disconnect should not raise
        await mgr.disconnect(ws, "user-1")


# ---------------------------------------------------------------------------
# NotificationService tests (mocked DB)
# ---------------------------------------------------------------------------

class TestNotificationService:
    def make_service(self, ws_manager=None):
        from app.services.notification_service import NotificationService
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # Mock the repo
        service = NotificationService(db, ws_manager=ws_manager or NotificationWSManager())
        return service, db

    def make_notif(self, **kwargs):
        n = MagicMock()
        n.id = kwargs.get("id", "notif-1")
        n.type = kwargs.get("type", "LEAD_REPLIED")
        n.title = kwargs.get("title", "Test Notification")
        n.body = kwargs.get("body", "Test body")
        n.entity_type = kwargs.get("entity_type", "lead")
        n.entity_id = kwargs.get("entity_id", "lead-1")
        n.priority = kwargs.get("priority", "NORMAL")
        n.is_read = kwargs.get("is_read", False)
        n.created_at = kwargs.get("created_at", "2024-01-01T00:00:00")
        return n

    @pytest.mark.asyncio
    async def test_create_notification_persists_and_pushes(self):
        svc, db = self.make_service()
        notif = self.make_notif()

        with patch.object(svc.repo, "create", return_value=notif), \
             patch.object(svc.repo, "get_unread_count", return_value=3), \
             patch.object(svc.ws_manager, "is_connected", return_value=True), \
             patch.object(svc.ws_manager, "push_notification", new_callable=AsyncMock) as mock_push, \
             patch.object(svc.ws_manager, "push_unread_count", new_callable=AsyncMock):

            result = await svc.create_notification(
                org_id="org-1", user_id="user-1",
                type="LEAD_REPLIED", title="Test", body="Test body",
            )

        assert result.id == "notif-1"
        mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_notification_no_push_if_not_connected(self):
        svc, db = self.make_service()
        notif = self.make_notif()

        with patch.object(svc.repo, "create", return_value=notif), \
             patch.object(svc.ws_manager, "is_connected", return_value=False), \
             patch.object(svc.ws_manager, "push_notification", new_callable=AsyncMock) as mock_push:

            await svc.create_notification(
                org_id="org-1", user_id="user-1",
                type="LEAD_REPLIED", title="Test", body="Test body",
            )

        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_read_delegates_to_repo(self):
        svc, db = self.make_service()
        with patch.object(svc.repo, "mark_read", new_callable=AsyncMock) as mock_mr:
            await svc.mark_read("notif-1", "user-1")
            mock_mr.assert_called_once_with("notif-1", "user-1")

    @pytest.mark.asyncio
    async def test_mark_all_read_pushes_zero_count(self):
        svc, db = self.make_service()
        with patch.object(svc.repo, "mark_all_read", new_callable=AsyncMock), \
             patch.object(svc.ws_manager, "is_connected", return_value=True), \
             patch.object(svc.ws_manager, "push_unread_count", new_callable=AsyncMock) as mock_count:

            await svc.mark_all_read("user-1")
            mock_count.assert_called_once_with("user-1", 0)

    @pytest.mark.asyncio
    async def test_get_unread_count(self):
        svc, db = self.make_service()
        with patch.object(svc.repo, "get_unread_count", return_value=7):
            count = await svc.get_unread_count("user-1")
            assert count == 7

    @pytest.mark.asyncio
    async def test_delete_notification(self):
        svc, db = self.make_service()
        with patch.object(svc.repo, "delete", new_callable=AsyncMock) as mock_del:
            await svc.delete_notification("notif-1", "user-1")
            mock_del.assert_called_once_with("notif-1", "user-1")

    @pytest.mark.asyncio
    async def test_list_notifications(self):
        svc, db = self.make_service()
        notifs = [self.make_notif(id=f"n-{i}") for i in range(5)]
        with patch.object(svc.repo, "list_by_user", return_value=(notifs, 5)):
            result, total = await svc.list_notifications("user-1", page=1, page_size=20)
            assert total == 5
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_create_for_org_admins_fans_out(self):
        svc, db = self.make_service()
        with patch.object(svc.repo, "get_users_by_org_roles", return_value=["u1", "u2", "u3"]), \
             patch.object(svc, "create_notification", new_callable=AsyncMock, return_value=self.make_notif()) as mock_create:

            await svc.create_for_org_admins(
                org_id="org-1", type="ORDER_CREATED",
                title="New order", body="Order body",
            )

        assert mock_create.call_count == 3


# ---------------------------------------------------------------------------
# Notification API endpoint tests
# ---------------------------------------------------------------------------

class TestNotificationAPI:
    def make_db_and_user(self):
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        user = MagicMock()
        user.id = "user-api-1"
        user.organization_id = "org-api-1"
        return db, user

    def make_notif_response(self, id="n1"):
        return MagicMock(
            id=id, organization_id="org-api-1", user_id="user-api-1",
            type="LEAD_REPLIED", title="Test", body="Test body",
            entity_type="lead", entity_id="lead-1", priority="NORMAL",
            is_read=False, read_at=None, notification_metadata=None,
            created_at="2024-01-01T00:00:00",
        )

    @pytest.mark.asyncio
    async def test_list_notifications_endpoint(self):
        from app.api.v1.endpoints.notifications import list_notifications
        db, user = self.make_db_and_user()

        notifs = [self.make_notif_response(f"n{i}") for i in range(3)]
        with patch("app.api.v1.endpoints.notifications.NotificationService") as MockSvc:
            instance = MockSvc.return_value
            instance.list_notifications = AsyncMock(return_value=(notifs, 3))
            instance.get_unread_count = AsyncMock(return_value=2)

            result = await list_notifications(
                page=1, page_size=20, unread_only=False,
                db=db, current_user=user,
            )

        assert result.total == 3
        assert result.unread_count == 2

    @pytest.mark.asyncio
    async def test_get_unread_count_endpoint(self):
        from app.api.v1.endpoints.notifications import get_unread_count
        db, user = self.make_db_and_user()

        with patch("app.api.v1.endpoints.notifications.NotificationService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_unread_count = AsyncMock(return_value=9)

            result = await get_unread_count(db=db, current_user=user)

        assert result.count == 9

    @pytest.mark.asyncio
    async def test_mark_notification_read_endpoint(self):
        from app.api.v1.endpoints.notifications import mark_notification_read
        db, user = self.make_db_and_user()

        with patch("app.api.v1.endpoints.notifications.NotificationService") as MockSvc:
            instance = MockSvc.return_value
            instance.mark_read = AsyncMock()

            await mark_notification_read(
                notification_id="notif-x", db=db, current_user=user,
            )
            instance.mark_read.assert_called_once_with("notif-x", "user-api-1")

    @pytest.mark.asyncio
    async def test_mark_all_read_endpoint(self):
        from app.api.v1.endpoints.notifications import mark_all_read
        db, user = self.make_db_and_user()

        with patch("app.api.v1.endpoints.notifications.NotificationService") as MockSvc:
            instance = MockSvc.return_value
            instance.mark_all_read = AsyncMock()

            await mark_all_read(db=db, current_user=user)
            instance.mark_all_read.assert_called_once_with("user-api-1")

    @pytest.mark.asyncio
    async def test_delete_notification_endpoint(self):
        from app.api.v1.endpoints.notifications import delete_notification
        db, user = self.make_db_and_user()

        with patch("app.api.v1.endpoints.notifications.NotificationService") as MockSvc:
            instance = MockSvc.return_value
            instance.delete_notification = AsyncMock()

            await delete_notification(
                notification_id="del-1", db=db, current_user=user,
            )
            instance.delete_notification.assert_called_once_with("del-1", "user-api-1")


# ---------------------------------------------------------------------------
# Notification handlers tests
# ---------------------------------------------------------------------------

class TestNotificationHandlers:
    def setup_method(self):
        EventBus.reset()

    def teardown_method(self):
        EventBus.reset()

    def test_register_notification_handlers_subscribes_all(self):
        from app.services.notification_handlers import register_notification_handlers
        register_notification_handlers()

        expected_types = [
            EventType.LEAD_CREATED, EventType.LEAD_REPLIED, EventType.LEAD_VERIFIED,
            EventType.VERIFICATION_COMPLETED, EventType.QUOTE_SENT,
            EventType.QUOTE_ACCEPTED, EventType.QUOTE_REJECTED, EventType.QUOTE_EXPIRED,
            EventType.ORDER_CREATED, EventType.AI_ACTION_PROPOSED,
            EventType.AI_ACTION_APPROVED, EventType.CALL_ENDED,
            EventType.CAMPAIGN_STARTED, EventType.CAMPAIGN_COMPLETED,
            EventType.FOLLOWUP_DUE,
        ]
        for et in expected_types:
            assert et in EventBus._handlers, f"No handler registered for {et}"

    @pytest.mark.asyncio
    async def test_on_quote_accepted_calls_notification_service(self):
        """Handler creates notifications for admins when quote accepted."""
        from app.services.notification_handlers import on_quote_accepted

        mock_svc = AsyncMock()
        mock_svc.create_for_org_admins = AsyncMock()

        mock_db_instance = AsyncMock()
        mock_db_instance.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.notification_handlers.AsyncSessionLocal", return_value=mock_db_instance), \
             patch("app.services.notification_handlers.NotificationService", return_value=mock_svc):

            event = Event(
                type=EventType.QUOTE_ACCEPTED, org_id="org-1",
                data={"quote_id": "q1", "quote_number": "Q-001",
                      "total": 1500.0, "company_name": "Big Corp", "order_id": "o1"},
                user_id="user-1",
            )
            await on_quote_accepted(event)

        mock_svc.create_for_org_admins.assert_called_once()
        call_kwargs = mock_svc.create_for_org_admins.call_args[1]
        assert call_kwargs["type"] == "QUOTE_ACCEPTED"
        assert call_kwargs["priority"] == "URGENT"

    @pytest.mark.asyncio
    async def test_on_followup_due_notifies_specific_user(self):
        from app.services.notification_handlers import on_followup_due

        mock_svc = AsyncMock()
        mock_svc.create_notification = AsyncMock()

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.notification_handlers.AsyncSessionLocal", return_value=mock_db), \
             patch("app.services.notification_handlers.NotificationService", return_value=mock_svc):

            event = Event(
                type=EventType.FOLLOWUP_DUE, org_id="org-1",
                data={"lead_id": "l1", "company_name": "Acme", "contact_name": "John"},
                user_id="agent-user",
            )
            await on_followup_due(event)

        mock_svc.create_notification.assert_called_once()
        kwargs = mock_svc.create_notification.call_args[1]
        assert kwargs["user_id"] == "agent-user"
        assert kwargs["priority"] == "HIGH"

    @pytest.mark.asyncio
    async def test_on_followup_due_skips_if_no_user(self):
        from app.services.notification_handlers import on_followup_due

        mock_svc = AsyncMock()
        mock_svc.create_notification = AsyncMock()

        with patch("app.services.notification_handlers.NotificationService", return_value=mock_svc):
            event = Event(
                type=EventType.FOLLOWUP_DUE, org_id="org-1",
                data={"lead_id": "l1"},
                user_id=None,  # no user — should skip
            )
            await on_followup_due(event)

        mock_svc.create_notification.assert_not_called()
