"""
Marketing Strategy Service - AI-powered marketing strategy generation
Ported from Multi-Agent-System-for-SMEs
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException
from openai import OpenAI

import pandas as pd
import numpy as np

from app.utils import get_dataframe
from app.models import (
    MarketingStrategyRequest,
    MarketingStrategyResponse,
    MarketingCampaign
)


def _get_data_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Create a token-efficient summary of the dataset for AI context"""
    summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist()[:15],  # Limit columns
        "date_range": None,
        "top_metrics": {}
    }
    
    # Get date range if available
    date_cols = df.select_dtypes(include=['datetime64']).columns
    if len(date_cols) > 0:
        summary["date_range"] = {
            "start": str(df[date_cols[0]].min()),
            "end": str(df[date_cols[0]].max())
        }
    
    # Get top numeric columns summary
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in list(numeric_cols)[:5]:  # Top 5 numeric columns
        summary["top_metrics"][col] = {
            "mean": round(float(df[col].mean()), 2),
            "total": round(float(df[col].sum()), 2),
            "min": round(float(df[col].min()), 2),
            "max": round(float(df[col].max()), 2)
        }
    
    return summary


def _parse_campaigns_from_response(response_text: str) -> List[MarketingCampaign]:
    """Parse AI response to extract structured campaigns"""
    campaigns = []
    
    # Try to extract JSON from response
    try:
        # Look for JSON array in response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            for item in parsed:
                campaigns.append(MarketingCampaign(
                    campaign_name=item.get('campaign_name', 'Untitled Campaign'),
                    theme=item.get('theme', item.get('campaign_name', '')),
                    timing=item.get('timing', 'To be determined'),
                    tactics=item.get('tactics', []) if isinstance(item.get('tactics'), list) else [item.get('tactics', '')],
                    target_audience=item.get('target_audience', item.get('audience', 'General audience')),
                    expected_outcome=item.get('expected_outcome', 'Increased engagement'),
                    budget_recommendation=item.get('budget_recommendation')
                ))
            return campaigns
    except json.JSONDecodeError:
        pass
    
    # Fallback: create a single campaign from the text
    campaigns.append(MarketingCampaign(
        campaign_name="AI Generated Strategy",
        theme="Data-Driven Campaign",
        timing="Based on forecast trends",
        tactics=["See strategy summary for details"],
        target_audience="Target audience from data analysis",
        expected_outcome="Improved business metrics"
    ))
    
    return campaigns


def _extract_insights(response_text: str) -> List[str]:
    """Extract key insights from AI response"""
    insights = []
    
    # Look for bullet points or numbered lists
    lines = response_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith(('-', '•', '*', '1', '2', '3', '4', '5')):
            # Clean up the line
            cleaned = line.lstrip('-•*0123456789.').strip()
            if len(cleaned) > 10:  # Meaningful insight
                insights.append(cleaned)
    
    # If no bullet points found, extract first few sentences
    if not insights:
        sentences = response_text.replace('\n', ' ').split('.')
        insights = [s.strip() + '.' for s in sentences[:3] if len(s.strip()) > 20]
    
    return insights[:5]  # Max 5 insights


def generate_marketing_strategy(request: MarketingStrategyRequest) -> MarketingStrategyResponse:
    """
    Generate marketing strategy based on data insights using AI.
    
    Args:
        request: MarketingStrategyRequest with file_id and business context
        
    Returns:
        MarketingStrategyResponse with campaigns and insights
    """
    try:
        df = get_dataframe(request.file_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File ID {request.file_id} not found")
    
    # Get data summary
    data_summary = _get_data_summary(df)
    
    # Build context for AI
    context = f"""
Business Context:
- Business Name: {request.business_name or 'Not specified'}
- Business Type: {request.business_type or 'Not specified'}
- Target Audience: {request.target_audience or 'Not specified'}
- Forecast Trend: {request.forecast_trend or 'Not analyzed'}
- Additional Context: {request.additional_context or 'None'}

Data Summary:
- Total Records: {data_summary['rows']}
- Date Range: {data_summary['date_range']}
- Key Metrics: {json.dumps(data_summary['top_metrics'], indent=2)}
"""

    prompt = f"""You are a marketing strategist for a small/medium enterprise. Based on the business data:

{context}

Create a marketing strategy with 2-3 concrete, actionable campaigns.

For each campaign, provide:
1. Campaign Name - catchy and memorable
2. Theme - the main message/concept
3. Timing - when to run (e.g., "Next 2 weeks", "During peak season")
4. Tactics - 3-5 specific tactics (e.g., "10% discount on top products", "Email campaign to returning customers")
5. Target Audience - specific segment
6. Expected Outcome - measurable goals

Format your response as a JSON array with these exact keys:
[
  {{
    "campaign_name": "...",
    "theme": "...",
    "timing": "...",
    "tactics": ["...", "..."],
    "target_audience": "...",
    "expected_outcome": "...",
    "budget_recommendation": "..."
  }}
]

After the JSON, provide a brief strategy summary explaining the overall approach.
"""

    try:
        client = OpenAI()  # Uses OPENAI_API_KEY from environment
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert marketing strategist specializing in SME growth strategies."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse campaigns from response
        campaigns = _parse_campaigns_from_response(response_text)
        
        # Extract insights
        insights = _extract_insights(response_text)
        
        # Clean up strategy summary (remove JSON if present)
        strategy_summary = response_text
        if '[' in strategy_summary and ']' in strategy_summary:
            # Get text after the JSON array
            end_idx = strategy_summary.rfind(']')
            strategy_summary = strategy_summary[end_idx + 1:].strip()
        
        if not strategy_summary or len(strategy_summary) < 50:
            strategy_summary = f"Generated {len(campaigns)} marketing campaigns based on your business data and context."
        
        return MarketingStrategyResponse(
            file_id=request.file_id,
            strategy_summary=strategy_summary,
            campaigns=campaigns,
            key_insights=insights,
            message=f"Successfully generated {len(campaigns)} marketing campaigns"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating marketing strategy: {str(e)}")
