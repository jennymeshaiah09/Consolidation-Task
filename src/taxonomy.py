"""
Taxonomy Module
Handles loading and managing product taxonomy from Excel file.
"""

import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


# Product type to Excel sheet name mapping
# Supports both legacy names (BWS, Pets, Electronics) and all Excel sheet names
SHEET_MAPPING = {
    # Legacy mappings (backward compatibility)
    "BWS": "Alcoholic Beverages",
    "Pets": "Pets",
    "Electronics": "Electronics",

    # All 14 Excel sheets (direct access)
    "F&F (Later)": "F&F (Later)",
    "Alcoholic Beverages": "Alcoholic Beverages",
    "Party & Celebration": "Party & Celebration",
    "Toys": "Toys",
    "Baby & Toddler": "Baby & Toddler",
    "Health & Beauty": "Health & Beauty",
    "Sporting Goods": "Sporting Goods",
    "Home & Garden": "Home & Garden",
    "Luggage & Bags": "Luggage & Bags",
    "Furniture": "Furniture",
    "Cameras & Optics": "Cameras & Optics",
    "Hardware": "Hardware",
}


def load_taxonomy(taxonomy_file: str = "Categories & subs.xlsx") -> Dict[str, pd.DataFrame]:
    """
    Load taxonomy from Excel file.

    Args:
        taxonomy_file: Path to the taxonomy Excel file

    Returns:
        Dictionary mapping product type to taxonomy DataFrame
    """
    taxonomy = {}

    # Get the path to the taxonomy file (in project root)
    project_root = Path(__file__).parent.parent
    
    # Check potential locations
    possible_paths = [
        project_root / taxonomy_file,
        project_root / "Examples" / taxonomy_file,
        project_root / "data" / taxonomy_file
    ]
    
    taxonomy_path = None
    for path in possible_paths:
        if path.exists():
            taxonomy_path = path
            break

    if taxonomy_path is None:
        raise FileNotFoundError(f"Taxonomy file not found in: {[str(p) for p in possible_paths]}")

    xl = pd.ExcelFile(taxonomy_path)

    # Load each product type's taxonomy
    for product_type, sheet_name in SHEET_MAPPING.items():
        if sheet_name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet_name)
            taxonomy[product_type] = df
        else:
            raise ValueError(f"Sheet '{sheet_name}' not found in taxonomy file")

    return taxonomy


def get_category_list(product_type: str, taxonomy: Dict[str, pd.DataFrame]) -> List[str]:
    """
    Get a list of all unique categories for a product type.
    Combines Level 1 and Level 2 for better granularity.

    Args:
        product_type: Product type (BWS, Pets, Electronics)
        taxonomy: Taxonomy dictionary from load_taxonomy()

    Returns:
        List of category strings in format "Level 1 > Level 2"
    """
    if product_type not in taxonomy:
        return []

    df = taxonomy[product_type]
    categories = []

    # Create "Level 1 > Level 2" format categories
    for _, row in df.iterrows():
        level1 = row.get('Level 1', '')
        level2 = row.get('Level 2', '')

        if pd.notna(level1) and pd.notna(level2):
            category = f"{level1} > {level2}"
            if category not in categories:
                categories.append(category)

    return sorted(categories)


def format_categories_for_llm(product_type: str, taxonomy: Dict[str, pd.DataFrame]) -> str:
    """
    Format category list for LLM prompt.

    Args:
        product_type: Product type (BWS, Pets, Electronics)
        taxonomy: Taxonomy dictionary from load_taxonomy()

    Returns:
        Formatted string of categories for LLM prompt
    """
    categories = get_category_list(product_type, taxonomy)

    if not categories:
        return "No categories available"

    # Format as numbered list
    formatted = "\n".join(f"{i+1}. {cat}" for i, cat in enumerate(categories))
    return formatted


def get_level1_category(full_category: str) -> str:
    """
    Extract Level 1 category from full category string.

    Args:
        full_category: Full category string (e.g., "Wine > Red Wine")

    Returns:
        Level 1 category (e.g., "Wine")
    """
    if " > " in full_category:
        return full_category.split(" > ")[0]
    return full_category


# Cache for loaded taxonomy (avoid reloading on every call)
_TAXONOMY_CACHE: Optional[Dict[str, pd.DataFrame]] = None


def get_taxonomy() -> Dict[str, pd.DataFrame]:
    """
    Get cached taxonomy or load if not cached.

    Returns:
        Taxonomy dictionary
    """
    global _TAXONOMY_CACHE

    if _TAXONOMY_CACHE is None:
        _TAXONOMY_CACHE = load_taxonomy()

    return _TAXONOMY_CACHE


def clear_taxonomy_cache():
    """Clear the taxonomy cache (useful for testing)."""
    global _TAXONOMY_CACHE
    _TAXONOMY_CACHE = None


def load_all_categories() -> List[str]:
    """
    Load all unique categories from all product types.
    Returns leaf categories (most specific level) from the generated keywords.

    Returns:
        List of all unique category names across all product types
    """
    try:
        # Import generated keywords
        from .generated_keywords import CATEGORY_KEYWORDS

        # Extract all category names (keys from the dictionary)
        all_categories = list(CATEGORY_KEYWORDS.keys())

        return sorted(all_categories)

    except ImportError:
        # Fallback: Load from Excel taxonomy if generated_keywords not available
        taxonomy = get_taxonomy()
        all_categories = set()

        for product_type, df in taxonomy.items():
            # Only use Level 2 and Level 3 for more specific categories
            # Skip Level 1 (too broad like "Alcoholic Beverages", "Pets", etc.)
            for level_col in ['Level 2', 'Level 3']:
                if level_col in df.columns:
                    categories = df[level_col].dropna().unique()
                    all_categories.update(categories)

        return sorted(list(all_categories))


def load_categories_for_product_type(product_type: str) -> List[str]:
    """
    Load categories for a specific product type only.

    Args:
        product_type: Product type (BWS, Pets, Electronics, etc.)

    Returns:
        List of category names for the specific product type
    """
    try:
        from .generated_keywords import CATEGORY_KEYWORDS

        mapped_type = SHEET_MAPPING.get(product_type, product_type)
        product_categories = CATEGORY_KEYWORDS.get(mapped_type, {})

        # Extract leaf categories (Level 2 and Level 3) — skip Level 1 (too broad)
        categories = set()
        for full_path in product_categories.keys():
            parts = full_path.split(" > ")
            for part in parts[1:]:
                categories.add(part.strip())

        return sorted(list(categories))

    except ImportError:
        # Fallback: Load from Excel taxonomy for specific product type
        taxonomy = get_taxonomy()

        if product_type not in taxonomy:
            # Try to map legacy names
            product_type = SHEET_MAPPING.get(product_type, product_type)

        if product_type not in taxonomy:
            raise ValueError(f"Product type '{product_type}' not found in taxonomy")

        df = taxonomy[product_type]
        categories = set()

        # Only use Level 2 and Level 3 for more specific categories
        # Skip Level 1 (too broad)
        for level_col in ['Level 2', 'Level 3']:
            if level_col in df.columns:
                cats = df[level_col].dropna().unique()
                categories.update(cats)

        return sorted(list(categories))
