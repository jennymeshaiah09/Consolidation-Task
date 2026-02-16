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
    Uses the new detailed prompt for high-quality, cost-effective generation.
    """
    # Sanitize inputs
    def sanitize(text):
        text = str(text).replace('"', "'").replace('\n', ' ').replace('\r', ' ')
        text = text.replace('\\', ' ').strip()
        return text[:100]
    
    # Construct structured list for the prompt
    items_text = ""
    for item in batch_data:
        title = sanitize(item['title'])
        brand = sanitize(item['brand'])
        # Only include brand if it's meaningful
        brand_part = f" | Brand: {brand}" if brand and brand.lower() not in ('', 'nan', 'none') else ""
        items_text += f'{{"product": "{title}{brand_part}", "id": "{item["id"]}"}}\n'

    prompt = f"""You are an ecommerce SEO keyword extraction specialist for alcohol retail products.

Your job is to generate realistic Google search queries customers would use to find the exact product.

Focus on product-identifying words with high search intent.

--------------------------------
TASK
--------------------------------

Extract 3 search-friendly keyword variations from each product title.

Return ONLY valid JSON.

--------------------------------
CORE PRINCIPLE (MOST IMPORTANT)
--------------------------------

Choose the most specific product-identifying words users would search.

Priority order:

1. Brand + Age Statement (e.g., "Dalmore 15", "Macallan 12") -> STRONGEST SIGNAL
2. Brand + Product Type (e.g., "Baileys Irish Cream Liqueur", "Kraken Rum")
3. Exact product name or cuvée (e.g., "Blue Label", "Nastro Azzurro")
4. Product name + vintage (for wine)

Prefer simplest, shortest forms.

--------------------------------
BRAND DECISION RULE
--------------------------------

Ask:

"Would someone search this brand name alone?"

YES → keep brand (moet, kraken, glenfiddich, grey goose, au vodka)
NO → drop brand and use product/region/type instead.

Always DROP retailer labels:
majestic, chosen by, tesco, waitrose, amazon.

If unsure → keep product name.

--------------------------------
KEEP WHEN IDENTIFYING THE PRODUCT
--------------------------------

- product name / cuvée / label
- vintage year for wine
- grape variety or spirit type
- recognised brand names
- well-known regions (bordeaux, champagne, rioja, barolo)
- spirit age statements (12, 15, 18) - BUT REMOVE "Year Old" text
- flavour descriptors when core product difference
- wine classifications (doc, reserva, cru)

--------------------------------
REMOVE
--------------------------------

- "Year Old", "Years Old", "YO" (Use just the number: "12" not "12 Year Old")
- "Single Malt" (Use just "Whisky" or implied by brand)
- promotions or marketing text
- packaging or bundle wording
- retailer messaging
- celebrity endorsements
- size or volume
- gift wording
- non-essential modifiers

--------------------------------
WINE RULES
--------------------------------

- keep vintage when present
- keep château/domaine if recognised wine
- for generic wines use grape or region
- do not collapse specific wine to generic "wine"

--------------------------------
SPIRITS RULES
--------------------------------

- brand usually primary search driver
- SIMPLIFY Age Statements: "12 Year Old" -> "12"
- SIMPLIFY Types: "Irish Cream Liqueur" -> "Liqueur" (if implied) or keep simple type

--------------------------------
KEYWORD GENERATION
--------------------------------

Keyword 1 — Core Intent (Brand + Age/Type)
e.g. "Dalmore 15", "Baileys Liqueur"

Keyword 2 — Add Specificity
e.g. "Baileys Irish Cream Liqueur", "Dalmore 15 Whisky"

Keyword 3 — Alternative Discovery  
Different structure or modifier.

ADDITIONAL RULES:
- For wine products include vintage as one variation if available.
- If product is a case or mix, prefer generic search phrase like "mixed wine case".
- If product entity is weak or generic, prefer product type.

--------------------------------
FORMAT RULES
--------------------------------

- 2–4 words preferred
- lowercase (except brand names like Au Vodka)
- remove accents (moët → moet)
- natural search order
- each keyword must be different
- no explanations

--------------------------------
INPUT DATA
--------------------------------
{items_text}

--------------------------------
OUTPUT FORMAT (STRICT JSON)
--------------------------------

{{
  "id_1": "keyword1",
  "id_2": "keyword1"
}}

Note: Return a single best keyword per ID (choose the best from the 3 variations you generated internally).
Return strictly a JSON object mapping ID to the single best search keyword.
"""

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
                "temperature": 0.1,
                "max_output_tokens": 8192,  # Increased for batch output
                "response_mime_type": "application/json"
            },
            safety_settings=safety_settings
        )
        
        if not response.parts or not response.text:
            print(f"  [BATCH {batch_id}] Blocked by safety filters.")
            return {}

        text = response.text.strip()
        
        # Clean markdown
        if '```' in text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if match:
                text = match.group(1).strip()
            else:
                text = text.replace('```json', '').replace('```', '').strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback regex
            result = {}
            pattern = r'"(\d+)"\s*:\s*"([^"]*)"'
            matches = re.findall(pattern, text)
            for k, v in matches:
                result[k] = v.strip()
            return result

    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
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
        prompt = f"""You are an ecommerce SEO keyword specialist.

