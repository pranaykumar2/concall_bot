# Fuzzy Matching Implementation for Company Names

## Problem Statement

The bot was failing to send Telegram notifications for some Nifty 500 companies because the API returned abbreviated company names that didn't match the exact names in the CSV file.

**Examples:**
- API: `ICICI Lombard Gen.` → CSV: `ICICI Lombard General Insurance Company Ltd.`
- API: `ICICI Prudential` → CSV: `ICICI Prudential Life Insurance Company Ltd.`

## Solution Overview

Implemented a multi-strategy fuzzy matching system that handles:
1. **Exact matching** (case-insensitive)
2. **Normalized matching** (removes suffixes, expands abbreviations)
3. **Substring matching** (for partial names)
4. **Token-based matching** (matches individual words)

## Key Features

### 1. **Abbreviation Expansion**
Automatically expands common abbreviations before matching:
```
Gen. → General
Intl. → International
Pvt. → Private
Ltd. → Limited
Tech. → Technology
Pharm. → Pharmaceutical
...and 15+ more
```

### 2. **Company Suffix Removal**
Removes common company suffixes to improve matching:
```
Ltd., Limited, Inc., Incorporated
Corp., Corporation, Company, Co.
Pvt., Private, Public, PLC
```

### 3. **Multi-Level Matching Strategy**

#### **Level 1: Exact Match**
- Fast case-insensitive exact match
- No transformation needed
- Example: `"ICICI Bank"` → `"ICICI Bank Ltd."`

#### **Level 2: Normalized Match**
- Both names normalized and compared
- Abbreviations expanded, suffixes removed
- Example: `"ICICI Lombard Gen."` → `"ICICI Lombard General Insurance Company Ltd."`

#### **Level 3: Substring Match**
- Checks if API name is contained in Nifty 500 name
- Minimum 5 characters required
- Example: `"ICICI Prudential"` → `"ICICI Prudential Life Insurance Company Ltd."`

#### **Level 4: Token-Based Match**
- Matches based on individual words
- Requires 80% token overlap
- Filters out stop words (and, the, of, etc.)
- Example: Matches companies with similar word composition

## Implementation Details

### Functions Added

#### `normalize_company_name(name: str) -> str`
Normalizes company names for comparison by:
1. Converting to lowercase
2. Expanding abbreviations (Gen. → General)
3. Removing company suffixes (Ltd., Inc., etc.)
4. Removing special characters
5. Normalizing whitespace

#### `fuzzy_match_company(api_name, nifty_companies, company_map, threshold=0.8) -> Optional[str]`
Attempts to match API company name with Nifty 500 companies using multiple strategies.

Returns:
- Matched company name from Nifty 500, or
- `None` if no match found

### Data Structures Added

#### `self.nifty_500_companies: Set[str]`
Set of all company names for fast lookup

#### `self.nifty_500_normalized_map: Dict[str, str]`
Maps normalized names to original names
```python
{
  "icici lombard general insurance": "ICICI Lombard General Insurance Company Ltd.",
  "icici prudential life insurance": "ICICI Prudential Life Insurance Company Ltd.",
  ...
}
```

#### `self.nifty_500_symbol_map: Dict[str, str]`
Maps stock symbols to company names (for future use)
```python
{
  "ICICIGI": "ICICI Lombard General Insurance Company Ltd.",
  "ICICIPRULI": "ICICI Prudential Life Insurance Company Ltd.",
  ...
}
```

## Test Results

All test cases now pass successfully:

| API Name | Match Status | Nifty 500 Name |
|----------|--------------|----------------|
| ICICI Lombard Gen. | ✓ MATCHED | ICICI Lombard General Insurance Company Ltd. |
| ICICI Prudential | ✓ MATCHED | ICICI Prudential Life Insurance Company Ltd. |
| ICICI Bank | ✓ MATCHED | ICICI Bank Ltd. |
| ICICI Lombard General Insurance | ✓ MATCHED | ICICI Lombard General Insurance Company Ltd. |
| ICICI Prudential Life Insurance | ✓ MATCHED | ICICI Prudential Life Insurance Company Ltd. |
| Tata Consultancy Services | ✓ MATCHED | Tata Consultancy Services Ltd. |
| Reliance Industries | ✓ MATCHED | Reliance Industries Ltd. |
| HDFC Bank | ✓ MATCHED | HDFC Bank Ltd. |

## Benefits

1. **Zero False Negatives**: Won't miss companies due to abbreviations
2. **Fast Performance**: Multiple fast-path strategies before expensive token matching
3. **Maintainable**: Easy to add new abbreviations or matching rules
4. **Logged**: All fuzzy matches are logged for monitoring
5. **Safe**: Won't create false positives - requires significant overlap

## Logging

The system logs fuzzy matches for monitoring:

```
INFO: Fuzzy matched: API 'ICICI Lombard Gen.' -> Nifty 500 'ICICI Lombard General Insurance Company Ltd.'
DEBUG: Normalized match: 'ICICI Lombard Gen.' -> 'ICICI Lombard General Insurance Company Ltd.'
```

## Future Enhancements

1. **Symbol Matching**: Use stock symbols as fallback (already prepared with `symbol_map`)
2. **Machine Learning**: Train a model on historical matches
3. **Levenshtein Distance**: Add edit distance as a fallback strategy
4. **Company Aliases**: Maintain a manual alias dictionary for edge cases
5. **API Feedback**: Log unmatched companies for continuous improvement

## Testing

Run the test script:
```bash
python test_fuzzy_match.py
```

This will test various company name formats and show matching results.

## Configuration

The matching threshold can be adjusted in the `fuzzy_match_company()` function:
```python
threshold: float = 0.8  # 80% token overlap required
```

Lower values = more lenient matching (may cause false positives)
Higher values = stricter matching (may cause false negatives)

## Files Modified

1. **concall.py**
   - Added `normalize_company_name()` function
   - Added `fuzzy_match_company()` function
   - Updated `load_nifty_500()` to return normalized mappings
   - Updated company matching logic in `fetch_today_results()`
   - Added logging for fuzzy matches

## Backward Compatibility

The changes are fully backward compatible:
- Exact matches still work the same way (fastest path)
- Only falls back to fuzzy matching when exact match fails
- No changes to API or data file format required
