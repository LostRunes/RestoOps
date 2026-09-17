"""
DNS MX resolution with multi-resolver fallback — ported from BounceBlitz verifier.py.
"""
import dns.resolver
from app.services.verification.constants import DNS_RESOLVERS


def resolve_all_mx(domain: str) -> list[str] | bool | None:
    """
    Resolve ALL MX records for a domain, priority-sorted (lowest preference = highest priority).

    Returns:
        list[str]  — MX hostnames in priority order (primary first, backups after)
        False      — NXDOMAIN: domain definitively does not exist → mark invalid
        None       — Transient DNS failure → mark unknown (do NOT cache)
    """
    for ns in DNS_RESOLVERS:
        try:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [ns]
            resolver.timeout = 5
            resolver.lifetime = 8
            records = resolver.resolve(domain, "MX")
            sorted_records = sorted(records, key=lambda r: r.preference)
            return [str(r.exchange).rstrip(".") for r in sorted_records]
        except dns.resolver.NXDOMAIN:
            return False
        except dns.resolver.NoAnswer:
            break
        except Exception:
            continue

    # No MX records — try A-record as direct SMTP fallback
    for ns in DNS_RESOLVERS:
        try:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [ns]
            resolver.timeout = 5
            resolver.lifetime = 8
            resolver.resolve(domain, "A")
            return [domain]
        except dns.resolver.NXDOMAIN:
            return False
        except Exception:
            continue

    return None  # All resolvers failed — transient DNS failure


def detect_provider(mx_host: str) -> str:
    """Identify mail provider from MX hostname for DHA-aware classification."""
    from app.services.verification.constants import PROVIDER_MX_SIGNATURES
    mx_lower = mx_host.lower()
    for signatures, provider in PROVIDER_MX_SIGNATURES:
        if any(sig in mx_lower for sig in signatures):
            return provider
    return "generic"
