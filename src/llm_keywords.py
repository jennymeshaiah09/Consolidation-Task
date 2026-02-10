"""
LLM Keyword Generation Module
Generates SEO-friendly product keywords using Google Gemini API.
Refactored for High-Speed Batch Processing.
"""

import os
import pandas as pd
from typing import Optional, List, Dict
import google.generativeai as genai
import time
import json
import re
from .taxonomy import get_taxonomy, format_categories_for_llm
from .normalization import extract_leaf_category
from . import get_google_api_key


class QuotaExceededError(Exception):
    """Exception raised when API quota is exceeded during batch processing."""
    pass


def get_gemini_client(model_name: str = "gemini-2.5-flash-lite"):
    """Initialize Google Gemini client."""
    api_key = get_google_api_key()
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def generate_batch_keywords_api(
    model,
    batch_data: List[Dict],
    batch_id: int
) -> Dict[str, str]:
    """
    Generate keywords for a batch of products in one API call.
    
    Args:
        batch_data: List of dicts checks incl. 'id', 'title', 'brand', 'type'
    
    Returns:
        Dictionary mapping ID -> Keyword
    """
    # Sanitize inputs - remove characters that break JSON
    def sanitize(text):
        # Remove quotes, newlines, and JSON-breaking chars
        text = str(text).replace('"', "'").replace('\n', ' ').replace('\r', ' ')
        text = text.replace('\\', ' ').strip()
        return text[:100]  # Limit length
    
    # Construct a structured prompt for the batch
    items_text = ""
    for item in batch_data:
        title = sanitize(item['title'])
        brand = sanitize(item['brand'])
        brand_part = f" | Brand: {brand}" if brand and brand.lower() not in ('', 'nan', 'none') else ""
        items_text += f"{item['id']}: {title}{brand_part}\n"

    prompt = f"""You are a Google Ads keyword specialist. For each product, output the single search phrase a real customer would type into Google. Short and punchy — if in doubt, drop the word.

Products:
{items_text}

KEEP: Brand (if given) + Product Type. Add one distinguishing feature only if it genuinely changes what the product is.
Product types to always keep: Champagne, Whisky, Wine, Rose, Lager, Gin, Vodka, Rum, Tequila, Liqueur, Cider, Prosecco, Bourbon, Brandy, Cognac, Scotch, Sake, Whiskey, Beer, Ale, Stout, Port, Sherry, Vermouth, Absinthe, Mead, Perry.

BRAND WARNING: The Brand field sometimes contains the estate or producer (e.g. Château d'Esclans) rather than the consumer-facing brand. If the title already contains a distinct, more recognisable brand name (e.g. Whispering Angel), use THAT as the brand and DROP the estate/producer from the Brand field entirely.

DROP everything below — none of it adds search value:
- Sizes / volumes: ml, cl, L, oz, 700ml, 750ml, 1L, 330ml
- Quantities: 6 pack, 12 pack, 24x330ml
- ABV: 40%, ABV, vol, proof
- Promotional: gift, hamper, personalised, offer, deal, bestseller, sale
- Age / vintage: 12 Year Old, 18 Year, 2023, 2024 — drop entirely, not even abbreviated
- Multipack: case, set, mixed, selection, tasting, bundle, collection
- Retailers: Laithwaites, Waitrose, Tesco, Amazon, Majestic
- Filler / generic: premium, classic, original, reserve, special, limited, edition, vintage, imperial, brut, single malt, blended, dry, smooth, rich, delicate, finest, authentic, natural, real, true, great, extra
- Geography (unless it IS the brand): Scottish, Tennessee, French, Highland, Islay, Kentucky, Irish, London, Italian, Spanish
- Accents → plain text: rosé → rose, moët → moet, château → chateau

EXAMPLES:
"Johnnie Walker Black Label 12 Year Old Blended Scotch Whisky 700ml | Brand: Johnnie Walker" → Johnnie Walker Whisky
"Bollinger Special Cuvee Brut Champagne 750ml | Brand: Bollinger" → Bollinger Champagne
"Tanqueray London Dry Gin 1L Gift Edition | Brand: Tanqueray" → Tanqueray Gin
"Stella Artois Lager 24x330ml | Brand: Stella Artois" → Stella Artois Lager
"Whispering Angel Rosé 2023 750ml | Brand: Château d'Esclans" → Whispering Angel Rose

FORMAT: Return ONLY a JSON object mapping ID to keyword. Title Case values.
{{"0": "Brand Product", "1": "Product Type"}}

No explanation. No markdown. Just the JSON."""

    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0,  # More deterministic
                "max_output_tokens": 2048,
                "response_mime_type": "application/json"  # Force JSON output
            },
            safety_settings=safety_settings
        )
        
        if not response.parts or not response.text:
            print(f"  [BATCH {batch_id}] Blocked by safety filters.")
            return {item['id']: "BLOCKED" for item in batch_data}

        # Parse JSON from response
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        if '```' in text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if match:
                text = match.group(1).strip()
            else:
                text = text.replace('```json', '').replace('```', '').strip()
        
        # Try standard JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # FALLBACK: Extract key-value pairs using regex (handles malformed JSON)
        result = {}
        # Match patterns like "0": "keyword here" or "0":"keyword"
        pattern = r'"(\d+)"\s*:\s*"([^"]*)"'
        matches = re.findall(pattern, text)
        
        if matches:
            for key, value in matches:
                result[key] = value.strip()
            return result
        
        # Last resort: try to fix common issues
        fixed = text.replace("'", '"')  # Single to double quotes
        fixed = re.sub(r',\s*}', '}', fixed)  # Trailing commas
        fixed = re.sub(r',\s*]', ']', fixed)  # Trailing commas in arrays
        
        try:
            return json.loads(fixed)
        except:
            print(f"  [BATCH {batch_id}] JSON Error: Could not parse response")
            return {}

    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg or "resource" in error_msg:
            raise QuotaExceededError("API Quota Exceeded")
        print(f"  [BATCH {batch_id}] Error: {str(e)[:100]}")
        return {}


