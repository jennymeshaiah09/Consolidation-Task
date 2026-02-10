"""
Phase 3: MSV Management
Upload and integrate Monthly Search Volume data
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
    render_info_banner,
    render_custom_divider,
    render_header_navigation,
    render_summary_section
)
from utils.state_manager import (
    init_session_state,
    check_phase_prerequisites,
    get_consolidated_df,
    save_pipeline_state
)

# Page configuration
st.set_page_config(
    page_title="Phase 3: MSV Management",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def calculate_peak_seasonality(row):
    """
    Calculate Peak Seasonality from MSV monthly data.
    Returns the months with highest search volume (within 1 std dev of max).
    """
    # MSV columns: Jan 2023 - Dec 2025 (36 months)
    months = []
    for year in [2023, 2024, 2025]:
        for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']:
            months.append(f"{month} {year}")

    # Extract MSV values for these columns
    msv_values = {}
    for month_col in months:
        if month_col in row.index and pd.notna(row[month_col]):
            try:
                msv_values[month_col] = float(row[month_col])
            except (ValueError, TypeError):
                continue

    if not msv_values:
        return ""

    # Find months with highest search volume
    # Get top 4 months
    sorted_months = sorted(msv_values.items(), key=lambda x: x[1], reverse=True)
    top_4 = sorted_months[:4]

    if len(top_4) < 2:
        # If less than 2 months, return the highest
        return top_4[0][0] if top_4 else ""

    # Calculate mean and std dev of top 4
    top_values = [msv for _, msv in top_4]
    mean_msv = sum(top_values) / len(top_values)
    std_dev = (sum((x - mean_msv) ** 2 for x in top_values) / len(top_values)) ** 0.5

    # Find months within 1 std dev of mean
    threshold = mean_msv - std_dev
    peak_months = [month for month, msv in top_4 if msv >= threshold]

    # Extract just the month names (remove year)
    peak_month_names = [month.split()[0] for month in peak_months]

    return ", ".join(peak_month_names)


def calculate_true_peak(row):
    """
    Calculate True Peak using comprehensive 7-step algorithm.
    
    Steps:
    1. Monthly Average MSV (across 3 years per month)
    2. Z-Score for each month
    3. Monthly YoY Growth (avg of 2024 vs 2023 and 2025 vs 2024)
    4. Normalize Avg YoY
    5. Consistency Check (both YoY positive = 1, else 0)
    6. True Peak Score = (Z-Score × 0.4) + (Normalized YoY × 0.4) + (Consistency × 0.2)
    7. Select months with score > 0.5, max 3, or single highest
    
    Returns: comma-separated list of 1-3 peak months
    """
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    years = [2023, 2024, 2025]
    
    # Get MSV values for all months/years (treat blank as 0)
    msv_data = {}  # {month: {year: value}}
    for month in month_names:
        msv_data[month] = {}
        for year in years:
            col = f"{month} {year}"
            if col in row.index and pd.notna(row[col]):
                try:
                    msv_data[month][year] = float(row[col])
                except (ValueError, TypeError):
                    msv_data[month][year] = 0
            else:
                msv_data[month][year] = 0
    
    # Step 1: Monthly Average MSV
    monthly_averages = {}
    for month in month_names:
        values = [msv_data[month].get(year, 0) for year in years]
        monthly_averages[month] = sum(values) / len(values)
    
    # Check if all averages are 0
    if all(avg == 0 for avg in monthly_averages.values()):
        return ""
    
    # Step 2: Z-Score for each month
    avg_values = list(monthly_averages.values())
    mean = sum(avg_values) / len(avg_values)
    
    variance = sum((x - mean) ** 2 for x in avg_values) / len(avg_values)
    std_dev = variance ** 0.5
    
    z_scores = {}
    for month, avg in monthly_averages.items():
        if std_dev == 0:
            z_scores[month] = 0
        else:
            z_scores[month] = (avg - mean) / std_dev
    
    # Step 3: Monthly YoY Growth
    avg_yoy = {}
    for month in month_names:
        # YoY 2024 = (2024 - 2023) / 2023 * 100
        val_2023 = msv_data[month].get(2023, 0)
        val_2024 = msv_data[month].get(2024, 0)
        val_2025 = msv_data[month].get(2025, 0)
        
        if val_2023 == 0:
            yoy_2024 = 0
        else:
            yoy_2024 = ((val_2024 - val_2023) / val_2023) * 100
        
        if val_2024 == 0:
            yoy_2025 = 0
        else:
            yoy_2025 = ((val_2025 - val_2024) / val_2024) * 100
        
        avg_yoy[month] = (yoy_2024 + yoy_2025) / 2
    
    # Step 4: Normalize Avg YoY
    max_avg_yoy = max(avg_yoy.values()) if avg_yoy else 0
    
    normalized_yoy = {}
    for month, yoy in avg_yoy.items():
        if max_avg_yoy == 0:
            normalized_yoy[month] = 0
        else:
            normalized_yoy[month] = yoy / max_avg_yoy
    
    # Step 5: Consistency Check
    consistency = {}
    for month in month_names:
        val_2023 = msv_data[month].get(2023, 0)
        val_2024 = msv_data[month].get(2024, 0)
        val_2025 = msv_data[month].get(2025, 0)
        
        # Check if YoY is positive for both years
        yoy_2024_positive = val_2024 > val_2023
        yoy_2025_positive = val_2025 > val_2024
        
        consistency[month] = 1 if (yoy_2024_positive and yoy_2025_positive) else 0
    
    # Step 6: True Peak Score
    true_peak_scores = {}
    for month in month_names:
        score = (z_scores[month] * 0.4) + (normalized_yoy[month] * 0.4) + (consistency[month] * 0.2)
        true_peak_scores[month] = score
    
    # Step 7: Select True Peak Months
    # Get months with score > 0.5
    high_score_months = [(month, score) for month, score in true_peak_scores.items() if score > 0.5]
    
    if high_score_months:
        # Sort by score descending and take top 3
        high_score_months.sort(key=lambda x: x[1], reverse=True)
        peak_months = [month for month, _ in high_score_months[:3]]
        return ", ".join(peak_months)
    else:
        # No month above 0.5 - take single highest scoring month
        highest_month = max(true_peak_scores.items(), key=lambda x: x[1])[0]
        return highest_month


def merge_msv_data(consolidated_df, msv_df):
    """
    Merge MSV data with consolidated data.

    Args:
        consolidated_df: Consolidated product data
        msv_df: MSV data with Product Key/Title and MSV columns

    Returns:
        Merged DataFrame with MSV data
    """

    consolidated_df = consolidated_df.copy()

    # Pick the first join key that exists in BOTH dataframes
    join_key = None
    for candidate in ('Product Key', 'Product Title', 'Product Keyword'):
        if candidate in msv_df.columns and candidate in consolidated_df.columns:
            join_key = candidate
            break

    if join_key is None:
        raise ValueError(
            "MSV file must contain 'Product Key', 'Product Title', or 'Product Keyword' "
            "column that also exists in the consolidated data."
        )

    # Make re-merge idempotent: drop columns that will come from MSV (except join key)
    # and any leftover _msv-suffixed columns from a previous merge.
    incoming = {c for c in msv_df.columns if c != join_key}
    stale = [c for c in consolidated_df.columns
             if c in incoming or c.endswith('_msv')]
    if stale:
        consolidated_df = consolidated_df.drop(columns=stale, errors='ignore')

    st.info(f"Merging MSV data using '{join_key}' as the join key...")

    if join_key == 'Product Keyword':
        # Google Ads exports keywords in lowercase; consolidated data uses Title Case.
        # Merge on a temporary lowercase key, then drop it.  Also drop the MSV file's
        # Product Keyword so we keep our Title-Case version in consolidated_df.
        _cons = consolidated_df.copy()
        _msv  = msv_df.drop(columns=['Product Keyword']).copy()
        _cons['_join_lower'] = _cons['Product Keyword'].astype(str).str.lower().str.strip()
        _msv['_join_lower']  = msv_df['Product Keyword'].astype(str).str.lower().str.strip()
        merged_df = _cons.merge(_msv, on='_join_lower', how='left', suffixes=('', '_msv'))
        merged_df = merged_df.drop(columns=['_join_lower'])
    else:
        merged_df = consolidated_df.merge(
            msv_df,
            on=join_key,
            how='left',
            suffixes=('', '_msv')
        )

    # Calculate (or Recalculate) Peak Seasonality if missing or empty
    should_calculate = False
    
    if 'Peak Seasonality' not in merged_df.columns:
        should_calculate = True
    else:
        # Check if it's effectively empty (all NaN or empty strings)
        non_empty = merged_df['Peak Seasonality'].astype(str).str.strip().replace('nan', '').replace('None', '')
        if (non_empty == '').all():
            should_calculate = True

    if should_calculate:
        st.info("Calculating Peak Seasonality from MSV monthly data...")
        # Ensure we have month columns before trying
        sample_cols = [c for c in merged_df.columns if 'Jan 20' in str(c) or 'Dec 20' in str(c)]
        if sample_cols:
            merged_df['Peak Seasonality'] = merged_df.apply(calculate_peak_seasonality, axis=1)
            
            # Calculate True Peak using comprehensive algorithm
            st.info("Calculating True Peak (Z-score + YoY growth + consistency)...")
            merged_df['True Peak'] = merged_df.apply(calculate_true_peak, axis=1)
        else:
            st.warning("Could not calculate Peak Seasonality: No monthly MSV columns (e.g. 'Jan 2023') found.")

    return merged_df


def normalize_date_columns(df):
    """
    Convert datetime-formatted columns (2023-01-01 00:00:00) to "Jan 2023" format.

    Args:
        df: DataFrame with potential datetime-formatted columns

    Returns:
        DataFrame with normalized column names
    """
    df = df.copy()

    # Month name mapping
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }

    month_name_set = set(month_names.values())  # {'Jan', 'Feb', ...}

    # Find and rename datetime columns
    rename_map = {}
    for col in df.columns:
        col_str = str(col)

        # Handle Mon-YY format from Google Ads (e.g., Jan-23 → Jan 2023)
        parts = col_str.split('-')
        if (len(parts) == 2
                and parts[0] in month_name_set
                and parts[1].isdigit()
                and len(parts[1]) == 2):
            year = 2000 + int(parts[1])
            rename_map[col] = f"{parts[0]} {year}"
            continue

        # Try to parse as datetime
        try:
            # Handle different datetime formats
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                # Column is already datetime type
                dt = pd.to_datetime(col)
                month_name = month_names[dt.month]
                year = dt.year
                new_name = f"{month_name} {year}"
                rename_map[col] = new_name
            elif isinstance(col, str):
                # Try parsing string column name (JANUARY-2023, Jan-23, etc.)
                # We skip things that look like plain text but check if pandas sees a date
                dt = pd.to_datetime(col_str, errors='coerce')
                if pd.notna(dt):
                    month_name = month_names[dt.month]
                    year = dt.year
                    new_name = f"{month_name} {year}"
                    # Only rename if it actually looks like a monthly date (ignore "Product Keyword which might parse if weird")
                    if year >= 2000 and year <= 2030:
                        rename_map[col] = new_name
        except:
            continue

    if rename_map:
        st.info(f"🔄 Auto-detected {len(rename_map)} datetime-formatted columns. Converting to 'Mon YYYY' format...")
        df = df.rename(columns=rename_map)

    return df


def normalize_google_ads_columns(df):
    """
    Detect and rename Google Ads Keyword Planner export columns to match our schema.
    Keyword → Product Keyword, Monthly Search Estimated → Product Keyword Avg MSV.
    """
    rename_map = {}
    if 'Keyword' in df.columns and 'Product Keyword' not in df.columns:
        rename_map['Keyword'] = 'Product Keyword'
    if 'Monthly Search Estimated' in df.columns and 'Product Keyword Avg MSV' not in df.columns:
        rename_map['Monthly Search Estimated'] = 'Product Keyword Avg MSV'
    if rename_map:
        df = df.rename(columns=rename_map)
        st.info(f"🔄 Google Ads format detected. Renamed: {rename_map}")
    return df


def validate_msv_file(df):
    """
    Validate the uploaded MSV file structure.

    Returns:
        (is_valid, error_message, warnings)
    """
    errors = []
    warnings = []

    # Check for required columns (join key)
    has_product_key = ('Product Key' in df.columns
                       or 'Product Title' in df.columns
                       or 'Product Keyword' in df.columns)
    if not has_product_key:
        errors.append("File must contain 'Product Key', 'Product Title', or 'Product Keyword' column")

    # Check for MSV columns
    has_avg_msv = 'Product Keyword Avg MSV' in df.columns
    if not has_avg_msv:
        warnings.append("'Product Keyword Avg MSV' column not found")

    # Check for monthly MSV columns (both formats)
    expected_months = []
    for year in [2023, 2024, 2025]:
        for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']:
            expected_months.append(f"{month} {year}")

    found_months = [col for col in expected_months if col in df.columns]

    if len(found_months) == 0:
        warnings.append("No monthly MSV columns (Jan 2023 - Dec 2025) found")
    elif len(found_months) < 36:
        warnings.append(f"Only {len(found_months)}/36 monthly MSV columns found")

    is_valid = len(errors) == 0
    error_message = "; ".join(errors) if errors else ""

    return is_valid, error_message, warnings


def main():
    """Main page rendering"""
    render_header_navigation(current_page="Phase 3")

    # Page header
    render_page_header(
        title="Phase 3: MSV Management",
        subtitle="Upload and integrate Monthly Search Volume data",
        icon="📈"
    )

    # Progress tracker
    render_progress_tracker(current_phase=3)

    # Sidebar
    render_sidebar_info(current_phase=3)

    # Check prerequisites
    is_ready, message = check_phase_prerequisites(3)

    if not is_ready:
        st.error(message)
        st.info("Please complete Phase 1 (Data Consolidation) and Phase 2 (Keywords & Categories) first.")

        if st.button("← Back to Phase 1"):
            st.switch_page("pages/1_📊_Data_Consolidation.py")
        return

    # Get consolidated data
    consolidated_df = get_consolidated_df()

    if consolidated_df is None:
        st.error("No consolidated data found. Please complete Phase 1 first.")
        return

    # Main content
    st.markdown("### 📊 Current Data Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Products", len(consolidated_df))

    with col2:
        has_msv = 'Product Keyword Avg MSV' in consolidated_df.columns
        msv_status = "✅ Integrated" if has_msv else "⏳ Pending"
        st.metric("MSV Data", msv_status)

    with col3:
        if has_msv:
            with_msv = consolidated_df['Product Keyword Avg MSV'].notna().sum()
            coverage = (with_msv / len(consolidated_df)) * 100 if len(consolidated_df) > 0 else 0
            st.metric("MSV Coverage", f"{coverage:.1f}%")
        else:
            st.metric("MSV Coverage", "0%")

    render_custom_divider()

    # Two options: Manual upload or API
    st.markdown("### 🎯 Choose MSV Integration Method")

    tab1, tab2 = st.tabs(["📁 Manual Upload", "🤖 Automated API (Coming Soon)"])

    with tab1:
        st.markdown("#### Upload MSV Data File")

        st.info("""
        **File Requirements:**
        - Format: Excel (.xlsx) or CSV (.csv)
        - Must contain a join key: `Product Key`, `Product Title`, or `Product Keyword`
        - **Google Ads Keyword Planner exports are supported directly** — `Keyword` and
          `Monthly Search Estimated` are auto-renamed, and `Jan-23` date columns are
          converted to `Jan 2023`. The merge uses a case-insensitive keyword match.
        - Recommended columns:
          - `Product Keyword Avg MSV` - Average monthly search volume
          - Monthly columns: `Jan 2023`, `Feb 2023`, ..., `Dec 2025` (36 months)
            OR short format: `Jan-23`, `Feb-23`, etc. (auto-converted)
            OR datetime format: `2023-01-01`, `2023-02-01`, etc. (auto-converted)
          - `Peak Seasonality` (optional, will be calculated if not provided)
        """)

        uploaded_file = st.file_uploader(
            "Upload MSV data file",
            type=['xlsx', 'csv'],
            help="Upload Excel or CSV file containing MSV data"
        )

        if uploaded_file:
            try:
                # Read file
                if uploaded_file.name.endswith('.csv'):
                    msv_df = pd.read_csv(uploaded_file)
                else:
                    msv_df = pd.read_excel(uploaded_file)

                st.success(f"✅ File loaded: {len(msv_df)} products found")

                # Detect and rename Google Ads Keyword Planner columns
                msv_df = normalize_google_ads_columns(msv_df)

                # Normalize date columns (Mon-YY / datetime → "Jan 2023" format)
                msv_df = normalize_date_columns(msv_df)

                # Validate file structure
                is_valid, error_message, warnings = validate_msv_file(msv_df)

                if not is_valid:
                    st.error(f"❌ File validation failed: {error_message}")
                    return

                if warnings:
                    with st.expander("⚠️ Validation Warnings", expanded=True):
                        for warning in warnings:
                            st.warning(warning)

                # Show preview
                with st.expander("📋 MSV Data Preview", expanded=True):
                    st.dataframe(msv_df.head(10), use_container_width=True)

                # Merge button
                st.markdown("---")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("🔗 Merge MSV Data with Consolidated Data", type="primary", use_container_width=True):
                        with st.spinner("Merging MSV data..."):
                            try:
                                # Merge data
                                merged_df = merge_msv_data(consolidated_df, msv_df)

                                # Update session state and persist to disk
                                st.session_state.consolidated_df = merged_df
                                save_pipeline_state()

                                st.success(f"✅ MSV data merged successfully!")
                                st.success(f"✅ Peak Seasonality calculated for all products")

                                # Show updated metrics
                                with_msv = merged_df['Product Keyword Avg MSV'].notna().sum() if 'Product Keyword Avg MSV' in merged_df.columns else 0
                                coverage = (with_msv / len(merged_df)) * 100 if len(merged_df) > 0 else 0

                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.metric("Products with MSV", with_msv)
                                with col_b:
                                    st.metric("Coverage", f"{coverage:.1f}%")

                                st.info("You can now proceed to Phase 4 (Peak Analysis) to analyze Peak Popularity and Peak Seasonality!")

                                st.balloons()

                            except Exception as e:
                                st.error(f"❌ Error merging data: {e}")
                                st.exception(e)

                with col2:
                    if st.button("🔄 Clear and Re-upload", type="secondary", use_container_width=True):
                        st.rerun()

            except Exception as e:
                st.error(f"❌ Error reading file: {e}")
                st.info("Please ensure the file is a valid Excel (.xlsx) or CSV (.csv) file")

    with tab2:
        st.markdown("#### Automated MSV Lookup via Google Ads API")

        st.info("""
        **Status:** Awaiting Google Ads API Approval

        The automated MSV lookup requires:
        - ✅ Google Ads API credentials configured
        - ✅ OAuth refresh token generated
        - ⏳ Standard Access approval (currently Explorer access only)

        **Current Limitation:** Explorer access only works with test accounts.
        For production MSV data, Standard Access is required.
        """)

        render_info_banner(
            "💡 While waiting for API approval, use the **Manual Upload** tab to upload MSV data provided by Tenny.",
            "info"
        )

        if st.button("📖 View API Setup Documentation"):
            st.markdown("""
            ### Google Ads API Setup Steps

            1. **Apply for Standard Access**
               - Go to Google Ads API Centre
               - Click "Request Standard Access"
               - Provide use case description

            2. **Wait for Approval** (24-72 hours)

            3. **Test API Connection**
               - Run `python test_google_ads_api.py`
               - Run `python test_keyword_planner.py`

            4. **Enable Automated MSV**
               - Once approved, the automated option will be enabled

            For detailed instructions, see `GOOGLE_ADS_API_SETUP.md`
            """)

    render_custom_divider()

    # Information section
    st.markdown("### 📚 About MSV Data")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 📊 What is MSV?")
        st.markdown("""
        **Monthly Search Volume (MSV)** represents the number of times
        a keyword is searched on search engines per month.

        This data helps understand:
        - Product search demand
        - Seasonal trends
        - Keyword popularity over time
        """)

    with col2:
        st.markdown("#### 📁 Data Structure")
        st.markdown("""
        MSV data adds these columns to your dataset:

        - **Product Keyword Avg MSV** - Average search volume
        - **Jan 2023** through **Dec 2025** - Monthly values (36 columns)
        - **Peak Seasonality** - Months with highest search volume

        These enable Peak Seasonality analysis in Phase 4.
        """)

    render_custom_divider()

    # Navigation
    st.markdown("### 🗺️ Navigation")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back to Phase 2", use_container_width=True):
            st.switch_page("pages/2_🔤_Keywords_Categories.py")

    with col2:
        if st.button("🏠 Back to Home", use_container_width=True):
            st.switch_page("Home.py")

    with col3:
        # Check if MSV data exists
        has_msv = 'Product Keyword Avg MSV' in consolidated_df.columns if consolidated_df is not None else False

        if has_msv:
            if st.button("Phase 4: Peak Analysis →", type="primary", use_container_width=True):
                st.switch_page("pages/4_⭐_Peak_Analysis.py")
        else:
            st.button("Phase 4: Peak Analysis →", use_container_width=True, disabled=True, help="Upload MSV data first")


if __name__ == "__main__":
    main()
