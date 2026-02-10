"""
Enhanced Keyword Preprocessor Module
Handles all 11 MSV issues BEFORE keyword extraction.

This module provides deterministic, rule-based preprocessing that:
1. Strips noise (sizes, ABV, years, retailers, promos)
2. Normalizes accents safely
3. Deduplicates words
4. Prepares clean text for keyword extraction
"""

import re
import unicodedata
from typing import Optional, Set, Tuple

# ============================================================================
# ISSUE 2: Size and volume units to STRIP
# ============================================================================
SIZE_PATTERNS = [
    r'\d+\s*ml\b',              # 700ml, 750 ml
    r'\d+\s*cl\b',              # 50cl, 70cl
    r'\d+\s*l\b',               # 1l, 2l
    r'\d+\s*ltr?\b',            # 1ltr, 2lt
    r'\d+\s*litre?s?\b',        # 1 litre, 2 litres
    r'\d+\s*g\b',               # 500g
    r'\d+\s*kg\b',              # 1kg
    r'\d+\s*oz\b',              # 12oz
    r'\d+\s*lb\b',              # 1lb
    r'\d+\s*miniature\b',       # 4cl miniature
    r'\d+\s*pack\b',            # 6 pack, 24pack
    r'\d+\s*x\s*\d+\s*\w*',     # 24x330ml, 6 x 500ml, 24x
    r'\d+x\b',                  # 24x, 6x (no space)
    r'x\s*\d+',                 # x6, x12
    r'\d+\s*bottles?\b',        # 6 bottles
    r'\d+\s*cans?\b',           # 12 cans
    r'case\s*of\s*\d+',         # case of 6
]

# ============================================================================
# ISSUE 10: ABV/proof patterns to STRIP
# ============================================================================
ABV_PATTERNS = [
    r'\d+\.?\d*\s*%\s*abv',     # 40% abv, 13.5% ABV
    r'\d+\.?\d*\s*%\s*vol',     # 13% vol
    r'\d+\.?\d*\s*%',           # 40%, 13.5%
    r'\d+\s*proof',             # 100 proof
]

# ============================================================================
# ISSUE 5: Vintage years to STRIP (4-digit years 1900-2099)
# ============================================================================
YEAR_PATTERN = r'\b(19|20)\d{2}\b'

# ============================================================================
# ISSUE 3: Age statements to SIMPLIFY
# ============================================================================
AGE_PATTERNS = [
    (r'(\d+)\s*[-]?\s*years?\s*[-]?\s*old', r'\1yr'),  # "12 Year Old" -> "12yr"
    (r'(\d+)\s*yo\b', r'\1yr'),                        # "12yo" -> "12yr"
]

# ============================================================================
# ISSUE 4: Gift/personalization language to STRIP
# ============================================================================
GIFT_WORDS = {
    'gift', 'gifts', 'hamper', 'hampers', 'present', 'presents',
    'personalised', 'personalized', 'customised', 'customized',
    'engraved', 'engraving', 'custom', 'bespoke', 'giftset',
    'gift set', 'gift box', 'gift pack', 'giftbox', 'giftpack',
}

# ============================================================================
# ISSUE 6: Case/multipack descriptors to STRIP
# ============================================================================
MULTIPACK_WORDS = {
    'case', 'cases', 'mixed', 'selection', 'variety', 'assortment',
    'multipack', 'multi', 'tasting', 'sampler', 'bundle', 'combo',
    'collection', 'set', 'sets', 'duo', 'trio', 'pack', 'packs',
}

# ============================================================================
# ISSUE 9: Promotional/commercial language to STRIP
# ============================================================================
PROMO_WORDS = {
    'offer', 'deal', 'discount', 'save', 'buy', 'shop', 'bestseller',
    'welcome', 'sale', 'special', 'exclusive', 'limited', 'edition',
    'black friday', 'cyber monday', 'free', 'delivery', 'shipping',
    'stock', 'clearance', 'reduced', 'promo', 'promotion', 'new',
}

# ============================================================================
# ISSUE 11: Retailer/merchant names to STRIP
# ============================================================================
RETAILER_NAMES = {
    'laithwaites', 'waitrose', 'tesco', 'sainsburys', 'asda', 'morrisons',
    'aldi', 'lidl', 'ocado', 'amazon', 'majestic', 'virgin', 'wines',
    'threshers', 'nicolas', 'oddbins', 'berry bros', 'rudd', 'cellar',
    'direct', 'online', 'greene king', 'shop', 'store', 'buy',
    'whisky exchange', 'master of malt', 'thewhiskyexchange', 'masterofmalt',
    'wine society', 'winesociety', 'personalised gifts shop',
}

