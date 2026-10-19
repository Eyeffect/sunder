"""SUNDER — LLM client (OpenAI-compatible chat completions).

Talks to any OpenAI-compatible endpoint. The default is the local OmniRoute
gateway (no key required) so generation costs nothing. Some gateways attach
an extra `reasoning_content` field to the message; it is ignored — we only
read `message.content`, then parse the JSON inside.

OmniRoute streams the response as server-sent events even when `stream` is
false, so the client decodes both SSE (`data:` lines with `delta.content`)
and plain JSON bodies.
"""

from __future__ import annotations

import json
import os

import httpx

DEFAULT_BASE_URL = os.environ.get("SUNDER_LLM_BASE_URL", "http://127.0.0.1:20128/v1")
DEFAULT_MODEL = os.environ.get("SUNDER_LLM_MODEL", "oc/big-pickle")

try:
    DEFAULT_TIMEOUT = float(os.environ.get("SUNDER_LLM_TIMEOUT", "120"))
except ValueError:
    DEFAULT_TIMEOUT = 120.0


class LLMError(RuntimeError):
    """Raised when the LLM is unreachable or returns unusable content."""


class LLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 api_key: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.api_key = api_key or os.environ.get("SUNDER_LLM_API_KEY") or None
        self.timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        self._transport = transport

    def chat_json(self, messages: list[dict], *, temperature: float = 0.9,
                  max_tokens: int = 24000, attempts: int = 2,
                  timeout: float | None = None):
        """POST a chat completion and return the parsed JSON from content.

        `timeout` overrides the client-wide timeout for this one call (used
        for short-lived fallback re-probes).
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        last: Exception | None = None
        for _ in range(max(1, attempts)):
            try:
                with httpx.Client(timeout=self.timeout if timeout is None
                                  else timeout, transport=self._transport) as http:
                    resp = http.post(f"{self.base_url}/chat/completions",
                                     headers=headers, json=body)
                    resp.raise_for_status()
                content = _decode_body(resp.text)
                return _parse_json_content(content)
            except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
                last = LLMError(f"LLM request failed: {exc}")
            except json.JSONDecodeError as exc:
                last = LLMError(f"LLM returned unusable content: {exc}")
        if last is None:
            raise LLMError("LLM request loop did not run")
        raise last

    def available(self) -> bool:
        try:
            self.chat_json(
                [{"role": "user", "content": 'Reply with exactly: {"ok": true}'}],
                temperature=0.0, max_tokens=32,
            )
            return True
        except LLMError:
            return False


def _decode_body(text: str) -> str:
    """Return the message content from an SSE or plain JSON chat response."""
    text = text.strip()
    if not text.startswith("data:"):
        data = json.loads(text)
        return data["choices"][0]["message"]["content"]
    parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        chunk = json.loads(payload)
        delta = chunk["choices"][0].get("delta", {})
        parts.append(delta.get("content") or "")
    return "".join(parts)


def _parse_json_content(content: str):
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
