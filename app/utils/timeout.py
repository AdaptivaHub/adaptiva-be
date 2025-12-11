"""
Timeout utility for long-running operations.
Uses threading for cross-platform compatibility (works on Windows).
"""
import threading
from functools import wraps
from typing import Callable, Any, TypeVar
from fastapi import HTTPException

# Default timeout in seconds
CHART_GENERATION_TIMEOUT = 30

# Type variable for generic return type
T = TypeVar('T')


class ChartTimeoutError(Exception):
    """Exception raised when chart generation times out."""
    pass


def with_timeout(seconds: int = CHART_GENERATION_TIMEOUT):
    """
    Decorator to add timeout to a function.
    
    Args:
        seconds: Maximum execution time in seconds (default: 30)
        
    Returns:
        Decorated function that raises HTTPException on timeout
        
    Example:
        @with_timeout(30)
        def slow_function():
            # ... long running operation
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result: list = [None]
            exception: list = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)
            
            if thread.is_alive():
                raise HTTPException(
                    status_code=408,
                    detail=f"Chart generation timed out after {seconds} seconds. "
                           "Try reducing the data size or simplifying the chart."
                )
            
            if exception[0] is not None:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    return decorator