Output up to 5 realistic Google search phrases a customer would type to find this exact product.

Prioritise the most specific product-identifying words that match how products are searched.

PRIORITY ORDER:
1. Brand + Age Statement (e.g., "Dalmore 15", "Macallan 12") -> STRONGEST SIGNAL
2. Brand + Product Type (e.g., "Baileys Irish Cream Liqueur", "Kraken Rum")
3. Exact product name / cuvée / label (strongest)
4. Product name + vintage (if wine or year identifies the product)

IMPORTANT RULES:

KEEP when they identify the product:
- Product name / cuvée / label
- Vintage year for wine
- Numbers that are part of brand names (Porta 6)
- Collection names (Chosen by Majestic)
- Age Statements (Number ONLY, e.g. "12", "15")

DROP only if NOT product identifying:
- "Year Old", "Years Old", "YO" (Use just the number: "12" not "12 Year Old")
- "Single Malt" (Use just "Whisky" or implied by brand)
- Sizes / volumes
- Pack quantities
- ABV
- Promotions
- Retailers
- Gift / bundle wording

For wine specifically:
- KEEP vintage year
- KEEP product label names
- Do NOT collapse to generic "wine"

For whisky/spirits:
- SIMPLIFY Age Statements: "12 Year Old" -> "12"
- SIMPLIFY Types: "Irish Cream Liqueur" -> "Liqueur" (if implied) or keep simple type

Title: {title}{brand_line}

OUTPUT RULES:
- Lowercase
- Plain text (no accents)
- 2–4 words preferred
- Return only keywords, one per line.
"""

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
                    # Handle multiple lines - take the first non-empty line
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if lines:
                        keyword = lines[0]
                        keyword = keyword.strip().strip('"').strip("'")
                        # Post-process: strip special chars, normalise whitespace
                        keyword = keyword.replace('&', 'And')
                        keyword = re.sub(r'[^A-Za-z0-9 ]', '', keyword)
                        keyword = re.sub(r'\s+', ' ', keyword).strip()
                        # User requested lowercase in prompt, but we usually like Title Case for UI.
                        # However, prompt said "Lowercase". Let's stick to Title Case for consistency 
                        # or respect Prompt? 
                        # The user prompt: "Output up to 5... Lowercase... Return only keywords"
                        # But typically the UI expects Title Case. 
                        # I will stick to .title() for UI consistency, or should I leave it lower?
                        # User specifically asked for Lowercase.
                        # But `src/keyword_generator.py` (Advanced) does custom_title_case.
                        # I will use .lower() to match the Prompt's "Lowercase" rule strictly.
                        # Wait, the previous code forced .title().
                        # If I change to lower, it might look different.
                        # Let's use lower() since the user explicitly put it in the prompt rules.
                        keyword = keyword.lower()
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

def generate_keywords_batch(
    df: pd.DataFrame,
    product_type: str,
    progress_callback=None,
    batch_size: int = 20,
    delay_between_batches: float = 0.5,
    model_name: str = "gemini-2.5-flash-lite",
    max_products: int = None,
    max_workers: int = 5
) -> pd.DataFrame:
    """
    Generate keywords using Parallel Batch Processing (The Winner).
    Chunks data -> Sends batches in parallel -> Merges results.
    """
    model = get_gemini_client(model_name)
    if model is None:
        raise ValueError("GOOGLE_API_KEY not set")

    df = df.copy()
    if 'Product Keyword' not in df.columns:
        df['Product Keyword'] = ""
        
    # Slice if max_products set
    if max_products is not None and max_products > 0:
        target_df = df.head(max_products)
    else:
        target_df = df

    # Prepare batches
    # Filter for rows that actually need keywords? Or just specific ones?
    # For now, process all in target_df
    
    indices = target_df.index.tolist()
    chunks = [indices[i:i + batch_size] for i in range(0, len(indices), batch_size)]
    
    total_items = len(target_df)
    print(f"Starting PARALLEL BATCH generation for {total_items} items.")
    print(f"Configuration: {len(chunks)} batches, {batch_size} items/batch, {max_workers} workers.")

    results_map = {}
    errors = []
    
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_batch_task(chunk_indices, batch_idx):
        batch_payload = []
        for idx in chunk_indices:
            row = target_df.loc[idx]
            batch_payload.append({
                "id": str(idx),
                "title": str(row.get('Product Title', '')),
                "brand": str(row.get('Product Brand', ''))
            })
            
        # Retry logic for the batch
        for attempt in range(3):
            try:
                # Add delay based on worker usage to avoid initial spike
                time.sleep(delay_between_batches * attempt)
                
                batch_result = generate_batch_keywords_api(model, batch_payload, batch_idx)
                if batch_result:
                    return batch_result
            except QuotaExceededError:
                time.sleep(5 * (attempt + 1))  # Specific backoff for quota
            except Exception as e:
                errors.append(f"Batch {batch_idx} error: {e}")
                time.sleep(1)
        
        return {}

    # Execute
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, chunk in enumerate(chunks):
            future = executor.submit(process_batch_task, chunk, i+1)
            futures[future] = len(chunk)
            
        completed_items = 0
        
        for future in as_completed(futures):
            num_in_batch = futures[future]
            try:
                batch_res = future.result()
                
                # Update map
                for str_id, keyword in batch_res.items():
                    # clean up
                    if keyword and keyword.lower() not in ('blocked', 'error'):
                        try:
                            # Ensure ID matches index type (int)
                            idx = int(str_id)
                            results_map[idx] = keyword
                        except:
                            pass
                            
                completed_items += num_in_batch
                if progress_callback:
                    progress_callback(completed_items / total_items, completed_items, total_items)
                    
            except Exception as e:
                errors.append(f"Future block error: {e}")

    # Apply results
    for idx, keyword in results_map.items():
        if keyword:
            df.at[idx, 'Product Keyword'] = keyword

    df.attrs['errors'] = errors
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


def extract_brands_batch(
    df: pd.DataFrame,
    progress_callback=None,
    batch_size: int = 30,
    model_name: str = "gemini-2.5-flash-lite",
    max_workers: int = 5
) -> pd.DataFrame:
    """
    Extract missing brands from Product Title using LLM.
    If brand cannot be determined, returns "Unbranded".
    """
    model = get_gemini_client(model_name)
    if model is None:
        raise Exception("GOOGLE_API_KEY not set.")

    df = df.copy()

    # Normalize column names
    if 'Product Brand' not in df.columns:
        df['Product Brand'] = ""

    # Filter for missing brands (empty, NaN, None, or just whitespace)
    # We'll treat "Unbranded" as populated to avoid re-processing.
    def is_missing(val):
        s = str(val).lower().strip()
        return s in ('', 'nan', 'none', 'null') 

    missing_mask = df['Product Brand'].apply(is_missing)
    target_products = df[missing_mask]

    if len(target_products) == 0:
        print("No products with missing brands found.")
        return df

    print(f"Found {len(target_products)} products with missing brands.")
    print(f"Starting PARALLEL Brand Extraction (Batch Size: {batch_size}, Workers: {max_workers})...")

    # Helper function to process a single batch
    def process_batch(batch_idx, batch_payload):
        # Construct prompt
        items_text = ""
        for item in batch_payload:
            items_text += f"- ID: {item['id']}\n  Product: {item['title']}\n\n"

        prompt = f"""You are a data validation expert for an e-commerce catalog.

