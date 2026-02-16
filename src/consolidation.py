"""
Consolidation Module
Handles the pandas merge pipeline for consolidating monthly data.
"""

import pandas as pd
from typing import Dict, List, Optional
from .normalization import create_product_key, add_product_key_column, add_category_column, add_category_level_columns
from .validation import get_column_mapping, normalize_column_names
from .ingestion import get_month_order


def build_master_product_list(monthly_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build a master product list using the union of all product_key values.

    Args:
        monthly_data: Dictionary mapping month name to DataFrame

    Returns:
        DataFrame with unique products (product_key, Product Title, Brand)
    """
    all_products = []

    for month, df in monthly_data.items():
        df = normalize_column_names(df)
        col_mapping = get_column_mapping(df)

        title_col = col_mapping.get("Product Title", "Product Title")
        brand_col = col_mapping.get("Brand", "Brand")

        # Extract product info
        for _, row in df.iterrows():
            title = row.get(title_col, "")
            brand = row.get(brand_col, "")
            product_key = create_product_key(title)

            if product_key:  # Skip empty keys
                all_products.append({
                    'product_key': product_key,
                    'Product Title': title,
                    'Product Brand': brand
                })

    # Create DataFrame and remove duplicates (keep first occurrence)
    products_df = pd.DataFrame(all_products)

    if products_df.empty:
        return pd.DataFrame(columns=['product_key', 'Product Title', 'Product Brand'])

    # Drop duplicates based on product_key, keeping first
    products_df = products_df.drop_duplicates(subset=['product_key'], keep='first')

    return products_df.reset_index(drop=True)


def get_monthly_popularity(monthly_data: Dict[str, pd.DataFrame], month: str) -> pd.DataFrame:
    """
    Extract popularity data for a specific month.

    Args:
        monthly_data: Dictionary mapping month name to DataFrame
        month: Month name (e.g., "Jan", "Feb")

    Returns:
        DataFrame with product_key and popularity for that month
    """
    if month not in monthly_data:
        return pd.DataFrame(columns=['product_key', f'Product Popularity {month}'])

    df = monthly_data[month].copy()
    df = normalize_column_names(df)
    col_mapping = get_column_mapping(df)

    title_col = col_mapping.get("Product Title", "Product Title")
    popularity_col = col_mapping.get("Popularity rank", "Popularity rank")

    # Create product key and extract popularity
    result = pd.DataFrame({
        'product_key': df[title_col].apply(create_product_key),
        f'Product Popularity {month}': df[popularity_col]
    })

    # Remove duplicates
    result = result.drop_duplicates(subset=['product_key'], keep='first')

    return result


def get_december_data(monthly_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Extract December-specific data (Price and Availability).

    Args:
        monthly_data: Dictionary mapping month name to DataFrame

    Returns:
        DataFrame with product_key, price, and availability from December
    """
    if "Dec" not in monthly_data:
        return pd.DataFrame(columns=['product_key', 'Product Max Price', 'Availability'])

    df = monthly_data["Dec"].copy()
    df = normalize_column_names(df)
    col_mapping = get_column_mapping(df)

    title_col = col_mapping.get("Product Title", "Product Title")
    price_col = col_mapping.get("Price range max.", "Price range max.")
    avail_col = col_mapping.get("Availability", "Availability")

    result = pd.DataFrame({
        'product_key': df[title_col].apply(create_product_key),
        'Product Max Price': df[price_col],
        'Availability': df[avail_col]
    })

    # Remove duplicates
    result = result.drop_duplicates(subset=['product_key'], keep='first')

    return result


def calculate_peak_popularity(row: pd.Series, months: List[str]) -> str:
    """
    Calculate months with stable/consistent popularity among TOP 4 performing months.
    Returns months with low variance within the top 4.

    Note: Lower rank number = higher popularity.

    Args:
        row: pandas Series containing popularity columns
        months: List of month names

    Returns:
        Comma-separated month names with stable popularity from top 4, or empty string if insufficient data
    """
    popularity_cols = [f'Product Popularity {month}' for month in months]

    # Get values for each month
    values = {}
    for month, col in zip(months, popularity_cols):
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                try:
                    values[month] = float(val)
                except (ValueError, TypeError):
                    continue

    # Need at least 3 months of data to calculate variance
    if len(values) < 3:
        return ""

    # Sort months by rank (best first) and take TOP 4 only
    sorted_months = sorted(values.items(), key=lambda x: x[1])
    top_4_months = dict(sorted_months[:4])  # Top 4 best performing months

    # If less than 3 months in top 4, return the best one
    if len(top_4_months) < 3:
        return sorted_months[0][0]

    # Calculate mean and standard deviation of TOP 4 only
    top_ranks = list(top_4_months.values())
    mean_rank = sum(top_ranks) / len(top_ranks)
    variance = sum((x - mean_rank) ** 2 for x in top_ranks) / len(top_ranks)
    std_dev = variance ** 0.5

    # Find months within 1 std dev of mean (stable among top 4)
    stable_months = []
    for month, rank in top_4_months.items():
        if abs(rank - mean_rank) <= std_dev:
            stable_months.append(month)

    # If no stable months found, return the best performing month
    if not stable_months:
        return sorted_months[0][0]

    # Sort by rank (best first) and return as comma-separated
    stable_months.sort(key=lambda m: top_4_months[m])
    return ", ".join(stable_months)


def consolidate_data(monthly_data: Dict[str, pd.DataFrame], product_type: str) -> pd.DataFrame:
    """
    Main consolidation function that merges all monthly data.

    Args:
        monthly_data: Dictionary mapping month name to DataFrame
        product_type: Product type (BWS, Pets, Electronics)

    Returns:
        Consolidated DataFrame matching the output template
    """
    months = get_month_order()

    # Step 1: Build master product list
    master_df = build_master_product_list(monthly_data)

    if master_df.empty:
        return pd.DataFrame()

    # Step 2: Add L1, L2, L3 category columns based on product type
    master_df = add_category_level_columns(master_df, product_type, 'Product Title')

    # Step 3: Merge December data (Price and Availability)
    dec_data = get_december_data(monthly_data)
    master_df = master_df.merge(dec_data, on='product_key', how='left')

    # Apply business rules for December data
    # Price: If not available, set to "N/A"
    # Convert to string type to avoid mixed-type column issues
    master_df['Product Max Price'] = master_df['Product Max Price'].apply(
        lambda x: str(x) if pd.notna(x) else "N/A"
    )

    # Availability: If empty, set to "Potential Gap"
    master_df['Availability'] = master_df['Availability'].apply(
        lambda x: x if pd.notna(x) and str(x).strip() != "" else "Potential Gap"
    )

    # Step 4: Merge monthly popularity data
    for month in months:
        month_popularity = get_monthly_popularity(monthly_data, month)
        master_df = master_df.merge(month_popularity, on='product_key', how='left')

    # Step 5: Calculate Peak Popularity
    master_df['Peak Popularity'] = master_df.apply(
        lambda row: calculate_peak_popularity(row, months), axis=1
    )

    # Step 6: Add placeholder columns (to be filled later)
    master_df['Product Keyword'] = ""  # Will be filled by LLM
    master_df['Product Keyword Avg MSV'] = ""  # Left blank per requirements

    # Add MSV date columns (Jan 2023 to Dec 2025) - all blank
    years = [2023, 2024, 2025]
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for year in years:
        for month_num in range(1, 13):
            col_name = f"{month_names[month_num-1]} {year}"
            master_df[col_name] = ""

    master_df['Peak Seasonality'] = ""  # Left blank per requirements

    # Step 7: Reorder columns to match output template
    output_columns = [
        'Product Title',
        'Product Max Price',
        'Product Category L1',
        'Product Category L2',
        'Product Category L3',
        'Product Keyword',
        'Product Keyword Avg MSV',
        'Product Brand',
        'Availability',
    ]

    # Add monthly popularity columns
    for month in months:
        output_columns.append(f'Product Popularity {month}')

    # Add MSV date columns
    for year in years:
        for month_num in range(1, 13):
            output_columns.append(f"{month_names[month_num-1]} {year}")

    # Add peak columns
    output_columns.extend(['Peak Seasonality', 'Peak Popularity'])

    # Select and reorder columns
    final_df = master_df[[col for col in output_columns if col in master_df.columns]]

    return final_df
