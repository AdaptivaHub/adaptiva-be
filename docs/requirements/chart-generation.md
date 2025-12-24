# Feature: Chart Generation

## Overview
Generate interactive data visualizations using Plotly through a unified ChartSpec-based architecture.

## User Story
As a data analyst,
I want to create charts from my uploaded data,
So that I can visualize trends, patterns, and insights.

## Architecture

The chart generation system uses a **ChartSpec-centric architecture**:

1. **ChartSpec** - The canonical schema for all chart configurations
2. **Single Render Path** - All charts (manual and AI-generated) go through the same render service
3. **Validation Layer** - Pre-flight validation before rendering
4. **AI Suggestions** - AI generates ChartSpec JSON (not executable code)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Chart Editor   │────▶│   ChartSpec     │────▶│  Render Service │
│  (Frontend UI)  │     │   (JSON Schema) │     │  (Plotly JSON)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       ▲
        │                       │
┌───────┴───────┐     ┌─────────┴─────────┐
│ Manual Edits  │     │  AI Suggestions   │
│ (User Input)  │     │  (LLM → ChartSpec)│
└───────────────┘     └───────────────────┘
```

## Sub-Features

### 1. Chart Rendering (`POST /api/charts/render`)
Convert ChartSpec → Plotly JSON. Single render path for all charts.

### 2. Chart Validation (`POST /api/charts/validate`)
Pre-flight validation of ChartSpec against data. Returns errors and warnings.

### 3. AI Chart Suggestions (`POST /api/charts/suggest`)
AI analyzes data and generates a complete ChartSpec. Rate-limited for anonymous users.

---

## ChartSpec Schema

> **See also**: [ChartSpec Model Requirements](./chartspec-model.md) for detailed schema specification and model validation tests.

The ChartSpec is organized into 4 categories:

### 1. Data & Mapping
- `file_id` - Data source reference
- `sheet_name` - Optional Excel sheet name
- `chart_type` - Type of chart (bar, line, scatter, histogram, box, pie, area, heatmap)
- `x_axis` - X-axis column configuration
- `y_axis` - Y-axis column(s) configuration (supports multiple columns)
- `series` - Grouping/color configuration (group_column, size_column)
- `aggregation` - Data aggregation (method: none/sum/mean/count/median/min/max, group_by)
- `filters` - Data filtering with conditions and logic (and/or)

### 2. Visual Structure
- `visual.title` - Chart title
- `visual.stacking` - Stacking mode (grouped, stacked, percent)
- `visual.secondary_y_axis` - Enable secondary Y-axis
- `legend` - Legend visibility and position (top, bottom, left, right, none)

### 3. Interaction
- `interaction.zoom_scroll` - Enable scroll zoom
- `interaction.responsive` - Responsive sizing
- `interaction.modebar` - Toolbar display (always, hover, hidden)
- `interaction.export_formats` - Available export formats
- `interaction.tooltip_detail` - Tooltip detail level

### 4. Styling
- `styling.color_palette` - Color palette (default, vibrant, pastel, monochrome, colorblind_safe)
- `styling.theme` - Theme (light, dark)
- `styling.show_data_labels` - Show data labels on chart

---

## Chart Rendering

### Acceptance Criteria

#### AC-1: Supported Chart Types
- **Given**: A valid ChartSpec
- **When**: Render is requested
- **Then**: One of 8 chart types is generated: bar, line, scatter, histogram, box, pie, area, heatmap

#### AC-2: Multiple Y Columns
- **Given**: A ChartSpec with multiple y_axis.columns
- **When**: A bar or line chart is rendered
- **Then**: Multiple series/traces are displayed

#### AC-3: Data Filtering
- **Given**: A ChartSpec with filter conditions
- **When**: The chart is rendered
- **Then**: Only matching rows are included (supports: eq, ne, gt, gte, lt, lte, in, not_in, between, contains)

#### AC-4: Data Aggregation
- **Given**: A ChartSpec with aggregation settings
- **When**: The chart is rendered
- **Then**: Data is grouped and aggregated before charting

#### AC-5: Series Grouping
- **Given**: A ChartSpec with series.group_column
- **When**: The chart is rendered
- **Then**: Data is grouped and colored by the specified column

#### AC-6: Stacking Modes
- **Given**: A bar chart with visual.stacking
- **When**: The chart is rendered
- **Then**: Bars are grouped, stacked, or normalized to 100%

#### AC-7: Styling Presets
- **Given**: A ChartSpec with styling configuration
- **When**: The chart is rendered
- **Then**: Color palette and theme are applied

#### AC-8: Invalid File ID
- **Given**: A non-existent file_id in ChartSpec
- **When**: Render is requested
- **Then**: A 404 error is returned with error details

#### AC-9: Invalid Column Names
- **Given**: Column names that don't exist in the dataset
- **When**: Render is requested
- **Then**: A 400 error is returned with specific validation errors

### API Contract - Chart Rendering

#### Endpoint: `POST /api/charts/render`

**Request:**
```json
{
  "spec": {
    "file_id": "uuid-string",
    "sheet_name": "Sheet1",
    "chart_type": "bar",
    "x_axis": {
      "column": "category",
      "label": "Category"
    },
    "y_axis": {
      "columns": ["sales", "profit"],
      "label": "Amount ($)"
    },
    "series": {
      "group_column": "region"
    },
    "aggregation": {
      "method": "sum",
      "group_by": ["category", "region"]
    },
    "filters": {
      "conditions": [
        {"column": "year", "operator": "gte", "value": 2020}
      ],
      "logic": "and"
    },
    "visual": {
      "title": "Sales by Category",
      "stacking": "grouped"
    },
    "legend": {
      "visible": true,
      "position": "right"
    },
    "styling": {
      "color_palette": "default",
      "theme": "light",
      "show_data_labels": false
    },
    "version": "1.0"
  }
}
```

**Response (Success - 200):**
```json
{
  "chart_json": {
    "data": [...],
    "layout": {...}
  },
  "rendered_at": "2024-12-24T10:30:00Z",
  "spec_version": "1.0"
}
```

**Response (Error - 400):**
```json
{
  "detail": {
    "error": "Validation failed: 2 error(s)",
    "errors": [
      {
        "field": "x_axis.column",
        "code": "column_not_found",
        "message": "Column 'invalid_col' not found in data"
      },
      {
        "field": "y_axis",
        "code": "missing_required_field",
        "message": "Chart type 'bar' requires y_axis to be specified"
      }
    ]
  }
}
```

**Response (Error - 404):**
```json
{
  "detail": {
    "error": "File not found: xxx",
    "errors": [
      {"field": "file_id", "code": "file_not_found", "message": "..."}
    ]
  }
}
```

---

## Chart Validation

### Acceptance Criteria

#### AC-10: Pre-flight Validation
- **Given**: A ChartSpec
- **When**: Validation is requested
- **Then**: Errors and warnings are returned without rendering

#### AC-11: Column Existence Check
- **Given**: A ChartSpec referencing columns
- **When**: Validation runs
- **Then**: All x_axis, y_axis, series, filter, and aggregation columns are verified

#### AC-12: Chart Type Requirements
- **Given**: A chart type that requires y_axis (bar, line, scatter, area, heatmap)
- **When**: y_axis is missing
- **Then**: A validation error is returned

#### AC-13: Type Compatibility Warnings
- **Given**: A numeric chart with non-numeric y_axis columns
- **When**: Validation runs
- **Then**: A warning is returned (not an error)

### API Contract - Chart Validation

#### Endpoint: `POST /api/charts/validate`

**Request:**
```json
{
  "spec": { /* ChartSpec */ }
}
```

**Response (Success - 200):**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "field": "y_axis.columns",
      "code": "type_mismatch",
      "message": "Column 'category' is not numeric; chart may not render as expected",
      "suggestion": null
    }
  ]
}
```

