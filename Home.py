"""
Meridian — search keyword generation, with an optional catalog pipeline.
"""

import streamlit as st
from utils.ui_components import (
    apply_custom_css,
    render_hero_section,
    render_phase_card,
    render_metric_card,
    render_custom_divider,
    render_info_banner,
    render_header_navigation,
    render_section_heading,
    render_api_key_field,
)
from utils.sample_data import build_sample_catalog_zip
from utils.state_manager import (
    init_session_state,
    get_session_stats,
    get_phase_status,
    clear_session_data,
)

st.set_page_config(
    page_title="Meridian",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
apply_custom_css()


def render_quick_stats():
    """Session metrics when data exists."""
    stats = get_session_stats()
    if not stats:
        return

    render_section_heading("Session", "Live snapshot from the current pipeline run.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Product type", stats["product_type"])
    with col2:
        render_metric_card("Products", str(stats["total_products"]))
    with col3:
        render_metric_card("Categories", str(stats["categories_count"]))
    with col4:
        render_metric_card("Keywords", str(stats["keywords_generated"]))

    if stats.get("last_updated"):
        st.caption(f"Updated {stats['last_updated'].strftime('%Y-%m-%d %H:%M')}")
    render_custom_divider()


def render_primary_task():
    """Keyword generation is the main job of the app."""
    render_section_heading(
        "Generate keywords",
        "Upload a list of product titles, or type them in. You get a short search phrase for each one.",
    )
    render_info_banner(
        "Fast mode needs no API key. Paste a Gemini key in the sidebar when you want Quality mode."
    )
    primary, secondary = st.columns(2)
    with primary:
        if st.button("Generate keywords", key="home_tool_gen", type="primary", use_container_width=True):
            st.switch_page("pages/06_Keyword_Generator.py")
    with secondary:
        if st.button("Check a keyword", key="home_tool_ver", use_container_width=True):
            st.switch_page("pages/07_Keyword_Verifier.py")


def render_phase_overview():
    """Optional catalog pipeline."""
    render_section_heading(
        "Catalog pipeline",
        "Optional. Use this when you have monthly files and also want categories, search volume, and peaks.",
    )

    col1, col2 = st.columns(2)
    with col1:
        render_phase_card(
            phase_num=1,
            title="Data consolidation",
            description="Upload monthly files, validate columns, and merge into one product master.",
            status=get_phase_status(1),
            page_link="01_Consolidate",
        )
    with col2:
        render_phase_card(
            phase_num=2,
            title="Keywords & categories",
            description="Generate MSV-ready search phrases and review taxonomy classification.",
            status=get_phase_status(2),
            page_link="02_Keywords",
        )

    col3, col4 = st.columns(2)
    with col3:
        render_phase_card(
            phase_num=3,
            title="MSV management",
            description="Optional. Upload a search-volume export for any months you have.",
            status=get_phase_status(3),
            page_link="03_MSV",
        )
    with col4:
        render_phase_card(
            phase_num=4,
            title="Peak analysis",
            description="Inspect popularity peaks and compare against search seasonality.",
            status=get_phase_status(4),
            page_link="04_Peaks",
        )

    col5, col6 = st.columns(2)
    with col5:
        render_phase_card(
            phase_num=5,
            title="Insights",
            description="Category and brand rollups with a formatted Excel export.",
            status=get_phase_status(5),
            page_link="05_Insights",
        )
def render_getting_started():
    """Sample catalog for the optional pipeline."""
    render_section_heading("Sample catalog", "A small ZIP if you want to try the monthly pipeline.")
    st.download_button(
        "Download a sample catalog",
        data=build_sample_catalog_zip(),
        file_name="meridian-sample-catalog.zip",
        mime="application/zip",
    )


def main():
    render_header_navigation(current_page="Home")
    render_hero_section()

    with st.sidebar:
        st.markdown("### Meridian")
        st.caption("Search keyword generation")
        st.markdown("---")
        render_api_key_field()
        st.markdown("---")
        if st.button("Generate keywords", key="home_side_gen", type="primary", use_container_width=True):
            st.switch_page("pages/06_Keyword_Generator.py")
        if st.button("Check a keyword", key="home_side_ver", use_container_width=True):
            st.switch_page("pages/07_Keyword_Verifier.py")
        st.markdown("---")
        if st.button("Start fresh session", help="Clear all pipeline data", use_container_width=True):
            clear_session_data()
            st.rerun()
        st.markdown("---")
        st.markdown("**Primary task**")
        st.markdown(
            """
- Generate keywords from titles  
- Fast mode, no API key  
- Quality mode with your Gemini key  
            """
        )

    render_primary_task()
    render_custom_divider()
    render_quick_stats()
    render_phase_overview()
    render_getting_started()
    render_custom_divider()
    st.caption("Meridian · Streamlit · Google Gemini")


if __name__ == "__main__":
    main()
