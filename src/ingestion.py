"""
File Ingestion Module
Handles ZIP file extraction and reading CSV/Excel files.
"""

import zipfile
import pandas as pd
from io import BytesIO
from typing import Dict, Tuple, Optional
import re


# Valid month names for filename parsing
VALID_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# Month name to number mapping
MONTH_TO_NUM = {month: idx + 1 for idx, month in enumerate(VALID_MONTHS)}

# Alternative month name spellings (maps to standard 3-letter abbreviation)
MONTH_ALIASES = {
    # Common 4-letter abbreviations
    "Sept": "Sep",

    # Full month names
    "January": "Jan",
    "February": "Feb",
    "March": "Mar",
    "April": "Apr",
    "May": "May",  # Already 3 letters
    "June": "Jun",
    "July": "Jul",
    "August": "Aug",
    "September": "Sep",
    "October": "Oct",
    "November": "Nov",
    "December": "Dec",
}


def extract_files_from_zip(zip_file: BytesIO) -> Dict[str, BytesIO]:
    """
    Extract all files from a ZIP archive.

    Args:
        zip_file: BytesIO object containing the ZIP file

    Returns:
        Dictionary mapping filename to file content as BytesIO
    """
    extracted_files = {}

    with zipfile.ZipFile(zip_file, 'r') as zf:
        for filename in zf.namelist():
            # Skip directories and hidden files
            if filename.endswith('/') or filename.startswith('__MACOSX'):
                continue

            # Get just the filename without path
            base_filename = filename.split('/')[-1]

            # Skip hidden files
            if base_filename.startswith('.'):
                continue

            # Read file content
            file_content = BytesIO(zf.read(filename))
            extracted_files[base_filename] = file_content

    return extracted_files


