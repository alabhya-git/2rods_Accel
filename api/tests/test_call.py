"""The AI call: the advisor in call mode, the voice adapter, and what the call screen relies on. No paid calls."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.advisor.agent import Advisor
from app.advisor.messages import M, t
from app.main import app
from app.security import LIMITS
from app.voice import speech

LANGS = ["en", "hi", "mr", "ta", "te", "kn", "gu", "bn", "ml", "pa"]
SHOP = {"en": "kirana shop in Jaipur, 3 people, no GST", "hi": "मेरी जयपुर में किराना दुकान है, तीन लोग काम करते हैं और GST नहीं है"}


def call(adv, *msgs, lang="en"):
    state = {"profile": {"language": lang}, "history": [], "language": lang, "lang_locked": True}
    turn = None
    for m in msgs:
        turn, state = adv.respond(state, m, voice=True)
    return turn, state


class NoModel:
    """The call's yes, and its rules-only turns, must never reach a model."""
    provider, model = "fake", "fake-1"

    def run(self, *a, **kw):
        raise AssertionError("the model was called")


@pytest.mark.parametrize("lang", LANGS)
def test_the_plan_is_said_in_a_few_sentences_in_every_language(lang):
    turn, _ = call(Advisor(use_llm=False), SHOP.get(lang, SHOP["en"]), lang=lang)
    assert turn.stage == "recommended"
    assert "\n" not in turn.text and "•" not in turn.text and "->" not in turn.text  # heard, not read
    assert turn.bundle["name"] in turn.text and turn.text.endswith(t("call_plan_ask", lang))
    assert len(turn.text) < 600


@pytest.mark.parametrize("yes", ["हाँ", "ठीक है, आगे बढ़िए", "go ahead", "yes"])
def test_a_plain_yes_to_the_plan_is_accepted_without_a_model(yes):
    _, state = call(Advisor(use_llm=False), SHOP["hi"], lang="hi")
    turn, after = Advisor(llm=NoModel()).respond(state, yes, voice=True)
    assert turn.stage == "accepted" and turn.bundle == state["bundle"] and turn.text == t("call_accept", "hi")


@pytest.mark.parametrize("change", ["हाँ लेकिन सस्ता करो", "yes but add CCTV", "no, remove the SIMs", "ok, make it 24 months"])
def test_a_yes_with_a_change_is_a_change(change):
    _, state = call(Advisor(use_llm=False), SHOP["hi"], lang="hi")
    turn, _ = Advisor(use_llm=False).respond(state, change, voice=True)
    assert turn.stage != "accepted"


def test_every_go_ahead_button_on_the_call_screen_is_a_yes():
    """The plan card's button sends its own label: the server must take it as a yes in all 10 languages."""
    src = (Path(__file__).resolve().parents[2] / "web" / "src" / "i18n" / "call.ts").read_text(encoding="utf-8")
    labels = re.findall(r"call_go_ahead: '([^']+)'", src)
    assert len(labels) == 10
    for lang, label in zip(LANGS, labels):
        _, state = call(Advisor(use_llm=False), SHOP.get(lang, SHOP["en"]), lang=lang)
        turn, _ = Advisor(llm=NoModel()).respond(state, label, voice=True)
        assert turn.stage == "accepted", (lang, label)


def test_chat_has_no_accepted_stage():
    _, state = call(Advisor(use_llm=False), SHOP["en"])
    turn, _ = Advisor(use_llm=False).respond(state, "yes")  # not a call: the chat recommends again, the quote page takes over
    assert turn.stage == "recommended"


class CallModel:
    provider, model = "fake", "fake-1"

    def __init__(self):
        self.stop_after, self.context = None, None

    def run(self, system, history, tools, execute, max_steps=5, context=None, stop_after=frozenset()):
        self.stop_after, self.context = stop_after, context
        execute("update_profile", {"business_type": "Dental clinic", "segment": "prof", "employees": 4, "city": "Pune", "has_gstin": True})
        execute("recommend", {})
        return "", [{"tool": "update_profile"}, {"tool": "recommend"}]


def test_on_a_call_the_loop_ends_at_recommend_and_the_server_says_the_plan():
    model = CallModel()
    turn, _ = call(Advisor(llm=model), "dental clinic in Pune, 4 people, we have GST")
    assert model.stop_after == frozenset({"recommend"}) and "[Phone call]" in model.context
    assert turn.stage == "recommended" and turn.llm_used and turn.guard["passed"]
    assert turn.text.startswith(t("bundle_intro", "en", name=turn.bundle["name"], monthly=f"Rs {turn.bundle['monthly']:,}", days=turn.bundle["install_days"]))


