"""Score the same candidate keywords with Jev and Clef, then compare their ranks.

A title is ranked only after both models have scored every candidate. Requests
stay within 64 questions. The two models for one batch run together, and nothing
else runs beside them.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.clef_rank import CLEF_QUESTION_LIMIT, score_keyword_batch as score_clef_batch
from src.clef_rank import cloudflare_account_id, cloudflare_api_token
from src.jev_rank import score_keyword_batch as score_jev_batch
from src.jev_rank import typesafe_api_key

JEV_USD_PER_MILLION_INPUT = 0.042
CLEF_USD_PER_MILLION_INPUT = 0.24
COMPARE_CONCURRENCY = 2
BATCH_LIMIT = CLEF_QUESTION_LIMIT

_TOKEN_KEYS = ("input_tokens", "prompt_tokens", "inputTokens", "promptTokens")


def read_input_tokens(payload: dict, request_bytes: int) -> tuple[int, bool]:
    """Return (input tokens, estimated). Published usage wins; otherwise estimate from the request body."""
    for usage in _usage_dicts(payload):
        for key in _TOKEN_KEYS:
            value = usage.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and value >= 0:
                return int(value), False
    return max(1, int(request_bytes) // 4), True


def _usage_dicts(payload: object) -> list[dict]:
    found: list[dict] = []
    if not isinstance(payload, dict):
        return found
    for key in ("usage", "token_usage"):
        usage = payload.get(key)
        if isinstance(usage, dict):
            found.append(usage)
    for key in ("result", "metadata", "response"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            found.extend(_usage_dicts(nested))
    return found


def model_cost(input_tokens: int, usd_per_million: float) -> float:
    return input_tokens / 1_000_000 * usd_per_million


def rank_side(pairs: list[tuple[str, float]]) -> list[dict]:
    """Highest score is rank 1. Equal scores keep the original candidate order."""
    ordered = list(enumerate(pairs))
    ordered.sort(key=lambda item: (-float(item[1][1]), item[0]))
    return [
        {"rank": place, "keyword": keyword, "score": round(float(score), 2)}
        for place, (_, (keyword, score)) in enumerate(ordered, start=1)
    ]


def title_winner(jev_best: dict, clef_best: dict) -> str:
    """same when both rank-1 keywords match. Otherwise the higher rank-1 score. Equal scores are labeled jev."""
    if str(jev_best.get("keyword", "")).casefold() == str(clef_best.get("keyword", "")).casefold():
        return "same"
    jev_score = float(jev_best.get("score", 0.0))
    clef_score = float(clef_best.get("score", 0.0))
    if clef_score > jev_score:
        return "clef"
    return "jev"


def assemble_comparison(rows: list[dict]) -> list[dict]:
    """Group scored rows by title, in first-seen order, and rank each model on its own."""
    order: list[str] = []
    bucket: dict[str, list[tuple[str, float, float]]] = {}
    for row in rows:
        title = str(row.get("title", "")).strip()
        keyword = str(row.get("keyword", "")).strip()
        if not title or not keyword:
            continue
        if title not in bucket:
            order.append(title)
            bucket[title] = []
        bucket[title].append((keyword, float(row.get("jev_score", 0.0)), float(row.get("clef_score", 0.0))))

    assembled = []
    for title in order:
        items = bucket[title]
        jev = rank_side([(keyword, jev_score) for keyword, jev_score, _ in items])
        clef = rank_side([(keyword, clef_score) for keyword, _, clef_score in items])
        winner = title_winner(jev[0], clef[0]) if jev and clef else "same"
        assembled.append(
            {
                "title": title,
                "jev": jev,
                "clef": clef,
                "winner": winner,
                "agree": winner == "same",
            }
        )
    return assembled


def comparison_summary(
    titles: list[dict],
    jev_tokens: int,
    clef_tokens: int,
    jev_estimated: bool,
    clef_estimated: bool,
) -> dict:
    compared = len(titles)
    same = sum(1 for title in titles if title.get("agree"))
    jev_scores = [float(item["score"]) for title in titles for item in title.get("jev", [])]
    clef_scores = [float(item["score"]) for title in titles for item in title.get("clef", [])]
    jev_cost = model_cost(jev_tokens, JEV_USD_PER_MILLION_INPUT)
    clef_cost = model_cost(clef_tokens, CLEF_USD_PER_MILLION_INPUT)
    return {
        "titles": compared,
        "same": same,
        "disagree": compared - same,
        "jev_average": (sum(jev_scores) / len(jev_scores)) if jev_scores else 0.0,
        "clef_average": (sum(clef_scores) / len(clef_scores)) if clef_scores else 0.0,
        "jev_input_tokens": jev_tokens,
        "clef_input_tokens": clef_tokens,
        "jev_cost": jev_cost,
        "clef_cost": clef_cost,
        "cost": jev_cost + clef_cost,
        "estimated": bool(jev_estimated or clef_estimated),
    }


def comparison_flat_rows(titles: list[dict]) -> list[dict]:
    """One CSV row per keyword. Winner is the title's rank-1 outcome on every row."""
    flat = []
    for title in titles:
        jev_by = {str(item["keyword"]).casefold(): item for item in title.get("jev", [])}
        clef_by = {str(item["keyword"]).casefold(): item for item in title.get("clef", [])}
        ordered: list[str] = []
        seen: set[str] = set()
        for item in sorted(title.get("jev", []), key=lambda row: int(row["rank"])):
            folded = str(item["keyword"]).casefold()
            if folded in seen:
                continue
            seen.add(folded)
            ordered.append(str(item["keyword"]))
        for item in sorted(title.get("clef", []), key=lambda row: int(row["rank"])):
            folded = str(item["keyword"]).casefold()
            if folded in seen:
                continue
            seen.add(folded)
            ordered.append(str(item["keyword"]))
        for keyword in ordered:
            jev = jev_by.get(keyword.casefold(), {})
            clef = clef_by.get(keyword.casefold(), {})
            flat.append(
                {
                    "title": title["title"],
                    "keyword": keyword,
                    "jev_rank": jev.get("rank", ""),
                    "jev_score": jev.get("score", ""),
                    "clef_rank": clef.get("rank", ""),
                    "clef_score": clef.get("score", ""),
                    "winner": title.get("winner", ""),
                }
            )
    return flat


