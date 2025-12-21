"""
Rate limiting service for anonymous AI requests.
Uses in-memory storage with automatic cleanup.
"""
import uuid
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from threading import Lock

from app.config import get_settings

settings = get_settings()

# In-memory storage for rate limiting (use Redis in production)
_rate_limit_store: Dict[str, Dict] = {}
_store_lock = Lock()

# Global counters
_global_daily_count = 0
_global_daily_reset: Optional[datetime] = None
_global_lock = Lock()

# Burst tracking per IP
_burst_store: Dict[str, list] = {}
_burst_lock = Lock()


def _get_today_key() -> str:
    """Get a key representing today's date."""
    return datetime.utcnow().strftime("%Y-%m-%d")


def _cleanup_expired_entries():
    """Remove expired entries from the store."""
    now = datetime.utcnow()
    with _store_lock:
        expired_keys = [
            key for key, data in _rate_limit_store.items()
            if data.get("expires_at", now) < now
        ]
        for key in expired_keys:
            del _rate_limit_store[key]


def create_anonymous_session() -> str:
    """
    Create a signed anonymous session token.
    Returns a base64-encoded signed token.
    """
    session_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    # Create payload
    payload = {
        "sid": session_id,
        "iat": created_at
    }
    payload_bytes = json.dumps(payload).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode()
    
    # Create signature
    signature = hmac.new(
        settings.ANONYMOUS_SESSION_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode()
    
    return f"{payload_b64}.{signature_b64}"


def validate_anonymous_session(token: str) -> Optional[str]:
    """
    Validate an anonymous session token.
    Returns the session ID if valid, None otherwise.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        payload_b64, signature_b64 = parts
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        
        # Verify signature
        expected_signature = hmac.new(
            settings.ANONYMOUS_SESSION_SECRET.encode(),
            payload_bytes,
            hashlib.sha256
        ).digest()
        actual_signature = base64.urlsafe_b64decode(signature_b64)
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        
        # Parse payload
        payload = json.loads(payload_bytes)
        return payload.get("sid")
    except Exception:
        return None


def get_ip_usage_count(ip: str) -> int:
    """Get the current usage count for an IP address."""
    key = f"anon_ip:{ip}:{_get_today_key()}"
    with _store_lock:
        data = _rate_limit_store.get(key, {})
        return data.get("count", 0)


def get_session_usage_count(session_id: str) -> int:
    """Get the current usage count for a session."""
    key = f"anon_session:{session_id}:{_get_today_key()}"
    with _store_lock:
        data = _rate_limit_store.get(key, {})
        return data.get("count", 0)


def increment_usage(ip: str, session_id: Optional[str]) -> Tuple[int, int]:
    """
    Increment usage counts for both IP and session.
    Returns (ip_count, session_count) after increment.
    """
    today = _get_today_key()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    with _store_lock:
        # Increment IP count
        ip_key = f"anon_ip:{ip}:{today}"
        ip_data = _rate_limit_store.get(ip_key, {"count": 0, "expires_at": expires_at, "first_request": datetime.utcnow()})
        ip_data["count"] += 1
        _rate_limit_store[ip_key] = ip_data
        ip_count = ip_data["count"]
        
        # Increment session count if provided
        session_count = 0
        if session_id:
            session_key = f"anon_session:{session_id}:{today}"
            session_data = _rate_limit_store.get(session_key, {"count": 0, "expires_at": expires_at, "first_request": datetime.utcnow()})
            session_data["count"] += 1
            _rate_limit_store[session_key] = session_data
            session_count = session_data["count"]
    
    return ip_count, session_count


def get_combined_usage(ip: str, session_id: Optional[str]) -> int:
    """
    Get the combined usage count (maximum of IP and session).
    This prevents bypass via VPN hopping or session clearing.
    """
    ip_count = get_ip_usage_count(ip)
    session_count = get_session_usage_count(session_id) if session_id else 0
    return max(ip_count, session_count)


def get_reset_time(ip: str, session_id: Optional[str]) -> datetime:
    """Get the time when the rate limit will reset."""
    today = _get_today_key()
    
    with _store_lock:
        # Check IP first request time
        ip_key = f"anon_ip:{ip}:{today}"
        ip_data = _rate_limit_store.get(ip_key, {})
        ip_first = ip_data.get("first_request")
        
        # Check session first request time
        session_first = None
        if session_id:
            session_key = f"anon_session:{session_id}:{today}"
            session_data = _rate_limit_store.get(session_key, {})
            session_first = session_data.get("first_request")
    
    # Use the earliest first request time
    first_request = None
    if ip_first and session_first:
        first_request = min(ip_first, session_first)
    elif ip_first:
        first_request = ip_first
    elif session_first:
        first_request = session_first
    
    if first_request:
        return first_request + timedelta(hours=24)
    
    return datetime.utcnow() + timedelta(hours=24)


def check_global_limit() -> bool:
    """
    Check if global anonymous limit has been reached.
    Returns True if limit exceeded.
    """
    global _global_daily_count, _global_daily_reset
    
    with _global_lock:
        now = datetime.utcnow()
        
        # Reset counter if it's a new day
        if _global_daily_reset is None or _global_daily_reset.date() < now.date():
            _global_daily_count = 0
            _global_daily_reset = now
        
        return _global_daily_count >= settings.GLOBAL_ANONYMOUS_DAILY_LIMIT


def increment_global_count():
    """Increment the global anonymous request counter."""
    global _global_daily_count
    
    with _global_lock:
        _global_daily_count += 1


def check_burst_limit(ip: str) -> bool:
    """
    Check if IP has exceeded burst limit (requests per minute).
    Returns True if limit exceeded.
    """
    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)
    
    with _burst_lock:
        # Get or create burst tracking for this IP
        if ip not in _burst_store:
            _burst_store[ip] = []
        
        # Remove old entries
        _burst_store[ip] = [t for t in _burst_store[ip] if t > minute_ago]
        
        # Check limit
        return len(_burst_store[ip]) >= settings.BURST_LIMIT_PER_MINUTE


def record_burst_request(ip: str):
    """Record a request for burst limiting."""
    with _burst_lock:
        if ip not in _burst_store:
            _burst_store[ip] = []
        _burst_store[ip].append(datetime.utcnow())


def get_rate_limit_info(ip: str, session_id: Optional[str]) -> dict:
    """
    Get rate limit information for response headers.
    """
    usage = get_combined_usage(ip, session_id)
    remaining = max(0, settings.ANONYMOUS_DAILY_LIMIT - usage)
    reset_time = get_reset_time(ip, session_id)
    
    return {
        "limit": settings.ANONYMOUS_DAILY_LIMIT,
        "remaining": remaining,
        "reset": int(reset_time.timestamp()),
        "used": usage
    }
