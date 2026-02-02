"""
Keyword Generator Module
Auto-generates CATEGORY_KEYWORDS from Excel taxonomy file.
"""

import pandas as pd
import re
from typing import Dict, List, Set
from pathlib import Path


def extract_keywords_from_category(category_name: str) -> List[str]:
    """
    Extract keywords from a category name.
    For multi-word categories, prioritizes full phrases over individual words.

    Args:
        category_name: Category name (e.g., "Red Wine", "Bluetooth Speakers")

    Returns:
        List of keywords extracted from the category name
    """
    if pd.isna(category_name):
        return []

    # Convert to lowercase
    name = str(category_name).lower()

    # Remove special characters, keep alphanumeric and spaces
    name = re.sub(r'[^a-z0-9\s&-]', '', name)

    keywords = []
    words = name.split()

    # Always add full category name
    keywords.append(name.strip())

    # For multi-word categories (e.g., "Dark Rum", "Red Wine"),
    # ONLY add individual words if they're distinctive (not common)
    # Common words that are too generic to use alone:
    generic_words = {
        # Base beverage/alcohol categories
        'rum', 'wine', 'beer', 'whisky', 'whiskey', 'vodka', 'gin', 'tequila',
        'brandy', 'cognac', 'liqueur', 'spirits', 'champagne', 'cider',
        # Base product categories (too broad)
        'food', 'supplies', 'accessories', 'toys', 'furniture', 'clothing',
        'camera', 'lenses', 'bag', 'bags', 'bottle', 'bottles',
        # Pet-related generic words (cause Baby Clothing to match all baby products)
        'baby', 'dog', 'cat', 'pet', 'kitten', 'puppy', 'infant', 'toddler',
        # Generic descriptive adjectives
        'premium', 'classic', 'special', 'original', 'traditional', 'standard',
        'basic', 'regular', 'flavoured', 'mixed', 'dry', 'wet', 'fresh',
        'frozen', 'canned', 'bottled', 'organic', 'natural', 'adult',
        # Geographic/nationality descriptors (too generic alone)
        'american', 'european', 'asian', 'french', 'italian', 'spanish', 'german',
        'irish', 'scottish', 'english', 'japanese', 'chinese', 'mexican',
        # Brand names that appear in multiple categories (handle separately)
        'samsung', 'sony', 'lg', 'apple', 'panasonic', 'philips',
        # Size/quantity words
        'small', 'medium', 'large', 'extra', 'pack', 'set', 'kit',
        # Common words
        'and', 'for', 'the', 'with', '&', 'new', 'pro', 'plus', 'max', 'ultra'
    }

    if len(words) > 1:
        # For multi-word: Add bigrams and distinctive words only
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            keywords.append(bigram)

        # Add individual words only if they're NOT generic
        for word in words:
            if len(word) > 3 and word not in generic_words:
                keywords.append(word)
    else:
        # For single-word: Add the word even if generic (it's the only identifier)
        if len(words[0]) > 2:
            keywords.append(words[0])

    return list(set(keywords))  # Remove duplicates


