# Product Data Consolidation Package

import os
from dotenv import load_dotenv

# Load .env file on import
load_dotenv()


def get_google_api_key() -> str | None:
    """Resolve a Gemini key for this visitor, then deployment secrets, then .env.

    Checks in order:
        1. st.session_state["user_api_key"]       – key pasted in the sidebar
        2. st.secrets["GOOGLE_API_KEY"]           – top-level TOML key
        3. st.secrets["google_gemini"]["api_key"] – nested under [google_gemini]
        4. os.getenv("GOOGLE_API_KEY")            – .env file / shell env
    """
    try:
        import streamlit as st
        user_key = st.session_state.get("user_api_key")
        if isinstance(user_key, str) and user_key.strip():
            return user_key.strip()
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
        if "google_gemini" in st.secrets and "api_key" in st.secrets["google_gemini"]:
            return st.secrets["google_gemini"]["api_key"]
    except Exception:
        pass  # st.secrets unavailable outside Streamlit runtime
    env_key = os.getenv("GOOGLE_API_KEY")
    return env_key.strip() if isinstance(env_key, str) and env_key.strip() else None
