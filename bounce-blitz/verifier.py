# verifier.py - Bounce Blitz High-Concurrency Verification Engine

import csv
import io
import re
import time
import random
import uuid
import json
import threading
import urllib.request
import dns.resolver
import smtplib
from tempfile import NamedTemporaryFile
from concurrent.futures import ThreadPoolExecutor, as_completed

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
    "throwawaymail.com", "getairmail.com", "sharklasers.com", "yopmail.com",
    "trashmail.com", "dispostable.com"
}

ROLE_BASED_PREFIXES = {
    "info", "support", "admin", "sales", "contact", "billing", "help", "jobs",
    "careers", "marketing", "office", "team", "enquiries", "hello", "privacy"
}

SPAMTRAP_PATTERNS = {
    "spamtrap", "honeypot", "abuse@", "postmaster@", "spam@", "trap@"
}

# ─── Option A: Conservative invalid detection ────────────────────────────────
# Only these specific phrases, when present in an SMTP response, unambiguously
# signal that the mailbox does not exist.
#
# WHY: Many corporate SMTP servers (especially O365, Mimecast, Proofpoint) return
# bare 550/554 codes to ALL external SMTP probes as anti-harvesting protection —
# even for addresses that do exist. Treating every 550 as "invalid" produces a
# massive false-positive rate. We only mark "invalid" when the server's own
# message text leaves zero ambiguity about mailbox non-existence.
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
    "this address no longer accepts mail",   # Gmail disabled accounts
    "does not exist",
    "unrouteable address",                   # Postfix non-existent user
]

# ─── Option B: Provider-aware SMTP classification ────────────────────────────
# Map MX hostname substrings to known provider names.
#
# WHY: Gateway providers like Microsoft O365, Mimecast, and Proofpoint sit in
# front of real mail servers and reject SMTP probes from unknown IPs with 550
# as a Directory Harvest Attack (DHA) defence — not because the mailbox is gone.
# Provider detection lets us return "unknown" for these cases instead of "invalid".
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

# These providers use security gateways / DHA protection.
# A bare 550 from them (without a definitive invalid phrase) → unknown, not invalid.
GATEWAY_PROVIDERS = {
    "microsoft", "mimecast", "proofpoint", "barracuda",
    "messagelabs", "sophos", "spamhero", "mailchannels"
}

# DNS resolvers to cycle through for resilience against single-resolver timeouts
DNS_RESOLVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]

# Module-level sentinel — distinguishes "key not in cache" from False/None stored values
_MX_NOT_CACHED = object()

STATUS_DETAILS = {
    "safe": {
        "label": "Safe",
        "score": 100,
        "meaning": "Mailbox exists and accepts mail; no risk flags.",
        "what_to_do": "Send with confidence."
    },
    "role": {
        "label": "Role",
        "score": 70,
        "meaning": "Valid, but a shared company address (info@, support@).",
        "what_to_do": "Fine for B2B outreach; usually skip for newsletters."
    },
    "catch_all": {
        "label": "Catch-All",
        "score": 50,
        "meaning": "The domain accepts mail for any name, so mailbox cannot be confirmed.",
        "what_to_do": "Send with caution, as a separate segment."
    },
    "disposable": {
        "label": "Disposable",
        "score": 0,
        "meaning": "A throwaway address that expires shortly after creation.",
        "what_to_do": "Do not send; block it at sign-up."
    },
    "inbox_full": {
        "label": "Inbox Full",
        "score": 35,
        "meaning": "A real mailbox that cannot accept new mail right now.",
        "what_to_do": "Skip for now and re-verify later."
    },
    "spamtrap": {
        "label": "Spamtrap",
        "score": 0,
        "meaning": "An address that exists only to catch careless senders.",
        "what_to_do": "Never send."
    },
    "disabled": {
        "label": "Disabled",
        "score": 0,
        "meaning": "Existed once; the provider has shut it down.",
        "what_to_do": "Do not send."
    },
    "invalid": {
        "label": "Invalid",
        "score": 0,
        "meaning": "No mailbox exists: a guaranteed hard bounce.",
        "what_to_do": "Do not send."
    },
    "unknown": {
        "label": "Unknown",
        "score": 15,
        "meaning": "The server would not give a definitive answer.",
        "what_to_do": "Not charged; re-verify later."
    }
}

