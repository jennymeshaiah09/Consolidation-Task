"""Rank search phrases with Cloudflare Clef on Workers AI.

Clef does not write keywords. It returns a probability that a shopper would
type each phrase for the product. The caller sorts on that probability.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable

CLEF_MODEL = "clef"
CLEF_QUESTION_LIMIT = 64

_NOUL_CRITERIA = {
    "true": "A natural 2 to 4 word search for this product. It names what the shopper wants and is not only the title rewritten.",
    "false": "The title restated, a pack count, a retailer, or a search that would not find this product.",
}


def cloudflare_account_id(override: str = "") -> str:
    value = (override or os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if not value:
        raise ValueError("Add a Cloudflare account ID to rank with Clef. Paste it on the page or set CLOUDFLARE_ACCOUNT_ID.")
    return value


def cloudflare_api_token(override: str = "") -> str:
    value = (override or os.getenv("CLOUDFLARE_AUTH_TOKEN") or "").strip()
    if not value:
        raise ValueError("Add a Cloudflare API token to rank with Clef. Paste it on the page or set CLOUDFLARE_AUTH_TOKEN.")
    return value


def _post(payload: dict, account_id: str, api_token: str) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/cloudflare/clef"
    body = json.dumps(payload).encode("utf-8")
    delay = 1.0
    last_error = "Clef did not respond."
    for _ in range(3):
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            last_error = f"Clef returned {exc.code}. {detail}"
            if exc.code not in {429, 529}:
                raise RuntimeError(last_error) from exc
            time.sleep(delay)
            delay *= 2
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach Clef. {exc.reason}") from exc
    raise RuntimeError(last_error)


def _answers(payload: dict) -> dict:
    if payload.get("success") is False:
        errors = payload.get("errors") or []
        message = "Clef request failed."
        if errors and isinstance(errors[0], dict):
            message = str(errors[0].get("message") or message)
        raise RuntimeError(message)
    result = payload.get("result", payload)
    if isinstance(result, dict) and isinstance(result.get("answers"), dict):
        return result["answers"]
    if isinstance(result, dict) and isinstance(result.get("response"), dict):
        nested = result["response"].get("answers")
        if isinstance(nested, dict):
            return nested
    return {}


def rank_keywords(
    title: str,
    keywords: list[str],
    account_id: str = "",
    api_token: str = "",
) -> list[dict]:
    """Score each phrase with Clef, then return them best-first."""
    phrases = [phrase.strip() for phrase in keywords if phrase and phrase.strip()]
    if not phrases:
        return []

    state = {
        "title": title,
        "candidates": [{"keyword": phrase} for phrase in phrases],
    }
    questions = {
        f"c{index}": {
            "type": "noul",
            "instructions": (
                f"Would a shopper type `candidates[{index}].keyword` into Google "
                "to find the product in `title`, without already knowing that exact title?"
            ),
            "criteria": _NOUL_CRITERIA,
        }
        for index in range(len(phrases))
    }
    payload = _post(
        {"model": CLEF_MODEL, "state": state, "questions": questions},
        cloudflare_account_id(account_id),
        cloudflare_api_token(api_token),
    )
    answers = _answers(payload)

    scored: list[tuple[int, str, float]] = []
    for index, phrase in enumerate(phrases):
        answer = answers.get(f"c{index}") or {}
        try:
            score = float(answer.get("noul", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        scored.append((index, phrase, score))

    scored.sort(key=lambda item: (-item[2], item[0]))
    return [
        {"rank": place, "keyword": phrase, "score": round(score, 2)}
        for place, (_, phrase, score) in enumerate(scored, start=1)
    ]


def plan_clef_batches(groups: list[dict], limit: int = CLEF_QUESTION_LIMIT) -> list[list[dict]]:
    """Pack keyword questions into Clef requests of at most `limit` questions.

    Keywords for one title stay in the same request when they fit. A title with
    more than `limit` keywords is split into chunks, then those scores are
    ranked together by the caller.
    """
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_count = 0

    def flush() -> None:
        nonlocal current, current_count
        if current:
            batches.append(current)
            current = []
            current_count = 0

    for group in groups:
        title = str(group.get("title", "")).strip()
        keywords = [str(keyword).strip() for keyword in group.get("keywords", []) if str(keyword).strip()]
        if not title or not keywords:
            continue
        offset = 0
        while offset < len(keywords):
            remaining = len(keywords) - offset
            room = limit - current_count
            if current and remaining > room:
                flush()
                continue
            take = min(limit, remaining)
            current.append({"title": title, "keywords": keywords[offset : offset + take]})
            current_count += take
            offset += take
            if current_count >= limit:
                flush()
    flush()
    return batches


def build_noul_payload(batch: list[dict], model: str) -> tuple[dict, list[tuple[str, str, str]]]:
    """Build one ranking request. The model name is an argument so Jev can reuse the question shape."""
    products = []
    questions = {}
    mapping: list[tuple[str, str, str]] = []
    question_index = 0
    for product_index, group in enumerate(batch):
        products.append(
            {
                "title": group["title"],
                "candidates": [{"keyword": phrase} for phrase in group["keywords"]],
            }
        )
        for candidate_index, phrase in enumerate(group["keywords"]):
            question_id = f"c{question_index}"
            questions[question_id] = {
                "type": "noul",
                "instructions": (
                    f"Would a shopper type `products[{product_index}].candidates[{candidate_index}].keyword` "
                    f"into Google to find the product in `products[{product_index}].title`, "
                    "without already knowing that exact title?"
                ),
                "criteria": _NOUL_CRITERIA,
            }
            mapping.append((question_id, group["title"], phrase))
            question_index += 1
    payload = {"model": model, "state": {"products": products}, "questions": questions}
    return payload, mapping


def _batch_payload(batch: list[dict]) -> tuple[dict, list[tuple[str, str, str]]]:
    return build_noul_payload(batch, CLEF_MODEL)


def _noul_score(answer: object) -> float:
    if not isinstance(answer, dict):
        raise RuntimeError("Clef returned an answer without a noul score.")
    try:
        return float(answer.get("noul"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Clef returned an answer without a noul score.") from exc


def score_keyword_batch(batch: list[dict], account_id: str = "", api_token: str = "") -> dict:
    """Score one packed batch. Does not rank; the caller sorts after every chunk for a title arrives."""
    payload, mapping = _batch_payload(batch)
    if len(payload["questions"]) > CLEF_QUESTION_LIMIT:
        raise RuntimeError(f"Clef accepts at most {CLEF_QUESTION_LIMIT} questions per request.")
    request_bytes = len(json.dumps(payload).encode("utf-8"))
    raw = _post(payload, cloudflare_account_id(account_id), cloudflare_api_token(api_token))
    answers = _answers(raw)
    if not answers:
        raise RuntimeError("Clef did not return answers.")
    scores = []
    for question_id, title, phrase in mapping:
        if question_id not in answers:
            raise RuntimeError("Clef omitted one or more answers.")
        scores.append({"title": title, "keyword": phrase, "score": _noul_score(answers[question_id])})
    return {"scores": scores, "response": raw, "request_bytes": request_bytes}


def rank_keyword_groups(
    groups: list[dict],
    account_id: str = "",
    api_token: str = "",
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Score every keyword with Clef, in batches of 64, and rank within each title."""
    prepared = []
    for group in groups:
        title = str(group.get("title", "")).strip()
        keywords = [str(keyword).strip() for keyword in group.get("keywords", []) if str(keyword).strip()]
        if title and keywords:
            prepared.append({"title": title, "keywords": keywords})
    if not prepared:
        return []

    batches = plan_clef_batches(prepared)
    account = cloudflare_account_id(account_id)
    token = cloudflare_api_token(api_token)
    total = sum(len(group["keywords"]) for group in prepared)
    done = 0
    order: list[str] = []
    bucket: dict[str, list[tuple[int, str, float]]] = {}
    sequence = 0

    for batch in batches:
        payload, mapping = _batch_payload(batch)
        if len(payload["questions"]) > CLEF_QUESTION_LIMIT:
            raise RuntimeError(f"Clef accepts at most {CLEF_QUESTION_LIMIT} questions per request.")
        answers = _answers(_post(payload, account, token))
        for question_id, title, phrase in mapping:
            answer = answers.get(question_id) or {}
            try:
                score = float(answer.get("noul", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            if title not in bucket:
                order.append(title)
                bucket[title] = []
            bucket[title].append((sequence, phrase, score))
            sequence += 1
        done += sum(len(group["keywords"]) for group in batch)
        if on_progress:
            on_progress(done, total)

    ranked = []
    for title in order:
        rows = sorted(bucket[title], key=lambda item: (-item[2], item[0]))
        ranked.append(
            {
                "title": title,
                "keywords": [
                    {"rank": place, "keyword": phrase, "score": round(score, 2)}
                    for place, (_, phrase, score) in enumerate(rows, start=1)
                ],
            }
        )
    return ranked
