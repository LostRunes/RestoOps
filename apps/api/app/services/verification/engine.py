"""
Async Email Verification Engine — orchestrates BounceBlitz-style verification.

Architecture:
    - Blocking DNS/SMTP/O365 calls run in a thread-pool executor so the event loop stays free.
    - Domain-level semaphore (max 2 concurrent SMTP probes per domain) prevents DHA triggering.
    - Primary MX → backup MX fallback when primary blocks/throttles.
    - Microsoft O365 fast-path bypasses SMTP entirely for *.protection.outlook.com domains.
"""
from __future__ import annotations

import asyncio
import re
import threading
import time
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from app.services.verification.constants import (
    AMBIGUOUS_REASONS,
    DISPOSABLE_DOMAINS,
    ROLE_BASED_PREFIXES,
    SPAMTRAP_PATTERNS,
    STATUS_DETAILS,
)
from app.services.verification.dns_checker import detect_provider, resolve_all_mx
from app.services.verification.o365_checker import check_o365_user
from app.services.verification.smtp_prober import smtp_probe_mx

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Sentinel object — distinguishes "key not in cache" from False/None stored values
_MX_NOT_CACHED = object()


@dataclass
class VerificationResult:
    email: str
    status: str
    status_label: str
    score: int
    reason: str
    meaning: str
    what_to_do: str

    # Granular flags
    syntax_valid: bool = True
    domain_valid: bool | None = None
    mx_valid: bool | None = None
    disposable: bool = False
    role_based: bool = False
    catch_all: bool = False
    spamtrap: bool = False

    # SMTP details
    smtp_code: int | None = None
    smtp_message: str | None = None
    mx_host: str | None = None
    provider: str | None = None

    latency_ms: int | None = None


class DomainRateLimiter:
    """Thread-safe per-domain semaphore limiting concurrent SMTP probes."""

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._lock = threading.Lock()

    def get(self, domain: str) -> threading.Semaphore:
        with self._lock:
            if domain not in self._semaphores:
                self._semaphores[domain] = threading.Semaphore(self.max_concurrent)
            return self._semaphores[domain]


def _build_result(
    email: str, status: str, reason: str, **kwargs
) -> VerificationResult:
    """Helper to construct a fully populated VerificationResult."""
    info = STATUS_DETAILS.get(status, STATUS_DETAILS["unknown"])
    return VerificationResult(
        email=email,
        status=status,
        status_label=info["label"],
        score=info["score"],
        reason=reason,
        meaning=info["meaning"],
        what_to_do=info["what_to_do"],
        **kwargs,
    )


