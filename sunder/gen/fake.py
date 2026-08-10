"""SUNDER — scriptable LLM double for hermetic tests and offline previews."""

from __future__ import annotations

import json
from typing import Callable


class FakeLLM:
    """Drop-in for `LLMClient`. Scripted responses are returned in order;

    a callback (receiving the request messages) can be used instead. Every
    call is recorded on `.calls`.
    """

    def __init__(self, responses: list | None = None,
                 on_call: Callable[[list[dict]], object] | None = None):
        self.responses = list(responses or [])
        self.on_call = on_call
        self.calls: list[list[dict]] = []
        self._index = 0

    def chat_json(self, messages: list[dict], **kwargs):
        self.calls.append(messages)
        if self.on_call is not None:
            content = self.on_call(messages)
        elif self._index < len(self.responses):
            content = self.responses[self._index]
            self._index += 1
        else:
            raise RuntimeError("FakeLLM: no more responses scripted")
        return content if isinstance(content, (dict, list)) else json.loads(content)

    def available(self) -> bool:
        return True
