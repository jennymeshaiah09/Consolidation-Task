"""
Normalization Module
Handles product key normalization and category classification.
"""

import re
import pandas as pd
from typing import Optional

# Import auto-generated keywords from Excel taxonomy
from .generated_keywords import CATEGORY_KEYWORDS

# Backward compatibility mapping: old product type names to Excel sheet names
PRODUCT_TYPE_MAPPING = {
    "BWS": "Alcoholic Beverages",
    "Pets": "Pets",
    "Electronics": "Electronics",
}


def create_product_key(product_title: str) -> str:
    """
    Create a normalized product key from a product title.
    Used for matching products across different monthly files.

    Args:
        product_title: The original product title

    Returns:
        Normalized product key (lowercase, alphanumeric only, spaces collapsed)
    """
    if pd.isna(product_title) or not isinstance(product_title, str):
        return ""

    # Convert to lowercase
    key = product_title.lower()

    # Remove special characters, keep only alphanumeric and spaces
    key = re.sub(r'[^a-z0-9\s]', '', key)

    # Collapse multiple spaces into single space
    key = re.sub(r'\s+', ' ', key)

    # Strip leading/trailing whitespace
    key = key.strip()

    return key


def extract_leaf_category(category_full: str) -> str:
    """
    Extract the most specific category (leaf node) from full category path.

    Args:
        category_full: Full category path (e.g., "Wine > Sparkling Wine")

    Returns:
        Leaf category (e.g., "Sparkling Wine")
    """
    if " > " in category_full:
        return category_full.split(" > ")[-1].strip()
    return category_full


def classify_category(product_title: str, product_type: str) -> str:
    """
    Classify a product into a category based on keywords in the title.
    Uses cascading matching: tries Level 3, then Level 2, then Level 1.
    Returns only the most specific category (leaf node).

    Args:
        product_title: The product title to classify
        product_type: The product type (BWS, Pets, Electronics, or any Excel sheet name)

    Returns:
        Leaf category name or "Other" if no match found
    """
    if pd.isna(product_title) or not isinstance(product_title, str):
        return "Other"

    title_lower = product_title.lower()

    # Handle common spelling variants for better matching
    title_lower = title_lower.replace('whiskey', 'whisky')  # Normalize to British spelling

    # ===================================================================
    # ACCESSORY DETECTION - Prevent main products matching accessory categories
    # ===================================================================

    # Electronics accessories
    electronics_accessory_keywords = ['case', 'cover', 'charger', 'cable', 'screen protector',
                                       'protector', 'adapter', 'holder', 'stand', 'mount', 'bag']
    electronics_controller_keywords = ['controller', 'gamepad', 'joystick']
    phone_brands = ['iphone', 'galaxy', 'pixel', 'oneplus', 'xiaomi', 'oppo', 'vivo', 'nokia']

    is_phone_accessory = (any(kw in title_lower for kw in electronics_accessory_keywords) and
                          any(brand in title_lower for brand in phone_brands))
    is_controller = any(kw in title_lower for kw in electronics_controller_keywords)

    # Camera accessories (prevent "Canon Camera Bag" from matching "Cameras")
    # IMPORTANT: Check for FULL phrases like "camera bag", not just "camera"
    camera_accessory_keywords = ['camera bag', 'camera case', 'tripod', 'filter',
                                  'strap', 'lens cap', 'memory card']
    is_camera_accessory = any(kw in title_lower for kw in camera_accessory_keywords)

    # If title contains brand + "camera" but NOT accessory keywords, prioritize main camera
    camera_brands = ['canon', 'nikon', 'sony', 'fujifilm', 'panasonic', 'olympus']
    is_main_camera = (any(brand in title_lower for brand in camera_brands) and
                      'camera' in title_lower and
                      not is_camera_accessory)

    # Pet accessories (prevent "Dog Collar" from matching "Dog Food")
    pet_food_keywords = ['food', 'treats', 'kibble', 'wet food', 'dry food']
    pet_accessory_keywords = ['collar', 'leash', 'lead', 'harness', 'bed', 'bowl', 'toy']
    is_pet_food = any(kw in title_lower for kw in pet_food_keywords)
    is_pet_accessory = (any(kw in title_lower for kw in pet_accessory_keywords) and
                        not is_pet_food)

    # Map old product type names to Excel sheet names
    mapped_type = PRODUCT_TYPE_MAPPING.get(product_type, product_type)

    # Get category keywords for this product type
    categories = CATEGORY_KEYWORDS.get(mapped_type, {})

    if not categories:
        # Try with original product_type if mapping didn't work
        categories = CATEGORY_KEYWORDS.get(product_type, {})

    # Sort categories by specificity (most specific first)
    # Count " > " separators: Level 3 has 2, Level 2 has 1, Level 1 has 0
    sorted_categories = sorted(
        categories.items(),
        key=lambda x: x[0].count(" > "),
        reverse=True  # Most specific first
    )

    # Try matching from most specific to least specific
    # Keep track of best match (longest keyword)
    best_match = None
    best_keyword_length = 0

    for category_name, keywords in sorted_categories:
        # ===================================================================
        # CATEGORY FILTERING - Skip incompatible categories based on product type
        # ===================================================================

        # Electronics: Phone accessories
        if is_phone_accessory:
            if "Phone Accessories" not in category_name and "Phone Cases" not in category_name:
                continue

        # Electronics: Gaming controllers
        if is_controller:
            if "Controller" not in category_name and "Gamepad" not in category_name:
                continue

        # Cameras & Optics: Camera accessories vs main cameras
        if is_camera_accessory:
            # Only match accessory categories
            if "Accessories" not in category_name and "Bags" not in category_name and "Tripod" not in category_name:
                continue
        elif is_main_camera:
            # Skip accessory categories for main cameras
            if "Accessories" in category_name or "Bags" in category_name or "Tripod" in category_name:
                continue

        # Pets: Food vs Accessories/Toys
        if is_pet_food:
            # Only match food categories
            if "Food" not in category_name and "Treats" not in category_name:
                continue
        elif is_pet_accessory:
            # Skip food categories for accessories
            if "Food" in category_name:
                continue

        # Sort keywords by length (longest first) for more specific matching
        sorted_keywords = sorted(keywords, key=len, reverse=True)

        for keyword in sorted_keywords:
            # Check if keyword exists in title using word boundaries
            # This prevents "phone" from matching "iPhone"
            # Use regex word boundary \b for exact word matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, title_lower):
                # Keep track of the longest keyword match
                if len(keyword) > best_keyword_length:
                    best_match = category_name
                    best_keyword_length = len(keyword)
                elif len(keyword) == best_keyword_length:
                    # Tie: prefer less specific category (fewer " > " separators)
                    current_specificity = category_name.count(" > ")
                    best_specificity = best_match.count(" > ") if best_match else 999
                    if current_specificity < best_specificity:
                        best_match = category_name
                break  # Found a match in this category, move to next category

    if best_match:
        # Return only the leaf category (most specific)
        return extract_leaf_category(best_match)

    return "Other"


