"""
Phase 2: Keywords & Categories
Generate SEO-friendly keywords using AI and review product categorization
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import core modules
from src.llm_keywords import (
    generate_keywords_batch,
    classify_other_products_batch,
    validate_api_key,
    test_api_connection
)
from src.rake_keywords import generate_keywords_rake

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
    save_keyword_results,
    check_phase_prerequisites,
    get_consolidated_df
)

# Page configuration
st.set_page_config(
    page_title="Phase 2: Keywords & Categories",
    page_icon="🔤",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def render_category_overview():
    """Display category breakdown for L1, L2, L3"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        return

    # Check if we have the new 3-level system or old single category
    has_levels = all(col in consolidated_df.columns for col in ['Product Category L1', 'Product Category L2', 'Product Category L3'])

    if not has_levels:
        st.warning("⚠️ Categories not found. Please re-run Phase 1 to generate L1, L2, L3 categories.")
        return

    st.markdown("### 📁 Category Distribution")

    # Create tabs for L1, L2, L3
    tab1, tab2, tab3 = st.tabs(["Level 1 (Main)", "Level 2 (Sub)", "Level 3 (Specific)"])

    with tab1:
        st.markdown("**Level 1 Categories** (Broadest)")
        l1_counts = consolidated_df['Product Category L1'].value_counts()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.bar_chart(l1_counts)

        with col2:
            st.markdown("**Top L1 Categories:**")
            for category, count in l1_counts.head(5).items():
                percentage = (count / len(consolidated_df)) * 100
                st.metric(category, f"{count} ({percentage:.1f}%)")

    with tab2:
        st.markdown("**Level 2 Categories** (Subcategories)")
        l2_counts = consolidated_df['Product Category L2'].value_counts()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.bar_chart(l2_counts)

        with col2:
            st.markdown("**Top L2 Categories:**")
            other_count = (consolidated_df['Product Category L2'] == 'Other').sum()
            if other_count > 0:
                st.info(f"ℹ️ {other_count} products have 'Other' at L2")

            for category, count in l2_counts.head(5).items():
                percentage = (count / len(consolidated_df)) * 100
                st.metric(category, f"{count} ({percentage:.1f}%)")

    with tab3:
        st.markdown("**Level 3 Categories** (Most Specific)")
        l3_counts = consolidated_df['Product Category L3'].value_counts()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.bar_chart(l3_counts)

        with col2:
            st.markdown("**Top L3 Categories:**")
            other_count = (consolidated_df['Product Category L3'] == 'Other').sum()
            if other_count > 0:
                st.info(f"ℹ️ {other_count} products have 'Other' at L3")

            for category, count in l3_counts.head(5).items():
                percentage = (count / len(consolidated_df)) * 100
                st.metric(category, f"{count} ({percentage:.1f}%)")


