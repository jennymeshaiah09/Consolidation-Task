"""
RAKE Keyword Extraction Module - COMPREHENSIVE MSV OPTIMIZATION
Fast, local keyword extraction without API calls.
Optimized to produce keywords that match Google search patterns.
"""

import re
from typing import List, Optional, Set
import pandas as pd

from .keyword_preprocessor import normalize_accents_safe

# Stop words for RAKE - common words to ignore
STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
    'this', 'that', 'these', 'those', 'it', 'its', 'up', 'out', 'if',
    'about', 'into', 'through', 'during', 'before', 'after', 'above',
    'below', 'between', 'under', 'again', 'further', 'then', 'once',
    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
    # Product-specific stop words
    'pack', 'packs', 'bottle', 'bottles', 'can', 'cans', 'box', 'boxes',
    'unit', 'units', 'piece', 'pieces',
    'ml', 'cl', 'l', 'ltr', 'litre', 'litres', 'liter', 'liters',
    'g', 'kg', 'gram', 'grams', 'kilogram', 'oz', 'lb', 'lbs',
    'x', 'vol', 'proof',
    's',  # Possessive ending (Daniel's -> Daniel + s)
}

# ISSUE 9: Promotional/commercial language to REMOVE
PROMOTIONAL_WORDS = {
    'offer', 'deal', 'discount', 'save', 'buy', 'shop', 'bestseller',
    'welcome', 'sale', 'special', 'exclusive', 'black', 'friday',
    'cyber', 'monday', 'free', 'delivery', 'shipping', 'stock',
}

# ISSUE 4: Gift/personalization language to REMOVE
GIFT_WORDS = {
    'gift', 'gifts', 'hamper', 'hampers', 'present', 'presents',
    'personalised', 'personalized', 'customised', 'customized',
    'engraved', 'engraving', 'custom', 'bespoke',
}

# ISSUE 6: Case/multipack descriptors to REMOVE
MULTIPACK_WORDS = {
    'case', 'cases', 'set', 'sets', 'mixed', 'selection', 'variety',
    'multipack', 'multi', 'tasting', 'assortment', 'pack', 'packs',
    'bundle', 'combo', 'collection',
}

# ISSUE 11: Retailer/merchant names to REMOVE
RETAILER_WORDS = {
    'laithwaites', 'waitrose', 'tesco', 'sainsburys', 'asda', 'morrisons',
    'aldi', 'lidl', 'ocado', 'amazon', 'majestic', 'virgin', 'wines',
    'threshers', 'nicolas', 'oddbins', 'berry', 'bros', 'rudd',
    'cellar', 'direct', 'online',
    # Remove duplicates and move these to appropriate categories
}

# Words to REMOVE from keywords - these don't add search value
DESCRIPTOR_WORDS = {
    # Locations (don't add search value)
    'tennessee', 'kentucky', 'scottish', 'scotch', 'irish', 'japanese',
    'french', 'italian', 'spanish', 'german', 'australian', 'american',
    'english', 'british', 'canadian', 'mexican', 'russian', 'polish',
    'dutch', 'belgian', 'swiss', 'new', 'zealand', 'south', 'african',
    'bordeaux', 'burgundy', 'champagne', 'provence', 'napa', 'sonoma',
    'highland', 'lowland', 'speyside', 'islay', 'cornish', 'welsh',
    # Generic descriptors
    'premium', 'classic', 'original', 'special', 'reserve', 'select',
    'finest', 'superior', 'deluxe', 'exclusive', 'limited', 'edition',
    'old', 'aged', 'vintage', 'rare', 'extra', 'ultra', 'super',
    'blend', 'blended', 'pure', 'natural', 'organic', 'craft',
    'small', 'batch', 'handcrafted', 'artisan', 'traditional',
    # Quality terms that people rarely search
    'cuvee', 'cuvée', 'brut', 'imperial', 'royal', 'grand', 'cru',
    'single', 'malt', 'grain', 'pot', 'still',
}

# Combine all removal words
ALL_REMOVAL_WORDS = (
    PROMOTIONAL_WORDS | GIFT_WORDS | MULTIPACK_WORDS |
    RETAILER_WORDS | DESCRIPTOR_WORDS
)

