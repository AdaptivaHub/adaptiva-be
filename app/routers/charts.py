from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.models import (
    ChartGenerationRequest, 
    ChartGenerationResponse, 
    AIChartGenerationRequest,
    AIChartGenerationResponse,
    ErrorResponse,
    RateLimitExceededResponse
)
from app.models.user import User
from app.services import generate_chart, generate_ai_chart
from app.services import rate_limit_service
from app.utils.deps import get_optional_user, get_client_ip
from app.config import get_settings

settings = get_settings()
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
    responses={
        400: {"model": ErrorResponse}, 
        404: {"model": ErrorResponse}, 
        429: {"model": RateLimitExceededResponse},
        500: {"model": ErrorResponse}
    },
    summary="Generate chart using AI",
    description="Use AI to analyze your data and generate the most appropriate visualization automatically. Anonymous users are limited to 3 requests per day."
)
def create_ai_chart(
    request: AIChartGenerationRequest,
    http_request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Generate a chart using AI to write the visualization code.
    
    - **file_id**: The file identifier returned from upload
    - **user_instructions**: Optional instructions for what kind of chart to create (e.g., "Show sales trends over time")
    - **base_prompt**: Optional system-level prompt to customize AI behavior
    
    The AI will analyze your data schema and generate Python/Plotly code to create
    an appropriate visualization. The code is executed in a sandboxed environment.
    
    **Rate Limiting (Anonymous Users):**
    - Anonymous users are limited to 3 AI chart requests per 24-hour rolling window
    - Authenticated users have unlimited access
    
    Returns:
    - **chart_json**: Plotly JSON that can be rendered in the frontend
    - **generated_code**: The Python code that was generated and executed
    - **explanation**: Brief explanation of what the chart shows
    """
    # Get client IP
    client_ip = get_client_ip(http_request)
    
    # Get or create anonymous session token
    session_token = http_request.headers.get("X-Anonymous-Session")
    session_id = None
    
    if session_token:
        session_id = rate_limit_service.validate_anonymous_session(session_token)
    
    # If no valid session, create new one
    if not session_id:
        session_token = rate_limit_service.create_anonymous_session()
        session_id = rate_limit_service.validate_anonymous_session(session_token)
    
    # Add session token to response header
    response.headers["X-Anonymous-Session"] = session_token
    
    # If user is authenticated, bypass rate limiting
    if current_user:
        return generate_ai_chart(request)
    
    # Check burst limit first (prevents rapid-fire abuse)
    if rate_limit_service.check_burst_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down."
        )
    
    # Check global limit
    if rate_limit_service.check_global_limit():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Service is currently at capacity. Please try again later or sign up for an account."
        )
    
    # Get combined usage (anti-bypass: uses max of IP and session count)
    usage = rate_limit_service.get_combined_usage(client_ip, session_id)
    
    # Check if limit exceeded
    if usage >= settings.ANONYMOUS_DAILY_LIMIT:
        rate_info = rate_limit_service.get_rate_limit_info(client_ip, session_id)
        from datetime import datetime
        reset_at = datetime.fromtimestamp(rate_info["reset"]).isoformat() + "Z"
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": "Daily AI query limit reached",
                "queries_used": rate_info["used"],
                "queries_limit": rate_info["limit"],
                "reset_at": reset_at,
                "message": "Sign up for free to get unlimited AI queries!"
            }
        )
    
    # Record the request BEFORE processing (to prevent race conditions)
    rate_limit_service.increment_usage(client_ip, session_id)
    rate_limit_service.increment_global_count()
    rate_limit_service.record_burst_request(client_ip)
    
    # Add rate limit headers
    rate_info = rate_limit_service.get_rate_limit_info(client_ip, session_id)
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
    
    return generate_ai_chart(request)
