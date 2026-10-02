"""HTTP API for the Meridian Next.js UI.

The Streamlit pages stay in place. This server exposes the same Python
pipeline so the new interface can generate keywords, verify them, and
consolidate a monthly catalog.
"""

from __future__ import annotations

import os
import sys
import threading
from io import BytesIO
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from src.chat_models import MODEL_OPTIONS, complete_text  # noqa: E402
from src.consolidation import consolidate_data, resolve_snapshot_month  # noqa: E402
from src.ingestion import get_month_order, load_monthly_data  # noqa: E402
from src.llm_keywords import generate_keywords_batch  # noqa: E402
from src.rake_keywords import generate_keywords_rake  # noqa: E402
from src.validation import apply_column_mapping, guess_column_mapping  # noqa: E402

app = FastAPI(title="Meridian")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_lock = threading.Lock()
_ENV = {
    "Gemini": "GOOGLE_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Claude": "ANTHROPIC_API_KEY",
}


class TitleIn(BaseModel):
    title: str
    brand: str = ""


class GenerateIn(BaseModel):
    titles: list[TitleIn]
    method: str = "rake"
    provider: str = "Gemini"
    model: str = "gemini-2.5-flash-lite"
    product_type: str = "General"
    gemini_key: str = ""
    openai_key: str = ""
    anthropic_key: str = ""
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""


class VerifyIn(BaseModel):
    title: str
    keyword: str
    provider: str = "Gemini"
    model: str = "gemini-2.5-flash-lite"
    gemini_key: str = ""
    openai_key: str = ""
    anthropic_key: str = ""


class RankGroup(BaseModel):
    title: str
    keywords: list[str]


class RankIn(BaseModel):
    groups: list[RankGroup]
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""


class CompareIn(BaseModel):
    groups: list[RankGroup]
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    typesafe_api_key: str = ""


def _redact(message: str, secrets: list[str]) -> str:
    import re

    text = message
    values = list(secrets)
    for name in ("TYPESAFE_API_KEY", "CLOUDFLARE_AUTH_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        values.append(os.getenv(name) or "")
    for secret in values:
        cleaned = (secret or "").strip()
        if len(cleaned) >= 6:
            text = text.replace(cleaned, "[redacted]")
    return re.sub(r"Bearer\s+\S+", "Bearer [redacted]", text)


def _keys(body: GenerateIn | VerifyIn) -> dict[str, str]:
    return {
        "Gemini": body.gemini_key,
        "OpenAI": body.openai_key,
        "Claude": body.anthropic_key,
    }


def _with_keys(keys: dict[str, str], fn):
    with _lock:
        previous = {env: os.environ.get(env) for env in _ENV.values()}
        for provider, env in _ENV.items():
            value = (keys.get(provider) or "").strip()
            if value:
                os.environ[env] = value
        try:
            return fn()
        finally:
            for env, old in previous.items():
                if old is None:
                    os.environ.pop(env, None)
                else:
                    os.environ[env] = old


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/models")
def models() -> dict[str, list[str]]:
    return MODEL_OPTIONS


@app.get("/api/sample")
def sample_catalog() -> Response:
    from utils.sample_data import build_sample_catalog_zip

    return Response(
        content=build_sample_catalog_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="meridian-sample-catalog.zip"'},
    )


def _titles_from_table(frame) -> list[str]:
    import pandas as pd

    if frame is None or frame.empty:
        return []
    columns = [str(col) for col in frame.columns]
    preferred = next(
        (col for col in columns if col.strip().lower() in {"product title", "title", "product name", "name"}),
        columns[0],
    )
    values = frame[preferred].dropna().astype(str).str.strip()
    return [value for value in values.tolist() if value and value.lower() != "nan"]


@app.post("/api/titles")
async def extract_titles(file: UploadFile = File(...)) -> dict[str, Any]:
    import pandas as pd

    raw = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".xlsx") or name.endswith(".xls"):
            frame = pd.read_excel(BytesIO(raw))
        else:
            frame = pd.read_csv(BytesIO(raw))
    except Exception as exc:
        return {"error": f"Could not read that file. {exc}"}
    titles = _titles_from_table(frame)
    if not titles:
        return {"error": "No product titles were found."}
    return {"titles": titles[:500]}


@app.post("/api/keywords")
def keywords(body: GenerateIn) -> dict[str, Any]:
    import pandas as pd

    rows = [item for item in body.titles if item.title.strip()]
    if not rows:
        return {"error": "Add at least one product title."}
    frame = pd.DataFrame(
        [{"Product Title": item.title.strip(), "Product Brand": item.brand.strip()} for item in rows]
    )

    def run():
        if body.method == "llm":
            from src.clef_rank import rank_keywords
            from src.llm_keywords import generate_keyword_options

            titles = [item.title.strip() for item in rows]
            brands = [item.brand.strip() for item in rows]
            options = generate_keyword_options(
                titles,
                brands,
                provider=body.provider,
                model_name=body.model,
            )
            groups = []
            for title, brand, phrases in zip(titles, brands, options):
                ranked = rank_keywords(title, phrases, body.cloudflare_account_id, body.cloudflare_api_token)
                groups.append({"title": title, "brand": brand, "keywords": ranked})
            return groups
        result = generate_keywords_rake(frame)
        return [
            {
                "title": str(row.get("Product Title", "")),
                "brand": str(row.get("Product Brand", "")),
                "keywords": [{"rank": 1, "keyword": str(row.get("Product Keyword", "")), "score": None}],
            }
            for _, row in result.iterrows()
        ]

    try:
        groups = _with_keys(_keys(body), run)
    except Exception as exc:
        return {"error": str(exc)}

    return {"groups": groups, "method": body.method, "provider": body.provider, "model": body.model}