def generate_keywords_parallel(
    df: pd.DataFrame,
    progress_callback=None,
    model_name: str = "gemini-2.5-flash-lite",
    max_workers: int = 10
) -> pd.DataFrame:
    """
    Generate keywords using Parallel Single Requests (Accurate & Reliable).
    Instead of batching (which causes JSON errors), we send single requests in parallel.
    """
    model = get_gemini_client(model_name)
    if model is None:
        raise ValueError("GOOGLE_API_KEY not set")

    df = df.copy()
    if 'Product Keyword' not in df.columns:
        df['Product Keyword'] = ""
    
    # Filter rows that need keywords
    # If we want to process all, just use df.iterrows()
    # For now, let's assume we overwrite or fill empty
    
    total_items = len(df)
    print(f"Starting PARALLEL keyword generation for {total_items} items (Workers: {max_workers})...")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Thread-safe error collector — list.append() is atomic in CPython
    errors = []

    # Helper for single generation
    def process_single(idx, row):
        _title = row.get('Product Title', '')
        title = str(_title).replace('"', "'")[:200] if pd.notna(_title) else ''
        _brand = row.get('Product Brand', '')
        brand = str(_brand).replace('"', "'")[:50] if pd.notna(_brand) else ''

        brand_line = f"\nBrand: {brand}" if brand else ""
        prompt = f"""You are a Google Ads keyword specialist. Output the single search phrase a real customer would type into Google to find this product. Short and punchy — if in doubt, drop the word.

Title: {title}{brand_line}

KEEP: Brand (if given) + Product Type. Add one distinguishing feature only if it genuinely changes what the product is.
Product types to always keep: Champagne, Whisky, Wine, Rose, Lager, Gin, Vodka, Rum, Tequila, Liqueur, Cider, Prosecco, Bourbon, Brandy, Cognac, Scotch, Sake, Whiskey, Beer, Ale, Stout, Port, Sherry, Vermouth, Absinthe, Mead, Perry.

BRAND WARNING: The Brand field sometimes contains the estate or producer (e.g. Château d'Esclans) rather than the consumer-facing brand. If the title already contains a distinct, more recognisable brand name (e.g. Whispering Angel), use THAT as the brand and DROP the estate/producer from the Brand field entirely.

DROP everything below — none of it adds search value:
- Sizes / volumes: ml, cl, L, oz, 700ml, 750ml, 1L, 330ml
- Quantities: 6 pack, 12 pack, 24x330ml
- ABV: 40%, ABV, vol, proof
- Promotional: gift, hamper, personalised, offer, deal, bestseller, sale
- Age / vintage: 12 Year Old, 18 Year, 2023, 2024 — drop entirely, not even abbreviated
- Multipack: case, set, mixed, selection, tasting, bundle, collection
- Retailers: Laithwaites, Waitrose, Tesco, Amazon, Majestic
- Filler / generic: premium, classic, original, reserve, special, limited, edition, vintage, imperial, brut, single malt, blended, dry, smooth, rich, delicate, finest, authentic, natural, real, true, great, extra
- Geography (unless it IS the brand): Scottish, Tennessee, French, Highland, Islay, Kentucky, Irish, London, Italian, Spanish
- Accents → plain text: rosé → rose, moët → moet, château → chateau

EXAMPLES:
Title: Johnnie Walker Black Label 12 Year Old Blended Scotch Whisky 700ml 40% ABV | Brand: Johnnie Walker
→ Johnnie Walker Whisky

Title: Bollinger Special Cuvee Brut Champagne 750ml | Brand: Bollinger
→ Bollinger Champagne

Title: Tanqueray London Dry Gin 1L Gift Edition | Brand: Tanqueray
→ Tanqueray Gin

Title: Stella Artois Lager 24x330ml | Brand: Stella Artois
→ Stella Artois Lager

Title: Whispering Angel Rosé 2023 750ml | Brand: Château d'Esclans
→ Whispering Angel Rose

Title Case. No quotes. No explanation. Return ONLY the keyword."""

        # SDK 0.8.4 has no thinking_config — 2.5 models use thinking by
        # default and thinking tokens count against max_output_tokens.
        # 2048 is needed so thinking + keyword both fit.
        gen_config = genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=2048,
        )

        for attempt in range(3):
            try:
                response = model.generate_content(prompt, generation_config=gen_config)

                # .text is a property that can raise on blocked/empty responses —
                # catch that explicitly instead of letting it fall through silently.
                text = None
                try:
                    if response.text:
                        text = response.text
                except Exception:
                    pass

                if not text:
                    try:
                        if response.parts and response.parts[0].text:
                            text = response.parts[0].text
                    except Exception:
                        pass

                if text:
                    keyword = text.strip().strip('"').strip("'")
                    # Post-process: strip special chars, normalise whitespace,
                    # then title-case so output is consistent regardless of
                    # what case the LLM chose.
                    keyword = keyword.replace('&', 'And')
                    keyword = re.sub(r'[^A-Za-z0-9 ]', '', keyword)
                    keyword = re.sub(r'\s+', ' ', keyword).strip()
                    keyword = keyword.title()
                    if keyword:
                        return idx, keyword

                # Empty response — retry before giving up
                if attempt < 2:
                    continue
                errors.append(f"idx={idx}: empty response after {attempt+1} attempts")
                return idx, None

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    if attempt < 2:
                        time.sleep(1 * (attempt + 1))
                        continue
                errors.append(f"idx={idx}: {str(e)[:150]}")
                return idx, None
        return idx, None

    # Execute in parallel
    results_map = {}
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_single, idx, row): idx for idx, row in df.iterrows()}
        
        for future in as_completed(futures):
            idx, keyword = future.result()
            if keyword:
                results_map[idx] = keyword
            
            completed += 1
            if progress_callback and completed % 10 == 0:
                progress_callback(completed / total_items, completed, total_items)

    # Apply results
    for idx, keyword in results_map.items():
        if keyword:
            df.at[idx, 'Product Keyword'] = keyword

    # Attach collected errors so callers can surface them
    df.attrs['errors'] = errors
    return df

