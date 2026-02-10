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
    """Explain the peak popularity and seasonality algorithms"""
    st.markdown("### 📐 Algorithm Explanation")

    with st.expander("How Peaks are Calculated", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **⭐ Peak Popularity (Rank-Based)**
            *Best for: Finding stable, consistent performers.*

            1. **Identify Top 4 Months**: Finds months with best (lowest) rank.
            2. **Variance Check**: Ensures ranks are stable (low standard deviation).
            3. **Result**: Months where product is reliably popular.
            """)
            
        with col2:
            st.markdown("""
            **📈 Peak Seasonality (MSV-Based)**
            *Best for: Identifying high-volume search spikes.*

            1. **Analyze 3 Years**: Uses Jan 2023 - Dec 2025 Search Volume.
            2. **Identify Top 4 Months**: Finds months with highest search volume.
            3. **Variance Check**: Selects months within 1 Std Dev of the peak.
            4. **Result**: Months where customer demand is highest.
            """)


def render_peak_distribution():
    """Display peak month distribution for both metrics"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        return

    st.markdown("### 📊 Peak Month Distribution")

    # Helper to count peaks
    def get_peak_counts(column_name):
        counts = {}
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        if column_name not in consolidated_df.columns:
            return None

        for _, row in consolidated_df.iterrows():
            val = row[column_name]
            if pd.notna(val) and str(val).strip() != "":
                peak_months = [m.strip() for m in str(val).split(',')]
                for month in peak_months:
                    # Handle "Jan 2024" -> "Jan" if needed, but usually it's just "Jan"
                    clean_month = month.split()[0]
                    if clean_month in months:
                        counts[clean_month] = counts.get(clean_month, 0) + 1
        return counts

    # Get counts
    pop_counts = get_peak_counts('Peak Popularity')
    seas_counts = get_peak_counts('Peak Seasonality')

    # Render charts
    if pop_counts and seas_counts:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**⭐ Peak Popularity (Rank)**")
            st.bar_chart(pd.Series(pop_counts).reindex(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']).fillna(0))
        with col2:
            st.markdown("**📈 Peak Seasonality (MSV)**")
            st.bar_chart(pd.Series(seas_counts).reindex(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']).fillna(0))
            
    elif pop_counts:
        st.markdown("**⭐ Peak Popularity (Rank)**")
        st.bar_chart(pd.Series(pop_counts))
    elif seas_counts:
         st.markdown("**📈 Peak Seasonality (MSV)**")
         st.bar_chart(pd.Series(seas_counts))
    else:
        st.info("No peak data available.")


def render_top_products():
    """Display top products with stable peak popularity"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        return

    st.markdown("### 🏆 Top Products with Peak Data")

    # Filter columns to display
    base_cols = ['Product Title', 'Product Brand', 'Product Category L3']
    peak_cols = []
    
    if 'Peak Popularity' in consolidated_df.columns:
        peak_cols.append('Peak Popularity')
    if 'Peak Seasonality' in consolidated_df.columns:
        peak_cols.append('Peak Seasonality')

    if not peak_cols:
        st.info("No peak data columns found.")
        return

    # Filter rows that have SOME peak data
    mask = pd.Series(False, index=consolidated_df.index)
    for col in peak_cols:
        mask |= (consolidated_df[col].notna()) & (consolidated_df[col] != '')
    
    filtered_df = consolidated_df[mask].copy()

    if filtered_df.empty:
        st.info("No products with peak data found.")
        return

    # Show table
    display_cols = base_cols + peak_cols
    st.dataframe(
        filtered_df[display_cols].head(50),
        use_container_width=True,
        height=500
    )

    # Export filtered data
    st.markdown("---")

    if st.button("📥 Export Products with Peak Data", type="secondary"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df[display_cols].to_excel(writer, index=False, sheet_name='Peak Analysis')
            
            # Format columns
            worksheet = writer.sheets['Peak Analysis']
            for idx, col in enumerate(display_cols):
                max_length = max(
                    filtered_df[col].astype(str).map(len).max(),
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
    """Interactive filtering by peak months (Seasonality prioritized)"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        return

    st.markdown("### 🔍 Filter by Peak Months (Seasonality)")

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    selected_months = st.multiselect(
        "Select months to filter products:",
        options=months,
        help="Shows products that peak in these months (based on Seasonality if available, else Popularity)"
    )

    if selected_months:
        # Prioritize Seasonality, fallback to Popularity
        target_col = 'Peak Seasonality' if 'Peak Seasonality' in consolidated_df.columns else 'Peak Popularity'
        
        if target_col not in consolidated_df.columns:
            return

        # Filter
        filtered = consolidated_df[
            consolidated_df[target_col].apply(
                lambda x: any(month in str(x) for month in selected_months) if pd.notna(x) else False
            )
        ]

        st.info(f"Found {len(filtered)} products dealing in **{', '.join(selected_months)}** (Source: {target_col})")

        if not filtered.empty:
            display_cols = ['Product Title', 'Product Brand', 'Product Category L3', target_col]
            st.dataframe(
                filtered[display_cols],
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
