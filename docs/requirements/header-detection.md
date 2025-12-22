# Feature: Automatic Header Detection

## Overview
Automatically detect which row in a spreadsheet contains column headers, enabling better handling of files with title rows, metadata, or inconsistent formatting.

## User Stories

### Data Analyst
As a data analyst,
I want the system to automatically find my column headers,
So that I don't have to manually clean files that have title rows or metadata above the headers.

### Business User
As a business user,
I want to upload spreadsheets without worrying about formatting,
So that I can focus on analysis rather than data preparation.

## Sub-Features

### 1. Header Row Detection
Identify the most likely header row using multi-factor heuristics.

### 2. Confidence Scoring
Provide a confidence score indicating detection reliability.

### 3. Automatic Application
Optionally apply detected headers to clean the DataFrame.

---

## Header Row Detection

### Acceptance Criteria

#### AC-1: String Content Factor
- **Given**: A row with mostly string values
- **When**: Header detection is performed
- **Then**: The row receives a higher score proportional to string content ratio

#### AC-2: Uniqueness Factor
- **Given**: A row with all unique values
- **When**: Header detection is performed
- **Then**: The row receives a higher score (headers typically have unique column names)

#### AC-3: Non-Empty Cells Factor
- **Given**: A row with no empty cells
- **When**: Header detection is performed
- **Then**: The row receives a higher score (headers usually have all columns labeled)

#### AC-4: Data Consistency Below Factor
- **Given**: A row followed by rows with consistent data types per column
- **When**: Header detection is performed
- **Then**: The row receives a higher score (data below headers is typically consistent)

#### AC-5: Position Factor
- **Given**: Multiple candidate header rows
- **When**: Header detection is performed
- **Then**: Earlier rows receive a slight position bonus (headers are usually near the top)

#### AC-6: Header Keywords Factor
- **Given**: A row containing common header keywords (id, name, date, etc.)
- **When**: Header detection is performed
- **Then**: The row receives a bonus score

#### AC-7: Length Check Factor
- **Given**: A row with cell values of typical header length (3-40 characters average)
- **When**: Header detection is performed
- **Then**: The row receives a bonus score

---

## Confidence Scoring

### Acceptance Criteria

#### AC-8: High Confidence Detection
- **Given**: A clear header row with strong signals
- **When**: Detection completes
- **Then**: Confidence score is >= 0.8

#### AC-9: Medium Confidence Detection
- **Given**: A likely header row with moderate signals
- **When**: Detection completes
- **Then**: Confidence score is 0.5-0.8

#### AC-10: Low Confidence Detection
- **Given**: No clear header row
- **When**: Detection completes
- **Then**: Confidence score is < 0.5 and row 0 is returned as default

---

## Automatic Application

### Acceptance Criteria

#### AC-11: Apply High Confidence Header
- **Given**: Header detected with confidence >= 0.7
- **When**: `auto_apply=True` is set
- **Then**: The DataFrame is updated to use detected row as header

#### AC-12: Skip Low Confidence Application
- **Given**: Header detected with confidence < 0.7
- **When**: `auto_apply=True` is set
- **Then**: The DataFrame is NOT modified (use row 0 as default)

#### AC-13: Manual Override
- **Given**: Any detection result
- **When**: User specifies `header_row` parameter
- **Then**: User's choice overrides detection

---

## Algorithm Details

### Scoring Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| String Content | 2.0 | Ratio of string cells in the row |
| Uniqueness | 2.0 | Ratio of unique values in the row |
| Non-Empty | 1.5 | Ratio of non-empty cells |
| Data Consistency Below | 3.0 | How consistent data types are in rows below |
| Position | 0.5 | Earlier rows get slight bonus |
| Header Keywords | 1.5 | Presence of common header terms |
| Length Check | 1.0 | Average cell length in sweet spot (3-40 chars) |

### Total Maximum Score
- Maximum possible score: ~11.5 points
- Confidence = min(score / 10.0, 1.0)

### Search Parameters
- `max_search_rows`: Maximum rows to consider (default: 10)
- `min_data_rows_below`: Minimum rows needed for consistency check (default: 3)

---

## API Contract

### HeaderDetector.detect()

```python
def detect(
    df: pd.DataFrame,
    max_search_rows: int = 10,
    min_data_rows_below: int = 3
) -> HeaderDetectionResult:
    """
    Detect the most likely header row in a DataFrame.
    
    Args:
        df: Input DataFrame (raw, with potential metadata rows)
        max_search_rows: How many rows from top to search
        min_data_rows_below: Minimum rows needed for consistency scoring
        
    Returns:
        HeaderDetectionResult with row index, confidence, and scoring details
    """
```

### HeaderDetectionResult

```python
@dataclass
class HeaderDetectionResult:
    header_row: int           # 0-indexed row number
    confidence: float         # 0.0 to 1.0
    total_score: float        # Raw score before normalization
    factor_scores: dict       # Breakdown by factor
    all_row_scores: List[tuple]  # [(row_idx, score), ...] for debugging
```

### HeaderDetector.apply_header()

```python
def apply_header(
    df: pd.DataFrame,
    header_row: int,
    drop_above: bool = True
) -> pd.DataFrame:
    """
    Apply detected header row to DataFrame.
    
    Args:
        df: Input DataFrame
        header_row: Row index to use as header
        drop_above: Whether to drop rows above header (default: True)
        
    Returns:
        New DataFrame with header applied and cleaned
    """
```

---

## Integration Points

### Upload Service
- Call `HeaderDetector.detect()` after reading each file/sheet
- **For Excel files**: Apply header detection to ALL sheets independently
  - Each sheet may have different header row positions
  - Each sheet is processed and stored with its detected headers applied
- Include detection results in `FileUploadResponse` (for primary/first sheet)
- Auto-apply header if confidence >= 0.7
- If confidence < 0.7, keep original data but convert column indices to strings

### Preview Service
- Show original data with header row highlighted
- Allow user to override detection

### Frontend
- Display header detection status and confidence
- Allow manual header row selection

---

## Multi-Sheet Handling

### Acceptance Criteria

#### AC-14: Independent Sheet Detection
- **Given**: An Excel file with multiple sheets
- **When**: File is uploaded
- **Then**: Each sheet has header detection applied independently

#### AC-15: Per-Sheet Header Application
- **Given**: Sheet A has header in row 0, Sheet B has header in row 2
- **When**: File is processed
- **Then**: Each sheet uses its own detected header row

#### AC-16: Response Contains Primary Sheet Info
- **Given**: An Excel file with multiple sheets
- **When**: File upload response is returned
- **Then**: `header_row` and `header_confidence` reflect the first/primary sheet

---

## Test Scenarios

| Scenario | Input | Expected Header Row | Expected Confidence |
|----------|-------|---------------------|---------------------|
| Clean CSV with header in row 0 | Normal CSV | 0 | >= 0.8 |
| Excel with title in row 0, header in row 1 | Title + Header | 1 | >= 0.8 |
| Excel with 3 metadata rows, header in row 3 | Metadata + Header | 3 | >= 0.7 |
| No clear header (all numeric) | Numeric data only | 0 | < 0.5 |
| Header with some numbers ("Q1 2024") | Mixed header | 0 | >= 0.7 |
| Empty rows before header | Sparse top rows | First non-empty with header traits | >= 0.6 |
| Multi-line merged header | Complex Excel | Last header row | >= 0.6 |

---

## Performance Requirements

- Detection should complete in < 100ms for files up to 10,000 rows
- Memory usage should not exceed 2x the DataFrame size
- Only first N rows (default 10) are analyzed for header detection
