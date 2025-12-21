# Feature: Authentication & Authorization

## Overview
Secure the Adaptiva API with JWT-based authentication, allowing users to register, login, and access protected resources. Anonymous users can make limited AI queries before requiring authentication.

## User Stories

### Authenticated User
As a user,
I want to securely log in to the application,
So that my data and analysis results are protected and personalized.

### Anonymous User
As an anonymous user,
I want to try the AI chart features up to 3 times per day,
So that I can evaluate the product before creating an account.

## Sub-Features

### 1. User Registration
Allow new users to create an account with email and password.

### 2. User Login
Authenticate users and issue JWT tokens for API access.

### 3. Token Management
Handle access token refresh and logout functionality.

### 4. Protected Routes
Secure API endpoints requiring authentication.

### 5. User Profile
Allow users to view and update their profile information.

### 6. Anonymous Rate Limiting
Allow limited AI usage (3 queries/day) without authentication, with layered protection against abuse.

---

## User Registration

### Acceptance Criteria

#### AC-1: Successful Registration
- **Given**: A new user with valid email and password
- **When**: Registration is requested
- **Then**: User account is created and tokens are returned

#### AC-2: Duplicate Email Prevention
- **Given**: An email that already exists in the system
- **When**: Registration is attempted
- **Then**: A 400 error is returned with "Email already registered"

#### AC-3: Password Validation
- **Given**: A password that doesn't meet requirements (min 8 chars)
- **When**: Registration is attempted
- **Then**: A 400 error is returned with validation details

#### AC-4: Email Validation
- **Given**: An invalid email format
- **When**: Registration is attempted
- **Then**: A 400 error is returned with validation details

### API Contract - Registration

