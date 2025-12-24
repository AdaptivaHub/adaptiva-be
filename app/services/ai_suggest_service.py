"""
AI Suggest Service - Generates ChartSpec suggestions using LLM.

This service:
1. Extracts data schema from uploaded files
2. Builds prompts for the LLM
3. Parses LLM responses into validated ChartSpec
4. Tracks usage for billing

Key principle: AI generates ChartSpec JSON, NOT executable code.
"""
import os
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

import pandas as pd
from openai import OpenAI

from app.models.chart_spec import (
    ChartSpec,
    AISuggestRequest,
    AISuggestResponse,
    AxisConfig,
    YAxisConfig,
)
from app.utils import storage


# =============================================================================
# Configuration
# =============================================================================

# Model configuration
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3  # Lower for more deterministic output
LLM_MAX_TOKENS = 1500

# OpenAI client - initialized lazily
_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AISuggestError(
                "OpenAI API key not configured",
                code="api_key_missing"
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# Expose for mocking in tests
openai_client = property(lambda self: get_openai_client())


# =============================================================================
# ChartSpec JSON Schema for LLM
# =============================================================================

CHARTSPEC_JSON_SCHEMA = json.dumps({
    "type": "object",
    "required": ["chart_type", "x_axis"],
    "properties": {
        "chart_type": {
            "type": "string",
            "enum": ["bar", "line", "scatter", "histogram", "box", "pie", "area", "heatmap"],
            "description": "Type of chart to generate"
        },
        "x_axis": {
            "type": "object",
            "required": ["column"],
            "properties": {
                "column": {"type": "string", "description": "Column name for X-axis"},
                "label": {"type": "string", "description": "Display label for X-axis"}
            }
        },
        "y_axis": {
            "type": "object",
            "properties": {
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column name(s) for Y-axis values"
                },
                "label": {"type": "string", "description": "Display label for Y-axis"}
            }
        },
        "series": {
            "type": "object",
            "properties": {
                "group_column": {"type": "string", "description": "Column to group/color by"},
                "size_column": {"type": "string", "description": "Column for bubble size (scatter)"}
            }
        },
        "aggregation": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["none", "sum", "mean", "count", "median", "min", "max"]
                },
                "group_by": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "visual": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "stacking": {"type": "string", "enum": ["grouped", "stacked", "percent"]}
            }
        },
        "styling": {
            "type": "object",
            "properties": {
                "color_palette": {
                    "type": "string",
                    "enum": ["default", "vibrant", "pastel", "monochrome", "colorblind_safe"]
                },
                "theme": {"type": "string", "enum": ["light", "dark"]},
                "show_data_labels": {"type": "boolean"}
            }
        },
        "explanation": {
            "type": "string",
            "description": "Brief explanation of why this chart was chosen"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score for the suggestion"
        },
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string"},
                    "reason": {"type": "string"}
                }
            }
        }
    }
}, indent=2)


# =============================================================================
# Exception Class
# =============================================================================

