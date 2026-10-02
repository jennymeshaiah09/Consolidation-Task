"""
Consolidation Module
Handles the pandas merge pipeline for consolidating monthly data.
"""

import pandas as pd
from typing import Dict, List, Optional
from .normalization import create_product_key, add_category_level_columns
from .validation import get_column_mapping, normalize_column_names
from .ingestion import get_month_order


def _series(df: pd.DataFrame, col_mapping: Dict[str, str], key: str, default_name: str) -> pd.Series:
    """Return a mapped column, or an empty series when the file does not have it."""
    col = col_mapping.get(key, default_name)
    if col in df.columns:
        return df[col]
    return pd.Series([pd.NA] * len(df), index=df.index)


def resolve_snapshot_month(
    monthly_data: Dict[str, pd.DataFrame],
    preferred: Optional[str] = None,
) -> tuple[Optional[str], str]:
    """Pick the month used for price and availability.

    ``preferred`` is honored when that month was uploaded. Otherwise the latest
    month in the ZIP is used and a warning is returned.
    """
    present = [month for month in get_month_order() if month in monthly_data]
    if not present:
        return None, "No recognised monthly files were found."
    if preferred and preferred in monthly_data:
        return preferred, ""
    latest = present[-1]
    if preferred:
        return latest, (
            f"{preferred} is not in this ZIP. "
            f"Price and availability will come from {latest}."
        )
    return latest, ""


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

        titles = _series(df, col_mapping, "Product Title", "Product Title")
        brands = _series(df, col_mapping, "Brand", "Brand")
        categories = (
            df["Source Category"]
            if "Source Category" in df.columns
            else pd.Series([pd.NA] * len(df), index=df.index)
        )

        # Extract product info
        for idx in df.index:
            title = titles.loc[idx]
            brand = brands.loc[idx]
            product_key = create_product_key(title)

            if product_key:  # Skip empty keys
                all_products.append({
                    'product_key': product_key,
                    'Product Title': title,
                    'Product Brand': "" if pd.isna(brand) else brand,
                    'Source Category': "" if pd.isna(categories.loc[idx]) else categories.loc[idx],
                })

    # Create DataFrame and remove duplicates (keep first occurrence)
    products_df = pd.DataFrame(all_products)

    if products_df.empty:
        return pd.DataFrame(columns=['product_key', 'Product Title', 'Product Brand', 'Source Category'])

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

    titles = _series(df, col_mapping, "Product Title", "Product Title")
    popularity = _series(df, col_mapping, "Popularity rank", "Popularity rank")

    # Create product key and extract popularity
    result = pd.DataFrame({
        'product_key': titles.apply(create_product_key),
        f'Product Popularity {month}': popularity
    })

    # Remove duplicates
    result = result.drop_duplicates(subset=['product_key'], keep='first')

    return result


def get_snapshot_data(monthly_data: Dict[str, pd.DataFrame], month: str) -> pd.DataFrame:
    """Extract price and availability from the chosen snapshot month."""
    if not month or month not in monthly_data:
        return pd.DataFrame(columns=['product_key', 'Product Max Price', 'Availability'])

    df = monthly_data[month].copy()
    df = normalize_column_names(df)
    col_mapping = get_column_mapping(df)

    titles = _series(df, col_mapping, "Product Title", "Product Title")
    prices = _series(df, col_mapping, "Price range max.", "Price range max.")
    availability = _series(df, col_mapping, "Availability", "Availability")

    result = pd.DataFrame({
        'product_key': titles.apply(create_product_key),
        'Product Max Price': prices,
        'Availability': availability
    })

    # Remove duplicates
    result = result.drop_duplicates(subset=['product_key'], keep='first')

    return result


def get_december_data(monthly_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Backward-compatible wrapper. Prefer get_snapshot_data."""
    return get_snapshot_data(monthly_data, "Dec")


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


def consolidate_data(
    monthly_data: Dict[str, pd.DataFrame],
    product_type: str,
    snapshot_month: Optional[str] = None,
) -> pd.DataFrame:
    """
    Main consolidation function that merges all monthly data.

    Args:
        monthly_data: Dictionary mapping month name to DataFrame
        product_type: Product type, or "General catalog" to skip built-in taxonomy
        snapshot_month: Month used for price and availability. Latest month if omitted.

    Returns:
        Consolidated DataFrame matching the output template
    """
    months = get_month_order()
    snapshot_month, _warning = resolve_snapshot_month(monthly_data, snapshot_month)

    # Step 1: Build master product list
    master_df = build_master_product_list(monthly_data)

    if master_df.empty:
        return pd.DataFrame()

    # Step 2: Categories — visitor column, general catalog, or built-in taxonomy
    source = master_df.get("Source Category", pd.Series(dtype=str)).astype(str).str.strip()
    has_source_category = source.ne("").any() and source.str.lower().ne("nan").any()
    if has_source_category:
        label = "General" if product_type == "General catalog" else product_type
        filled = source.where(source.ne("") & source.str.lower().ne("nan"), "Uncategorized")
        master_df["Product Category L1"] = label
        master_df["Product Category L2"] = filled
        master_df["Product Category L3"] = filled
    elif product_type == "General catalog":
        master_df["Product Category L1"] = "General"
        master_df["Product Category L2"] = "Uncategorized"
        master_df["Product Category L3"] = "Uncategorized"
    else:
        master_df = add_category_level_columns(master_df, product_type, "Product Title")

    # Step 3: Merge snapshot-month price and availability
    snapshot_data = get_snapshot_data(monthly_data, snapshot_month or "")
    master_df = master_df.merge(snapshot_data, on='product_key', how='left')

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

    # Step 6: Keyword and search-volume columns are filled in later phases.
    # Monthly MSV columns are added only when a visitor uploads them.
    master_df['Product Keyword'] = ""
    master_df['Product Keyword Avg MSV'] = ""
    master_df['Peak Seasonality'] = ""

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

    # Add peak columns
    output_columns.extend(['Peak Seasonality', 'Peak Popularity'])

    # Select and reorder columns
    final_df = master_df[[col for col in output_columns if col in master_df.columns]]

    return final_df
