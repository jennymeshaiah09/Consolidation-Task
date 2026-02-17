import re
import json
import time
import pandas as pd
import unicodedata
import google.generativeai as genai
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import get_google_api_key

# Configure API
def get_gemini_client(model_name: str = "gemini-2.5-flash-lite"):
    """Initialize Google Gemini client."""
    api_key = get_google_api_key()
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

# ============================================================================
# PRODUCT TYPE WORDS - Must be preserved in keywords
# ============================================================================
PRODUCT_TYPES = {
    # Spirits
    'whisky', 'whiskey', 'vodka', 'gin', 'rum', 'brandy', 'cognac',
    'tequila', 'mezcal', 'bourbon', 'scotch', 'liqueur', 'liquor',
    'absinthe', 'grappa', 'schnapps', 'amaretto', 'sambuca',
    # Wine
    'wine', 'champagne', 'prosecco', 'cava', 'rose', 'port', 'sherry',
    'vermouth', 'madeira', 'marsala', 'cremant',
    # Beer
    'beer', 'lager', 'ale', 'stout', 'ipa', 'porter', 'pilsner',
    'cider', 'sour', 'wheat', 'weissbier',
    # Others
    'cocktail', 'mixer', 'tonic', 'bitters', 'aperitif', 'aperitivo',
}

# Words to STRIP from keywords (noise)
NOISE_WORDS = {
    'premium', 'classic', 'original', 'reserve', 'select', 'finest',
    'superior', 'deluxe', 'ultra', 'super', 'limited',
    'edition', 'exclusive', 'rare', 'vintage', 'nv', 'brut', 'sec',
    'demi-sec', 'extra', 'grand', 'cru', 'single', 'malt', 'blend',
    'blended', 'cask', 'strength', 'barrel', 'aged', 'old', 'year',
    'years', 'yo', 'gift', 'hamper',
    'selection', 'collection', 'bundle', 'miniature', 'mini',
}

# Retailer brands to generally UNLESS they are the only brand
RETAILER_BRANDS = {
    'majestic', 'chosen by majestic', 'waitrose', 'tesco', 'sainsburys', 
    'asda', 'lidl', 'aldi', 'morrisons', 'co-op', 'marks and spencer', 'm&s',
    'laithwaites', 'virgin wines', 'sunday times wine club'
}

# --- Step 1: Normalization ---
def normalize_title(title: str) -> str:
    """
    Deterministically clean the title before extraction.
    Lowercase, remove fluff, keep core product info.
    """
    if not title:
        return ""
    
    # 1. Lowercase
    text = title.lower()
    
    # 2. Strip known marketing fluff segments (after separators)
    # Separators: | - – •
    # We split by the first occurrence of a "fluff separator" if it looks like the start of marketing copy
    
    # Simple split by pipe or dash surrounded by spaces
    separators = [r'\s+\|\s+', r'\s+-\s+', r'\s+–\s+', r'\s+•\s+']
    for sep in separators:
        parts = re.split(sep, text)
        if len(parts) > 1:
            cleaned_parts = []
            for part in parts:
                if any(x in part for x in ['mix any', 'save', 'offer', 'deal', 'delivery']):
                    continue
                cleaned_parts.append(part)
            text = " ".join(cleaned_parts)

    # 2.5 Strip accents (e.g. rosé -> rose, moët -> moet)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")

    # 3. Remove punctuation except hyphens in names
    # Keep alphanumeric, spaces, hyphens inside words, numbers
    # Remove stand-alone punctuation
    text = re.sub(r'[^\w\s-]', '', text) # remove special chars like &, !, etc (except hyphen)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# --- Step 2: Entity Extraction (LLM) ---
