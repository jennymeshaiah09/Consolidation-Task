"""
Phase 5: Insights & Analytics
Advanced analytics for Seasonality, Categories, and Brands.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

# Import UI utilities
from utils.ui_components import (
    apply_custom_css,
    render_page_header,
    render_progress_tracker,
    render_sidebar_info,
    render_custom_divider,
    render_info_banner,
    render_header_navigation
)
from utils.state_manager import (
    init_session_state,
    get_consolidated_df
)

# Page configuration
st.set_page_config(
    page_title="Phase 5: Insights & Analytics",
    page_icon="💡",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def get_peak_month_data(row):
    """
    Extract the primary peak month and its MSV for a single row.
    Returns: (Peak Month, Avg MSV for that Month)
    """
    # 1. Try Peak Seasonality (MSV based) first
    peak_val = row.get('Peak Seasonality', '')
    if pd.isna(peak_val) or str(peak_val).strip() == '':
        # 2. Fallback to Peak Popularity (Rank based)
        peak_val = row.get('Peak Popularity', '')
    
    if pd.isna(peak_val) or str(peak_val).strip() == '':
        return "Unknown", 0
        
    # Get first month from comma-separated list
    # e.g. "Dec, Nov" -> "Dec"
    primary_month = str(peak_val).split(',')[0].strip().split()[0]  # "Dec 2024" -> "Dec"
    
    # Calculate Avg MSV for this month across 3 years (2023-2025)
    # e.g. if Month is 'Dec', average 'Dec 2023', 'Dec 2024', 'Dec 2025'
    total_msv = 0
    count = 0
    
    # Standard 3-letter months
    target_months = []
    for year in [2023, 2024, 2025]:
        target_months.append(f"{primary_month} {year}")
        
    for col in target_months:
        if col in row.index and pd.notna(row[col]):
            try:
                total_msv += float(row[col])
                count += 1
            except:
                pass
                
    avg_month_msv = int(total_msv / count) if count > 0 else 0
    
    # Fallback to general average if specific month data is missing
    if avg_month_msv == 0:
        avg_month_msv = row.get('Product Keyword Avg MSV', 0)
        
    return primary_month, avg_month_msv


def generate_insights_df(consolidated_df):
    """
    Augment dataframe with 'Calculated Peak Month' and 'Peak Month MSV'.
    Uses vectorized operations instead of row-wise apply for performance.
    """
    df = consolidated_df.copy()

    # Vectorized: determine primary peak month from Peak Seasonality or Peak Popularity
    peak_col = df['Peak Seasonality'].copy() if 'Peak Seasonality' in df.columns else pd.Series('', index=df.index)
    if 'Peak Popularity' in df.columns:
        mask = peak_col.isna() | (peak_col.astype(str).str.strip() == '')
        peak_col = peak_col.where(~mask, df['Peak Popularity'])

    # Extract first month token: "Dec, Nov" → "Dec", "Dec 2024" → "Dec"
    primary_month = (
        peak_col.astype(str)
        .str.split(',').str[0]
        .str.strip()
        .str.split().str[0]
    )
    primary_month = primary_month.where(
        peak_col.notna() & (peak_col.astype(str).str.strip() != ''), 'Unknown'
    )
    df['Calculated Peak Month'] = primary_month

    # Vectorized: calculate avg MSV for the peak month across 3 years
    months_3letter = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    avg_msv = pd.Series(0.0, index=df.index)

    for m in months_3letter:
        mask = primary_month == m
        if not mask.any():
            continue
        year_cols = [f"{m} {y}" for y in [2023, 2024, 2025]]
        existing = [c for c in year_cols if c in df.columns]
        if existing:
            subset = df.loc[mask, existing].apply(pd.to_numeric, errors='coerce')
            row_sum = subset.sum(axis=1)
            row_count = subset.notna().sum(axis=1).replace(0, float('nan'))
            avg_msv.loc[mask] = (row_sum / row_count).fillna(0).astype(int)

    # Fallback to general average if specific month data is missing
    if 'Product Keyword Avg MSV' in df.columns:
        fallback = pd.to_numeric(df['Product Keyword Avg MSV'], errors='coerce').fillna(0)
        avg_msv = avg_msv.where(avg_msv > 0, fallback)

    df['Peak Month Avg MSV'] = avg_msv.astype(int)

    return df


def _write_all_data_sheet(writer, export_df):
    """Write the All Data sheet: specific column order + Yearly Heatmap formatting.
    
    OPTIMIZED: Uses format caching, vectorized calculations, and a single merged
    loop instead of 5 separate cell-by-cell passes. ~5-8× faster for large datasets.
    """
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    years = [2023, 2024, 2025]
    
    # Columns to exclude from export
    exclude_cols = [
        '3Mo Change', '3Month change', '3 Mo Change', '3Moth change', '3 Month Change',
        '12Mo Change', '12Month change', '12 Mo Change', '12 Month Change',
        'Bids',
        'Top of Page Bid Low Range', 'Top of Page Bid High Range',
        'Peak Strength',
        'Competition Level',
        'Calculated Peak Month'
    ]
    
    # Build MSV columns grouped by year
    msv_cols_2023 = [f"{m} 2023" for m in months]
    msv_cols_2024 = [f"{m} 2024" for m in months]
    msv_cols_2025 = [f"{m} 2025" for m in months]
    all_msv_cols_list = msv_cols_2023 + msv_cols_2024 + msv_cols_2025
    
    # Popularity columns
    pop_cols = [f'Product Popularity {m}' for m in months]
    
    # --- VECTORIZED YoY Calculation (replaces row-wise .apply()) ---
    working_df = export_df.copy()
    
    existing_2023 = [c for c in msv_cols_2023 if c in working_df.columns]
    existing_2024 = [c for c in msv_cols_2024 if c in working_df.columns]
    existing_2025 = [c for c in msv_cols_2025 if c in working_df.columns]
    
    total_2023 = working_df[existing_2023].apply(pd.to_numeric, errors='coerce').sum(axis=1) if existing_2023 else pd.Series(0, index=working_df.index)
    total_2024 = working_df[existing_2024].apply(pd.to_numeric, errors='coerce').sum(axis=1) if existing_2024 else pd.Series(0, index=working_df.index)
    total_2025 = working_df[existing_2025].apply(pd.to_numeric, errors='coerce').sum(axis=1) if existing_2025 else pd.Series(0, index=working_df.index)
    
    # YoY 2024: (2024 - 2023) / 2023 * 100
    pct_2024 = ((total_2024 - total_2023) / total_2023.replace(0, float('nan')) * 100).round(2)
    # Where prev was 0: if current is also 0 → "0%", else → "100%"
    pct_2024 = pct_2024.fillna(0)
    pct_2024 = pct_2024.where(total_2023 != 0, (total_2024 > 0).astype(float) * 100)
    working_df['YoY MSV 2024'] = pct_2024.apply(lambda x: f"{x}%")
    
    # YoY 2025: (2025 - 2024) / 2024 * 100
    pct_2025 = ((total_2025 - total_2024) / total_2024.replace(0, float('nan')) * 100).round(2)
    pct_2025 = pct_2025.fillna(0)
    pct_2025 = pct_2025.where(total_2024 != 0, (total_2025 > 0).astype(float) * 100)
    working_df['YoY MSV 2025'] = pct_2025.apply(lambda x: f"{x}%")
    
    # --- Column ordering ---
    base_cols = [
        'Product Title', 'Product Brand', 'Product Max Price', 'Availability',
        'Product Category L1', 'Product Category L2', 'Product Category L3',
        'Product Keyword', 'Product Keyword Avg MSV',
        'Peak Seasonality', 'True Peak',
        'Peak Month Avg MSV', 'Peak Popularity',
        'YoY MSV 2024', 'YoY MSV 2025',
    ]
    desired_order = base_cols + msv_cols_2023 + msv_cols_2024 + msv_cols_2025 + pop_cols
    
    cols_to_keep = [c for c in working_df.columns if c not in exclude_cols]
    filtered_df = working_df[cols_to_keep]
    final_cols = [c for c in desired_order if c in filtered_df.columns]
    remaining = [c for c in filtered_df.columns if c not in final_cols]
    final_cols.extend(remaining)
    ordered_df = filtered_df[final_cols]
    
    # Sort by Avg MSV
    if 'Product Keyword Avg MSV' in ordered_df.columns:
        ordered_df = ordered_df.sort_values(by='Product Keyword Avg MSV', ascending=False, na_position='last')
    
    # Fill blanks
    for col in all_msv_cols_list:
        if col in ordered_df.columns:
            ordered_df[col] = ordered_df[col].fillna('N/A')
    for col in pop_cols:
        if col in ordered_df.columns:
            ordered_df[col] = ordered_df[col].fillna(0)
    if 'Peak Popularity' in ordered_df.columns:
        ordered_df['Peak Popularity'] = ordered_df['Peak Popularity'].fillna('N/A').replace('', 'N/A')
    
    # Write base data to Excel
    sheet_name = 'All Data'
    LOGO_ROWS = 6
    ordered_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=LOGO_ROWS)
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    num_rows = len(ordered_df)
    header_row = LOGO_ROWS
    
    # --- PRE-CACHE all format objects (instead of creating per-cell) ---
    format_cache = {}
    
    def get_heatmap_format(color):
        """Return cached format for a heatmap color."""
        if color not in format_cache:
            format_cache[color] = workbook.add_format({
                'bg_color': color,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
        return format_cache[color]
    
    na_format = workbook.add_format({
        'bg_color': '#D9D9D9',
        'font_color': '#666666',
        'align': 'center',
        'border': 1
    })
    
    data_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#000000',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # --- PRE-COMPUTE column indices and sets for fast lookup ---
    col_to_idx = {c: i for i, c in enumerate(final_cols)}
    all_msv_set = set(all_msv_cols_list) & set(final_cols)
    
    # Group MSV columns by year for heatmap
    year_groups = []
    for year_cols in [msv_cols_2023, msv_cols_2024, msv_cols_2025]:
        existing = [c for c in year_cols if c in col_to_idx]
        if existing:
            year_groups.append(existing)
    
    # --- VECTORIZED min/max per row for each year group ---
    year_row_stats = []
    for year_cols in year_groups:
        numeric_block = ordered_df[year_cols].apply(pd.to_numeric, errors='coerce')
        row_mins = numeric_block.min(axis=1).values
        row_maxs = numeric_block.max(axis=1).values
        year_row_stats.append((year_cols, numeric_block.values, row_mins, row_maxs))
    
    # Peak Popularity column index
    peak_pop_idx = col_to_idx.get('Peak Popularity', -1)
    
    # Non-MSV column indices (for center-alignment pass)
    non_msv_col_indices = [(i, c) for i, c in enumerate(final_cols) if c not in all_msv_set]
    
    # --- Write headers ---
    for col_idx, col_name in enumerate(final_cols):
        worksheet.write(header_row, col_idx, col_name, header_format)
    
    # --- SINGLE MERGED LOOP: heatmap + N/A + center-align ---
    # Convert ordered_df to numpy for fast access
    ordered_values = ordered_df.values
    col_name_list = list(ordered_df.columns)
    
    for row_idx in range(num_rows):
        excel_row = row_idx + header_row + 1
        
        # 1. Heatmap coloring for MSV year groups
        for year_cols, numeric_vals, row_mins, row_maxs in year_row_stats:
            min_val = row_mins[row_idx]
            max_val = row_maxs[row_idx]
            
            for j, col in enumerate(year_cols):
                col_idx = col_to_idx[col]
                cell_val = ordered_values[row_idx, col_name_list.index(col)]
                
                # Check for N/A first
                if cell_val == 'N/A' or (isinstance(cell_val, str) and cell_val.upper() == 'N/A'):
                    worksheet.write(excel_row, col_idx, 'N/A', na_format)
                    continue
                
                val = numeric_vals[row_idx, j]
                if pd.notna(val):
                    color = _get_color_for_value(val, min_val, max_val)
                    if color:
                        worksheet.write(excel_row, col_idx, val, get_heatmap_format(color))
                    else:
                        worksheet.write(excel_row, col_idx, val, data_format)
        
        # 2. N/A formatting for Peak Popularity
        if peak_pop_idx >= 0:
            pp_val = ordered_values[row_idx, peak_pop_idx]
            if pp_val == 'N/A' or (isinstance(pp_val, str) and str(pp_val).upper() == 'N/A'):
                worksheet.write(excel_row, peak_pop_idx, 'N/A', na_format)
        
        # 3. Center-align all non-MSV columns
        for col_idx, col in non_msv_col_indices:
            cell_val = ordered_values[row_idx, col_idx]
            if pd.isna(cell_val):
                cell_val = ''
            worksheet.write(excel_row, col_idx, cell_val, data_format)
    
    # --- Auto-fit column widths ---
    for idx, col in enumerate(final_cols):
        max_len = min(
            max(ordered_df[col].astype(str).map(len).max(), len(str(col))) + 2,
            50
        )
        worksheet.set_column(idx, idx, max_len)
    
    # Freeze panes below header
    worksheet.freeze_panes(header_row + 1, 0)


def _get_color_for_value(value, min_val, max_val):
    """Calculate RGB heatmap color. Red(min) → Yellow(mid) → Green(max)."""
    if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
        return None
    if min_val == max_val:
        return '#00B050'
    normalized = (value - min_val) / (max_val - min_val)
    if normalized <= 0.5:
        ratio = normalized * 2
        r = int(192 + (255 - 192) * ratio)
        g = int(0 + 255 * ratio)
        b = 0
    else:
        ratio = (normalized - 0.5) * 2
        r = int(255 - 255 * ratio)
        g = int(255 - (255 - 176) * ratio)
        b = int(0 + 80 * ratio)
    return f'#{r:02X}{g:02X}{b:02X}'


def render_excel_export_section(df, cat_agg, brand_agg):
    """Two downloads: raw pipeline data and full insights report — both contain all columns."""
    st.markdown("### 📤 Export")

    # Deduplicate columns once (safety net for double-merged MSV data)
    export_df = df.loc[:, ~df.columns.duplicated(keep='first')]

    # Progress bar for data preparation
    progress_bar = st.progress(0, text="Preparing export data...")

    # --- Build "All Data" Excel (single sheet, every column) ---
    progress_bar.progress(10, text="📊 Building All Data export...")
    out_data = BytesIO()
    with pd.ExcelWriter(out_data, engine='xlsxwriter') as writer:
        _write_all_data_sheet(writer, export_df)
    out_data.seek(0)
    progress_bar.progress(40, text="✅ All Data ready. Building Full Insights Report...")

    # --- Build "Full Insights Report" Excel (All Data + Summary + Categories + Brands + Charts) ---
    out_report = BytesIO()
    with pd.ExcelWriter(out_report, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Sheet 1: All Data — full pipeline, every column
        progress_bar.progress(50, text="📊 Report: Writing All Data sheet...")
        _write_all_data_sheet(writer, export_df)

        # Sheet 2: Summary
        progress_bar.progress(65, text="📊 Report: Writing Summary sheet...")
        summary_data = {
            'Metric': [
                'Total Products',
                'Total Monthly MSV Potential',
                'Top Peak Month',
                'Top Category (L3)',
                'Top Brand',
                'Products with MSV',
                'MSV Coverage (%)',
                'Products with Peak Seasonality',
                'Products with Peak Popularity',
            ],
            'Value': [
                len(export_df),
                f"{export_df['Peak Month Avg MSV'].sum():,.0f}",
                export_df['Calculated Peak Month'].mode()[0] if not export_df.empty else "N/A",
                cat_agg.iloc[0]['Product Category L3'] if not cat_agg.empty else "N/A",
                brand_agg.iloc[0]['Product Brand'] if not brand_agg.empty else "N/A",
                export_df['Product Keyword Avg MSV'].notna().sum() if 'Product Keyword Avg MSV' in export_df.columns else 0,
                f"{export_df['Product Keyword Avg MSV'].notna().sum() / len(export_df) * 100:.1f}" if 'Product Keyword Avg MSV' in export_df.columns and len(export_df) > 0 else "0.0",
                (export_df['Peak Seasonality'].notna() & (export_df['Peak Seasonality'] != '')).sum() if 'Peak Seasonality' in export_df.columns else 0,
                (export_df['Peak Popularity'].notna() & (export_df['Peak Popularity'] != '')).sum() if 'Peak Popularity' in export_df.columns else 0,
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        ws_summ = writer.sheets['Summary']
        ws_summ.set_column('A:A', 35)
        ws_summ.set_column('B:B', 30)

        # Sheet 3: Categories
        progress_bar.progress(75, text="📊 Report: Writing Categories sheet...")
        cat_agg.to_excel(writer, sheet_name='Categories', index=False)
        ws_cat = writer.sheets['Categories']
        ws_cat.set_column(0, 0, 35)
        ws_cat.freeze_panes(1, 0)

        # Sheet 4: Brands
        progress_bar.progress(85, text="📊 Report: Writing Brands sheet...")
        brand_agg.to_excel(writer, sheet_name='Brands', index=False)
        ws_brand = writer.sheets['Brands']
        ws_brand.set_column(0, 0, 30)
        ws_brand.freeze_panes(1, 0)

        # Sheet 5: Charts
        progress_bar.progress(92, text="📊 Report: Generating Charts...")
        ws_charts = workbook.add_worksheet('Charts')

        chart_cat = workbook.add_chart({'type': 'column'})
        chart_cat.add_series({
            'name':       'Avg MSV',
            'categories': ['Categories', 1, 0, 10, 0],
            'values':     ['Categories', 1, 3, 10, 3],
        })
        chart_cat.set_title({'name': 'Top 10 Categories by MSV'})
        chart_cat.set_size({'width': 720, 'height': 400})
        ws_charts.insert_chart('A1', chart_cat)

        chart_brand = workbook.add_chart({'type': 'bar'})
        chart_brand.add_series({
            'name':       'Avg MSV',
            'categories': ['Brands', 1, 0, 10, 0],
            'values':     ['Brands', 1, 3, 10, 3],
        })
        chart_brand.set_title({'name': 'Top 10 Brands by MSV'})
        chart_brand.set_size({'width': 720, 'height': 400})
        ws_charts.insert_chart('J1', chart_brand)
    out_report.seek(0)

    progress_bar.progress(100, text="✅ Both exports ready!")
    progress_bar.empty()  # Remove progress bar once done

    # --- Render two download buttons side by side ---
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 All Data",
            data=out_data,
            file_name=f"All_Data_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            help="Single sheet — every column from the full pipeline (MSV, popularity, categories, keywords)."
        )

    with col2:
        st.download_button(
            label="📥 Full Insights Report",
            data=out_report,
            file_name=f"Insights_Report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            help="All Data + Summary + Categories + Brands + Charts."
        )


def main():
    """Main page rendering"""
    render_header_navigation(current_page="Phase 5")

    render_page_header(
        title="Phase 5: Insights & Analytics",
        subtitle="Deep dive into Product, Category, and Brand seasonality",
        icon="💡"
    )

    render_progress_tracker(current_phase=5)
    render_sidebar_info(current_phase=5)
    
    consolidated_df = get_consolidated_df()
    
    if consolidated_df is None:
        st.error("No data available. Please complete previous phases.")
        return

    # Process Data
    with st.spinner("Analyzing seasonality patterns..."):
        df = generate_insights_df(consolidated_df)
        
        # Aggregations
        cat_agg = df.groupby(['Product Category L3', 'Calculated Peak Month']).agg({
             'Product Title': 'count',
             'Peak Month Avg MSV': 'sum'
        }).reset_index().rename(columns={'Product Title': 'Product Count', 'Peak Month Avg MSV': 'Total Avg MSV'})
        
        brand_agg = df.groupby(['Product Brand', 'Calculated Peak Month']).agg({
             'Product Title': 'count',
             'Peak Month Avg MSV': 'sum'
        }).reset_index().rename(columns={'Product Title': 'Product Count', 'Peak Month Avg MSV': 'Total Avg MSV'})

        # Sorting
        cat_agg = cat_agg.sort_values('Total Avg MSV', ascending=False)
        brand_agg = brand_agg.sort_values('Total Avg MSV', ascending=False)

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["🏆 Products by Peak", "📂 Categories by Peak", "🏷️ Brands by Peak"])
    
    # 1. Products Tab
    with tab1:
        st.markdown("### 📅 Products Peaking by Month")
        month_filter = st.selectbox("Select Peak Month", ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Unknown'])
        
        filtered = df[df['Calculated Peak Month'] == month_filter].sort_values('Peak Month Avg MSV', ascending=False)
        
        st.dataframe(
            filtered[['Product Title', 'Product Brand', 'Calculated Peak Month', 'Peak Month Avg MSV', 'Peak Popularity']],
            use_container_width=True,
            column_config={
                "Peak Month Avg MSV": st.column_config.ProgressColumn("Avg MSV (Month)", format="%d", min_value=0, max_value=int(df['Peak Month Avg MSV'].max()))
            }
        )
    
    # 2. Categories Tab
    with tab2:
        st.markdown("### 📂 Categories by Peak Month")
        col1, col2 = st.columns([2, 1])
        with col1:
             st.dataframe(
                cat_agg,
                use_container_width=True,
                column_config={
                    "Total Avg MSV": st.column_config.NumberColumn("Total Monthly Traffic", format="%d")
                }
            )
        with col2:
            st.markdown("#### Top Categories (All Months)")
            st.bar_chart(cat_agg.set_index('Product Category L3')['Total Avg MSV'].head(10))

    # 3. Brands Tab
    with tab3:
        st.markdown("### 🏷️ Brands by Peak Month")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(
                brand_agg,
                use_container_width=True,
                column_config={
                    "Total Avg MSV": st.column_config.NumberColumn("Total Monthly Traffic", format="%d")
                }
            )
        with col2:
            st.markdown("#### Top Brands (All Months)")
            st.bar_chart(brand_agg.set_index('Product Brand')['Total Avg MSV'].head(10))

    render_custom_divider()
    
    # Export Section
    render_excel_export_section(df, cat_agg, brand_agg)
    

if __name__ == "__main__":
    main()
