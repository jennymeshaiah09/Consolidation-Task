# Product Data Consolidation Package

import os


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