def extract_entities(client, product_title: str) -> Dict[str, str]:
    """
    Extract structured entities using LLM.
    Returns a dict with keys: brand, product_name, vintage, region, varietal, pack_format, collection
    Raises exceptions on API errors so caller can handle them.
    """
    prompt = f"""
    Analyze the following alcohol product title and extract entities into a JSON object.

    Product Title: "{product_title}"

    Format: JSON
    Fields to Extract:
    - brand: (The user-facing brand, e.g., "Porta 6", "Chateau Batailley", "Jack Daniel's". NOT the generic parent company if hidden. Keep numbers!)
    - product_name: (The specific product name or sub-brand. e.g. "Blue Label", "Nastro Azzurro", "Cordon Rouge". If none, use generic like "Red Wine" or "Lager")
    - vintage: (Year, e.g., "2016", "NV" if non-vintage but explicitly stated, else null. MUST look like a year.)
    - age_statement: (Numeric age, e.g., "12", "15", "18". Extract ONLY the number. Do NOT include "Year Old" or "Years".)
    - product_type: (The broad category, e.g., "Whisky", "Gin", "Liqueur", "Rum", "Vodka". Extract the simple type, e.g. "Whisky" not "Single Malt Whisky".)
    - region: (e.g., "Pauillac", "Bordeaux", "Lisbon")
    - varietal: (e.g., "Malbec", "Primitivo", "Cabernet Sauvignon")
    - pack_format: (e.g., "Case of 6", "Gift Set", "Magnum". Look for "case", "6x", "12x", "gift". Leave null if single bottle.)
    - collection: (e.g., "Chosen by Majestic", "Definition")

    Rules:
    1. Be precise. Do not hallucinate. If a field is not present, set it to null.
    2. Extract "Vintage" only if it looks like a year (19xx, 20xx).
    3. "Prosecco", "Champagne", "Cava" are REGIONS (or protected designations), not just varietals.
    4. For "Age", extract ONLY the number (e.g., "12" from "12 Year Old").
    
    Return ONLY JSON.
    """

    # Gemini 2.5 models use thinking tokens - need higher output limit
    gen_config = genai.GenerationConfig(
        temperature=0.0,
        max_output_tokens=2048,
    )
    response = client.generate_content(prompt, generation_config=gen_config)
    text = response.text.strip()
    # strip markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback empty dict if JSON fails
        return {}
        
    # Normalize nulls to empty strings for easier templating
    return {k: (v if v is not None else "") for k, v in data.items()}

# --- Step 3: Candidate Generation (Template-Based) ---
def generate_candidates(entities: Dict[str, str]) -> List[str]:
    """
    Generate candidate keywords using strict templates.
    """
    candidates = set()

    brand = entities.get('brand', '').strip()
    product = entities.get('product_name', '').strip()
    vintage = entities.get('vintage', '').strip()
    age = entities.get('age_statement', '').strip()
    prod_type = entities.get('product_type', '').strip()
    region = entities.get('region', '').strip()
    varietal = entities.get('varietal', '').strip()
    pack_format = entities.get('pack_format', '').strip()
    collection = entities.get('collection', '').strip()

    # Helper to clean and combine parts
    def combine(*parts):
        # Filter empty parts
        valid_parts = [p for p in parts if p]
        if not valid_parts:
            return ""
        
        text = " ".join(valid_parts).lower()
        # Normalize to ASCII but keep apostrophes logic later (clean_keyword handles casing)
        # Here we just want a clean lower string for the set
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
        
        return text.strip()

    # A) Strong Entities (unique names)
    if product:
        # {product_name}
        candidates.add(combine(product))
        # {product_name} {vintage}
        if vintage:
            candidates.add(combine(product, vintage))
        # {brand} {product_name}
        if brand:
            candidates.add(combine(brand, product))
            # {brand} {product_name} {vintage}
            if vintage:
                candidates.add(combine(brand, product, vintage))
            # {brand} {product_name} {product_type}
            if prod_type:
                 candidates.add(combine(brand, product, prod_type))
        # {product_name} wine
        candidates.add(combine(product, "wine"))

    # B) Age Statement Specific (High Value Simplification)
    # e.g. "Dalmore 15", "Macallan 12"
    if brand and age:
        candidates.add(combine(brand, age))
        if prod_type:
             candidates.add(combine(brand, age, prod_type))

    # C) Brand + Type (e.g. "Baileys Irish Cream Liqueur")
    if brand and prod_type and not age:
        candidates.add(combine(brand, prod_type))
        if product:
             candidates.add(combine(brand, product, prod_type))


    # D) Generic Entities (grape/region-led)
    # Disambiguation templates
    if varietal:
        # {varietal} {vintage}
        if vintage:
            candidates.add(combine(varietal, vintage))
        # {collection} {varietal} {vintage}
        if collection and vintage:
            candidates.add(combine(collection, varietal, vintage))
        # {varietal} majestic
        candidates.add(combine(varietal, "majestic"))
            
    if region:
        # {region} {vintage} wine
        if vintage:
            candidates.add(combine(region, vintage, "wine"))
        # {collection} {region} {vintage}
        if collection and vintage:
            candidates.add(combine(collection, region, vintage))

    # E) Pack Formats (Case)
    # Pack keywords usually win on MSV
    if pack_format or "case" in pack_format.lower():
        # {brand} {product_name} case
        if brand and product:
            candidates.add(combine(brand, product, "case"))
        
        # {product_name} mixed case
        if product:
            candidates.add(combine(product, "mixed case"))
            # {product_name} 6 bottle case
            candidates.add(combine(product, "6 bottle case"))
            # {product_name} wine case
            candidates.add(combine(product, "wine case"))
            
        # {brand} {product_name} red wine (if implied) - difficult to infer color without 'red' token 
        # but we can try generic "wine" if not present
        if brand and product:
            candidates.add(combine(brand, product, "wine"))

    # Extra: Fallback
    if not candidates and brand:
        candidates.add(combine(brand))
        if varietal:
             candidates.add(combine(brand, varietal))
             if vintage:
                 candidates.add(combine(brand, varietal, vintage))

    return list(candidates)

