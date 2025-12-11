import json
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException
from openai import OpenAI
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safer_getattr
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from app.utils import get_dataframe, with_timeout, CHART_GENERATION_TIMEOUT
from app.models import AIChartGenerationRequest, AIChartGenerationResponse


def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names by removing newlines, extra whitespace, and other problematic characters.
    Returns a copy of the dataframe with cleaned column names.
    """
    df = df.copy()
    
    # Create a mapping of old names to new names
    new_columns = {}
    for col in df.columns:
        # Convert to string in case of non-string column names
        new_name = str(col)
        # Replace actual newlines and carriage returns with spaces
        new_name = new_name.replace('\n', ' ').replace('\r', ' ')
        # Replace literal escape sequences (e.g., "\\n" as text) with spaces
        new_name = new_name.replace('\\n', ' ').replace('\\r', ' ').replace('\\t', ' ')
        # Replace tabs with spaces
        new_name = new_name.replace('\t', ' ')
        # Collapse multiple spaces into one
        new_name = ' '.join(new_name.split())
        # Strip leading/trailing whitespace
        new_name = new_name.strip()
        new_columns[col] = new_name
    
    df.rename(columns=new_columns, inplace=True)
    return df


# Default base prompt for chart generation
DEFAULT_BASE_PROMPT = """You are an expert data visualization assistant. Your task is to write Python code that creates beautiful, informative charts using Plotly.

IMPORTANT RULES:
1. You have access to a pandas DataFrame called `df` with the data
2. You must create a Plotly figure and assign it to a variable called `fig`
3. Use plotly.express (imported as `px`) or plotly.graph_objects (imported as `go`)
4. Make the chart visually appealing with proper titles, labels, and colors
5. Only output Python code, no explanations or markdown
6. Do NOT use any file operations, network calls, or system commands
7. Do NOT import any additional modules
8. The code should be self-contained and create exactly one figure

Available imports (already imported for you):
- pandas as pd
- numpy as np
- plotly.express as px
- plotly.graph_objects as go

Example output format:
```python
fig = px.bar(df, x='category', y='value', title='My Chart', color='category')
fig.update_layout(template='plotly_white')
```
"""


def _get_dataframe_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a concise schema description of the dataframe for the AI"""
    schema = {
        "columns": [],
        "row_count": len(df),
        "sample_data": df.head(5).to_dict(orient='records')
    }
    
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "unique_count": int(df[col].nunique())
        }
        
        # Add sample values
        sample_values = df[col].dropna().head(3).tolist()
        col_info["sample_values"] = [str(v) for v in sample_values]
        
        # Add numeric stats if applicable
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["min"] = float(df[col].min()) if not pd.isna(df[col].min()) else None
            col_info["max"] = float(df[col].max()) if not pd.isna(df[col].max()) else None
            col_info["mean"] = float(df[col].mean()) if not pd.isna(df[col].mean()) else None
        
        schema["columns"].append(col_info)
    
    return schema


def _generate_chart_code(
    schema: Dict[str, Any],
    user_instructions: Optional[str],
    base_prompt: Optional[str]
) -> tuple[str, str]:
    """
    Use OpenAI to generate Python code for chart creation.
    Returns tuple of (code, explanation)
    """
    client = OpenAI()  # Uses OPENAI_API_KEY from environment
    
    system_prompt = base_prompt or DEFAULT_BASE_PROMPT
    
    user_message = f"""Dataset Schema:
{json.dumps(schema, indent=2, default=str)}

"""
    if user_instructions:
        user_message += f"User Request: {user_instructions}"
    else:
        user_message += "Create the most appropriate and insightful visualization for this data."
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    code_response = response.choices[0].message.content.strip()
    
    # Extract code from markdown code blocks if present
    if "```python" in code_response:
        code_response = code_response.split("```python")[1].split("```")[0].strip()
    elif "```" in code_response:
        code_response = code_response.split("```")[1].split("```")[0].strip()
    
    # Generate explanation
    explanation_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Briefly explain what this chart shows and why it's useful. Keep it to 1-2 sentences."},
            {"role": "user", "content": f"Code:\n{code_response}\n\nData columns: {[c['name'] for c in schema['columns']]}"}
        ],
        temperature=0.5,
        max_tokens=150
    )
    
    explanation = explanation_response.choices[0].message.content.strip()
    
    return code_response, explanation


