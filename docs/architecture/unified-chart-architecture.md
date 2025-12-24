# Unified Chart Generation Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐         ┌─────────────────────────────────────────────┐  │
│   │  AI Suggest  │────────►│              CHART EDITOR                   │  │
│   │    Button    │ auto-   │  ┌─────────┬─────────┬─────────┬─────────┐  │  │
│   └──────────────┘ fills   │  │ Type    │ X-Axis  │ Y-Axis  │ Series  │  │  │
│                            │  ├─────────┼─────────┼─────────┼─────────┤  │  │
│   User can always          │  │ Filters │ Styling │ Legend  │ Title   │  │  │
│   override AI choices      │  └─────────┴─────────┴─────────┴─────────┘  │  │
│                            └──────────────────┬──────────────────────────┘  │
│                                               │                              │
│                                               ▼                              │
│                                        ┌────────────┐                        │
│                                        │ ChartSpec  │ (canonical schema)     │
│                                        └─────┬──────┘                        │
└──────────────────────────────────────────────┼───────────────────────────────┘
                                               │
┌──────────────────────────────────────────────┼───────────────────────────────┐
│                              BACKEND         │                               │
├──────────────────────────────────────────────┼───────────────────────────────┤
│                                              ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         POST /api/charts/render                         ││
│  │                    (single render path for ALL charts)                  ││
│  │                           No AI cost, no metering                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                              │                               │
│                                              ▼                               │
│                                     ┌────────────────┐                       │
│                                     │  Plotly JSON   │                       │
│                                     └────────────────┘                       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        POST /api/charts/suggest                         ││
│  │              (AI generates ChartSpec, NOT executable code)              ││
│  │                    Rate-limited, metered, auditable                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                              │                               │
│                                              ▼                               │
│                                        ┌───────────┐                         │
│                                        │ ChartSpec │ (returned to frontend)  │
│                                        └───────────┘                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Single Render Path**: All charts flow through `POST /api/charts/render`
2. **AI Produces Data, Not Code**: AI generates `ChartSpec` JSON, never executable code
3. **Editor is Always Engaged**: AI auto-fills the Chart Editor; users can modify before rendering
4. **Cost Isolation**: Only `/suggest` touches LLMs; `/render` and `/validate` are free

---

## 2. ChartSpec Schema (Source of Truth)

The `ChartSpec` is the canonical representation of a chart configuration. It is:
- **Generated** by AI suggestions (populates Chart Editor)
- **Edited** by users in the Chart Editor UI
- **Validated** before rendering
- **Rendered** to Plotly JSON
- **Stored** for saved charts

### Schema Structure

```
ChartSpec
├── file_id: str                    # Data source reference
├── sheet_name: str?                # For Excel files
├── chart_type: enum                # bar, line, scatter, histogram, box, pie, area, heatmap
│
├── [Data & Mapping]
│   ├── x_axis: {column, label?}
│   ├── y_axis: {columns[], label?}
│   ├── series: {group_column?, size_column?}
│   ├── aggregation: {method, group_by[]?}
│   └── filters: {conditions[], logic}
│
├── [Visual Structure]
│   ├── visual: {title?, stacking, secondary_y_axis}
│   └── legend: {visible, position}
│
├── [Interaction]
│   └── interaction: {zoom_scroll, responsive, modebar, export_formats[], tooltip_detail}
│
└── [Styling]
    └── styling: {color_palette, theme, show_data_labels}
```

### Enums

