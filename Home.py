"""
Product Data Consolidation Tool - Homepage
Modern multi-phase data processing workflow
"""

import streamlit as st
from utils.ui_components import (
    apply_custom_css,
    render_hero_section,
    render_phase_card,
    render_metric_card,
    render_custom_divider,
    render_info_banner,
    render_header_navigation
)
from utils.state_manager import (
    init_session_state,
    get_session_stats,
    get_phase_status,
    clear_session_data
)

# Page configuration
st.set_page_config(
    page_title="Product Data Consolidation Pipeline",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def render_quick_stats():
    """Render quick stats dashboard if data exists"""
    stats = get_session_stats()

    if stats:
        st.markdown("### 📊 Current Session Stats")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            render_metric_card(
                "Product Type",
                stats['product_type'],
                "🏷️"
            )

        with col2:
            render_metric_card(
                "Total Products",
                str(stats['total_products']),
                "📦"
            )

        with col3:
            render_metric_card(
                "Categories",
                str(stats['categories_count']),
                "📁"
            )

        with col4:
            render_metric_card(
                "Keywords Generated",
                str(stats['keywords_generated']),
                "🔤"
            )

        if stats['last_updated']:
            st.caption(f"Last updated: {stats['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")

        render_custom_divider()


def render_phase_overview():
    """Render overview of all phases"""
    st.markdown("### 🗺️ Pipeline Phases")
    st.markdown("Navigate through each phase of the data consolidation pipeline.")

    # Row 1: Phase 1 and 2
    col1, col2 = st.columns(2)

    with col1:
        render_phase_card(
            phase_num=1,
            title="Data Consolidation",
            description="Upload monthly data files, validate, and consolidate into a unified dataset.",
            status=get_phase_status(1),
            icon="📊",
            page_link="1_📊_Data_Consolidation"
        )

    with col2:
        render_phase_card(
            phase_num=2,
            title="Keywords & Categories",
            description="Generate SEO-friendly keywords using AI and categorize products automatically.",
            status=get_phase_status(2),
            icon="🔤",
            page_link="2_🔤_Keywords_Categories"
        )

    # Row 2: Phase 3 and 4
    col3, col4 = st.columns(2)

    with col3:
        render_phase_card(
            phase_num=3,
            title="MSV Management",
            description="Monthly Search Volume data handling (managed by teammate Tenny).",
            status=get_phase_status(3),
            icon="📈",
            page_link="3_📈_MSV_Management"
        )

    with col4:
        render_phase_card(
            phase_num=4,
            title="Peak Analysis",
            description="Analyze peak popularity patterns and identify seasonal trends.",
            status=get_phase_status(4),
            icon="⭐",
            page_link="4_⭐_Peak_Analysis"
        )

    # Row 3: Phase 5
    col5, _ = st.columns(2)

    with col5:
        render_phase_card(
            phase_num=5,
            title="Insights & Analytics",
            description="Advanced analytics and insights from consolidated data (coming soon).",
            status=get_phase_status(5),
            icon="💡",
            page_link="5_💡_Insights"
        )


def render_getting_started():
    """Render getting started guide for new users"""
    stats = get_session_stats()

    if not stats:  # Only show for new users
        st.markdown("### 🚀 Getting Started")

        render_info_banner(
            "Welcome! Start by uploading your monthly data in Phase 1, then proceed through each phase in order."
        )

        st.markdown("""
        **Quick Start Guide:**

        1. **Phase 1** - Upload a ZIP file containing monthly product data (Jan-Dec 2025)
        2. **Phase 2** - Generate SEO keywords using AI and review categorization
        3. **Phase 3** - MSV data will be handled by Tenny (informational phase)
        4. **Phase 4** - Review peak popularity analysis and trends
        5. **Phase 5** - Explore insights (coming soon)

        **Requirements:**
        - ZIP file with monthly CSV/Excel files
        - Files should contain: Product Title, Brand, Availability, Price, Popularity rank
        - December file is mandatory
        """)


def main():
    """Main homepage rendering"""
    render_header_navigation(current_page="Home")

    # Hero Section
    render_hero_section(
        title="🎯 Product Data Consolidation Pipeline",
        subtitle="Modern multi-phase data processing workflow for e-commerce analytics"
    )

    # Sidebar
    with st.sidebar:
        st.markdown("### 🏠 Home")
        st.markdown("You are on the homepage.")

        st.markdown("---")

        # Reset button
        if st.button("🔄 Start Fresh Session", help="Clear all data and start over"):
            clear_session_data()
            st.rerun()

        st.markdown("---")

        st.markdown("### ℹ️ About")
        st.markdown("""
        This tool consolidates monthly product data and enriches it with:
        - LLM-generated keywords
        - Automatic categorization
        - Peak popularity analysis
        - MSV integration (optional)
        """)

        st.markdown("---")

        st.markdown("### 📚 Resources")
        st.markdown("- [View Documentation](PLAN.md)")
        st.markdown("- Product Types: BWS, Pets, Electronics")

    # Quick Stats (if data exists)
    render_quick_stats()

    # Phase Overview
    render_phase_overview()

    # Getting Started (for new users)
    render_getting_started()

    # Footer
    render_custom_divider()
    st.caption("Product Data Consolidation Tool | Built with Streamlit & Google Gemini AI")


if __name__ == "__main__":
    main()