class DomainRateLimiter:
    """Thread-safe rate limiter restricting concurrent SMTP probes per target domain."""
    def __init__(self, max_concurrent=2):
        self.max_concurrent = max_concurrent
        self.semaphores = {}
        self.lock = threading.Lock()

    def get_semaphore(self, domain):
        with self.lock:
            if domain not in self.semaphores:
                self.semaphores[domain] = threading.Semaphore(self.max_concurrent)
            return self.semaphores[domain]


def detect_provider(mx_host: str) -> str:
    """
    Identify the mail provider from an MX hostname for provider-aware SMTP classification.
    Returns a provider name string, or 'generic' if the provider is unrecognised.
    """
    mx_lower = mx_host.lower()
    for signatures, provider in PROVIDER_MX_SIGNATURES:
        if any(sig in mx_lower for sig in signatures):
            return provider
    return "generic"


def is_definitive_invalid(msg_str: str) -> bool:
    """
    Return True only when the SMTP response message contains a phrase that
    unambiguously signals the mailbox does not exist (Option A).
    """
    msg_lower = msg_str.lower()
    return any(phrase in msg_lower for phrase in DEFINITIVE_INVALID_PHRASES)


def resolve_all_mx(domain: str):
    """
    Resolve ALL MX records for a domain (sorted by preference, lowest = highest priority)
    using multiple DNS resolvers with A-record fallback.

    Return values:
        list[str] — MX hostnames in priority order (primary first, backups after)
        False     — NXDOMAIN: domain definitively does not exist  → invalid
        None      — All resolvers failed: transient DNS failure   → unknown

    Returning the full list (instead of just the best) lets us fall back to
    secondary/tertiary MX servers when the primary blocks our probe.
    """
    for ns in DNS_RESOLVERS:
        try:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [ns]
            resolver.timeout = 5
            resolver.lifetime = 8
            records = resolver.resolve(domain, 'MX')
            # Sort ascending by preference so index 0 is the highest-priority MX
            sorted_records = sorted(records, key=lambda r: r.preference)
            return [str(r.exchange).rstrip('.') for r in sorted_records]
        except dns.resolver.NXDOMAIN:
            return False          # Definitive: domain does not exist
        except dns.resolver.NoAnswer:
            break                 # Domain exists but has no MX records — try A fallback
        except Exception:
            continue              # Timeout / network error — try next resolver

    # No MX records found on any resolver. Try A-record as direct SMTP fallback.
    for ns in DNS_RESOLVERS:
        try:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [ns]
            resolver.timeout = 5
            resolver.lifetime = 8
            resolver.resolve(domain, 'A')
            return [domain]       # Single-entry list so the rest of the logic is uniform
        except dns.resolver.NXDOMAIN:
            return False
        except Exception:
            continue

    return None                   # All resolvers failed — treat as transient DNS failure


