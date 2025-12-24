# Backend Services Summary

This document provides an overview of all services in `adaptiva-be/app/services/`.

---

## Quick Reference

| Service | Primary Function | Key Endpoints |
|---------|------------------|---------------|
| `upload_service` | File upload & parsing | `POST /upload` |
| `preview_service` | Excel-aware data preview | `POST /preview` |
| `cleaning_service` | Data cleaning & transformation | `POST /cleaning` |
| `chart_service` | Manual Plotly chart generation | `POST /charts/` |
| `ai_chart_service` | AI-powered chart generation | `POST /charts/ai` |
| `insights_service` | Dataset analysis & statistics | `GET /insights` |
| `ml_service` | Machine learning model training | `POST /ml/train` |
| `export_service` | Export to CSV/PDF/PPTX | `POST /export` |
| `auth_service` | JWT authentication | `POST /auth/*` |
| `rate_limit_service` | Anonymous user rate limiting | (internal) |

---

## 1. Upload Service (`upload_service.py`)

**Purpose:** Handle file uploads (CSV, XLSX, XLS) and store data for processing.

### Key Functions

| Function | Description |
|----------|-------------|
| `process_file_upload(file)` | Main upload handler - reads file, detects headers, stores in memory |
| `get_excel_sheet_names(content)` | Extract sheet names from Excel files |
| `_detect_and_apply_header(df)` | Smart header row detection with confidence scoring |

### Features
- **Multi-sheet Excel support:** Loads ALL sheets into memory with composite keys (`file_id:sheet_name`)
- **Smart header detection:** Uses `HeaderDetector` with configurable confidence threshold (0.7)
- **Supported formats:** CSV, XLSX, XLS
- **Validation:** Empty file detection, sheet validation

### Response
```python
FileUploadResponse(
    file_id: str,
    filename: str,
    rows: int,
    columns: int,
    column_names: List[str],
    sheets: Optional[List[str]],     # Excel only
    active_sheet: Optional[str],     # Excel only
    header_row: Optional[int],       # Detected header row index
    header_confidence: Optional[float]
)
```

---

## 2. Preview Service (`preview_service.py`)

**Purpose:** Generate formatted data previews with Excel-style cell formatting.

### Key Functions

| Function | Description |
|----------|-------------|
| `get_formatted_preview(request)` | Main preview handler |
| `format_excel_cell_value(cell)` | Format cell values to match Excel display |

### Features
- **Excel formatting preservation:** Handles percentages, currencies, dates, times, scientific notation
- **Sheet switching:** Uses composite keys for instant sheet changes
- **Row limiting:** Configurable `max_rows` for preview
- **Currency support:** USD ($), EUR (€), GBP (£)

### Response
```python
PreviewResponse(
    file_id: str,
    headers: List[str],
    data: List[Dict[str, str]],      # Formatted cell values as strings
    total_rows: int,
    preview_rows: int,
    formatted: bool,
    sheet_name: Optional[str],
    available_sheets: Optional[List[str]]
)
```

---

## 3. Cleaning Service (`cleaning_service.py`)

**Purpose:** Comprehensive data cleaning with Excel Copilot-like features.

### Key Functions

| Function | Description |
|----------|-------------|
| `clean_data(request)` | Main cleaning orchestrator |
| `_normalize_column_name(name)` | Convert to snake_case, remove special chars |
| `_try_convert_to_datetime(series)` | Auto-detect and convert date columns |
| `_try_convert_to_numeric(series)` | Auto-detect and convert numeric columns |

### Cleaning Operations (Configurable)
- `normalize_columns` - Clean column names (lowercase, underscores)
- `remove_empty_rows` - Drop rows that are entirely empty
- `remove_empty_columns` - Drop columns that are entirely empty
- `fill_missing` - Smart missing value filling (mode for categorical, median for numeric)
- `detect_types` - Auto-detect and convert column types
- `remove_duplicates` - Remove duplicate rows

### Features
- **Operation logging:** Detailed log of what was changed
- **Per-column tracking:** Reports changes per column
- **Missing value summary:** Before/after missing value counts
- **Composite key support:** Works with Excel sheet-specific data

### Response
```python
DataCleaningResponse(
    file_id: str,
    rows_before: int,
    rows_after: int,
    columns_before: int,
    columns_after: int,
    operations_performed: List[CleaningOperation],
    column_changes: List[ColumnChanges],
    missing_values: MissingValuesSummary,
    preview_data: List[Dict],
    headers: List[str]
)
```

---

## 4. Chart Service (`chart_service.py`)