def add_product_key_column(df: pd.DataFrame, title_column: str = "Product Title") -> pd.DataFrame:
    """
    Add a normalized product_key column to a DataFrame.

    Args:
        df: pandas DataFrame
        title_column: Name of the column containing product titles

    Returns:
        DataFrame with added 'product_key' column
    """
    df = df.copy()
    df['product_key'] = df[title_column].apply(create_product_key)
    return df


def classify_category_levels(product_title: str, product_type: str) -> tuple:
    """
    Classify a product into L1, L2, and L3 categories.

    Rules:
    - L1 (Level 1) MUST always have a value, never "Other"
    - L2 and L3 can be "Other" if no specific match found
    - Uses cascading matching: tries Level 3, then Level 2, then Level 1

    Args:
        product_title: The product title to classify
        product_type: The product type (BWS, Pets, Electronics, or any Excel sheet name)

    Returns:
        Tuple of (level1, level2, level3) category names
    """
    if pd.isna(product_title) or not isinstance(product_title, str):
        # Default L1 based on product type
        default_l1 = get_default_l1_for_product_type(product_type)
        return (default_l1, "Other", "Other")

    title_lower = product_title.lower()

    # Handle common spelling variants
    title_lower = title_lower.replace('whiskey', 'whisky')

    # ===================================================================
    # ACCESSORY DETECTION - Same as classify_category
    # ===================================================================
    electronics_accessory_keywords = ['case', 'cover', 'charger', 'cable', 'screen protector',
                                       'protector', 'adapter', 'holder', 'stand', 'mount', 'bag']
    electronics_controller_keywords = ['controller', 'gamepad', 'joystick']
    phone_brands = ['iphone', 'galaxy', 'pixel', 'oneplus', 'xiaomi', 'oppo', 'vivo', 'nokia']

    is_phone_accessory = (any(kw in title_lower for kw in electronics_accessory_keywords) and
                          any(brand in title_lower for brand in phone_brands))
    is_controller = any(kw in title_lower for kw in electronics_controller_keywords)

    camera_accessory_keywords = ['camera bag', 'camera case', 'tripod', 'filter',
                                  'strap', 'lens cap', 'memory card']
    is_camera_accessory = any(kw in title_lower for kw in camera_accessory_keywords)

    camera_brands = ['canon', 'nikon', 'sony', 'fujifilm', 'panasonic', 'olympus']
    is_main_camera = (any(brand in title_lower for brand in camera_brands) and
                      'camera' in title_lower and
                      not is_camera_accessory)

    pet_food_keywords = ['food', 'treats', 'kibble', 'wet food', 'dry food']
    pet_accessory_keywords = ['collar', 'leash', 'lead', 'harness', 'bed', 'bowl', 'toy']
    is_pet_food = any(kw in title_lower for kw in pet_food_keywords)
    is_pet_accessory = (any(kw in title_lower for kw in pet_accessory_keywords) and
                        not is_pet_food)

    # Map old product type names to Excel sheet names
    mapped_type = PRODUCT_TYPE_MAPPING.get(product_type, product_type)

    # Get category keywords for this product type
    categories = CATEGORY_KEYWORDS.get(mapped_type, {})

    if not categories:
        categories = CATEGORY_KEYWORDS.get(product_type, {})

    # Sort categories by specificity (most specific first)
    sorted_categories = sorted(
        categories.items(),
        key=lambda x: x[0].count(" > "),
        reverse=True
    )

    # Try matching from most specific to least specific
    best_match = None
    best_keyword_length = 0

    for category_name, keywords in sorted_categories:
        # Apply same filtering logic as classify_category
        if is_phone_accessory:
            if "Phone Accessories" not in category_name and "Phone Cases" not in category_name:
                continue

        if is_controller:
            if "Controller" not in category_name and "Gamepad" not in category_name:
                continue

        if is_camera_accessory:
            if "Accessories" not in category_name and "Bags" not in category_name and "Tripod" not in category_name:
                continue
        elif is_main_camera:
            if "Accessories" in category_name or "Bags" in category_name or "Tripod" in category_name:
                continue

        if is_pet_food:
            if "Food" not in category_name and "Treats" not in category_name:
                continue
        elif is_pet_accessory:
            if "Food" in category_name:
                continue

        sorted_keywords = sorted(keywords, key=len, reverse=True)

        for keyword in sorted_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, title_lower):
                if len(keyword) > best_keyword_length:
                    best_match = category_name
                    best_keyword_length = len(keyword)
                elif len(keyword) == best_keyword_length:
                    current_specificity = category_name.count(" > ")
                    best_specificity = best_match.count(" > ") if best_match else 999
                    if current_specificity < best_specificity:
                        best_match = category_name
                break

    # Extract L1, L2, L3 from best match
    if best_match:
        parts = best_match.split(" > ")
        level1 = parts[0].strip() if len(parts) >= 1 else get_default_l1_for_product_type(product_type)
        level2 = parts[1].strip() if len(parts) >= 2 else "Other"
        level3 = parts[2].strip() if len(parts) >= 3 else "Other"
        return (level1, level2, level3)

    # No match found - return default L1 and "Other" for L2/L3
    default_l1 = get_default_l1_for_product_type(product_type)
    return (default_l1, "Other", "Other")