def check_o365_user(email: str):
    """
    Verify whether a mailbox exists in Microsoft O365 / Azure AD via the public
    GetCredentialType endpoint used by Microsoft's own login page.

    This bypasses SMTP entirely — no IP reputation required.

    IfExistsResult codes:
        0 → user exists (managed O365 account)
        1 → user does NOT exist
        5 → user exists (different / federated auth flow)
        6 → user exists (passkey / FIDO auth)
        others → ambiguous; caller should fall back to SMTP

    ThrottleStatus 1 → Microsoft is rate-limiting us; result is unreliable.

    Returns (status, reason) where status=None means "exists — caller decides safe/role".
    """
    url = "https://login.microsoftonline.com/common/GetCredentialType"
    payload = json.dumps({"username": email}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("ThrottleStatus") == 1:
            return "unknown", "o365_throttled"

        if_exists = data.get("IfExistsResult", -1)

        if if_exists in (0, 5, 6):
            return None, None          # Mailbox confirmed to exist; caller adds safe/role
        elif if_exists == 1:
            return "invalid", "o365_user_not_found"
        else:
            # 2 = unknown (federated), 3 = other — can't determine; fall back to SMTP
            return "unknown", "o365_ambiguous_result"

    except Exception:
        return "unknown", "o365_api_error"


def classify_smtp_response(code, msg_str: str, provider: str):
    """
    Options A + B combined SMTP response classifier.

    Returns (status, reason) tuple.
    Returns (None, None) for code 250 — caller handles the safe/role distinction.
    """
    if code == 250:
        return None, None

    msg_lower = msg_str.lower()

    # Inbox full / quota exceeded — must check before 452 falls into invalid path
    if (code == 452
            or "quota exceeded" in msg_lower
            or "mailbox full" in msg_lower
            or "over quota" in msg_lower
            or "storage limit" in msg_lower):
        return "inbox_full", "mailbox_over_quota"

    # Account disabled / deactivated
    if ("disabled" in msg_lower
            or "inactive" in msg_lower
            or "suspended" in msg_lower):
        return "disabled", "account_disabled"

    # Determine once whether the message contains an unambiguous invalid signal
    definitive = is_definitive_invalid(msg_str)

    # 550: Most common ambiguous rejection code
    # Cannot be blindly trusted as "mailbox does not exist":
    #   - O365/Exchange returns 550 for ALL unknown-IP SMTP probes (DHA protection)
    #   - Many providers use 550 for policy blocks unrelated to mailbox existence
    if code == 550:
        if definitive:
            return "invalid", "user_not_found"
        if provider in GATEWAY_PROVIDERS:
            return "unknown", "provider_dha_" + provider
        # Generic provider — bare 550 without a definitive phrase: be conservative
        return "unknown", "smtp_550_ambiguous"

    # 554: Transaction/connection-level rejection
    # Means our IP/session was refused, NOT that the mailbox doesn't exist.
    if code == 554:
        if definitive:
            return "invalid", "user_not_found"
        return "unknown", "smtp_554_connection_rejected"

    # 553: Mailbox name not allowed — usually bad syntax, not non-existence
    if code == 553:
        if definitive:
            return "invalid", "user_not_found"
        return "unknown", "smtp_553_ambiguous"

    # 551: User not local — server may forward; can't determine existence
    if code == 551:
        return "unknown", "smtp_551_not_local"

    # Soft-fail / temporary deferral codes
    if code in [421, 450, 451, 503]:
        return "unknown", "smtp_soft_fail_" + str(code)

    # Connection/timeout failure (exception path — code is None)
    if code is None:
        return "unknown", "smtp_timeout"

    # Any other non-250 code
    if definitive:
        return "invalid", "user_not_found"

    # Unknown rejection without a definitive phrase — don't assume invalid
    return "unknown", "smtp_rejected_" + str(code)


def _smtp_probe_mx(mx_host: str, email: str, domain: str, is_role: bool):
    """
    Run catch-all detection + mailbox verification against a specific MX host.
    Returns (status, reason) — used for both primary and backup MX probes.
    """
    provider = detect_provider(mx_host)

    # Catch-all detection: probe a guaranteed-nonexistent address
    catch_all = False
    try:
        server = smtplib.SMTP(timeout=8)
        try:
            server.connect(mx_host)
            server.helo("bounceblitz.com")
            server.mail("probe@bounceblitz.com")
            code, msg = server.rcpt(f"nonexistent_probe_9918237@{domain}")
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

    # Mailbox existence probe with one soft-fail retry
    def smtp_probe():
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
        except Exception as e:
            return None, str(e)

    code, msg_str = smtp_probe()

    if code in [421, 450, 451, 452, 503]:
        time.sleep(2.0 + random.uniform(0.5, 2.0))
        code, msg_str = smtp_probe()

    if code == 250:
        return ("role", "role_account") if is_role else ("safe", "mailbox_exists")

    return classify_smtp_response(code, msg_str, provider)


# Reason strings that indicate the result was ambiguous/blocked (not definitive).
# When a primary MX returns one of these, we try backup MX records.
_AMBIGUOUS_REASONS = {
    "smtp_550_ambiguous", "smtp_554_connection_rejected", "smtp_553_ambiguous",
    "smtp_551_not_local", "smtp_timeout", "dns_timeout",
}


def check_single_email(email, mx_cache, mx_lock, rate_limiter):
    email = (email or "").strip()
    if not email or not EMAIL_REGEX.match(email):
        return "invalid", "bad_syntax"

    local, domain = email.split('@')[0].lower(), email.split('@')[1].lower()

    if any(pat in email.lower() for pat in SPAMTRAP_PATTERNS):
        return "spamtrap", "known_honeypot"

    if domain in DISPOSABLE_DOMAINS:
        return "disposable", "disposable_domain"

    is_role = local in ROLE_BASED_PREFIXES

    # ── Thread-safe MX Resolution & Caching ──────────────────────────────────
    # Cache stores the full priority-sorted MX list (or False for NXDOMAIN).
    # None (DNS timeout) is intentionally NOT cached — domain gets re-resolved next time.
    with mx_lock:
        cached_mx = mx_cache.get(domain, _MX_NOT_CACHED)

    if cached_mx is _MX_NOT_CACHED:
        mx_list = resolve_all_mx(domain)
        if mx_list is not None:         # Don't cache transient DNS failures
            with mx_lock:
                mx_cache[domain] = mx_list
    else:
        mx_list = cached_mx

    if mx_list is False:
        return "invalid", "no_mx_record"   # NXDOMAIN: domain definitively doesn't exist

    if mx_list is None:
        return "unknown", "dns_timeout"    # Transient failure: don't mark invalid

    primary_mx = mx_list[0]
    provider   = detect_provider(primary_mx)

    # ── Microsoft O365 fast-path (no SMTP, no IP reputation needed) ──────────
    # For O365-hosted domains, Microsoft's own login endpoint gives us a definitive
    # yes/no on mailbox existence without touching SMTP at all.
    if provider == "microsoft":
        status, reason = check_o365_user(email)
        if status == "unknown" and reason in ("o365_throttled", "o365_ambiguous_result",
                                               "o365_api_error"):
            # API inconclusive — fall through to SMTP as a last resort
            pass
        elif status is None:
            # Mailbox confirmed to exist
            return ("role", "o365_role_confirmed") if is_role else ("safe", "o365_mailbox_confirmed")
        else:
            return status, reason

    # ── Standard SMTP probe (primary MX, domain-throttled) ───────────────────
    domain_sem = rate_limiter.get_semaphore(domain)
    with domain_sem:
        status, reason = _smtp_probe_mx(primary_mx, email, domain, is_role)

    # ── Backup MX fallback ────────────────────────────────────────────────────
    # If the primary MX returned an ambiguous/blocked result (not a definitive
    # safe/invalid/catch_all), try secondary and tertiary MX servers.
    # Backup MX servers are often older, less hardened, and may not have the same
    # DHA protection, giving us a more accurate response.
    if status == "unknown" and reason in _AMBIGUOUS_REASONS and len(mx_list) > 1:
        for backup_mx in mx_list[1:]:
            backup_provider = detect_provider(backup_mx)
            # Don't retry another Microsoft gateway — same protection applies
            if backup_provider == "microsoft":
                continue
            with domain_sem:
                backup_status, backup_reason = _smtp_probe_mx(backup_mx, email, domain, is_role)
            # Accept the backup result if it's more informative than unknown
            if backup_status != "unknown":
                return backup_status, "backup_mx_" + backup_reason
            # If this backup was also ambiguous, note it but try the next one
            reason = backup_reason

    return status, reason

class VerificationJob:
    def __init__(self, job_id, filename, file_content):
        self.job_id = job_id
        self.filename = filename
        self.file_content = file_content
        self.progress = 0
        self.row_count = 0
        self.total = 0
        self.log = "Initializing batch..."
        self.cancelled = False
        self.output_file = None
        self.stats = {
            "safe": 0, "role": 0, "catch_all": 0, "disposable": 0,
            "inbox_full": 0, "spamtrap": 0, "disabled": 0, "invalid": 0, "unknown": 0
        }
        self.records = []
        self.fieldnames = []
        self.email_field = None

    def process(self):
        # ── Header detection ─────────────────────────────────────────────────
        # When users upload a raw list of emails with no header row, csv.DictReader
        # silently treats the FIRST email as the column name, losing it from the data
        # and misaligning every status column for that row.
        #
        # Fix: peek at the raw first row. If its first cell looks like an email address
        # (contains '@'), the file has no header — inject a synthetic one so every
        # email (including the first) is correctly treated as a data row.
        raw_rows = list(csv.reader(io.StringIO(self.file_content)))
        if not raw_rows:
            self.log = "Empty CSV file provided"
            self.progress = 100
            return

        first_cell = raw_rows[0][0].strip() if raw_rows[0] else ""
        has_header = '@' not in first_cell  # If first cell has @, it's an email, not a header

        if has_header:
            reader = list(csv.DictReader(io.StringIO(self.file_content)))
        else:
            # Headerless file: build synthetic column names and re-parse from scratch.
            # col_count accounts for any extra columns beyond just the email.
            col_count = len(raw_rows[0])
            synthetic_fields = ['email'] + [f'col{i}' for i in range(1, col_count)]
            reader = list(csv.DictReader(
                io.StringIO(self.file_content),
                fieldnames=synthetic_fields
            ))

        self.total = len(reader)
        if self.total == 0:
            self.log = "Empty CSV file provided"
            self.progress = 100
            return

        # Locate the email column: prefer a column literally named 'email',
        # otherwise fall back to the first column (covers headerless files too).
        self.email_field = next(
            (f for f in reader[0].keys() if f.lower().strip() == 'email'),
            list(reader[0].keys())[0]
        )
        # Output fieldnames: original columns first, then our appended status columns.
        self.fieldnames = list(reader[0].keys()) + [
            'status', 'status_label', 'score', 'meaning', 'what_to_do', 'reason'
        ]

        mx_cache = {}
        mx_lock = threading.Lock()
        rate_limiter = DomainRateLimiter(max_concurrent=2)

        completed = 0
        results = [None] * self.total

        def worker(idx_and_row):
            idx, row = idx_and_row
            if self.cancelled:
                return idx, row, "cancelled", "job_cancelled"

            email = (row.get(self.email_field) or "").strip()
            status, reason = check_single_email(email, mx_cache, mx_lock, rate_limiter)

            info = STATUS_DETAILS.get(status, STATUS_DETAILS["unknown"])
            row['status'] = status
            row['status_label'] = info['label']
            row['score'] = info['score']
            row['meaning'] = info['meaning']
            row['what_to_do'] = info['what_to_do']
            row['reason'] = reason

            return idx, row, status, reason

        # High concurrency worker pool running 50 threads across domain-throttled queue
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_map = {executor.submit(worker, (i, r)): i for i, r in enumerate(reader)}
            for future in as_completed(future_map):
                if self.cancelled:
                    self.log = f"❌ Canceled batch {self.job_id}"
                    break
                try:
                    idx, processed_row, status, reason = future.result()
                    results[idx] = processed_row
                    completed += 1
                    if status in self.stats:
                        self.stats[status] += 1

                    percent = int((completed / self.total) * 100)
                    self.progress = percent
                    self.row_count = completed
                    email_val = processed_row.get(self.email_field, '')
                    label = STATUS_DETAILS.get(status, {}).get("label", status.title())
                    score = STATUS_DETAILS.get(status, {}).get("score", 0)
                    self.log = f"⚡ [{completed}/{self.total}] {email_val} → {label} (Score: {score}) | {reason}"
                except Exception as e:
                    completed += 1

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fieldnames)
        writer.writeheader()
        for r in results:
            if r is not None:
                writer.writerow(r)

        output.seek(0)
        temp = NamedTemporaryFile(delete=False, suffix=".csv", mode='w+', encoding='utf-8')
        temp.write(output.read())
        temp.flush()
        temp.seek(0)
        self.output_file = temp.name
        self.progress = 100