def _label(name: str, exc: Exception) -> str:
    message = str(exc).strip() or f"{name} failed."
    if message.lower().startswith(name.lower()):
        return message
    return f"{name}: {message}"


def compare_batch(
    groups: list[dict],
    cloudflare_account_id_value: str = "",
    cloudflare_api_token_value: str = "",
    typesafe_api_key_value: str = "",
) -> dict:
    """Score one batch on both models. Raises before any network call when the batch or credentials are unusable."""
    prepared = []
    keyword_count = 0
    for group in groups:
        title = str(group.get("title", "")).strip()
        keywords = [str(phrase).strip() for phrase in group.get("keywords", []) if str(phrase).strip()]
        if not title or not keywords:
            continue
        prepared.append({"title": title, "keywords": keywords})
        keyword_count += len(keywords)
    if keyword_count == 0:
        raise ValueError("Add at least one keyword to rank.")
    if keyword_count > BATCH_LIMIT:
        raise ValueError(f"Send at most {BATCH_LIMIT} keywords per comparison batch.")

    problems: list[str] = []
    try:
        api_key = typesafe_api_key(typesafe_api_key_value)
    except ValueError as exc:
        problems.append(str(exc))
        api_key = ""
    try:
        account_id = cloudflare_account_id(cloudflare_account_id_value)
    except ValueError as exc:
        problems.append(str(exc))
        account_id = ""
    try:
        api_token = cloudflare_api_token(cloudflare_api_token_value)
    except ValueError as exc:
        problems.append(str(exc))
        api_token = ""
    if problems:
        raise ValueError(" ".join(problems))

    results: dict[str, dict] = {}
    errors: list[str] = []
    jobs = {
        "Jev": lambda: score_jev_batch(prepared, api_key),
        "Clef": lambda: score_clef_batch(prepared, account_id, api_token),
    }
    with ThreadPoolExecutor(max_workers=COMPARE_CONCURRENCY) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                errors.append(_label(name, exc))
    if errors:
        raise RuntimeError(" ".join(errors))

    jev_scores = results["Jev"]["scores"]
    clef_scores = results["Clef"]["scores"]
    if len(jev_scores) != len(clef_scores):
        raise RuntimeError("Jev and Clef returned different numbers of scores for the same candidates.")

    rows = []
    for jev_row, clef_row in zip(jev_scores, clef_scores):
        if jev_row["title"] != clef_row["title"] or jev_row["keyword"] != clef_row["keyword"]:
            raise RuntimeError("Jev and Clef scored the candidates in a different order.")
        rows.append(
            {
                "title": jev_row["title"],
                "keyword": jev_row["keyword"],
                "jev_score": jev_row["score"],
                "clef_score": clef_row["score"],
            }
        )

    jev_tokens, jev_estimated = read_input_tokens(results["Jev"]["response"], results["Jev"]["request_bytes"])
    clef_tokens, clef_estimated = read_input_tokens(results["Clef"]["response"], results["Clef"]["request_bytes"])
    return {
        "rows": rows,
        "usage": {
            "jev_input_tokens": jev_tokens,
            "clef_input_tokens": clef_tokens,
            "jev_estimated": jev_estimated,
            "clef_estimated": clef_estimated,
        },
    }
