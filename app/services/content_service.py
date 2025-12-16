"""
Content Generation Service - AI-powered ad content creation with image generation
Ported from Multi-Agent-System-for-SMEs
"""
import json
import os
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException
from openai import OpenAI

from app.models import (
    ContentGenerationRequest,
    ContentGenerationResponse,
    AdContent
)


def generate_image_url(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """
    Generate image URL using FREE Pollinations AI.
    No API key required - constructs URL that generates image on-demand.
    """
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    return image_url


def _parse_content_from_response(response_text: str, include_image: bool, campaign_name: str) -> AdContent:
    """Parse AI response to extract structured ad content"""
    
    # Try to parse as JSON first
    try:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            image_prompt = parsed.get('image_prompt', parsed.get('image_description', ''))
            image_url = None
            if include_image and image_prompt:
                image_url = generate_image_url(image_prompt)
            
            return AdContent(
                headline=parsed.get('headline', parsed.get('main_caption', campaign_name)),
                main_caption=parsed.get('main_caption', parsed.get('caption', '')),
                long_description=parsed.get('long_description', parsed.get('description', '')),
                hashtags=parsed.get('hashtags', []) if isinstance(parsed.get('hashtags'), list) else [],
                call_to_action=parsed.get('call_to_action', parsed.get('cta', 'Learn More')),
                image_prompt=image_prompt if image_prompt else None,
                image_url=image_url
            )
    except json.JSONDecodeError:
        pass
    
    # Fallback: Extract from text
    lines = response_text.split('\n')
    headline = campaign_name
    caption = ""
    description = ""
    hashtags = []
    cta = "Learn More"
    image_prompt = None
    
    current_section = None
    for line in lines:
        line_lower = line.lower().strip()
        
        if 'headline' in line_lower or 'caption' in line_lower:
            current_section = 'caption'
            caption = line.split(':', 1)[-1].strip() if ':' in line else ""
        elif 'description' in line_lower:
            current_section = 'description'
            description = line.split(':', 1)[-1].strip() if ':' in line else ""
        elif 'hashtag' in line_lower:
            current_section = 'hashtags'
        elif 'call-to-action' in line_lower or 'cta' in line_lower:
            current_section = 'cta'
            cta = line.split(':', 1)[-1].strip() if ':' in line else "Learn More"
        elif 'image' in line_lower and ('description' in line_lower or 'prompt' in line_lower):
            current_section = 'image'
            image_prompt = line.split(':', 1)[-1].strip() if ':' in line else ""
        elif current_section == 'hashtags' and line.strip().startswith('#'):
            hashtags.extend([tag.strip() for tag in line.split() if tag.startswith('#')])
        elif current_section == 'description' and line.strip():
            description += " " + line.strip()
    
    # Generate image URL if requested
    image_url = None
    if include_image:
        if image_prompt:
            image_url = generate_image_url(image_prompt)
        else:
            # Generate a default image prompt
            default_prompt = f"Professional marketing image for {campaign_name}, modern business style, clean design"
            image_url = generate_image_url(default_prompt)
            image_prompt = default_prompt
    
    return AdContent(
        headline=headline if headline else campaign_name,
        main_caption=caption if caption else f"Check out our latest {campaign_name}!",
        long_description=description.strip() if description else "",
        hashtags=hashtags if hashtags else ["#marketing", "#business"],
        call_to_action=cta,
        image_prompt=image_prompt,
        image_url=image_url
    )


def generate_ad_content(request: ContentGenerationRequest) -> ContentGenerationResponse:
    """
    Generate ad content based on campaign strategy using AI.
    Optionally generates image using Pollinations AI (free, no API key).
    
    Args:
        request: ContentGenerationRequest with campaign details
        
    Returns:
        ContentGenerationResponse with ad content and optional image
    """
    
    # Build tactics string
    tactics_str = "\n".join([f"- {t}" for t in request.tactics]) if request.tactics else "General marketing tactics"
    
    prompt = f"""You are a creative copywriter specializing in digital marketing. Create compelling ad content for this campaign:

Campaign Name: {request.campaign_name}
Campaign Theme: {request.campaign_theme}
Target Audience: {request.target_audience}
Platform: {request.platform}
Tone: {request.tone}
Tactics:
{tactics_str}

Generate the following in JSON format:
{{
  "headline": "Attention-grabbing headline (max 60 characters)",
  "main_caption": "Engaging main caption (max 150 characters)",
  "long_description": "Detailed post description (2-3 sentences)",
  "hashtags": ["#relevant", "#hashtags", "#list"],
  "call_to_action": "Clear CTA button text",
  "image_prompt": "Detailed description of the perfect image for this ad (for AI image generation)"
}}

Make it engaging, professional, and aligned with the campaign goals.
Use the specified tone: {request.tone}
Optimize for {request.platform} platform.
"""

    try:
        client = OpenAI()  # Uses OPENAI_API_KEY from environment
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert creative copywriter who creates viral marketing content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=800
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse content from response
        content = _parse_content_from_response(
            response_text, 
            request.include_image,
            request.campaign_name
        )
        
        return ContentGenerationResponse(
            campaign_name=request.campaign_name,
            platform=request.platform,
            content=content,
            generated_at=datetime.now().isoformat(),
            message="Successfully generated ad content"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")
