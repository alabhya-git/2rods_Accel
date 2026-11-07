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


def number_verify_for(phone: str) -> dict:
    """An Accel SIM answers the network check silently; other networks fall back to an OTP."""
    return number_verify(phone, device_hint="accel_sim" if accel_account(phone) else None)


# Accel's own subscriber base (BSS/CRM). 38% of leads already use Accel, yet each one starts
# as a stranger. Demo numbers below; production reads the CRM by the verified number.
ACCOUNTS = {
    "9876500001": {"account": "ACC-20191184", "since": 2019, "kind": "mobile", "monthly_spend": 1150,
                   "lines": [("L1", "9876500001", "Postpaid 399"), ("L2", "9876500011", "Postpaid 299"), ("L3", "9876500012", "Prepaid 239")]},
    "9876500002": {"account": "ACC-20210457", "since": 2021, "kind": "home_fibre_mobile", "monthly_spend": 1499,
                   "lines": [("L1", "9876500002", "Postpaid 499")]},
}


def accel_account(phone: str) -> dict | None:
    """Only ever called with a number that has just been verified: nothing about an account is
    shown to someone who merely typed the number."""
    return ACCOUNTS.get(phone[-10:])


def masked_number() -> str:
    """A virtual number from the CPaaS pool, bridged to the customer for 72 hours."""
    return "+91 80" + "".join(secrets.choice("0123456789") for _ in range(8))
