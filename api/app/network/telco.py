"""Mocked telco-native APIs. In production these call Accel's own network:

* fibre serviceability by pin code (OSS inventory)
* SIM Swap check (GSMA Open Gateway / CAMARA; Indian operators launched it in 2025)
* Number Verification (CAMARA) instead of SMS OTP
* masked calling through Accel CPaaS virtual numbers, so partners never see a customer's number
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from ..db import now

# pin codes the demo treats as having no fibre yet (deterministic elsewhere)
NO_FIBRE_PINS = {"302001", "416001", "226010", "800001", "462001"}


def fibre_feasible(pincode: str | None) -> bool | None:
    if not pincode:
        return None
    if pincode in NO_FIBRE_PINS:
        return False
    return int(hashlib.sha256(pincode.encode()).hexdigest(), 16) % 10 >= 2  # ~80% of pin codes have fibre


def sim_swap(phone: str) -> dict:
    """Days since the SIM was last swapped. A swap in the last 72 hours blocks auto-approval."""
    h = int(hashlib.sha256(phone.encode()).hexdigest(), 16)
    recent = phone.endswith("0000") or h % 50 == 0
    swapped_at = now() - (timedelta(hours=20) if recent else timedelta(days=200 + h % 400))
    return {"swapped_recently": recent, "last_swap": swapped_at.isoformat(), "window_hours": 72}


def number_verify(phone: str, device_hint: str | None = None) -> dict:
    return {"verified": True, "method": "network" if device_hint else "otp_fallback"}


def masked_number() -> str:
    """A virtual number from the CPaaS pool, bridged to the customer for 72 hours."""
    return "+91 80" + "".join(secrets.choice("0123456789") for _ in range(8))