# Words that MUST be preserved as they indicate product type
PRODUCT_TYPE_WORDS = {
    # Spirits
    'whisky', 'whiskey', 'vodka', 'gin', 'rum', 'brandy', 'cognac',
    'tequila', 'mezcal', 'bourbon', 'scotch', 'liqueur', 'liquor',
    # Wine
    'wine', 'champagne', 'prosecco', 'cava', 'rose', 'rosé', 'red',
    'white', 'sparkling', 'port', 'sherry', 'vermouth',
    # Beer
    'beer', 'lager', 'ale', 'stout', 'ipa', 'porter', 'pilsner',
    'cider', 'sour',
    # Others
    'cocktail', 'mixer', 'tonic', 'bitters',
}

# Generic descriptors to strip (they don't help search)
DESCRIPTOR_WORDS = {
    'premium', 'classic', 'original', 'reserve', 'select', 'finest',
    'superior', 'deluxe', 'ultra', 'super', 'blend', 'blended',
    'pure', 'natural', 'organic', 'craft', 'artisan', 'traditional',
    'handcrafted', 'small batch', 'smallbatch', 'single', 'malt',
    'grain', 'pot still', 'cask', 'strength', 'cuvee', 'cuvée',
    'brut', 'imperial', 'royal', 'grand', 'cru', 'luxury', 'the',
    'barrel', 'sweet', 'toast', 'american', 'oak',  # Common noise
}

# Combine all words to potentially strip
ALL_STRIP_WORDS = GIFT_WORDS | MULTIPACK_WORDS | PROMO_WORDS | DESCRIPTOR_WORDS


def strip_size_units(text: str) -> str:
    """ISSUE 2: Remove all size/volume units and quantity formats."""
    result = text
    for pattern in SIZE_PATTERNS:
        result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
    return result


def strip_abv_proof(text: str) -> str:
    """ISSUE 10: Remove ABV and proof information."""
    result = text
    for pattern in ABV_PATTERNS:
        result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
    return result


def strip_vintage_years(text: str) -> str:
    """ISSUE 5: Remove 4-digit vintage years."""
    return re.sub(YEAR_PATTERN, ' ', text)


def simplify_age_statements(text: str) -> str:
    """ISSUE 3: Convert '12 Year Old' -> '12yr' to save words."""
    result = text
    for pattern, replacement in AGE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def normalize_accents_safe(text: str) -> str:
    """
    ISSUE 8: Properly normalize accents to ASCII equivalents.
    rosé -> rose, château -> chateau, côtes -> cotes, Glühwein -> Gluhwein
    """
    # Explicit mapping for common wine/spirits accents
    accent_map = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ñ': 'n', 'ç': 'c', 'ß': 'ss',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A',
        'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ñ': 'N', 'Ç': 'C',
    }
    
    result = text
    for accented, plain in accent_map.items():
        result = result.replace(accented, plain)
    
    return result


def strip_retailer_names(text: str, merchant_name: str = "") -> str:
    """ISSUE 11: Remove retailer/merchant names from text."""
    result = text.lower()
    
    # Strip the merchant name if provided
    if merchant_name:
        merchant_lower = merchant_name.lower().strip()
        result = result.replace(merchant_lower, ' ')
    
    # Strip known retailer names
    for retailer in RETAILER_NAMES:
        result = re.sub(r'\b' + re.escape(retailer) + r'\b', ' ', result, flags=re.IGNORECASE)
    
    return result


def strip_noise_words(text: str) -> str:
    """ISSUE 4, 6, 9: Remove gift/multipack/promo words."""
    words = text.lower().split()
    filtered = []
    
    for word in words:
        word_clean = re.sub(r'[^\w]', '', word)
        if word_clean and word_clean not in ALL_STRIP_WORDS:
            filtered.append(word)
    
    return ' '.join(filtered)


