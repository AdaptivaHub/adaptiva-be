"""
Orchestrator Service - Coordinates all AI agents in a pipeline
Ported from Multi-Agent-System-for-SMEs
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException

from app.utils import get_dataframe
from app.models import (
    AgentPipelineRequest,
    AgentPipelineResponse,
    ForecastRequest,
    MarketingStrategyRequest,
    ContentGenerationRequest
)
from app.services.insights_service import get_data_insights
from app.services.forecast_service import generate_forecast, get_forecastable_columns
from app.services.marketing_service import generate_marketing_strategy
from app.services.content_service import generate_ad_content


def run_agent_pipeline(request: AgentPipelineRequest) -> AgentPipelineResponse:
    """
    Run the full AI agent pipeline sequentially:
    1. Data Insights (always runs)
    2. Forecasting (optional)
    3. Marketing Strategy (optional)
    4. Content Generation (optional)
    
    Each step builds on the previous results.
    
    Args:
        request: AgentPipelineRequest with configuration
        
    Returns:
        AgentPipelineResponse with all results
    """
    steps_completed = []
    insights_summary = None
    forecast_summary = None
    marketing_strategy = None
    ad_content = None
    
    # Validate file exists
    try:
        df = get_dataframe(request.file_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File ID {request.file_id} not found")
    
    # STEP 1: Data Insights (always runs)
    try:
        insights_result = get_data_insights(request.file_id)
        insights_summary = f"Dataset has {insights_result.rows} rows, {insights_result.columns} columns. " \
                          f"Found {insights_result.duplicates_count} duplicates. " \
                          f"Missing values in {sum(1 for v in insights_result.missing_values.values() if v > 0)} columns."
        steps_completed.append("insights")
    except Exception as e:
        insights_summary = f"Insights generation failed: {str(e)}"
    
    # STEP 2: Forecasting (optional)
    forecast_trend = None
    if request.run_forecast:
        try:
            # Check if forecasting is possible
            forecastable = get_forecastable_columns(request.file_id)
            
            if forecastable.forecastable_columns:
                forecast_request = ForecastRequest(
                    file_id=request.file_id,
                    periods=request.forecast_periods
                )
                forecast_result = generate_forecast(forecast_request)
                
                forecast_summary = {
                    "date_column": forecast_result.date_column,
                    "target_column": forecast_result.target_column,
                    "periods": forecast_result.periods,
                    "trend": forecast_result.trend,
                    "average_prediction": forecast_result.average_prediction,
                    "training_data_points": forecast_result.training_data_points
                }
                forecast_trend = forecast_result.trend
                steps_completed.append("forecast")
            else:
                forecast_summary = {"message": "No forecastable columns found in dataset"}
        except Exception as e:
            forecast_summary = {"error": str(e)}
    
    # STEP 3: Marketing Strategy (optional)
    campaign_for_content = None
    if request.run_marketing:
        try:
            marketing_request = MarketingStrategyRequest(
                file_id=request.file_id,
                business_name=request.business_name,
                business_type=request.business_type,
                target_audience=request.target_audience,
                forecast_trend=forecast_trend
            )
            marketing_result = generate_marketing_strategy(marketing_request)
            
            marketing_strategy = {
                "strategy_summary": marketing_result.strategy_summary,
                "campaigns": [c.model_dump() for c in marketing_result.campaigns],
                "key_insights": marketing_result.key_insights
            }
            
            # Get first campaign for content generation
            if marketing_result.campaigns:
                campaign_for_content = marketing_result.campaigns[0]
            
            steps_completed.append("marketing")
        except Exception as e:
            marketing_strategy = {"error": str(e)}
    
    # STEP 4: Content Generation (optional)
    if request.run_content and campaign_for_content:
        try:
            content_request = ContentGenerationRequest(
                campaign_name=campaign_for_content.campaign_name,
                campaign_theme=campaign_for_content.theme,
                target_audience=campaign_for_content.target_audience,
                tactics=campaign_for_content.tactics,
                platform="social_media",
                tone="professional",
                include_image=True
            )
            content_result = generate_ad_content(content_request)
            
            ad_content = {
                "campaign_name": content_result.campaign_name,
                "platform": content_result.platform,
                "content": content_result.content.model_dump(),
                "generated_at": content_result.generated_at
            }
            steps_completed.append("content")
        except Exception as e:
            ad_content = {"error": str(e)}
    elif request.run_content and not campaign_for_content:
        ad_content = {"message": "Content generation skipped - no marketing campaign available"}
    
    return AgentPipelineResponse(
        file_id=request.file_id,
        steps_completed=steps_completed,
        insights_summary=insights_summary,
        forecast_summary=forecast_summary,
        marketing_strategy=marketing_strategy,
        ad_content=ad_content,
        message=f"Pipeline completed. Steps: {', '.join(steps_completed)}"
    )