#### Endpoint: `POST /api/auth/register`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "full_name": "John Doe"
}
```

**Response (Success - 201):**
```json
{
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2025-12-21T10:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Response (Error - 400):**
```json
{
  "detail": "Email already registered"
}
```

---

## User Login

### Acceptance Criteria

#### AC-5: Successful Login
- **Given**: Valid email and password
- **When**: Login is requested
- **Then**: JWT tokens are returned

#### AC-6: Invalid Credentials
- **Given**: Incorrect email or password
- **When**: Login is attempted
- **Then**: A 401 error is returned with "Invalid credentials"

#### AC-7: Account Not Found
- **Given**: An email that doesn't exist
- **When**: Login is attempted
- **Then**: A 401 error is returned with "Invalid credentials" (same as AC-6 for security)

### API Contract - Login

#### Endpoint: `POST /api/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response (Success - 200):**
```json
{
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2025-12-21T10:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Response (Error - 401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

## Token Management

### Acceptance Criteria

#### AC-8: Token Refresh
- **Given**: A valid refresh token
- **When**: Token refresh is requested
- **Then**: New access and refresh tokens are returned

#### AC-9: Expired Refresh Token
- **Given**: An expired refresh token
- **When**: Token refresh is attempted
- **Then**: A 401 error is returned requiring re-login

#### AC-10: Logout
- **Given**: A logged-in user
- **When**: Logout is requested
- **Then**: Tokens are invalidated (optional: add to blacklist)

### API Contract - Token Refresh

#### Endpoint: `POST /api/auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (Success - 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### API Contract - Logout

#### Endpoint: `POST /api/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (Success - 200):**
```json
{
  "message": "Successfully logged out"
}
```

---

## Protected Routes

### Acceptance Criteria

#### AC-11: Valid Token Access
- **Given**: A request with valid access token
- **When**: A protected endpoint is called
- **Then**: The request is processed normally

#### AC-12: Missing Token
- **Given**: A request without Authorization header
- **When**: A protected endpoint is called
- **Then**: A 401 error is returned with "Not authenticated"

#### AC-13: Invalid Token
- **Given**: A request with invalid/malformed token
- **When**: A protected endpoint is called
- **Then**: A 401 error is returned with "Invalid token"

#### AC-14: Expired Token
- **Given**: A request with expired access token
- **When**: A protected endpoint is called
- **Then**: A 401 error is returned with "Token expired"

### Protected Endpoints

The following endpoints require authentication:
- `POST /api/upload` - File upload
- `POST /api/cleaning` - Data cleaning
- `POST /api/charts/*` - Chart generation
- `POST /api/preview` - Data preview
- `GET /api/auth/me` - Current user info

### API Contract - Current User

#### Endpoint: `GET /api/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (Success - 200):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-12-21T10:00:00Z"
}
```

---

## Anonymous Rate Limiting

### Overview
Anonymous users can make up to 3 AI chart generation requests per day without logging in. Multiple layers of protection prevent abuse while allowing users to evaluate the product.

### Acceptance Criteria

#### AC-15: Anonymous Query Limit
- **Given**: An anonymous user (no JWT token)
- **When**: They make AI chart requests (`POST /api/charts/ai`)
- **Then**: They are limited to 3 requests per 24-hour rolling window

#### AC-16: Limit Exceeded Response
- **Given**: An anonymous user who has used 3 queries
- **When**: They attempt a 4th query
- **Then**: A 429 error is returned with upgrade prompt

#### AC-17: Authenticated Users Bypass
- **Given**: A logged-in user with valid JWT
- **When**: They make AI chart requests
- **Then**: They are not subject to the anonymous rate limit

#### AC-18: Rate Limit Reset
- **Given**: An anonymous user who reached the limit
- **When**: 24 hours have passed since their first query
- **Then**: Their limit resets (rolling window)

#### AC-19: Combined IP + Session Tracking
- **Given**: An anonymous user attempting to bypass limits
- **When**: They switch IPs (VPN) or clear session storage
- **Then**: The system uses the higher count from IP or session

### API Contract - Rate Limit Response

#### Response (Error - 429 Too Many Requests):
```json
{
  "detail": "Daily AI query limit reached",
  "queries_used": 3,
  "queries_limit": 3,
  "reset_at": "2025-12-22T10:00:00Z",
  "message": "Sign up for free to get unlimited AI queries!"
}
```

#### Rate Limit Headers (All AI Requests):
```
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1703239200
X-Anonymous-Session: <session-token>
```

### Rate Limiting Implementation

#### Layer 1: IP-Based Rate Limiting
Track requests by client IP address with 24-hour TTL.

```python
# Key format: anon_ip:{ip_address}
# Value: request count
# TTL: 24 hours from first request
```

#### Layer 2: Anonymous Session Token
Issue a signed session token to anonymous users, stored in localStorage.

```python
# Header: X-Anonymous-Session
# Key format: anon_session:{session_id}
# Value: request count
# TTL: 24 hours from first request
```

#### Layer 3: Combined Tracking (Anti-Bypass)
Use the MAXIMUM count from both IP and session to prevent circumvention.

```python
def get_usage_count(ip: str, session_id: str) -> int:
    ip_count = cache.get(f"anon_ip:{ip}", 0)
    session_count = cache.get(f"anon_session:{session_id}", 0)
    return max(ip_count, session_count)  # Most restrictive wins
```

### Anonymous Session Token Structure

```json
{
  "sid": "random-uuid",
  "iat": 1703154600,
  "exp": 1703760600
}
```

- Signed with HMAC-SHA256 to prevent forgery
- 7-day expiry (longer than rate limit window)
- New session issued if missing or invalid

### Protected Endpoint Configuration

| Endpoint | Anonymous Access | Rate Limited | Auth Required |
|----------|------------------|--------------|---------------|
| `POST /api/charts/ai` | ✅ Yes | ✅ 3/day | No |
| `POST /api/charts/` | ❌ No | No | Yes |
| `POST /api/upload` | ✅ Yes | No | No |
| `POST /api/preview` | ✅ Yes | No | No |
| `POST /api/cleaning` | ❌ No | No | Yes |
| `GET /api/auth/me` | ❌ No | No | Yes |

### Global Safety Limits

Additional protection against coordinated attacks:

```python
GLOBAL_ANONYMOUS_DAILY_LIMIT = 1000  # Total anonymous AI queries per day
BURST_LIMIT_PER_MINUTE = 10          # Max queries per IP per minute
```

### Frontend Integration

#### Anonymous Session Management
```typescript
// Store session token from response header
const ANON_SESSION_KEY = 'adaptiva_anon_session';

apiClient.interceptors.response.use((response) => {
  const sessionToken = response.headers['x-anonymous-session'];
  if (sessionToken) {
    localStorage.setItem(ANON_SESSION_KEY, sessionToken);
  }
  return response;
});

// Send session token with requests
apiClient.interceptors.request.use((config) => {
  const authToken = getAccessToken();
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  } else {
    const anonSession = localStorage.getItem(ANON_SESSION_KEY);
    if (anonSession) {
      config.headers['X-Anonymous-Session'] = anonSession;
    }
  }
  return config;
});
```

#### Rate Limit UI Handling
```typescript
// Handle 429 response
if (error.response?.status === 429) {
  const data = error.response.data;
  showUpgradeModal({
    message: data.message,
    resetAt: data.reset_at,
    queriesUsed: data.queries_used
  });
}

