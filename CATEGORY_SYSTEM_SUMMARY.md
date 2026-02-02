# Category Classification System - Summary

## Overview

The system now uses **auto-generated keywords** extracted from your Excel taxonomy file ([Categories & subs.xlsx](Categories & subs.xlsx)) for Phase 1 classification, with LLM fallback for "Other" products in Phase 2.

---

## What Changed

### **Before:**
- Hardcoded keywords for 3 product types (BWS, Pets, Electronics)
- Simple categories: "Beers", "Wines", "Spirits"
- 13 total categories

### **After:**
- Auto-generated keywords from Excel taxonomy
- **14 product types** supported
- **260 categories** with detailed hierarchy
- Example: "Beer > Lager", "Wine > Red Wine", "Liqueurs > Cream Liqueurs"

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Excel Taxonomy (Categories & subs.xlsx)                     │
│ - 14 sheets (product types)                                 │
│ - 746 rows (product categories)                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Keyword Generator (src/keyword_generator.py)                │
│ - Extracts keywords from category names                     │
│ - Generates CATEGORY_KEYWORDS dictionary                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Generated Keywords (src/generated_keywords.py)               │
│ - 260 categories with keywords                              │
│ - Automatically synced with Excel                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Keyword Matching (src/normalization.py)            │
│ - Fast, free classification                                 │
│ - Uses auto-generated keywords                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: LLM Fallback (src/llm_keywords.py)                 │
│ - Only for "Other" products                                 │
│ - Uses same Excel taxonomy                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Supported Product Types

| Product Type | Categories | Example Categories |
|--------------|------------|-------------------|
| **Alcoholic Beverages** | 16 | Beer > Lager, Wine > Red Wine, Spirits > Whisky |
| **Electronics** | 24 | Audio > Headphones, Video > TVs, Computers > Laptops |
| **Pets** | 21 | Dog Supplies > Dog Food, Cat Supplies > Cat Toys |
| **Baby & Toddler** | 20 | Feeding > Baby Bottles, Nursery Furniture > Cots |
| **Cameras & Optics** | 18 | Cameras > Digital Cameras, Optics > Binoculars |
| **Furniture** | 23 | Bedroom Furniture > Beds, Living Room > Sofas |
| **Hardware** | 23 | Power Tools > Drills, Hand Tools > Hammers |
| **Health & Beauty** | 21 | Skincare > Face Creams, Makeup > Lipstick |
| **Home & Garden** | 22 | Garden > Plants, Home Decor > Cushions |
| **Luggage & Bags** | 17 | Suitcases > Hard Shell, Backpacks > Travel |
| **Sporting Goods** | 20 | Fitness > Weights, Outdoor > Camping |
| **Toys** | 21 | Action Figures > Superheroes, Puzzles > Jigsaw |
| **Party & Celebration** | 13 | Party Supplies > Balloons, Decorations > Banners |
| **F&F (Later)** | 1 | Clothing & Accessories |

**Total: 14 product types, 260 categories**

---

## How to Update Categories

When you modify the Excel taxonomy ([Categories & subs.xlsx](Categories & subs.xlsx)):

1. **Edit Excel file** - Add/modify/remove categories
2. **Regenerate keywords:**
   ```bash
   python -m src.keyword_generator
   ```
3. **Restart application** - New keywords will be loaded

---

## Testing

Test the classification system:
```bash
python test_hybrid_categories.py
```

---

## Files Modified

1. **[src/keyword_generator.py](src/keyword_generator.py)** - NEW: Auto-generates keywords from Excel
2. **[src/generated_keywords.py](src/generated_keywords.py)** - NEW: Auto-generated keywords dictionary
3. **[src/normalization.py](src/normalization.py)** - UPDATED: Uses auto-generated keywords
4. **[src/taxonomy.py](src/taxonomy.py)** - UPDATED: Supports all 14 product types
5. **[src/llm_keywords.py](src/llm_keywords.py)** - UPDATED: LLM fallback for "Other"
6. **[pages/2_🔤_Keywords_Categories.py](pages/2_🔤_Keywords_Categories.py)** - UPDATED: Integrated LLM classification

---

## Benefits

✅ **Consistent** - Phase 1 and Phase 2 use same Excel taxonomy
✅ **Scalable** - Supports all 14 product types (260 categories)
✅ **Maintainable** - Update Excel, regenerate keywords
✅ **Cost-effective** - Keyword matching first, LLM only when needed
✅ **Accurate** - Detailed categories from curated Google taxonomy

---

## Backward Compatibility

Old product type names still work:
- `"BWS"` → maps to `"Alcoholic Beverages"`
- `"Pets"` → maps to `"Pets"`
- `"Electronics"` → maps to `"Electronics"`

---

**Last Updated:** 2026-02-01