# --- Step 4: Scoring Logic (Weighted Model) ---
def score_candidates(candidates: List[str], entities: Dict[str, str], original_title_normalized: str) -> List[tuple]:
    """
    Score candidates using weighted model.
    """
    scored = []

    # Helper to clean for matching (strip accents, lower)
    def clean_for_match(s):
        if not s: return ""
        s = s.lower()
        s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode("utf-8")
        return s.strip()

    brand = clean_for_match(entities.get('brand', ''))
    product = clean_for_match(entities.get('product_name', ''))
    vintage = clean_for_match(entities.get('vintage', ''))
    age = clean_for_match(entities.get('age_statement', ''))
    prod_type = clean_for_match(entities.get('product_type', ''))
    pack_format = clean_for_match(entities.get('pack_format', ''))
    collection = clean_for_match(entities.get('collection', ''))
    
    # Check if brand is a retailer brand
    is_retailer_brand = brand in RETAILER_BRANDS
    
    # Identify critical tokens (digits in brand/product)
    # e.g. "Porta 6", "19 Crimes"
    critical_tokens = []
    if brand:
        critical_tokens.extend(re.findall(r'\d+', brand))
    # if product:
    #     critical_tokens.extend(re.findall(r'\d+', product))
    if age:
        critical_tokens.append(age)
    
    is_case = "case" in original_title_normalized.lower() or "case" in pack_format

    for cand in candidates:
        score = 0
        cand_lower = cand.lower()
        
        # +5 if contains product core entity (product name)
        if product and product in cand_lower:
            score += 5
            
        # +4 if contains vintage (and title has vintage)
        if vintage and vintage in cand_lower:
            score += 4
            
        # +4 if contains brand (and title has brand)
        if brand and brand in cand_lower:
            if not is_retailer_brand:
                score += 4
            else:
                score -= 2
        
        # +6 NEW: Preferred Short Forms
        # "Brand + Age" (e.g. "Dalmore 15")
        if brand and age and (f"{brand} {age}" == cand_lower):
            score += 8  # Huge boost for specific simplifications
        
        # "Brand + Type" (e.g. "Baileys Liqueur" - simplification)
        if brand and prod_type and not age and (f"{brand} {prod_type}" == cand_lower):
            score += 6

        # "Brand + Product + Type"
        if brand and product and prod_type and (f"{brand} {product} {prod_type}" == cand_lower):
             score += 6

        # +3 if contains "case" (and title is a case)
        if is_case and "case" in cand_lower:
            score += 3
            
        # -6 if it drops a critical token (like age or number in brand)
        for token in critical_tokens:
            if token not in cand_lower:
                score -= 6
        
        # Penalize verbose "Year Old" if simpler "15" is available (implicit in candidates generation, 
        # but penalize if verbose tokens leak in via hallucination or bad extraction)
        if "year old" in cand_lower or "years old" in cand_lower:
            score -= 5
                
        # -5 if generic (only varietal/region, no brand/collection)
        if brand and brand not in cand_lower and collection and collection not in cand_lower:
            if not is_retailer_brand:
                score -= 5
        elif brand and brand not in cand_lower and not collection:
             if not is_retailer_brand:
                score -= 5
             
        scored.append((score, cand))

    # Sort by score desc, then length asc
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return scored