def _create_restricted_globals(df: pd.DataFrame) -> Dict[str, Any]:
    """Create a restricted globals dictionary for safe code execution"""
    
    # Custom _getattr_ that allows access to safe attributes
    def guarded_getattr(obj, name):
        # Block access to dangerous attributes
        dangerous_attrs = {
            '__class__', '__bases__', '__subclasses__', '__mro__',
            '__code__', '__globals__', '__builtins__', '__import__',
            '__reduce__', '__reduce_ex__', 'gi_frame', 'gi_code',
            'f_locals', 'f_globals', 'f_builtins', 'f_code'
        }
        if name in dangerous_attrs:
            raise AttributeError(f"Access to '{name}' is not allowed")
        return getattr(obj, name)
    
    # Custom _getitem_ for safe indexing
    def guarded_getitem(obj, index):
        return obj[index]
    
    restricted_globals = {
        '__builtins__': {
            'True': True,
            'False': False,
            'None': None,
            'abs': abs,
            'all': all,
            'any': any,
            'bool': bool,
            'dict': dict,
            'enumerate': enumerate,
            'filter': filter,
            'float': float,
            'format': format,
            'frozenset': frozenset,
            'int': int,
            'len': len,
            'list': list,
            'map': map,
            'max': max,
            'min': min,
            'print': print,
            'range': range,
            'reversed': reversed,
            'round': round,
            'set': set,
            'sorted': sorted,
            'str': str,
            'sum': sum,
            'tuple': tuple,
            'zip': zip,
            'isinstance': isinstance,
            'type': type,
        },
        '_getattr_': guarded_getattr,
        '_getitem_': guarded_getitem,
        '_getiter_': default_guarded_getiter,
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        
        # Write guard - allows attribute/item assignment
        # Using a simple pass-through since we trust pandas/plotly operations
        '_write_': lambda x: x,
        
        # Inplace binary operations (+=, -=, etc.)
        '_inplacevar_': lambda op, x, y: op(x, y),
        
        # Data and visualization libraries
        'df': df,
        'pd': pd,
        'np': np,
        'px': px,
        'go': go,
    }
    
    return restricted_globals


def _execute_code_safely(code: str, df: pd.DataFrame) -> Any:
    """
    Execute the generated code in a restricted environment using RestrictedPython.
    Returns the created Plotly figure.
    """
    # Compile with RestrictedPython
    try:
        byte_code = compile_restricted(
            code,
            filename='<ai_generated>',
            mode='exec'
        )
    except SyntaxError as e:
        raise ValueError(f"Syntax error in generated code: {e}")
    
    # Check for compilation errors
    if byte_code is None:
        raise ValueError("Code compilation failed - potentially unsafe code detected")
    
    # Create restricted execution environment
    restricted_globals = _create_restricted_globals(df)
    restricted_locals = {}
    
    # Execute the code
    try:
        exec(byte_code, restricted_globals, restricted_locals)
    except Exception as e:
        raise ValueError(f"Error executing generated code: {str(e)}")
    
    # Extract the figure
    if 'fig' not in restricted_locals:
        raise ValueError("Generated code did not create a 'fig' variable")
    
    fig = restricted_locals['fig']
    
    # Validate it's a Plotly figure
    if not isinstance(fig, (go.Figure,)):
        raise ValueError(f"Generated 'fig' is not a Plotly Figure, got {type(fig)}")
    
    return fig


@with_timeout(CHART_GENERATION_TIMEOUT)
def generate_ai_chart(request: AIChartGenerationRequest) -> AIChartGenerationResponse:
    """
    Generate a chart using AI to write the visualization code.
    
    Args:
        request: AIChartGenerationRequest with file_id, optional user_instructions, and optional base_prompt
        
    Returns:
        AIChartGenerationResponse with chart JSON, generated code, and explanation
    """
    try:
        # Get the dataframe
        df = get_dataframe(request.file_id)
        
        # Clean column names (remove newlines, extra whitespace, etc.)
        df = _clean_column_names(df)
        
        # Generate schema for AI
        schema = _get_dataframe_schema(df)
        
        # Generate code using AI
        generated_code, explanation = _generate_chart_code(
            schema=schema,
            user_instructions=request.user_instructions,
            base_prompt=request.base_prompt
        )
        
        # Execute code safely
        fig = _execute_code_safely(generated_code, df)
        
        # Convert to JSON
        chart_json = json.loads(fig.to_json())
        
        return AIChartGenerationResponse(
            chart_json=chart_json,
            generated_code=generated_code,
            explanation=explanation,
            message="AI chart generated successfully"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating AI chart: {str(e)}"
        )