# ISSUE 2, 5, 10: Patterns to remove from product titles
REMOVE_PATTERNS = [
    # ISSUE 2: Size and volume units
    r'\d+\s*ml\b',           # 700ml, 750 ml
    r'\d+\s*cl\b',           # 50cl
    r'\d+\s*l\b',            # 1l, 2l
    r'\d+\s*ltr?\b',         # 1ltr, 2lt
    r'\d+\s*g\b',            # 500g
    r'\d+\s*kg\b',           # 1kg
    r'\d+\s*oz\b',           # 12oz
    r'\d+\s*litre?s?\b',     # 1 litre, 2 litres
    r'\d+\s*miniature',      # 4cl miniature
    # ISSUE 2: Quantity formats
    r'\d+\s*pack',           # 6 pack, 24pack
    r'\d+\s*x\s*\d+\s*\w+',  # 24x330ml, 6 x 500ml
    r'x\s*\d+',              # x6, x12
    r'\d+\s*bottles?',       # 6 bottles
    r'\d+\s*cans?',          # 12 cans
    # ISSUE 10: ABV/proof information
    r'\d+\s*%\s*abv',        # 40% abv
    r'\d+\s*%\s*vol',        # 13% vol
    r'\d+\s*%',              # 40%
    r'\d+\s*proof',          # 100 proof
    r'\d+\.\d+\s*%',         # 13.5%
    # ISSUE 5: Vintage years (4-digit years)
    r'\b(19|20)\d{2}\b',     # 2024, 2023, 1999, etc.
    # Misc cleanup
    r'\|\s*.*$',             # | anything after pipe
    r'\(\d+.*?\)',           # (6 pack), (700ml)
    r'\[.*?\]',              # [gift set]
    r'\d{5,}',               # Long numbers (barcodes, model numbers 5+ digits)
]

# ISSUE 3: Age statement patterns to simplify
AGE_PATTERNS = [
    (r'(\d+)\s*[-]?\s*years?\s*[-]?\s*old', r'\1yr'),  # "12 Year Old" -> "12yr"
    (r'(\d+)\s*yo\b', r'\1yr'),                         # "12yo" -> "12yr"
]


def simplify_age_statements(text: str) -> str:
    """
    ISSUE 3: Convert "12 Year Old" -> "12yr" to reduce keyword length.
    """
    result = text
    for pattern, replacement in AGE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def clean_title(title: str) -> str:
    """
    Comprehensive title cleaning addressing Issues 2, 3, 5, 8, 10.

    Returns:
        Cleaned title string
    """
    result = title

    # ISSUE 8: Normalize accents (rosé -> rose)
    result = normalize_accents_safe(result)

    # ISSUE 3: Simplify age statements BEFORE removing patterns
    result = simplify_age_statements(result)

    # ISSUE 2, 5, 10: Apply removal patterns
    for pattern in REMOVE_PATTERNS:
        result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)

    # Remove apostrophes to handle possessives (Daniel's -> Daniels)
    result = result.replace("'", "").replace("'", "").replace("`", "")

    # Clean up extra whitespace
    result = re.sub(r'\s+', ' ', result).strip()

    return result.lower()


def deduplicate_words(text: str) -> str:
    """
    ISSUE 7: Remove repeated words.
    "vodka strawberry burst vodka" -> "vodka strawberry burst"
    """
    words = text.split()
    seen = set()
    result = []

    for word in words:
        word_lower = word.lower()
        if word_lower not in seen:
            seen.add(word_lower)
            result.append(word)

    return ' '.join(result)


def extract_candidate_phrases(text: str) -> List[str]:
    """Split text into candidate phrases using stop words as delimiters."""
    # Tokenize - include alphanumeric characters
    words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())

    phrases = []
    current_phrase = []

    for word in words:
        if word in STOP_WORDS:
            if current_phrase:
                phrases.append(' '.join(current_phrase))
                current_phrase = []
        else:
            current_phrase.append(word)

    if current_phrase:
        phrases.append(' '.join(current_phrase))

    return [p for p in phrases if p]


def calculate_word_scores(phrases: List[str]) -> dict:
    """Calculate RAKE scores for each word."""
    word_freq = {}
    word_degree = {}

    for phrase in phrases:
        words = phrase.split()
        degree = len(words) - 1

        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
            word_degree[word] = word_degree.get(word, 0) + degree

    # Score = degree / frequency
    word_scores = {}
    for word in word_freq:
        word_scores[word] = (word_degree[word] + word_freq[word]) / word_freq[word]

    return word_scores


