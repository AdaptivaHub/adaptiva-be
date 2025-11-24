import plotly.express as px
import plotly.graph_objects as go
from fastapi import HTTPException
from typing import Dict, Any

from app.utils import get_dataframe
from app.models import ChartGenerationRequest, ChartGenerationResponse, ChartType


def generate_chart(request: ChartGenerationRequest) -> ChartGenerationResponse:
    """
    Generate a chart using Plotly
    
    Args:
        request: ChartGenerationRequest with chart parameters
        
    Returns:
        ChartGenerationResponse with chart JSON
    """
    try:
        # Get the dataframe
        df = get_dataframe(request.file_id)
        
        # Validate columns exist
        if request.x_column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{request.x_column}' not found in dataset"
            )
        
        if request.y_column and request.y_column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{request.y_column}' not found in dataset"
            )
        
        if request.color_column and request.color_column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{request.color_column}' not found in dataset"
            )
        
        # Generate chart based on type
        fig = None
        
        if request.chart_type == ChartType.BAR:
            if not request.y_column:
                raise HTTPException(
                    status_code=400,
                    detail="y_column is required for bar charts"
                )
            fig = px.bar(
                df,
                x=request.x_column,
                y=request.y_column,
                title=request.title,
                color=request.color_column
            )
        
        elif request.chart_type == ChartType.LINE:
            if not request.y_column:
                raise HTTPException(
                    status_code=400,
                    detail="y_column is required for line charts"
                )
            fig = px.line(
                df,
                x=request.x_column,
                y=request.y_column,
                title=request.title,
                color=request.color_column
            )
        
        elif request.chart_type == ChartType.SCATTER:
            if not request.y_column:
                raise HTTPException(
                    status_code=400,
                    detail="y_column is required for scatter plots"
                )
            fig = px.scatter(
                df,
                x=request.x_column,
                y=request.y_column,
                title=request.title,
                color=request.color_column
            )
        
        elif request.chart_type == ChartType.HISTOGRAM:
            fig = px.histogram(
                df,
                x=request.x_column,
                title=request.title,
                color=request.color_column
            )
        
        elif request.chart_type == ChartType.BOX:
            fig = px.box(
                df,
                x=request.x_column,
                y=request.y_column,
                title=request.title,
                color=request.color_column
            )
        
        elif request.chart_type == ChartType.PIE:
            if not request.y_column:
                # Use value counts for pie chart
                value_counts = df[request.x_column].value_counts()
                fig = px.pie(
                    values=value_counts.values,
                    names=value_counts.index,
                    title=request.title
                )
            else:
                fig = px.pie(
                    df,
                    values=request.y_column,
                    names=request.x_column,
                    title=request.title
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported chart type: {request.chart_type}"
            )
        
        # Convert to JSON
        chart_json = fig.to_json()
        
        # Parse JSON to dict for response
        import json
        chart_dict = json.loads(chart_json)
        
        # Prepare response
        response = ChartGenerationResponse(
            chart_json=chart_dict,
            message="Chart generated successfully"
        )
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")
