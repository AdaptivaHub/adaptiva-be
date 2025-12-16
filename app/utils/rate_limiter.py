"""
Rate Limiter - IP-based daily cost limiting for AI API calls
Limits each IP to a configurable daily spend (default: $0.20/day)
"""
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException

# Cost per 1K tokens for different models (approximate)
# GPT-4o-mini: $0.15/1M input, $0.60/1M output
MODEL_COSTS = {
    "gpt-4o-mini": {
        "input": 0.00015,   # $0.15 per 1M = $0.00015 per 1K
        "output": 0.0006    # $0.60 per 1M = $0.0006 per 1K
    },
    "gpt-4o": {
        "input": 0.0025,    # $2.50 per 1M
        "output": 0.01      # $10 per 1M
    }
}

# Default daily limit in cents
DEFAULT_DAILY_LIMIT_CENTS = float(os.getenv("DAILY_COST_LIMIT_CENTS", "20"))

# Storage for IP usage tracking
# Structure: {ip: {"date": "YYYY-MM-DD", "cost_cents": float, "requests": int}}
_ip_usage: Dict[str, Dict] = defaultdict(lambda: {"date": "", "cost_cents": 0.0, "requests": 0})
_lock = Lock()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, first is the client
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def get_today_str() -> str:
    """Get today's date as string"""
    return datetime.now().strftime("%Y-%m-%d")


def estimate_cost_cents(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4o-mini"
) -> float:
    """
    Estimate cost in cents for a request.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name
        
    Returns:
        Estimated cost in cents
    """
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
    
    # Cost per 1K tokens, convert to actual cost
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]
    
    # Convert dollars to cents
    return (input_cost + output_cost) * 100


def check_rate_limit(request: Request, estimated_cost_cents: float = 0.5) -> Tuple[bool, str]:
    """
    Check if the request is within rate limits.
    
    Args:
        request: FastAPI request object
        estimated_cost_cents: Estimated cost for this request
        
    Returns:
        Tuple of (allowed: bool, message: str)
    """
    ip = get_client_ip(request)
    today = get_today_str()
    limit = DEFAULT_DAILY_LIMIT_CENTS
    
    with _lock:
        usage = _ip_usage[ip]
        
        # Reset if new day
        if usage["date"] != today:
            usage["date"] = today
            usage["cost_cents"] = 0.0
            usage["requests"] = 0
        
        current_cost = usage["cost_cents"]
        
        # Check if adding this request would exceed limit
        if current_cost + estimated_cost_cents > limit:
            remaining = max(0, limit - current_cost)
            return False, f"Daily limit exceeded. Used: ${current_cost/100:.4f} of ${limit/100:.2f}. Remaining: ${remaining/100:.4f}"
        
        return True, f"OK. Current usage: ${current_cost/100:.4f} of ${limit/100:.2f}"


def record_usage(request: Request, input_tokens: int, output_tokens: int, model: str = "gpt-4o-mini"):
    """
    Record actual usage after a successful API call.
    
    Args:
        request: FastAPI request object
        input_tokens: Actual input tokens used
        output_tokens: Actual output tokens used
        model: Model used
    """
    ip = get_client_ip(request)
    today = get_today_str()
    cost = estimate_cost_cents(input_tokens, output_tokens, model)
    
    with _lock:
        usage = _ip_usage[ip]
        
        # Reset if new day
        if usage["date"] != today:
            usage["date"] = today
            usage["cost_cents"] = 0.0
            usage["requests"] = 0
        
        usage["cost_cents"] += cost
        usage["requests"] += 1


def get_usage_stats(request: Request) -> Dict:
    """Get usage statistics for the requesting IP"""
    ip = get_client_ip(request)
    today = get_today_str()
    limit = DEFAULT_DAILY_LIMIT_CENTS
    
    with _lock:
        usage = _ip_usage[ip]
        
        # Reset if new day
        if usage["date"] != today:
            return {
                "ip": ip,
                "date": today,
                "cost_cents": 0.0,
                "requests": 0,
                "limit_cents": limit,
                "remaining_cents": limit
            }
        
        return {
            "ip": ip,
            "date": usage["date"],
            "cost_cents": round(usage["cost_cents"], 4),
            "requests": usage["requests"],
            "limit_cents": limit,
            "remaining_cents": round(max(0, limit - usage["cost_cents"]), 4)
        }


def require_rate_limit(estimated_cost_cents: float = 0.5):
    """
    Dependency for FastAPI endpoints that require rate limiting.
    
    Usage:
        @router.post("/endpoint")
        def my_endpoint(request: Request, _: None = Depends(require_rate_limit(1.0))):
            ...
    """
    async def dependency(request: Request):
        allowed, message = check_rate_limit(request, estimated_cost_cents)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": message,
                    "retry_after": "tomorrow"
                }
            )
        return None
    
    return dependency


# Middleware-style rate limit check
async def rate_limit_middleware_check(request: Request, estimated_cost: float = 0.5):
    """Check rate limit and raise HTTPException if exceeded"""
    allowed, message = check_rate_limit(request, estimated_cost)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": message,
                "daily_limit_cents": DEFAULT_DAILY_LIMIT_CENTS,
                "reset": "midnight UTC"
            }
        )