```json
{
  "valid": false,
  "errors": [
    {
      "field": "x_axis.column",
      "code": "column_not_found",
      "message": "Column 'missing_col' not found in data",
      "suggestion": null
    }
  ],
  "warnings": []
}
```

---

## AI Chart Suggestions

### Overview

The AI suggestion service uses GPT-4o-mini to analyze data schema and generate a complete ChartSpec. 

**Key Principle**: AI generates ChartSpec JSON, NOT executable code. This eliminates security risks from code execution.

### Rate Limiting

Anonymous users are rate-limited:
- **3 requests per 24-hour rolling window** (per IP + session)
- **Burst protection**: Prevents rapid-fire requests
- **Global daily limit**: System-wide cap for cost control
- **Authenticated users**: Unlimited access

### Acceptance Criteria

#### AC-14: Automatic Chart Selection
- **Given**: A dataset without specific instructions
- **When**: AI suggestion is requested
- **Then**: AI analyzes data schema and suggests the best chart type

#### AC-15: User Instructions
- **Given**: User provides instructions like "Show sales trends over time"
- **When**: AI suggestion is requested
- **Then**: AI generates a ChartSpec matching the user's intent

#### AC-16: Complete ChartSpec Output
- **Given**: A successful AI suggestion
- **When**: The response is received
- **Then**: It includes a complete, validated ChartSpec