**Purpose:** Generate Plotly charts from manual configuration.

### Key Functions

| Function | Description |
|----------|-------------|
| `generate_chart(request)` | Create Plotly chart from user-specified parameters |

### Supported Chart Types
| Type | Required Columns | Optional |
|------|------------------|----------|
| `bar` | x_column, y_column | color_column |
| `line` | x_column, y_column | color_column |
| `scatter` | x_column, y_column | color_column |
| `histogram` | x_column | color_column |
| `box` | x_column | y_column, color_column |
| `pie` | x_column | y_column (values) |

### Features
- **Plotly Express:** Uses `px.bar()`, `px.line()`, etc.
- **Color grouping:** Optional `color_column` for data segmentation
- **Timeout protection:** Wrapped with `@with_timeout(CHART_GENERATION_TIMEOUT)`
- **Column validation:** Checks columns exist before processing

### Response
```python
ChartGenerationResponse(
    chart_json: Dict,    # Full Plotly JSON (data + layout)
    message: str
)
```

---

## 5. AI Chart Service (`ai_chart_service.py`)

**Purpose:** Generate charts using OpenAI to write Plotly code.

### Key Functions

| Function | Description |
|----------|-------------|
| `generate_ai_chart(request)` | Main AI chart generation handler |
| `_get_dataframe_schema(df)` | Generate schema for AI context |
| `_clean_column_names(df)` | Sanitize column names for code generation |
| `_execute_chart_code(code, df)` | Sandboxed execution with RestrictedPython |
| `_extract_chart_settings(code)` | Parse generated code for chart config |

### Features
- **Sandboxed execution:** Uses `RestrictedPython` for safe code execution
- **Schema-aware:** Sends column types, sample data to AI
- **Code extraction:** Returns generated Python code for transparency
- **Settings extraction:** Attempts to parse chart config from generated code
- **Custom prompts:** Supports `user_instructions` and `base_prompt`

### Security
- No file operations, network calls, or system commands allowed
- Limited imports: pandas, numpy, plotly.express, plotly.graph_objects
- Execution timeout protection

### Response
```python
AIChartGenerationResponse(
    chart_json: Dict,           # Plotly JSON
    generated_code: str,        # The Python code that was executed
    explanation: str,           # AI's explanation of the chart
    message: str,
    chart_settings: Optional[ChartSettings]  # Extracted config
)
```

---

## 6. Insights Service (`insights_service.py`)

**Purpose:** Generate statistical insights about datasets.

### Key Functions

| Function | Description |
|----------|-------------|
| `get_data_insights(file_id)` | Analyze dataset and return statistics |

### Insights Generated
- **Column info:** dtype, non-null count, null count, unique values
- **Numerical summary:** mean, std, min, 25%, 50%, 75%, max
- **Missing values:** Per-column missing value counts
- **Duplicates:** Total duplicate row count

### Response
```python
DataInsightsResponse(
    file_id: str,
    rows: int,
    columns: int,
    column_info: Dict[str, ColumnInfo],
    numerical_summary: Dict[str, NumericStats],
    missing_values: Dict[str, int],
    duplicates_count: int
)
```

---

## 7. ML Service (`ml_service.py`)

**Purpose:** Train basic machine learning models on uploaded data.

### Key Functions

| Function | Description |
|----------|-------------|
| `train_ml_model(request)` | Train model and return metrics |

### Supported Models
| Model Type | Algorithm | Use Case |
|------------|-----------|----------|
| `linear_regression` | `sklearn.LinearRegression` | Continuous target prediction |
| `decision_tree` | `sklearn.DecisionTreeRegressor` | Non-linear regression |

### Features
- **Auto-encoding:** Handles categorical variables via label encoding
- **Train/test split:** Configurable `test_size` (default 0.2)
- **Missing value handling:** Drops rows with NaN
- **Feature importance:** Returns coefficients/importances when available

### Metrics Returned
- MSE (Mean Squared Error)
- RMSE (Root Mean Squared Error)
- MAE (Mean Absolute Error)
- R² Score

### Response
```python
MLModelResponse(
    model_type: str,
    target_column: str,
    feature_columns: List[str],
    metrics: Dict[str, float],
    feature_importance: Optional[Dict[str, float]],
    predictions_sample: List[float]
)
```

---

## 8. Export Service (`export_service.py`)

**Purpose:** Export data to various formats (CSV, PDF, PPTX).

### Key Functions

| Function | Description |
|----------|-------------|
| `export_data(request)` | Export to CSV/Excel |
| `export_to_pdf(request)` | Generate PDF report with ReportLab |
| `export_to_pptx(request)` | Generate PowerPoint presentation |

