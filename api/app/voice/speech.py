"""Speech in Indian languages: Sarvam speech-to-text and text-to-speech behind one adapter.

The API key stays on the server; the browser and WhatsApp send audio here. Without
SARVAM_API_KEY these return None and the web app falls back to the browser's own speech
(Web Speech API), so voice degrades instead of breaking. Every transcript is shown back
to the owner for confirmation before it changes an order.
"""
from __future__ import annotations

import base64
import json
import re
import logging
import threading
from collections import OrderedDict

import httpx

from ..config import get_settings

log = logging.getLogger("app.voice")
BASE = "https://api.sarvam.ai"
LOCALES = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN", "gu": "gu-IN",
           "bn": "bn-IN", "ml": "ml-IN", "pa": "pa-IN"}
FROM_LOCALE = {v: k for k, v in LOCALES.items()}
MAX_AUDIO_BYTES = 5 * 1024 * 1024
MAX_TTS_CHARS = 1500
TTS_MODEL = "bulbul:v3"  # bulbul:v2 was retired by Sarvam; v4-flash measured slower for our lines
STT_MODEL = "saaras:v4"  # Sarvam's current model: same 0.6 s as saarika:v2.5, and it takes key terms
# words owners say that a general model spells many ways: heard as written here, the extractor matches them directly
KEY_TERMS = ["Dukaan Connect", "Biz Fibre", "AirFiber", "broadband", "fibre", "leased line", "Wi-Fi", "SIM", "postpaid", "Mbps", "Gbps",
             "GST", "GSTIN", "Udyam", "UPI", "DigiLocker", "Aadhaar", "PAN", "WhatsApp", "CCTV", "POS", "static IP", "firewall",
             "SD-WAN", "toll-free", "cloud", "email", "kirana", "clinic", "CA firm"]
FORMATS = {"wav": "audio/wav", "mp3": "audio/mpeg"}  # a call takes mp3 at 16 kHz: a third of the bytes, measured no slower
CACHE_ITEMS, CACHE_CHARS = 120, 400  # greetings, prompts and fillers repeat across callers: synthesise each once
_cache: OrderedDict[tuple, bytes] = OrderedDict()
_cache_lock = threading.Lock()


def enabled() -> bool:
    return bool(get_settings().sarvam_api_key)


def _headers() -> dict:
    return {"api-subscription-key": get_settings().sarvam_api_key or ""}


def transcribe(audio: bytes | None, mime: str, language: str | None = None) -> dict | None:
    """Audio -> {"text", "language"}; language auto-detected when not given. None if unavailable."""
    if not enabled() or not audio or len(audio) > MAX_AUDIO_BYTES:
        return None
    try:
        r = httpx.post(f"{BASE}/speech-to-text", headers=_headers(), timeout=30,
                       files={"file": ("audio", audio, mime or "audio/webm")},
                       data={"model": STT_MODEL, "language_code": LOCALES.get(language or "", "unknown"), "keyterms": json.dumps(KEY_TERMS)})
        r.raise_for_status()
        body = r.json()
        text = (body.get("transcript") or "").strip()
        return {"text": text, "language": FROM_LOCALE.get(body.get("language_code") or "", language), "provider": "sarvam"}
    except (httpx.HTTPError, ValueError) as e:
        log.warning("sarvam stt failed: %s", e)
        return None


RUPEES = {"en": "rupees", "hi": "रुपये", "mr": "रुपये", "ta": "ரூபாய்", "te": "రూపాయలు", "kn": "ರೂಪಾಯಿ", "gu": "રૂપિયા",
          "bn": "টাকা", "ml": "രൂപ", "pa": "ਰੁਪਏ"}


def spoken(text: str, language: str) -> str:
    """Text as it should be heard: 'Rs 1,947' becomes '1947 rupees' in the owner's language; bullets and codes go."""
    word = RUPEES.get(language, RUPEES["en"])
    text = re.sub(r"(?:Rs\.?|₹)\s?([\d,]+(?:\.\d+)?)", lambda m: f"{m.group(1).replace(',', '')} {word}", text)
    text = re.sub(r"[•*#|_]+", " ", text)
    text = re.sub(r"\s*\n+\s*", ". ", text)
    return re.sub(r"\s{2,}", " ", text).strip(" .")


def speak(text: str, language: str, fmt: str = "wav") -> bytes | None:
    """Text -> audio bytes (wav, or mp3 at 16 kHz) in the owner's language. None if unavailable."""
    if not enabled() or not text.strip():
        return None
    key = (language, fmt, text.strip())
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    extra = {"speech_sample_rate": 16000, "output_audio_codec": "mp3"} if fmt == "mp3" else {}
    try:
        r = httpx.post(f"{BASE}/text-to-speech", headers=_headers(), timeout=30,
                       json={"text": spoken(text, language)[:MAX_TTS_CHARS], "target_language_code": LOCALES.get(language, "hi-IN"),
                             "model": TTS_MODEL, **extra})
        r.raise_for_status()
        audios = r.json().get("audios") or []
        audio = base64.b64decode(audios[0]) if audios else None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("sarvam tts failed: %s", e)
        return None
    if audio and len(key[2]) <= CACHE_CHARS:
        with _cache_lock:
            _cache[key] = audio
            while len(_cache) > CACHE_ITEMS:
                _cache.popitem(last=False)
    return audio