class AISuggestError(Exception):
    """Exception raised by AI suggest service."""
    
    def __init__(self, message: str, code: str = "ai_suggest_error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


# =============================================================================
# Data Schema Extraction
# =============================================================================

def extract_data_schema(df: pd.DataFrame, max_unique_values: int = 10, max_sample_values: int = 5) -> Dict[str, Any]:
    """
    Extract schema information from a dataframe for LLM context.
    
    Args:
        df: The pandas DataFrame to analyze
        max_unique_values: Max unique values to include for categorical columns
        max_sample_values: Max sample values to include
        
    Returns:
        Dictionary with column information, types, and sample values
    """
    columns = []
    
    for col_name in df.columns:
        col_data = df[col_name]
        col_info: Dict[str, Any] = {
            "name": col_name,
            "dtype": str(col_data.dtype),
            "null_count": int(col_data.isnull().sum()),
        }
        
        # Get cardinality
        unique_count = col_data.nunique()
        col_info["cardinality"] = unique_count
        
        # For numeric columns, include stats
        if pd.api.types.is_numeric_dtype(col_data):
            col_info["min"] = float(col_data.min()) if not pd.isna(col_data.min()) else None
            col_info["max"] = float(col_data.max()) if not pd.isna(col_data.max()) else None
            col_info["sample_values"] = [
                float(v) if pd.notna(v) else None 
                for v in col_data.head(max_sample_values).tolist()
            ]
        # For low-cardinality columns, include unique values
        elif unique_count <= max_unique_values:
            unique_vals = col_data.dropna().unique().tolist()[:max_unique_values]
            col_info["unique_values"] = [str(v) for v in unique_vals]
            col_info["sample_values"] = [str(v) for v in col_data.head(max_sample_values).tolist()]
        # For high-cardinality columns, just show samples
        else:
            col_info["sample_values"] = [str(v) for v in col_data.head(max_sample_values).tolist()]
        
        columns.append(col_info)
    
    return {
        "columns": columns,
        "row_count": len(df),
    }


# =============================================================================
# LLM Prompt Building
# =============================================================================

SYSTEM_PROMPT = """You are a data visualization expert. Your task is to analyze a dataset and suggest the best chart configuration.

IMPORTANT RULES:
1. Output ONLY valid JSON matching the ChartSpec schema
2. CRITICAL: Use the EXACT column names from the data schema. Column names are strings like "Product Name", "Sales", "Date" - NOT indices like 0, 1, 2
3. The column names are provided in the "name" field of each column in the schema
4. Choose chart types based on the data characteristics:
   - Use LINE for time series / trends
   - Use BAR for categorical comparisons
   - Use SCATTER for relationships between numeric variables
   - Use PIE for part-to-whole relationships (< 7 categories)
   - Use HISTOGRAM for distributions of a single variable
   - Use BOX for comparing distributions across categories
   - Use AREA for cumulative or stacked time series
   - Use HEATMAP for two-dimensional categorical data
5. Always include an explanation of your choice
6. Suggest 1-2 alternatives when applicable

Output JSON only, no markdown formatting."""


def build_llm_prompt(schema: Dict[str, Any], user_instructions: Optional[str] = None) -> str:
    """
    Build the user prompt for the LLM.
    
    Args:
        schema: Data schema extracted from the dataframe
        user_instructions: Optional user-provided instructions
        
    Returns:
        Formatted prompt string
    """
    prompt_parts = []
    
    # Data schema section
    prompt_parts.append("## Data Schema\n")
    prompt_parts.append(f"Total rows: {schema['row_count']}\n\n")
    
    # Explicitly list column names first for clarity
    column_names = [col['name'] for col in schema["columns"]]
    prompt_parts.append(f"**Available column names (use these exact names):** {column_names}\n\n")
    
    prompt_parts.append("Column details:\n")
    
    for col in schema["columns"]:
        col_desc = f"- Column name: \"{col['name']}\" (type: {col['dtype']})"
        
        if "min" in col and "max" in col:
            col_desc += f" range: [{col['min']}, {col['max']}]"
        if "unique_values" in col:
            col_desc += f" values: {col['unique_values']}"
        if "cardinality" in col and col["cardinality"] > 10:
            col_desc += f" ({col['cardinality']} unique values)"
        
        prompt_parts.append(col_desc + "\n")
    
    # User instructions section
    if user_instructions:
        prompt_parts.append(f"\n## User Request\n{user_instructions}\n")
    else:
        prompt_parts.append("\n## Task\nSuggest the best chart to visualize this data.\n")
    
    # Schema reference
    prompt_parts.append("\n## ChartSpec Schema\n")
    prompt_parts.append(f"```json\n{CHARTSPEC_JSON_SCHEMA}\n```\n")
    
    return "".join(prompt_parts)


# =============================================================================
# LLM Response Parsing
# =============================================================================

def parse_llm_response(
    response_text: str, 
    file_id: str, 
    sheet_name: Optional[str] = None,
    valid_columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Parse LLM response into a validated ChartSpec.
    
    Args:
        response_text: Raw text response from LLM
        file_id: File ID to inject (never trust LLM for this)
        sheet_name: Optional sheet name to inject
        valid_columns: List of valid column names to validate against
        
    Returns:
        Dictionary with 'spec' (ChartSpec), 'explanation', 'confidence', 'alternatives'
        
    Raises:
        AISuggestError: If parsing or validation fails
    """
    # Strip markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```"):
        # Remove opening fence
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    # Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise AISuggestError(
            f"Failed to parse LLM response as JSON: {e}",
            code="json_parse_error",
            details={"raw_response": response_text[:500]}
        )
      # Extract metadata (before validation removes unknown fields)
    explanation = data.pop("explanation", "")
    confidence = data.pop("confidence", 0.5)
    alternatives = data.pop("alternatives", [])
      # Inject file_id (NEVER trust LLM for this)
    data["file_id"] = file_id
    if sheet_name:
        data["sheet_name"] = sheet_name
    
    # Validate and normalize column names if valid_columns provided
    if valid_columns:
        # Normalize valid columns to strings for comparison
        valid_columns_str = [str(c) for c in valid_columns]
        
        # Helper to check and normalize column name
        def normalize_column(col_name: str) -> str:
            """Try to match column name, handling int/str conversion."""
            if col_name in valid_columns:
                return col_name
            # Try string comparison
            if col_name in valid_columns_str:
                # Return the original column name (might be int)
                idx = valid_columns_str.index(col_name)
                return valid_columns[idx]
            return None  # Not found
        
        invalid_cols = []
        
        # Check and normalize x_axis column
        x_axis = data.get("x_axis", {})
        if isinstance(x_axis, dict):
            x_col = x_axis.get("column")
            if x_col is not None:
                normalized = normalize_column(str(x_col))
                if normalized is None:
                    invalid_cols.append(f"x_axis.column: '{x_col}'")
                else:
                    # Update with normalized column name
                    x_axis["column"] = str(normalized) if isinstance(normalized, int) else normalized
        
        # Check and normalize y_axis columns
        y_axis = data.get("y_axis", {})
        if isinstance(y_axis, dict):
            y_cols = y_axis.get("columns", [])
            normalized_y_cols = []
            for i, y_col in enumerate(y_cols):
                if y_col is not None:
                    normalized = normalize_column(str(y_col))
                    if normalized is None:
                        invalid_cols.append(f"y_axis.columns[{i}]: '{y_col}'")
                    else:
                        normalized_y_cols.append(str(normalized) if isinstance(normalized, int) else normalized)
            if normalized_y_cols:
                y_axis["columns"] = normalized_y_cols
        
        # Check and normalize series columns
        series = data.get("series", {})
        if isinstance(series, dict):
            group_col = series.get("group_column")
            if group_col is not None:
                normalized = normalize_column(str(group_col))
                if normalized is None:
                    invalid_cols.append(f"series.group_column: '{group_col}'")
                else:
                    series["group_column"] = str(normalized) if isinstance(normalized, int) else normalized
            
            size_col = series.get("size_column")
            if size_col is not None:
                normalized = normalize_column(str(size_col))
                if normalized is None:
                    invalid_cols.append(f"series.size_column: '{size_col}'")
                else:
                    series["size_column"] = str(normalized) if isinstance(normalized, int) else normalized
        
        if invalid_cols:
            raise AISuggestError(
                f"LLM suggested invalid column names: {', '.join(invalid_cols)}. Valid columns: {valid_columns_str}",
                code="invalid_columns",
                details={"invalid_columns": invalid_cols, "valid_columns": valid_columns_str}
            )
    
    # Validate as ChartSpec
    try:
        spec = ChartSpec(**data)
    except Exception as e:
        raise AISuggestError(
            f"LLM response failed ChartSpec validation: {e}",
            code="validation_error",
            details={"validation_error": str(e)}
        )
    
    return {
        "spec": spec,
        "explanation": explanation,
        "confidence": confidence,
        "alternatives": alternatives,
    }


# =============================================================================
# Main Function
# =============================================================================

def generate_chart_suggestion(request: AISuggestRequest) -> AISuggestResponse:
    """
    Generate a chart suggestion using AI.
    
    Args:
        request: The suggestion request with file_id and optional instructions
        
    Returns:
        AISuggestResponse with suggested ChartSpec and metadata
        
    Raises:
        AISuggestError: If file not found, LLM call fails, or response invalid
    """
    # 1. Load dataframe
    try:
        df = storage.get_dataframe(request.file_id, request.sheet_name)
    except ValueError as e:
        raise AISuggestError(
            f"File not found: {request.file_id}",
            code="file_not_found",
            details={"file_id": request.file_id, "sheet_name": request.sheet_name}
        )
    
    # 2. Extract schema
    schema = extract_data_schema(df)
    
    # 3. Build prompt
    user_prompt = build_llm_prompt(schema, request.user_instructions)
    
    # 4. Call LLM
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        raise AISuggestError(
            f"LLM API call failed: {e}",
            code="llm_api_error",
            details={"error": str(e)}
        )
      # 5. Parse response with column validation
    llm_output = response.choices[0].message.content
    valid_columns = list(df.columns)  # Get actual column names from dataframe
    result = parse_llm_response(
        llm_output, 
        request.file_id, 
        request.sheet_name,
        valid_columns=valid_columns
    )
    
    # 6. Build response
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.prompt_tokens + response.usage.completion_tokens,
        "model": LLM_MODEL,
    }
    
    return AISuggestResponse(
        suggested_spec=result["spec"],
        explanation=result["explanation"],
        confidence=result["confidence"],
        alternatives=result["alternatives"],
        usage=usage,
    )