def test_a_spoken_question_from_the_model_still_passes_the_guard():
    class Asks(CallModel):
        def run(self, system, history, tools, execute, max_steps=5, context=None, stop_after=frozenset()):
            execute("update_profile", {"business_type": "Dental clinic", "segment": "prof"})
            return "Which city is the clinic in? It's free and guaranteed!", []
    turn, _ = call(Advisor(llm=Asks()), "I have a dental clinic")
    assert not turn.guard["passed"] and "guaranteed" not in turn.text  # the template question replaces it


def test_a_call_session_is_marked_and_greets_as_an_ai():
    with TestClient(app) as c:
        s = c.post("/api/advisor/sessions", json={"language": "ta", "channel": "voice"}).json()
        assert s["channel"] == "voice" and s["messages"][0]["text"] == M["call_greet"]["ta"]
        assert c.get("/api/advisor/greeting?language=ta&channel=voice").json()["text"] == M["call_greet"]["ta"]
        assert c.get("/api/advisor/greeting?language=xx").json()["text"] == M["greet"]["en"]
        turn = c.post(f"/api/advisor/sessions/{s['session_id']}/messages", json={"text": SHOP["en"], "language": "en"}).json()["turn"]
        assert turn["stage"] == "recommended" and "\n" not in turn["text"]


@pytest.mark.parametrize("key", ["call_greet", "call_includes", "call_see_card", "call_plan_ask", "call_accept"])
def test_call_lines_exist_in_every_language(key):
    assert set(M[key]) == set(LANGS) and all("AI" in M[key][l] for l in LANGS if key == "call_greet")


class Sarvam:
    def __init__(self, body):
        self.calls, self.body = [], body

    def __call__(self, url, **kw):
        self.calls.append((url, kw))
        body = self.body

        class R:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return body
        return R()


def test_speech_is_cached_and_a_call_gets_small_mp3(monkeypatch):
    fake = Sarvam({"audios": ["SUQz"]})  # "ID3"
    monkeypatch.setattr(speech, "enabled", lambda: True)
    monkeypatch.setattr(speech.httpx, "post", fake)
    speech._cache.clear()
    assert speech.speak("एक पल।", "hi", "mp3") == b"ID3"
    assert speech.speak("एक पल।", "hi", "mp3") == b"ID3"
    assert len(fake.calls) == 1  # said once, then from the cache
    body = fake.calls[0][1]["json"]
    assert body["output_audio_codec"] == "mp3" and body["speech_sample_rate"] == 16000
    speech.speak("एक पल।", "hi")  # the WAV for WhatsApp and read-aloud is its own entry
    assert len(fake.calls) == 2 and "output_audio_codec" not in fake.calls[1][1]["json"]


def test_long_lines_are_not_cached(monkeypatch):
    fake = Sarvam({"audios": ["SUQz"]})
    monkeypatch.setattr(speech, "enabled", lambda: True)
    monkeypatch.setattr(speech.httpx, "post", fake)
    speech._cache.clear()
    long = "word " * 100
    speech.speak(long, "en", "mp3")
    speech.speak(long, "en", "mp3")
    assert len(fake.calls) == 2


def test_hearing_uses_the_current_model_and_the_key_terms(monkeypatch):
    fake = Sarvam({"transcript": "मेरी जयपुर में किराना दुकान है", "language_code": "hi-IN"})
    monkeypatch.setattr(speech, "enabled", lambda: True)
    monkeypatch.setattr(speech.httpx, "post", fake)
    out = speech.transcribe(b"RIFF....", "audio/wav", "hi")
    data = fake.calls[0][1]["data"]
    assert out["text"].startswith("मेरी") and data["model"] == "saaras:v4" and data["language_code"] == "hi-IN"
    assert "Udyam" in json.loads(data["keyterms"]) and len(json.loads(data["keyterms"])) <= 50


def test_the_speak_endpoint_returns_mp3_for_a_call(monkeypatch):
    monkeypatch.setattr(speech, "enabled", lambda: True)
    monkeypatch.setattr(speech, "speak", lambda text, lang, fmt="wav": b"ID3" if fmt == "mp3" else b"RIFF")
    with TestClient(app) as c:
        r = c.post("/api/voice/speak", json={"text": "One moment.", "language": "en", "format": "mp3"})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and r.content == b"ID3"
        assert c.post("/api/voice/speak", json={"text": "x", "language": "en", "format": "ogg"}).status_code == 422


def test_spoken_audio_is_rate_limited_both_ways():
    voice = [(m, b) for m, test, b, *_ in LIMITS if b == "voice"]
    assert ("GET", "voice") in voice and ("POST", "voice") in voice