#### AC-17: Explanation & Confidence
- **Given**: A successful AI suggestion
- **When**: The response is received
- **Then**: It includes an explanation and confidence score (0-1)

#### AC-18: Alternative Suggestions
- **Given**: A successful AI suggestion
- **When**: Multiple chart types would work
- **Then**: Alternatives are provided with reasons

#### AC-19: Column Validation
- **Given**: AI generates a ChartSpec
- **When**: The response is processed
- **Then**: All column names are validated against the actual data

#### AC-20: Anonymous Session Tracking
- **Given**: An anonymous user makes a request
- **When**: No session token is provided
- **Then**: A signed session token is created and returned

#### AC-21: Rate Limit Exceeded
- **Given**: An anonymous user has used all daily requests
- **When**: Another request is made
- **Then**: A 429 error is returned with reset time and signup prompt

#### AC-22: Authenticated Bypass
- **Given**: A request with valid Bearer token
- **When**: AI suggestion is requested
- **Then**: Rate limits are bypassed

### API Contract - AI Suggestions

#### Endpoint: `POST /api/charts/suggest`

**Request:**
```json
{
  "file_id": "uuid-string",
  "sheet_name": "Sheet1",
  "user_instructions": "Show me sales trends over time by region",
  "current_spec": null
}
```

**Response (Success - 200):**
```json
{
  "suggested_spec": {
    "file_id": "uuid-string",
    "sheet_name": "Sheet1",
    "chart_type": "line",
    "x_axis": {
      "column": "date",
      "label": "Date"
    },
    "y_axis": {
      "columns": ["sales"],
      "label": "Sales ($)"
    },
    "series": {
      "group_column": "region"
    },
    "aggregation": {
      "method": "sum",
      "group_by": ["date", "region"]
    },
    "visual": {
      "title": "Sales Trends by Region"
    },
    "version": "1.0"
  },
  "explanation": "A line chart best shows sales trends over time. Grouping by region allows comparison across different areas.",
  "confidence": 0.85,
  "alternatives": [
    {
      "chart_type": "area",
      "reason": "Could show cumulative sales with stacking"
    },
    {
      "chart_type": "bar",
      "reason": "Better for discrete time periods like months"
    }
  ],
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 180,
    "total_tokens": 630
  }
}
```

**Response Headers:**
```
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1703505600
X-RateLimit-Used: 1
X-Anonymous-Session: <signed-token>
```

**Response (Error - 404):**
```json
{
  "detail": {
    "error": "File not found",
    "code": "file_not_found"
  }
}
```

**Response (Error - 429 Rate Limited):**
```json
{
  "detail": {
    "detail": "Daily AI query limit reached",
    "code": "rate_limit_exceeded",
    "queries_used": 3,
    "queries_limit": 3,
    "reset_at": "2024-12-25T00:00:00Z",
    "message": "Sign up for a free account to get unlimited AI suggestions!"
  }
}
```

**Response (Error - 429 Burst Limited):**
```json
{
  "detail": {
    "detail": "Too many requests. Please wait a moment.",
    "code": "burst_limit_exceeded"
  }
}
```

---

## Test Cases

> **Test Files**:
> - Unit: `tests/unit/test_chart_render_service.py`, `tests/unit/test_chart_validation.py`, `tests/unit/test_ai_suggest_service.py`
> - Integration: `tests/integration/test_chart_endpoint.py`

