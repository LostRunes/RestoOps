"""
BounceBlitz verification constants — ported directly from verifier.py.
All status definitions, scoring, provider signatures, and detection lists.
"""

# ─── Conservative invalid-detection phrases (Option A) ───────────────────────
# Only these unambiguous phrases cause an email to be marked INVALID.
# Many corporate servers return 550 as DHA protection — we must NOT blindly trust it.
DEFINITIVE_INVALID_PHRASES = [
    "user unknown",
    "no such user",
    "no such recipient",
    "no mailbox here",
    "mailbox not found",
    "user not found",
    "account does not exist",
    "account not found",
    "recipient not found",
    "invalid recipient",
    "bad destination mailbox",
    "address unknown",
    "unknown recipient",
    "no such mailbox",
    "no such address",
    "this address no longer accepts mail",
    "does not exist",
    "unrouteable address",
    "recipient address rejected: user unknown",
    "no such local user",
]

# ─── Provider MX signatures (Option B) ────────────────────────────────────────
# Maps MX hostname substrings → provider name for DHA-aware classification.
PROVIDER_MX_SIGNATURES = [
    (["protection.outlook.com", "mail.protection.outlook.com"], "microsoft"),
    (["aspmx.l.google.com", "googlemail.com", ".google.com", "aspmx"], "google"),
    (["mimecast.com"], "mimecast"),
    (["pphosted.com", "proofpoint.com", "ppe-hosted.com"], "proofpoint"),
    (["barracudanetworks.com"], "barracuda"),
    (["messagelabs.com"], "messagelabs"),
    (["sophos.com", "reflexion.net"], "sophos"),
    (["spamhero.com"], "spamhero"),
    (["mailchannels.net"], "mailchannels"),
]

# Providers that use security gateways / DHA protection.
# A bare 550 from them (without a definitive phrase) → unknown, NOT invalid.
GATEWAY_PROVIDERS = {
    "microsoft", "mimecast", "proofpoint", "barracuda",
    "messagelabs", "sophos", "spamhero", "mailchannels",
}

# ─── Disposable email domains ─────────────────────────────────────────────────
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
    "throwawaymail.com", "getairmail.com", "sharklasers.com", "yopmail.com",
    "trashmail.com", "dispostable.com", "maildrop.cc", "fakeinbox.com",
    "spam4.me", "binkmail.com", "bob.email", "discard.email",
    "mailnull.com", "tempr.email", "nwytg.com", "getnada.com",
}

# ─── Role-based local-parts ───────────────────────────────────────────────────
ROLE_BASED_PREFIXES = {
    "info", "support", "admin", "sales", "contact", "billing", "help", "jobs",
    "careers", "marketing", "office", "team", "enquiries", "hello", "privacy",
    "legal", "noreply", "no-reply", "postmaster", "abuse", "webmaster",
    "hr", "finance", "accounts", "press", "media", "events",
}

# ─── Spamtrap patterns ────────────────────────────────────────────────────────
SPAMTRAP_PATTERNS = [
    "spamtrap", "honeypot", "abuse@", "postmaster@", "spam@", "trap@",
]

# ─── DNS resolvers (cycled for resilience) ────────────────────────────────────
DNS_RESOLVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]

# ─── Microsoft O365 GetCredentialType endpoint ────────────────────────────────
O365_CREDENTIAL_URL = "https://login.microsoftonline.com/common/GetCredentialType"

# ─── Status definitions (BounceBlitz 9-status system) ────────────────────────
STATUS_DETAILS: dict[str, dict] = {
    "safe": {
        "label": "Safe",
        "score": 100,
        "meaning": "Mailbox exists and accepts mail; no risk flags.",
        "what_to_do": "Send with confidence.",
    },
    "role": {
        "label": "Role",
        "score": 70,
        "meaning": "Valid, but a shared company address (info@, support@).",
        "what_to_do": "Fine for B2B outreach; usually skip for newsletters.",
    },
    "catch_all": {
        "label": "Catch-All",
        "score": 50,
        "meaning": "The domain accepts mail for any name, so mailbox cannot be confirmed.",
        "what_to_do": "Send with caution, as a separate segment.",
    },
    "disposable": {
        "label": "Disposable",
        "score": 0,
        "meaning": "A throwaway address that expires shortly after creation.",
        "what_to_do": "Do not send; block it at sign-up.",
    },
    "inbox_full": {
        "label": "Inbox Full",
        "score": 35,
        "meaning": "A real mailbox that cannot accept new mail right now.",
        "what_to_do": "Skip for now and re-verify later.",
    },
    "spamtrap": {
        "label": "Spamtrap",
        "score": 0,
        "meaning": "An address that exists only to catch careless senders.",
        "what_to_do": "Never send.",
    },
    "disabled": {
        "label": "Disabled",
        "score": 0,
        "meaning": "Existed once; the provider has shut it down.",
        "what_to_do": "Do not send.",
    },
    "invalid": {
        "label": "Invalid",
        "score": 0,
        "meaning": "No mailbox exists: a guaranteed hard bounce.",
        "what_to_do": "Do not send.",
    },
    "unknown": {
        "label": "Unknown",
        "score": 15,
        "meaning": "The server would not give a definitive answer.",
        "what_to_do": "Not charged; re-verify later.",
    },
}

# Reason strings from primary MX indicating ambiguous/blocked result → try backup MX
AMBIGUOUS_REASONS = {
    "smtp_550_ambiguous", "smtp_554_connection_rejected", "smtp_553_ambiguous",
    "smtp_551_not_local", "smtp_timeout", "dns_timeout", "smtp_soft_fail_421",
    "smtp_soft_fail_450", "smtp_soft_fail_451",
}
