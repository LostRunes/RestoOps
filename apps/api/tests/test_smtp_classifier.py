"""
Phase 3 — Verification Engine Tests
Tests classify_smtp_response logic and the 452 false-positive fix.
No network calls — pure unit tests.
"""
import pytest
from app.services.verification.smtp_prober import classify_smtp_response, is_definitive_invalid


class TestIsDefinitiveInvalid:
    def test_user_unknown(self):
        assert is_definitive_invalid("550 user unknown") is True

    def test_no_such_user(self):
        assert is_definitive_invalid("No such user here") is True

    def test_mailbox_not_found(self):
        assert is_definitive_invalid("550 Mailbox not found") is True

    def test_ambiguous_rejection(self):
        # Ambiguous — no definitive phrase
        assert is_definitive_invalid("550 Rejected") is False

    def test_empty_string(self):
        assert is_definitive_invalid("") is False


class TestClassifySmtpResponse:
    # ── Code 250 passthrough ────────────────────────────────────────────────
    def test_250_returns_none(self):
        status, reason = classify_smtp_response(250, "OK", "unknown")
        assert status is None
        assert reason is None

    # ── 452 fix: FortiMail sender domain error must NOT be inbox_full ───────
    def test_452_sender_domain_error_is_not_inbox_full(self):
        """THE critical regression test for the FortiMail false-positive bug."""
        msg = "452 Could not resolve sender domain bounceblitz.com"
        status, reason = classify_smtp_response(452, msg, "fortimail")
        # Must NOT be inbox_full — sender DNS error should fall through
        assert status != "inbox_full", (
            f"REGRESSION: 452 sender domain error incorrectly classified as '{status}'"
        )

    def test_452_without_sender_error_is_inbox_full(self):
        """452 with no sender domain error phrase = genuine quota issue."""
        status, reason = classify_smtp_response(452, "452 Too many recipients", "unknown")
        assert status == "inbox_full"
        assert reason == "mailbox_over_quota"

    def test_quota_exceeded_phrase_triggers_inbox_full(self):
        status, reason = classify_smtp_response(550, "Quota exceeded for mailbox", "unknown")
        assert status == "inbox_full"

    def test_mailbox_full_phrase_triggers_inbox_full(self):
        status, reason = classify_smtp_response(550, "Mailbox full", "unknown")
        assert status == "inbox_full"

    def test_over_quota_phrase_triggers_inbox_full(self):
        status, reason = classify_smtp_response(200, "over quota storage", "unknown")
        assert status == "inbox_full"

    def test_storage_limit_phrase_triggers_inbox_full(self):
        status, reason = classify_smtp_response(200, "storage limit reached", "unknown")
        assert status == "inbox_full"

    # ── Account disabled ────────────────────────────────────────────────────
    def test_disabled_account(self):
        status, reason = classify_smtp_response(550, "Account is disabled", "unknown")
        assert status == "disabled"
        assert reason == "account_disabled"

    def test_inactive_account(self):
        status, reason = classify_smtp_response(550, "User inactive", "unknown")
        assert status == "disabled"

    def test_suspended_account(self):
        status, reason = classify_smtp_response(550, "Account suspended", "unknown")
        assert status == "disabled"

    # ── 550 disambiguation ──────────────────────────────────────────────────
    def test_550_with_definitive_phrase_is_invalid(self):
        status, reason = classify_smtp_response(550, "550 User unknown", "unknown")
        assert status == "invalid"
        assert reason == "user_not_found"

    def test_550_ambiguous_non_gateway(self):
        status, reason = classify_smtp_response(550, "550 Rejected", "unknown")
        assert status == "unknown"
        assert reason == "smtp_550_ambiguous"

    def test_550_gateway_provider_is_dha(self):
        # mimecast IS in GATEWAY_PROVIDERS — bare 550 without definitive phrase → DHA unknown
        status, reason = classify_smtp_response(550, "550 Rejected", "mimecast")
        assert status == "unknown"
        assert "dha" in reason

    def test_550_google_ambiguous_not_dha(self):
        # Google is NOT in GATEWAY_PROVIDERS (returns clean SMTP, no DHA protection)
        # So bare 550 without definitive phrase → smtp_550_ambiguous (generic unknown)
        status, reason = classify_smtp_response(550, "550 Rejected", "google")
        assert status == "unknown"
        assert reason == "smtp_550_ambiguous"

    # ── 554 ─────────────────────────────────────────────────────────────────
    def test_554_definitive_is_invalid(self):
        status, reason = classify_smtp_response(554, "554 No such user here", "unknown")
        assert status == "invalid"

    def test_554_ambiguous_is_unknown(self):
        status, reason = classify_smtp_response(554, "554 Transaction failed", "unknown")
        assert status == "unknown"
        assert reason == "smtp_554_connection_rejected"

    # ── 553 ─────────────────────────────────────────────────────────────────
    def test_553_ambiguous_is_unknown(self):
        status, reason = classify_smtp_response(553, "553 Bad mailbox name", "unknown")
        assert status == "unknown"
        assert reason == "smtp_553_ambiguous"

    # ── 551 ─────────────────────────────────────────────────────────────────
    def test_551_not_local(self):
        status, reason = classify_smtp_response(551, "551 User not local", "unknown")
        assert status == "unknown"
        assert reason == "smtp_551_not_local"

    # ── Soft-fail codes ──────────────────────────────────────────────────────
    def test_421_soft_fail(self):
        status, reason = classify_smtp_response(421, "Service unavailable", "unknown")
        assert status == "unknown"
        assert "soft_fail" in reason

    def test_450_soft_fail(self):
        status, reason = classify_smtp_response(450, "Mailbox busy", "unknown")
        assert status == "unknown"

    def test_451_soft_fail(self):
        status, reason = classify_smtp_response(451, "Try again later", "unknown")
        assert status == "unknown"

    def test_503_soft_fail(self):
        status, reason = classify_smtp_response(503, "Bad sequence", "unknown")
        assert status == "unknown"

    # ── Timeout / no connection ──────────────────────────────────────────────
    def test_none_code_is_timeout(self):
        status, reason = classify_smtp_response(None, "Connection timed out", "unknown")
        assert status == "unknown"
        assert reason == "smtp_timeout"

    # ── Unknown code with definitive phrase ──────────────────────────────────
    def test_unknown_code_with_definitive_phrase(self):
        status, reason = classify_smtp_response(599, "No such user here", "unknown")
        assert status == "invalid"
        assert reason == "user_not_found"

    def test_unknown_code_without_phrase(self):
        status, reason = classify_smtp_response(599, "Generic rejection", "unknown")
        assert status == "unknown"
        assert reason == "smtp_rejected_599"