def deduplicate_words(text: str) -> str:
    """
    ISSUE 7: Remove repeated words, keeping first occurrence.
    Also handles plurals (cocktail/cocktails) and accent variants (rose/rosé).
    """
    words = text.split()
    seen_bases = set()
    result = []
    
    def get_base(word: str) -> str:
        """Get base form for comparison (handle plurals)."""
        w = word.lower()
        # Remove common plural endings
        if w.endswith('ies'):
            return w[:-3] + 'y'
        elif w.endswith('es'):
            return w[:-2]
        elif w.endswith('s') and not w.endswith('ss'):
            return w[:-1]
        return w
    
    for word in words:
        word_lower = word.lower()
        word_base = get_base(word_lower)
        
        # Skip if we've already seen this base form
        if word_base in seen_bases or word_lower in seen_bases:
            continue
        
        seen_bases.add(word_lower)
        seen_bases.add(word_base)
        result.append(word)
    
    return ' '.join(result)


def extract_product_type(text: str) -> Optional[str]:
    """Extract the product type keyword (whisky, vodka, wine, etc.)."""
    text_lower = text.lower()
    
    for product_type in PRODUCT_TYPE_WORDS:
        if product_type in text_lower:
            return product_type
    
    return None


def clean_brand(brand: str) -> str:
    """Clean brand name - remove apostrophes, normalize accents, limit to 2 words."""
    if not brand:
        return ""
    
    # Normalize accents
    brand = normalize_accents_safe(brand)
    
    # Remove apostrophes and special chars
    brand = brand.replace("'", "").replace("'", "").replace("`", "")
    brand = re.sub(r'[^\w\s]', ' ', brand)
    
    # Limit to first 2 significant words (skip "the", "of", etc.)
    words = brand.split()
    significant = [w for w in words if len(w) > 2 and w.lower() not in {'the', 'and', 'of'}]
    
    return ' '.join(significant[:2])


def preprocess_title(title: str, brand: str = "", merchant_name: str = "") -> str:
    """
    Master preprocessing function - applies all 11 fixes in order.
    
    Returns clean text ready for keyword extraction.
    """
    if not title:
        return ""
    
    result = title
    
    # 1. Normalize accents FIRST (before any regex matching)
    result = normalize_accents_safe(result)
    
    # 2. Strip retailer/merchant names
    result = strip_retailer_names(result, merchant_name)
    
    # 3. Simplify age statements BEFORE removing patterns
    result = simplify_age_statements(result)
    
    # 4. Strip size/volume units
    result = strip_size_units(result)
    
    # 5. Strip ABV/proof
    result = strip_abv_proof(result)
    
    # 6. Strip vintage years
    result = strip_vintage_years(result)
    
    # 7. Remove apostrophes and normalize
    result = result.replace("'", "").replace("'", "").replace("`", "")
    
    # 8. Remove misc noise (pipes, brackets, long numbers)
    result = re.sub(r'\|.*$', ' ', result)           # | anything after
    result = re.sub(r'\(.*?\)', ' ', result)         # (parentheses)
    result = re.sub(r'\[.*?\]', ' ', result)         # [brackets]
    result = re.sub(r'\d{5,}', ' ', result)          # Long numbers (barcodes)
    
    # 9. Strip gift/multipack/promo words
    result = strip_noise_words(result)
    
    # 10. Deduplicate words
    result = deduplicate_words(result)
    
    # 11. Clean up whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result.lower()


