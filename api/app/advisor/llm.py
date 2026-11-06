"""Provider-neutral tool-calling loop. Each adapter keeps the provider's native message
format internally (so thinking blocks / thought signatures are passed back intact),
and exposes one call: run(system, history, tools, execute) -> (text, calls).

LLM_PROVIDER = anthropic | gemini | openai (any OpenAI-compatible endpoint) | none
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from ..config import get_settings

log = logging.getLogger("app.llm")

DEFAULT_MODELS = {
    "anthropic": "claude-opus-5-5",
    "gemini": "gemini-flash-latest",
    "openai": "gpt-4o-mini",
}


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict


Executor = Callable[[str, dict], Any]


class LLMError(RuntimeError):
    pass


class _Base:
    provider = "none"

    def __init__(self, api_key: str, model: str, timeout: float, base_url: str | None = None):
        self.api_key, self.model, self.timeout, self.base_url = api_key, model, timeout, base_url

    def run(self, system: str, history: list[dict], tools: list[Tool], execute: Executor, max_steps: int = 5,
            context: str | None = None) -> tuple[str, list[dict]]:
        raise NotImplementedError


class Anthropic(_Base):
    """Claude through the official SDK. The system prompt and tool list are frozen so the
    prefix caches; the per-turn context (profile, language) rides in the last user turn.
    Thinking blocks are passed back unchanged inside the tool loop."""
    provider = "anthropic"
    effort = "low"  # chat turns: fast, cheap; raise only if the eval shows headroom

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        import anthropic
        self._sdk = anthropic
        self.client = anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url or None, timeout=self.timeout, max_retries=1)
        self.usage: dict = {}

    def run(self, system, history, tools, execute, max_steps=5, context: str | None = None):
        messages: list[dict] = [{"role": "user" if h["role"] == "user" else "assistant", "content": h["text"]} for h in history]
        if context and messages and messages[-1]["role"] == "user":  # volatile facts after the cached prefix
            messages[-1] = {"role": "user", "content": [{"type": "text", "text": messages[-1]["content"]},
                                                        {"type": "text", "text": context}]}
        spec = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]
        calls: list[dict] = []
        sdk = self._sdk
        for _ in range(max_steps):
            try:
                resp = self.client.beta.messages.create(
                    model=self.model, max_tokens=4096, system=system, messages=messages, tools=spec,
                    output_config={"effort": self.effort}, cache_control={"type": "ephemeral"},
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            except sdk.APIStatusError as e:
                raise LLMError(f"anthropic {e.status_code}: {str(e)[:200]}") from e
            except sdk.APIConnectionError as e:
                raise LLMError(f"anthropic connection: {e}") from e
            u = resp.usage
            self.usage = {"input": u.input_tokens, "output": u.output_tokens,
                          "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                          "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0}
            if resp.stop_reason == "refusal":
                raise LLMError("refused")
            uses = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not uses:
                return "".join(b.text for b in resp.content if b.type == "text").strip(), calls
            messages.append({"role": "assistant", "content": resp.content})  # thinking blocks kept as-is
            results = []
            for b in uses:
                args = b.input if isinstance(b.input, dict) else {}
                out = execute(b.name, dict(args))
                calls.append({"tool": b.name, "args": args})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
        raise LLMError("too many tool steps")


class Gemini(_Base):
    provider = "gemini"

    def run(self, system, history, tools, execute, max_steps=5, context=None):
        if context and history:
            history = history[:-1] + [{**history[-1], "text": history[-1]["text"] + "\n" + context}]
        base = self.base_url or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base}/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key, "content-type": "application/json"}
        contents = [{"role": "user" if h["role"] == "user" else "model", "parts": [{"text": h["text"]}]} for h in history]
        decl = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in tools]
        calls: list[dict] = []
        with httpx.Client(timeout=self.timeout) as c:
            for _ in range(max_steps):
                r = c.post(url, headers=headers, json={"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                                                        "tools": [{"functionDeclarations": decl}]})
                if r.status_code >= 400:
                    raise LLMError(f"gemini {r.status_code}: {r.text[:300]}")
                cand = (r.json().get("candidates") or [{}])[0]
                content = cand.get("content") or {"role": "model", "parts": []}
                parts = content.get("parts") or []
                fcalls = [p["functionCall"] for p in parts if "functionCall" in p]
                if not fcalls:
                    return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip(), calls
                contents.append(content)  # keeps thought signatures
                responses = []
                for fc in fcalls:
                    out = execute(fc["name"], fc.get("args") or {})
                    calls.append({"tool": fc["name"], "args": fc.get("args") or {}})
                    responses.append({"functionResponse": {"name": fc["name"], "response": {"result": out}}})
                contents.append({"role": "user", "parts": responses})
        raise LLMError("too many tool steps")


class OpenAICompatible(_Base):
    provider = "openai"

    def run(self, system, history, tools, execute, max_steps=5, context=None):
        if context and history:
            history = history[:-1] + [{**history[-1], "text": history[-1]["text"] + "\n" + context}]
        url = (self.base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        headers = {"authorization": f"Bearer {self.api_key}", "content-type": "application/json"}
        messages: list[dict] = [{"role": "system", "content": system}]
        messages += [{"role": "user" if h["role"] == "user" else "assistant", "content": h["text"]} for h in history]
        spec = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]
        calls: list[dict] = []
        with httpx.Client(timeout=self.timeout) as c:
            for _ in range(max_steps):
                r = c.post(url, headers=headers, json={"model": self.model, "messages": messages, "tools": spec})
                if r.status_code >= 400:
                    raise LLMError(f"openai {r.status_code}: {r.text[:300]}")
                msg = r.json()["choices"][0]["message"]
                tcs = msg.get("tool_calls") or []
                if not tcs:
                    return (msg.get("content") or "").strip(), calls
                messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": tcs})
                for tc in tcs:
                    try:
                        args = json.loads(tc["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    out = execute(tc["function"]["name"], args)
                    calls.append({"tool": tc["function"]["name"], "args": args})
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out, ensure_ascii=False)})
        raise LLMError("too many tool steps")


ADAPTERS = {"anthropic": Anthropic, "gemini": Gemini, "openai": OpenAICompatible}


def get_llm() -> _Base | None:
    s = get_settings()
    if s.llm_provider not in ADAPTERS or not s.llm_api_key:
        return None
    return ADAPTERS[s.llm_provider](s.llm_api_key, s.llm_model or DEFAULT_MODELS[s.llm_provider], s.llm_timeout_s, s.llm_base_url)