@app.post("/api/keywords/candidates")
async def keyword_candidates(file: UploadFile = File(...)) -> dict[str, Any]:
    from src.keyword_csv import MAX_FILE_BYTES, parse_candidate_frame, read_table

    raw = await file.read()
    if len(raw) > MAX_FILE_BYTES:
        return {"error": "That file is over 8 MB. Split it and rank a smaller CSV."}
    if not raw:
        return {"error": "That file is empty."}
    try:
        frame = read_table(raw, file.filename or "")
    except Exception as exc:
        return {"error": f"Could not read that file. {exc}"}
    try:
        return parse_candidate_frame(frame)
    except Exception as exc:
        return {"error": f"Could not read that file. {exc}"}


@app.post("/api/keywords/rank")
def rank_existing(body: RankIn) -> dict[str, Any]:
    from src.clef_rank import CLEF_QUESTION_LIMIT, rank_keyword_groups

    prepared = []
    keyword_count = 0
    for group in body.groups:
        title = group.title.strip()
        keywords = [phrase.strip() for phrase in group.keywords if phrase and phrase.strip()]
        if not title or not keywords:
            continue
        prepared.append({"title": title, "keywords": keywords})
        keyword_count += len(keywords)
    if keyword_count == 0:
        return {"error": "Add at least one keyword to rank."}
    if keyword_count > CLEF_QUESTION_LIMIT:
        return {"error": f"Send at most {CLEF_QUESTION_LIMIT} keywords per rank request."}

    try:
        groups = rank_keyword_groups(prepared, body.cloudflare_account_id, body.cloudflare_api_token)
    except Exception as exc:
        return {"error": str(exc)}
    for group in groups:
        group["brand"] = ""
    return {"groups": groups}


@app.post("/api/compare")
def compare(body: CompareIn) -> dict[str, Any]:
    from src.compare_rank import compare_batch

    prepared = [{"title": group.title, "keywords": group.keywords} for group in body.groups]
    try:
        return compare_batch(
            prepared,
            body.cloudflare_account_id,
            body.cloudflare_api_token,
            body.typesafe_api_key,
        )
    except Exception as exc:
        return {
            "error": _redact(
                str(exc),
                [body.typesafe_api_key, body.cloudflare_api_token, body.cloudflare_account_id],
            )
        }


@app.post("/api/verify")
def verify(body: VerifyIn) -> dict[str, Any]:
    prompt = f"""
You evaluate whether a search keyword fits an ecommerce product.
Title: {body.title}
Keyword: {body.keyword}

Reply with JSON only: {{"match": "Y" or "N", "reason": "one short sentence"}}
Accept a broader keyword when this product is a normal example of that search.
"""

    def run():
        text = complete_text(body.provider, body.model, prompt)
        import json
        import re

        match = re.search(r"\{[\s\S]*\}", text)
        payload = json.loads(match.group(0) if match else text)
        return {
            "match": str(payload.get("match", "N")).upper().startswith("Y"),
            "reason": str(payload.get("reason", "")),
        }

    try:
        return _with_keys(_keys(body), run)
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/api/consolidate")
async def consolidate(
    file: UploadFile = File(...),
    product_type: str = Form("General catalog"),
    snapshot: str = Form("Latest available"),
) -> dict[str, Any]:
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        return {"error": "ZIP is over the 50 MB limit."}
    monthly, errors = load_monthly_data(BytesIO(raw))
    if errors:
        return {"error": " ".join(errors)}
    if not monthly:
        return {"error": "No monthly files were found in the ZIP."}

    sample_columns: list[str] = []
    for frame in monthly.values():
        sample_columns = [str(col) for col in frame.columns]
        break
    mapping = guess_column_mapping(sample_columns)
    mapped = {month: apply_column_mapping(frame, mapping) for month, frame in monthly.items()}
    preferred = None if snapshot == "Latest available" else snapshot
    snapshot_month, warning = resolve_snapshot_month(mapped, preferred)
    result = consolidate_data(mapped, product_type, snapshot_month)
    if result.empty:
        return {"error": "No products could be consolidated. Check that titles are present."}

    preview = result.head(40).fillna("").astype(str)
    keep = [
        col
        for col in [
            "Product Title",
            "Product Brand",
            "Product Max Price",
            "Availability",
            "Product Category L1",
            "Product Category L3",
            "Peak Popularity",
        ]
        if col in preview.columns
    ]
    return {
        "total": int(len(result)),
        "months": [month for month in get_month_order() if month in monthly],
        "snapshot": snapshot_month,
        "warning": warning,
        "mapping": mapping,
        "preview": preview[keep].to_dict(orient="records"),
    }
