"""
Authentication router for user registration, login, and token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import EmailStr, field_validator
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import (
    UserCreate, 
    UserLogin, 
    UserResponse, 
    AuthResponse, 
    RefreshTokenRequest,
    MessageResponse
)
from app.models.user import User
from app.services import auth_service
from app.utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Enhanced request models with validation
class RegisterRequest(BaseModel):
    """Registration request with email validation."""
    email: str = Field(description="Valid email address")
    password: str = Field(min_length=8, description="Password (minimum 8 characters)")
    full_name: str | None = Field(default=None, description="User's full name")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()


class LoginRequest(BaseModel):
    """Login request."""
    email: str = Field(description="User email address")
    password: str = Field(description="User password")


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account and return JWT tokens"
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Register a new user account.
    
    - **email**: Valid email address (must be unique)
    - **password**: Password (minimum 8 characters)
    - **full_name**: Optional user's full name
    
    Returns user info and JWT tokens.
    """
    user_data = UserCreate(
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )
    return auth_service.register_user(db, user_data)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User login",
    description="Authenticate user and return JWT tokens"
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Authenticate a user and return tokens.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns user info and JWT tokens.
    """
    return auth_service.login_user(db, request.email, request.password)


@router.post(
    "/refresh",
    response_model=dict,
    summary="Refresh tokens",
    description="Get new access and refresh tokens using a valid refresh token"
)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Refresh access and refresh tokens.
    
    - **refresh_token**: Valid refresh token
    
    Returns new token pair. The old refresh token is invalidated.
    """
    return auth_service.refresh_tokens(db, request.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
    description="Invalidate refresh token"
)
def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Logout user by invalidating their refresh token.
    
    - **refresh_token**: Refresh token to invalidate
    """
    auth_service.logout_user(db, request.refresh_token)
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the currently authenticated user's information"
)
def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.
    
    Requires valid access token in Authorization header.
    """
    return auth_service.user_to_response(current_user)
