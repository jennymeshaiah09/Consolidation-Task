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


class QuotaExceededError(Exception):
    """Exception raised when API quota is exceeded during batch processing."""
    pass


def get_gemini_client(model_name: str = "gemma-3-4b-it"):
    """Initialize Google Gemini client."""
    api_key = os.getenv("GOOGLE_API_KEY")
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
    # Construct a structured prompt for the batch
    items_text = ""
    for item in batch_data:
        items_text += f"- ID: {item['id']}\n  Product: {item['title']}\n  Brand: {item['brand']}\n  Category: {item['type']}\n\n"

    prompt = f"""You are generating search keywords for an e-commerce product catalog optimized for MSV (Monthly Search Volume).

Create concise search keywords that match what customers actually type into search engines.

Input Data:
{items_text}

CRITICAL RULES - Keywords that violate these get ZERO search volume:

1. LENGTH: Maximum 4 words total. 96% of keywords with MSV are under 7 words, with 2-4 words being optimal.
   Formula: Brand + Product Type + (optional 1 differentiator)

2. REMOVE size/volume units: NO ml, cl, L, oz, kg, g, 750ml, 24x330ml, 4cl miniature, etc.

3. SIMPLIFY age statements: "12 Year Old" → "12yr" (or drop entirely if brand is well-known)

4. REMOVE gift/personalization language: personalised, hamper, gift, present, gift set, gift box

5. REMOVE vintage years: Drop 4-digit years (2024, 2023, 2022, etc.) unless brand-critical

6. REMOVE case/multipack descriptors: mixed case, tasting set, selection, variety, case of six

7. DEDUPLICATE words: "vodka strawberry vodka" → "vodka strawberry"

8. HANDLE accents properly: Keep as-is OR normalize to ASCII (rosé → rose, château → chateau)

9. REMOVE promotional language: offer, deal, discount, buy, shop, limited edition, black friday, special offer

10. REMOVE ABV/proof: 40% ABV, 20% vol, 100 proof

11. REMOVE retailer names: Laithwaites, Waitrose, Greene King Shop, Buy X Shop, merchant names

Examples of MSV-Optimized Transformations:
- "Balvenie 12 Year Old The Sweet Toast of American Oak Single Malt Whisky 700ml" → "Balvenie Oak Whisky" (3 words)
- "Personalised Luxury Grey Goose Vodka Hamper Gift 750ml" → "Grey Goose Vodka" (3 words)
- "Vault City Sour Mixed Case 24x330ml" → "Vault City Sour" (3 words)
- "Chin Chin Vinho Verde 2024 750ml" → "Chin Vinho Verde" (3 words)
- "Urban Rhino Dragon Lime Liqueur 50cl 20% ABV" → "Urban Rhino Liqueur" (3 words)
- "Buy Bonkers Conkers Ale Greene King Shop" → "Bonkers Conkers Ale" (3 words)
- "Lagavulin 16 Year Old Single Malt Whisky" → "Lagavulin 16yr Whisky" (3 words)

Expected Output Format:
{{
  "0": "Brand Product Type",
  "1": "Brand Product Type"
}}

Return ONLY the JSON object. If blocked, use value "BLOCKED"."""

    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 1024},
            safety_settings=safety_settings
        )
        
        if not response.parts or not response.text:
            print(f"  [BATCH {batch_id}] Blocked by safety filters.")
            return {item['id']: "BLOCKED" for item in batch_data}

        # Parse JSON from response
        text = response.text.strip()
        # Clean markdown code blocks if present
        if text.startswith("```"):
            text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
            
        return json.loads(text)

    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg:
            raise QuotaExceededError("API Quota Exceeded")
        print(f"  [BATCH {batch_id}] Error: {str(e)[:100]}")
        return {}


