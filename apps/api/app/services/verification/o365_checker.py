"""
Microsoft O365 GetCredentialType API check — ported from BounceBlitz verifier.py.
Bypasses SMTP entirely for Microsoft-hosted domains.
"""
import json
import urllib.request
from app.services.verification.constants import O365_CREDENTIAL_URL


def check_o365_user(email: str) -> tuple[str | None, str | None]:
    """
    Query Microsoft's public GetCredentialType API to check if a mailbox exists.

    This bypasses SMTP entirely — no IP reputation required.

    IfExistsResult codes:
        0 → user exists (managed O365 account)
        1 → user does NOT exist
        5 → user exists (different/federated auth flow)
        6 → user exists (passkey/FIDO auth)
        others → ambiguous; fall back to SMTP

    ThrottleStatus 1 → Microsoft is rate-limiting; result unreliable.

    Returns:
        (None, None)           → mailbox confirmed to exist; caller assigns safe/role
        ("invalid", reason)    → mailbox does not exist
        ("unknown", reason)    → ambiguous/throttled/API error; fall back to SMTP
    """
    payload = json.dumps({"username": email}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        req = urllib.request.Request(
            O365_CREDENTIAL_URL, data=payload, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("ThrottleStatus") == 1:
            return "unknown", "o365_throttled"

        if_exists = data.get("IfExistsResult", -1)

        if if_exists in (0, 5, 6):
            return None, None  # Mailbox confirmed — caller decides safe/role
        elif if_exists == 1:
            return "invalid", "o365_user_not_found"
        else:
            # 2 = unknown (federated), others — can't determine; fall back to SMTP
            return "unknown", "o365_ambiguous_result"

    except Exception:
        return "unknown", "o365_api_error"
