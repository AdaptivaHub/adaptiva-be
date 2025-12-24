# Services

This directory contains all business logic services for the Adaptiva backend. Services are organized by domain and handle specific aspects of the data visualization pipeline.

---

## Overview

| Service | Description |
|---------|-------------|
| [`upload_service`](#upload-service) | File upload processing and multi-sheet Excel support |
| [`preview_service`](#preview-service) | Excel-aware data preview with formatting preservation |
| [`cleaning_service`](#cleaning-service) | Data cleaning and transformation |
| [`chart_render_service`](#chart-render-service) | ChartSpec → Plotly JSON rendering |
| [`chart_validation`](#chart-validation) | ChartSpec validation against data |
| [`ai_suggest_service`](#ai-suggest-service) | LLM-powered chart suggestions |
| [`insights_service`](#insights-service) | Dataset analysis and statistics |
| [`ml_service`](#ml-service) | Machine learning model training |
| [`export_service`](#export-service) | Export to PDF/PPTX formats |
| [`auth_service`](#auth-service) | JWT authentication and password management |
| [`rate_limit_service`](#rate-limit-service) | Anonymous user rate limiting |

---

## Upload Service

**File:** `upload_service.py`

Handles file uploads (CSV, XLSX, XLS) and stores data for processing.

### Key Functions

- `process_file_upload(file)` - Main upload handler that reads files, detects headers, and stores in memory
- `get_excel_sheet_names(content)` - Extracts sheet names from Excel files
- `_detect_and_apply_header(df)` - Smart header row detection with confidence scoring

### Features

- **Multi-sheet Excel support**: Loads ALL sheets into memory with composite keys (`file_id:sheet_name`)
- **Smart header detection**: Uses `HeaderDetector` with configurable confidence threshold (0.7)
- **Supported formats**: CSV, XLSX, XLS
- **Validation**: Empty file detection, sheet validation

---

## Preview Service

**File:** `preview_service.py`

Generates formatted data previews with Excel-style cell formatting.

### Key Functions

- `get_formatted_preview(request)` - Main preview handler
- `format_excel_cell_value(cell)` - Formats cell values to match Excel display

### Features

- **Excel formatting preservation**: Handles percentages, currencies, dates, times, scientific notation
- **Sheet switching**: Uses composite keys for instant sheet changes
- **Row limiting**: Configurable `max_rows` for preview
- **Currency support**: USD ($), EUR (€), GBP (£)

---

## Cleaning Service

**File:** `cleaning_service.py`

Comprehensive data cleaning with Excel Copilot-like features.

### Key Functions

- `clean_data(request)` - Main cleaning orchestrator
- `_normalize_column_name(name)` - Converts to snake_case, removes special characters

### Features

- **Column name normalization**: Lowercase, replace spaces with underscores
- **Empty row/column removal**: Automatic cleanup of empty data
- **Smart missing value detection and filling**: Intelligent fill strategies
- **Automatic type detection**: Date, numeric, and string type inference
- **Duplicate removal**: Identifies and removes duplicate rows
- **Comprehensive operation logging**: Tracks all changes made

---

## Chart Render Service

**File:** `chart_render_service.py`

Converts `ChartSpec` objects to Plotly JSON. This is the **single render path** for all charts (manual and AI-generated).

### Key Functions

- `render_chart(spec)` - Main render function, converts ChartSpec → Plotly JSON
- `apply_filters(df, spec)` - Applies filter conditions to dataframe
- `apply_aggregation(df, spec)` - Applies grouping and aggregation
- `build_plotly_figure(df, spec)` - Builds Plotly figure from data and spec
- `apply_styling(fig, spec)` - Applies color palettes, themes, and styling

### Supported Chart Types

- `bar` - Bar charts (grouped/stacked)
- `line` - Line charts
- `scatter` - Scatter plots (with optional bubble size)
- `histogram` - Histograms
- `box` - Box plots
- `pie` - Pie charts
- `area` - Area charts
- `heatmap` - Heatmaps

### Filter Operators

`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `between`, `contains`

---

## Chart Validation

**File:** `chart_validation.py`

Validates `ChartSpec` objects against the actual data.

### Key Functions

- `validate_chart_spec(spec, df)` - Main validation function
- `validate_columns_exist(spec, df)` - Checks all referenced columns exist
- `validate_chart_type_requirements(spec, df)` - Validates chart-type-specific requirements

### Validation Checks

- Column existence in dataframe
- Chart-type-specific requirements (e.g., y-axis for bar/line charts)
- Column type compatibility
- Filter column validation

### Result

Returns `ValidationResult` with:
- `valid: bool` - Whether spec is valid
- `errors: List[ValidationError]` - Blocking errors
- `warnings: List[ValidationError]` - Non-blocking warnings

---

## AI Suggest Service

**File:** `ai_suggest_service.py`

Generates ChartSpec suggestions using LLM (GPT-4o-mini).

### Key Functions

- `generate_chart_suggestion(request)` - Main entry point for AI suggestions
- `get_openai_client()` - Lazy initialization of OpenAI client

### Key Principle

**AI generates ChartSpec JSON, NOT executable code.** The LLM outputs a structured JSON object that is then validated and rendered through the standard pipeline.

### Features

- Extracts data schema from uploaded files
- Builds context-aware prompts for the LLM
- Parses LLM responses into validated ChartSpec
- Tracks usage for billing

### Configuration

- **Model**: `gpt-4o-mini`
- **Temperature**: 0.3 (lower for deterministic output)
- **Max Tokens**: 1500

---

## Insights Service

**File:** `insights_service.py`

Generates basic insights and statistics about datasets.

### Key Functions

- `get_data_insights(file_id)` - Generates comprehensive dataset insights

### Returns

- **Column information**: Data types, null counts, unique values
- **Numerical summary**: Mean, std, min, max, quartiles
- **Missing values**: Count per column
- **Duplicates count**: Number of duplicate rows

---

## ML Service

**File:** `ml_service.py`

Trains machine learning models on uploaded data.

### Key Functions

- `train_ml_model(request)` - Trains a model and returns metrics

### Supported Models

- **Linear Regression**: `MLModelType.LINEAR_REGRESSION`
- **Decision Tree**: `MLModelType.DECISION_TREE`

### Features

- Automatic train/test split
- Handles categorical variables with label encoding
- Automatic removal of rows with NaN values
- Returns comprehensive metrics:
  - MSE (Mean Squared Error)
  - RMSE (Root Mean Squared Error)
  - MAE (Mean Absolute Error)
  - R² Score
- Feature importance (where available)

---

## Export Service

**File:** `export_service.py`

Exports data and charts to various formats.

### Key Functions

- `export_to_pdf(request)` - Exports data to PDF format
- `export_to_pptx(request)` - Exports data to PowerPoint format
- `export_data(request)` - General export handler

### Features

- **PDF Export**: Uses ReportLab for professional PDF generation
  - Dataset information
  - Column statistics tables
  - Optional insights inclusion
  - Missing values summary

---

## Auth Service

**File:** `auth_service.py`

Handles JWT token management and password hashing.

### Key Functions

- `verify_password(plain, hashed)` - Verifies password against hash
- `hash_password(password)` - Hashes password using bcrypt
- `create_access_token(user_id, email)` - Creates short-lived access token
- `create_refresh_token(user_id)` - Creates long-lived refresh token with JTI
- `decode_token(token)` - Decodes and validates JWT
- `validate_access_token(token)` - Validates access token type
- `validate_refresh_token(token, db)` - Validates refresh token and checks blacklist

### Security Features

- **bcrypt** password hashing
- **JWT** tokens with configurable expiration
- Access/Refresh token separation
- Token blacklisting support
- Unique token IDs (JTI) for refresh tokens

---

## Rate Limit Service

**File:** `rate_limit_service.py`

Rate limiting for anonymous AI requests using in-memory storage.

### Key Functions

- `create_anonymous_session()` - Creates signed anonymous session token
- `validate_anonymous_session(token)` - Validates session token signature
- `check_rate_limit(session_id, ip)` - Checks if request is allowed
- `increment_usage(session_id, ip)` - Increments usage counter

### Features

- **Signed tokens**: HMAC-SHA256 signed session tokens
- **In-memory storage**: Fast lookup with automatic cleanup
- **Per-session limits**: Tracks usage per anonymous session
- **IP-based burst protection**: Prevents rapid-fire requests
- **Global daily limits**: System-wide rate limiting
- **Automatic expiration**: Cleans up expired entries

### Configuration (via settings)

- Session limits per time window
- Global daily maximum
- Burst window and limits

---

## Usage

All services are exported from `__init__.py`:

```python
from app.services import (
    process_file_upload,
    clean_data,
    get_data_insights,
    render_chart,
    ChartRenderError,
    validate_chart_spec,
    ValidationResult,
    ValidationError,
    generate_chart_suggestion,
    AISuggestError,
    train_ml_model,
    export_data,
    export_to_pdf,
    export_to_pptx,
    get_formatted_preview,
    auth_service,
    rate_limit_service,
)
```

---

## Error Handling

Each service defines its own exception classes:

- `ChartRenderError` - Chart rendering failures (includes list of validation errors)
- `AISuggestError` - AI suggestion failures (includes error code)
- Standard `HTTPException` - For request validation errors

---

## Dependencies

- **pandas** - Data manipulation
- **plotly** - Chart generation
- **openpyxl** - Excel file handling
- **scikit-learn** - Machine learning
- **openai** - LLM integration
- **bcrypt** - Password hashing
- **python-jose** - JWT handling
- **reportlab** - PDF generation
