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


def validate_all_files(monthly_data: Dict[str, pd.DataFrame]) -> Tuple[bool, List[str]]:
    """
    Validate all monthly data files.

    Args:
        monthly_data: Dictionary mapping month name to DataFrame

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check that December file exists (mandatory)
    if "Dec" not in monthly_data:
        errors.append("December 2025 file (Dec-2025.xlsx or Dec-2025.csv) is required but missing")

    # Validate columns for each file
    for month, df in monthly_data.items():
        filename = f"{month}-2025"
        column_errors = validate_required_columns(df, filename)
        errors.extend(column_errors)

    is_valid = len(errors) == 0
    return is_valid, errors


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
