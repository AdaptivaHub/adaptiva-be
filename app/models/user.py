"""
User database model for authentication.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.sqlite import TEXT
from app.database import Base


class User(Base):
    """User model for storing user accounts."""
    
    __tablename__ = "users"
    
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.email}>"


class TokenBlacklist(Base):
    """
    Token blacklist for invalidated refresh tokens.
    Used for logout functionality.
    """
    
    __tablename__ = "token_blacklist"
    
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_jti = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