# --- Step 5: Post-Processing ---
def clean_keyword(keyword: str) -> str:
    """
    Final cleanup.
    - Custom Title Case (respects apostrophes)
    - Max 4 words roughly
    """
    if not keyword:
        return ""

    # Strip 4-digit years - REMOVED per user request to keep vintages (e.g. 2016)
    # keyword = re.sub(r'\b(19|20)\d{2}\b', '', keyword)

    # Strip age statements but KEEP the number (e.g. "12 Year Old" -> "12")
    # We replace "12 year old" with "12"
    keyword = re.sub(r'\b(\d+)\s*-?\s*(year|yr|yo)s?\s*(old)?\b', r'\1', keyword, flags=re.IGNORECASE)

    # Strip any remaining noise words
    words = keyword.lower().split()
    # Keep words if length > 1 OR if it's a digit (e.g. "6")
    words = [w for w in words if w not in NOISE_WORDS and (len(w) > 1 or w.isdigit())]

    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)

    # Limit to 5 words (to handle "Porta 6 Red Wine Case")
    unique_words = unique_words[:5]
    
    keyword_joined = " ".join(unique_words)

    # Custom Title Case: Capitalize start of string and any letter following a space
    # This prevents "Daniel's" becoming "Daniel'S" (standard title() behavior)
    def custom_title_case(s):
        return re.sub(r"(^|\s)([a-z])", lambda m: m.group(1) + m.group(2).upper(), s.lower())

    result = custom_title_case(keyword_joined)

    return result



# --- Step 6: Verification (New) ---
def verify_keyword_match(client, product_title: str, keyword: str) -> Dict[str, Any]:
    """
    Verify if a keyword is a valid match for a product title using LLM.
    Returns: {'match': 'Y'/'N', 'reason': '...'}
    """
    prompt = f"""
    You are an SEO keyword quality evaluator for e-commerce product pages. Your task is to evaluate if a generated keyword is a VALID match for a specific product's PDP.

    # EVALUATION CRITERIA

    ## Context
    - Keywords must likely lead a user to this product.
    - **BROAD KEYWORDS ARE ACCEPTABLE** if this product is a core/canonical version of that term.
    - Cannibalization is a concern, but do NOT reject a keyword just because it *could* apply to other variants, as long as it fits this one well.

    ## Evaluation Rules

    ### MATCH (Y - Good Keyword) IF:
    1. **Exact Product Match**: Keyword matches the specific product variant.
    2. **Core/Base Match (Broader Terms)**:
       - **ACCEPT** broad terms if the product is a standard/representative version.
       - **Electronics**: "Apple iPad 10.2 (9th Gen)" -> "ipad" = **YES** (It IS an iPad).
       - **Furniture**: "Herman Miller Aeron Office Chair" -> "herman miller aeron" = **YES**.
       - **Luggage**: "Samsonite Winfield 2 Hardside Luggage" -> "samsonite luggage" = **YES**.
       - **Pets**: "Royal Canin Golden Retriever Puppy Food" -> "royal canin puppy food" = **YES**.
       - **Toys**: "LEGO Star Wars Millennium Falcon" -> "lego millennium falcon" = **YES**.
       - **Baby**: "Pampers Swaddlers Diapers Size 1" -> "pampers swaddlers" = **YES**.

    3. **Appropriate Specificity**: Includes key differentiators when necessary, but handles "implied" defaults.
       - Example: "Whispering Angel Rosé" -> "whispering angel" = **YES** (The Rosé is the main product people mean).

    ### NO MATCH (N - Bad Keyword) IF:
    1. **Factually Wrong**: Keyword describes a completely different product.
       - Example: "Macallan 15" -> "macallan 12" = **NO** (Wrong age).
       - Example: "Prosecco" -> "Champagne" = **NO**.
       - Example: "iPhone 13 Case" -> "iphone 13" = **NO** (It's a case, not the phone).

    2. **Completely Misses the Point**:
       - Example: "Red Wine Glass" -> "red wine" = **NO** (It's a glass, not wine).
       - Example: "Dog Food Bowl" -> "dog food" = **NO**.

    3. **Too Generic (Category Level)**:
       - Example: "Jack Daniel's" -> "whisky" = **NO** (Too broad, it's a category).
       - Example: "Sony Bravia TV" -> "electronics" = **NO**.
       - Example: "Barbie Dreamhouse" -> "toys" = **NO**.
       - *Exception*: If the brand IS the category leader, sometimes short is okay, but "toys" alone is usually too vague.

    # INPUT
    Product Title: "{product_title}"
    Keyword: "{keyword}"

    # OUTPUT FORMAT
    Output JSON ONLY:
    {{
        "match": "Y" or "N",
        "reason": "Short explanation (max 15 words)"
    }}
    """

    gen_config = genai.GenerationConfig(
        temperature=0.0,
        max_output_tokens=128,
        response_mime_type="application/json"
    )

    try:
        response = client.generate_content(prompt, generation_config=gen_config)
        text = response.text.strip()
        data = json.loads(text)
        
        # Normalize output keys to be safe
        match_val = data.get('match', 'N').upper()
        # Fallback if LLM gives True/False instead of Y/N
        if match_val == 'TRUE': match_val = 'Y'
        if match_val == 'FALSE': match_val = 'N'
        
        return {
            'match': match_val,
            'reason': data.get('reason', 'No reason provided')
        }
    except Exception as e:
        return {'match': 'N', 'reason': f"Error: {str(e)}"}


