"""
Product Data Consolidation Streamlit Application
Consolidates monthly product data and enriches with LLM-generated keywords.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom modules
from src.ingestion import load_monthly_data, get_month_order
from src.validation import validate_all_files
from src.consolidation import consolidate_data
from src.llm_keywords import (
    generate_keywords_batch,
    validate_api_key,
    test_api_connection
)


# Page configuration
st.set_page_config(
    page_title="Product Data Consolidation",
    page_icon="📊",
    layout="wide"
)


def main():
    st.title("📊 Product Data Consolidation Tool")
    st.markdown("---")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # Product type selection
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

        # API Key status
        st.subheader("API Status")
        if validate_api_key():
            st.success("✅ Google Gemini API Key configured")
            if st.button("Test API Connection"):
                with st.spinner("Testing connection..."):
                    success, message = test_api_connection()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        else:
            st.error("❌ GOOGLE_API_KEY not found")
            st.info("Set the GOOGLE_API_KEY environment variable to enable keyword generation")

        st.markdown("---")

        # File format info
        st.subheader("File Requirements")
        st.markdown("""
        **ZIP File Contents:**
        - Files for Jan-Dec 2025
        - Format: `Mon-2025.xlsx` or `Mon-2025.csv`
        - Example: `Jan-2025.xlsx`, `Feb-2025.csv`

        **Required Columns:**
        - Product Title
        - Brand
        - Availability
        - Price range max.
        - Popularity rank

        **Note:** December file is mandatory.
        """)

    # Main content area
    st.header(f"Upload {product_type} Product Data")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload ZIP file containing monthly data",
        type=["zip"],
        help="Upload a ZIP file containing CSV/Excel files for each month"
    )

    if uploaded_file is not None:
        # Process the uploaded file
        process_uploaded_file(uploaded_file, product_type)


def process_uploaded_file(uploaded_file, product_type: str):
    """Process the uploaded ZIP file and display results."""

    # Read uploaded file
    zip_bytes = BytesIO(uploaded_file.read())

    # Step 1: Load and parse files
    with st.spinner("Loading files from ZIP..."):
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
    st.info(f"Months loaded: {', '.join(months_loaded)}")

    # Step 2: Validate files
    with st.spinner("Validating data files..."):
        is_valid, validation_errors = validate_all_files(monthly_data)

    if not is_valid:
        st.error("**Validation Errors:**")
        for error in validation_errors:
            st.error(f"• {error}")
        return

    st.success("✅ All files validated successfully")

    # Step 3: Consolidate data
    with st.spinner("Consolidating data..."):
        consolidated_df = consolidate_data(monthly_data, product_type)

    if consolidated_df.empty:
        st.error("No data to consolidate. Please check your input files.")
        return

    st.success(f"✅ Consolidated {len(consolidated_df)} unique products")

    # Step 4: Generate keywords (optional)
    st.markdown("---")
    st.subheader("Keyword Generation")

    if not validate_api_key():
        st.warning("Google API key not configured. Keywords will be left empty.")
        st.info("Set GOOGLE_API_KEY environment variable to enable keyword generation.")
    else:
        generate_keywords = st.checkbox(
            "Generate SEO keywords using AI",
            value=True,
            help="Use Google Gemini (1.5 Flash) to generate SEO-friendly keywords for each product"
        )

        if generate_keywords:
            # Trial mode option
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

            if st.button("Generate Keywords", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(progress, current, total):
                    progress_bar.progress(progress)
                    status_text.text(f"Processing product {current} of {total}...")

                try:
                    with st.spinner("Generating keywords..."):
                        consolidated_df = generate_keywords_batch(
                            consolidated_df,
                            product_type,
                            progress_callback=update_progress,
                            max_products=max_products
                        )
                    if trial_mode and max_products:
                        st.success(f"✅ Keywords generated for first {max_products} products!")
                        st.info(f"Remaining {len(consolidated_df) - max_products} products have empty keywords.")
                    else:
                        st.success("✅ Keywords generated successfully!")
                    progress_bar.progress(1.0)
                    status_text.text("Complete!")
                except Exception as e:
                    st.error(f"Error generating keywords: {str(e)}")
                    return

    # Step 5: Display preview
    st.markdown("---")
    st.subheader("Data Preview")

    # Column selector for preview
    preview_columns = st.multiselect(
        "Select columns to preview",
        options=list(consolidated_df.columns),
        default=[
            'Product Title', 'Product Max Price',
            'Product Category L1', 'Product Category L2', 'Product Category L3',
            'Product Keyword', 'Product Brand', 'Availability',
            'Product Popularity Jan', 'Product Popularity Dec', 'Peak Popularity'
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

    # Step 6: Download
    st.markdown("---")
    st.subheader("Download Results")

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
    filename = f"{product_type}_consolidated_data.xlsx"
    st.download_button(
        label="📥 Download Consolidated Excel",
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

    # Statistics
    st.markdown("---")
    st.subheader("Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Products", len(consolidated_df))

    with col2:
        if 'Product Category L3' in consolidated_df.columns:
            categories = consolidated_df['Product Category L3'].value_counts()
            st.metric("Categories (L3)", len(categories))

    with col3:
        available = (consolidated_df['Availability'] != 'Potential Gap').sum()
        st.metric("Available Products", available)

    with col4:
        has_keywords = (consolidated_df['Product Keyword'] != '').sum()
        st.metric("With Keywords", has_keywords)

    # Category breakdown (3-level system)
    if all(col in consolidated_df.columns for col in ['Product Category L1', 'Product Category L2', 'Product Category L3']):
        st.markdown("### Category Breakdown")

        tab1, tab2, tab3 = st.tabs(["Level 1", "Level 2", "Level 3"])

        with tab1:
            l1_counts = consolidated_df['Product Category L1'].value_counts()
            st.bar_chart(l1_counts)

        with tab2:
            l2_counts = consolidated_df['Product Category L2'].value_counts()
            st.bar_chart(l2_counts)

        with tab3:
            l3_counts = consolidated_df['Product Category L3'].value_counts()
            st.bar_chart(l3_counts)


if __name__ == "__main__":
    main()