### Data Filtering (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-F1 | No filters returns original | `test_no_filters_returns_original` | Same row count |
| TC-F2 | Equal (eq) filter | `test_eq_filter` | Only matching rows |
| TC-F3 | Greater than (gt) filter | `test_gt_filter` | Values > threshold |
| TC-F4 | In filter with list | `test_in_filter` | Values in list |
| TC-F5 | Between filter | `test_between_filter` | Values in range |
| TC-F6 | AND logic | `test_and_logic` | All conditions met |
| TC-F7 | OR logic | `test_or_logic` | Any condition met |

### Data Aggregation (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-A1 | No aggregation | `test_no_aggregation_returns_original` | Same row count |
| TC-A2 | Sum aggregation | `test_sum_aggregation` | Grouped sums |
| TC-A3 | Mean aggregation | `test_mean_aggregation` | Grouped averages |
| TC-A4 | Count aggregation | `test_count_aggregation` | Row counts per group |

### Plotly Figure Building (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-P1 | Bar chart | `test_bar_chart` | Valid figure with title |
| TC-P2 | Line chart | `test_line_chart` | Valid figure |
| TC-P3 | Scatter chart | `test_scatter_chart` | Valid figure |
| TC-P4 | Histogram | `test_histogram` | Valid figure |
| TC-P5 | Pie chart | `test_pie_chart` | Valid figure |
| TC-P6 | Box chart | `test_box_chart` | Valid figure |
| TC-P7 | Area chart | `test_area_chart` | Valid figure |
| TC-P8 | Series grouping | `test_chart_with_series_grouping` | 2 traces |
| TC-P9 | Multiple y columns | `test_multiple_y_columns` | 2 traces |

### Styling (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-S1 | Color palette applied | `test_color_palette_applied` | colorway set |
| TC-S2 | Dark theme | `test_dark_theme` | Dark template applied |

### Render Pipeline (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-R1 | Valid render response | `test_render_returns_valid_response` | chart_json, rendered_at, spec_version |
| TC-R2 | Full pipeline | `test_render_with_full_pipeline` | Filters + aggregation work together |
| TC-R3 | File not found | `test_render_file_not_found_raises` | ChartRenderError raised |
| TC-R4 | Validation failure | `test_render_validation_failure_raises` | ChartRenderError raised |

### Chart Validation (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-V1 | Valid columns pass | `test_valid_columns_pass` | No errors |
| TC-V2 | Invalid x column | `test_invalid_x_column_fails` | column_not_found error |
| TC-V3 | Invalid y column | `test_invalid_y_column_fails` | column_not_found error |
| TC-V4 | Invalid group column | `test_invalid_group_column_fails` | column_not_found error |
| TC-V5 | Invalid filter column | `test_invalid_filter_column_fails` | column_not_found error |
| TC-V6 | Multiple invalid columns | `test_multiple_invalid_columns_all_reported` | 3 errors |
| TC-V7 | Bar requires y_axis | `test_bar_chart_requires_y_axis` | missing_required_field |
| TC-V8 | Bar with y_axis passes | `test_bar_chart_with_y_axis_passes` | No errors |
| TC-V9 | Line requires y_axis | `test_line_chart_requires_y_axis` | missing_required_field |
| TC-V10 | Scatter requires y_axis | `test_scatter_chart_requires_y_axis` | missing_required_field |
| TC-V11 | Histogram no y_axis | `test_histogram_does_not_require_y_axis` | No errors |
| TC-V12 | Pie no y_axis | `test_pie_does_not_require_y_axis` | No errors |
| TC-V13 | Box no y_axis | `test_box_does_not_require_y_axis` | No errors |
| TC-V14 | Numeric y_axis passes | `test_numeric_y_axis_passes` | No warnings |
| TC-V15 | Non-numeric y_axis warns | `test_non_numeric_y_axis_warns` | type_mismatch warning |
| TC-V16 | Histogram numeric x | `test_histogram_numeric_x_passes` | No warnings |
| TC-V17 | Valid spec success | `test_valid_spec_returns_success` | valid=true |
| TC-V18 | Invalid spec errors | `test_invalid_spec_returns_errors` | valid=false |
| TC-V19 | Warnings included | `test_validation_includes_warnings` | warnings array populated |
| TC-V20 | File not found | `test_file_not_found_returns_error` | file_not_found error |

