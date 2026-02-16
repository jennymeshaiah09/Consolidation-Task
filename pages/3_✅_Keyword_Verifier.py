
"""
Page: Keyword Verifier
Check if keywords match product titles using LLM.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.keyword_generator import verify_keyword_match, verify_keywords_bulk, get_gemini_client
from src.llm_keywords import validate_api_key

# Import UI utilities
from utils.ui_components import (
    apply_custom_css,
    render_page_header,
    render_sidebar_info,
    render_custom_divider,
    render_info_banner,
    render_header_navigation
)

# Page configuration
st.set_page_config(
    page_title="Keyword Verifier",
    page_icon="✅",
    layout="wide"
)

apply_custom_css()

def main():
    # Header Navigation
    render_header_navigation(current_page="Verifier")

    render_page_header(
        title="Keyword Verifier",
        subtitle="Validate if your keywords actually match your products using AI.",
        icon="✅"
    )

    render_sidebar_info(current_phase="Verifier")

    # API Key Check
    if not validate_api_key():
        render_info_banner(
            "⚠️ Google API key not configured. Set GOOGLE_API_KEY environment variable.",
            "warning"
        )
        return

    client = get_gemini_client()
    if not client:
         st.error("Failed to initialize Gemini client. Check API key.")
         return

    # Tabs
    tab1, tab2 = st.tabs(["🔎 Single Check", "📁 Bulk Upload"])

    # --- Tab 1: Single Check ---
    with tab1:
        st.markdown("### Quick Check")
        st.markdown("Test a single Title vs Keyword pair.")

        col1, col2 = st.columns(2)
        with col1:
            title_input = st.text_input("Product Title", placeholder="e.g. Jack Daniels 70cl")
        with col2:
            keyword_input = st.text_input("Keyword", placeholder="e.g. Jack Daniels Whiskey")

        if st.button("Verify Match", type="primary", disabled=not (title_input and keyword_input)):
            with st.spinner("Asking AI..."):
                result = verify_keyword_match(client, title_input, keyword_input)
                
            match_status = result.get('match', 'N')
            reason = result.get('reason', '')

            if match_status == 'Y':
                st.success(f"### ✅ MATCH (Y)")
            else:
                st.error(f"### ❌ NO MATCH (N)")
            
            st.info(f"**Reason:** {reason}")

    # --- Tab 2: Bulk Check ---
    with tab2:
        st.markdown("### Bulk Verification")
        st.markdown("Upload a CSV/Excel file to verify multiple rows at once.")

        uploaded_file = st.file_uploader("Upload File", type=['csv', 'xlsx'])

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.write(f"Loaded {len(df)} rows.")
                st.dataframe(df.head(), use_container_width=True)

                col_title, col_kw = st.columns(2)
                with col_title:
                    title_col = st.selectbox("Select Product Title Column", df.columns, index=0 if 'Product Title' in df.columns else 0)
                with col_kw:
                    kw_col = st.selectbox("Select Keyword Column", df.columns, index=1 if 'Keyword' in df.columns else 0)

                if st.button("🚀 Verify All Columns"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def update_prog(pct, curr, total):
                        progress_bar.progress(pct)
                        status_text.text(f"Verifying {curr}/{total}...")

                    result_df = verify_keywords_bulk(
                        df, 
                        title_col=title_col, 
                        keyword_col=kw_col,
                        progress_callback=update_prog
                    )

                    progress_bar.progress(1.0)
                    status_text.text("Done!")

                    st.markdown("### Results")
                    st.dataframe(result_df, use_container_width=True)

                    # Download
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        result_df.to_excel(writer, index=False)
                    output.seek(0)

                    st.download_button(
                        label="📥 Download Results",
                        data=output,
                        file_name="keyword_verification_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )

            except Exception as e:
                st.error(f"Error processing file: {e}")

if __name__ == "__main__":
    main()
