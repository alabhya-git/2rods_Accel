"""Spelling-proof matching for loanwords written in Indian scripts.

Owners spell English loanwords many ways: व्हाट्सऐप, वाट्सऐप, व्हाट्सअप and व्हाट्सएप are
all "WhatsApp". Exact-spelling lists miss most of them, so instead each word is
reduced to its consonant skeleton (vowels, vowel signs, nuktas, viramas and joiners
dropped; aspirated and retroflex consonants folded) and matched against one pattern
per need. Unicode character names give the consonant in every script, so the same
pattern covers Devanagari, Tamil, Telugu, Kannada, Gujarati, Bengali, Malayalam and
Gurmukhi without a table per language.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

VOWEL_TOKENS = {"A", "AA", "I", "II", "U", "UU", "E", "EE", "AI", "O", "OO", "AU", "VOCALIC", "SHORT", "CANDRA", "LONG"}
PREFIX_TOKENS = {"CHILLU", "KHANDA"}  # Malayalam chillu letters, Bengali khanda ta: the consonant follows
FOLD = [  # longest first: retroflex/aspirated -> plain
    ("TTH", "T"), ("DDH", "D"), ("KH", "K"), ("GH", "G"), ("CH", "C"), ("JH", "J"), ("TT", "T"), ("DD", "D"),
    ("TH", "T"), ("DH", "D"), ("PH", "F"), ("BH", "B"), ("SH", "S"), ("SS", "S"), ("NN", "N"), ("NG", "N"),
    ("NY", "N"), ("LLL", "L"), ("LL", "L"), ("RRR", "R"), ("RR", "R"), ("YY", "Y"), ("W", "V"), ("Z", "J"),
]

# need -> skeleton pattern (searched inside each word's skeleton)
LOANWORDS: dict[str, str] = {
    "whatsapp": r"[vh]h?y?ts+y?p",        # वाट्सऐप वॉट्सएप व्हाट्सअप வாட்ஸ்அப் হোয়াটসঅ্যাপ ਵਟਸਐਪ
    "cctv": r"^s{1,2}t[vb]",              # सीसीटीवी সিসিটিভি (Bengali writes v as ভ), spaced: सी सी टी वी
    "website": r"v[bp](s|ss)a?[st]",      # वेबसाइट வெப்சைட் ওয়েবসাইট
    "internet": r"^(n?trn[ae]?t|n?nrnr)", # इंटरनेट ఇంటర్నెట్ ഇന്റർനെറ്റ്
    "backup": r"^[bp]y?k[ae]?p$",         # बैकअप பேக்கப் ব্যাকআপ
    "pos": r"^[bp]l+n?[gk]$",             # बिलिंग பில்லிங்
    "guest_wifi": r"^vy?[fp]y?$",         # वाईफाई வைஃபை ওয়াইফাই
    "mobile_lines": r"^m[bp][ae]?l$",     # मोबाइल மொபைல் মোবাইল
}


@lru_cache(maxsize=4096)
def _consonant(ch: str) -> str:
    name = unicodedata.name(ch, "")
    if " LETTER " not in name or ch.isascii():
        return ""
    tokens = name.split(" LETTER ", 1)[1].split()
    tok = tokens[0]
    if tok in PREFIX_TOKENS and len(tokens) > 1:
        tok = tokens[1]
    if tok in VOWEL_TOKENS:
        return ""
    if len(tok) > 1 and tok.endswith("A"):
        tok = tok[:-1]
    for a, b in FOLD:
        if tok == a:
            tok = b
            break
    return tok.lower()


def skeleton(word: str) -> str:
    """Consonant skeleton of an Indic-script word; '' for Latin words."""
    word = unicodedata.normalize("NFC", word)
    out: list[str] = []
    for ch in word:
        c = _consonant(ch)
        if c and (not out or out[-1] != c):  # doubled consonants (ट्ट, ப்ப) collapse
            out.append(c)
    return "".join(out)


def is_indic(word: str) -> bool:
    return any(0x0900 <= ord(ch) <= 0x0DFF or 0x0A00 <= ord(ch) <= 0x0A7F for ch in word)


def loanword_needs(text: str) -> set[str]:
    """Needs named by a loanword in an Indian script, whatever the spelling."""
    found: set[str] = set()
    words = [w for w in re.split(r"[\s,.;:!?।()\"'/-]+", text) if w and is_indic(w)]
    skels = [skeleton(w) for w in words]
    for need, pat in LOANWORDS.items():
        rx = re.compile(pat)
        if any(s and rx.search(s) for s in skels):
            found.add(need)
        # spaced spellings: "सी सी टी वी"
        elif need == "cctv" and rx.search("".join(skels)):
            found.add(need)
    return found
