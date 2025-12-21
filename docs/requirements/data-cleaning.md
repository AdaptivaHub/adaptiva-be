# Feature: Enhanced Data Cleaning Service

## Overview
An enhanced data cleaning service that mimics Excel Copilot's data cleaning functionality. The service provides intelligent data cleaning operations including column name normalisation, empty row/column removal, missing value detection and smart filling, type detection, and comprehensive cleaning operation logging.

## User Story
As a **data analyst using Adaptiva**,
I want **intelligent data cleaning capabilities that automatically detect and fix common data quality issues**,
So that **I can quickly prepare messy datasets for analysis without manual cleaning in Excel**.

## Acceptance Criteria

### AC-1: Column Name Normalisation
- **Given**: A dataset with column names containing uppercase letters, spaces, or special characters
- **When**: The user requests data cleaning with `normalize_columns: true`
- **Then**: All column names are converted to lowercase, stripped of whitespace, and spaces are replaced with underscores

### AC-2: Empty Row Removal
- **Given**: A dataset containing rows where all values are null/empty
- **When**: The user requests data cleaning with `remove_empty_rows: true`
- **Then**: All completely empty rows are removed from the dataset

### AC-3: Empty Column Removal
- **Given**: A dataset containing columns where all values are null/empty
- **When**: The user requests data cleaning with `remove_empty_columns: true`
- **Then**: All completely empty columns are removed from the dataset

### AC-4: Missing Value Detection
- **Given**: A dataset with missing values in various columns
- **When**: The user requests data cleaning (any operation)
- **Then**: A summary of missing values per column is included in the cleaning log

### AC-5: Smart Missing Value Filling
- **Given**: A dataset with missing values in numeric and categorical columns
- **When**: The user requests data cleaning with `smart_fill_missing: true`
- **Then**: Numeric columns are filled with median values and categorical columns are filled with mode or 'Unknown'

### AC-6: Automatic Type Detection
- **Given**: A dataset with date-like strings in object columns
- **When**: The user requests data cleaning with `auto_detect_types: true`
- **Then**: Date columns are converted to datetime type and numeric strings are converted to appropriate numeric types

### AC-7: Duplicate Detection and Removal
- **Given**: A dataset with duplicate rows
- **When**: The user requests data cleaning with `drop_duplicates: true`
- **Then**: Duplicate rows are removed and the count is logged

### AC-8: Cleaning Operation Log
- **Given**: Any data cleaning operation is performed
- **When**: The cleaning operation completes
- **Then**: A detailed log of all operations performed with counts and details is returned

## API Contract

### Endpoint: `POST /api/cleaning/enhanced`

**Request:**
```json
{
  "file_id": "string - required - UUID of uploaded file",
  "normalize_columns": "boolean - optional - default: false - Normalize column names",
  "remove_empty_rows": "boolean - optional - default: true - Remove rows with all null values",
  "remove_empty_columns": "boolean - optional - default: true - Remove columns with all null values",
  "drop_duplicates": "boolean - optional - default: true - Remove duplicate rows",
  "drop_na": "boolean - optional - default: false - Remove rows with any missing values",
  "smart_fill_missing": "boolean - optional - default: false - Smart fill missing values",
  "auto_detect_types": "boolean - optional - default: false - Auto-detect and convert data types",
  "fill_na": "object - optional - Manual fill values per column {column: value}",
  "columns_to_drop": "array - optional - List of column names to drop"
}
```

**Response (Success - 200):**
```json
{
  "file_id": "string - File identifier",
  "rows_before": "integer - Original row count",
  "rows_after": "integer - Final row count",
  "columns_before": "integer - Original column count",
  "columns_after": "integer - Final column count",
  "operations_log": [
    {
      "operation": "string - Operation name",
      "details": "string - Operation details",
      "affected_count": "integer - Number of items affected"
    }
  ],
  "column_changes": {
    "renamed": "object - Old name to new name mapping",
    "dropped": "array - List of dropped columns",
    "type_converted": "object - Column to new type mapping"
  },
  "missing_values_summary": {
    "before": "object - Missing values per column before cleaning",
    "after": "object - Missing values per column after cleaning"
  },
  "message": "string - Summary message"
}
```

**Response (Error - 404):**
```json
{
  "error": "File not found",
  "detail": "The specified file_id does not exist"
}
```

**Response (Error - 500):**
```json
{
  "error": "Cleaning error",
  "detail": "Detailed error message"
}
```

## Test Cases

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Normalize column names | Columns: "First Name", "LAST NAME", " Age " | Columns: "first_name", "last_name", "age" |
| TC-2 | Remove empty rows | DataFrame with 3 rows, 1 fully empty | 2 rows remaining, log shows 1 removed |
| TC-3 | Remove empty columns | DataFrame with 3 cols, 1 fully null | 2 columns remaining, log shows 1 removed |
| TC-4 | Smart fill numeric | Column with [1, 2, NaN, 4] | Column with [1, 2, 2.0, 4] (median fill) |
| TC-5 | Smart fill categorical | Column with ["A", "A", NaN, "B"] | Column with ["A", "A", "A", "B"] (mode fill) |
| TC-6 | Auto-detect date | Column with ["2023-01-01", "2023-02-01"] as strings | Column converted to datetime |
| TC-7 | Duplicate removal | DataFrame with 5 rows, 2 duplicates | 3 rows remaining |
| TC-8 | Combined operations | All operations enabled | All transformations applied, full log returned |
| TC-9 | File not found | Invalid file_id | 404 error |
| TC-10 | Empty dataframe | DataFrame with 0 rows | Appropriate handling, no errors |

## Dependencies
- `pandas`: DataFrame operations
- `app.utils`: `get_dataframe`, `update_dataframe` for file storage
- `app.models`: Pydantic models for request/response validation

## Notes
- The enhanced cleaning service is backward compatible - the original `/cleaning/` endpoint remains unchanged
- Column name normalization replaces spaces with underscores and special characters with empty strings
- Smart fill uses median for numeric types and mode (most frequent value) for categorical types
- Type detection checks column names for patterns like 'date', 'time', 'created', 'updated'
- The operations log provides an audit trail for all cleaning actions
- All cleaning operations are atomic - if any operation fails, changes are not persisted
