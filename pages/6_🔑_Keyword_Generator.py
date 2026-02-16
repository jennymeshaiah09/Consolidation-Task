"""
Dedicated Keyword Generator Page
Generates MSV-optimized keywords using Hybrid, RAKE, or LLM methods.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.keyword_preprocessor import (
    extract_keyword_hybrid,
    preprocess_title,
    PRODUCT_TYPE_WORDS
)
from src.rake_keywords import extract_keyword_rake, generate_keywords_rake
from src.llm_keywords import (
    generate_keywords_batch,
    validate_api_key,
    test_api_connection
)
# Import new generator
try:
    from src.keyword_generator import (
        get_gemini_client,
        normalize_title,
        extract_entities,
        generate_candidates,
        score_candidates
    )
    HAS_ADVANCED = True
except ImportError:
    HAS_ADVANCED = False

# Page config
st.set_page_config(
    page_title="Keyword Generator",
    page_icon="🔑",
    layout="wide"
)

st.title("🔑 Keyword Generator")
st.markdown("""
**MSV-Optimized Keyword Extraction**

This tool generates search-friendly keywords (2-4 words) optimized for Monthly Search Volume.
It addresses common issues that cause 0 MSV keywords.
""")

# Sidebar options
st.sidebar.header("⚙️ Settings")

method_options = ["Hybrid (Recommended)", "RAKE", "LLM (API)"]
if HAS_ADVANCED:
    method_options.insert(0, "Advanced (Entity + Template)")

method = st.sidebar.selectbox(
    "Extraction Method",
    method_options,
    help="""
    **Advanced**: Entity Extraction -> Templates -> Scoring (Best for MSV)
    **Hybrid**: Brand + Product Type + Differentiator (Fast, reliable)
    **RAKE**: Statistical keyword extraction (Local)
    **LLM**: Legacy AI extraction
    """
)

max_words = st.sidebar.slider(
    "Max Words per Keyword",
    min_value=2,
    max_value=6,
    value=4,
    help="96% of keywords with MSV are under 7 words. 4 is optimal."
)

# Model selector (only shown for LLM/Advanced method)
if method in ["LLM (API)", "Advanced (Entity + Template)"]:
    st.sidebar.divider()
    st.sidebar.markdown("### 🤖 LLM Settings")
    
    llm_model = st.sidebar.selectbox(
        "Gemini Model",
        ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemma-3-4b-it"],
        index=0
    )
    
    batch_size = st.sidebar.slider(
        "Batch Size",
        min_value=10,
        max_value=50,
        value=20,
        help="Products per API call."
    )
    
    api_delay = st.sidebar.slider(
        "Delay Between Calls (sec)",
        min_value=0.0,
        max_value=2.0,
        value=0.1,  # Fast for Tier 1 users
        step=0.05,
        help="Tier 1: 0.1s is fine. Increase to 0.5-1.0s if seeing errors."
    )
    
    max_products_llm = st.sidebar.number_input(
        "Max Products (0 = All)",
        min_value=0,
        max_value=100000,
        value=0,
        step=1000,
        help="Limit products to process. Useful for testing."
    )
else:
    llm_model = "gemini-2.5-flash-lite"
    batch_size = 20
    api_delay = 0.5
    max_products_llm = 0

st.sidebar.divider()
# ... (rest of sidebar info is fine) ...

# ... (Upload Data Section - Keep as is) ...
# ... (File Loading Logic - Keep as is) ...

# ... (Main Processing Logic) ...
# INSIDE existing file loading block...
# I need to target the "Generate Keywords" button logic specifically.

# Quick test section at the bottom needs update
st.divider()
with st.expander("🧪 Quick Test - Try Single Keywords", expanded=True):
    st.markdown("Test keyword extraction on individual products:")
    
    test_title = st.text_input(
        "Product Title",
        value="Porta 6 Red Wine Case | Mix Any Six & Save"
    )
    test_brand = st.text_input(
        "Product Brand",
        value="Porta 6"
    )
    
    if st.button("Test Extraction"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🧠 Advanced (Entity + Template)")
            if HAS_ADVANCED:
                # Run the pipeline
                client = get_gemini_client(llm_model)
                if client:
                    norm = normalize_title(test_title)
                    st.text(f"Normalized: {norm}")
                    
                    with st.spinner("Extracting..."):
                        entities = extract_entities(client, norm)
                    st.json(entities)
                    
                    candidates = generate_candidates(entities)
                    scores = score_candidates(candidates, entities, norm)
                    
                    st.markdown("**🏆 Top Candidates (Scored):**")
                    score_df = pd.DataFrame(scores, columns=['Score', 'Keyword'])
                    st.dataframe(score_df, hide_index=True)
                else:
                    st.error("API Key missing")
            else:
                st.error("Module not found")

        with col2:
            st.markdown("### 🐢 Legacy Methods")
            hybrid_kw = extract_keyword_hybrid(test_title, test_brand, "", max_words)
            st.markdown(f"**Hybrid:** `{hybrid_kw}`")
            
            rake_kw = extract_keyword_rake(test_title, test_brand, max_words)
            st.markdown(f"**RAKE:** `{rake_kw}`")
            
            cleaned = preprocess_title(test_title, test_brand)
            st.markdown(f"**Preprocessed:** `{cleaned}`")


st.sidebar.divider()
st.sidebar.markdown("### ℹ️ About Methods")
st.sidebar.markdown("""
**Hybrid** 🏆
- Deterministic: Brand + Product Type
- Handles all 11 MSV issues
- No API required
- Best accuracy