def _verify_sync(
    email: str,
    mx_cache: dict,
    mx_lock: threading.Lock,
    rate_limiter: DomainRateLimiter,
) -> VerificationResult:
    """
    Synchronous single-email verification — runs inside a thread executor.
    Full BounceBlitz pipeline: syntax → spamtrap → disposable → DNS → O365/SMTP.
    """
    t0 = time.monotonic()
    email = (email or "").strip()

    # ── 1. Syntax check ───────────────────────────────────────────────────────
    if not email or not EMAIL_REGEX.match(email):
        return _build_result(email, "invalid", "bad_syntax", syntax_valid=False,
                             latency_ms=int((time.monotonic() - t0) * 1000))

    local, domain = email.split("@", 1)
    local = local.lower()
    domain = domain.lower()

    # ── 2. Spamtrap check ─────────────────────────────────────────────────────
    if any(pat in email.lower() for pat in SPAMTRAP_PATTERNS):
        return _build_result(email, "spamtrap", "known_honeypot", spamtrap=True,
                             latency_ms=int((time.monotonic() - t0) * 1000))

    # ── 3. Disposable domain check ────────────────────────────────────────────
    if domain in DISPOSABLE_DOMAINS:
        return _build_result(email, "disposable", "disposable_domain", disposable=True,
                             latency_ms=int((time.monotonic() - t0) * 1000))

    is_role = local in ROLE_BASED_PREFIXES

    # ── 4. MX resolution (thread-safe with domain cache) ─────────────────────
    with mx_lock:
        cached_mx = mx_cache.get(domain, _MX_NOT_CACHED)

    if cached_mx is _MX_NOT_CACHED:
        mx_list = resolve_all_mx(domain)
        if mx_list is not None:  # Don't cache transient DNS failures
            with mx_lock:
                mx_cache[domain] = mx_list
    else:
        mx_list = cached_mx

    if mx_list is False:
        return _build_result(email, "invalid", "no_mx_record",
                             domain_valid=False, mx_valid=False,
                             latency_ms=int((time.monotonic() - t0) * 1000))
    if mx_list is None:
        return _build_result(email, "unknown", "dns_timeout",
                             domain_valid=None, mx_valid=None,
                             latency_ms=int((time.monotonic() - t0) * 1000))

    primary_mx = mx_list[0]
    provider = detect_provider(primary_mx)

    # ── 5. Microsoft O365 fast-path ───────────────────────────────────────────
    if provider == "microsoft":
        o365_status, o365_reason = check_o365_user(email)
        if o365_status == "unknown" and o365_reason in (
            "o365_throttled", "o365_ambiguous_result", "o365_api_error"
        ):
            pass  # API inconclusive — fall through to SMTP
        elif o365_status is None:
            final_status = "role" if is_role else "safe"
            final_reason = "o365_role_confirmed" if is_role else "o365_mailbox_confirmed"
            return _build_result(
                email, final_status, final_reason,
                mx_valid=True, role_based=is_role,
                mx_host=primary_mx, provider=provider,
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        else:
            return _build_result(
                email, o365_status, o365_reason,
                mx_valid=True, mx_host=primary_mx, provider=provider,
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

    # ── 6. Standard SMTP probe (primary MX, domain-throttled) ─────────────────
    domain_sem = rate_limiter.get(domain)
    with domain_sem:
        status, reason = smtp_probe_mx(primary_mx, email, domain, is_role)

    # ── 7. Backup MX fallback ─────────────────────────────────────────────────
    if status == "unknown" and reason in AMBIGUOUS_REASONS and len(mx_list) > 1:
        for backup_mx in mx_list[1:]:
            backup_provider = detect_provider(backup_mx)
            if backup_provider == "microsoft":
                continue  # Same DHA protection applies
            with domain_sem:
                backup_status, backup_reason = smtp_probe_mx(
                    backup_mx, email, domain, is_role
                )
            if backup_status != "unknown":
                status = backup_status
                reason = "backup_mx_" + backup_reason
                primary_mx = backup_mx
                provider = backup_provider
                break
            reason = backup_reason

    return _build_result(
        email, status, reason,
        mx_valid=True, role_based=is_role,
        catch_all=(status == "catch_all"),
        mx_host=primary_mx, provider=provider,
        latency_ms=int((time.monotonic() - t0) * 1000),
    )


# ─── Async public interface ────────────────────────────────────────────────────

_executor = ThreadPoolExecutor(max_workers=50)


async def verify_email(email: str) -> VerificationResult:
    """Verify a single email asynchronously (non-blocking)."""
    mx_cache: dict = {}
    mx_lock = threading.Lock()
    rate_limiter = DomainRateLimiter()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _verify_sync, email, mx_cache, mx_lock, rate_limiter
    )


async def verify_batch(
    emails: list[str],
    progress_callback=None,
    cancelled_flag=None,
) -> list[VerificationResult]:
    """
    Verify a list of emails concurrently.

    Args:
        emails: List of email strings to verify.
        progress_callback: Optional async callable(index, total, result) for real-time updates.
        cancelled_flag: Optional asyncio.Event; set it to cancel the batch mid-run.

    Returns:
        List of VerificationResult in the same order as input.
    """
    mx_cache: dict = {}
    mx_lock = threading.Lock()
    rate_limiter = DomainRateLimiter()
    loop = asyncio.get_event_loop()

    results: list[VerificationResult | None] = [None] * len(emails)

    async def _run_one(idx: int, email: str):
        if cancelled_flag and cancelled_flag.is_set():
            results[idx] = _build_result(email, "unknown", "job_cancelled")
            return
        result = await loop.run_in_executor(
            _executor, _verify_sync, email, mx_cache, mx_lock, rate_limiter
        )
        results[idx] = result
        if progress_callback:
            await progress_callback(idx, len(emails), result)

    await asyncio.gather(*[_run_one(i, e) for i, e in enumerate(emails)])
    return results
