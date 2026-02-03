"""
Phase 1: Data Consolidation
Upload and consolidate monthly product data from ZIP files
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import time

# Import core modules
from src.ingestion import load_monthly_data, get_month_order
from src.validation import validate_all_files
from src.consolidation import consolidate_data
from src.category_validator import CategoryValidator
from src.taxonomy import load_all_categories, load_categories_for_product_type

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
    save_consolidation_results,
    check_phase_prerequisites
)

# Page configuration
st.set_page_config(
    page_title="Phase 1: Data Consolidation",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def validate_categories(consolidated_df: pd.DataFrame, product_type: str, is_test: bool = False):
    """Validate and fix product categories using LLM

    Args:
        consolidated_df: DataFrame with products to validate
        product_type: Product type (BWS, Pets, etc.)
        is_test: If True, only shows preview without updating session state
    """

    try:
        # Initialize validator
        validator = CategoryValidator()

        # Load categories for the specific product type only
        all_categories = load_categories_for_product_type(product_type)

        # Remove "Other" and any empty/null categories
        all_categories = [cat for cat in all_categories if cat and cat.lower() != 'other']

        st.info(f"📊 Loaded {len(all_categories)} categories from {product_type} taxonomy")

        # Show all available categories for debugging
        with st.expander(f"📋 Available Categories for {product_type}", expanded=False):
            # Display in columns for better readability
            st.markdown("**All categories that the AI can choose from:**")
            st.write(", ".join(sorted(all_categories)))

        # Prepare products for validation (validate L3 - most specific level)
        products = []
        for idx, row in consolidated_df.iterrows():
            products.append({
                'title': row['Product Title'],
                'brand': row.get('Product Brand', 'Unknown'),
                'assigned_category': row.get('Product Category L3', 'Other')
            })

        # Progress indicator
        progress_bar = st.progress(0)
        status_text = st.empty()

        total_products = len(products)
        total_batches = (total_products + 19) // 20  # Ceiling division

        test_label = "🧪 TEST MODE: " if is_test else ""
        status_text.text(f"{test_label}🤖 Validating {total_products:,} products in {total_batches} batches...")

        # Validate in batches with progress updates
        validation_results = []
        batch_size = 20

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1

            # Update progress
            progress = (i / total_products) * 100
            progress_bar.progress(int(progress))
            status_text.text(f"🤖 Validating batch {batch_num}/{total_batches} ({len(batch)} products)...")

            try:
                batch_results = validator._validate_batch(batch, all_categories)
                validation_results.extend(batch_results)

                # Rate limiting between batches
                if i + batch_size < len(products):
                    time.sleep(2)

            except Exception as e:
                st.warning(f"⚠️ Batch {batch_num} failed: {e}. Assuming categories are correct for this batch.")
                # Add fallback results
                for product in batch:
                    validation_results.append({
                        'title': product['title'],
                        'assigned_category': product['assigned_category'],
                        'llm_suggested_category': product['assigned_category'],
                        'is_correct': True,
                        'confidence': 'unknown',
                        'error': str(e)
                    })

        progress_bar.progress(100)
        status_text.text(f"✅ Validated {total_products:,} products!")

        # Generate report
        report = validator.generate_validation_report(validation_results)

        # Update DataFrame with corrected categories (L3 - most specific level)
        corrections_made = 0
        for idx, result in enumerate(validation_results):
            if not result['is_correct']:
                consolidated_df.at[idx, 'Product Category L3'] = result['llm_suggested_category']
                corrections_made += 1

        # Update session state (only if not a test run)
        if not is_test:
            st.session_state.consolidated_df = consolidated_df
            st.success("✅ Session state updated with corrected categories!")
        else:
            st.info("🧪 Test mode: Session state not updated. Run full validation to apply changes.")

        # Display results
        st.markdown("---")
        st.subheader("📊 Validation Results")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Products", report['total_products'])

        with col2:
            st.metric("Correct", report['correct'], delta=None)

        with col3:
            st.metric("Fixed", corrections_made, delta=None)

        with col4:
            accuracy_pct = report['accuracy'] * 100
            st.metric("Accuracy", f"{accuracy_pct:.1f}%")

        # Show misclassifications if any
        if report['misclassifications']:
            st.markdown("### 🔄 Categories Updated")

            with st.expander(f"View {len(report['misclassifications'])} corrections", expanded=True):
                corrections_df = pd.DataFrame([
                    {
                        'Product': m['title'][:50] + '...' if len(m['title']) > 50 else m['title'],
                        'Original': m['assigned_category'],
                        'Corrected': m['llm_suggested_category'],
                        'Confidence': m['confidence'].upper()
                    }
                    for m in report['misclassifications']
                ])

                st.dataframe(
                    corrections_df,
                    use_container_width=True,
                    height=min(400, len(corrections_df) * 35 + 50)
                )

            if is_test:
                st.success(f"🧪 Test complete: Would update {corrections_made} categories. Run full validation to apply changes.")
            else:
                st.success(f"✅ Updated {corrections_made} categories successfully!")
        else:
            if is_test:
                st.success("🧪 Test complete: All sampled categories are correct!")
            else:
                st.success("✅ All categories are correct! No changes needed.")

        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()

    except ValueError as e:
        st.error(f"❌ Configuration Error: {e}")
        st.info("💡 Make sure GOOGLE_API_KEY is set in your .env file")

    except Exception as e:
        st.error(f"❌ Validation Error: {e}")
        st.info("💡 The validation failed, but your data is still saved. You can proceed without validation.")


def process_uploaded_file(uploaded_file, product_type: str):
    """Process the uploaded ZIP file and display results"""

    # Skip re-processing if already done for this exact file and product type.
    # Streamlit re-runs the script on every widget interaction (including button clicks),
    # so the file uploader still holds the previous file — guard against redundant work.
    if (st.session_state.get('phase_1_complete', False)
            and st.session_state.get('_uploaded_file_name') == uploaded_file.name
            and st.session_state.get('product_type') == product_type):
        consolidated_df = st.session_state.consolidated_df
        st.success(f"✅ Loaded {len(consolidated_df)} unique products (cached)")
    else:
        # Read uploaded file
        zip_bytes = BytesIO(uploaded_file.read())

        # Step 1: Load and parse files
        with st.spinner("📂 Loading files from ZIP..."):
            monthly_data, load_errors = load_monthly_data(zip_bytes)

        if load_errors:
            st.error("**File Loading Errors:**")
            for error in load_errors:
                st.error(f"• {error}")
            return

        # Display loaded files
        st.success(f"✅ Loaded {len(monthly_data)} monthly files")

        # Show which months were loaded
        months_loaded = sorted(monthly_data.keys(), key=lambda x: get_month_order().index(x))
        st.info(f"📅 Months loaded: {', '.join(months_loaded)}")

        # Step 2: Validate files
        with st.spinner("🔍 Validating data files..."):
            is_valid, validation_errors = validate_all_files(monthly_data)

        if not is_valid:
            st.error("**Validation Errors:**")
            for error in validation_errors:
                st.error(f"• {error}")
            return

        st.success("✅ All files validated successfully")

        # Step 3: Consolidate data
        with st.spinner("🔄 Consolidating data..."):
            consolidated_df = consolidate_data(monthly_data, product_type)

        if consolidated_df.empty:
            st.error("No data to consolidate. Please check your input files.")
            return

        st.success(f"✅ Consolidated {len(consolidated_df)} unique products")

        # Save to session state
        save_consolidation_results(product_type, monthly_data, consolidated_df)
        st.session_state['_uploaded_file_name'] = uploaded_file.name

    # Category Validation Section
    st.markdown("---")
    st.subheader("🔍 Category Validation (Optional)")

    st.info("💡 Use AI to validate and improve Level 3 (specific) categories. Helps minimize 'Other' classifications. L1 and L2 remain unchanged.")

    # Two buttons: Test with sample, or validate all
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧪 Test Validation (50 products)", type="secondary", use_container_width=True):
            # Validate just first 50 products as a test
            test_sample = consolidated_df.head(50).copy()
            validate_categories(test_sample, product_type, is_test=True)

    with col2:
        if st.button("🤖 Validate All Categories", type="primary", use_container_width=True):
            validate_categories(consolidated_df, product_type, is_test=False)

    # Display preview
    st.markdown("---")
    st.subheader("📋 Data Preview")

    # Column selector for preview
    preview_columns = st.multiselect(
        "Select columns to preview",
        options=list(consolidated_df.columns),
        default=[
            'Product Title', 'Product Max Price',
            'Product Category L1', 'Product Category L2', 'Product Category L3',
            'Product Brand', 'Availability',
            'Product Popularity Jan', 'Product Popularity Dec'
        ]
    )

    if preview_columns:
        # Filter to only columns that exist
        preview_columns = [col for col in preview_columns if col in consolidated_df.columns]
        st.dataframe(
            consolidated_df[preview_columns],
            use_container_width=True,
            height=400
        )
    else:
        st.dataframe(consolidated_df, use_container_width=True, height=400)

    # Export preliminary results
    st.markdown("---")
    st.subheader("💾 Export Preliminary Results")

    st.info("💡 You can export the consolidated data now, or proceed to Phase 2 to add keywords first.")

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
    filename = f"{product_type}_preliminary_consolidated.xlsx"
    st.download_button(
        label="📥 Download Preliminary Excel",
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Summary statistics
    render_custom_divider()

    # Build metrics dictionary
    metrics = {"Total Products": (len(consolidated_df), "📦")}

    if 'Product Category L3' in consolidated_df.columns:
        categories_l3 = consolidated_df['Product Category L3'].value_counts()
        metrics["Categories (L3)"] = (len(categories_l3), "📁")

    if 'Availability' in consolidated_df.columns:
        available = (consolidated_df['Availability'] != 'Potential Gap').sum()
        metrics["Available Products"] = (available, "✅")

    # Render aligned summary
    render_summary_section("Summary Statistics", metrics, icon="📈")

    # Category breakdown (3-level system)
    if all(col in consolidated_df.columns for col in ['Product Category L1', 'Product Category L2', 'Product Category L3']):
        st.markdown("### 📊 Category Breakdown")

        tab1, tab2, tab3 = st.tabs(["Level 1 (Main)", "Level 2 (Sub)", "Level 3 (Specific)"])

        with tab1:
            l1_counts = consolidated_df['Product Category L1'].value_counts()
            st.bar_chart(l1_counts)
            st.caption(f"✅ L1 has {len(l1_counts)} main categories (never 'Other')")

        with tab2:
            l2_counts = consolidated_df['Product Category L2'].value_counts()
            st.bar_chart(l2_counts)
            other_count = (consolidated_df['Product Category L2'] == 'Other').sum()
            if other_count > 0:
                st.caption(f"ℹ️ {other_count} products have 'Other' at L2")

        with tab3:
            l3_counts = consolidated_df['Product Category L3'].value_counts()
            st.bar_chart(l3_counts)
            other_count = (consolidated_df['Product Category L3'] == 'Other').sum()
            if other_count > 0:
                st.caption(f"ℹ️ {other_count} products have 'Other' at L3")

    # Next step prompt
    render_custom_divider()
    render_info_banner(
        "✨ Phase 1 Complete! Proceed to Phase 2 to generate SEO keywords using AI.",
        "info"
    )

    # Navigation button
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        if st.button("Next: Generate Keywords →", type="primary", use_container_width=True):
            st.switch_page("pages/2_🔤_Keywords_Categories.py")


def main():
    """Main page rendering"""

    # Header Navigation
    render_header_navigation(current_page="Phase 1")

    # Page header
    render_page_header(
        title="Phase 1: Data Consolidation",
        subtitle="Upload and consolidate monthly product data from multiple files",
        icon="📊"
    )

    # Progress tracker
    render_progress_tracker(current_phase=1)

    # Sidebar
    render_sidebar_info(current_phase=1)

    # Check prerequisites
    is_ready, message = check_phase_prerequisites(1)

    if not is_ready:
        st.error(message)
        return

    # Main content
    st.markdown("### 📦 Product Type Selection")

    product_type = st.selectbox(
        "Select Product Type",
        options=[
            "Alcoholic Beverages",
            "Pets",
            "Electronics",
            "F&F (Later)",
            "Party & Celebration",
            "Toys",
            "Baby & Toddler",
            "Health & Beauty",
            "Sporting Goods",
            "Home & Garden",
            "Luggage & Bags",
            "Furniture",
            "Cameras & Optics",
            "Hardware",
        ],
        help="Choose the product category for your data"
    )

    st.markdown("---")
    st.markdown("### 📁 Upload Data Files")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload ZIP file containing monthly data",
        type=["zip"],
        help="Upload a ZIP file containing CSV/Excel files for each month"
    )

    # File format info
    with st.expander("📋 File Requirements", expanded=False):
        st.markdown("""
        **ZIP File Contents:**
        - Files for Jan-Dec 2025
        - Format: `Mon-2025.xlsx` or `Mon-2025.csv`
        - Example: `Jan-2025.xlsx`, `Feb-2025.csv`, `BWS Apr 2025.csv`

        **Required Columns:**
        - Product Title (or Title)
        - Brand
        - Availability
        - Price range max.
        - Popularity rank

        **Note:** December file is mandatory.
        """)

    if uploaded_file is not None:
        # Process the uploaded file
        process_uploaded_file(uploaded_file, product_type)

    # Show session data if already processed
    elif st.session_state.get('phase_1_complete', False):
        render_info_banner(
            f"✅ Data already consolidated for {st.session_state.product_type}. Upload a new file to start over, or proceed to Phase 2.",
            "info"
        )

        st.markdown("### 📊 Current Data")
        st.info(f"**Product Type:** {st.session_state.product_type}")
        st.info(f"**Total Products:** {st.session_state.total_products}")

        # Show quick preview
        if st.session_state.consolidated_df is not None:
            with st.expander("📋 View Data Preview"):
                st.dataframe(
                    st.session_state.consolidated_df.head(20),
                    use_container_width=True
                )

        # Navigation button
        col_left, col_center, col_right = st.columns([2, 1, 2])
        with col_center:
            if st.button("Next: Generate Keywords →", type="primary", use_container_width=True):
                st.switch_page("pages/2_🔤_Keywords_Categories.py")


if __name__ == "__main__":
    main()
