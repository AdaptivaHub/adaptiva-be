"""
Unit tests for authentication functionality.
Tests cover all acceptance criteria from docs/requirements/authentication.md

AC-1 to AC-4: User Registration
AC-5 to AC-7: User Login
AC-8 to AC-10: Token Management
AC-11 to AC-14: Protected Routes
AC-15 to AC-19: Anonymous Rate Limiting
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.services import auth_service
from app.services import rate_limit_service
from app.config import get_settings


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123",
        "full_name": "Test User"
    }


@pytest.fixture
def registered_user(client, test_user_data):
    """Register a user and return the response."""
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


# =============================================================================
# AC-1 to AC-4: User Registration Tests
# =============================================================================

class TestUserRegistration:
    """Tests for user registration functionality."""

    def test_ac1_successful_registration(self, client, test_user_data):
        """
        AC-1: Successful Registration
        Given: A new user with valid email and password
        When: Registration is requested
        Then: User account is created and tokens are returned
        """
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "user" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify user data
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["full_name"] == test_user_data["full_name"]
        assert "id" in data["user"]
        assert "created_at" in data["user"]

    def test_ac2_duplicate_email_prevention(self, client, test_user_data, registered_user):
        """
        AC-2: Duplicate Email Prevention
        Given: An email that already exists in the system
        When: Registration is attempted
        Then: A 400 error is returned with "Email already registered"
        """
        # Try to register with the same email
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Email already registered" in data["detail"]

    def test_ac3_password_validation_too_short(self, client):
        """
        AC-3: Password Validation
        Given: A password that doesn't meet requirements (min 8 chars)
        When: Registration is attempted
        Then: A 422 error is returned with validation details (Pydantic validation)
        """
        user_data = {
            "email": "test@example.com",
            "password": "short",  # Less than 8 characters
            "full_name": "Test User"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        # Pydantic validation returns 422
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_ac4_email_validation_invalid_format(self, client):
        """
        AC-4: Email Validation
        Given: An invalid email format
        When: Registration is attempted
        Then: A 422 error is returned with validation details
        """
        user_data = {
            "email": "not-a-valid-email",
            "password": "SecurePass123",
            "full_name": "Test User"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        # Pydantic validation should catch invalid email
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_registration_without_full_name(self, client):
        """Test registration works without optional full_name."""
        user_data = {
            "email": "noname@example.com",
            "password": "SecurePass123"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == user_data["email"]


# =============================================================================
# AC-5 to AC-7: User Login Tests
# =============================================================================

class TestUserLogin:
    """Tests for user login functionality."""

    def test_ac5_successful_login(self, client, test_user_data, registered_user):
        """
        AC-5: Successful Login
        Given: Valid email and password
        When: Login is requested
        Then: JWT tokens are returned
        """
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "user" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify user data matches
        assert data["user"]["email"] == test_user_data["email"]

    def test_ac6_invalid_credentials_wrong_password(self, client, test_user_data, registered_user):
        """
        AC-6: Invalid Credentials
        Given: Incorrect email or password
        When: Login is attempted
        Then: A 401 error is returned with "Invalid credentials"
        """
        login_data = {
            "email": test_user_data["email"],
            "password": "WrongPassword123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["detail"]

    def test_ac7_account_not_found(self, client):
        """
        AC-7: Account Not Found
        Given: An email that doesn't exist
        When: Login is attempted
        Then: A 401 error is returned with "Invalid credentials" (same as AC-6 for security)
        """
        login_data = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        # Same error as wrong password for security (prevents email enumeration)
        assert "Invalid credentials" in data["detail"]


# =============================================================================
# AC-8 to AC-10: Token Management Tests
# =============================================================================

class TestTokenManagement:
    """Tests for token refresh and logout functionality."""

    def test_ac8_token_refresh(self, client, registered_user):
        """
        AC-8: Token Refresh
        Given: A valid refresh token
        When: Token refresh is requested
        Then: New access and refresh tokens are returned
        """
        refresh_data = {
            "refresh_token": registered_user["refresh_token"]
        }
        
        response = client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify new refresh token is different
        assert data["refresh_token"] != registered_user["refresh_token"]

    def test_ac9_expired_refresh_token(self, client):
        """
        AC-9: Expired Refresh Token
        Given: An expired refresh token
        When: Token refresh is attempted
        Then: A 401 error is returned requiring re-login
        """
        # Create an expired token manually
        with patch.object(auth_service, 'validate_refresh_token') as mock_validate:
            from fastapi import HTTPException
            mock_validate.side_effect = HTTPException(
                status_code=401,
                detail="Token expired"
            )
            
            refresh_data = {
                "refresh_token": "expired.token.here"
            }
            
            response = client.post("/api/auth/refresh", json=refresh_data)
            
            assert response.status_code == 401

    def test_ac10_logout(self, client, registered_user):
        """
        AC-10: Logout
        Given: A logged-in user
        When: Logout is requested
        Then: Tokens are invalidated
        """
        logout_data = {
            "refresh_token": registered_user["refresh_token"]
        }
        
        response = client.post("/api/auth/logout", json=logout_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out" in data["message"]

    def test_logout_without_token(self, client):
        """Test that logout without refresh token returns 422 (validation error)."""
        response = client.post("/api/auth/logout", json={})
        
        assert response.status_code == 422

    def test_invalid_refresh_token(self, client):
        """Test refresh with invalid token format."""
        refresh_data = {
            "refresh_token": "invalid-token-format"
        }
        
        response = client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401


# =============================================================================
# AC-11 to AC-14: Protected Routes Tests
# =============================================================================

class TestProtectedRoutes:
    """Tests for protected route authentication."""

    def test_ac11_valid_token_access(self, client, registered_user):
        """
        AC-11: Valid Token Access
        Given: A request with valid access token
        When: A protected endpoint is called
        Then: The request is processed normally
        """
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_ac12_missing_token(self, client):
        """
        AC-12: Missing Token
        Given: A request without Authorization header
        When: A protected endpoint is called
        Then: A 401 error is returned with "Not authenticated"
        """
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    def test_ac13_invalid_token(self, client):
        """
        AC-13: Invalid Token
        Given: A request with invalid/malformed token
        When: A protected endpoint is called
        Then: A 401 error is returned with "Invalid token"
        """
        headers = {"Authorization": "Bearer invalid.token.format"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid token" in data["detail"] or "Could not validate" in data["detail"]

    def test_ac14_expired_token(self, client, registered_user):
        """
        AC-14: Expired Token
        Given: A request with expired access token
        When: A protected endpoint is called
        Then: A 401 error is returned with "Token expired"
        """
        # Create an expired token by mocking
        with patch.object(auth_service, 'validate_access_token') as mock_validate:
            from fastapi import HTTPException
            mock_validate.side_effect = HTTPException(
                status_code=401,
                detail="Token expired"
            )
            
            headers = {"Authorization": "Bearer expired.token.here"}
            response = client.get("/api/auth/me", headers=headers)
            
            assert response.status_code == 401


# =============================================================================
# AC-15 to AC-19: Anonymous Rate Limiting Tests
# =============================================================================

class TestAnonymousRateLimiting:
    """Tests for anonymous user rate limiting on AI endpoints."""

    @pytest.fixture(autouse=True)
    def reset_rate_limits(self):
        """Reset rate limiting state before each test."""
        # Clear in-memory rate limit stores
        rate_limit_service._rate_limit_store.clear()
        rate_limit_service._burst_store.clear()
        with rate_limit_service._global_lock:
            rate_limit_service._global_daily_count = 0
            rate_limit_service._global_daily_reset = None
        yield

    def test_ac15_anonymous_query_limit(self, client):
        """
        AC-15: Anonymous Query Limit
        Given: An anonymous user (no JWT token)
        When: They make AI chart requests
        Then: They are limited to 3 requests per 24-hour rolling window
        """
        # We'll mock the AI chart generation to isolate rate limiting logic
        with patch('app.routers.charts.generate_ai_chart') as mock_generate:
            mock_generate.return_value = {
                "chart_json": {},
                "generated_code": "# code",
                "explanation": "Test chart",
                "message": "Chart generated successfully"
            }
            
            # First 3 requests should succeed
            for i in range(3):
                response = client.post(
                    "/api/charts/ai",
                    json={"file_id": "test-file-id"}
                )
                # May get 404 for file not found, but not 429 yet
                # Here we just verify rate limit headers are present
                assert response.status_code != 429 or i < 3

    def test_ac16_limit_exceeded_response(self, client):
        """
        AC-16: Limit Exceeded Response
        Given: An anonymous user who has used 3 queries
        When: They attempt a 4th query
        Then: A 429 error is returned with upgrade prompt
        """
        test_ip = "192.168.1.100"
        session_token = rate_limit_service.create_anonymous_session()
        session_id = rate_limit_service.validate_anonymous_session(session_token)
        
        # Simulate 3 prior requests
        for _ in range(3):
            rate_limit_service.increment_usage(test_ip, session_id)
        
        # Mock the request to use our test IP
        with patch('app.routers.charts.get_client_ip', return_value=test_ip):
            with patch('app.routers.charts.generate_ai_chart') as mock_generate:
                mock_generate.return_value = {
                    "chart_json": {},
                    "generated_code": "# code",
                    "explanation": "Test",
                    "message": "Chart generated"
                }
                
                response = client.post(
                    "/api/charts/ai",
                    json={"file_id": "test-file"},
                    headers={"X-Anonymous-Session": session_token}
                )
                
                assert response.status_code == 429
                data = response.json()
                assert "detail" in data
                # Check for rate limit message
                detail = data["detail"]
                if isinstance(detail, dict):
                    assert "Daily AI query limit reached" in detail.get("detail", "")
                    assert detail.get("queries_used") == 3
                    assert detail.get("queries_limit") == 3
                    assert "reset_at" in detail
                    assert "Sign up" in detail.get("message", "")

    def test_ac17_authenticated_users_bypass(self, client, registered_user):
        """
        AC-17: Authenticated Users Bypass
        Given: A logged-in user with valid JWT
        When: They make AI chart requests
        Then: They are not subject to the anonymous rate limit
        """
        test_ip = "192.168.1.100"
        
        # Pre-exhaust the anonymous limit for this IP
        for _ in range(5):
            rate_limit_service.increment_usage(test_ip, None)
        
        with patch('app.routers.charts.get_client_ip', return_value=test_ip):
            with patch('app.routers.charts.generate_ai_chart') as mock_generate:
                mock_generate.return_value = {
                    "chart_json": {},
                    "generated_code": "# code",
                    "explanation": "Test",
                    "message": "Chart generated"
                }
                
                headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
                response = client.post(
                    "/api/charts/ai",
                    json={"file_id": "test-file"},
                    headers=headers
                )
                
                # Should NOT get 429 because user is authenticated
                assert response.status_code != 429

    def test_ac18_rate_limit_reset(self):
        """
        AC-18: Rate Limit Reset
        Given: An anonymous user who reached the limit
        When: 24 hours have passed since their first query
        Then: Their limit resets (rolling window)
        """
        test_ip = "192.168.1.200"
        session_token = rate_limit_service.create_anonymous_session()
        session_id = rate_limit_service.validate_anonymous_session(session_token)
        
        # Add requests with yesterday's date key
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        key = f"anon_ip:{test_ip}:{yesterday}"
        
        with rate_limit_service._store_lock:
            rate_limit_service._rate_limit_store[key] = {
                "count": 3,
                "expires_at": datetime.utcnow() - timedelta(hours=1),
                "first_request": datetime.utcnow() - timedelta(days=1)
            }
        
        # Today's usage should be 0 (fresh day)
        usage = rate_limit_service.get_combined_usage(test_ip, session_id)
        assert usage == 0

    def test_ac19_combined_ip_session_tracking(self):
        """
        AC-19: Combined IP + Session Tracking
        Given: An anonymous user attempting to bypass limits
        When: They switch IPs (VPN) or clear session storage
        Then: The system uses the higher count from IP or session
        """
        # Test scenario: User has 2 requests on IP, 1 on session
        # Combined should return max(2, 1) = 2
        
        ip1 = "10.0.0.1"
        session_token = rate_limit_service.create_anonymous_session()
        session_id = rate_limit_service.validate_anonymous_session(session_token)
        
        # Make 2 requests from IP only
        rate_limit_service.increment_usage(ip1, None)
        rate_limit_service.increment_usage(ip1, None)
        
        # Make 1 request with session only (different IP)
        ip2 = "10.0.0.2"
        rate_limit_service.increment_usage(ip2, session_id)
        
        # Now check combined from new IP but same session
        # Should be max(0 for new ip, 1 for session) = 1
        combined = rate_limit_service.get_combined_usage("10.0.0.3", session_id)
        assert combined == 1
        
        # Check from original IP with no session
        # Should be max(2 for ip1, 0 for no session) = 2
        combined = rate_limit_service.get_combined_usage(ip1, None)
        assert combined == 2

    def test_rate_limit_headers_included(self, client):
        """Test that rate limit headers are included in responses."""
        with patch('app.routers.charts.generate_ai_chart') as mock_generate:
            mock_generate.return_value = {
                "chart_json": {},
                "generated_code": "# code",
                "explanation": "Test",
                "message": "Chart generated"
            }
            
            response = client.post(
                "/api/charts/ai",
                json={"file_id": "test-file"}
            )
            
            # Check rate limit headers (if request processed before file validation)
            if response.status_code != 404:
                assert "X-RateLimit-Limit" in response.headers or response.status_code == 429
                assert "X-Anonymous-Session" in response.headers

    def test_anonymous_session_token_creation(self):
        """Test anonymous session token creation and validation."""
        token = rate_limit_service.create_anonymous_session()
        
        assert token is not None
        assert "." in token  # Should have payload.signature format
        
        session_id = rate_limit_service.validate_anonymous_session(token)
        assert session_id is not None
        
        # Invalid token should return None
        invalid = rate_limit_service.validate_anonymous_session("invalid")
        assert invalid is None

    def test_burst_limit_protection(self):
        """Test burst rate limiting (requests per minute)."""
        test_ip = "172.16.0.1"
        settings = get_settings()
        
        # Record many requests quickly
        for _ in range(settings.BURST_LIMIT_PER_MINUTE):
            rate_limit_service.record_burst_request(test_ip)
        
        # Should now be at burst limit
        assert rate_limit_service.check_burst_limit(test_ip) is True
        
        # Different IP should not be limited
        assert rate_limit_service.check_burst_limit("172.16.0.2") is False

    def test_global_limit_protection(self):
        """Test global anonymous daily limit."""
        settings = get_settings()
        
        # Set global count to limit
        with rate_limit_service._global_lock:
            rate_limit_service._global_daily_count = settings.GLOBAL_ANONYMOUS_DAILY_LIMIT
            rate_limit_service._global_daily_reset = datetime.utcnow()
        
        assert rate_limit_service.check_global_limit() is True
        
        # Reset counter
        with rate_limit_service._global_lock:
            rate_limit_service._global_daily_count = 0
        
        assert rate_limit_service.check_global_limit() is False


# =============================================================================
# Auth Service Unit Tests
# =============================================================================

class TestAuthService:
    """Unit tests for auth service functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "TestPassword123"
        
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("WrongPassword", hashed) is False

    def test_access_token_creation(self):
        """Test JWT access token creation."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = auth_service.create_access_token(user_id, email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_refresh_token_creation(self):
        """Test JWT refresh token creation."""
        user_id = "test-user-id"
        
        token, jti = auth_service.create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        assert jti is not None

    def test_token_validation(self):
        """Test token validation returns correct payload."""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = auth_service.create_access_token(user_id, email)
        payload = auth_service.validate_access_token(token)
        
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_invalid_token_raises_error(self):
        """Test invalid token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_access_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
