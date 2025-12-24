"""
Charts router - unified chart generation API.

Endpoints:
- POST /api/charts/render - Render ChartSpec → Plotly JSON (no AI cost)
- POST /api/charts/validate - Pre-flight validation (no AI cost)
- POST /api/charts/suggest - AI generates ChartSpec (rate-limited, metered)
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.models.chart_spec import (
    ChartRenderRequest,
    ChartRenderResponse,
    ChartValidateRequest,
    ChartValidateResponse,
    AISuggestRequest,
    AISuggestResponse,
)
from app.models import ErrorResponse
from app.services import render_chart, ChartRenderError, validate_chart_spec
from app.services.ai_suggest_service import generate_chart_suggestion, AISuggestError
from app.services import rate_limit_service
from app.services import auth_service
from app.config import get_settings

settings = get_settings()


router = APIRouter(prefix="/charts", tags=["Chart Generation"])


@router.post(
    "/render",
    response_model=ChartRenderResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Render chart from ChartSpec",
    description="Convert a ChartSpec into Plotly JSON. This is the single render path for all charts (manual and AI-generated). No AI cost, no rate limiting."
)
def render_chart_endpoint(request: ChartRenderRequest):
    """
    Render a chart from a ChartSpec.
    
    The ChartSpec contains all chart configuration:
    - **file_id**: Data source reference
    - **chart_type**: Type of chart (bar, line, scatter, etc.)
    - **x_axis**: X-axis column configuration
    - **y_axis**: Y-axis column(s) configuration
    - **series**: Grouping/color configuration
    - **aggregation**: Data aggregation settings
    - **filters**: Data filtering conditions
    - **visual**: Title, stacking, legend settings
    - **styling**: Color palette, theme, data labels
    
    Returns Plotly JSON that can be rendered in the frontend.
    """
    try:
        result = render_chart(request.spec)
        return ChartRenderResponse(
            chart_json=result["chart_json"],
            rendered_at=result["rendered_at"],
            spec_version=result["spec_version"]
        )
    except ChartRenderError as e:
        # Determine appropriate status code
        if any(err.get("code") == "file_not_found" for err in e.errors):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": str(e), "errors": e.errors}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": str(e), "errors": e.errors}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Unexpected error: {str(e)}"}
        )


@router.post(
    "/validate",
    response_model=ChartValidateResponse,
    responses={
        500: {"model": ErrorResponse}
    },
    summary="Validate ChartSpec",
    description="Pre-flight validation without rendering. Returns errors and warnings. No AI cost, no rate limiting."
)
def validate_chart_endpoint(request: ChartValidateRequest):
    """
    Validate a ChartSpec without rendering.
    
    Checks:
    - Column existence in the data
    - Chart-type-specific requirements (e.g., bar charts need y_axis)
    - Column type compatibility (returns warnings)
    
    Returns validation result with errors and warnings.
    """
    try:
        result = validate_chart_spec(request.spec)
        return ChartValidateResponse(
            valid=result.valid,
            errors=[
                {"field": e.field, "code": e.code, "message": e.message, "suggestion": e.suggestion}
                for e in result.errors
            ],
            warnings=[
                {"field": w.field, "code": w.code, "message": w.message, "suggestion": w.suggestion}
                for w in result.warnings
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Validation error: {str(e)}"}
        )


# =============================================================================
# Helper Functions for Rate Limiting
# =============================================================================

def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies."""
    # Check X-Forwarded-For header (set by reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (client's original IP)
        return forwarded_for.split(",")[0].strip()
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


def get_session_token(request: Request) -> Optional[str]:
    """Get anonymous session token from request header."""
    return request.headers.get("X-Anonymous-Session")


def add_rate_limit_headers(response: Response, rate_info: dict, session_token: Optional[str] = None):
    """Add rate limit headers to response."""
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
    response.headers["X-RateLimit-Used"] = str(rate_info["used"])
    if session_token:
        response.headers["X-Anonymous-Session"] = session_token


# =============================================================================
# AI Suggest Endpoint
# =============================================================================

@router.post(
    "/suggest",
    response_model=AISuggestResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="AI-generated chart suggestion",
    description="Use AI to analyze data and suggest a ChartSpec. Rate-limited for anonymous users (3/day). Authenticated users have unlimited access."
)
def suggest_chart_endpoint(
    request: AISuggestRequest,
    http_request: Request,
    response: Response,
):
    """
    Generate an AI-powered chart suggestion.
    
    The AI analyzes the data schema and user instructions to suggest
    the best chart configuration. The response includes:
    - **suggested_spec**: Complete ChartSpec to render
    - **explanation**: Why this chart type was chosen
    - **confidence**: How confident the AI is (0-1)
    - **alternatives**: Other chart types that could work
    - **usage**: Token usage for billing
    
    Rate Limiting (anonymous users):
    - 3 requests per 24-hour rolling window
    - Tracked by IP + session token
    - Authenticated users bypass rate limits
    """
    client_ip = get_client_ip(http_request)
    session_token = get_session_token(http_request)
    session_id = None
    
    # Create or validate session token
    if session_token:
        session_id = rate_limit_service.validate_anonymous_session(session_token)
    
    if not session_id:
        # Create new session
        session_token = rate_limit_service.create_anonymous_session()
        session_id = rate_limit_service.validate_anonymous_session(session_token)
    
    # Check if user is authenticated (bypass rate limits)
    auth_header = http_request.headers.get("Authorization")
    is_authenticated = False
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            user_data = auth_service.validate_access_token(token)
            is_authenticated = user_data is not None
        except Exception:
            pass  # Invalid token, treat as anonymous
    
    # Rate limiting for anonymous users
    if not is_authenticated:
        # Check burst limit first
        if rate_limit_service.check_burst_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "Too many requests. Please wait a moment.",
                    "code": "burst_limit_exceeded"
                }
            )
        
        # Check global limit
        if rate_limit_service.check_global_limit():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "Service is experiencing high demand. Please try again later.",
                    "code": "global_limit_exceeded"
                }
            )
        
        # Check user-specific limit
        current_usage = rate_limit_service.get_combined_usage(client_ip, session_id)
        if current_usage >= settings.ANONYMOUS_DAILY_LIMIT:
            reset_time = rate_limit_service.get_reset_time(client_ip, session_id)
            rate_info = rate_limit_service.get_rate_limit_info(client_ip, session_id)
            add_rate_limit_headers(response, rate_info, session_token)
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "Daily AI query limit reached",
                    "code": "rate_limit_exceeded",
                    "queries_used": current_usage,
                    "queries_limit": settings.ANONYMOUS_DAILY_LIMIT,
                    "reset_at": reset_time.isoformat(),
                    "message": "Sign up for a free account to get unlimited AI suggestions!"
                }
            )
    
    # Call AI suggestion service
    try:
        result = generate_chart_suggestion(request)
    except AISuggestError as e:
        if e.code == "file_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": str(e), "code": e.code}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": str(e), "code": e.code, "details": e.details}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"AI suggestion failed: {str(e)}"}
        )
    
    # Increment usage counters (only for anonymous users)
    if not is_authenticated:
        rate_limit_service.increment_usage(client_ip, session_id)
        rate_limit_service.increment_global_count()
        rate_limit_service.record_burst_request(client_ip)
    
    # Add rate limit headers
    rate_info = rate_limit_service.get_rate_limit_info(client_ip, session_id)
    add_rate_limit_headers(response, rate_info, session_token)
    
    return result
