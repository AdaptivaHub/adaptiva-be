# Feature: Chart Generation

## Overview
Generate interactive data visualizations using Plotly. Supports both manual chart configuration and AI-powered automatic chart generation based on data analysis.

## User Story
As a data analyst,
I want to create charts from my uploaded data,
So that I can visualize trends, patterns, and insights.

## Sub-Features

### 1. Manual Chart Generation
Generate charts by specifying chart type and column mappings.

### 2. AI-Powered Chart Generation
Use AI (OpenAI) to analyze data and automatically generate appropriate visualizations.

---

## Manual Chart Generation

### Acceptance Criteria

#### AC-1: Bar Chart
- **Given**: A dataset with categorical and numerical columns
- **When**: A bar chart is requested with x and y columns
- **Then**: A bar chart is generated showing category values

#### AC-2: Line Chart
- **Given**: A dataset with sequential/time data
- **When**: A line chart is requested with x and y columns
- **Then**: A line chart is generated showing trends

#### AC-3: Scatter Plot
- **Given**: A dataset with two numerical columns
- **When**: A scatter chart is requested
- **Then**: A scatter plot is generated showing correlation

#### AC-4: Histogram
- **Given**: A dataset with a numerical column
- **When**: A histogram is requested with x column
- **Then**: A histogram is generated showing distribution

#### AC-5: Box Plot
- **Given**: A dataset with numerical data
- **When**: A box chart is requested
- **Then**: A box plot is generated showing statistical distribution

#### AC-6: Pie Chart
- **Given**: A dataset with categorical data
- **When**: A pie chart is requested
- **Then**: A pie chart is generated showing proportions

#### AC-7: Color Grouping
- **Given**: Any chart type with a color_column specified
- **When**: The chart is generated
- **Then**: Data is grouped and colored by the specified column

#### AC-8: Invalid File ID
- **Given**: A non-existent file_id
- **When**: Chart generation is requested
- **Then**: A 404 error is returned

#### AC-9: Invalid Column Name
- **Given**: A column name that doesn't exist in the dataset
- **When**: Chart generation is requested
- **Then**: A 400 error is returned with details

### API Contract - Manual Charts

#### Endpoint: `POST /api/charts/`

**Request:**
```json
{
  "file_id": "uuid-string",
  "chart_type": "bar|line|scatter|histogram|box|pie",
  "x_column": "column_name",
  "y_column": "column_name (optional for histogram/pie)",
  "title": "Chart Title (optional)",
  "color_column": "column_name (optional)"
}
```

**Response (Success - 200):**
```json
{
  "chart_json": {
    "data": [...],
    "layout": {...}
  },
  "message": "Chart generated successfully"
}
```

**Response (Error - 400):**
```json
{
  "detail": "Column 'invalid_col' not found in dataset"
}
```

```json
{
  "detail": "y_column is required for bar charts"
}
```

**Response (Error - 404):**
```json
{
  "detail": "File ID xxx not found"
}
```

---

## AI-Powered Chart Generation

### Acceptance Criteria

#### AC-10: Automatic Chart Selection
- **Given**: A dataset without specific instructions
- **When**: AI chart generation is requested
- **Then**: AI analyzes data schema and creates an appropriate chart

#### AC-11: User Instructions
- **Given**: User provides instructions like "Show sales trends over time"
- **When**: AI chart generation is requested
- **Then**: AI generates a chart matching the user's intent

#### AC-12: Code Generation
- **Given**: A successful AI chart generation
- **When**: The response is received
- **Then**: It includes the generated Python code

#### AC-13: Explanation
- **Given**: A successful AI chart generation
- **When**: The response is received
- **Then**: It includes an explanation of what the chart shows

#### AC-14: Sandboxed Execution
- **Given**: AI generates chart code
- **When**: The code is executed
- **Then**: It runs in a restricted sandbox (no file/network access)

#### AC-15: Invalid Code Handling
- **Given**: AI generates invalid or dangerous code
- **When**: Execution is attempted
- **Then**: An error is returned, not a system compromise

### API Contract - AI Charts

#### Endpoint: `POST /api/charts/ai`

**Request:**
```json
{
  "file_id": "uuid-string",
  "user_instructions": "Show me a chart of sales by region (optional)",
  "base_prompt": "Custom system prompt (optional)"
}
```

**Response (Success - 200):**
```json
{
  "chart_json": {
    "data": [...],
    "layout": {...}
  },
  "generated_code": "fig = px.bar(df, x='region', y='sales', title='Sales by Region')",
  "explanation": "This bar chart shows the total sales for each region, making it easy to compare performance across different areas.",
  "message": "Chart generated successfully"
}
```

**Response (Error - 400/500):**
```json
{
  "detail": "Error generating chart: [specific error]"
}
```

---

## Test Cases

### Manual Chart Generation

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Bar chart | file_id, chart_type=bar, x, y | 200, valid Plotly JSON |
| TC-2 | Line chart | file_id, chart_type=line, x, y | 200, valid Plotly JSON |
| TC-3 | Scatter plot | file_id, chart_type=scatter, x, y | 200, valid Plotly JSON |
| TC-4 | Histogram | file_id, chart_type=histogram, x | 200, valid Plotly JSON |
| TC-5 | Box plot | file_id, chart_type=box, x, y | 200, valid Plotly JSON |
| TC-6 | Pie chart | file_id, chart_type=pie, x | 200, valid Plotly JSON |
| TC-7 | With color grouping | Any chart + color_column | 200, colored chart |
| TC-8 | Missing y for bar | chart_type=bar, no y_column | 400, y_column required |
| TC-9 | Invalid column | x_column="nonexistent" | 400, column not found |
| TC-10 | Invalid file_id | Non-existent UUID | 404, file not found |
| TC-11 | Custom title | title="My Custom Chart" | 200, chart with custom title |

### AI Chart Generation

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-12 | Auto chart | file_id only | 200, chart + code + explanation |
| TC-13 | With instructions | file_id + user_instructions | 200, relevant chart |
| TC-14 | Invalid file_id | Non-existent UUID | 404, file not found |
| TC-15 | Empty dataset | file_id for empty data | Appropriate error |

## Dependencies

### Manual Charts
- plotly: For chart generation
- pandas: For data manipulation

### AI Charts
- openai: For GPT API calls (requires OPENAI_API_KEY)
- RestrictedPython: For sandboxed code execution

## Security Considerations

### AI Chart Sandboxing
The AI-generated code runs in a restricted environment:
- No file system access
- No network access
- No module imports beyond allowed list
- Blocked dangerous attributes (__class__, __globals__, etc.)
- Timeout on execution (recommended)

### Allowed in Sandbox
- pandas operations (pd)
- numpy operations (np)
- plotly.express (px)
- plotly.graph_objects (go)
- Basic Python builtins (list, dict, len, etc.)

## Notes
- Chart JSON follows Plotly's JSON schema and can be rendered directly in frontend
- AI uses GPT-4o-mini for cost efficiency; can be configured
- Column names are cleaned (newlines removed) before AI processing
- The generated code is returned for transparency and debugging
