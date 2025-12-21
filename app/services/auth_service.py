"""
Authentication service for JWT token management and password hashing.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import get_settings
from app.models.user import User, TokenBlacklist
from app.models import UserCreate, UserResponse, AuthResponse

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(user_id: str, email: str) -> str:
    """Create a short-lived access token."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> Tuple[str, str]:
    """
    Create a long-lived refresh token.
    Returns tuple of (token, jti) where jti is the unique token ID.
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())  # Unique token ID for blacklisting
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "type": "refresh"
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises HTTPException if invalid.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def validate_access_token(token: str) -> dict:
    """Validate an access token and return its payload."""
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return payload


def validate_refresh_token(token: str, db: Session) -> dict:
    """
    Validate a refresh token and check it's not blacklisted.
    Returns the payload if valid.
    """
    payload = decode_token(token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti:
        blacklisted = db.query(TokenBlacklist).filter(
            TokenBlacklist.token_jti == jti
        ).first()
        if blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    return payload


def blacklist_token(db: Session, jti: str, expires_at: datetime) -> None:
    """Add a token to the blacklist."""
    blacklisted = TokenBlacklist(
        token_jti=jti,
        expires_at=expires_at
    )
    db.add(blacklisted)
    db.commit()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user account.
    Raises HTTPException if email already exists.
    """
    # Check if email already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_pw = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
        full_name=user_data.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Authenticate a user by email and password.
    Raises HTTPException if credentials are invalid.
    """
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def user_to_response(user: User) -> UserResponse:
    """Convert a User model to UserResponse."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at.isoformat()
    )


def register_user(db: Session, user_data: UserCreate) -> AuthResponse:
    """
    Register a new user and return tokens.
    """
    user = create_user(db, user_data)
    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = create_refresh_token(user.id)
    
    return AuthResponse(
        user=user_to_response(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


def login_user(db: Session, email: str, password: str) -> AuthResponse:
    """
    Authenticate user and return tokens.
    """
    user = authenticate_user(db, email, password)
    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = create_refresh_token(user.id)
    
    return AuthResponse(
        user=user_to_response(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    """
    Refresh access and refresh tokens.
    Returns new token pair.
    """
    payload = validate_refresh_token(refresh_token, db)
    user_id = payload.get("sub")
    
    # Get user to verify they still exist and are active
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Blacklist the old refresh token
    old_jti = payload.get("jti")
    if old_jti:
        exp_timestamp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_timestamp)
        blacklist_token(db, old_jti, expires_at)
    
    # Create new tokens
    new_access_token = create_access_token(user.id, user.email)
    new_refresh_token, _ = create_refresh_token(user.id)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


def logout_user(db: Session, refresh_token: str) -> None:
    """
    Logout user by blacklisting their refresh token.
    """
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti")
        if jti:
            exp_timestamp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp_timestamp)
            blacklist_token(db, jti, expires_at)
    except HTTPException:
        # Token already invalid, nothing to blacklist
        pass
