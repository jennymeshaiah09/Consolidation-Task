"""
Taxonomy Classifier Module
Uses Google Product Taxonomy with fuzzy matching for accurate product categorization.
"""

from rapidfuzz import fuzz, process
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class TaxonomyClassifier:
    """Classify products using Google Product Taxonomy with fuzzy matching."""
    
    def __init__(self, taxonomy_file: str = "taxonomy.txt"):
        """Initialize with taxonomy file."""
        self.categories: Dict[str, List[str]] = {}  # product_type -> [categories]
        self.category_keywords: Dict[str, List[str]] = {}  # category -> keywords
        self._load_taxonomy(taxonomy_file)
    
    def _load_taxonomy(self, taxonomy_file: str):
        """Load and parse Google Product Taxonomy."""
        project_root = Path(__file__).parent.parent
        taxonomy_path = project_root / taxonomy_file
        
        if not taxonomy_path.exists():
            raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")
        
        # Map Google top-level categories to our product types
        type_mapping = {
            "Animals & Pet Supplies": "Pets",
            "Baby & Toddler": "Baby & Toddler",
            "Electronics": "Electronics",
            "Cameras & Optics": "Cameras & Optics",
            "Sporting Goods": "Sporting Goods",
            "Toys & Games": "Toys",
            "Home & Garden": "Home & Garden",
            "Furniture": "Furniture",
            "Hardware": "Hardware",
            "Luggage & Bags": "Luggage & Bags",
            "Health & Beauty": "Health & Beauty",
            "Food, Beverages & Tobacco": "Alcoholic Beverages",
            "Arts & Entertainment": "Party & Celebration",
        }
        
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse: "ID - Category > Subcategory > ..."
                if ' - ' not in line:
                    continue
                    
                parts = line.split(' - ', 1)
                if len(parts) != 2:
                    continue
                
                category_path = parts[1].strip()
                
                # Get top-level category
                top_level = category_path.split(' > ')[0]
                product_type = type_mapping.get(top_level)
                
                if product_type:
                    if product_type not in self.categories:
                        self.categories[product_type] = []
                    self.categories[product_type].append(category_path)
                    
                    # Extract keywords from category path
                    self.category_keywords[category_path] = self._extract_keywords(category_path)
    
    def _extract_keywords(self, category_path: str) -> List[str]:
        """Extract searchable keywords from category path."""
        keywords = []
        
        # Get each level
        levels = category_path.split(' > ')
        
        for level in levels:
            # Clean and lowercase
            clean = level.lower().strip()
            clean = re.sub(r'[^a-z0-9\s&-]', '', clean)
            
            # Add full level name
            keywords.append(clean)
            
            # Add individual words (except very short ones)
            words = clean.split()
            for word in words:
                if len(word) > 3 and word not in ['with', 'and', 'the', 'for']:
                    keywords.append(word)
        
        return list(set(keywords))
    
    def classify(self, product_title: str, product_type: str) -> Tuple[str, float]:
        """
        Classify a product using fuzzy matching against taxonomy.
        
        Args:
            product_title: Product title to classify
            product_type: Expected product type (Pets, Electronics, etc.)
            
        Returns:
            Tuple of (category_name, confidence_score)
        """
        if product_type not in self.categories:
            return ("Other", 0.0)
        
        title_lower = product_title.lower()
        
        # Get all categories for this product type
        candidates = self.categories[product_type]
        
        if not candidates:
            return ("Other", 0.0)
        
        # Score each category
        best_match = None
        best_score = 0
        
        for category in candidates:
            keywords = self.category_keywords.get(category, [])
            
            # Calculate score based on keyword matches
            score = 0
            for keyword in keywords:
                if keyword in title_lower:
                    # Longer keywords get higher scores
                    score += len(keyword) * 2
                    
                    # Exact word boundary matches score higher
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, title_lower):
                        score += len(keyword)
            
            # Also use fuzzy matching on last level (most specific)
            leaf = category.split(' > ')[-1].lower()
            fuzzy_score = fuzz.partial_ratio(leaf, title_lower)
            score += fuzzy_score * 0.5  # Weight fuzzy score less
            
            if score > best_score:
                best_score = score
                best_match = category
        
        if best_match and best_score > 20:  # Minimum threshold
            # Return just the leaf category
            leaf = best_match.split(' > ')[-1]
            confidence = min(best_score / 100, 1.0)
            return (leaf, confidence)
        
        return ("Other", 0.0)
    
    def get_leaf_category(self, full_path: str) -> str:
        """Extract leaf (most specific) category from full path."""
        if ' > ' in full_path:
            return full_path.split(' > ')[-1]
        return full_path


# Singleton instance
_classifier = None

def get_classifier() -> TaxonomyClassifier:
    """Get singleton classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = TaxonomyClassifier()
    return _classifier


def classify_with_taxonomy(product_title: str, product_type: str) -> str:
    """
    Convenience function to classify a product.
    
    Args:
        product_title: Product title
        product_type: Product type (Pets, Electronics, BWS, etc.)
        
    Returns:
        Category name
    """
    # Handle product type aliases
    type_mapping = {
        "BWS": "Alcoholic Beverages",
    }
    mapped_type = type_mapping.get(product_type, product_type)
    
    classifier = get_classifier()
    category, confidence = classifier.classify(product_title, mapped_type)
    return category


if __name__ == "__main__":
    # Quick test
    test_cases = [
        ("Samsung Galaxy S25 Ultra 5G", "Electronics"),
        ("iPhone 16 Pro Max 256GB", "Electronics"),
        ("Pampers Baby Dry Nappies Size 3", "Baby & Toddler"),
        ("Baby Formula Milk Powder", "Baby & Toddler"),
        ("Pedigree Adult Dog Food 20kg", "Pets"),
        ("Whiskas Cat Food Variety Pack", "Pets"),
        ("Corona Extra Beer 355ml", "Alcoholic Beverages"),
        ("Jim Beam Bourbon 700ml", "Alcoholic Beverages"),
    ]
    
    print("Testing Taxonomy Classifier:")
    print("=" * 70)
    
    for title, ptype in test_cases:
        result = classify_with_taxonomy(title, ptype)
        print(f"{title[:40]:<45} -> {result}")