### AI Schema Extraction (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-AI1 | Basic schema | `test_basic_schema_extraction` | columns, row_count |
| TC-AI2 | Numeric stats | `test_numeric_column_stats` | min, max included |
| TC-AI3 | High cardinality truncated | `test_large_unique_values_truncated` | ≤10 unique values |
| TC-AI4 | Datetime detected | `test_datetime_format_detection` | dtype=datetime64 |

### AI Prompt Building (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-AI5 | Schema in prompt | `test_prompt_includes_schema` | Column names present |
| TC-AI6 | Instructions in prompt | `test_prompt_includes_user_instructions` | Instructions included |
| TC-AI7 | ChartSpec schema | `test_prompt_includes_chartspec_schema` | Chart types mentioned |
| TC-AI8 | JSON format requested | `test_prompt_format_is_json` | "JSON" in prompt |

### AI Response Parsing (Unit Tests)

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-AI9 | Valid response | `test_parse_valid_response` | ChartSpec created |
| TC-AI10 | File ID injected | `test_file_id_always_injected` | Server file_id used |
| TC-AI11 | Invalid JSON | `test_parse_invalid_json` | AISuggestError |
| TC-AI12 | Missing required | `test_parse_missing_required_fields` | AISuggestError |
| TC-AI13 | Invalid chart type | `test_parse_invalid_chart_type` | AISuggestError |
| TC-AI14 | Metadata extracted | `test_parse_extracts_metadata` | explanation, confidence, alternatives |
| TC-AI15 | Markdown wrapper | `test_parse_with_markdown_wrapper` | JSON extracted from ```json blocks |
| TC-AI16 | Optional defaults | `test_parse_defaults_for_optional_metadata` | Empty explanation, 0.5 confidence |
| TC-AI17 | Invalid columns rejected | `test_parse_validates_column_names` | invalid_columns error |
| TC-AI18 | Valid columns accepted | `test_parse_accepts_valid_column_names` | Columns preserved |

### Integration Tests

| ID | Scenario | Test Method | Expected |
|----|----------|-------------|----------|
| TC-I1 | Render endpoint | POST /api/charts/render | 200, chart_json |
| TC-I2 | Validate endpoint | POST /api/charts/validate | 200, valid/errors |
| TC-I3 | Suggest endpoint | POST /api/charts/suggest | 200, suggested_spec |
| TC-I4 | Suggest 404 | Invalid file_id | 404, file_not_found |

---

## Dependencies

### Chart Rendering
- **plotly**: Plotly Express and Graph Objects for chart generation
- **pandas**: Data manipulation and filtering

### Chart Validation
- **pandas**: Column type checking and data validation

### AI Suggestions
- **openai**: GPT-4o-mini API calls (requires `OPENAI_API_KEY`)
- **pydantic**: ChartSpec schema validation

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI suggestions | Required |
| `ANONYMOUS_DAILY_LIMIT` | Daily AI requests for anonymous users | 3 |
| `ANONYMOUS_SESSION_SECRET` | Secret for signing session tokens | Required |

### AI Model Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| Model | `gpt-4o-mini` | Cost-efficient model |
| Temperature | 0.3 | Lower for deterministic output |
| Max Tokens | 1500 | Response token limit |

---

## Security Considerations

### ChartSpec Approach (Current)

The current architecture eliminates code execution security risks:

1. **No Code Execution**: AI generates structured JSON, not executable code
2. **Schema Validation**: All ChartSpec fields are validated by Pydantic
3. **File ID Injection**: `file_id` is always server-controlled, never from AI
4. **Column Validation**: All column references are validated against actual data

### Rate Limiting

Anonymous AI requests are protected by multiple layers:

1. **Session-based limits**: 3 requests per 24-hour rolling window
2. **IP-based burst protection**: Prevents rapid-fire abuse
3. **Global daily cap**: System-wide limit for cost control
4. **Signed session tokens**: HMAC-SHA256 prevents token forgery

---

## Notes

- Chart JSON follows Plotly's JSON schema and can be rendered directly in frontend
- AI uses GPT-4o-mini for cost efficiency; model can be configured
- Column names are provided to AI with explicit instructions to use exact names
- The suggested ChartSpec can be edited in the Chart Editor UI before rendering
- All charts (manual and AI) use the same render pipeline for consistency