// Show remaining queries warning
const remaining = response.headers['x-ratelimit-remaining'];
if (remaining === '1') {
  showWarning('1 free AI query remaining today!');
}
```

---

## Test Cases

### Registration

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Successful registration | Valid email, password, name | 201, user + tokens |
| TC-2 | Duplicate email | Existing email | 400, "Email already registered" |
| TC-3 | Weak password | Password < 8 chars | 400, validation error |
| TC-4 | Invalid email | "not-an-email" | 400, validation error |
| TC-5 | Missing required fields | No password | 422, validation error |

### Login

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-6 | Successful login | Valid credentials | 200, user + tokens |
| TC-7 | Wrong password | Valid email, wrong password | 401, "Invalid credentials" |
| TC-8 | Non-existent email | Unknown email | 401, "Invalid credentials" |
| TC-9 | Missing fields | No password | 422, validation error |

### Token Management

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-10 | Token refresh | Valid refresh token | 200, new tokens |
| TC-11 | Expired refresh token | Expired token | 401, requires re-login |
| TC-12 | Invalid refresh token | Malformed token | 401, invalid token |
| TC-13 | Logout | Valid access token | 200, success message |

### Protected Routes

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-14 | Valid token | Bearer token in header | Request processed |
| TC-15 | Missing token | No Authorization header | 401, "Not authenticated" |
| TC-16 | Invalid token | Malformed token | 401, "Invalid token" |
| TC-17 | Expired token | Expired access token | 401, "Token expired" |

### Anonymous Rate Limiting

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-18 | First anonymous AI query | No prior usage | 200, X-RateLimit-Remaining: 2 |
| TC-19 | Third anonymous AI query | 2 prior queries | 200, X-RateLimit-Remaining: 0 |
| TC-20 | Fourth anonymous AI query | 3 prior queries | 429, limit exceeded |
| TC-21 | VPN switch (same session) | Session token, new IP | Uses max(IP, session) count |
| TC-22 | New session (same IP) | Cleared storage, same IP | Uses max(IP, session) count |
| TC-23 | Authenticated user bypass | Valid JWT token | 200, no rate limit headers |
| TC-24 | After 24 hours reset | Previous day's usage expired | 200, X-RateLimit-Remaining: 2 |
| TC-25 | Global limit reached | 1000+ anonymous queries/day | 503, service unavailable |
| TC-26 | Burst limit exceeded | 10+ queries/minute from IP | 429, too many requests |

---

## Technical Implementation

### Dependencies

```
python-jose[cryptography]>=3.3.0  # JWT encoding/decoding
passlib[bcrypt]>=1.7.4            # Password hashing
sqlalchemy>=2.0.0                 # Database ORM
aiosqlite>=0.19.0                 # Async SQLite (dev)
# For production: asyncpg for PostgreSQL
```

### Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Token blacklist for logout
CREATE TABLE token_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### JWT Token Structure

**Access Token (short-lived: 15-30 minutes):**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "exp": 1703156400,
  "iat": 1703154600,
  "type": "access"
}
```

**Refresh Token (long-lived: 7 days):**
```json
{
  "sub": "user-uuid",
  "exp": 1703761200,
  "iat": 1703154600,
  "jti": "unique-token-id",
  "type": "refresh"
}
```

### File Structure

```
app/
├── models/
│   └── user.py              # User model
├── routers/
│   └── auth.py              # Auth endpoints
├── services/
│   └── auth_service.py      # Auth business logic
├── utils/
│   └── deps.py              # Dependency injection (get_current_user)
├── database.py              # Database connection
└── config.py                # JWT settings, secrets
```

### Environment Variables

```env
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=sqlite:///./adaptiva.db  # Dev
# DATABASE_URL=postgresql://user:pass@localhost/adaptiva  # Prod
```

---

## Security Considerations

### Password Security
- Passwords hashed with bcrypt (cost factor 12)
- Never store or log plain-text passwords
- Minimum password length: 8 characters

### Token Security
- Use secure random secret key (min 32 bytes)
- Short access token expiry (15-30 min)
- Refresh tokens stored securely (httpOnly cookies recommended)
- Consider token blacklist for logout

### API Security
- Rate limiting on auth endpoints (prevent brute force)
- HTTPS required in production
- CORS configured for specific origins in production

---

## Frontend Integration

### Storage
- Access token: Memory (React state/context) or localStorage
- Refresh token: httpOnly cookie (preferred) or localStorage

### API Interceptor
```typescript
// Add to axios instance
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token, or redirect to login
    }
    return Promise.reject(error);
  }
);
```

### Auth Context
```typescript
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}
```

---

## Notes

- Start with SQLite for development, migrate to PostgreSQL for production
- Consider adding OAuth2 providers (Google, GitHub) in future
- Implement rate limiting before production deployment
- Add email verification as an optional enhancement
- Consider 2FA for enterprise deployments
