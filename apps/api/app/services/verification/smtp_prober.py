"""
SMTP probing engine — ported from BounceBlitz verifier.py.
Handles catch-all detection, mailbox existence probing, and
DHA-aware classification via Options A+B.
"""
import smtplib
import time
import random
from app.services.verification.constants import (
    DEFINITIVE_INVALID_PHRASES,
    GATEWAY_PROVIDERS,
)
from app.services.verification.dns_checker import detect_provider


def is_definitive_invalid(msg_str: str) -> bool:
    """
    Returns True only when the SMTP response contains an unambiguous
    mailbox non-existence phrase (Option A conservative matching).
    """
    msg_lower = msg_str.lower()
    return any(phrase in msg_lower for phrase in DEFINITIVE_INVALID_PHRASES)


def classify_smtp_response(
    code: int | None, msg_str: str, provider: str
) -> tuple[str, str]:
    """
    Options A + B combined SMTP response classifier (ported from BounceBlitz).

    Returns (status, reason). Returns (None, None) for code 250 — caller handles safe/role.
    """
    if code == 250:
        return None, None

    msg_lower = msg_str.lower()

    # Inbox full / quota exceeded
    is_quota_phrase = (
        "quota exceeded" in msg_lower
        or "mailbox full" in msg_lower
        or "over quota" in msg_lower
        or "storage limit" in msg_lower
    )
    is_sender_error = "resolve sender domain" in msg_lower or "sender address rejected" in msg_lower
    
    if is_quota_phrase or (code == 452 and not is_sender_error):
        return "inbox_full", "mailbox_over_quota"

    # Account disabled / deactivated
    if (
        "disabled" in msg_lower
        or "inactive" in msg_lower
        or "suspended" in msg_lower
    ):
        return "disabled", "account_disabled"

    definitive = is_definitive_invalid(msg_str)

    # 550: Most common ambiguous rejection code
    if code == 550:
        if definitive:
            return "invalid", "user_not_found"
        if provider in GATEWAY_PROVIDERS:
            return "unknown", f"provider_dha_{provider}"
        return "unknown", "smtp_550_ambiguous"

    # 554: Transaction/connection-level rejection (usually NOT mailbox non-existence)
    if code == 554:
        if definitive:
            return "invalid", "user_not_found"
        return "unknown", "smtp_554_connection_rejected"

    # 553: Mailbox name not allowed
    if code == 553:
        if definitive:
            return "invalid", "user_not_found"
        return "unknown", "smtp_553_ambiguous"

    # 551: User not local
    if code == 551:
        return "unknown", "smtp_551_not_local"

    # Soft-fail / temporary deferral codes
    if code in [421, 450, 451, 503]:
        return "unknown", f"smtp_soft_fail_{code}"

    # Connection/timeout failure
    if code is None:
        return "unknown", "smtp_timeout"

    # Any other non-250 with definitive phrase
    if definitive:
        return "invalid", "user_not_found"

    return "unknown", f"smtp_rejected_{code}"


def smtp_probe_mx(
    mx_host: str, email: str, domain: str, is_role: bool
) -> tuple[str, str]:
    """
    Run catch-all detection + mailbox verification against a specific MX host.
    Returns (status, reason).
    """
    provider = detect_provider(mx_host)

    # ── Catch-all detection: probe guaranteed-nonexistent address ────────────
    catch_all = False
    try:
        server = smtplib.SMTP(timeout=8)
        try:
            server.connect(mx_host)
            server.helo("bounceblitz.com")
            server.mail("probe@bounceblitz.com")
            code, _ = server.rcpt(f"nonexistent_probe_xr7k29@{domain}")
            if code == 250:
                catch_all = True
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except Exception:
        pass

    if catch_all:
        return ("role", "catch_all_role") if is_role else ("catch_all", "domain_accepts_all")

    # ── Mailbox existence probe with one soft-fail retry ─────────────────────
    def _probe() -> tuple[int | None, str]:
        try:
            server = smtplib.SMTP(timeout=8)
            try:
                server.connect(mx_host)
                server.helo("bounceblitz.com")
                server.mail("verifier@bounceblitz.com")
                code, msg = server.rcpt(email)
                return code, str(msg)
            finally:
                try:
                    server.quit()
                except Exception:
                    pass
        except Exception as exc:
            return None, str(exc)

    code, msg_str = _probe()

    # Retry once on soft-fail codes
    if code in [421, 450, 451, 452, 503]:
        time.sleep(2.0 + random.uniform(0.5, 2.0))
        code, msg_str = _probe()

    if code == 250:
        return ("role", "role_account") if is_role else ("safe", "mailbox_exists")

    return classify_smtp_response(code, msg_str, provider)