**RAKE**
- Statistical scoring
- Fast & local
- May miss product types

**LLM**
- Google Gemini API
- With credits: 2,000 RPM
- ~£0.50 per 55k keywords
""")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Data")
    
    uploaded_file = st.file_uploader(
        "Upload CSV, Excel, or ZIP file",
        type=['csv', 'xlsx', 'xls', 'zip'],
        help="ZIP files containing monthly CSVs are supported. Unique titles will be extracted automatically."
    )

with col2:
    st.subheader("📋 Supported Formats")
    st.markdown("""
    | Format | Description |
    |--------|-------------|
    | `.csv` | Single CSV file |
    | `.xlsx` | Excel file |
    | `.zip` | ZIP with multiple CSVs (unique titles extracted) |
    
    **Required column:** `Title` or `Product Title`
    """)

if uploaded_file:
    # Load file based on type
    try:
        if uploaded_file.name.endswith('.zip'):
            # Handle ZIP file with multiple CSVs
            import zipfile
            from io import StringIO, BytesIO
            
            z = zipfile.ZipFile(BytesIO(uploaded_file.read()))
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            
            if not csv_files:
                st.error("❌ No CSV files found in ZIP")
                st.stop()
            
            st.info(f"📦 Found {len(csv_files)} CSV files in ZIP")
            
            all_dfs = []
            for csv_name in csv_files:
                try:
                    with z.open(csv_name) as f:
                        content = f.read()
                    
                    # Try UTF-16 first (common for Google exports), then fallback
                    try:
                        text = content.decode('utf-16')
                    except:
                        try:
                            text = content.decode('utf-8')
                        except:
                            text = content.decode('latin-1')
                    
                    # Skip metadata lines and find header row
                    lines = text.split('\n')
                    header_idx = 0
                    for i, line in enumerate(lines):
                        if ('Title' in line or 'title' in line) and '\t' in line:
                            header_idx = i
                            break
                    
                    # Parse from header row
                    data_text = '\n'.join(lines[header_idx:])
                    temp_df = pd.read_csv(StringIO(data_text), sep='\t', on_bad_lines='skip')
                    all_dfs.append(temp_df)
                except Exception as e:
                    st.warning(f"⚠️ Skipped {csv_name}: {str(e)[:50]}")
            
            if not all_dfs:
                st.error("❌ Could not parse any CSV files from ZIP")
                st.stop()
            
            # Combine all dataframes
            df = pd.concat(all_dfs, ignore_index=True)
            st.success(f"✅ Combined {len(all_dfs)} files, {len(df)} total rows")
            
            # Rename columns to standard names
            col_mapping = {}
            for col in df.columns:
                if col.lower() == 'title':
                    col_mapping[col] = 'Product Title'
                elif col.lower() == 'brand':
                    col_mapping[col] = 'Product Brand'
            df = df.rename(columns=col_mapping)
            
            # Get unique titles with their brands
            if 'Product Title' in df.columns:
                if 'Product Brand' in df.columns:
                    df = df.drop_duplicates(subset=['Product Title', 'Product Brand'])
                else:
                    df = df.drop_duplicates(subset=['Product Title'])
                st.info(f"📊 {len(df)} unique products after deduplication")
        
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ Loaded {len(df)} products")
        
        # Check for required columns - accept both 'Title' and 'Product Title'
        if 'Product Title' not in df.columns and 'Title' in df.columns:
            df = df.rename(columns={'Title': 'Product Title', 'Brand': 'Product Brand'})
        
        if 'Product Title' not in df.columns:
            st.error("❌ Missing required column: 'Product Title' or 'Title'")
            st.stop()
        
        # Show sample of input data
        with st.expander("📊 Preview Input Data", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
        
        # Check for brand column
        has_brand = 'Product Brand' in df.columns
        has_merchant = 'Merchant Name' in df.columns
        
        if not has_brand:
            st.warning("⚠️ No 'Product Brand' column found. Keywords may be less accurate.")

        # --- Keyword cache check ---
        # Persists keywords across refreshes so the LLM doesn't need to re-run
        # while waiting for MSV data from another source.
        CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'keyword_cache.csv')

        if 'keyword_results' not in st.session_state and os.path.exists(CACHE_FILE):
            try:
                cache_df = pd.read_csv(CACHE_FILE)
                if 'Product Title' in cache_df.columns and 'Product Keyword' in cache_df.columns:
                    merged = df.merge(
                        cache_df[['Product Title', 'Product Keyword']].drop_duplicates('Product Title'),
                        on='Product Title',
                        how='left'
                    )
                    cached_count = int(merged['Product Keyword'].notna().sum())
                    total_count = len(df)

                    if cached_count > 0:
                        st.info(
                            f"📂 **{cached_count}/{total_count}** products have cached keywords "
                            f"from a previous run. Load them to skip LLM generation."
                        )
                        cache_col1, cache_col2 = st.columns(2)
                        with cache_col1:
                            if st.button("✅ Load Cached Keywords", type="primary", use_container_width=True):
                                merged['Product Keyword'] = merged['Product Keyword'].fillna('')
                                st.session_state['keyword_results'] = merged
                        with cache_col2:
                            if st.button("🗑️ Clear Cache", type="secondary", use_container_width=True):
                                os.remove(CACHE_FILE)
                                st.rerun()
            except Exception:
                pass  # Corrupted or incompatible cache — ignore

        # --- Trial Run (LLM only) ---
        if method == "LLM (API)":
            st.divider()
            st.markdown("### 🧪 Trial Run")
            st.markdown("Test the selected model on the first 10 records before running the full batch. Useful to confirm the model is producing keywords correctly.")

            trial_col1, trial_col2 = st.columns([1, 2])

            with trial_col1:
                trial_clicked = st.button("▶️ Trial (10 records)", type="secondary", use_container_width=True)

            with trial_col2:
                if 'trial_results' in st.session_state:
                    trial_df = st.session_state['trial_results']
                    filled = trial_df['Product Keyword'].astype(str).str.strip().ne('').sum()
                    st.markdown(f"Last trial: **{filled}/10** keywords generated")
                else:
                    st.markdown("No trial run yet.")

            if trial_clicked:
                if not validate_api_key():
                    st.error("❌ GOOGLE_API_KEY not set.")
                    st.stop()

                import google.generativeai as genai
                from src import get_google_api_key

                # --- Step 1: Single direct diagnostic call (shows raw response/error) ---
                st.markdown("**Step 1 — Single-call diagnostic**")
                sample_title = str(df.iloc[0].get('Product Title', ''))[:100]
                _raw_brand = df.iloc[0].get('Product Brand', '') if has_brand else ''
                sample_brand = str(_raw_brand)[:50] if pd.notna(_raw_brand) and str(_raw_brand).strip() else 'Unknown'
                st.markdown(f"Testing with: `{sample_title}` / `{sample_brand}`")

                brand_line = f"\nBrand: {sample_brand}" if sample_brand != 'Unknown' else ""
                diag_prompt = (
                    "You are an ecommerce SEO keyword specialist.\n\n"

                    "Output the search phrase a real customer would type into Google to find this exact product. "
                    "Focus on product-identifying words that match real search behaviour.\n\n"

                    "PRIORITY ORDER (most important first):\n"
                    "1. Exact product name / cuvee / label / model (strongest signal)\n"
                    "2. Product name + vintage year if the year identifies the product (especially for wine)\n"
                    "3. Brand + product name\n"
                    "4. Brand + product type\n"
                    "5. Category fallback only if no product entity exists\n\n"

                    "Title: {sample_title}{brand_line}\n\n"

                    "KEEP when they identify the product:\n"
                    "- Product name, cuvee, label, collection name\n"
                    "- Vintage year for wine\n"
                    "- Numbers that are part of brand names (example: Porta 6)\n"
                    "- Collection lines (example: Chosen by Majestic)\n"
                    "- Core product type words: Champagne, Whisky, Wine, Rose, Lager, Gin, Vodka, Rum, Tequila, "
                    "Liqueur, Cider, Prosecco, Bourbon, Brandy, Cognac, Scotch, Sake, Whiskey, Beer, Ale, Stout, "
                    "Port, Sherry, Vermouth, Absinthe, Mead, Perry\n\n"

                    "DROP only if NOT product-identifying:\n"
                    "- Sizes or volumes: ml, cl, L, oz, 700ml, 750ml, 1L, 330ml\n"
                    "- Quantities: 6 pack, 12 pack, 24x330ml\n"
                    "- ABV, proof, vol\n"
                    "- Promotional wording: gift, hamper, personalised, offer, deal, sale\n"
                    "- Multipack wording: case, set, bundle, mixed selection\n"
                    "- Retailers: Laithwaites, Waitrose, Tesco, Amazon, Majestic\n"
                    "- Generic filler only when not part of product name: premium, classic, special, limited, reserve\n\n"

                    "SPECIAL RULES:\n"
                    "- For wine: KEEP vintage year and product label names\n"
                    "- Do NOT collapse specific products into generic terms like 'wine'\n"
                    "- If product name uniquely identifies the product, prefer it over generic category terms\n"
                    "- Convert accents to plain text: rosé → rose, moët → moet, château → chateau\n\n"

                    "OUTPUT RULES:\n"
                    "- 2–4 words preferred\n"
                    "- lowercase\n"
                    "- no quotes\n"
                    "- no explanation\n"
                    "- return only the keyword\n\n"

                    "EXAMPLES:\n"
                    "\"Chateau Batailley 2016 Pauillac Bordeaux\" → chateau batailley 2016\n"
                    "\"Porta 6 Red Wine Case\" → porta 6 red wine\n"
                    "\"Chosen by Majestic Primitivo 2022\" → primitivo 2022\n"
                    "\"Whispering Angel Rose 2023\" → whispering angel rose"
                )

                try:
                    genai.configure(api_key=get_google_api_key())
                    diag_model = genai.GenerativeModel(llm_model)

                    # SDK 0.8.4 has no thinking_config — 2.5 models burn
                    # thinking tokens out of max_output_tokens, so 2048 is required.
                    gen_cfg = genai.GenerationConfig(
                        temperature=0.0,
                        max_output_tokens=2048,
                    )

                    diag_response = diag_model.generate_content(diag_prompt, generation_config=gen_cfg)

                    # Show everything we got back
                    st.markdown("**Raw response fields:**")
                    diag_info = {
                        "has .text": hasattr(diag_response, 'text'),
                        "has .parts": hasattr(diag_response, 'parts') and bool(diag_response.parts),
                        "has .candidates": hasattr(diag_response, 'candidates') and bool(diag_response.candidates),
                    }
                    # Safely get .text
                    try:
                        diag_info[".text value"] = repr(diag_response.text)
                    except Exception as tex:
                        diag_info[".text raised"] = str(tex)
                    # Safely get .parts[0].text
                    try:
                        if diag_response.parts:
                            diag_info[".parts[0].text"] = repr(diag_response.parts[0].text)
                    except Exception as pex:
                        diag_info[".parts[0] raised"] = str(pex)
                    # Candidate finish reason
                    try:
                        if diag_response.candidates:
                            diag_info["finish_reason"] = str(diag_response.candidates[0].finish_reason)
                    except Exception:
                        pass

                    st.json(diag_info)

                    # Check if we actually got a keyword
                    diag_keyword = None
                    try:
                        if diag_response.text and diag_response.text.strip():
                            diag_keyword = diag_response.text.strip().strip('"').strip("'")
                    except Exception:
                        pass

                    if diag_keyword:
                        st.success(f"Diagnostic OK — keyword: **{diag_keyword}**")
                    else:
                        st.error("Diagnostic failed — no keyword extracted. Check the raw fields above.")
                        st.stop()

                except Exception as diag_err:
                    err_str = str(diag_err)
                    if "429" in err_str or "quota" in err_str.lower():
                        st.error(f"**{llm_model}** has no quota on your API key.")
                        st.warning("Switch to **gemini-2.0-flash** or **gemma-3-4b-it** in the sidebar — those have free-tier quota.")
                    else:
                        st.error(f"Diagnostic exception: {diag_err}")
                    st.stop()

                # --- Step 2: Run batch of 10 using the parallel machinery ---
                st.divider()
                st.markdown("**Step 2 — Batch of 10 records**")

                with st.status(f"Running 10 records with **{llm_model}**...", expanded=True) as trial_status:
                    trial_df = df.head(10).copy()
                    trial_df['Product Keyword'] = ""

                    try:
                        trial_df = generate_keywords_batch(
                            trial_df,
                            product_type="General",
                            batch_size=10,
                            delay_between_batches=0.0,
                            model_name=llm_model,
                            max_products=10
                        )
                        filled = trial_df['Product Keyword'].astype(str).str.strip().ne('').sum()
                        blank = 10 - filled

                        if blank == 0:
                            trial_status.update(label=f"Trial complete — {filled}/10 keywords generated", state="complete")
                        else:
                            trial_status.update(label=f"Trial complete — {blank}/10 blanks detected", state="error")

                        st.session_state['trial_results'] = trial_df

                        display_cols = [c for c in ['Product Title', 'Product Brand', 'Product Keyword'] if c in trial_df.columns]
                        st.dataframe(trial_df[display_cols], use_container_width=True, hide_index=True)

                        # Surface any errors collected from the worker threads
                        api_errors = trial_df.attrs.get('errors', [])
                        if api_errors:
                            with st.expander(f"⚠️ API errors ({len(api_errors)})", expanded=True):
                                for err in api_errors:
                                    st.code(err)

                        if blank > 0:
                            st.warning(f"⚠️ {blank}/10 keywords are blank. Check the model or API key before running the full batch.")

                    except Exception as e:
                        trial_status.update(label="Trial failed", state="error")
                        st.error(f"❌ Trial Error: {str(e)}")

        # Generate button
        st.divider()

        if st.button("🚀 Generate Keywords", type="primary", use_container_width=True):
            
            # Create result dataframe
            result_df = df.copy()
            result_df['Product Keyword'] = ""
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total = len(result_df)
            
            if method == "Hybrid (Recommended)":
                # Hybrid extraction
                status_text.text("Generating keywords with Hybrid method...")
                
                for count, (idx, row) in enumerate(result_df.iterrows()):
                    title = str(row.get('Product Title', ''))
                    brand = str(row.get('Product Brand', '')) if has_brand else ''
                    merchant = str(row.get('Merchant Name', '')) if has_merchant else ''
                    
                    keyword = extract_keyword_hybrid(title, brand, merchant, max_words)
                    result_df.at[idx, 'Product Keyword'] = keyword
                    
                    # Update progress
                    if count % 50 == 0:
                        progress = min((count + 1) / total, 1.0)
                        progress_bar.progress(progress)
                        status_text.text(f"Processing {count + 1}/{total}...")
                
                progress_bar.progress(1.0)
                status_text.text(f"✅ Generated {total} keywords")
                
            elif method == "RAKE":
                # RAKE extraction
                status_text.text("Generating keywords with RAKE...")
                
                for count, (idx, row) in enumerate(result_df.iterrows()):
                    title = str(row.get('Product Title', ''))
                    brand = str(row.get('Product Brand', '')) if has_brand else ''
                    
                    keyword = extract_keyword_rake(title, brand, max_words)
                    result_df.at[idx, 'Product Keyword'] = keyword
                    
                    if count % 50 == 0:
                        progress = min((count + 1) / total, 1.0)
                        progress_bar.progress(progress)
                        status_text.text(f"Processing {count + 1}/{total}...")
                
                progress_bar.progress(1.0)
                status_text.text(f"✅ Generated {total} keywords")
                
            elif method == "Advanced (Entity + Template)":
                # Advanced extraction
                if not validate_api_key():
                    st.error("❌ GOOGLE_API_KEY not set.")
                    st.stop()
                
                client = get_gemini_client(llm_model)
                if not client:
                    st.error("❌ Failed to initialize Gemini client.")
                    st.stop()
                
                status_text.text(f"Generating with Advanced Strategy ({llm_model})...")
                
                # Check for limit
                if max_products_llm > 0:
                    df_to_process = result_df.head(max_products_llm).copy()
                else:
                    df_to_process = result_df.copy()
                
                try:
                    from src.keyword_generator import generate_keywords_advanced_parallel
                    
                    def update_advanced_progress(progress, current, total):
                        progress_bar.progress(min(progress, 1.0))
                        status_text.text(f"Processing... {current}/{total} products")

                    df_processed = generate_keywords_advanced_parallel(
                        df_to_process,
                        progress_callback=update_advanced_progress,
                        model_name=llm_model,
                        max_workers=batch_size, # Reuse batch slider as worker count
                        api_delay=api_delay
                    )
                    
                    # Update the main DataFrame
                    if max_products_llm > 0:
                        # Update only the processed rows in the main df
                        result_df.update(df_processed)
                    else:
                        result_df = df_processed

                    progress_bar.progress(1.0)

                    # Check how many keywords were generated
                    filled = result_df['Product Keyword'].astype(str).str.strip().ne('').sum()
                    blank = len(result_df) - filled

                    if blank == 0:
                        status_text.text(f"✅ Generated {filled} keywords with Advanced Strategy")
                    else:
                        status_text.text(f"⚠️ Generated {filled}/{len(result_df)} keywords ({blank} blanks)")

                    # Surface any errors collected from the worker threads
                    api_errors = df_processed.attrs.get('errors', [])
                    if api_errors:
                        with st.expander(f"⚠️ API/Extraction errors ({len(api_errors)})", expanded=True):
                            for err in api_errors[:10]:
                                st.warning(err)
                            if len(api_errors) > 10:
                                st.info(f"... and {len(api_errors) - 10} more errors")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.stop()

            else:
                # LLM extraction
                if not validate_api_key():
                    st.error("❌ GOOGLE_API_KEY not set. Please add it to your .env file.")
                    st.stop()
                
                status_text.text(f"Connecting to Gemini API ({llm_model})...")
                
                success, msg = test_api_connection(llm_model)
                if not success:
                    st.error(f"❌ API Connection Failed: {msg}")
                    st.stop()
                
                max_prods = None if max_products_llm == 0 else max_products_llm
                st.info(f"🚀 Model: **{llm_model}** | Batch: **{batch_size}** | Delay: **{api_delay}s** | Products: **{max_prods or 'All'}**")
                
                def update_progress(progress, current, total):
                    progress_bar.progress(min(progress, 1.0))
                    status_text.text(f"Processing... {current}/{total} products")
                
                try:
                    result_df = generate_keywords_batch(
                        result_df,
                        product_type="General",
                        progress_callback=update_progress,
                        batch_size=batch_size,
                        delay_between_batches=api_delay,
                        model_name=llm_model,
                        max_products=max_prods,
                        max_workers=batch_size  # Use batch_size as proxy for workers or limit to 5-10
                    )
                    status_text.text(f"✅ Generated keywords with {llm_model}")
                except Exception as e:
                    st.error(f"❌ LLM Error: {str(e)}")
                    st.stop()
            
            # Store results in session
            st.session_state['keyword_results'] = result_df

            # Auto-save to cache so keywords survive page refreshes
            try:
                result_df.to_csv(CACHE_FILE, index=False)
            except Exception:
                pass

            st.success("✅ Keywords generated and cached successfully!")
    
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")

# Display results if available
if 'keyword_results' in st.session_state:
    result_df = st.session_state['keyword_results']
    
    st.divider()
    st.subheader("📊 Results")
    
    # Stats
    col1, col2, col3 = st.columns(3)
    
    # Calculate stats
    keywords = result_df['Product Keyword'].dropna()
    word_counts = keywords.apply(lambda x: len(str(x).split()) if x else 0)
    
    with col1:
        st.metric("Total Keywords", len(keywords))
    
    with col2:
        avg_words = word_counts.mean()
        st.metric("Avg Words/Keyword", f"{avg_words:.1f}")
    
    with col3:
        under_4 = (word_counts <= 4).sum()
        pct = (under_4 / len(word_counts)) * 100 if len(word_counts) > 0 else 0
        st.metric("≤4 Words", f"{pct:.1f}%")
    
    # Preview table
    with st.expander("📋 Preview Generated Keywords", expanded=True):
        # Show relevant columns only
        display_cols = ['Product Title', 'Product Brand', 'Product Keyword'] if 'Product Brand' in result_df.columns else ['Product Title', 'Product Keyword']
        display_cols = [c for c in display_cols if c in result_df.columns]
        
        st.dataframe(
            result_df[display_cols].head(50),
            use_container_width=True,
            height=400
        )
    
    # Download
    st.divider()
    
    # Prepare download
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False, sheet_name='Keywords')
    output.seek(0)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.download_button(
            label="📥 Download Excel",
            data=output,
            file_name="generated_keywords.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        csv_data = result_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="generated_keywords.csv",
            mime="text/csv",
            use_container_width=True
        )