def render_keyword_generation():
    """Handle keyword generation workflow"""
    consolidated_df = get_consolidated_df()
    product_type = st.session_state.product_type

    if consolidated_df is None:
        st.error("No data available. Please complete Phase 1 first.")
        return

    st.markdown("### 🔤 Keyword Generation")

    # Mode selection
    st.markdown("**Choose Generation Mode:**")
    mode = st.radio(
        "Keyword Generation Mode",
        options=["⚡ Fast (RAKE)", "🧠 Quality (LLM)"],
        horizontal=True,
        help="RAKE is instant but less accurate. LLM is slower but produces better keywords.",
        label_visibility="collapsed"
    )
    use_rake = mode == "⚡ Fast (RAKE)"

    if use_rake:
        st.info("⚡ **RAKE Mode**: Instant keyword extraction using NLP. No API calls needed!")
    else:
        # API Key status for LLM mode
        if not validate_api_key():
            render_info_banner(
                "⚠️ Google API key not configured. Set GOOGLE_API_KEY environment variable or use RAKE mode.",
                "warning"
            )

            st.markdown("""
            **How to configure LLM mode:**
            1. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
            2. Create a `.env` file in the project root
            3. Add: `GOOGLE_API_KEY=your_key_here`
            4. Restart the application
            
            **Or use RAKE mode above for instant results without API!**
            """)
            return

        # API connection test (only for LLM mode)
        st.success("✅ Google Gemini API Key configured")

        if st.button("🔍 Test API Connection"):
            with st.spinner("Testing connection..."):
                success, message = test_api_connection()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")

    st.markdown("---")

    # Generation controls
    col1, col2 = st.columns([1, 1])

    with col1:
        trial_mode = st.checkbox(
            "Trial mode (first N products only)",
            value=True,
            help="Process only a limited number of products for testing"
        )

    with col2:
        if trial_mode:
            max_products = st.number_input(
                "Number of products",
                min_value=1,
                max_value=len(consolidated_df),
                value=min(10, len(consolidated_df)),
                help="Number of products to process in trial mode"
            )
        else:
            max_products = None

    # Generate button
    button_label = "⚡ Generate Keywords (Instant)" if use_rake else "🚀 Generate Keywords"
    if st.button(button_label, type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(progress, current, total):
            progress_bar.progress(progress)
            status_text.text(f"Processing product {current} of {total}...")

        try:
            # Step 1: Generate keywords
            if use_rake:
                # RAKE mode - instant, no API
                with st.spinner("Generating keywords with RAKE..."):
                    # Handle trial mode
                    if trial_mode and max_products:
                        df_to_process = consolidated_df.head(max_products).copy()
                    else:
                        df_to_process = consolidated_df.copy()
                    
                    updated_df = generate_keywords_rake(
                        df_to_process,
                        progress_callback=update_progress
                    )
                    
                    # Merge back if trial mode
                    if trial_mode and max_products:
                        consolidated_df.update(updated_df)
                        updated_df = consolidated_df.copy()
            else:
                # LLM mode
                with st.spinner("Generating keywords with LLM..."):
                    updated_df = generate_keywords_batch(
                        consolidated_df,
                        product_type,
                        progress_callback=update_progress,
                        max_products=max_products
                    )

            if trial_mode and max_products:
                st.success(f"✅ Keywords generated for first {max_products} products!")
            else:
                st.success("✅ Keywords generated successfully!")

            # Note: Category classification happens in Phase 1
            # L1, L2, L3 categories are already assigned

            # Save results
            save_keyword_results(updated_df)

            if trial_mode and max_products:
                st.info(f"Remaining {len(consolidated_df) - max_products} products have empty keywords.")

            progress_bar.progress(1.0)
            status_text.text("Complete!")

        except Exception as e:
            st.error(f"Error generating keywords: {str(e)}")
            return


def render_keyword_preview():
    """Display keyword quality preview"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None or 'Product Keyword' not in consolidated_df.columns:
        return

    # Count keywords
    total_keywords = (consolidated_df['Product Keyword'] != '').sum()
    total_products = len(consolidated_df)

    st.markdown("### 🔍 Keyword Preview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Keywords Generated", f"{total_keywords} / {total_products}")
    with col2:
        percentage = (total_keywords / total_products) * 100 if total_products > 0 else 0
        st.metric("Completion Rate", f"{percentage:.1f}%")

    # Show sample keywords
    with_keywords = consolidated_df[consolidated_df['Product Keyword'] != '']

    if not with_keywords.empty:
        st.markdown("**Sample Keywords:**")
        # Show L1, L2, L3 if available, otherwise show old single category
        display_cols = ['Product Title', 'Product Keyword']
        if 'Product Category L1' in consolidated_df.columns:
            display_cols.extend(['Product Category L1', 'Product Category L2', 'Product Category L3'])
        elif 'Product Category' in consolidated_df.columns:
            display_cols.append('Product Category')

        sample = with_keywords[display_cols].head(10)
        st.dataframe(sample, use_container_width=True)


def render_export_section():
    """Handle final data export"""
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        return

    st.markdown("### 💾 Export Final Results")

    st.info("💡 Download the complete consolidated dataset with keywords and categories.")

    # Create Excel file for download
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        consolidated_df.to_excel(writer, index=False, sheet_name='Consolidated Data')

        # Auto-adjust column widths
        worksheet = writer.sheets['Consolidated Data']
        for idx, col in enumerate(consolidated_df.columns):
            max_length = max(
                consolidated_df[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            worksheet.set_column(idx, idx, min(max_length, 50))

    output.seek(0)

    # Download button
    product_type = st.session_state.product_type or "Product"
    filename = f"{product_type}_consolidated_with_keywords.xlsx"

    st.download_button(
        label="📥 Download Complete Excel File",
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )


def main():
    """Main page rendering"""

    # Header Navigation
    render_header_navigation(current_page="Phase 2")

    # Page header
    render_page_header(
        title="Phase 2: Keywords & Categories",
        subtitle="Generate SEO-friendly keywords using AI and review product categorization",
        icon="🔤"
    )

    # Progress tracker
    render_progress_tracker(current_phase=2)

    # Sidebar
    render_sidebar_info(current_phase=2)

    # Check prerequisites
    is_ready, message = check_phase_prerequisites(2)

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
    st.markdown("### 📊 Current Dataset")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Product Type", st.session_state.product_type)

    with col2:
        st.metric("Total Products", len(consolidated_df))

    with col3:
        if 'Product Category' in consolidated_df.columns:
            categories = consolidated_df['Product Category'].nunique()
            st.metric("Categories", categories)

    render_custom_divider()

    # Category overview
    render_category_overview()

    render_custom_divider()

    # Keyword generation
    render_keyword_generation()

    render_custom_divider()

    # Keyword preview
    render_keyword_preview()

    render_custom_divider()

    # Export section
    render_export_section()

    # Next step navigation
    render_custom_divider()
    render_info_banner(
        "✨ Phase 2 Complete! You can now proceed to Phase 4 (Peak Analysis) or download your results.",
        "info"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back to Phase 1", use_container_width=True):
            st.switch_page("pages/1_📊_Data_Consolidation.py")

    with col2:
        if st.button("Phase 3: MSV Info →", use_container_width=True):
            st.switch_page("pages/3_📈_MSV_Management.py")

    with col3:
        if st.button("Skip to Phase 4 →", type="primary", use_container_width=True):
            st.switch_page("pages/4_⭐_Peak_Analysis.py")


if __name__ == "__main__":
    main()
