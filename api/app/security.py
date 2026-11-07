"""Who may do what: signed staff tokens with roles, rate limits, and a production start-up guard.

Staff (partners, KYC reviewers, ops, admins) sign in and get a short-lived token signed
with a key derived from the master key. Every back-office action names a real person
and role from that token, never a free-text field. In production the demo passcode,
judge routes and open CORS refuse to start.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from .config import get_settings

TOKEN_TTL_S = 8 * 3600
ROLES = ("partner", "reviewer", "ops", "admin")

# Demo staff, only when judge mode is on. Production reads STAFF_ACCOUNTS (JSON) from Secret Manager.
DEMO_ACCOUNTS = {
    "PARTNER-001": {"secret": "partner-demo", "role": "partner", "partner_id": "PARTNER-001", "name": "Sharma Telecom, Jaipur"},
    "PARTNER-002": {"secret": "partner-demo", "role": "partner", "partner_id": "PARTNER-002", "name": "Kochi Mobiles"},
    "reviewer-1": {"secret": "review-demo", "role": "reviewer", "name": "Asha (KYC)"},
    "reviewer-2": {"secret": "review-demo", "role": "reviewer", "name": "Imran (KYC)"},
    "ops-1": {"secret": "ops-demo", "role": "ops", "name": "Field ops desk"},
    "admin": {"secret": "admin-demo", "role": "admin", "name": "Demo admin"},
}


def _key() -> bytes:
    return hmac.new(get_settings().master_key(), b"staff-token-v1", hashlib.sha256).digest()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def accounts() -> dict:
    st = get_settings()
    out = dict(DEMO_ACCOUNTS) if st.judge_mode else {}
    if st.staff_accounts:
        out.update(json.loads(st.staff_accounts))
    return out


def login(user: str, secret: str) -> dict:
    acct = accounts().get(user)
    if not acct or not hmac.compare_digest(acct["secret"].encode(), (secret or "").encode()):
        raise HTTPException(401, "wrong name or passcode")
    claims = {"sub": user, "role": acct["role"], "name": acct.get("name", user), "partner_id": acct.get("partner_id"),
              "exp": int(time.time()) + TOKEN_TTL_S}
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    return {"token": f"{body}.{sig}", **claims}


def verify(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    good = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, sig):
        return None
    claims = json.loads(_unb64(body))
    return claims if claims.get("exp", 0) > time.time() else None


def staff(*roles: str):
    """Dependency: a signed-in staff member holding one of `roles` (admin always passes)."""
    def dep(authorization: str | None = Header(default=None), x_staff_token: str | None = Header(default=None),
            x_partner_key: str | None = Header(default=None)) -> dict:
        token = (authorization or "").removeprefix("Bearer ").strip() or x_staff_token
        claims = verify(token)
        if claims is None and x_partner_key and get_settings().judge_mode and x_partner_key == get_settings().backoffice_passcode:
            claims = {"sub": "PARTNER-001", "role": "partner", "name": "Demo partner", "partner_id": "PARTNER-001"}  # demo only
        if claims is None:
            raise HTTPException(401, "sign in to the partner desk")
        if roles and claims["role"] not in roles and claims["role"] != "admin":
            raise HTTPException(403, f"needs the {' or '.join(roles)} role")
        return claims
    return dep


# ---- rate limits ------------------------------------------------------------------------

LIMITS = [  # (method, path prefix or suffix test, bucket, max requests, window seconds)
    ("POST", lambda p: p == "/api/orders", "order", 10, 60),
    ("POST", lambda p: p.startswith("/api/advisor/") and p.endswith("/messages"), "chat", 40, 60),
    ("POST", lambda p: "/kyc/documents" in p, "upload", 30, 60),
    ("POST", lambda p: p == "/api/help", "help", 5, 300),
    ("POST", lambda p: p == "/api/staff/login", "login", 10, 300),
    # a call speaks and listens every few seconds; GET speak costs the same as POST, so both count
    ("POST", lambda p: p.startswith("/api/voice/"), "voice", 120, 60),
    ("GET", lambda p: p == "/api/voice/speak", "voice", 120, 60),
]
_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "?")


def check_rate(request: Request) -> tuple[bool, int]:
    """In-process sliding window. With REDIS_URL set the same limits run per instance; Cloudflare adds a global cap."""
    path, method = request.url.path, request.method
    for m, test, bucket, limit, window in LIMITS:
        if m == method and test(path):
            key = (bucket, client_ip(request))
            now = time.monotonic()
            with _lock:
                q = _hits[key]
                while q and q[0] <= now - window:
                    q.popleft()
                if len(q) >= limit:
                    return False, int(window - (now - q[0])) + 1
                q.append(now)
            return True, 0
    return True, 0


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


# ---- production guard ------------------------------------------------------------------

def production_problems() -> list[str]:
    st = get_settings()
    if st.environment != "prod":
        return []
    out = []
    if st.judge_mode:
        out.append("JUDGE_MODE must be false in production")
    if not st.master_key_b64:
        out.append("MASTER_KEY_B64 must be set (from Secret Manager, wrapped by Cloud KMS)")
    if not st.staff_accounts:
        out.append("STAFF_ACCOUNTS must be set; demo staff are disabled in production")
    if st.cors_origins.strip() in ("", "*"):
        out.append("CORS_ORIGINS must list the app's own origin")
    if st.whatsapp_token and not st.whatsapp_app_secret:
        out.append("WHATSAPP_APP_SECRET is required to verify webhook signatures")
    if st.mock_adapters_allowed:
        out.append("MOCK_ADAPTERS_ALLOWED must be false in production")
    return out
