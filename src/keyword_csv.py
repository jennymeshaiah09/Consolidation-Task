"""Read a sheet of product titles and candidate keywords."""

from __future__ import annotations

from collections import OrderedDict
from io import BytesIO
from typing import Any

from src.clef_rank import plan_clef_batches

TITLE_PRIORITY = ("product title", "title", "product name")
KEYWORD_PRIORITY = (
    "product keyword",
    "search keyword",
    "keyword",
    "product keywords",
    "search keywords",
    "keywords",
)

MAX_CANDIDATE_ROWS = 5000
MAX_FILE_BYTES = 8 * 1024 * 1024


def normalize_header(value: object) -> str:
    text = str(value).replace("\ufeff", "").strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def _pick(columns: list[tuple[str, str]], priority: tuple[str, ...]) -> str | None:
    by_norm: dict[str, str] = {}
    for original, norm in columns:
        by_norm.setdefault(norm, original)
    for name in priority:
        if name in by_norm:
            return by_norm[name]
    return None


def detect_columns(columns: list[object]) -> tuple[str | None, str | None]:
    normalized = [(str(column), normalize_header(column)) for column in columns]
    title_col = _pick(normalized, TITLE_PRIORITY)
    keyword_col = _pick(normalized, KEYWORD_PRIORITY)
    if title_col and keyword_col and title_col == keyword_col:
        keyword_col = None
    return title_col, keyword_col


def _clean(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text


def group_candidate_rows(pairs: list[tuple[object, object]]) -> list[dict[str, Any]]:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    seen: dict[str, set[str]] = {}
    for raw_title, raw_keyword in pairs:
        title = _clean(raw_title)
        keyword = _clean(raw_keyword)
        if not title or not keyword:
            continue
        folded = keyword.casefold()
        seen_for_title = seen.setdefault(title, set())
        if folded in seen_for_title:
            continue
        seen_for_title.add(folded)
        grouped.setdefault(title, []).append(keyword)
    return [{"title": title, "keywords": keywords} for title, keywords in grouped.items()]


def _column_values(frame, column: str) -> list[str]:
    values = []
    for value in frame[column].tolist():
        text = _clean(value)
        if text:
            values.append(text)
    # Preserve order, drop duplicate titles.
    unique: list[str] = []
    seen: set[str] = set()
    for title in values:
        if title in seen:
            continue
        seen.add(title)
        unique.append(title)
    return unique


def parse_candidate_frame(frame) -> dict[str, Any]:
    if frame is None or getattr(frame, "empty", True):
        return {"error": "That file has no rows."}
    if len(frame) > 20000:
        return {"error": "This file has too many rows to rank at once. Split it under 5,000 candidate rows."}

    title_col, keyword_col = detect_columns(list(frame.columns))
    if title_col is None:
        return {"error": "Add a title column named title, Product Title, or product name."}
    if keyword_col is None:
        titles = _column_values(frame, title_col)
        if not titles:
            return {"error": "No product titles were found."}
        message = (
            "This file has titles but no keyword column. Generate new keywords for these titles, "
            "or add a keyword column (keyword, Product Keyword, or search keyword)."
        )
        if len(titles) > 500:
            message += f" The first 500 of {len(titles)} titles can be sent to Generate."
        return {"titles_only": True, "titles": titles[:500], "error": message}

    groups = group_candidate_rows(list(zip(frame[title_col].tolist(), frame[keyword_col].tolist())))
    keyword_count = sum(len(group["keywords"]) for group in groups)
    if keyword_count == 0:
        return {"error": "No rows had both a title and a keyword."}
    if keyword_count > MAX_CANDIDATE_ROWS:
        return {
            "error": (
                f"This file has {keyword_count} candidate keywords. "
                f"Rank up to {MAX_CANDIDATE_ROWS} at a time."
            ),
        }

    batches = plan_clef_batches(groups)
    return {
        "row_count": int(len(frame)),
        "title_count": len(groups),
        "keyword_count": keyword_count,
        "large": keyword_count > 64,
        "batch_count": len(batches),
        "batches": batches,
    }


def read_table(raw: bytes, filename: str):
    import pandas as pd

    name = (filename or "").lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(BytesIO(raw))
    # A single title column has nothing for a sniffer to latch onto, so pick the
    # separator from the header instead of guessing.
    sample = raw[:8192].decode("utf-8-sig", errors="replace")
    header = sample.splitlines()[0] if sample.splitlines() else ""
    if header.count(";") > header.count(",") and ";" in header:
        separator = ";"
    elif header.count("\t") > header.count(",") and "\t" in header:
        separator = "\t"
    else:
        separator = ","
    return pd.read_csv(BytesIO(raw), encoding="utf-8-sig", sep=separator)
