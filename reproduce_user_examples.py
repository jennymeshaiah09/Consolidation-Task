
import sys
import os
import pandas as pd

# Add source to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.keyword_generator import generate_candidates, score_candidates, clean_keyword, normalize_title

def test_user_example(title, entities, description):
    print(f"\n=== {description} ===")
    print(f"Original Title: {title}")
    print(f"Entities: {entities}")
    
    candidates = generate_candidates(entities)
    norm_title = normalize_title(title)
    scored = score_candidates(candidates, entities, norm_title)
    
    print("Top 3 Scored Candidates:")
    for score, text in scored[:3]:
        print(f"  {score}: {text}")

    if scored:
        top_keyword = clean_keyword(scored[0][1])
        print(f"Final Keyword: {top_keyword}")
    else:
        print("Final Keyword: (None)")

# Example 0: Majestic La Marée Bleue 2024
# Issue: Generated "Majestic La Maree Bleue", Wanted "la maree bleue"
test_user_example(
    "Majestic La Marée Bleue 2024",
    {
        'brand': 'Majestic',
        'product_name': 'La Marée Bleue',
        'vintage': '2024',
        'region': '',
        'varietal': '',
        'pack_format': '',
        'collection': ''
    },
    "Example 0: Majestic Brand Removal"
)

# Example 1: Chosen by Majestic Primitivo 2022/24
# Issue: Generated "Majestic Primitivo", Wanted "primitivo 2022"
test_user_example(
    "Chosen by Majestic Primitivo 2022/24",
    {
        'brand': 'Majestic',   # "Chosen by" likely stripped or put in collection
        'product_name': 'Primitivo', # Primitivo might be product name if no other unique name
        'vintage': '2022',
        'region': '',
        'varietal': 'Primitivo',
        'pack_format': '',
        'collection': 'Chosen by Majestic'
    },
    "Example 1: Chosen by Majestic + Primitivo"
)

# Example 2: Majestic Château Batailley 2016/17
# Issue: Generated "Chateau Batailley Majestic", Wanted "chateau batailley 2016"
test_user_example(
    "Majestic Château Batailley 2016/17",
    {
        'brand': 'Chateau Batailley', # Or Majestic? Likely Chateau Batailley is brand, Majestic is collection or ignored
        # User screenshot says "Majestic Château Batailley 2016/17"
        # If Logic sees "Majestic" as brand, it might score it high.
        # But here clearly Chateau Batailley is the real brand.
        # Let's assume the LLM might be confused or extracts Majestic as Collection.
        'brand': 'Chateau Batailley',
        'product_name': '',
        'vintage': '2016',
        'region': 'Pauillac',
        'varietal': '',
        'pack_format': '',
        'collection': 'Majestic'
    },
    "Example 2: Majestic as Collection/Prefix"
)

# Example 3: Porta 6 Red Wine Case
# Issue: Generated "Porta 6 Red Wine Case", Wanted "porta 6 red wine" 
# (Actually user screenshot shows "porta 6 red wine" as GREEN.
# Wait, user screenshot Green V0 says "Porta 6 Red Wine Case", wait V2 is Green.
# V2 says "porta 6 red wine" (1900 MSV).
# User generated: "Porta 6 Red Wine Case". 
# So wants to drop "Case"?
test_user_example(
    "Porta 6 Red Wine Case | Mix Any Six & Save",
    {
        'brand': 'Porta 6',
        'product_name': 'Red Wine',
        'vintage': '',
        'region': 'Lisbon',
        'varietal': '',
        'pack_format': 'Case',
        'collection': ''
    },
    "Example 3: Porta 6 Case"
)
