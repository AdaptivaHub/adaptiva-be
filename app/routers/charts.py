from fastapi import APIRouter
from app.models import ChartGenerationRequest, ChartGenerationResponse, ErrorResponse
from app.services import generate_chart

router = APIRouter(prefix="/charts", tags=["Chart Generation"])


@router.post(
    "/",
    response_model=ChartGenerationResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate chart",
    description="Generate interactive charts using Plotly. Supports bar, line, scatter, histogram, box, and pie charts"
)
def create_chart(request: ChartGenerationRequest):
    """
    Generate a chart from the dataset.
    
    - **file_id**: The file identifier returned from upload
    - **chart_type**: Type of chart (bar, line, scatter, histogram, box, pie)
    - **x_column**: Column name for x-axis
    - **y_column**: Column name for y-axis (optional for histogram, pie)
    - **title**: Chart title (optional)
    - **color_column**: Column name for color grouping (optional)
    
    Returns JSON representation of the Plotly chart.
    """
    return generate_chart(request)
