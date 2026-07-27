import httpx
import json
from typing import Iterator

OLLAMA_BASE_URL = "http://localhost:11434"


def chat(model: str, messages: list, tools: list = None) -> dict:
    payload = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=300) as client:
        resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


def chat_stream(model: str, messages: list, tools: list = None) -> Iterator[dict]:
    payload = {"model": model, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=300) as client:
        with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    yield json.loads(line)


def list_models() -> list[str]:
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []
