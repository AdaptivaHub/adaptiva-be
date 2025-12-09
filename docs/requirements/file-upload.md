# Feature: File Upload

## Overview
Allow users to upload CSV and Excel (XLSX/XLS) files for data analysis. The system parses the file, validates the content, stores it for subsequent operations, and returns metadata about the uploaded file.

## User Story
As a data analyst,
I want to upload my data files (CSV or Excel),
So that I can analyze, visualize, and export insights from my data.

## Acceptance Criteria

### AC-1: CSV File Upload
- **Given**: A valid CSV file
- **When**: The file is uploaded via POST /api/upload
- **Then**: The file is parsed, stored, and a file_id is returned with metadata

### AC-2: Excel File Upload
- **Given**: A valid XLSX or XLS file
- **When**: The file is uploaded via POST /api/upload
- **Then**: The file is parsed (first sheet by default), stored, and a file_id is returned with metadata including available sheet names

### AC-3: File Validation - Format
- **Given**: A file with an unsupported format (e.g., .txt, .pdf)
- **When**: The file is uploaded
- **Then**: A 400 error is returned with message "Unsupported file format"

### AC-4: File Validation - Empty File
- **Given**: An empty CSV or Excel file (no data rows)
- **When**: The file is uploaded
- **Then**: A 400 error is returned with message "The uploaded file is empty"

### AC-5: File Validation - Corrupted File
- **Given**: A corrupted or malformed file
- **When**: The file is uploaded
- **Then**: A 400 error is returned with details about the parsing error

### AC-6: File Size Limit
- **Given**: A file larger than the maximum allowed size
- **When**: The file is uploaded
- **Then**: A 400 error is returned (handled by FastAPI/server config)

### AC-7: Metadata Response
- **Given**: A successful file upload
- **When**: The response is received
- **Then**: It includes file_id, filename, row count, column count, and column names

### AC-8: Multi-Sheet Detection (Excel)
- **Given**: An Excel file with multiple worksheets is uploaded
- **When**: The file is successfully processed
- **Then**: The response includes a list of all sheet names and indicates which sheet was used for the initial metadata

## API Contract

### Endpoint: `POST /api/upload/`

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` - The CSV or XLSX file

**Response (Success - 200):**
```json
{
  "file_id": "uuid-string",
  "filename": "data.csv",
  "rows": 1500,
  "columns": 10,
  "column_names": ["id", "name", "value", "date", ...],
  "message": "File uploaded successfully",
  "sheets": ["Sheet1", "Sheet2", "Sheet 3", ...],
  "active_sheet": "Sheet1"
}
```

> **Note**: `sheets` and `active_sheet` are only included for Excel files. For CSV files, these fields are `null`.

**Response (Error - 400):**
```json
{
  "detail": "Unsupported file format. Only CSV and XLSX files are supported."
}
```

```json
{
  "detail": "The uploaded file is empty"
}
```

```json
{
  "detail": "Error reading file: [specific error message]"
}
```

## Test Cases

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Valid CSV upload | CSV file with headers and data | 200, file_id and metadata |
| TC-2 | Valid XLSX upload | Excel file with data | 200, file_id and metadata |
| TC-3 | Empty CSV | CSV with only headers | 400, "file is empty" |
| TC-4 | Empty Excel | Empty worksheet | 400, "file is empty" |
| TC-5 | Unsupported format | .txt file | 400, "Unsupported file format" |
| TC-6 | Corrupted file | Invalid binary data with .csv extension | 400, parsing error |
| TC-7 | Large file | File with 100k+ rows | 200, processes successfully |
| TC-8 | Special characters in headers | Headers with spaces, unicode | 200, headers preserved |
| TC-9 | Mixed data types | Columns with mixed string/number | 200, parsed correctly |
| TC-10 | XLS format | Old Excel format (.xls) | 200, file_id and metadata |
| TC-11 | Multi-sheet Excel | XLSX with 3 sheets | 200, sheets array with 3 names |
| TC-12 | Single-sheet Excel | XLSX with 1 sheet | 200, sheets array with 1 name |

## Data Storage

After upload, the system stores:
1. **Parsed DataFrame** - In memory for quick access during analysis
2. **Original file content** - For formatted preview (preserving Excel formatting)

Storage is keyed by `file_id` (UUID) which is used in all subsequent operations.

## Dependencies
- pandas: For CSV and Excel parsing
- openpyxl: For XLSX file support
- python-multipart: For file upload handling

## Performance Considerations
- Files are read into memory; consider streaming for very large files
- DataFrame storage is in-memory (not persistent across restarts)
- Consider Redis or database storage for production

## Notes
- The first row of the file is assumed to be headers
- Column names are preserved as-is (including spaces and special characters)
- The file_id is valid only for the current server session (in-memory storage)
