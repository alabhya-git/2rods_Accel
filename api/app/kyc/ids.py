"""GSTIN and Udyam identifiers: format, checksum, masking and OCR self-healing.

GSTIN = 2-digit state code + 10-char PAN + entity number + 'Z' + check character.
The dataset's PANs use 'X' as 4th character (not a real entity type); we accept it.

Self-healing fixes only *OCR confusions* (O/0, I/1, Z/2, S/5, B/8 ...) chosen by the
position's character class, plus stray duplicated characters. It can never change a
digit into a different digit, so a tampered number (e.g. 5189 -> 8189) still fails.
"""
from __future__ import annotations

import itertools
import re

CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$")

# confusions OCR makes, by the character class a position must hold
TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "U": "0", "I": "1", "L": "1", "T": "7", "Z": "2", "S": "5", "B": "8", "G": "6", "A": "4"}
TO_LETTER = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G", "7": "T", "4": "A"}
ALNUM_ALTS = {"0": "OQD", "O": "0QD", "Q": "O0", "D": "O0", "1": "I", "I": "1", "2": "Z", "Z": "2", "5": "S", "S": "5", "8": "B", "B": "8"}

STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand",
    "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya",
    "18": "Assam", "19": "West Bengal", "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}

# character class per GSTIN position: d = digit, L = letter, a = alnum, z = literal Z
GSTIN_CLASSES = "ddLLLLLddddLazA"  # pos 12 in [1-9A-Z], pos 14 checksum alnum (A)


def checksum(first14: str) -> str:
    total = 0
    for i, c in enumerate(first14):
        v = CH.index(c) * (2 if i % 2 else 1)
        total += v // 36 + v % 36
    return CH[(36 - total % 36) % 36]


def gstin_valid(g: str | None) -> bool:
    return bool(g) and bool(GSTIN_RE.match(g)) and checksum(g[:14]) == g[14]


def gstin_state(g: str) -> str | None:
    return STATE_CODES.get(g[:2])


def udyam_valid(u: str | None) -> bool:
    return bool(u) and bool(UDYAM_RE.match(u))


def mask_gstin(g: str | None) -> str:
    if not g:
        return ""
    return g[:4] + "*" * max(0, len(g) - 7) + g[-3:]


def mask_udyam(u: str | None) -> str:
    if not u:
        return ""
    return u[:12] + "*" * max(0, len(u) - 14) + u[-2:]


def mask_phone(p: str | None) -> str:
    if not p:
        return ""
    digits = re.sub(r"\D", "", p)
    return digits[:2] + "*" * max(0, len(digits) - 4) + digits[-2:]


def _coerce(s: str) -> str | None:
    """Map each character to the class its position requires; None if impossible."""
    out = []
    for c, cls in zip(s, GSTIN_CLASSES):
        if cls == "d":
            c = c if c.isdigit() else TO_DIGIT.get(c, "")
        elif cls == "L":
            c = c if c.isalpha() else TO_LETTER.get(c, "")
        elif cls == "z":
            c = "Z" if c in "Z2" else ""
        elif cls == "a":
            c = c if c != "0" else ""
        if not c:
            return None
        out.append(c)
    return "".join(out)


def heal_gstin(raw: str, known: set[str] | None = None) -> dict:
    """Return {'value', 'healed', 'valid', 'edits', 'raw'} for an OCR'd GSTIN.

    Tries removing up to 3 stray characters, coerces by position class, then resolves
    the remaining alphanumeric ambiguity (positions 13 and 15) with the checksum.
    A candidate in `known` (the registry) is preferred when several pass.
    """
    s = re.sub(r"[^0-9A-Z]", "", (raw or "").upper())
    result = {"raw": raw, "value": s, "healed": False, "valid": gstin_valid(s), "edits": 0}
    if result["valid"]:
        return result
    best: tuple[int, int, str] | None = None
    for n_del in range(0, min(3, max(0, len(s) - 15)) + 1):
        if len(s) - n_del != 15:
            continue
        for drop in itertools.combinations(range(len(s)), n_del):
            cand = "".join(c for i, c in enumerate(s) if i not in drop)
            base = _coerce(cand)
            if not base:
                continue
            edits = n_del + sum(a != b for a, b in zip(cand, base))
            options = [[c] + list(ALNUM_ALTS.get(c, "")) if GSTIN_CLASSES[i] in "aA" else [c] for i, c in enumerate(base)]
            for combo in itertools.product(*options):
                g = "".join(combo)
                if not gstin_valid(g):
                    continue
                e = edits + sum(a != b for a, b in zip(base, g))
                rank = (0 if known and g in known else 1, e, g)
                if best is None or rank < best:
                    best = rank
    if best:
        result.update(value=best[2], healed=True, valid=True, edits=best[1])
    else:
        coerced = _coerce(s) if len(s) == 15 else None
        result["value"] = coerced or s
    return result


def heal_udyam(raw: str, known: set[str] | None = None) -> dict:
    s = re.sub(r"[^0-9A-Z]", "", (raw or "").upper())
    result = {"raw": raw, "value": "", "healed": False, "valid": False}
    if not s:
        return result
    s = re.sub(r"^(UDYAM|UOYAM|UDVAM|UDYAN|UBYAM)", "UDYAM", s)
    if not s.startswith("UDYAM"):
        s = "UDYAM" + s[-11:] if len(s) >= 11 else s
    body = s[5:]
    if len(body) != 11:
        result["value"] = s
        return result
    st = "".join(c if c.isalpha() else TO_LETTER.get(c, c) for c in body[:2])
    rest = "".join(c if c.isdigit() else TO_DIGIT.get(c, c) for c in body[2:])
    value = f"UDYAM-{st}-{rest[:2]}-{rest[2:]}"
    result.update(value=value, valid=udyam_valid(value), healed=value.replace("-", "") != s)
    if known is not None and result["valid"] and value not in known:
        result["in_registry"] = False
    return result
