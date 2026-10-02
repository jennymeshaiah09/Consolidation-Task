"""Rank search phrases with TypeSafe Jev.

Jev is only used by the comparison page. It scores the same candidate keywords
as Clef and does not write new phrases.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from src.clef_rank import CLEF_QUESTION_LIMIT, build_noul_payload

JEV_MODEL = "jev-latest"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_QUESTION_LIMIT = CLEF_QUESTION_LIMIT


def typesafe_api_key(override: str = "") -> str:
    value = (override or os.getenv("TYPESAFE_API_KEY") or "").strip()
    if not value:
        raise ValueError("Add a Jev API key to compare. Paste it on the page or set TYPESAFE_API_KEY.")
    return value


def _post(payload: dict, api_key: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    delay = 1.0
    last_error = "Jev did not respond."
    for _ in range(3):
        request = urllib.request.Request(
            JEV_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            last_error = f"Jev returned {exc.code}. {detail}".strip()
            if exc.code not in {429, 529}:
                raise RuntimeError(last_error) from exc
            time.sleep(delay)
            delay *= 2
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach Jev. {exc.reason}") from exc
    raise RuntimeError(last_error)


def _answers(payload: dict) -> dict:
    error = payload.get("error")
    if isinstance(error, str) and error.strip():
        raise RuntimeError(f"Jev request failed. {error.strip()[:300]}")
    if isinstance(error, dict):
        message = str(error.get("message") or error.get("detail") or "Jev request failed.")
        raise RuntimeError(message[:400])
    answers = payload.get("answers")
    if isinstance(answers, dict):
        return answers
    raise RuntimeError("Jev did not return answers.")


def _noul_score(answer: object) -> float:
    if not isinstance(answer, dict):
        raise RuntimeError("Jev returned an answer without a noul score.")
    try:
        return float(answer.get("noul"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Jev returned an answer without a noul score.") from exc


def score_keyword_batch(batch: list[dict], api_key: str = "") -> dict:
    """Score one packed batch with jev-latest. The caller ranks a title only after every candidate is scored."""
    payload, mapping = build_noul_payload(batch, JEV_MODEL)
    if payload["model"] != JEV_MODEL:
        raise RuntimeError("Jev requests must use the jev-latest model.")
    if len(payload["questions"]) > JEV_QUESTION_LIMIT:
        raise RuntimeError(f"Jev comparison batches accept at most {JEV_QUESTION_LIMIT} questions per request.")
    request_bytes = len(json.dumps(payload).encode("utf-8"))
    raw = _post(payload, typesafe_api_key(api_key))
    answers = _answers(raw)
    scores = []
    for question_id, title, phrase in mapping:
        if question_id not in answers:
            raise RuntimeError("Jev omitted one or more answers.")
        scores.append({"title": title, "keyword": phrase, "score": _noul_score(answers[question_id])})
    return {"scores": scores, "response": raw, "request_bytes": request_bytes}
