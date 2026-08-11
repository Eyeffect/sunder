"""LLM client: OpenAI-compatible transport + JSON parsing."""

import json

import httpx
import pytest

from sunder.gen.client import LLMClient, LLMError, _decode_body, _parse_json_content


def _sse_client():
    """
    Create a mock LLM client that emits a streamed JSON response.
    """
    def chunk(piece):
        data = json.dumps({"choices": [{"delta": {"content": piece}}]})
        return f"data: {data}\n"

    sse = (
        chunk('{"name":') + chunk('"Jazz"}') +
        "data: {\"id\":\"c\",\"object\":\"chat.completion.chunk\","
        "\"choices\":[{\"index\":0,\"delta\":{},\"finish_reason\":\"stop\"}]}\n"
        ": x-omniroute-cache-hit=false\n"
        "data: [DONE]\n"
    )

    def handler(request):
        return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

    return _client(handler)


def test_chat_json_parses_sse_stream():
    c = _sse_client()
    assert c.chat_json([{"role": "user", "content": "hi"}]) == {"name": "Jazz"}


def test_decode_body_plain_json():
    body = json.dumps({"choices": [{"message": {"content": "{\"ok\": 1}"}}]})
    assert _decode_body(body) == '{"ok": 1}'


def test_decode_body_sse_without_done():
    sse = 'data: {"choices":[{"delta":{"content":"a"}}]}\ndata: {"choices":[{"delta":{"content":"b"}}]}\n'
    assert _decode_body(sse) == "ab"


def _client(handler):
    """Create an LLM client using the supplied mock HTTP request handler.
    
    Parameters:
        handler: The mock request handler used by the client's transport.
    
    Returns:
        LLMClient: A client configured for the fake API endpoint and test model.
    """
    return LLMClient(base_url="http://fake/v1", model="m", timeout=1,
                     transport=httpx.MockTransport(handler))


def _resp(content):
    """Create a mock chat-completion handler that returns the specified message content."""
    def handler(request):
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["model"] == "m"
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content,
                                     "reasoning_content": "ignore me"}}],
        })
    return handler


def test_chat_json_parses_content():
    c = _client(_resp('{"name": "Jazz"}'))
    assert c.chat_json([{"role": "user", "content": "hi"}]) == {"name": "Jazz"}


def test_chat_json_strips_markdown_fence():
    c = _client(_resp('```json\n{"ok": true}\n```'))
    assert c.chat_json([{"role": "user", "content": "hi"}]) == {"ok": True}


def test_chat_json_returns_lists():
    c = _client(_resp('[{"name": "A"}, {"name": "B"}]'))
    assert c.chat_json([]) == [{"name": "A"}, {"name": "B"}]


def test_retries_then_raises_on_bad_content():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "not json"}}]})

    c = _client(handler)
    with pytest.raises(LLMError):
        c.chat_json([], attempts=3)
    assert calls["n"] == 3


def test_raises_on_http_error():
    c = _client(lambda req: httpx.Response(500, text="boom"))
    with pytest.raises(LLMError):
        c.chat_json([], attempts=1)


def test_available_true():
    c = _client(_resp('{"ok": true}'))
    assert c.available() is True


def test_available_false():
    c = _client(lambda req: httpx.Response(500))
    assert c.available() is False


def test_parse_json_content_edge_cases():
    assert _parse_json_content('{"a": 1}') == {"a": 1}
    assert _parse_json_content(' ```json\n{"b": 2}\n``` ') == {"b": 2}
