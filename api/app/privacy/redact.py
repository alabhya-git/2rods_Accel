"""Masking for logs, LLM prompts and any text that leaves the trust boundary."""
from __future__ import annotations

import logging
import re

PATTERNS = [
    (re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"), lambda m: m.group()[:4] + "********" + m.group()[-3:]),  # GSTIN
    (re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b"), lambda m: m.group()[:12] + "*****" + m.group()[-2:]),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), lambda m: m.group()[:2] + "******" + m.group()[-2:]),  # PAN
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"), lambda m: re.sub(r"\d(?=\d{2})", "*", m.group())),  # mobile
    (re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"), lambda m: "XXXX XXXX " + m.group()[-4:]),  # Aadhaar-like
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), lambda m: m.group()[0] + "***@" + m.group().split("@")[1]),
    (re.compile(r"\bSYN-ID-\d{6}\b"), lambda m: "SYN-ID-****" + m.group()[-2:]),
]


def mask_text(text: str) -> str:
    for rx, fn in PATTERNS:
        text = rx.sub(fn, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and record.args:  # mask each value, keep the shape: uvicorn's access log unpacks it
            record.msg = mask_text(str(record.msg))
            record.args = tuple(mask_text(a) if isinstance(a, str) else a for a in record.args)
            return True
        try:
            msg = record.getMessage()
        except Exception:  # pragma: no cover
            return True
        record.msg, record.args = mask_text(msg), ()
        return True


def install() -> None:
    f = RedactingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "app"):
        lg = logging.getLogger(name)
        lg.addFilter(f)
        for h in lg.handlers:
            h.addFilter(f)