Your task is to EXTRACT the brand name from the product title.

Input Products:
{items_text}

Instructions:
1. Extract the BRAND NAME from the title.
2. If the brand is NOT clear or mentions "Generic", return "Unbranded".
3. Remove retailer names (Majestic, Tesco, etc.) if they appear as the brand, unless they are the private label.
4. Capitalize the brand name correctly (Title Case).
5. Return a strict JSON object mapping ID to Brand Name.

Example:
Product: "Baileys Original Irish Cream" -> Brand: "Baileys"
Product: "Red Wine 75cl" -> Brand: "Unbranded"
Product: "Smirnoff Red Label Vodka" -> Brand: "Smirnoff"

Expected Output Format:
{{
  "0": "BrandName",
  "1": "Unbranded"
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
                    generation_config={"temperature": 0.0, "max_output_tokens": 2048},
                    safety_settings=safety_settings
                )

                if not response.parts or not response.text:
                    return {}

                text = response.text.strip()
                
                # Robust cleanup
                try:
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        text = text[start:end+1]
                    else:
                        continue
                except Exception:
                    pass

                try:
                    batch_results = json.loads(text)
                    return batch_results
                except json.JSONDecodeError:
                    if attempt == 2:
                        print(f"  [BATCH {batch_idx}] JSON Error: {text[:100]}...")
                    continue

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(2 * (attempt + 1))
                    continue
                print(f"  [BATCH {batch_idx}] Error: {str(e)[:100]}")
                return {}
        
        return {}

    # Create batches
    indices = target_products.index.tolist()
    chunks = [indices[i:i + batch_size] for i in range(0, len(indices), batch_size)]
    
    results_map = {}  # index -> brand
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        
        # Submit all batches
        for i, chunk_indices in enumerate(chunks):
            batch_payload = []
            for idx in chunk_indices:
                row = target_products.loc[idx]
                batch_payload.append({
                    "id": str(idx),
                    "title": str(row.get('Product Title', '')),
                })
            
            future = executor.submit(process_batch, i+1, batch_payload)
            futures[future] = len(chunk_indices)

        # Collect results
        completed_items = 0
        total_items = len(target_products)
        
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
                for raw_id, brand in batch_result.items():
                    if brand:
                        results_map[int(raw_id)] = brand
            except Exception as e:
                print(f"Batch failed: {e}")

    # Apply results
    improved_count = 0
    for idx, brand in results_map.items():
        try:
            df.at[idx, 'Product Brand'] = brand
            improved_count += 1
        except Exception as e:
            pass

    print(f"✓ Extracted {improved_count} brands using LLM")

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