def extract_keyword_hybrid(
    title: str,
    brand: str = "",
    merchant_name: str = "",
    max_words: int = 4
) -> str:
    """
    Hybrid keyword extraction - combines preprocessing with smart selection.
    
    Strategy:
    1. Preprocess to remove noise
    2. Ensure Brand + Product Type are included
    3. Add 1-2 differentiators if space allows
    4. Cap at max_words
    
    This avoids RAKE's issue of stripping product names in favor of brand.
    """
    # Clean brand
    brand_clean = clean_brand(brand)
    brand_words = brand_clean.split() if brand_clean else []
    
    # Preprocess title
    clean_text = preprocess_title(title, brand, merchant_name)
    
    # Extract product type from CLEANED title (after accent normalization)
    product_type = extract_product_type(clean_text)
    
    # Get remaining words from cleaned title
    title_words = clean_text.split()
    
    # Filter out short words and noise
    title_words = [w for w in title_words 
                   if len(w) >= 3 and w.lower() not in {'the', 'and', 'for', 'with'}]
    
    # Remove brand words from title words to avoid duplication
    if brand_words:
        title_words = [w for w in title_words 
                       if w.lower() not in [b.lower() for b in brand_words]]
    
    # Build keyword: Brand + Product Type + Differentiators
    keyword_parts = []
    
    # Add brand (up to 2 words)
    keyword_parts.extend(brand_words[:2])
    
    # Calculate remaining slots
    remaining_slots = max_words - len(keyword_parts)
    
    # Ensure product type is included if found
    if product_type and remaining_slots > 0:
        # Remove product type from title_words if present (will add separately)
        title_words = [w for w in title_words if w.lower() != product_type.lower()]
    
    # Add best differentiators from title (prioritize non-generic words)
    differentiators = []
    for word in title_words:
        if len(word) >= 3 and word.lower() not in ALL_STRIP_WORDS:
            differentiators.append(word)
    
    # Add differentiators up to remaining slots (save 1 for product type)
    slots_for_diff = remaining_slots - 1 if product_type else remaining_slots
    keyword_parts.extend(differentiators[:max(0, slots_for_diff)])
    
    # Add product type last if we have room
    if product_type and len(keyword_parts) < max_words:
        keyword_parts.append(product_type)
    
    # Deduplicate using same logic as deduplicate_words (handles plurals)
    def get_base(word: str) -> str:
        w = word.lower()
        if w.endswith('ies'):
            return w[:-3] + 'y'
        elif w.endswith('es'):
            return w[:-2]
        elif w.endswith('s') and not w.endswith('ss'):
            return w[:-1]
        return w
    
    seen_bases = set()
    final_parts = []
    for part in keyword_parts:
        part_lower = part.lower()
        part_base = get_base(part_lower)
        if part_base not in seen_bases and part_lower not in seen_bases:
            seen_bases.add(part_lower)
            seen_bases.add(part_base)
            final_parts.append(part)
    
    # Cap at max_words
    final_parts = final_parts[:max_words]
    
    # Title case
    result = ' '.join(final_parts).title()
    
    return result


# ============================================================================
# QUICK TEST
# ============================================================================
if __name__ == "__main__":
    test_cases = [
        # (title, brand, expected_result_description)
        ("Balvenie 12 Year Old The Sweet Toast of American Oak Single Malt Whisky 700ml", "Balvenie", "Brand + Age + Whisky"),
        ("Blantons Single Barrel Bourbon 750ml", "Blantons", "Brand + Bourbon"),
        ("Personalised Luxury Grey Goose Vodka Hamper Gift 750ml", "Grey Goose", "Brand + Vodka"),
        ("Vault City Sour Mixed Case 24x330ml", "Vault City", "Brand + Sour"),
        ("Chin Chin Vinho Verde 2024 750ml", "Chin Chin", "Brand + Vinho Verde"),
        ("Tread Softly Rosé Wine", "Tread Softly", "Brand + Rose Wine"),
        ("Moët & Chandon Brut Imperial 750ml", "Moët & Chandon", "Brand + Champagne"),
        ("Buy Bonkers Conkers Ale Greene King Shop", "Bonkers Conkers", "Brand + Ale"),
        ("Urban Rhino Dragon Lime Liqueur 50cl 20% ABV", "Urban Rhino", "Brand + Dragon Lime Liqueur"),
        ("Lagavulin 16 Year Old Single Malt Whisky 700ml", "Lagavulin", "Brand + 16yr + Whisky"),
        ("Johnnie Walker Blue Label Whisky 70cl", "Johnnie Walker", "Brand Blue Label Whisky"),
        ("Jack Daniel's Tennessee Whiskey 40%", "Jack Daniel's", "Brand + Whiskey"),
        ("Whispering Angel Rosé 2022 750ml", "Whispering Angel", "Brand + Rose"),
        ("Edmunds Cocktails 1L Edmunds Strawberry Daiquiri Cocktail", "Edmunds", "Brand + Strawberry Daiquiri"),
    ]
    
    print("=" * 80)
    print("HYBRID KEYWORD EXTRACTION TEST")
    print("=" * 80)
    
    for title, brand, desc in test_cases:
        keyword = extract_keyword_hybrid(title, brand)
        word_count = len(keyword.split())
        print(f"\nTitle:    {title}")
        print(f"Brand:    {brand}")
        print(f"Keyword:  {keyword} ({word_count} words)")
        print(f"Expected: {desc}")
        print("-" * 80)
