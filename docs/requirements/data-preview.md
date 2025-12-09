# Feature: Data Preview

## Overview
The Data Preview feature allows users to retrieve a formatted preview of uploaded data files (CSV and Excel). It preserves Excel formatting such as dates, currencies, percentages, and number formats, providing users with an accurate representation of their data before further processing.

## User Story
As a data analyst,
I want to preview my uploaded data with proper formatting preserved,
So that I can verify the data was imported correctly and understand its structure before performing analysis.

## Acceptance Criteria

### AC-1: Preview Uploaded File
- **Given**: A file has been successfully uploaded and a valid file_id exists
- **When**: The user requests a preview with the file_id
- **Then**: The system returns the first 100 rows (default) with headers and formatted data

### AC-2: Configurable Row Limit
- **Given**: A file has been uploaded
- **When**: The user requests a preview with a custom max_rows parameter (1-1000)
- **Then**: The system returns up to the specified number of rows

### AC-3: Excel Formatting Preservation
- **Given**: An Excel file (.xlsx/.xls) has been uploaded with formatted cells
- **When**: The user requests a preview
- **Then**: The system preserves formatting for:
  - Dates (displayed as MM/DD/YYYY)
  - Times (displayed as HH:MM:SS)
  - DateTime (displayed as MM/DD/YYYY HH:MM:SS)
  - Percentages (e.g., 50.00%)
  - Currency (USD $, EUR €, GBP £)
  - Comma-separated numbers
  - Scientific notation

### AC-4: CSV File Support
- **Given**: A CSV file has been uploaded
- **When**: The user requests a preview
- **Then**: The system returns the data with basic formatting (integers vs floats, empty string for NA values)

### AC-5: File Not Found Handling
- **Given**: An invalid or expired file_id is provided
- **When**: The user requests a preview
- **Then**: The system returns a 404 error with an appropriate message

### AC-6: Unsupported File Format Handling
- **Given**: A file with an unsupported format is referenced
- **When**: The user requests a preview
- **Then**: The system returns a 400 error indicating the unsupported format

### AC-7: Sheet Selection (Excel)
- **Given**: An Excel file with multiple sheets has been uploaded
- **When**: The user requests a preview with a specific sheet_name parameter
- **Then**: The system returns preview data for the specified sheet

### AC-8: Default Sheet Behavior (Excel)
- **Given**: An Excel file with multiple sheets has been uploaded
- **When**: The user requests a preview without specifying a sheet_name
- **Then**: The system returns preview data for the first (active) sheet

### AC-9: Invalid Sheet Name Handling
- **Given**: An Excel file has been uploaded
- **When**: The user requests a preview with a non-existent sheet_name
- **Then**: The system returns a 400 error with message indicating the sheet was not found

## API Contract

### Endpoint: `POST /preview/`

**Request:**
```json
{
  "file_id": "string - Required. The ID of the uploaded file",
  "max_rows": "integer - Optional. Maximum rows to return (default: 100, min: 1, max: 1000)",
  "sheet_name": "string - Optional. Name of the sheet to preview (Excel only, defaults to first sheet)"
}
```

**Response (Success - 200):**
```json
{
  "file_id": "string - The ID of the file",
  "headers": ["string"] ,
  "data": [
    {
      "column_name": "string - Formatted cell value"
    }
  ],
  "total_rows": "integer - Total rows in the file (excluding header)",
  "preview_rows": "integer - Number of rows returned in this preview",
  "formatted": "boolean - Whether Excel formatting was preserved",
  "sheet_name": "string - The sheet being previewed (Excel only, null for CSV)",
  "available_sheets": ["string"] ,
  "message": "string - Success message"
}
```

**Response (Error - 404):**
```json
{
  "error": "string",
  "detail": "File with ID {file_id} not found"
}
```

**Response (Error - 400):**
```json
{
  "error": "string",
  "detail": "Error generating preview: {error_message}"
}
```

```json
{
  "error": "string",
  "detail": "Sheet '{sheet_name}' not found. Available sheets: [...]"
}
```

## Test Cases

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Happy path - Excel file | Valid file_id for .xlsx | 200 with formatted data, `formatted: true` |
| TC-2 | Happy path - CSV file | Valid file_id for .csv | 200 with data, `formatted: false` |
| TC-3 | Custom row limit | `max_rows: 50` | Returns up to 50 rows |
| TC-4 | Maximum row limit | `max_rows: 1000` | Returns up to 1000 rows |
| TC-5 | Row limit validation - too low | `max_rows: 0` | 422 validation error |
| TC-6 | Row limit validation - too high | `max_rows: 1001` | 422 validation error |
| TC-7 | File not found | Invalid file_id | 404 error |
| TC-8 | Date formatting | Excel with date cells | Dates displayed as MM/DD/YYYY |
| TC-9 | Currency formatting | Excel with currency cells | Values prefixed with $, €, or £ |
| TC-10 | Percentage formatting | Excel with percentage cells | Values displayed as X.XX% |
| TC-11 | Empty cells | File with null/empty values | Empty strings in response |
| TC-12 | Boolean values | Excel with TRUE/FALSE | "TRUE" or "FALSE" strings |
| TC-13 | Scientific notation | Excel with scientific format | Values in X.XXE+XX format |
| TC-14 | Large numbers with commas | Excel with #,##0 format | Comma-separated numbers |
| TC-15 | Missing header cells | Excel with empty header | Default to "Column_N" naming |
| TC-16 | Preview specific sheet | `sheet_name: "Sheet2"` | Returns data from Sheet2 |
| TC-17 | Preview default sheet | No sheet_name provided | Returns data from first sheet |
| TC-18 | Invalid sheet name | `sheet_name: "NonExistent"` | 400 error with available sheets |
| TC-19 | Sheet selection for CSV | `sheet_name` with CSV file | Parameter ignored, returns CSV data |
| TC-20 | Available sheets in response | Multi-sheet Excel | `available_sheets` contains all sheet names |

## Dependencies
- **File Upload Service**: Requires a valid file_id from the upload endpoint
- **Storage Utility**: Uses `get_file_content()` to retrieve stored files
- **openpyxl**: For Excel file parsing and format detection
- **pandas**: For CSV file parsing

## Technical Implementation

### Supported File Formats
| Format | Extension | Formatting Preserved |
|--------|-----------|---------------------|
| Excel (OOXML) | .xlsx | Yes |
| Excel (Legacy) | .xls | Yes |
| CSV | .csv | No (basic type inference) |

### Excel Number Format Handling
The service interprets Excel number format codes to display values correctly:
- `%` → Percentage (value × 100 + %)
- `$#,##0.00` → US Dollar currency
- `€#,##0.00` → Euro currency
- `£#,##0.00` → British Pound currency
- `#,##0` → Comma-separated integers
- `0.00` → Two decimal places
- `E+00` → Scientific notation

## Notes
- The preview is read-only and does not modify the uploaded file
- Excel files are loaded with `data_only=False` to access formatting information
- For large files, only the requested number of rows are processed for the preview, but total_rows reflects the full file size
- CSV files do not have inherent formatting, so `formatted` will be `false` in the response
- All cell values are converted to strings in the response for consistent JSON serialization
- For Excel files, `sheet_name` parameter allows switching between sheets without re-uploading
- The `available_sheets` field enables frontend sheet selector UI components
- CSV files ignore the `sheet_name` parameter; `sheet_name` and `available_sheets` will be `null` in response
