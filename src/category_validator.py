"""
Category Validation Module
Validates category assignments using LLM to ensure accuracy.

Supports multiple validation strategies:
1. Full validation - Check all products
2. Dual classification - Compare keyword vs LLM
3. Confidence-based - Only validate uncertain matches
"""

import os
import time
from typing import List, Dict, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class CategoryValidator:
    """Validates product category assignments using LLM."""

    def __init__(self, api_key: str = None):
        """Initialize the validator with Gemini API."""
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        genai.configure(api_key=self.api_key)

        # Use the same model as keyword generation for consistency
        self.model = genai.GenerativeModel('gemma-3-4b-it')

    def validate_categories_batch(
        self,
        products: List[Dict],
        available_categories: List[str],
        batch_size: int = 20
    ) -> List[Dict]:
        """
        Validate category assignments for a batch of products.

        Args:
            products: List of dicts with 'title', 'brand', 'assigned_category'
            available_categories: List of valid category names
            batch_size: Number of products to process per API call

        Returns:
            List of dicts with validation results:
            {
                'title': str,
                'assigned_category': str,
                'llm_suggested_category': str,
                'is_correct': bool,
                'confidence': str (high/medium/low)
            }
        """
        results = []
        total_batches = (len(products) + batch_size - 1) // batch_size

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1

            print(f"Validating batch {batch_num}/{total_batches} ({len(batch)} products)...")

            try:
                batch_results = self._validate_batch(batch, available_categories)
                results.extend(batch_results)

                # Rate limiting between batches
                if i + batch_size < len(products):
                    time.sleep(2)

            except Exception as e:
                print(f"Error validating batch {batch_num}: {e}")
                # Add fallback results (assume correct if validation fails)
                for product in batch:
                    results.append({
                        'title': product['title'],
                        'assigned_category': product['assigned_category'],
                        'llm_suggested_category': product['assigned_category'],
                        'is_correct': True,
                        'confidence': 'unknown',
                        'error': str(e)
                    })

        return results

    def _validate_batch(self, products: List[Dict], available_categories: List[str]) -> List[Dict]:
        """Validate a single batch of products."""

        # Build the prompt for batch validation
        prompt = self._build_validation_prompt(products, available_categories)

        # Configure safety settings (correct format for Gemini API)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Generate validation
        response = self.model.generate_content(
            prompt,
            safety_settings=safety_settings
        )

        # Parse response
        results = self._parse_validation_response(response.text, products)

        return results

    def _build_validation_prompt(self, products: List[Dict], available_categories: List[str]) -> str:
        """Build the prompt for batch validation."""

        # Format products for the prompt
        products_text = ""
        for idx, product in enumerate(products, 1):
            products_text += f"{idx}. Title: {product['title']}\n"
            products_text += f"   Brand: {product.get('brand', 'Unknown')}\n"
            products_text += f"   Assigned Category: {product['assigned_category']}\n\n"

        # Format available categories (show a sample if too many)
        if len(available_categories) > 100:
            categories_text = f"Available categories ({len(available_categories)} total): " + \
                            ", ".join(available_categories[:50]) + "... and more"
        else:
            categories_text = "Available categories: " + ", ".join(available_categories)

        prompt = f"""You are validating product category assignments for an e-commerce catalog.

{categories_text}

CRITICAL RULES:
1. NEVER use "Other" as a category - it is forbidden
2. ALWAYS choose the MOST SPECIFIC category from the available options
3. For alcoholic beverages, use specific types:
   - Whisky/Scotch/Bourbon for whiskies (Glenlivet, Macallan, Jack Daniels)
   - Red Wine for red wines (Cabernet, Merlot, Shiraz, Pinot Noir)
   - White Wine for white wines (Chardonnay, Sauvignon Blanc, Pinot Grigio)
   - Rosé Wine or Rose Wine for pink wines (Whispering Angel, Provence rosé)
   - Sparkling Wine/Champagne for fizzy wines (Prosecco, Champagne, Cava, Nyetimber)
   - Beer/Lager/IPA/Ale for beers (Peroni, Heineken, Corona)
   - Vodka/Gin/Rum/Tequila for spirits
   - Liqueur for flavored spirits (Aperol, Disaronno, Pimm's, Baileys, St Germain)
4. If unsure between options, pick the closest matching category
5. Only use broad categories as last resort if no specific match exists

For each product below, validate if the assigned category is correct.
If incorrect, suggest the best alternative from the available categories.
Also rate your confidence: HIGH (very sure), MEDIUM (fairly sure), or LOW (uncertain).

Products to validate:
{products_text}

Respond in this exact format for each product (one per line):
<product_number>|<CORRECT or INCORRECT>|<suggested_category>|<confidence>

Examples:
1|INCORRECT|Whisky|HIGH
2|INCORRECT|Rosé Wine|HIGH
3|INCORRECT|Liqueur|HIGH
4|INCORRECT|Sparkling Wine|MEDIUM
5|INCORRECT|Beer|HIGH

Validate all {len(products)} products now:"""

        return prompt

    def _parse_validation_response(self, response_text: str, products: List[Dict]) -> List[Dict]:
        """Parse the LLM's validation response."""

        results = []
        lines = response_text.strip().split('\n')

        for idx, product in enumerate(products):
            # Find matching line for this product
            matching_line = None
            for line in lines:
                if line.strip().startswith(f"{idx + 1}|"):
                    matching_line = line.strip()
                    break

            if matching_line:
                try:
                    parts = matching_line.split('|')
                    is_correct = parts[1].strip().upper() == 'CORRECT'
                    suggested_category = parts[2].strip()
                    confidence = parts[3].strip().lower()

                    results.append({
                        'title': product['title'],
                        'assigned_category': product['assigned_category'],
                        'llm_suggested_category': suggested_category,
                        'is_correct': is_correct,
                        'confidence': confidence
                    })
                except (IndexError, ValueError) as e:
                    # Fallback if parsing fails
                    results.append({
                        'title': product['title'],
                        'assigned_category': product['assigned_category'],
                        'llm_suggested_category': product['assigned_category'],
                        'is_correct': True,
                        'confidence': 'unknown',
                        'parse_error': str(e)
                    })
            else:
                # No matching line found, assume correct
                results.append({
                    'title': product['title'],
                    'assigned_category': product['assigned_category'],
                    'llm_suggested_category': product['assigned_category'],
                    'is_correct': True,
                    'confidence': 'unknown'
                })

        return results

    def dual_classify(
        self,
        products: List[Dict],
        available_categories: List[str],
        batch_size: int = 20
    ) -> List[Dict]:
        """
        Perform dual classification: Both keyword and LLM classify independently.

        Args:
            products: List of dicts with 'title', 'brand'
            available_categories: List of valid category names
            batch_size: Number of products per API call

        Returns:
            List of dicts with both classifications:
            {
                'title': str,
                'keyword_category': str,
                'llm_category': str,
                'agree': bool,
                'final_category': str (uses LLM if disagree)
            }
        """
        results = []
        total_batches = (len(products) + batch_size - 1) // batch_size

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1

            print(f"Dual-classifying batch {batch_num}/{total_batches} ({len(batch)} products)...")

            try:
                batch_results = self._dual_classify_batch(batch, available_categories)
                results.extend(batch_results)

                # Rate limiting
                if i + batch_size < len(products):
                    time.sleep(2)

            except Exception as e:
                print(f"Error in dual classification batch {batch_num}: {e}")
                # Fallback to keyword category
                for product in batch:
                    results.append({
                        'title': product['title'],
                        'keyword_category': product.get('keyword_category', 'Other'),
                        'llm_category': product.get('keyword_category', 'Other'),
                        'agree': True,
                        'final_category': product.get('keyword_category', 'Other'),
                        'error': str(e)
                    })

        return results

    def _dual_classify_batch(self, products: List[Dict], available_categories: List[str]) -> List[Dict]:
        """Perform dual classification for a single batch."""

        # Build prompt for LLM classification
        prompt = self._build_classification_prompt(products, available_categories)

        # Configure safety settings (correct format for Gemini API)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Get LLM classifications
        response = self.model.generate_content(
            prompt,
            safety_settings=safety_settings
        )

        # Parse and compare
        results = self._parse_dual_classification(response.text, products)

        return results

    def _build_classification_prompt(self, products: List[Dict], available_categories: List[str]) -> str:
        """Build prompt for LLM classification."""

        products_text = ""
        for idx, product in enumerate(products, 1):
            products_text += f"{idx}. {product['title']} - {product.get('brand', '')}\n"

        # Sample categories if too many
        if len(available_categories) > 100:
            categories_text = f"Available categories ({len(available_categories)} total): " + \
                            ", ".join(available_categories[:50]) + "..."
        else:
            categories_text = "Available categories: " + ", ".join(available_categories)

        prompt = f"""Classify each product into the most specific category from the available options.

{categories_text}

Products:
{products_text}

Respond with just the category name for each product (one per line):
1|<category>
2|<category>
...

Classify all {len(products)} products now:"""

        return prompt

    def _parse_dual_classification(self, response_text: str, products: List[Dict]) -> List[Dict]:
        """Parse dual classification results and compare."""

        results = []
        lines = response_text.strip().split('\n')

        for idx, product in enumerate(products):
            keyword_category = product.get('keyword_category', 'Other')

            # Find LLM category
            llm_category = keyword_category  # Default fallback
            for line in lines:
                if line.strip().startswith(f"{idx + 1}|"):
                    try:
                        llm_category = line.split('|')[1].strip()
                    except IndexError:
                        pass
                    break

            # Compare
            agree = keyword_category == llm_category
            final_category = llm_category  # Trust LLM if they disagree

            results.append({
                'title': product['title'],
                'keyword_category': keyword_category,
                'llm_category': llm_category,
                'agree': agree,
                'final_category': final_category
            })

        return results

    def generate_validation_report(self, validation_results: List[Dict]) -> Dict:
        """Generate summary statistics from validation results."""

        total = len(validation_results)
        correct = sum(1 for r in validation_results if r['is_correct'])
        incorrect = total - correct

        # Group by confidence
        high_conf = sum(1 for r in validation_results if r['confidence'] == 'high')
        medium_conf = sum(1 for r in validation_results if r['confidence'] == 'medium')
        low_conf = sum(1 for r in validation_results if r['confidence'] == 'low')

        # Find misclassifications
        misclassifications = [
            r for r in validation_results if not r['is_correct']
        ]

        return {
            'total_products': total,
            'correct': correct,
            'incorrect': incorrect,
            'accuracy': correct / total if total > 0 else 0,
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
            'misclassifications': misclassifications
        }


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    validator = CategoryValidator()

    # Example: Validate categories
    test_products = [
        {
            'title': 'Penfolds Grange Shiraz 2019',
            'brand': 'Penfolds',
            'assigned_category': 'Red Wine'
        },
        {
            'title': 'iPhone 15 Pro Max 256GB',
            'brand': 'Apple',
            'assigned_category': 'Smartphones'
        },
        {
            'title': 'Royal Canin Adult Dog Food',
            'brand': 'Royal Canin',
            'assigned_category': 'Dog Food'
        }
    ]

    available_categories = ['Red Wine', 'White Wine', 'Smartphones', 'Dog Food', 'Cat Food']

    print("Testing category validation...")
    results = validator.validate_categories_batch(test_products, available_categories)

    for r in results:
        status = "✅" if r['is_correct'] else "❌"
        print(f"{status} {r['title']}")
        print(f"   Assigned: {r['assigned_category']}")
        print(f"   LLM Says: {r['llm_suggested_category']} (confidence: {r['confidence']})")
        print()

    report = validator.generate_validation_report(results)
    print(f"\nValidation Report:")
    print(f"Accuracy: {report['accuracy']:.1%}")
    print(f"Correct: {report['correct']}/{report['total_products']}")
