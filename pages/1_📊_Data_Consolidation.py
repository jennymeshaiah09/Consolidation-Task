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
from src.llm_keywords import classify_other_products_batch, validate_api_key

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

def run_classification(consolidated_df: pd.DataFrame, product_type: str):
    """Run LLM classification for 'Other' products"""
    
    if not validate_api_key():
        st.error("❌ Google API Key not configured. Please add GOOGLE_API_KEY to your .env file.")
        return

    # Progress bar and status
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(progress, current, total):
        progress_bar.progress(progress)
        status_text.text(f"🤖 Classifying product {current} of {total}...")

    try:
        with st.spinner("🤖 Classifying 'Other' products with parallel AI..."):
            updated_df = classify_other_products_batch(
                consolidated_df,
                product_type,
                progress_callback=update_progress,
                batch_size=30,  # Optimized batch size
                max_workers=5   # Parallel workers
            )
        
        st.session_state.consolidated_df = updated_df
        st.success("✅ Classification complete! Product categories updated.")
        
        # Rerun to show updated data
        time.sleep(1)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Classification failed: {str(e)}")


def validate_categories(consolidated_df: pd.DataFrame, product_type: str, is_test: bool = False):
    """Validate and fix product categories using LLM"""
    if not validate_api_key():
        st.error("❌ Google API Key not configured. Please add GOOGLE_API_KEY to your .env file.")
        return

    # Determine category column
    category_col = 'Product Category L3' if 'Product Category L3' in consolidated_df.columns else 'Product Category'

    # Build product list for the validator
    products = []
    for idx, row in consolidated_df.iterrows():
        products.append({
            'title': str(row.get('Product Title', '')),
            'brand': str(row.get('Product Brand', '')),
            'assigned_category': str(row.get(category_col, 'Other')),
        })

    available_categories = load_categories_for_product_type(product_type)

    label = "sample" if is_test else "all"
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        with st.spinner(f"🔍 Validating {label} categories with AI..."):
            validator = CategoryValidator()
            validation_results = validator.validate_categories_batch(
                products, available_categories, batch_size=20
            )
            report = validator.generate_validation_report(validation_results)

        progress_bar.progress(1.0)
        status_text.text("Validation complete.")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Validated", report['total_products'])
        col2.metric("Correct", report['correct'])
        col3.metric("Incorrect", report['incorrect'])
        col4.metric("Accuracy", f"{report['accuracy']:.1%}")

        # Show misclassifications and offer to apply corrections
        if report['misclassifications']:
            st.markdown("#### ⚠️ Suggested Corrections")
            for item in report['misclassifications']:
                st.info(
                    f"**{item['title']}**\n"
                    f"Assigned: `{item['assigned_category']}` → Suggested: `{item['llm_suggested_category']}` "
                    f"(confidence: {item['confidence']})"
                )

            if st.button("✅ Apply Suggested Corrections", type="primary"):
                corrections = {item['title']: item['llm_suggested_category']
                               for item in report['misclassifications']}
                df = st.session_state.consolidated_df
                for idx, row in df.iterrows():
                    title = str(row.get('Product Title', ''))
                    if title in corrections:
                        df.at[idx, category_col] = corrections[title]
                st.session_state.consolidated_df = df
                save_consolidation_results(product_type, {}, df)
                st.success(f"✅ Applied {len(corrections)} corrections!")
                time.sleep(1)
                st.rerun()
        else:
            st.success("✅ All categories validated correctly!")

    except Exception as e:
        st.error(f"❌ Validation failed: {str(e)}")



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

    # Category Validation & Classification Section
    st.markdown("---")
    st.subheader("🔍 Category Management")

    st.info("💡 Use AI to improve 'Other' categories and validate Level 3 assignments.")

    # 1. Classify "Other" Products (The new feature)
    other_count = (consolidated_df['Product Category L3'] == 'Other').sum() if 'Product Category L3' in consolidated_df.columns else 0
    
    col_cls, col_brand = st.columns(2)
    
    with col_cls:
        if other_count > 0:
            st.warning(f"⚠️ {other_count} products classified as 'Other'.")
            if st.button(f"🤖 Auto-Classify 'Other' Products", type="primary", use_container_width=True):
                 run_classification(consolidated_df, product_type)
        else:
            st.success("✅ No 'Other' products found.")

    # 2. Extract Missing Brands (New Feature)
    from src.llm_keywords import extract_brands_batch
    
    # Check for missing brands
    def is_missing_brand(val):
        return str(val).lower().strip() in ('', 'nan', 'none', 'null')
        
    missing_brand_count = consolidated_df['Product Brand'].apply(is_missing_brand).sum()

    with col_brand:
        if missing_brand_count > 0:
            st.warning(f"⚠️ {missing_brand_count} products missing Brand.")
            if st.button(f"🏷️ Auto-Extract Missing Brands", type="primary", use_container_width=True):
                if not validate_api_key():
                    st.error("❌ Google API Key not configured.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_brand_progress(progress, current, total):
                        progress_bar.progress(progress)
                        status_text.text(f"🏷️ Extracting brand {current} of {total}...")
                        
                    try:
                        with st.spinner("🤖 Extracting brands from titles..."):
                            updated_df = extract_brands_batch(
                                consolidated_df,
                                progress_callback=update_brand_progress,
                                batch_size=30,
                                max_workers=5
                            )
                        
                        st.session_state.consolidated_df = updated_df
                        save_consolidation_results(product_type, {}, updated_df)
                        st.success("✅ Brand extraction complete!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        else:
            st.success("✅ All products have brands.")

    st.markdown("#### Validation (Quality Check)")
    
    # Two buttons: Test with sample, or validate all
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧪 Test Validation (50 products)", type="secondary", use_container_width=True):
            # Validate just first 50 products as a test
            test_sample = consolidated_df.head(50).copy()
            validate_categories(test_sample, product_type, is_test=True)

    with col2:
        if st.button("🔎 Validate All Categories", type="secondary", use_container_width=True):
            validate_categories(consolidated_df, product_type, is_test=False)

    # Display preview
    st.markdown("---")
# ... (rest of file)
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
