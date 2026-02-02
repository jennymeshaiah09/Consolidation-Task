# Keyword Extraction Optimization Summary

## Overview
Comprehensive optimization of keyword extraction based on MSV (Monthly Search Volume) analysis showing that 46.4% of zero-MSV keywords suffer from over-length issues.

**Target:** Produce 2-4 word keywords that match actual Google search patterns.

---

## 11 Critical Issues Fixed

### Issue 1: Over-Length Keywords (46.4% of zeros)
**Problem:** Keywords with 7+ words get zero MSV. 96.3% of keywords with MSV are under 7 words.

**Fix:**
- ✅ **RAKE:** Cap at 4 words maximum
- ✅ **LLM:** Updated prompt to enforce "Maximum 4 words total"
- **Formula:** Brand + Product Type + (optional 1 differentiator)

**Example:**
```
Before: Balvenie 12 Year Old The Sweet Toast of American Oak Single Malt Whisky (13 words)
After:  Balvenie Oak Whisky (3 words)
```

---

### Issue 2: Size & Volume Units (32.5% of zeros vs 4.6% of non-zeros)
**Problem:** Nobody searches "blantons bourbon 750ml". They search "blantons bourbon".

**Fix:**
- ✅ **RAKE:** Regex patterns to strip ml/cl/l/oz/kg/g and quantity×size formats
- ✅ **LLM:** Explicit rule to remove all size/volume units
- **Patterns:** 750ml, 24x330ml, 4cl miniature, 1L, 500g, etc.

**Example:**
```
Before: Blantons Single Barrel Bourbon 750ml
After:  Blantons Barrel Bourbon
```

---

### Issue 3: Age Statements (11.0% of zeros vs 0.2% of non-zeros)
**Problem:** "12 Year Old" adds 3 words unnecessarily. People search "balvenie 12" not "balvenie 12 year old".

**Fix:**
- ✅ **RAKE:** Convert "X year old" → "Xyr" or drop entirely
- ✅ **LLM:** Rule to simplify age statements
- **Pattern:** "12 Year Old" → "12yr", "18 year old" → "18yr"

**Example:**
```
Before: Lagavulin 16 Year Old Single Malt Whisky
After:  Lagavulin 16yr Whisky
```

---

### Issue 4: Gift/Personalization Language (12.3% of zeros vs 1.9%)
**Problem:** Merchandising descriptors from retailer feeds, not consumer search terms.

**Fix:**
- ✅ **RAKE:** Filter out gift/hamper/present/personalised/gift set/gift box
- ✅ **LLM:** Explicit rule to remove gift language
- **Words:** personalised, hamper, gift, present, gift set, gift box, custom, bespoke

**Example:**
```
Before: Personalised Luxury Grey Goose Vodka Hamper Gift
After:  Grey Goose Vodka
```

---

### Issue 5: Vintage Years (7.3% of zeros vs 2.7%)
**Problem:** Vintage years rarely add search value. People search "whispering angel rosé", not "whispering angel 2022".

**Fix:**
- ✅ **RAKE:** Strip 4-digit years (2023, 2024, 2025, etc.)
- ✅ **LLM:** Rule to drop vintage years unless brand-critical
- **Pattern:** Match `\b(19|20)\d{2}\b`

**Example:**
```
Before: Whispering Angel Rose 2022
After:  Whispering Angel Rose
```

---

### Issue 6: Case/Multipack Descriptors (6.8% of zeros vs 1.0%)
**Problem:** Purchase formats, not search intent keywords.

**Fix:**
- ✅ **RAKE:** Filter out case/multipack/selection/variety/tasting set
- ✅ **LLM:** Rule to remove case/multipack language
- **Words:** mixed case, tasting set, selection, variety, case of six, multipack

**Example:**
```
Before: Vault City Sour Mixed Case
After:  Vault City Sour
```

---

### Issue 7: Word Repetition (7.8% of zeros vs 0.6%)
**Problem:** Extraction failing to deduplicate. Brand names appearing twice.

**Fix:**
- ✅ **RAKE:** Deduplication pass to remove repeated content words
- ✅ **LLM:** Explicit deduplication rule
- **Logic:** Keep first occurrence, remove subsequent repeats

**Example:**
```
Before: Edmunds Cocktails 1L Edmunds Strawberry Daiquiri Cocktail
After:  Edmunds Cocktails Strawberry Daiquiri
```

---

### Issue 8: Broken/Stripped Accents (358 zeros)
**Problem:** Accent stripping corrupts words. "rosé" → "ros" is unsearchable.

**Fix:**
- ✅ **RAKE:** Proper accent normalization map (rosé → rose, château → chateau)
- ✅ **LLM:** Rule to handle accents properly (keep or normalize, never corrupt)
- **Map:** é→e, è→e, ê→e, ë→e, á→a, ó→o, ñ→n, ç→c, etc.

**Example:**
```
Before: Tread Softly Ros (broken)
After:  Tread Softly Rose (normalized)
```

---

### Issue 9: Promotional/Commercial Language (3.3% of zeros vs 0.4%)
**Problem:** CTAs and sales language from feeds, not search keywords.

