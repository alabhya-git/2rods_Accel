"""Speech in Indian languages: Sarvam speech-to-text and text-to-speech behind one adapter.

The API key stays on the server; the browser and WhatsApp send audio here. Without
SARVAM_API_KEY these return None and the web app falls back to the browser's own speech
(Web Speech API), so voice degrades instead of breaking. Every transcript is shown back
to the owner for confirmation before it changes an order.
"""
from __future__ import annotations

import base64
import re
import logging

import httpx

from ..config import get_settings

log = logging.getLogger("app.voice")
BASE = "https://api.sarvam.ai"
LOCALES = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN", "gu": "gu-IN",
           "bn": "bn-IN", "ml": "ml-IN", "pa": "pa-IN"}
FROM_LOCALE = {v: k for k, v in LOCALES.items()}
MAX_AUDIO_BYTES = 5 * 1024 * 1024
MAX_TTS_CHARS = 1500
TTS_MODEL = "bulbul:v3"  # bulbul:v2 was retired by Sarvam
STT_MODEL = "saarika:v2.5"


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
                       data={"model": STT_MODEL, "language_code": LOCALES.get(language or "", "unknown")})
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


def speak(text: str, language: str) -> bytes | None:
    """Text -> WAV bytes in the owner's language. None if unavailable."""
    if not enabled() or not text.strip():
        return None
    try:
        r = httpx.post(f"{BASE}/text-to-speech", headers=_headers(), timeout=30,
                       json={"text": spoken(text, language)[:MAX_TTS_CHARS], "target_language_code": LOCALES.get(language, "hi-IN"),
                             "model": TTS_MODEL})
        r.raise_for_status()
        audios = r.json().get("audios") or []
        return base64.b64decode(audios[0]) if audios else None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("sarvam tts failed: %s", e)
        return None