# Legacy batch function (kept for compatibility but deprecated functionality)
def generate_keywords_batch(
    df: pd.DataFrame,
    product_type: str,
    progress_callback=None,
    batch_size: int = 20,
    delay_between_batches: float = 0.0,
    model_name: str = "gemini-2.5-flash-lite",
    max_products: int = None
) -> pd.DataFrame:
    # Redirect to new parallel method if using Gemini models
    if "gemini" in model_name.lower():
        # Map batch_size to max_workers roughly (limit to 20 threads to be safe)
        workers = min(batch_size, 20)
        
        # Handle max_products slicing here if needed
        target_df = df if max_products is None or max_products == 0 else df.head(max_products)
        
        result_df = generate_keywords_parallel(
            target_df,
            progress_callback=progress_callback,
            model_name=model_name,
            max_workers=workers
        )
        
        # Propagate any collected errors to the caller
        df.attrs['errors'] = result_df.attrs.get('errors', [])

        # Merge back if we sliced a subset; otherwise result_df IS the full set
        if max_products and max_products > 0:
            df.update(result_df)
            return df
        return result_df
    return df


def classify_other_products_batch(
    df: pd.DataFrame,
    product_type: str,
    progress_callback=None,
    batch_size: int = 30,
    model_name: str = "gemini-2.5-flash-lite",  # Sync with Keyword Generator model
    max_workers: int = 5
) -> pd.DataFrame:
    """
    Classify products marked as "Other" using LLM with Excel taxonomy.
    Uses PARALLEL processing for speed.

    Args:
        df: DataFrame with Product Category column
        product_type: Product type (BWS, Pets, Electronics)
        progress_callback: Optional progress callback function
        batch_size: Number of products per API call (Default 30)
        model_name: Gemini model to use
        max_workers: Number of parallel threads (Default 5)

    Returns:
        DataFrame with updated Product Category for "Other" products
    """
    model = get_gemini_client(model_name)
    if model is None:
        raise Exception("GOOGLE_API_KEY not set. Please check your .env file.")

    df = df.copy()

    # Determine the category column (Phase 1 uses L3, legacy might use 'Product Category')
    if 'Product Category L3' in df.columns:
        category_col = 'Product Category L3'
    elif 'Product Category' in df.columns:
        category_col = 'Product Category'
    else:
        raise Exception("Missing Column: Could not find 'Product Category L3' or 'Product Category' in data.")

    # Filter only "Other" products
    other_mask = df[category_col] == 'Other'
    other_products = df[other_mask]

    if len(other_products) == 0:
        # This shouldn't happen if UI showed the button, implies sync issue
        raise Exception(f"No products found with '{category_col}' = 'Other' (found 0). Refresh page?")

    print(f"\nFound {len(other_products)} products with 'Other' category.")
    print(f"Starting PARALLEL LLM classification (Batch Size: {batch_size}, Workers: {max_workers})...")

    # Load taxonomy
    try:
        taxonomy = get_taxonomy()
        categories_text = format_categories_for_llm(product_type, taxonomy)
        if not categories_text or categories_text == "No categories available":
             raise Exception(f"No categories found for Product Type '{product_type}'. Check taxonomy file.")
    except Exception as e:
        raise Exception(f"Taxonomy Error: {str(e)}")

    # Helper function to process a single batch
    def process_batch(batch_idx, batch_payload):
        # Construct prompt
        items_text = ""
        for item in batch_payload:
            items_text += f"- ID: {item['id']}\n  Product: {item['title']}\n  Brand: {item['brand']}\n\n"

        prompt = f"""You are classifying products into categories for an e-commerce catalog.

Product Type: {product_type}

Available Categories:
{categories_text}

Products to Classify:
{items_text}

Instructions:
1. Return a VALID JSON object where keys are the IDs and values are the category names.
2. Choose the BEST MATCHING category from the list above.
3. Use the EXACT category name as shown (e.g., "Wine > Red Wine", "Audio > Speakers").
4. If no good match exists, use "Other".
5. Focus on the product type, not the brand.

Expected Output Format:
{{
  "0": "Category > Subcategory",
  "1": "Category > Subcategory"
}}

Return ONLY the JSON object."""

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Retry logic
        for attempt in range(3):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.1, "max_output_tokens": 2048},
                    safety_settings=safety_settings
                )

                if not response.parts or not response.text:
                    return {}

                # Parse JSON
                text = response.text.strip()
                
                # Robust cleanup: find first '{' and last '}'
                try:
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        text = text[start:end+1]
                    else:
                        if attempt == 2: print(f"  [BATCH {batch_idx}] Error: No JSON object found in response")
                        continue
                except Exception:
                    pass

                # Fix common JSON errors if needed
                # text = text.replace("'", '"') # Dangerous if names contain apostrophes

                try:
                    batch_results = json.loads(text)
                    
                    # Validate keys are in payload
                    valid_results = {}
                    payload_ids = {item['id'] for item in batch_payload}
                    
                    for k, v in batch_results.items():
                        if k in payload_ids:
                            valid_results[k] = v
                            
                    return valid_results
                except json.JSONDecodeError:
                    if attempt == 2:
                        print(f"  [BATCH {batch_idx}] JSON Error. Raw: {text[:100]}...")
                        # print(f"DEBUG RAW: {text}") 
                        return {}
                    continue

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                    continue
                print(f"  [BATCH {batch_idx}] Error: {str(e)[:100]}")
                return {}
        
        return {}


    # Create batches
    indices = other_products.index.tolist()
    chunks = [indices[i:i + batch_size] for i in range(0, len(indices), batch_size)]
    
    results_map = {}  # index -> category
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        
        # Submit all batches
        for i, chunk_indices in enumerate(chunks):
            batch_payload = []
            for idx in chunk_indices:
                row = other_products.loc[idx]
                batch_payload.append({
                    "id": str(idx),
                    "title": str(row.get('Product Title', '')),
                    "brand": str(row.get('Product Brand', ''))
                })
            
            future = executor.submit(process_batch, i+1, batch_payload)
            futures[future] = len(chunk_indices)

        # Collect results
        completed_items = 0
        total_items = len(other_products)
        
        for future in as_completed(futures):
            # Update progress
            num_items = futures[future]
            completed_items += num_items
            
            if progress_callback:
                progress_callback(completed_items / total_items, completed_items, total_items)

            # Process result
            try:
                batch_result = future.result()
                
                # Map results back
                for raw_id, category in batch_result.items():
                    if category and category != "Other":
                        # Extract only the leaf category (most specific)
                        leaf_category = extract_leaf_category(category)
                        results_map[int(raw_id)] = leaf_category
            except Exception as e:
                print(f"Batch failed: {e}")

    # Apply results
    improved_count = 0
    for idx, category in results_map.items():
        try:
            df.at[idx, category_col] = category
            improved_count += 1
        except Exception as e:
            pass

    print(f"✓ Improved {improved_count} categories from 'Other' using LLM")

    return df


def validate_api_key() -> bool:
    return get_google_api_key() is not None


def test_api_connection(model_name: str = "gemini-2.5-flash-lite") -> tuple[bool, str]:
    model = get_gemini_client(model_name)
    if model is None: return False, "No API Key"
    try:
        model.generate_content("Test", generation_config={"max_output_tokens": 5})
        return True, "Connected"
    except Exception as e:
        return False, str(e)