# --- Parallel Verification ---
def verify_keywords_bulk(
    df: pd.DataFrame,
    title_col: str,
    keyword_col: str,
    progress_callback=None,
    model_name: str = "gemini-2.5-flash-lite",
    max_workers: int = 10
) -> pd.DataFrame:
    """
    Verify keywords in bulk using threads.
    """
    df = df.copy()
    client = get_gemini_client(model_name)
    if not client:
        raise ValueError("API Key not found or client init failed")

    # Prepare results columns
    df['Match'] = ""
    df['Reason'] = ""

    total_items = len(df)
    completed = 0

    def process_row(idx, row):
        t = str(row.get(title_col, ''))
        k = str(row.get(keyword_col, ''))
        try:
            res = verify_keyword_match(client, t, k)
            return idx, res['match'], res['reason']
        except Exception as e:
            return idx, 'N', f"Error: {str(e)}"

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, row in df.iterrows():
            futures.append(executor.submit(process_row, idx, row))

        for future in as_completed(futures):
            idx, match, reason = future.result()
            df.at[idx, 'Match'] = match
            df.at[idx, 'Reason'] = reason
            
            completed += 1
            if progress_callback:
                progress_callback(completed / total_items, completed, total_items)

    return df


# --- Parallel Processing ---
def generate_keywords_advanced_parallel(
    df: pd.DataFrame,
    progress_callback=None,
    model_name: str = "gemini-2.5-flash-lite",
    max_workers: int = 10,
    api_delay: float = 0.1
) -> pd.DataFrame:
    """
    Run the advanced pipeline in parallel using ThreadPoolExecutor.
    """
    df = df.copy()
    if 'Product Keyword' not in df.columns:
        df['Product Keyword'] = ""

    client = get_gemini_client(model_name)
    if not client:
        raise ValueError("API Key not found or client init failed")

    # Collect errors for reporting
    errors_collected = []

    total_items = len(df)
    completed = 0

    def process_single_row(idx, row):
        try:
            time.sleep(api_delay) # slight stagger
            title = str(row.get('Product Title', ''))

            # Pipeline
            norm = normalize_title(title)
            entities = extract_entities(client, norm)

            # Check if entity extraction produced anything
            has_entities = any(v for v in entities.values() if v)
            if not has_entities:
                return idx, "", f"No entities extracted for: {title[:50]}"

            candidates = generate_candidates(entities)
            if not candidates:
                return idx, "", f"No candidates generated for: {title[:50]}"

            scores = score_candidates(candidates, entities, norm)

            best_keyword = scores[0][1] if scores else ""
            # Clean up the keyword
            best_keyword = clean_keyword(best_keyword)
            return idx, best_keyword, None
        except Exception as e:
            return idx, "", str(e)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, row in df.iterrows():
            futures.append(executor.submit(process_single_row, idx, row))

        for future in as_completed(futures):
            idx, keyword, error = future.result()

            if keyword:
                df.at[idx, 'Product Keyword'] = keyword

            if error:
                errors_collected.append(error)

            completed += 1
            if progress_callback:
                progress_callback(completed / total_items, completed, total_items)

    # Attach errors to dataframe for UI to display
    df.attrs['errors'] = errors_collected[:20]  # Limit to first 20

    return df

if __name__ == "__main__":
    # Helper for existing CLI test
    pass