def generate_keywords_batch(
    df: pd.DataFrame,
    product_type: str,
    progress_callback=None,
    batch_size: int = 20, # Increased batch size for speed
    delay_between_batches: float = 0.0, # Not used in batch mode logic below
    model_name: str = "gemma-3-4b-it",
    max_products: int = None
) -> pd.DataFrame:
    """
    Generate keywords using Batch API calls (Fast).
    """
    model = get_gemini_client(model_name)
    if model is None:
        raise ValueError("GOOGLE_API_KEY not set")

    df = df.copy()
    if 'Product Keyword' not in df.columns:
        df['Product Keyword'] = ""

    # Slice dataframe if limit set
    target_df = df if max_products is None else df.head(max_products)
    total_items = len(target_df)
    
    print(f"Starting BATCH keyword generation for {total_items} items (Batch Size: {batch_size})...")

    results_map = {} # index -> keyword

    # Create batches
    indices = target_df.index.tolist()
    chunks = [indices[i:i + batch_size] for i in range(0, len(indices), batch_size)]

    try:
        for i, chunk_indices in enumerate(chunks):
            # Prepare batch payload
            batch_payload = []
            for idx in chunk_indices:
                row = target_df.loc[idx]
                batch_payload.append({
                    "id": str(idx), # Use string ID for JSON compatibility
                    "title": str(row.get('Product Title', '')),
                    "brand": str(row.get('Product Brand', '')),
                    "type": product_type
                })
            
            # Call API
            retry_count = 0
            success = False
            batch_results = {}

            while retry_count < 2:
                try:
                    batch_results = generate_batch_keywords_api(model, batch_payload, i)
                    if batch_results:
                        success = True
                        break
                except QuotaExceededError:
                    raise # Re-raise to top level
                except Exception:
                    pass
                
                retry_count += 1
                time.sleep(2) # Backoff
            
            # Map results back
            for item in batch_payload:
                raw_id = item['id']
                # Get result or fallback
                keyword = batch_results.get(raw_id)
                
                # If parsed JSON misses an ID or failed, fallback to simple generation? 
                # For speed, we mark as "RETRY" or leave empty.
                if keyword:
                    results_map[int(raw_id)] = keyword
                else:
                    results_map[int(raw_id)] = "" # Failed item

            # Progress
            if progress_callback:
                processed_count = (i + 1) * batch_size
                processed_count = min(processed_count, total_items)
                progress_callback(processed_count / total_items, processed_count, total_items)

            # Rate Limit for Batch
            # 30 RPM = 2s per request.
            # We are sending 1 request every batch.
            # Sleep 2s to be universally safe.
            time.sleep(2.0)

    except QuotaExceededError:
        print("CRITICAL: API Quota Exceeded during batch processing.")
    except KeyboardInterrupt:
        print("Processing stopped by user.")
    
    # Apply results
    for idx, keyword in results_map.items():
        df.at[idx, 'Product Keyword'] = keyword

    return df


def classify_other_products_batch(
    df: pd.DataFrame,
    product_type: str,
    progress_callback=None,
    batch_size: int = 20,
    model_name: str = "gemma-3-4b-it"
) -> pd.DataFrame:
    """
    Classify products marked as "Other" using LLM with Excel taxonomy.
    Only processes products where Product Category == "Other".

    Args:
        df: DataFrame with Product Category column
        product_type: Product type (BWS, Pets, Electronics)
        progress_callback: Optional progress callback function
        batch_size: Number of products per API call
        model_name: Gemini model to use

    Returns:
        DataFrame with updated Product Category for "Other" products
    """
    model = get_gemini_client(model_name)
    if model is None:
        print("Warning: GOOGLE_API_KEY not set. Skipping LLM category classification.")
        return df

    df = df.copy()

    # Filter only "Other" products
    other_mask = df['Product Category'] == 'Other'
    other_products = df[other_mask]

    if len(other_products) == 0:
        print("No products with 'Other' category. Skipping LLM classification.")
        return df

    print(f"\nFound {len(other_products)} products with 'Other' category.")
    print(f"Starting LLM classification (Batch Size: {batch_size})...")

    # Load taxonomy
    try:
        taxonomy = get_taxonomy()
        categories_text = format_categories_for_llm(product_type, taxonomy)
    except Exception as e:
        print(f"Error loading taxonomy: {e}. Skipping LLM classification.")
        return df

    results_map = {}  # index -> category

    # Create batches
    indices = other_products.index.tolist()
    chunks = [indices[i:i + batch_size] for i in range(0, len(indices), batch_size)]

    try:
        for i, chunk_indices in enumerate(chunks):
            # Prepare batch payload
            batch_payload = []
            for idx in chunk_indices:
                row = other_products.loc[idx]
                batch_payload.append({
                    "id": str(idx),
                    "title": str(row.get('Product Title', '')),
                    "brand": str(row.get('Product Brand', ''))
                })

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

            try:
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]

                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.1, "max_output_tokens": 1024},
                    safety_settings=safety_settings
                )

                if not response.parts or not response.text:
                    print(f"  [BATCH {i+1}] Blocked by safety filters.")
                    continue

                # Parse JSON from response
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()

                batch_results = json.loads(text)

                # Map results back
                for item in batch_payload:
                    raw_id = item['id']
                    category = batch_results.get(raw_id)
                    if category and category != "Other":
                        # Extract only the leaf category (most specific)
                        leaf_category = extract_leaf_category(category)
                        results_map[int(raw_id)] = leaf_category

            except Exception as e:
                print(f"  [BATCH {i+1}] Error: {str(e)[:100]}")

            # Progress
            if progress_callback:
                processed_count = (i + 1) * batch_size
                processed_count = min(processed_count, len(other_products))
                progress_callback(processed_count / len(other_products), processed_count, len(other_products))

            # Rate limit
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("Classification stopped by user.")

    # Apply results
    improved_count = 0
    for idx, category in results_map.items():
        df.at[idx, 'Product Category'] = category
        improved_count += 1

    print(f"✓ Improved {improved_count} categories from 'Other' using LLM")

    return df


def validate_api_key() -> bool:
    return os.getenv("GOOGLE_API_KEY") is not None


def test_api_connection(model_name: str = "gemma-3-12b-it") -> tuple[bool, str]:
    model = get_gemini_client(model_name)
    if model is None: return False, "No API Key"
    try:
        model.generate_content("Test", generation_config={"max_output_tokens": 5})
        return True, "Connected"
    except Exception as e:
        return False, str(e)

