# Feature: ChartSpec Model

## Overview

The ChartSpec is the canonical schema for all chart configurations. It serves as the single source of truth for chart generation, validation, and storage.

## User Story

As a developer,
I want a well-defined chart specification schema,
So that I can consistently represent chart configurations across the application.

---

## Schema Structure

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | string | Reference to the data source |
| `chart_type` | enum | One of: bar, line, scatter, histogram, box, pie, area, heatmap |
| `x_axis` | AxisConfig | X-axis column configuration |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sheet_name` | string | null | Excel sheet name (for multi-sheet files) |
| `y_axis` | YAxisConfig | null | Y-axis column(s) configuration |
| `series` | SeriesConfig | null | Grouping/color configuration |
| `aggregation` | AggregationConfig | method: "none" | Aggregation settings |
| `filters` | FiltersConfig | null | Data filtering conditions |
| `visual` | VisualStructureConfig | defaults | Visual structure settings |
| `legend` | LegendConfig | visible: true, position: "right" | Legend settings |
| `interaction` | InteractionConfig | defaults | Interaction behavior |
| `styling` | StylingConfig | theme: "light", palette: "default" | Styling presets |
| `version` | string | "1.0" | Schema version |

---

## Acceptance Criteria

### AC-1: Minimal Valid Spec
- **Given**: Only required fields (file_id, chart_type, x_axis)
- **When**: ChartSpec is created
- **Then**: Spec is valid with defaults applied

### AC-2: Full Valid Spec
- **Given**: All fields populated with valid values
- **When**: ChartSpec is created
- **Then**: All values are preserved

### AC-3: Invalid Chart Type Rejected
- **Given**: An invalid chart_type value
- **When**: ChartSpec is created
- **Then**: Pydantic validation error is raised

### AC-4: Invalid Aggregation Method Rejected
- **Given**: An invalid aggregation.method value
- **When**: ChartSpec is created
- **Then**: Pydantic validation error is raised

### AC-5: Invalid Theme Rejected
- **Given**: An invalid styling.theme value
- **When**: ChartSpec is created
- **Then**: Pydantic validation error is raised

### AC-6: Defaults Applied Correctly
- **Given**: A minimal ChartSpec
- **When**: Optional fields are accessed
- **Then**: Default values are returned

### AC-7: All Filter Operators Valid
- **Given**: Any valid filter operator
- **When**: FilterCondition is created
- **Then**: Operator is accepted

### AC-8: Between Filter with Value End
- **Given**: A "between" operator
- **When**: FilterCondition has value and value_end
- **Then**: Both values are stored

### AC-9: In Filter with List Value
- **Given**: An "in" operator
- **When**: FilterCondition has a list value
- **Then**: List is stored

---

## Sub-Model Specifications

### AxisConfig
```python
class AxisConfig:
    column: str           # Required - column name
    label: str | None     # Optional - display label
```

### YAxisConfig
```python
class YAxisConfig:
    columns: List[str]    # Required - one or more column names
    label: str | None     # Optional - display label
```

### SeriesConfig
```python
class SeriesConfig:
    group_column: str | None   # Column to group/color by
    size_column: str | None    # Column for bubble size (scatter)
```

### FilterCondition
```python
class FilterCondition:
    column: str                         # Column to filter
    operator: FilterOperatorEnum        # Filter operator
    value: str | int | float | list     # Filter value
    value_end: str | int | float | None # For "between" operator
```

**Operators**: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `between`, `contains`

### AggregationConfig
```python
class AggregationConfig:
    method: AggregationMethodEnum = "none"  # Aggregation method
    group_by: List[str] | None = None       # Columns to group by
```

**Methods**: `none`, `sum`, `mean`, `count`, `median`, `min`, `max`

---

## Serialization

### AC-10: Serialize to Dict
- **Given**: A ChartSpec instance
- **When**: `model_dump()` is called
- **Then**: Valid dict is returned with all fields

### AC-11: Deserialize from Dict
- **Given**: A valid dict with ChartSpec fields
- **When**: `ChartSpec.model_validate(data)` is called
- **Then**: Valid ChartSpec instance is created

### AC-12: Serialize to JSON
- **Given**: A ChartSpec instance
- **When**: `model_dump_json()` is called
- **Then**: Valid JSON string is returned

---

## Test Cases

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Minimal valid spec | file_id, chart_type, x_axis | Valid spec with defaults |
| TC-2 | Full valid spec | All fields populated | All values preserved |
| TC-3 | Invalid chart_type | chart_type="invalid" | ValueError raised |
| TC-4 | Invalid aggregation | method="invalid_agg" | ValueError raised |
| TC-5 | Invalid theme | theme="invalid_theme" | ValueError raised |
| TC-6 | Default values | Minimal spec | Correct defaults |
| TC-7 | All filter operators | Each valid operator | All accepted |
| TC-8 | Between filter | operator="between", value_end=500 | Both values stored |
| TC-9 | In filter with list | operator="in", value=["a","b"] | List stored |
| TC-10 | X-axis minimal | column="date" | column set, label=None |
| TC-11 | X-axis with label | column="date", label="Date" | Both set |
| TC-12 | Y-axis single column | columns=["revenue"] | Single column list |
| TC-13 | Y-axis multiple columns | columns=["a", "b", "c"] | All 3 columns |
| TC-14 | Series with group | group_column="category" | group set, size=None |
| TC-15 | Series with size | size_column="population" | size column set |
| TC-16 | Serialize to dict | ChartSpec instance | Valid dict |
| TC-17 | Deserialize from dict | Valid dict | ChartSpec instance |
| TC-18 | Serialize to JSON | ChartSpec instance | Valid JSON string |

---

## Dependencies

- **pydantic**: Model validation and serialization
- **typing**: Type hints

---

## Notes

- ChartSpec is immutable after creation (Pydantic model)
- Version field enables future schema migrations
- All enum fields use Literal types for Pydantic v2 compatibility