def score_phrases(phrases: List[str], word_scores: dict) -> List[tuple]:
    """Score each phrase by summing word scores."""
    phrase_scores = []

    for phrase in phrases:
        words = phrase.split()
        score = sum(word_scores.get(word, 0) for word in words)
        phrase_scores.append((phrase, score))

    # Sort by score descending
    phrase_scores.sort(key=lambda x: x[1], reverse=True)

    return phrase_scores


def filter_removal_words(words: List[str]) -> List[str]:
    """
    ISSUE 4, 6, 9, 11: Filter out gift/multipack/promotional/retailer words.
    """
    return [w for w in words if w.lower() not in ALL_REMOVAL_WORDS]


def brand_in_text(brand: str, text: str) -> bool:
    """
    Check if brand is already present in text.
    Handles special characters like apostrophes, accents, ampersands.
    """
    if not brand:
        return True  # No brand to add

    # Normalize both for comparison
    brand_normalized = normalize_accents_safe(brand.lower())
    text_normalized = normalize_accents_safe(text.lower())

    # Remove special characters for comparison
    brand_clean = re.sub(r"[^a-z0-9\s]", "", brand_normalized)
    text_clean = re.sub(r"[^a-z0-9\s]", "", text_normalized)

    # Check if any significant word from brand is in text
    brand_words = brand_clean.split()
    text_words = text_clean.split()

    # If brand is single word, check direct inclusion
    if len(brand_words) == 1:
        return brand_words[0] in text_words

    # For multi-word brands, check if first significant word (3+ chars) is present
    for word in brand_words:
        if len(word) >= 3 and word in text_words:
            return True

    return False


def extract_keyword_rake(title: str, brand: str = "", max_words: int = 4) -> str:
    """
    Extract SEARCH-FRIENDLY keyword from product title.
    ISSUE 1: Cap at 4 words max for optimal MSV.

    Args:
        title: Product title
        brand: Product brand
        max_words: Maximum words in keyword (default 4 per analysis)

    Returns:
        Search-friendly keyword string (2-4 words ideal)
    """
    if not title or not title.strip():
        return ""

    # Clean the title (handles issues 2, 3, 5, 8, 10)
    cleaned = clean_title(title)

    # ISSUE 7: Deduplicate repeated words
    cleaned = deduplicate_words(cleaned)

    # Extract candidate phrases
    phrases = extract_candidate_phrases(cleaned)

    if not phrases:
        # Fallback: just use the first few words
        words = cleaned.split()[:max_words]
        keyword = ' '.join(words)
    else:
        # Calculate word scores
        word_scores = calculate_word_scores(phrases)

        # Score phrases
        scored_phrases = score_phrases(phrases, word_scores)

        if not scored_phrases:
            return ""

        # Get top phrase
        top_phrase = scored_phrases[0][0]
        words = top_phrase.split()

        # ISSUE 4, 6, 9, 11: Filter out removal words
        filtered_words = filter_removal_words(words)

        # If we filtered everything, use original (but limited)
        if not filtered_words:
            filtered_words = words[:max_words]
        else:
            # ISSUE 1: Cap at max_words (4 for best MSV)
            filtered_words = filtered_words[:max_words]

        keyword = ' '.join(filtered_words)

    # Add brand ONLY if not already present
    if brand and not brand_in_text(brand, keyword):
        # Use simplified brand (first 2 words max to keep under 4 total)
        brand_words = brand.split()[:2]
        brand_simple = ' '.join(brand_words)

        # ISSUE 1: Ensure we don't exceed 4 words total
        keyword_words = keyword.split()
        remaining_slots = max_words - len(brand_words)
        if len(keyword_words) > remaining_slots:
            keyword_words = keyword_words[:remaining_slots]

        keyword = f"{brand_simple} {' '.join(keyword_words)}"

    # ISSUE 7: Final deduplication check
    keyword = deduplicate_words(keyword)

    # Title case the result
    result = keyword.title()

    # Strip special characters — replace & with And, then remove everything
    # that isn't a letter, digit, or space
    result = result.replace('&', 'And')
    result = re.sub(r'[^A-Za-z0-9 ]', '', result)
    result = re.sub(r'\s+', ' ', result).strip()

    # Cap at max_words
    result_words = result.split()
    if len(result_words) > max_words:
        result = ' '.join(result_words[:max_words])

    return result


