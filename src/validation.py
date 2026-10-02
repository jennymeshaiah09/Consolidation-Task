"""
Validation Module
Handles validation of input data files and required columns.
"""

import pandas as pd
from typing import Dict, List, Tuple


# Required columns in input files
REQUIRED_COLUMNS = [
    "Title",  # Can also be "Product Title"
    "Brand",
    "Availability",
    "Price range max.",
    "Popularity rank"
]

# Column aliases - alternative names for required columns
COLUMN_ALIASES = {
    "Product Title": "Title",
    "Title": "Title",
}


def validate_required_columns(df: pd.DataFrame, filename: str) -> List[str]:
    """
    Validate that a DataFrame contains all required columns.
    Handles column aliases (e.g., "Title" and "Product Title").

    Args:
        df: pandas DataFrame to validate
        filename: Name of the file (for error messages)

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    df_columns = [col.strip() if isinstance(col, str) else str(col) for col in df.columns]

    for required_col in REQUIRED_COLUMNS:
        # Check for exact match or case-insensitive match
        found = False

        # Check the required column itself (allows for trailing period)
        for col in df_columns:
            col_lower = col.lower()
            required_lower = required_col.lower()
            # Match exact or with trailing period
            if col_lower == required_lower or col_lower == f"{required_lower}.":
                found = True
                break

        # Also check aliases
        if not found:
            for alias, canonical in COLUMN_ALIASES.items():
                if canonical == required_col:
                    for col in df_columns:
                        col_lower = col.lower()
                        alias_lower = alias.lower()
                        # Match exact or with trailing period
                        if col_lower == alias_lower or col_lower == f"{alias_lower}.":
                            found = True
                            break
                if found:
                    break

        if not found:
            errors.append(f"Missing required column '{required_col}' (or alias like 'Product Title') in {filename}")

    return errors


# Public catalog fields. Only the title blocks consolidation.
# Office exports still match through FIELD_ALIASES.
FIELD_ALIASES = {
    "Product Title": [
        "product title", "title", "name", "product name", "item name", "item",
    ],
    "Brand": ["brand", "product brand", "manufacturer", "maker"],
    "Availability": ["availability", "stock", "stock status", "in stock"],
    "Price range max.": [
        "price range max.", "price range max", "price", "max price",
        "product max price", "price max",
    ],
    "Popularity rank": ["popularity rank", "popularity", "rank", "sales rank"],
    "Source Category": [
        "category", "product category", "product category l3", "subcategory",
        "source category",
    ],
}

MAPPABLE_FIELDS = list(FIELD_ALIASES.keys())


def guess_column_mapping(columns: List[str]) -> Dict[str, str]:
    """Match file columns to canonical fields. Unmatched fields are omitted."""
    lookup = {}
    for col in columns:
        if isinstance(col, str):
            lookup.setdefault(col.strip().lower(), col)

    mapping = {}
    used = set()
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            actual = lookup.get(alias)
            if actual and actual not in used:
                mapping[field] = actual
                used.add(actual)
                break
    return mapping


def apply_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """Rename mapped source columns to canonical field names."""
    df = normalize_column_names(df.copy())
    rename = {}
    for canonical, actual in mapping.items():
        if not actual or actual == "— not in file —":
            continue
        if actual in df.columns and actual != canonical:
            rename[actual] = canonical
    return df.rename(columns=rename)


def validate_all_files(monthly_data: Dict[str, pd.DataFrame]) -> Tuple[bool, List[str]]:
    """
    Validate monthly files after column mapping.

    A product title is required. Other catalog fields are optional.
    A missing snapshot month is reported by the caller, not rejected here.
    """
    errors = []

    if not monthly_data:
        errors.append("No monthly files were found in the ZIP.")
        return False, errors

    for month, df in monthly_data.items():
        columns = {
            col.strip().lower() if isinstance(col, str) else str(col).lower()
            for col in df.columns
        }
        if "product title" not in columns and "title" not in columns:
            errors.append(f"{month} is missing a product title column.")

    return len(errors) == 0, errors


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names by stripping whitespace.

    Args:
        df: pandas DataFrame

    Returns:
        DataFrame with normalized column names
    """
    df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]
    return df


def get_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Create a mapping from required column names to actual column names in the DataFrame.
    Handles case-insensitive matching and column aliases.

    Args:
        df: pandas DataFrame

    Returns:
        Dictionary mapping standard column name to actual column name in DataFrame
    """
    mapping = {}
    df_columns = list(df.columns)

    # Map to standard names used in code
    standard_names = {
        "Title": "Product Title",  # Map Title to Product Title for consistency
        "Brand": "Brand",
        "Availability": "Availability",
        "Price range max.": "Price range max.",
        "Popularity rank": "Popularity rank"
    }

    for required_col in REQUIRED_COLUMNS:
        standard_name = standard_names.get(required_col, required_col)

        # First try exact match
        for actual_col in df_columns:
            if isinstance(actual_col, str) and actual_col.strip().lower() == required_col.lower():
                mapping[standard_name] = actual_col
                break

        # If not found, try aliases
        if standard_name not in mapping:
            for alias, canonical in COLUMN_ALIASES.items():
                if canonical == required_col:
                    for actual_col in df_columns:
                        if isinstance(actual_col, str) and actual_col.strip().lower() == alias.lower():
                            mapping[standard_name] = actual_col
                            break
                if standard_name in mapping:
                    break

    return mapping