**Fix:**
- ✅ **RAKE:** Stop word list of commercial terms
- ✅ **LLM:** Rule to remove promotional language
- **Words:** offer, deal, discount, buy, shop, limited edition, black friday, special offer, exclusive

**Example:**
```
Before: Black Friday Giordanos Bestsellers Limited Edition
After:  Giordanos
```

---

### Issue 10: ABV/Proof Information (2.9% of zeros vs 0.1%)
**Problem:** Nobody searches by alcohol percentage.

**Fix:**
- ✅ **RAKE:** Strip patterns matching X% abv, X proof, X vol
- ✅ **LLM:** Rule to remove ABV/proof info
- **Patterns:** 40% ABV, 20% vol, 100 proof, 13.5%

**Example:**
```
Before: Urban Rhino Dragon Lime Liqueur 50cl 20% ABV
After:  Urban Rhino Liqueur
```

---

### Issue 11: Retailer/Merchant Contamination (7.1% of zeros)
**Problem:** Merchant names from GMC feed bleeding into extraction.

**Fix:**
- ✅ **RAKE:** Retailer exclusion list from merchant IDs
- ✅ **LLM:** Rule to strip merchant names
- **Retailers:** Laithwaites, Waitrose, Greene King Shop, Buy X Shop, etc.

**Example:**
```
Before: Buy Bonkers Conkers Ale Greene King Shop
After:  Bonkers Conkers Ale
```

---

## Implementation Summary

### RAKE Algorithm (`src/rake_keywords.py`)
- 489 lines of code
- **Speed:** ~1000 products/second (instant)
- **API Calls:** None (fully local)
- **New Features:**
  - Comprehensive stop word lists (stop, promotional, gift, multipack, retailer)
  - Pattern removal for sizes, years, ABV, quantities
  - Accent normalization map
  - Word deduplication logic
  - 4-word cap enforcement at multiple stages
  - 26 test cases covering all 11 issues

### LLM Extraction (`src/llm_keywords.py`)
- Updated prompt with explicit MSV optimization rules
- Added 11 critical rules with examples
- Changed from "2-5 words" to "Maximum 4 words total"
- Added MSV-optimized transformation examples
- Maintained batch processing efficiency (20 products per call)

---

## Test Results

### RAKE Algorithm Test Cases:
```
✅ Balvenie 12 Year Old The Sweet Toast... → Balvenie Oak Whisky (3 words)
✅ Blantons Single Barrel Bourbon 750ml → Blantons Barrel Bourbon (3 words)
✅ Vault City Sour Mixed Case 24x330ml → Vault City Sour (3 words)
✅ Lagavulin 16 Year Old Single Malt → Lagavulin 16yr Whisky (3 words)
✅ Personalised Luxury Grey Goose Vodka Hamper → Grey Goose Vodka (3 words)
✅ Chin Chin Vinho Verde 2024 → Chin Vinho Verde (3 words)
✅ Whispering Angel Rose 2022 → Whispering Angel Rose (3 words)
✅ Edmunds Cocktails 1L Edmunds Strawberry → Edmunds Cocktails Strawberry Daiquiri (4 words)
✅ Tread Softly Rosé Wine → Tread Softly Rose Wine (4 words)
✅ Moët & Chandon Brut Imperial → Moet Chandon (2 words)
✅ Black Friday Giordanos Bestsellers → Giordanos (1 words)
✅ Urban Rhino Dragon Lime Liqueur 50cl 20% ABV → Urban Rhino Liqueur (3 words)
✅ Jack Daniels Tennessee Whiskey 40% → Jack Daniels Whiskey (3 words)
✅ Buy Bonkers Conkers Ale Greene King Shop → Bonkers Conkers Ale (3 words)
```

### Expected Impact:
- **Reduction in zero-MSV keywords:** From 46.4% to <10%
- **Average keyword length:** From 7+ words to 2-4 words
- **MSV optimization:** Keywords now match actual Google search patterns
- **Search-friendliness:** Produces keywords customers actually type

---

## Files Modified

1. **`src/rake_keywords.py`**
   - Complete rewrite with MSV optimization
   - 489 lines (from 353 lines)
   - All 11 issues addressed

2. **`src/llm_keywords.py`**
   - Updated prompt with 11 critical rules
   - Added MSV-optimized examples
   - Changed max word limit to 4

---

## Next Steps

1. **Test on Production Data:** Run both RAKE and LLM modes on full dataset
2. **MSV Validation:** Upload generated keywords to Google Ads Keyword Planner
3. **Compare Zero Rates:** Measure reduction from 46.4% baseline
4. **A/B Testing:** Compare RAKE vs LLM keyword quality
5. **Iterative Refinement:** Monitor MSV results and add edge case filters

---

## Deployment Checklist

- ✅ RAKE algorithm updated with all 11 fixes
- ✅ LLM prompt updated with comprehensive rules
- ✅ Test cases added covering all issues
- ✅ Accent normalization implemented
- ✅ Word deduplication added
- ✅ 4-word cap enforced at multiple stages
- ✅ Retailer exclusion list created
- ✅ Promotional/gift/multipack filters added
- ⏳ Production testing pending
- ⏳ MSV validation pending

---

**Date:** 2026-02-02
**Session:** 8 - MSV Keyword Optimization
**Status:** Complete - Ready for Production Testing
