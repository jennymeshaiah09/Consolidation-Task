"""
Phase 4: Peak Popularity Analysis
Analyze peak popularity patterns and identify seasonal trends
"""

import streamlit as st
import pandas as pd
from io import BytesIO

# Import UI utilities
from utils.ui_components import (
    apply_custom_css,
    render_page_header,
    render_progress_tracker,
    render_sidebar_info,
    render_custom_divider,
    render_info_banner,
    render_header_navigation,
    render_summary_section
)
from utils.state_manager import (
    init_session_state,
    check_phase_prerequisites,
    get_consolidated_df
)

# Page configuration
st.set_page_config(
    page_title="Phase 4: Peak Analysis",
    page_icon="⭐",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def render_algorithm_explanation():
    """Explain the peak popularity algorithm"""
    st.markdown("### 📐 Algorithm Explanation")

    with st.expander("How Peak Popularity is Calculated", expanded=False):
        st.markdown("""
        **Variance-Based Peak Popularity Algorithm:**

        1. **Identify Top 4 Months**: For each product, find the 4 months with the best (lowest) popularity ranks
        2. **Calculate Variance**: Compute mean and standard deviation among these top 4 months
        3. **Find Stable Months**: Select months within 1 standard deviation of the mean
        4. **Result**: Comma-separated list of months with consistent high popularity

        **Why Top 4 Only?**
        - Focuses on genuinely popular periods
        - Reduces noise from occasional spikes
        - Identifies stable, repeatable peak patterns

        **Note:** Lower rank number = higher popularity (rank 1 is most popular)
        """)


def render_peak_distribution():
    """Display peak month distribution"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None or 'Peak Popularity' not in consolidated_df.columns:
        return

    st.markdown("### 📊 Peak Month Distribution")

    # Count products by peak months
    peak_counts = {}
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    for _, row in consolidated_df.iterrows():
        peak_value = row['Peak Popularity']
        if pd.notna(peak_value) and str(peak_value).strip() != "":
            # Split comma-separated months
            peak_months = [m.strip() for m in str(peak_value).split(',')]
            for month in peak_months:
                if month in months:
                    peak_counts[month] = peak_counts.get(month, 0) + 1

    if peak_counts:
        # Create DataFrame for chart
        peak_df = pd.DataFrame(list(peak_counts.items()), columns=['Month', 'Products'])
        peak_df = peak_df.set_index('Month')

        col1, col2 = st.columns([2, 1])

        with col1:
            st.bar_chart(peak_df)

        with col2:
            st.markdown("**Top Peak Months:**")
            sorted_peaks = sorted(peak_counts.items(), key=lambda x: x[1], reverse=True)
            for month, count in sorted_peaks[:5]:
                st.metric(month, count)
    else:
        st.info("No peak popularity data available yet.")


def render_top_products():
    """Display top products with stable peak popularity"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None or 'Peak Popularity' not in consolidated_df.columns:
        return

    st.markdown("### 🏆 Top Products with Stable Popularity")

    # Filter products with peak popularity data
    with_peaks = consolidated_df[
        (consolidated_df['Peak Popularity'].notna()) &
        (consolidated_df['Peak Popularity'] != '')
    ].copy()

    if with_peaks.empty:
        st.info("No products with peak popularity data found.")
        return

    # Show top 20 products
    display_cols = ['Product Title', 'Product Brand', 'Product Category L1', 'Product Category L2', 'Product Category L3', 'Peak Popularity']
    available_cols = [col for col in display_cols if col in with_peaks.columns]

    st.dataframe(
        with_peaks[available_cols].head(20),
        use_container_width=True,
        height=400
    )

    # Export filtered data
    st.markdown("---")

    if st.button("📥 Export Products with Peak Data", type="secondary"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            with_peaks.to_excel(writer, index=False, sheet_name='Peak Analysis')

            worksheet = writer.sheets['Peak Analysis']
            for idx, col in enumerate(with_peaks.columns):
                max_length = max(
                    with_peaks[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(idx, idx, min(max_length, 50))

        output.seek(0)

        st.download_button(
            label="📥 Download Peak Analysis Excel",
            data=output,
            file_name="peak_analysis_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def render_filters():
    """Interactive filtering by peak months"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None or 'Peak Popularity' not in consolidated_df.columns:
        return

    st.markdown("### 🔍 Filter by Peak Months")

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    selected_months = st.multiselect(
        "Select peak months to filter",
        options=months,
        help="Show products with peak popularity in the selected months"
    )

    if selected_months:
        # Filter products containing any of the selected months
        filtered = consolidated_df[
            consolidated_df['Peak Popularity'].apply(
                lambda x: any(month in str(x) for month in selected_months) if pd.notna(x) else False
            )
        ]

        st.info(f"Found {len(filtered)} products with peaks in {', '.join(selected_months)}")

        if not filtered.empty:
            display_cols = ['Product Title', 'Product Brand', 'Product Category L1', 'Product Category L2', 'Product Category L3', 'Peak Popularity']
            available_cols = [col for col in display_cols if col in filtered.columns]

            st.dataframe(
                filtered[available_cols],
                use_container_width=True,
                height=400
            )


def main():
    """Main page rendering"""
    render_header_navigation(current_page="Phase 4")

    # Page header
    render_page_header(
        title="Phase 4: Peak Popularity Analysis",
        subtitle="Analyze peak popularity patterns and identify seasonal trends",
        icon="⭐"
    )

    # Progress tracker
    render_progress_tracker(current_phase=4)

    # Sidebar
    render_sidebar_info(current_phase=4)

    # Check prerequisites
    is_ready, message = check_phase_prerequisites(4)

    if not is_ready:
        st.error(message)
        st.info("👈 Go back to Phase 1 to upload and consolidate your data first.")

        if st.button("← Back to Phase 1"):
            st.switch_page("pages/1_📊_Data_Consolidation.py")
        return

    # Main content
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        st.error("No data available. Please complete Phase 1 first.")
        return

    # Display current data info
    st.markdown("### 📊 Dataset Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Products", len(consolidated_df))

    with col2:
        if 'Peak Popularity' in consolidated_df.columns:
            with_peaks = (consolidated_df['Peak Popularity'].notna()) & (consolidated_df['Peak Popularity'] != '')
            st.metric("Products with Peak Data", with_peaks.sum())

    with col3:
        if 'Peak Popularity' in consolidated_df.columns:
            percentage = (with_peaks.sum() / len(consolidated_df)) * 100 if len(consolidated_df) > 0 else 0
            st.metric("Coverage", f"{percentage:.1f}%")

    render_custom_divider()

    # Algorithm explanation
    render_algorithm_explanation()

    render_custom_divider()

    # Peak distribution
    render_peak_distribution()

    render_custom_divider()

    # Filters
    render_filters()

    render_custom_divider()

    # Top products
    render_top_products()

    # Navigation
    render_custom_divider()
    render_info_banner(
        "✨ Peak Analysis Complete! You can now proceed to Phase 5 (Insights) or download your results.",
        "info"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back to Phase 2", use_container_width=True):
            st.switch_page("pages/2_🔤_Keywords_Categories.py")

    with col2:
        if st.button("🏠 Back to Home", use_container_width=True):
            st.switch_page("Home.py")

    with col3:
        if st.button("Phase 5: Insights →", type="primary", use_container_width=True):
            st.switch_page("pages/5_💡_Insights.py")


if __name__ == "__main__":
    main()
