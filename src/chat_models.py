"""Chat completions for keyword generation across Gemini, OpenAI, and Claude."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

MODEL_OPTIONS = {
    "Gemini": [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ],
    "OpenAI": [
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4o-mini",
    ],
    "Claude": [
        "claude-haiku-4-5",
        "claude-sonnet-4-5",
        "claude-opus-4-1",
    ],
}


def provider_api_key(provider: str) -> str | None:
    """Key for the selected provider: sidebar session value, then environment."""
    provider = provider or "Gemini"
    env_names = {
        "Gemini": "GOOGLE_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Claude": "ANTHROPIC_API_KEY",
    }
    session_names = {
        "Gemini": "user_api_key",
        "OpenAI": "user_openai_api_key",
        "Claude": "user_anthropic_api_key",
    }
    value = None
    try:
        import streamlit as st
        value = st.session_state.get(session_names[provider])
    except Exception:
        value = None
    if provider == "Gemini" and not (isinstance(value, str) and value.strip()):
        from . import get_google_api_key
        value = get_google_api_key()
    if not (isinstance(value, str) and value.strip()):
        value = os.getenv(env_names[provider])
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def complete_text(provider: str, model: str, prompt: str) -> str:
    """Send one prompt and return the model's text. Raises on HTTP errors."""
    api_key = provider_api_key(provider)
    if not api_key:
        raise ValueError(f"Add a {provider} API key before generating keywords.")

    if provider == "Gemini":
        from .gemini_client import configure, GenerativeModel

        configure(api_key)
        response = GenerativeModel(model).generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json",
            },
        )
        return response.text

    if provider == "OpenAI":
        payload = {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Return only JSON."},
                {"role": "user", "content": prompt},
            ],
        }
        raw = _post_json(
            "https://api.openai.com/v1/chat/completions",
            payload,
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        return raw["choices"][0]["message"]["content"]

    if provider == "Claude":
        payload = {
            "model": model,
            "max_tokens": 8192,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        }
        raw = _post_json(
            "https://api.anthropic.com/v1/messages",
            payload,
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        parts = raw.get("content") or []
        texts = [part.get("text", "") for part in parts if part.get("type") == "text"]
        return "\n".join(texts).strip()

    raise ValueError(f"Unsupported provider: {provider}")


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        host = urllib.parse.urlparse(url).hostname or url
        raise RuntimeError(f"Could not reach {host}. {exc.reason}") from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 429:
            raise RuntimeError("API quota exceeded") from exc
        raise RuntimeError(f"{exc.code}: {detail}") from exc