### PDF Export Features
- Title page with branding
- Dataset information (rows, columns)
- Column information table
- Missing values summary (if any)
- Numerical statistics tables
- Optional insights inclusion

### PPTX Export Features
- Title slide
- Dataset overview slide
- Column details
- Statistics summary
- Professional formatting with proper sizing

### Response
```python
# Returns file path for download
str  # Path to generated file
```

---

## 9. Auth Service (`auth_service.py`)

**Purpose:** Handle user authentication with JWT tokens.

### Key Functions

| Function | Description |
|----------|-------------|
| `hash_password(password)` | Bcrypt password hashing |
| `verify_password(plain, hashed)` | Password verification |
| `create_access_token(user_id, email)` | Short-lived JWT (configurable minutes) |
| `create_refresh_token(user_id)` | Long-lived refresh token (configurable days) |
| `decode_token(token)` | Validate and decode JWT |
| `validate_access_token(token)` | Verify access token type |
| `validate_refresh_token(token, db)` | Check refresh token + blacklist |

### Token Structure
```python
# Access Token Payload
{
    "sub": user_id,
    "email": email,
    "exp": expiration,
    "iat": issued_at,
    "type": "access"
}

# Refresh Token Payload
{
    "sub": user_id,
    "exp": expiration,
    "iat": issued_at,
    "jti": unique_token_id,  # For blacklisting
    "type": "refresh"
}
```

### Security Features
- Bcrypt password hashing
- JWT with configurable expiration
- Refresh token rotation
- Token blacklisting support

---

## 10. Rate Limit Service (`rate_limit_service.py`)

**Purpose:** Rate limiting for anonymous users on AI endpoints.

### Key Functions

| Function | Description |
|----------|-------------|
| `create_anonymous_session()` | Generate signed session token |
| `validate_anonymous_session(token)` | Verify session token signature |
| `get_ip_usage_count(ip)` | Get today's request count for IP |
| `get_session_usage_count(session_id)` | Get today's request count for session |
| `increment_usage(ip, session_id)` | Increment both counters |
| `check_rate_limit(ip, session_id)` | Check if limit exceeded |

### Rate Limiting Strategy
- **Dual tracking:** Both IP and session-based limits
- **Rolling window:** 24-hour reset
- **Configurable limits:** Via `settings.ANONYMOUS_DAILY_LIMIT`
- **Signed tokens:** HMAC-SHA256 signed session tokens

### Storage
- **Current:** In-memory with automatic cleanup
- **Production recommendation:** Redis

### Session Token Format
```
{base64_payload}.{base64_signature}

Payload: {"sid": "uuid", "iat": "iso_timestamp"}
```

---

## Service Dependencies

```
upload_service
    └── utils/storage (store_dataframe, store_file_content)
    └── utils/header_detection (HeaderDetector)

preview_service
    └── utils/storage (get_file_content)
    └── openpyxl (Excel formatting)

cleaning_service
    └── utils/storage (get_dataframe, update_dataframe)

chart_service
    └── utils/storage (get_dataframe)
    └── plotly.express

ai_chart_service
    └── utils/storage (get_dataframe)
    └── openai (OpenAI API)
    └── RestrictedPython (sandboxed execution)
    └── plotly (express + graph_objects)

insights_service
    └── utils/storage (get_dataframe)

ml_service
    └── utils/storage (get_dataframe)
    └── sklearn (LinearRegression, DecisionTreeRegressor)

export_service
    └── utils/storage (get_dataframe)
    └── insights_service (for PDF insights)
    └── reportlab (PDF)
    └── python-pptx (PPTX)

auth_service
    └── bcrypt
    └── python-jose (JWT)
    └── database (User, TokenBlacklist models)

rate_limit_service
    └── config (settings)
    └── (in-memory storage)
```

---

## Configuration

Services use settings from `app/config.py`:

| Setting | Used By | Description |
|---------|---------|-------------|
| `JWT_SECRET_KEY` | auth_service | JWT signing key |
| `JWT_ALGORITHM` | auth_service | Usually "HS256" |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | auth_service | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | auth_service | Refresh token TTL |
| `ANONYMOUS_SESSION_SECRET` | rate_limit_service | Session token signing |
| `ANONYMOUS_DAILY_LIMIT` | rate_limit_service | Max AI requests/day |
| `OPENAI_API_KEY` | ai_chart_service | OpenAI API key |
| `CHART_GENERATION_TIMEOUT` | chart/ai_chart | Timeout in seconds |