| Enum | Values |
|------|--------|
| `ChartTypeEnum` | `bar`, `line`, `scatter`, `histogram`, `box`, `pie`, `area`, `heatmap` |
| `AggregationMethodEnum` | `none`, `sum`, `mean`, `count`, `median`, `min`, `max` |
| `StackingModeEnum` | `grouped`, `stacked`, `percent` |
| `ThemeEnum` | `light`, `dark` |
| `ColorPaletteEnum` | `default`, `vibrant`, `pastel`, `monochrome`, `colorblind_safe` |
| `FilterOperatorEnum` | `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `between`, `contains` |

Full implementation: `app/models/chart_spec.py`

---

## 3. API Endpoints

| Endpoint | Purpose | AI Cost | Auth Required |
|----------|---------|---------|---------------|
| `POST /api/charts/render` | Render ChartSpec → Plotly JSON | ❌ None | No |
| `POST /api/charts/validate` | Pre-flight validation | ❌ None | No |
| `POST /api/charts/suggest` | AI generates ChartSpec | ✅ Yes | No (rate-limited) |

### 3.1 POST /api/charts/render

Converts a `ChartSpec` into Plotly JSON. No AI, no metering.

**Request:**
```json
{
  "spec": {
    "file_id": "abc-123",
    "chart_type": "bar",
    "x_axis": { "column": "category" },
    "y_axis": { "columns": ["revenue"] },
    "visual": { "title": "Revenue by Category" },
    "styling": { "color_palette": "vibrant", "theme": "light" }
  }
}
```

**Response:**
```json
{
  "chart_json": { /* Plotly figure JSON */ },
  "rendered_at": "2024-12-24T10:30:00Z",
  "spec_version": "1.0"
}
```

**Errors:**
- `400` - Invalid ChartSpec (validation errors)
- `404` - File not found

### 3.2 POST /api/charts/validate

Pre-flight validation without rendering. Returns errors and warnings.

**Request:**
```json
{
  "spec": {
    "file_id": "abc-123",
    "chart_type": "bar",
    "x_axis": { "column": "nonexistent_column" }
  }
}
```

**Response:**
```json
{
  "valid": false,
  "errors": [
    {
      "field": "x_axis.column",
      "code": "column_not_found",
      "message": "Column 'nonexistent_column' not found in data"
    },
    {
      "field": "y_axis",
      "code": "missing_required_field",
      "message": "Chart type 'bar' requires y_axis to be specified"
    }
  ],
  "warnings": []
}
```

### 3.3 POST /api/charts/suggest

AI analyzes data and generates a `ChartSpec`. Rate-limited and metered.

**Request:**
```json
{
  "file_id": "abc-123",
  "sheet_name": null,
  "user_instructions": "Show revenue trends by region over time"
}
```

**Response:**
```json
{
  "suggested_spec": {
    "file_id": "abc-123",
    "chart_type": "line",
    "x_axis": { "column": "date", "label": "Date" },
    "y_axis": { "columns": ["revenue"], "label": "Revenue ($)" },
    "series": { "group_column": "region" },
    "visual": { "title": "Revenue Trends by Region" },
    "styling": { "color_palette": "colorblind_safe" }
  },
  "explanation": "I created a line chart showing revenue over time, grouped by region. This reveals trends and allows comparison between regions.",
  "confidence": 0.85,
  "alternatives": [
    { "chart_type": "area", "reason": "Area chart would emphasize cumulative totals" }
  ],
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 120,
    "model": "gpt-4o-mini"
  }
}
```

**Rate Limit Headers (anonymous users):**
```
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1703505600
X-Anonymous-Session: <token>
```

---

## 4. AI Suggestion Flow

### How AI Suggestions Work

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. USER CLICKS "AI SUGGEST"                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. FRONTEND → POST /api/charts/suggest                                      │
│    { file_id, user_instructions? }                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. BACKEND: Rate Limit Check                                                │
│    - Anonymous: 3/day per IP+session                                        │
│    - Authenticated: unlimited (or plan-based)                               │
│    - If exceeded → 429 with reset time                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. BACKEND: Build LLM Prompt                                                │
│    - Load dataframe, extract schema (column names, types, sample values)    │
│    - Include ChartSpec JSON schema in prompt                                │
│    - Include user instructions if provided                                  │
│    - System prompt: "Output valid ChartSpec JSON only"                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. BACKEND: Call LLM                                                        │
│    - Model: gpt-4o-mini (cost-effective)                                    │
│    - Temperature: 0.3 (deterministic)                                       │
│    - Response format: JSON mode                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. BACKEND: Validate & Sanitize                                             │
│    - Parse LLM response as ChartSpec (Pydantic validation)                  │
│    - Validate columns exist in dataframe                                    │
│    - Inject file_id (never trust LLM for this)                              │
│    - Log usage for billing                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. FRONTEND: Receives ChartSpec                                             │
│    - Populates Chart Editor fields with suggested values                    │
│    - User can modify any field                                              │
│    - "Render" button calls POST /api/charts/render                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Billing, Quotas & Usage Tracking

### Isolation Principle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           METERED (AI Cost)                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  POST /api/charts/suggest                                             │  │
│  │  - Rate limiting (IP + session + user)                                │  │
│  │  - Token usage tracking                                               │  │
│  │  - Audit logging                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          FREE (No AI Cost)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  POST /api/charts/render                                              │  │
│  │  POST /api/charts/validate                                            │  │
│  │  - No rate limiting                                                   │  │
│  │  - No usage tracking                                                  │  │
│  │  - Unlimited calls                                                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rate Limiting Strategy

| User Type | Limit | Scope | Reset |
|-----------|-------|-------|-------|
| Anonymous | 3/day | IP + Session | 24h rolling |
| Authenticated (Free) | Unlimited | - | - |
| Authenticated (Paid) | Unlimited | - | - |

### Usage Tracking

Each `/suggest` call logs:
```json
{
  "timestamp": "2024-12-24T10:30:00Z",
  "user_id": "user-123 | anonymous",
  "client_ip": "192.168.1.1",
  "session_id": "sess-abc",
  "file_id": "file-xyz",
  "model": "gpt-4o-mini",
  "prompt_tokens": 450,
  "completion_tokens": 120,
  "latency_ms": 1200,
  "success": true
}
```

### Audit Trail

- All AI suggestions are logged with full request/response
- Token usage aggregated for cost monitoring
- Rate limit violations tracked for abuse detection

---

## 6. File Structure

```
app/
├── models/
│   ├── __init__.py
│   ├── chart_spec.py           # ChartSpec schema & API models
│   └── user.py
├── services/
│   ├── chart_render_service.py # ChartSpec → Plotly JSON
│   ├── chart_validation.py     # Validation logic
│   ├── ai_suggest_service.py   # LLM integration
│   └── rate_limit_service.py   # Existing rate limiting
└── routers/
    └── charts.py               # /render, /validate, /suggest endpoints
