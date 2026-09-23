# Product Data Consolidation Package

import os
from dotenv import load_dotenv

# Load .env file on import
load_dotenv()


def get_google_api_key() -> str | None:
    """Resolve GOOGLE_API_KEY from Streamlit secrets (deployed) or .env (local).

    Checks in order:
        1. st.secrets["GOOGLE_API_KEY"]          – top-level TOML key
        2. st.secrets["google_gemini"]["api_key"] – nested under [google_gemini]
        3. os.getenv("GOOGLE_API_KEY")            – .env file / shell env
    """
    try:
        import streamlit as st
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
        if "google_gemini" in st.secrets and "api_key" in st.secrets["google_gemini"]:
            return st.secrets["google_gemini"]["api_key"]
    except Exception:
        pass  # st.secrets unavailable outside Streamlit runtime
    return os.getenv("GOOGLE_API_KEY")


def require_genai():
    """Lazy-import google.generativeai so pages can load without LLM deps installed."""
    try:
        import google.generativeai as genai
        return genai
    except ImportError as exc:
        raise ImportError(
            "Missing package 'google-generativeai'. "
            "Install with: python -m pip install google-generativeai"
        ) from exc


def get_gemini_model(model_name: str = "gemini-2.5-flash-lite"):
    """Configure Gemini and return a GenerativeModel, or None if no API key."""
    api_key = get_google_api_key()
    if not api_key:
        return None
    genai = require_genai()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)
