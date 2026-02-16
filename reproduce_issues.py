
import sys
import os
import pandas as pd

# Add source to path for imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.keyword_generator import generate_candidates, score_candidates, clean_keyword, normalize_title

def test_scenario(name, title, entities, expected_tokens=None, unexpected_tokens=None):
    print(f"\n--- {name} ---")
    print(f"Title: {title}")
    print(f"Entities: {entities}")
    
    # 1. Generate
    candidates = generate_candidates(entities)
    print(f"Candidates: {candidates}")
    
    # 2. Score
    norm_title = normalize_title(title)
    scored = score_candidates(candidates, entities, norm_title)
    print(f"Scored: {scored}")
    
    if not scored:
        print("NO CANDIDATES GENERATED")
        return

    top_keyword = scored[0][1]
    cleaned = clean_keyword(top_keyword)
    print(f"Top Cleaned: {cleaned}")
    
    if expected_tokens:
        for token in expected_tokens:
            if token.lower() not in cleaned.lower():
                print(f"FAIL: Expected token '{token}' not found in '{cleaned}'")
            else:
                print(f"PASS: Found '{token}'")
                
    if unexpected_tokens:
        for token in unexpected_tokens:
            if token.lower() in cleaned.lower():
                print(f"FAIL: Unexpected token '{token}' found in '{cleaned}'")
            else:
                print(f"PASS: '{token}' not found")

# Scenario 1: CTA/Strong Entity
# "Chateau Batailley 2016"
test_scenario(
    "Strong Entity - Chateau Batailley",
    "Chateau Batailley 2016",
    {
        'brand': 'Chateau Batailley',
        'product_name': 'Batailley', # Or maybe the brand is Chateau Batailley and product is implied? 
        # Let's assume extraction works as intended
        'vintage': '2016',
        'region': 'Pauillac',
        'varietal': 'Red Blend',
        'pack_format': '',
        'collection': ''
    },
    expected_tokens=['Batailley', '2016']
)

# Scenario 2: Generic
# "Barossa Shiraz 2022"
test_scenario(
    "Generic - Barossa Shiraz",
    "Barossa Shiraz 2022",
    {
        'brand': '',
        'product_name': '',
        'vintage': '2022',
        'region': 'Barossa',
        'varietal': 'Shiraz',
        'pack_format': '',
        'collection': ''
    },
    expected_tokens=['Barossa', 'Shiraz', '2022']
)

# Scenario 3: Pack Format & Critical Token
# "Porta 6 6 Bottle Case"
test_scenario(
    "Pack & Critical Token - Porta 6",
    "Porta 6 6 Bottle Case",
    {
        'brand': 'Porta 6',
        'product_name': 'Red Wine', # Inferred
        'vintage': '',
        'region': 'Lisbon',
        'varietal': '',
        'pack_format': '6 Bottle Case',
        'collection': ''
    },
    expected_tokens=['Porta 6', 'Case'], # Should have 6 (brand) and Case
    unexpected_tokens=['Porta Case'] # Should not lose the 6
)

# Scenario 4: Capitalization
# "Jack Daniel's"
test_scenario(
    "Capitalization - Jack Daniel's",
    "Jack Daniel's Tennessee Whiskey",
    {
        'brand': "Jack Daniel's",
        'product_name': 'Tennessee Whiskey',
        'vintage': '',
        'region': '',
        'varietal': '',
        'pack_format': '',
        'collection': ''
    },
    expected_tokens=["Jack Daniel's"]
)
