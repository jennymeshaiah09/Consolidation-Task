"""
Meridian — Product Data Consolidation Pipeline
Homepage
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
)
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


def render_phase_overview():
    """Pipeline phase cards."""
    render_section_heading(
        "Pipeline",
        "Move through each phase in order. Data carries forward automatically.",
    )

    col1, col2 = st.columns(2)
    with col1:
        render_phase_card(
            phase_num=1,
            title="Data consolidation",
            description="Upload monthly files, validate columns, and merge into one product master.",
            status=get_phase_status(1),
            page_link="1_📊_Data_Consolidation",
        )
    with col2:
        render_phase_card(
            phase_num=2,
            title="Keywords & categories",
            description="Generate MSV-ready search phrases and review taxonomy classification.",
            status=get_phase_status(2),
            page_link="2_🔤_Keywords_Categories",
        )

    col3, col4 = st.columns(2)
    with col3:
        render_phase_card(
            phase_num=3,
            title="MSV management",
            description="Join Monthly Search Volume exports and derive seasonal peaks.",
            status=get_phase_status(3),
            page_link="3_📈_MSV_Management",
        )
    with col4:
        render_phase_card(
            phase_num=4,
            title="Peak analysis",
            description="Inspect popularity peaks and compare against search seasonality.",
            status=get_phase_status(4),
            page_link="4_⭐_Peak_Analysis",
        )

    col5, col6 = st.columns(2)
    with col5:
        render_phase_card(
            phase_num=5,
            title="Insights",
            description="Category and brand rollups with a formatted Excel export.",
            status=get_phase_status(5),
            page_link="5_💡_Insights",
        )
    with col6:
        st.markdown(
            """
<div class="m-phase">
  <div class="m-phase-num">Tools</div>
  <h3>Standalone utilities</h3>
  <p>Run keyword generation or verification without walking the full pipeline.</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        t1, t2 = st.columns(2)
        with t1:
            if st.button("Keyword generator", key="home_tool_gen", use_container_width=True):
                st.switch_page("pages/6_🔑_Keyword_Generator.py")
        with t2:
            if st.button("Keyword verifier", key="home_tool_ver", use_container_width=True):
                st.switch_page("pages/3_✅_Keyword_Verifier.py")


def render_getting_started():
    """First-run guidance."""
    if get_session_stats():
        return

    render_section_heading("Start here", "One ZIP of monthly catalogs gets you into the pipeline.")
    render_info_banner(
        "Begin in Phase 01 with a ZIP of monthly CSV/Excel files. December is required. "
        "Then generate keywords, attach MSV, and review peaks."
    )
    st.markdown(
        """
- **Inputs:** Product Title, Brand, Availability, Price range max, Popularity rank  
- **Taxonomy:** Categories & subs Excel (14 product types, ~866 categories)  
- **Keywords:** Hybrid / RAKE / Gemini — optimized for non-zero MSV  
        """
    )


def main():
    render_header_navigation(current_page="Home")
    render_hero_section()

    with st.sidebar:
        st.markdown("### Meridian")
        st.caption("Product data consolidation pipeline")
        st.markdown("---")
        if st.button("Start fresh session", help="Clear all pipeline data", use_container_width=True):
            clear_session_data()
            st.rerun()
        st.markdown("---")
        st.markdown("**Includes**")
        st.markdown(
            """
- Taxonomy classification  
- MSV-ready keywords  
- Peak popularity & seasonality  
- Excel export  
            """
        )

    render_quick_stats()
    render_phase_overview()
    render_getting_started()
    render_custom_divider()
    st.caption("Meridian · Streamlit · Google Gemini")


if __name__ == "__main__":
    main()