def parse_filename(filename: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Parse filename to extract month, year, and file extension.

    Supported formats:
    - Mon-YYYY.ext (e.g., Jan-2025.xlsx, Feb-2025.csv)
    - Prefix Mon YYYY.ext (e.g., BWS Apr 2025.csv, Pets Jan 2025.xlsx)
    - Also handles Sept for September

    Args:
        filename: The filename to parse

    Returns:
        Tuple of (month_name, year, extension) or (None, None, None) if invalid
    """
    # Pattern 1: Mon-YYYY.ext (e.g., Jan-2025.xlsx)
    pattern1 = r'^([A-Za-z]{3,9})-(\d{4})\.(xlsx|csv)$'

    # Pattern 2: Prefix Mon YYYY.ext (e.g., BWS Apr 2025.csv, BWS Sept 2025.csv)
    pattern2 = r'^.+\s+([A-Za-z]{3,9})\s+(\d{4})\.(xlsx|csv)$'

    # Pattern 3: Mon YYYY.ext (e.g., Apr 2025.csv) - without prefix
    pattern3 = r'^([A-Za-z]{3,9})\s+(\d{4})\.(xlsx|csv)$'

    match = None

    # Try each pattern
    for pattern in [pattern1, pattern2, pattern3]:
        match = re.match(pattern, filename, re.IGNORECASE)
        if match:
            break

    if not match:
        return None, None, None

    month_name = match.group(1).capitalize()
    year = int(match.group(2))
    extension = match.group(3).lower()

    # Handle month aliases (e.g., Sept -> Sep)
    if month_name in MONTH_ALIASES:
        month_name = MONTH_ALIASES[month_name]

    # Validate month name
    if month_name not in VALID_MONTHS:
        return None, None, None

    return month_name, year, extension


def read_data_file(file_content: BytesIO, extension: str) -> pd.DataFrame:
    """
    Read a CSV or Excel file into a pandas DataFrame.
    Handles various encodings (UTF-8, UTF-16, Latin-1) and delimiters.
    Also handles files with header rows to skip.

    Args:
        file_content: BytesIO object containing file data
        extension: File extension ('csv' or 'xlsx')

    Returns:
        pandas DataFrame with file contents
    """
    file_content.seek(0)  # Reset file pointer

    if extension == 'csv':
        # Try multiple encodings and delimiters for CSV files
        encodings_to_try = ['utf-16', 'utf-8', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        delimiters_to_try = ['\t', ',', ';', '|']
        skip_rows_options = [0, 1, 2]  # Try skipping 0, 1, or 2 header rows

        best_df = None
        best_score = 0

        for encoding in encodings_to_try:
            for delimiter in delimiters_to_try:
                for skip_rows in skip_rows_options:
                    try:
                        file_content.seek(0)  # Reset pointer for each attempt
                        df = pd.read_csv(
                            file_content,
                            encoding=encoding,
                            sep=delimiter,
                            skiprows=skip_rows,
                            engine='python'  # Use Python engine for better error handling
                        )

                        # Clean column names (remove null bytes and BOM if present)
                        df.columns = [
                            col.replace('\x00', '').replace('\ufeff', '').replace('\ufffe', '').replace('\xff\xfe', '').replace('\xfe\xff', '').strip() if isinstance(col, str) else col
                            for col in df.columns
                        ]

                        # Clean all string data (remove null bytes from values)
                        for col in df.columns:
                            if df[col].dtype == 'object':
                                df[col] = df[col].apply(
                                    lambda x: x.replace('\x00', '').strip() if isinstance(x, str) else x
                                )

                        # Check if columns look reasonable (no null bytes remaining)
                        has_good_columns = all(
                            '\x00' not in str(col) for col in df.columns
                        )

                        # Score this attempt based on column name matching
                        # Prioritize versions that have expected column names
                        if not df.empty and len(df.columns) > 1 and has_good_columns:
                            # Check how many expected columns are present
                            expected_cols = ['popularity rank', 'title', 'brand', 'availability', 'price range max']
                            col_names_lower = [str(col).lower().strip() for col in df.columns]

                            # Check if each expected column is present (allows for trailing punctuation)
                            matches = 0
                            for expected in expected_cols:
                                # Check for exact match or match with trailing period
                                if expected in col_names_lower or f"{expected}." in col_names_lower:
                                    matches += 1

                            # Score heavily weighted by column name matches
                            # Each expected column match = 1000 points
                            # Number of columns = 10 points
                            # Number of rows = 1 point
                            score = (matches * 1000) + (len(df.columns) * 10) + len(df)

                            if score > best_score:
                                best_df = df
                                best_score = score

                    except (UnicodeDecodeError, UnicodeError):
                        continue
                    except Exception:
                        continue

        if best_df is not None:
            return best_df
        else:
            raise ValueError("Could not decode CSV file with any supported encoding or delimiter")

    elif extension == 'xlsx':
        return pd.read_excel(file_content, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file extension: {extension}")


def load_monthly_data(zip_file: BytesIO) -> Tuple[Dict[str, pd.DataFrame], list]:
    """
    Load all monthly data files from a ZIP archive.

    Args:
        zip_file: BytesIO object containing the ZIP file

    Returns:
        Tuple of:
        - Dictionary mapping month name to DataFrame
        - List of error messages (empty if all valid)
    """
    errors = []
    monthly_data = {}

    # Extract all files from ZIP
    extracted_files = extract_files_from_zip(zip_file)

    if not extracted_files:
        errors.append("No valid files found in ZIP archive")
        return monthly_data, errors

    for filename, file_content in extracted_files.items():
        # Parse filename
        month_name, year, extension = parse_filename(filename)

        if month_name is None:
            errors.append(f"Invalid filename format: '{filename}'. Expected formats: 'Mon-YYYY.xlsx', 'Mon YYYY.csv', or 'Prefix Mon YYYY.csv'")
            continue

        # Check for duplicate months
        if month_name in monthly_data:
            errors.append(f"Duplicate file for month: {month_name}")
            continue

        try:
            df = read_data_file(file_content, extension)
            monthly_data[month_name] = df
        except Exception as e:
            errors.append(f"Error reading '{filename}': {str(e)}")

    return monthly_data, errors


def get_month_order() -> list:
    """Return list of months in calendar order."""
    return VALID_MONTHS.copy()


def get_month_number(month_name: str) -> int:
    """Convert month name to number (1-12)."""
    return MONTH_TO_NUM.get(month_name, 0)
