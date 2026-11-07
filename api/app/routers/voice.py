"""Voice for the web app: the browser sends audio here so the speech key never leaves the server."""
from __future__ import annotations

import time

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..voice import speech

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/status")
def status():
    return {"server_speech": speech.enabled(), "fallback": "browser Web Speech API", "languages": sorted(speech.LOCALES)}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str | None = Form(default=None)):
    data = await audio.read()
    if len(data) > speech.MAX_AUDIO_BYTES:
        raise HTTPException(413, "Voice note too long")
    if not speech.enabled():
        raise HTTPException(503, "server speech is off; use the browser's speech")
    t0 = time.perf_counter()
    out = await run_in_threadpool(speech.transcribe, data, audio.content_type or "audio/webm", language)
    if not out:
        raise HTTPException(502, "Could not hear that. Please try again or type.")
    return {**out, "ms": round((time.perf_counter() - t0) * 1000)}


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=speech.MAX_TTS_CHARS)
    language: str = "hi"
    format: str = Field(default="wav", pattern="^(wav|mp3)$")


@router.get("/speak")
async def speak_stream(text: str = Query(min_length=1, max_length=speech.MAX_TTS_CHARS), language: str = "hi"):
    """GET so an <audio> element can start it inside the owner's tap (browsers block audio started later)."""
    return await speak(SpeakIn(text=text, language=language))


@router.post("/speak")
async def speak(body: SpeakIn):
    if not speech.enabled():
        raise HTTPException(503, "server speech is off; use the browser's voice")
    audio = await run_in_threadpool(speech.speak, body.text, body.language, body.format)
    if not audio:
        raise HTTPException(502, "speech service unavailable")
    return Response(audio, media_type=speech.FORMATS[body.format], headers={"Cache-Control": "private, max-age=3600"})