def generate_category_keywords_from_excel(
    excel_path: str = "Categories & subs.xlsx"
) -> Dict[str, Dict[str, List[str]]]:
    """
    Generate CATEGORY_KEYWORDS dictionary from Excel taxonomy file.

    Args:
        excel_path: Path to Excel taxonomy file

    Returns:
        Dictionary mapping product type to categories with keywords
        Format: {product_type: {category_full_name: [keywords]}}
    """
    project_root = Path(__file__).parent.parent
    full_path = project_root / excel_path

    if not full_path.exists():
        raise FileNotFoundError(f"Excel file not found: {full_path}")

    xl = pd.ExcelFile(full_path)
    category_keywords = {}

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet_name)

        # Map sheet name to product type
        # Use sheet name as product type (clean up special characters)
        product_type = sheet_name.strip()

        sheet_categories = {}

        # Process each row to build category hierarchy
        # Create separate entries for each level to enable cascading matching
        for _, row in df.iterrows():
            # Get all levels
            level1 = row.get('Level 1') or row.get('Main Category')
            level2 = row.get('Level 2') or row.get('Sub Category')
            level3 = row.get('Level 3') or row.get('Additional Category 1')

            # Skip if no valid data
            if pd.isna(level1):
                continue

            level1_str = str(level1).strip() if pd.notna(level1) else None
            level2_str = str(level2).strip() if pd.notna(level2) else None
            level3_str = str(level3).strip() if pd.notna(level3) else None

            # Add Level 3 entry (most specific) if available
            if level3_str:
                category_l3 = f"{level1_str} > {level2_str} > {level3_str}"
                keywords_l3 = extract_keywords_from_category(level3_str)
                if category_l3 not in sheet_categories:
                    sheet_categories[category_l3] = list(set(keywords_l3))
                else:
                    existing = set(sheet_categories[category_l3])
                    existing.update(keywords_l3)
                    sheet_categories[category_l3] = list(existing)

            # Add Level 2 entry if available
            if level2_str:
                category_l2 = f"{level1_str} > {level2_str}"
                keywords_l2 = extract_keywords_from_category(level2_str)
                if category_l2 not in sheet_categories:
                    sheet_categories[category_l2] = list(set(keywords_l2))
                else:
                    existing = set(sheet_categories[category_l2])
                    existing.update(keywords_l2)
                    sheet_categories[category_l2] = list(existing)

            # Add Level 1 entry (least specific)
            if level1_str:
                category_l1 = level1_str
                keywords_l1 = extract_keywords_from_category(level1_str)
                if category_l1 not in sheet_categories:
                    sheet_categories[category_l1] = list(set(keywords_l1))
                else:
                    existing = set(sheet_categories[category_l1])
                    existing.update(keywords_l1)
                    sheet_categories[category_l1] = list(existing)

        # Enhance keywords for specific categories with common brand/product names
        # ===================================================================
        # ELECTRONICS
        # ===================================================================
        if product_type == "Electronics":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Smartphones - Brand keywords (with model numbers to distinguish from TVs)
                if "Smartphones" in cat_name:
                    existing.update(['iphone', 'galaxy s', 'galaxy z', 'galaxy a', 'galaxy s25',
                                     'galaxy s24', 'galaxy s23', 'samsung galaxy', 'pixel', 'pixel 9',
                                     'oneplus', 'xiaomi', 'oppo', 'vivo', 'realme', 'nokia', 'motorola',
                                     'smartphone', 'smartphones', 'mobile phone', '5g phone'])

                # Gaming Consoles - Brand/model keywords
                elif "Video Game Consoles" in cat_name or "Home Consoles" in cat_name:
                    existing.update(['playstation', 'xbox', 'nintendo', 'switch',
                                     'ps4', 'ps5', 'ps6'])

                # Gaming Controllers - Product type keywords
                elif "Gaming Controllers" in cat_name or "Gamepads" in cat_name:
                    existing.update(['controller', 'controllers', 'gamepad', 'gamepads',
                                     'joystick', 'joysticks', 'dualsense', 'dualshock'])

                # Phone Accessories - Singular/plural variants
                elif "Phone Cases" in cat_name:
                    existing.update(['case', 'cases', 'cover', 'covers', 'phone case'])
                elif "Chargers & Cables" in cat_name:
                    existing.update(['charger', 'chargers', 'cable', 'cables', 'usb-c cable'])
                elif "Screen Protectors" in cat_name:
                    existing.update(['protector', 'protectors', 'screen protector', 'tempered glass'])

                # TVs - NO brand keywords (samsung removed to avoid phone conflicts)
                elif "Smart TVs" in cat_name or "Televisions" in cat_name:
                    existing.update(['smart tv', 'television', 'tv', 'qled', 'oled', 'led tv',
                                     '55 inch', '65 inch', '75 inch', 'inch tv'])

                # Laptops - Brand keywords
                elif "Laptops" in cat_name:
                    existing.update(['macbook', 'thinkpad', 'dell', 'hp', 'asus', 'lenovo'])

                # Tablets - Brand/model keywords
                elif "Tablets" in cat_name:
                    existing.update(['ipad', 'galaxy tab', 'surface'])

                # Cameras - Brand keywords (main product, not accessories)
                elif cat_name == "Cameras" or "DSLR" in cat_name or "Mirrorless" in cat_name:
                    existing.update(['canon', 'nikon', 'sony', 'fujifilm', 'panasonic'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # PETS
        # ===================================================================
        elif product_type == "Pets":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Dog Food - Brand keywords + product types
                if "Dog Food" in cat_name:
                    existing.update(['pedigree', 'purina', 'royal canin', 'hills',
                                     'kibble', 'dry food', 'wet food', 'puppy', 'adult dog'])

                # Cat Food - Brand keywords + product types
                elif "Cat Food" in cat_name:
                    existing.update(['whiskas', 'fancy feast', 'felix', 'purina',
                                     'kitten', 'adult cat', 'wet food', 'dry food'])

                # Dog Toys - Product types
                elif "Dog Toys" in cat_name:
                    existing.update(['kong', 'chew toy', 'ball', 'rope toy', 'plush toy'])

                # Cat Toys - Product types
                elif "Cat Toys" in cat_name:
                    existing.update(['feather', 'mouse toy', 'laser', 'catnip'])

                # Cat Scratching Posts / Furniture
                elif "Cat Furniture" in cat_name or "Scratching" in cat_name or "Cat Tree" in cat_name:
                    existing.update(['scratching post', 'cat tree', 'cat tower', 'scratch post',
                                     'climbing', 'sisal', 'cat condo'])

                # Aquarium/Fish - Product identifiers
                elif "Fish" in cat_name or "Aquarium" in cat_name:
                    existing.update(['tank', 'aqua one', 'filter', 'heater', 'pump'])

                # Dog Collars & Leashes
                elif "Collars" in cat_name or "Leashes" in cat_name:
                    existing.update(['collar', 'leash', 'lead', 'harness'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # ALCOHOLIC BEVERAGES
        # ===================================================================
        elif product_type == "Alcoholic Beverages":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Beer brands and types
                if "Lager" in cat_name:
                    existing.update(['heineken', 'corona', 'budweiser', 'carlsberg', 'stella'])
                elif "IPA" in cat_name or "Pale Ale" in cat_name:
                    existing.update(['ipa', 'pale ale', 'xpa', 'hop'])
                elif "Ale" in cat_name:
                    existing.update(['ale'])

                # Wine varieties
                elif "Red Wine" in cat_name:
                    existing.update(['shiraz', 'cabernet', 'merlot', 'pinot noir'])
                elif "White Wine" in cat_name:
                    existing.update(['chardonnay', 'sauvignon blanc', 'riesling', 'pinot gris'])

                # Spirits - Bourbon (specific to avoid whisky confusion)
                elif "Bourbon" in cat_name:
                    existing.update(['bourbon', 'jim beam', 'jack daniels', 'makers mark', 'wild turkey'])

                # Spirits brands
                elif "Vodka" in cat_name:
                    existing.update(['smirnoff', 'absolut', 'grey goose'])
                elif "Whisky" in cat_name:
                    existing.update(['johnnie walker', 'jameson', 'chivas', 'glenfiddich'])
                elif "Rum" in cat_name:
                    existing.update(['bacardi', 'captain morgan', 'malibu'])
                elif "Gin" in cat_name:
                    existing.update(['tanqueray', 'bombay sapphire', 'hendricks'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # TOYS
        # ===================================================================
        elif product_type == "Toys":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Building toys
                if "Building" in cat_name or "LEGO" in cat_name:
                    existing.update(['lego', 'building blocks', 'construction', 'bricks'])

                # Action figures
                elif "Action Figures" in cat_name:
                    existing.update(['figure', 'figurine', 'collectible'])

                # Dolls
                elif "Dolls" in cat_name:
                    existing.update(['barbie', 'doll', 'dollhouse'])

                # Board games
                elif "Board Games" in cat_name:
                    existing.update(['monopoly', 'scrabble', 'chess', 'game'])

                # Puzzles
                elif "Puzzles" in cat_name:
                    existing.update(['jigsaw', 'puzzle', '1000 piece'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # BABY & TODDLER
        # ===================================================================
        elif product_type == "Baby & Toddler":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Diapers/Nappies - Match "Disposable Nappies", "Reusable Nappies"
                if "Nappies" in cat_name:
                    existing.update(['pampers', 'huggies', 'nappy', 'nappies', 'diaper', 'diapers',
                                     'baby dry', 'pull-up', 'newborn'])

                # Weaning = Baby Food (purees, formula, etc.)
                elif "Weaning" in cat_name:
                    existing.update(['formula', 'baby food', 'puree', 'infant formula',
                                     'baby formula', 'powder', 'milk powder', 'weaning'])

                # Baby bottles and feeding
                elif "Bottles" in cat_name or "Feeding" in cat_name:
                    existing.update(['bottle', 'bottles', 'sippy cup', 'feeding', 'anti-colic',
                                     'baby formula', 'formula'])

                # Pushchairs = Strollers (British vs American terms)
                elif "Pushchairs" in cat_name or "Travel System" in cat_name:
                    existing.update(['stroller', 'strollers', 'pram', 'prams', 'pushchair',
                                     'buggy', 'lightweight', 'compact', 'travel system'])

                # Car seats
                elif "Car Seats" in cat_name:
                    existing.update(['car seat', 'car seats', 'carseat', 'infant seat',
                                     'safety seat', 'convertible car seat', 'isofix'])

                # Baby Carriers
                elif "Carriers" in cat_name or "Slings" in cat_name:
                    existing.update(['carrier', 'baby carrier', 'sling', 'baby sling',
                                     'wrap', 'structured carrier'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # HEALTH & BEAUTY
        # ===================================================================
        elif product_type == "Health & Beauty":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Haircare products
                if "Shampoo" in cat_name:
                    existing.update(['shampoo', 'hair wash', 'cleansing'])
                elif "Conditioner" in cat_name:
                    existing.update(['conditioner', 'hair conditioner', 'treatment'])

                # Skincare
                elif "Moisturizer" in cat_name or "Moisturiser" in cat_name:
                    existing.update(['moisturizer', 'moisturiser', 'cream', 'lotion'])
                elif "Cleanser" in cat_name:
                    existing.update(['cleanser', 'face wash', 'cleansing'])

                # Makeup
                elif "Lipstick" in cat_name:
                    existing.update(['lipstick', 'lip', 'matte', 'gloss'])
                elif "Foundation" in cat_name:
                    existing.update(['foundation', 'base', 'coverage'])

                # Fragrances
                elif "Perfume" in cat_name or "Cologne" in cat_name:
                    existing.update(['perfume', 'cologne', 'fragrance', 'eau de'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # SPORTING GOODS
        # ===================================================================
        elif product_type == "Sporting Goods":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Gym equipment
                if "Dumbbells" in cat_name or "Weights" in cat_name:
                    existing.update(['dumbbell', 'weight', 'kettlebell'])
                elif "Treadmills" in cat_name:
                    existing.update(['treadmill', 'running machine'])
                elif "Exercise Bikes" in cat_name:
                    existing.update(['exercise bike', 'stationary bike', 'spin bike'])

                # Sports equipment
                elif "Football" in cat_name:
                    existing.update(['soccer', 'football', 'ball'])
                elif "Basketball" in cat_name:
                    existing.update(['basketball', 'hoop', 'ball'])
                elif "Tennis" in cat_name:
                    existing.update(['tennis', 'racket', 'racquet', 'ball'])

                # Activewear brands
                elif "Activewear" in cat_name or "Sports Clothing" in cat_name:
                    existing.update(['nike', 'adidas', 'under armour', 'puma', 'reebok'])
                
                # Running shoes / Athletic footwear
                elif "Running Shoes" in cat_name or "Athletic Shoes" in cat_name or "Trainers" in cat_name:
                    existing.update(['running shoes', 'trainers', 'sneakers', 'air max', 'nike',
                                     'adidas', 'running', 'jogging', 'marathon'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # CAMERAS & OPTICS
        # ===================================================================
        elif product_type == "Cameras & Optics":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Main Cameras ONLY - Add brand keywords (not for lenses or accessories!)
                if cat_name == "Cameras":
                    existing.update(['canon', 'nikon', 'sony', 'fujifilm', 'panasonic', 'olympus'])

                # Camera Lenses - NO brand keywords, only lens-specific terms
                elif "Lenses" in cat_name and cat_name != "Cameras":
                    # Remove any brand keywords that might have been auto-added
                    existing = {kw for kw in existing if kw not in ['canon', 'nikon', 'sony', 'fujifilm', 'panasonic', 'olympus']}
                    existing.update(['lens', 'lenses', 'mm', 'zoom', 'prime', 'telephoto', 'wide angle'])

                # Binoculars
                elif "Binoculars" in cat_name:
                    existing.update(['binoculars', 'binocular', 'optics'])

                # Camera accessories
                elif "Camera Bags" in cat_name:
                    existing.update(['camera bag', 'case'])
                elif "Tripods" in cat_name:
                    existing.update(['tripod', 'stand', 'mount'])
                elif "Filters" in cat_name or "Filter" in cat_name:
                    existing.update(['filter', 'uv filter', 'lens filter', 'nd filter', 
                                     'polarizer', 'cpl', '77mm', '82mm', '67mm', '52mm'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # HOME & GARDEN
        # ===================================================================
        elif product_type == "Home & Garden":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Bedding
                if "Bed Sheets" in cat_name or "Bedding" in cat_name:
                    existing.update(['sheets', 'bedding', 'linen', 'duvet', 'quilt'])
                elif "Pillows" in cat_name:
                    existing.update(['pillow', 'pillows', 'cushion', 'memory foam', 'bamboo',
                                     'orthopaedic', 'neck support', 'soft pillow'])

                # Kitchen
                elif "Cookware" in cat_name:
                    existing.update(['pan', 'pot', 'frying pan', 'saucepan'])
                elif "Cutlery" in cat_name:
                    existing.update(['knife', 'fork', 'spoon', 'cutlery'])

                # Garden
                elif "Garden Tools" in cat_name:
                    existing.update(['spade', 'rake', 'hoe', 'trowel'])
                elif "Plants" in cat_name:
                    existing.update(['plant', 'seed', 'flower', 'tree'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # FURNITURE
        # ===================================================================
        elif product_type == "Furniture":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Bedroom
                if "Beds" in cat_name:
                    existing.update(['bed', 'king', 'queen', 'double', 'single'])
                elif "Mattresses" in cat_name:
                    existing.update(['mattress', 'memory foam', 'spring'])

                # Living room
                elif "Sofas" in cat_name:
                    existing.update(['sofa', 'couch', 'sectional'])
                elif "Coffee Tables" in cat_name:
                    existing.update(['coffee table', 'table'])

                # Dining
                elif "Dining Tables" in cat_name:
                    existing.update(['dining table', 'table'])
                elif "Chairs" in cat_name:
                    existing.update(['chair', 'seating'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # HARDWARE
        # ===================================================================
        elif product_type == "Hardware":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Power tools
                if "Drills" in cat_name:
                    existing.update(['drill', 'driver', 'cordless'])
                elif "Saws" in cat_name:
                    existing.update(['saw', 'circular saw', 'chainsaw'])

                # Hand tools
                elif "Hammers" in cat_name:
                    existing.update(['hammer', 'mallet'])
                elif "Screwdrivers" in cat_name:
                    existing.update(['screwdriver', 'phillips', 'flathead'])

                # Materials
                elif "Paint" in cat_name:
                    existing.update(['paint', 'primer', 'coating'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # LUGGAGE & BAGS
        # ===================================================================
        elif product_type == "Luggage & Bags":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Backpacks
                if "Backpacks" in cat_name:
                    existing.update(['backpack', 'rucksack', 'bag'])

                # Suitcases and luggage
                elif "Suitcases" in cat_name or "Luggage" in cat_name or "Cabin" in cat_name:
                    existing.update(['suitcase', 'suitcases', 'luggage', 'trolley', 'roller',
                                     'cabin', 'carry on', 'hard shell', 'spinner'])

                # Handbags
                elif "Handbags" in cat_name:
                    existing.update(['handbag', 'purse', 'tote'])

                sheet_categories[cat_name] = list(existing)

        # ===================================================================
        # PARTY & CELEBRATION
        # ===================================================================
        elif product_type == "Party & Celebration":
            for cat_name in sheet_categories.keys():
                existing = set(sheet_categories[cat_name])

                # Party supplies
                if "Balloons" in cat_name:
                    existing.update(['balloon', 'balloons'])
                elif "Gift Wrap" in cat_name:
                    existing.update(['wrapping paper', 'gift wrap', 'wrap'])
                elif "Party Decorations" in cat_name:
                    existing.update(['decoration', 'banner', 'streamer'])

                sheet_categories[cat_name] = list(existing)

        # Add to main dictionary
        if sheet_categories:
            category_keywords[product_type] = sheet_categories

    # =========================================================================
    # SUPPLEMENTAL CATEGORIES FROM GOOGLE TAXONOMY
    # Add categories that don't exist in Excel but are needed for classification
    # =========================================================================
    
    # Hardware - Add Painting categories (missing from Excel)
    if "Hardware" in category_keywords:
        hw = category_keywords["Hardware"]
        hw["Painting Tools"] = ["paint", "primer", "brush", "roller", "paint brush", 
                                 "paint roller", "spray paint", "wall paint", "interior paint",
                                 "exterior paint", "painting"]
        hw["Paint"] = ["paint", "wall paint", "interior paint", "exterior paint", 
                       "dulux", "crown", "matt paint", "gloss paint", "emulsion"]
        hw["Paint Brushes"] = ["brush", "paint brush", "brushes", "painting brush"]
        hw["Paint Rollers"] = ["roller", "paint roller", "rollers"]
        
    # Sporting Goods - Add Athletic Footwear (missing from Excel)
    if "Sporting Goods" in category_keywords:
        sg = category_keywords["Sporting Goods"]
        sg["Athletic Shoes"] = ["running shoes", "trainers", "sneakers", "athletic shoes",
                                 "nike", "adidas", "air max", "running", "jogging",
                                 "marathon", "sports shoes"]
        sg["Running Shoes"] = ["running shoes", "running trainers", "marathon shoes",
                                "jogging shoes", "air max", "ultraboost"]
        
    # Home & Garden - Ensure Pillows category exists and has good keywords
    if "Home & Garden" in category_keywords:
        hg = category_keywords["Home & Garden"]
        if "Pillows" not in hg:
            hg["Pillows"] = ["pillow", "pillows", "memory foam", "bamboo", "cushion",
                              "orthopaedic", "neck pillow", "sleeping pillow"]

    return category_keywords


def format_as_python_dict(category_keywords: Dict) -> str:
    """
    Format the category keywords as a Python dictionary string.

    Args:
        category_keywords: Dictionary from generate_category_keywords_from_excel()

    Returns:
        Formatted Python code string
    """
    lines = ["CATEGORY_KEYWORDS = {"]

    for product_type, categories in sorted(category_keywords.items()):
        lines.append(f'    "{product_type}": {{')

        for category, keywords in sorted(categories.items()):
            # Format keywords list
            keywords_str = ", ".join(f'"{kw}"' for kw in sorted(keywords)[:20])  # Limit to 20 keywords
            lines.append(f'        "{category}": [{keywords_str}],')

        lines.append("    },")

    lines.append("}")

    return "\n".join(lines)


def save_generated_keywords(output_file: str = "generated_keywords.py"):
    """
    Generate and save CATEGORY_KEYWORDS to a file.

    Args:
        output_file: Output Python file path
    """
    print("Generating category keywords from Excel taxonomy...")

    category_keywords = generate_category_keywords_from_excel()

    # Count statistics
    total_product_types = len(category_keywords)
    total_categories = sum(len(cats) for cats in category_keywords.values())

    print(f"Generated keywords for:")
    print(f"  - {total_product_types} product types")
    print(f"  - {total_categories} categories")

    # Format as Python code
    code = format_as_python_dict(category_keywords)

    # Add header
    header = '''"""
Auto-generated Category Keywords
Generated from Categories & subs.xlsx
DO NOT EDIT MANUALLY - Use keyword_generator.py to regenerate
"""

'''

    # Save to file
    project_root = Path(__file__).parent.parent
    output_path = project_root / "src" / output_file

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header + code)

    print(f"\nSaved to: {output_path}")
    return category_keywords


if __name__ == "__main__":
    # Generate and save keywords
    save_generated_keywords()