```

---

## 7. Migration Phases

### Phase 1: Schema & Validation ✅
- [x] Create `app/models/chart_spec.py`
- [x] Create `app/services/chart_validation.py`
- [x] Create tests for validation

### Phase 2: Render Service ✅
- [x] Create tests for `chart_render_service.py`
- [x] Create `app/services/chart_render_service.py`
- [x] Create `POST /api/charts/render` endpoint
- [x] Create `POST /api/charts/validate` endpoint
- [x] Delete `chart_service.py`
- [x] Delete `ai_chart_service.py`

### Phase 3: AI Suggest Service ✅
- [x] Create tests for `ai_suggest_service.py`
- [x] Create `app/services/ai_suggest_service.py`
- [x] Create `POST /api/charts/suggest` endpoint
- [x] Remove RestrictedPython dependency

### Phase 4: Frontend Integration ✅
- [x] Update Chart Editor to accept `ChartSpec` from AI
- [x] Update render calls to use new endpoint
- [x] Remove old `/charts` and `/charts/ai` calls
- [x] Create `src/types/chartSpec.ts` with TypeScript types
- [x] Rewrite `src/services/chartService.ts` with suggest/render/validate
- [x] Rewrite `src/hooks/useChart.ts` with new unified API
- [x] Update `src/components/ChartEditor.tsx` and `ChartView.tsx`
- [x] Update `src/App.tsx` to use new useChart hook
- [x] Update `src/app/routes/ChartsPage.tsx` to use new API
- [x] Frontend compiles successfully
