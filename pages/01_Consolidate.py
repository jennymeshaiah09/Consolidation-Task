"""
Phase 1: Data Consolidation
Upload and consolidate monthly product data from ZIP files
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import time

# Import core modules (LLM deps loaded lazily inside the helpers that need them)
from src.ingestion import load_monthly_data, get_month_order
from src.validation import (
    validate_all_files,
    guess_column_mapping,
    apply_column_mapping,
    MAPPABLE_FIELDS,
)
from src.consolidation import consolidate_data, resolve_snapshot_month
from src.taxonomy import load_categories_for_product_type

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
    check_phase_prerequisites,
    MAX_ZIP_BYTES,
)
from utils.sample_data import build_sample_catalog_zip

# Page configuration
st.set_page_config(
    page_title="Meridian · Consolidate",
    page_icon="◇",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()

def run_classification(consolidated_df: pd.DataFrame, product_type: str):
    """Run LLM classification for 'Other' products"""
    from src.llm_keywords import classify_other_products_batch, validate_api_key

    if not validate_api_key():
        st.error("Add a Gemini API key in the sidebar to classify products.")
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
    from src.category_validator import CategoryValidator
    from src.llm_keywords import validate_api_key

    if not validate_api_key():
        st.error("Add a Gemini API key in the sidebar to review categories.")
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



def _upload_token(uploaded_file) -> str:
    return f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"


def _load_zip(uploaded_file):
    """Read a ZIP once per file and keep the monthly frames in session."""
    token = _upload_token(uploaded_file)
    if (
        st.session_state.get("_upload_token") == token
        and st.session_state.get("pending_monthly")
    ):
        return st.session_state.pending_monthly, []

    if getattr(uploaded_file, "size", 0) > MAX_ZIP_BYTES:
        limit_mb = MAX_ZIP_BYTES // (1024 * 1024)
        return None, [f"This ZIP is over the {limit_mb} MB limit."]

    monthly_data, load_errors = load_monthly_data(BytesIO(uploaded_file.getvalue()))
    if load_errors:
        return None, load_errors

    st.session_state.pending_monthly = monthly_data
    st.session_state._upload_token = token
    return monthly_data, []


def process_uploaded_file(monthly_data, product_type: str, snapshot_choice: str, run_key: str):
    """Consolidate mapped monthly files and show the Phase 1 result."""

    # Skip re-processing when this exact mapping was already saved.
    if (
        st.session_state.get("phase_1_complete", False)
        and st.session_state.get("_uploaded_file_name") == run_key
        and st.session_state.get("product_type") == product_type
    ):
        consolidated_df = st.session_state.consolidated_df
        st.success(f"✅ Loaded {len(consolidated_df)} unique products (cached)")
    else:
        months_loaded = sorted(monthly_data.keys(), key=lambda x: get_month_order().index(x) if x in get_month_order() else 99)
        st.success(f"✅ Loaded {len(monthly_data)} monthly files")
        st.info(f"📅 Months loaded: {', '.join(months_loaded)}")

        is_valid, validation_errors = validate_all_files(monthly_data)
        if not is_valid:
            st.error("**Validation errors**")
            for error in validation_errors:
                st.error(f"• {error}")
            return

        preferred = None if snapshot_choice == "Latest available" else snapshot_choice
        snapshot_month, snapshot_warning = resolve_snapshot_month(monthly_data, preferred)
        if snapshot_warning:
            st.warning(snapshot_warning)
        if snapshot_month:
            st.caption(f"Price and availability come from {snapshot_month}.")

        with st.spinner("🔄 Consolidating data..."):
            consolidated_df = consolidate_data(monthly_data, product_type, snapshot_month)

        if consolidated_df.empty:
            st.error("No data to consolidate. Check that the title column is mapped.")
            return

        st.success(f"✅ Consolidated {len(consolidated_df)} unique products")

        save_consolidation_results(product_type, monthly_data, consolidated_df)
        st.session_state.snapshot_month = snapshot_month
        st.session_state["_uploaded_file_name"] = run_key

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
    from src.llm_keywords import extract_brands_batch, validate_api_key
    
    # Check for missing brands
    def is_missing_brand(val):
        return str(val).lower().strip() in ('', 'nan', 'none', 'null')
        
    missing_brand_count = consolidated_df['Product Brand'].apply(is_missing_brand).sum()

    with col_brand:
        if missing_brand_count > 0:
            st.warning(f"⚠️ {missing_brand_count} products missing Brand.")
            if st.button(f"🏷️ Auto-Extract Missing Brands", type="primary", use_container_width=True):
                if not validate_api_key():
                    st.error("Add a Gemini API key in the sidebar to fill missing brands.")
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
            value_len = consolidated_df[col].map(
                lambda v: len("" if pd.isna(v) else str(v))
            ).max()
            max_length = max(int(value_len) if pd.notna(value_len) else 0, len(str(col))) + 2
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
        st.markdown("### Category breakdown")

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
        "Phase 1 is done. Next, generate keywords. Fast mode does not need an API key.",
        "info"
    )

    # Navigation button
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        if st.button("Next: Keywords", type="primary", use_container_width=True):
            st.switch_page("pages/02_Keywords.py")


def main():
    """Main page rendering"""

    # Header Navigation
    render_header_navigation(current_page="Phase 1")

    # Page header
    render_page_header(
        title="Data consolidation",
        subtitle="Upload monthly catalogs, validate columns, and merge into one product master.",
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
    st.markdown("### Product type")

    product_type = st.selectbox(
        "Select product type",
        options=[
            "General catalog",
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
        help="General catalog keeps your own category column, or leaves categories unset. A named vertical uses the built-in taxonomy when you do not map a category.",
    )

    render_custom_divider()
    st.markdown("### Upload data")

    st.download_button(
        "Download a sample catalog",
        data=build_sample_catalog_zip(),
        file_name="meridian-sample-catalog.zip",
        mime="application/zip",
    )

    uploaded_file = st.file_uploader(
        "ZIP of monthly CSV or Excel files",
        type=["zip"],
        help=f"Up to {MAX_ZIP_BYTES // (1024 * 1024)} MB. Name files like Jan-2024.csv.",
    )

    with st.expander("File requirements", expanded=False):
        st.markdown("""
        **ZIP contents**
        - One file per month, any year
        - Names like `Jan-2024.csv`, `Apr 2024.xlsx`, or `Catalog Jun 2024.csv`

        **Columns**
        - A product title is required
        - Brand, availability, price, popularity rank, and category are optional
        - Match your headers on the next step. Office-style names are recognised automatically.

        Price and availability come from the snapshot month you choose. If that month is missing, the latest month in the ZIP is used.
        """)

    if uploaded_file is not None:
        monthly_data, load_errors = _load_zip(uploaded_file)
        if load_errors:
            for error in load_errors:
                st.error(error)
        elif monthly_data:
            sample_columns = []
            for frame in monthly_data.values():
                sample_columns = [str(col) for col in frame.columns]
                break
            guessed = guess_column_mapping(sample_columns)
            options = ["— not in file —"] + sample_columns

            st.markdown("### Match your columns")
            st.caption("Titles are required. Leave a field unset when your file does not have it.")
            mapping = {}
            for field in MAPPABLE_FIELDS:
                default = guessed.get(field)
                index = options.index(default) if default in options else 0
                choice = st.selectbox(
                    field,
                    options,
                    index=index,
                    key=f"map_{field}_{_upload_token(uploaded_file)}",
                )
                if choice != "— not in file —":
                    mapping[field] = choice

            present_months = [m for m in get_month_order() if m in monthly_data]
            snapshot_choice = st.selectbox(
                "Snapshot month for price and availability",
                ["Latest available"] + present_months,
                index=(present_months.index("Dec") + 1) if "Dec" in present_months else 0,
            )

            mapped_frames = {
                month: apply_column_mapping(frame, mapping)
                for month, frame in monthly_data.items()
            }
            mapping_sig = "|".join(f"{k}={v}" for k, v in sorted(mapping.items()))
            run_key = f"{_upload_token(uploaded_file)}|{product_type}|{snapshot_choice}|{mapping_sig}"

            already_done = (
                st.session_state.get("phase_1_complete", False)
                and st.session_state.get("_uploaded_file_name") == run_key
            )
            if st.button("Consolidate catalog", type="primary") or already_done:
                process_uploaded_file(mapped_frames, product_type, snapshot_choice, run_key)

    # Show session data if already processed
    elif st.session_state.get('phase_1_complete', False):
        render_info_banner(
            f"Data already consolidated for {st.session_state.product_type}. "
            "Upload a new file to start over, or continue to keywords.",
            "info"
        )

        st.markdown("### Current data")
        st.info(f"**Product type:** {st.session_state.product_type}")
        st.info(f"**Total products:** {st.session_state.total_products}")

        # Show quick preview
        if st.session_state.consolidated_df is not None:
            with st.expander("Data preview"):
                st.dataframe(
                    st.session_state.consolidated_df.head(20),
                    use_container_width=True
                )

        # Navigation button
        col_left, col_center, col_right = st.columns([2, 1, 2])
        with col_center:
            if st.button("Next: Keywords", type="primary", use_container_width=True):
                st.switch_page("pages/02_Keywords.py")


if __name__ == "__main__":
    main()
