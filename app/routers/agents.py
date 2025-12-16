"""
Agents Router - Multi-agent AI endpoints for forecasting, marketing, and content generation
Rate limited to $0.20/day per IP for AI endpoints.
"""
from fastapi import APIRouter, Request, Depends
from app.models import (
    ErrorResponse,
    ForecastRequest,
    ForecastResponse,
    ForecastableColumnsResponse,
    MarketingStrategyRequest,
    MarketingStrategyResponse,
    ContentGenerationRequest,
    ContentGenerationResponse,
    AgentPipelineRequest,
    AgentPipelineResponse,
    UsageStatsResponse
)
from app.services import (
    generate_forecast,
    get_forecastable_columns,
    generate_marketing_strategy,
    generate_ad_content,
    run_agent_pipeline
)
from app.utils import require_rate_limit, record_usage, get_usage_stats

router = APIRouter(prefix="/agents", tags=["AI Agents"])


# ============================================================================
# USAGE STATS ENDPOINT
# ============================================================================

@router.get(
    "/usage",
    response_model=UsageStatsResponse,
    summary="Get usage statistics",
    description="Get your current API usage statistics for today"
)
def get_my_usage(request: Request):
    """
    Get your current AI API usage statistics.
    
    Returns:
    - Current cost used today (in cents)
    - Number of requests made
    - Daily limit
    - Remaining budget
    
    Usage resets at midnight UTC.
    """
    stats = get_usage_stats(request)
    return UsageStatsResponse(
        **stats,
        message=f"Used ${stats['cost_cents']/100:.4f} of ${stats['limit_cents']/100:.2f} daily limit"
    )


# ============================================================================
# FORECAST ENDPOINTS
# ============================================================================

@router.get(
    "/forecast/columns/{file_id}",
    response_model=ForecastableColumnsResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get forecastable columns",
    description="Detect which columns in a dataset can be forecasted using time-series analysis"
)
def get_forecast_columns(file_id: str):
    """
    Detect forecastable columns in the dataset.
    
    Returns columns that:
    - Have a paired date column
    - Contain numeric values suitable for forecasting
    - Have keywords like 'sales', 'revenue', 'quantity', etc.
    """
    return get_forecastable_columns(file_id)


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate forecast",
    description="Generate time-series forecast using Prophet. Columns are auto-detected if not specified."
)
def create_forecast(request: ForecastRequest):
    """
    Generate time-series forecast.
    
    - **file_id**: The file identifier returned from upload
    - **date_column**: Column containing dates (auto-detected if not specified)
    - **target_column**: Column to forecast (auto-detected if not specified)
    - **periods**: Number of future periods to predict (1-365 days)
    
    Returns predictions with confidence intervals and trend analysis.
    """
    return generate_forecast(request)


# ============================================================================
# MARKETING STRATEGY ENDPOINTS
# ============================================================================

@router.post(
    "/marketing/strategy",
    response_model=MarketingStrategyResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate marketing strategy",
    description="Use AI to generate data-driven marketing campaigns based on your business data. Rate limited."
)
def create_marketing_strategy(
    request: MarketingStrategyRequest,
    req: Request,
    _: None = Depends(require_rate_limit(estimated_cost_cents=1.0))
):
    """
    Generate AI-powered marketing strategy.
    
    - **file_id**: The file identifier returned from upload
    - **business_name**: Name of your business (optional)
    - **business_type**: Type of business, e.g., 'retail', 'e-commerce' (optional)
    - **target_audience**: Description of target customers (optional)
    - **forecast_trend**: Trend from previous forecast analysis (optional)
    - **additional_context**: Any additional business context (optional)
    
    Returns 2-3 concrete marketing campaigns with tactics and expected outcomes.
    Rate limited to ~$0.20/day per IP.
    """
    result = generate_marketing_strategy(request)
    record_usage(req, input_tokens=800, output_tokens=500, model="gpt-4o-mini")
    return result


# ============================================================================
# CONTENT GENERATION ENDPOINTS
# ============================================================================

@router.post(
    "/content/generate",
    response_model=ContentGenerationResponse,
    responses={429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate ad content",
    description="Generate ad content including copy and optional AI-generated images using Pollinations AI (free). Rate limited."
)
def create_ad_content(
    request: ContentGenerationRequest,
    req: Request,
    _: None = Depends(require_rate_limit(estimated_cost_cents=0.5))
):
    """
    Generate ad content for a marketing campaign.
    
    - **campaign_name**: Name of the campaign
    - **campaign_theme**: Main theme/message of the campaign
    - **target_audience**: Who the ad is targeting
    - **tactics**: List of marketing tactics to highlight
    - **platform**: Target platform (social_media, email, website)
    - **tone**: Content tone (professional, casual, exciting, urgent)
    - **include_image**: Generate image URL using Pollinations AI (free, no API key needed)
    
    Returns headline, caption, description, hashtags, CTA, and optional image URL.
    Rate limited to ~$0.20/day per IP.
    """
    result = generate_ad_content(request)
    record_usage(req, input_tokens=400, output_tokens=300, model="gpt-4o-mini")
    return result


# ============================================================================
# ORCHESTRATOR ENDPOINTS
# ============================================================================

@router.post(
    "/pipeline",
    response_model=AgentPipelineResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Run full agent pipeline",
    description="Run the complete AI agent pipeline: Insights → Forecast → Marketing → Content. Rate limited."
)
def run_pipeline(
    request: AgentPipelineRequest,
    req: Request,
    _: None = Depends(require_rate_limit(estimated_cost_cents=2.0))
):
    """
    Run the full AI agent pipeline sequentially.
    
    Steps:
    1. **Insights** (always runs) - Analyze dataset statistics
    2. **Forecast** (optional) - Generate time-series predictions
    3. **Marketing** (optional) - Create marketing strategy based on data
    4. **Content** (optional) - Generate ad content for first campaign
    
    Each step builds on previous results. Configure which steps to run.
    
    - **file_id**: The file identifier returned from upload
    - **business_name**: Name of your business (optional)
    - **business_type**: Type of business (optional)
    - **target_audience**: Target customer description (optional)
    - **run_forecast**: Include forecasting step (default: true)
    - **run_marketing**: Include marketing strategy step (default: true)
    - **run_content**: Include content generation step (default: true)
    - **forecast_periods**: Number of periods to forecast (default: 30)
    
    Returns results from all completed steps.
    Rate limited to ~$0.20/day per IP.
    """
    result = run_agent_pipeline(request)
    # Estimate tokens based on which steps ran
    total_input = 500  # base
    total_output = 200
    if request.run_marketing:
        total_input += 800
        total_output += 500
    if request.run_content:
        total_input += 400
        total_output += 300
    record_usage(req, input_tokens=total_input, output_tokens=total_output, model="gpt-4o-mini")
    return result