def get_default_l1_for_product_type(product_type: str) -> str:
    """
    Get the default Level 1 category for a product type.
    L1 should never be "Other" - always provide a base category.

    Args:
        product_type: The product type

    Returns:
        Default Level 1 category name
    """
    # Map product types to their most common/generic Level 1
    mapped_type = PRODUCT_TYPE_MAPPING.get(product_type, product_type)

    defaults = {
        "Alcoholic Beverages": "Alcoholic Beverages",
        "BWS": "Alcoholic Beverages",
        "Pets": "Pet Supplies",
        "Electronics": "Electronics",
        "F&F (Later)": "Food & Beverages",
        "Party & Celebration": "Party Supplies",
        "Toys": "Toys & Games",
        "Baby & Toddler": "Baby Products",
        "Health & Beauty": "Health & Beauty",
        "Sporting Goods": "Sports & Fitness",
        "Home & Garden": "Home & Living",
        "Luggage & Bags": "Luggage & Bags",
        "Furniture": "Furniture",
        "Cameras & Optics": "Cameras & Photography",
        "Hardware": "Hardware & Tools",
    }

    return defaults.get(mapped_type, defaults.get(product_type, "Uncategorized"))


def add_category_column(df: pd.DataFrame, product_type: str,
                        title_column: str = "Product Title") -> pd.DataFrame:
    """
    Add a category column to a DataFrame based on product titles.
    DEPRECATED: Use add_category_level_columns() for new 3-level system.

    Args:
        df: pandas DataFrame
        product_type: The product type (BWS, Pets, Electronics)
        title_column: Name of the column containing product titles

    Returns:
        DataFrame with added 'Product Category' column
    """
    df = df.copy()
    df['Product Category'] = df[title_column].apply(
        lambda x: classify_category(x, product_type)
    )
    return df


def add_category_level_columns(df: pd.DataFrame, product_type: str,
                                title_column: str = "Product Title") -> pd.DataFrame:
    """
    Add L1, L2, and L3 category columns to a DataFrame.

    Args:
        df: pandas DataFrame
        product_type: The product type (BWS, Pets, Electronics)
        title_column: Name of the column containing product titles

    Returns:
        DataFrame with added 'Product Category L1', 'Product Category L2', 'Product Category L3' columns
    """
    df = df.copy()

    # Apply classification and split into 3 columns
    category_levels = df[title_column].apply(
        lambda x: classify_category_levels(x, product_type)
    )

    # Create 3 separate columns
    df['Product Category L1'] = category_levels.apply(lambda x: x[0])
    df['Product Category L2'] = category_levels.apply(lambda x: x[1])
    df['Product Category L3'] = category_levels.apply(lambda x: x[2])

    return df