def generate_keywords_rake(
    df: pd.DataFrame,
    progress_callback=None
) -> pd.DataFrame:
    """
    Generate keywords for all products using RAKE (instant, no API).
    Optimized for MSV with 2-4 word keywords.

    Args:
        df: DataFrame with 'Product Title' and 'Product Brand' columns
        progress_callback: Optional callback for progress updates

    Returns:
        DataFrame with 'Product Keyword' column populated
    """
    df = df.copy()

    if 'Product Keyword' not in df.columns:
        df['Product Keyword'] = ""

    total = len(df)
    print(f"Generating MSV-optimized keywords with RAKE for {total} products...")

    for idx, row in df.iterrows():
        _title = row.get('Product Title', '')
        title = str(_title) if pd.notna(_title) else ''
        _brand = row.get('Product Brand', '')
        brand = str(_brand) if pd.notna(_brand) else ''

        keyword = extract_keyword_rake(title, brand, max_words=4)
        df.at[idx, 'Product Keyword'] = keyword

        # Progress callback
        if progress_callback and idx % 100 == 0:
            progress = (idx + 1) / total
            progress_callback(progress, idx + 1, total)

    if progress_callback:
        progress_callback(1.0, total, total)

    print(f"✓ Generated {total} keywords with RAKE (instant, MSV-optimized)")

    return df


# Quick test
if __name__ == "__main__":
    test_cases = [
        # Test ISSUE 1: Over-length keywords
        ("Balvenie 12 Year Old The Sweet Toast of American Oak Single Malt Whisky", "Balvenie"),
        # Test ISSUE 2: Size/volume units
        ("Blantons Single Barrel Bourbon 750ml", "Blantons"),
        ("Vault City Sour Mixed Case 24x330ml", "Vault City"),
        # Test ISSUE 3: Age statements
        ("Lagavulin 16 Year Old Single Malt Whisky", "Lagavulin"),
        ("Glenallachie 12 Year Old", "Glenallachie"),
        # Test ISSUE 4: Gift/personalization
        ("Personalised Luxury Grey Goose Vodka Hamper Gift", "Grey Goose"),
        ("Personalised Glass Whisky Set", ""),
        # Test ISSUE 5: Vintage years
        ("Chin Chin Vinho Verde 2024", "Chin Chin"),
        ("Whispering Angel Rose 2022", "Whispering Angel"),
        # Test ISSUE 6: Case/multipack
        ("Vault City Sour Mixed Case", "Vault City"),
        ("Whisky Tasting Set Selection", ""),
        # Test ISSUE 7: Word repetition
        ("Edmunds Cocktails 1L Edmunds Strawberry Daiquiri Cocktail", "Edmunds"),
        ("Vodka USA Christmas Edition Strawberry Burst Vodka", ""),
        # Test ISSUE 8: Broken accents
        ("Tread Softly Rosé Wine", "Tread Softly"),
        ("Moët & Chandon Brut Imperial", "Moët & Chandon"),
        ("Château Margaux", "Château Margaux"),
        # Test ISSUE 9: Promotional language
        ("Black Friday Giordanos Bestsellers", "Giordanos"),
        ("Limited Edition Special Offer Whisky", ""),
        # Test ISSUE 10: ABV/proof
        ("Urban Rhino Dragon Lime Liqueur 50cl 20% ABV", "Urban Rhino"),
        ("Jack Daniels Tennessee Whiskey 40%", "Jack Daniels"),
        # Test ISSUE 11: Retailer contamination
        ("Buy Bonkers Conkers Ale Greene King Shop", "Bonkers Conkers"),
        ("Laithwaites Premium Red Wine Selection", "Laithwaites"),
        # General tests
        ("Jack Daniel's Tennessee Whiskey", "Jack Daniel's"),
        ("Budweiser Lager Beer", "Budweiser"),
        ("Bollinger Special Cuvee Champagne", "Bollinger"),
    ]

    print("MSV-OPTIMIZED RAKE Keyword Extraction Test:")
    print("=" * 80)

    for title, brand in test_cases:
        keyword = extract_keyword_rake(title, brand)
        word_count = len(keyword.split())
        print(f"Title:   {title}")
        print(f"Brand:   {brand}")
        print(f"Keyword: {keyword} ({word_count} words)")
        print("-" * 80)
