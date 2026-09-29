"""Compatibility wrapper around the current Google Gen AI SDK.

The app used to call ``google.generativeai``, which Google has retired.
Call sites still use ``configure``, ``GenerativeModel``, ``GenerationConfig``,
and ``response.text`` / ``response.parts``. This module keeps that surface
and sends the request through ``google.genai``.
"""

from google import genai
from google.genai import types


_client = None


def configure(api_key: str) -> None:
    """Store an API key for later ``GenerativeModel`` calls."""
    global _client
    _client = genai.Client(api_key=api_key)


class GenerationConfig:
    """Stand-in for the old ``genai.GenerationConfig`` constructor."""

    def __init__(
        self,
        temperature=None,
        max_output_tokens=None,
        response_mime_type=None,
        **extra,
    ):
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.response_mime_type = response_mime_type
        self.extra = extra


class _Part:
    def __init__(self, text: str):
        self.text = text


class _Response:
    """Expose ``.text``, ``.parts``, and ``.candidates`` like the old SDK."""

    def __init__(self, raw):
        self._raw = raw
        text = getattr(raw, "text", None) or ""
        self._text = text

        parts = []
        candidates = list(getattr(raw, "candidates", None) or [])
        try:
            if candidates and candidates[0].content and candidates[0].content.parts:
                for part in candidates[0].content.parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        parts.append(_Part(part_text))
        except Exception:
            parts = []

        if not parts and text:
            parts.append(_Part(text))

        self.parts = parts
        self.candidates = candidates

    @property
    def text(self) -> str:
        if not self._text:
            raise ValueError("The model returned an empty response")
        return self._text


def _config_kwargs(generation_config, safety_settings) -> dict:
    kwargs = {}
    if isinstance(generation_config, dict):
        kwargs.update(generation_config)
    elif isinstance(generation_config, GenerationConfig):
        if generation_config.temperature is not None:
            kwargs["temperature"] = generation_config.temperature
        if generation_config.max_output_tokens is not None:
            kwargs["max_output_tokens"] = generation_config.max_output_tokens
        if generation_config.response_mime_type is not None:
            kwargs["response_mime_type"] = generation_config.response_mime_type
        kwargs.update(generation_config.extra)

    if safety_settings:
        settings = []
        for item in safety_settings:
            if isinstance(item, dict):
                settings.append(
                    types.SafetySetting(
                        category=item["category"],
                        threshold=item["threshold"],
                    )
                )
            else:
                settings.append(item)
        kwargs["safety_settings"] = settings

    # Gemini 2.5 spends part of max_output_tokens on hidden thinking.
    # Keyword prompts need the whole budget for the actual answer.
    kwargs.setdefault("thinking_config", types.ThinkingConfig(thinking_budget=0))
    return kwargs


class GenerativeModel:
    """Stand-in for ``genai.GenerativeModel``."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate_content(self, prompt, generation_config=None, safety_settings=None):
        if _client is None:
            raise RuntimeError("Gemini client is not configured. Call configure(api_key) first.")

        kwargs = _config_kwargs(generation_config, safety_settings)
        try:
            raw = _client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )
        except Exception as exc:
            # Models that do not accept a thinking budget should still run.
            if "thinking" not in str(exc).lower() or "thinking_config" not in kwargs:
                raise
            kwargs.pop("thinking_config", None)
            raw = _client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs) if kwargs else None,
            )
        return _Response(raw)
