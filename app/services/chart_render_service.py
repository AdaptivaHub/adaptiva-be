"""
Chart render service.

Converts ChartSpec → Plotly JSON. This is the single render path for all charts.
No AI, no metering - just data transformation.
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.models.chart_spec import (
    ChartSpec,
    COLOR_PALETTES,
    FilterCondition,
)
from app.services.chart_validation import validate_chart_spec
from app.utils import storage


class ChartRenderError(Exception):
    """Raised when chart rendering fails."""
    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        super().__init__(message)
        self.errors = errors or []


def apply_filters(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
    """
    Apply filter conditions to the dataframe.
    
    Args:
        df: Input dataframe
        spec: ChartSpec with optional filters
        
    Returns:
        Filtered dataframe
    """
    if not spec.filters or not spec.filters.conditions:
        return df
    
    masks = []
    for condition in spec.filters.conditions:
        mask = _apply_single_filter(df, condition)
        masks.append(mask)
    
    if not masks:
        return df
    
    # Combine masks with AND or OR logic
    if spec.filters.logic == "and":
        combined_mask = masks[0]
        for mask in masks[1:]:
            combined_mask = combined_mask & mask
    else:  # "or"
        combined_mask = masks[0]
        for mask in masks[1:]:
            combined_mask = combined_mask | mask
    
    return df[combined_mask].copy()


def _apply_single_filter(df: pd.DataFrame, condition: FilterCondition) -> pd.Series:
    """Apply a single filter condition and return a boolean mask."""
    col = condition.column
    op = condition.operator
    val = condition.value
    
    # For comparison operators, attempt numeric conversion if value is numeric
    if op in ("gt", "gte", "lt", "lte", "between"):
        try:
            col_values = pd.to_numeric(df[col], errors='coerce')
        except (ValueError, TypeError):
            col_values = df[col]
    else:
        col_values = df[col]
    
    if op == "eq":
        return df[col] == val
    elif op == "ne":
        return df[col] != val
    elif op == "gt":
        return col_values > val
    elif op == "gte":
        return col_values >= val
    elif op == "lt":
        return col_values < val
    elif op == "lte":
        return col_values <= val
    elif op == "in":
        return df[col].isin(val if isinstance(val, list) else [val])
    elif op == "not_in":
        return ~df[col].isin(val if isinstance(val, list) else [val])
    elif op == "between":
        return (col_values >= val) & (col_values <= condition.value_end)
    elif op == "contains":
        return df[col].astype(str).str.contains(str(val), case=False, na=False)
    else:
        # Default: no filter
        return pd.Series([True] * len(df), index=df.index)


def apply_aggregation(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
    """
    Apply aggregation to the dataframe.
    
    Args:
        df: Input dataframe
        spec: ChartSpec with aggregation config
        
    Returns:
        Aggregated dataframe
    """
    if spec.aggregation.method == "none" or not spec.aggregation.group_by:
        return df
    
    group_cols = spec.aggregation.group_by
    method = spec.aggregation.method
    
    # Determine which columns to aggregate (y_axis columns)
    agg_cols = []
    if spec.y_axis and spec.y_axis.columns:
        agg_cols = [c for c in spec.y_axis.columns if c in df.columns]
    
    if not agg_cols:
        return df
    
    # Build aggregation dict
    agg_dict = {}
    for col in agg_cols:
        if method == "sum":
            agg_dict[col] = "sum"
        elif method == "mean":
            agg_dict[col] = "mean"
        elif method == "count":
            agg_dict[col] = "count"
        elif method == "median":
            agg_dict[col] = "median"
        elif method == "min":
            agg_dict[col] = "min"
        elif method == "max":
            agg_dict[col] = "max"
    
    if not agg_dict:
        return df
    
    # Perform aggregation
    result = df.groupby(group_cols, as_index=False).agg(agg_dict)
    return result


def build_plotly_figure(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    """
    Build a Plotly figure from the dataframe and spec.
    
    Args:
        df: Prepared dataframe (filtered, aggregated)
        spec: ChartSpec with chart configuration
        
    Returns:
        Plotly Figure object
    """
    chart_type = spec.chart_type
    x_col = spec.x_axis.column
    y_cols = spec.y_axis.columns if spec.y_axis else []
    title = spec.visual.title
    color_col = spec.series.group_column if spec.series else None
    
    fig = None
    
    if chart_type == "bar":
        if len(y_cols) == 1 and not color_col:
            fig = px.bar(df, x=x_col, y=y_cols[0], title=title, color=color_col)
        elif len(y_cols) == 1 and color_col:
            fig = px.bar(df, x=x_col, y=y_cols[0], title=title, color=color_col)
        else:
            # Multiple y columns - create traces
            fig = go.Figure()
            for y_col in y_cols:
                fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=y_col))
            fig.update_layout(title=title, barmode="group")
    
    elif chart_type == "line":
        if len(y_cols) == 1 and not color_col:
            fig = px.line(df, x=x_col, y=y_cols[0], title=title, color=color_col)
        elif len(y_cols) == 1 and color_col:
            fig = px.line(df, x=x_col, y=y_cols[0], title=title, color=color_col)
        else:
            fig = go.Figure()
            for y_col in y_cols:
                fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode="lines", name=y_col))
            fig.update_layout(title=title)
    
    elif chart_type == "scatter":
        size_col = spec.series.size_column if spec.series else None
        if len(y_cols) >= 1:
            fig = px.scatter(df, x=x_col, y=y_cols[0], title=title, color=color_col, size=size_col)
        else:
            fig = px.scatter(df, x=x_col, title=title, color=color_col)
    
    elif chart_type == "histogram":
        fig = px.histogram(df, x=x_col, title=title, color=color_col)
    
    elif chart_type == "box":
        if y_cols:
            fig = px.box(df, x=x_col, y=y_cols[0], title=title, color=color_col)
        else:
            fig = px.box(df, x=x_col, title=title, color=color_col)
    
    elif chart_type == "pie":
        if y_cols:
            fig = px.pie(df, names=x_col, values=y_cols[0], title=title)
        else:
            # Use value counts
            value_counts = df[x_col].value_counts()
            fig = px.pie(values=value_counts.values, names=value_counts.index, title=title)
    
    elif chart_type == "area":
        if len(y_cols) == 1:
            fig = px.area(df, x=x_col, y=y_cols[0], title=title, color=color_col)
        else:
            fig = go.Figure()
            for y_col in y_cols:
                fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], fill="tozeroy", name=y_col))
            fig.update_layout(title=title)
    
    elif chart_type == "heatmap":
        if len(y_cols) >= 1:
            # Create pivot table for heatmap
            if color_col:
                pivot = df.pivot_table(index=x_col, columns=color_col, values=y_cols[0], aggfunc="mean")
                fig = px.imshow(pivot, title=title)
            else:
                fig = px.density_heatmap(df, x=x_col, y=y_cols[0], title=title)
        else:
            fig = go.Figure()
            fig.update_layout(title=title)
    
    else:
        # Fallback
        fig = go.Figure()
        fig.update_layout(title=title or "Chart")
    
    # Apply stacking if configured
    if spec.visual.stacking == "stacked":
        fig.update_layout(barmode="stack")
    elif spec.visual.stacking == "percent":
        fig.update_layout(barmode="stack", barnorm="percent")
    
    # Apply axis labels
    if spec.x_axis.label:
        fig.update_xaxes(title_text=spec.x_axis.label)
    if spec.y_axis and spec.y_axis.label:
        fig.update_yaxes(title_text=spec.y_axis.label)
    
    # Apply legend settings
    if not spec.legend.visible:
        fig.update_layout(showlegend=False)
    else:
        legend_position = _get_legend_position(spec.legend.position)
        fig.update_layout(legend=legend_position)
    
    return fig


def _get_legend_position(position: str) -> Dict[str, Any]:
    """Convert legend position enum to Plotly legend config."""
    positions = {
        "top": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        "bottom": {"orientation": "h", "yanchor": "top", "y": -0.15, "xanchor": "center", "x": 0.5},
        "left": {"yanchor": "middle", "y": 0.5, "xanchor": "right", "x": -0.15},
        "right": {"yanchor": "middle", "y": 0.5, "xanchor": "left", "x": 1.02},
        "none": {},
    }
    return positions.get(position, {})


def apply_styling(fig: go.Figure, spec: ChartSpec) -> go.Figure:
    """
    Apply styling presets to the figure.
    
    Args:
        fig: Plotly figure
        spec: ChartSpec with styling config
        
    Returns:
        Styled Plotly figure
    """
    # Apply color palette
    palette = COLOR_PALETTES.get(spec.styling.color_palette, COLOR_PALETTES["default"])
    fig.update_layout(colorway=palette)
    
    # Apply theme
    if spec.styling.theme == "dark":
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e1e",
            plot_bgcolor="#1e1e1e",
        )
    else:
        fig.update_layout(template="plotly_white")
    
    # Apply data labels
    if spec.styling.show_data_labels:
        fig.update_traces(textposition="outside")
        for trace in fig.data:
            if hasattr(trace, "text"):
                trace.textposition = "outside"
    
    # Apply interaction settings
    config = {
        "scrollZoom": spec.interaction.zoom_scroll,
        "responsive": spec.interaction.responsive,
    }
    
    # Modebar display
    if spec.interaction.modebar == "hidden":
        config["displayModeBar"] = False
    elif spec.interaction.modebar == "always":
        config["displayModeBar"] = True
    # "hover" is the default
    
    return fig


def render_chart(spec: ChartSpec) -> Dict[str, Any]:
    """
    Main render function - converts ChartSpec to Plotly JSON.
    
    This is the single render path for all charts (manual and AI-generated).
    
    Args:
        spec: The ChartSpec to render
        
    Returns:
        Dict with chart_json, rendered_at, and spec_version
        
    Raises:
        ChartRenderError: If rendering fails
    """
    # Load dataframe
    try:
        df = storage.get_dataframe(spec.file_id, spec.sheet_name)
    except ValueError as e:
        raise ChartRenderError(f"File not found: {e}", errors=[{
            "field": "file_id",
            "code": "file_not_found",
                        "message": str(e)
        }])
    
    # Validate spec against data (pass the already-loaded dataframe)
    validation_result = validate_chart_spec(spec, df=df)
    if not validation_result.valid:
        error_dicts = [
            {"field": e.field, "code": e.code, "message": e.message}
            for e in validation_result.errors
        ]
        raise ChartRenderError(
            f"Validation failed: {len(validation_result.errors)} error(s)",
            errors=error_dicts
        )
    
    # Apply filters
    df = apply_filters(df, spec)
    
    # Apply aggregation
    df = apply_aggregation(df, spec)
    
    # Build Plotly figure
    fig = build_plotly_figure(df, spec)
    
    # Apply styling
    fig = apply_styling(fig, spec)
    
    # Convert to JSON
    chart_json = json.loads(fig.to_json())
    
    return {
        "chart_json": chart_json,
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "spec_version": spec.version,
    }
