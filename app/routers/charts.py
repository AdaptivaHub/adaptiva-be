from fastapi import APIRouter, Request, Depends
from app.models import (
    ChartGenerationRequest, 
    ChartGenerationResponse, 
    AIChartGenerationRequest,
    AIChartGenerationResponse,
    ErrorResponse
)
from app.services import generate_chart, generate_ai_chart
from app.utils import require_rate_limit, record_usage

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


@router.post(
    "/ai",
    response_model=AIChartGenerationResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate chart using AI",
    description="Use AI to analyze your data and generate the most appropriate visualization automatically"
)
def create_ai_chart(
    request: AIChartGenerationRequest,
    req: Request,
    _: None = Depends(require_rate_limit(estimated_cost_cents=0.5))
):
    """
    Generate a chart using AI to write the visualization code.
    
    - **file_id**: The file identifier returned from upload
    - **user_instructions**: Optional instructions for what kind of chart to create (e.g., "Show sales trends over time")
    - **base_prompt**: Optional system-level prompt to customize AI behavior
    
    The AI will analyze your data schema and generate Python/Plotly code to create
    an appropriate visualization. The code is executed in a sandboxed environment.
    
    Returns:
    - **chart_json**: Plotly JSON that can be rendered in the frontend
    - **generated_code**: The Python code that was generated and executed
    - **explanation**: Brief explanation of what the chart shows
    
    Rate limited to ~$0.20/day per IP.
    """
    result = generate_ai_chart(request)
    # Record approximate usage (estimate ~500 input, ~300 output tokens)
    record_usage(req, input_tokens=500, output_tokens=300, model="gpt-4o-mini")
    return result
