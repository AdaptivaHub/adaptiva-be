# Adaptiva Backend Architecture

## System Overview

Adaptiva Backend is a FastAPI-based REST API for data analysis, visualization, and machine learning. It provides endpoints for file upload, data cleaning, insights generation, chart creation and export capabilities.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Auth Middleware (JWT)                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Routers Layer                          ││
│  │ auth│upload│charts│cleaning│insights│ml│export│preview      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Services Layer                          ││
│  │  Business logic, data processing, AI integration           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Utils Layer                            ││
│  │  Storage, file handling, common utilities, dependencies     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
    ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
    │  In-Memory   │   │   OpenAI     │    │   SQLite/    │
    │   Storage    │   │     API      │    │  PostgreSQL  │
    └──────────────┘   └──────────────┘    └──────────────┘
```

## Directory Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app initialization, middleware, routers
├── config.py            # App configuration (JWT secrets, DB URL)
├── database.py          # Database connection and session management
├── models/
│   ├── __init__.py      # Pydantic models for request/response validation
│   └── user.py          # User database model
├── routers/
│   ├── __init__.py      # Router exports
│   ├── auth.py          # Authentication endpoints (login, register, refresh)
│   ├── upload.py        # File upload endpoints
│   ├── charts.py        # Chart generation endpoints
│   ├── cleaning.py      # Data cleaning endpoints
│   ├── insights.py      # Data insights endpoints
│   ├── ml.py            # Machine learning endpoints
│   ├── export.py        # Data export endpoints
│   └── preview.py       # Formatted data preview endpoints
├── services/
│   ├── __init__.py      # Service exports
│   ├── auth_service.py  # JWT creation, password hashing
│   ├── upload_service.py
│   ├── chart_service.py
│   ├── ai_chart_service.py
│   ├── cleaning_service.py
│   ├── insights_service.py
│   ├── ml_service.py
│   ├── export_service.py
│   └── preview_service.py
└── utils/
    ├── __init__.py
    ├── storage.py       # In-memory data storage
    └── deps.py          # Dependency injection (get_current_user)
```

## Layer Responsibilities

### Routers Layer
- Define API endpoints and routes
- Handle HTTP request/response
- Input validation via Pydantic models
- Delegate business logic to services
- Error response formatting

### Services Layer
- Implement business logic
- Data transformation and processing
- External API integration (OpenAI)
- Raise appropriate exceptions

### Utils Layer
- Shared utilities
- Data storage management
- File ID generation
- Common helper functions

### Models Layer
- Pydantic models for validation
- Request/Response schemas
- Enum definitions
- Type safety
- SQLAlchemy models for database entities

## Authentication Flow

### JWT Authentication Architecture
```
┌─────────────┐     POST /api/auth/login      ┌─────────────┐
│   Client    │ ─────────────────────────────▶│  Auth Router│
│  (React)    │                               │             │
└─────────────┘                               └──────┬──────┘
      │                                              │
      │                                              ▼
      │                                       ┌─────────────┐
      │                                       │Auth Service │
      │                                       │(validate pw)│
      │                                       └──────┬──────┘
      │                                              │
      │         ◀──── JWT Tokens ────────────────────┘
      │         (access_token + refresh_token)
      │
      │         GET /api/charts (protected)
      │         Authorization: Bearer <token>
      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Request   │────▶│  JWT Auth   │────▶│   Router    │
│             │     │ Dependency  │     │  (charts)   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    Validate Token
                    Extract User
                    Inject into Request
```

### Token Lifecycle
```
┌──────────────────────────────────────────────────────────────┐
│                     Token Lifecycle                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Login ──▶ Access Token (15-30 min) ──▶ Expires             │
│       └──▶ Refresh Token (7 days)                           │
│                    │                                         │
│                    ▼                                         │
│            POST /api/auth/refresh                           │
│                    │                                         │
│                    ▼                                         │
│            New Access Token ──▶ Continue using API          │
│                                                              │
│  Logout ──▶ Tokens invalidated (optional blacklist)         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### File Upload Flow
```
POST /api/upload
       │
       ▼
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│    Router    │────▶│  Upload Service │────▶│   Storage    │
│  (upload.py) │     │                 │     │  (memory)    │
└──────────────┘     └─────────────────┘     └──────────────┘
       │                     │
       │              ┌──────┴──────┐
       │              ▼             ▼
       │         DataFrame     Raw Content
       │         (for ops)    (for preview)
       ▼
  FileUploadResponse
```

### Chart Generation Flow
```
POST /api/charts
       │
       ▼
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│    Router    │────▶│  Chart Service  │────▶│   Storage    │
│  (charts.py) │     │                 │     │  get_dataframe│
└──────────────┘     └─────────────────┘     └──────────────┘
                             │
                             ▼
                     ┌──────────────┐
                     │    Plotly    │
                     │  Generation  │
                     └──────────────┘
                             │
                             ▼
                   ChartGenerationResponse
```

### AI Chart Flow
```
POST /api/charts/ai
       │
       ▼
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│    Router    │────▶│  AI Chart Svc   │────▶│   Storage    │
│  (charts.py) │     │                 │     │              │
└──────────────┘     └─────────────────┘     └──────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌────────────┐
        │  Schema  │  │  OpenAI  │  │ Restricted │
        │ Extract  │  │   API    │  │  Python    │
        └──────────┘  └──────────┘  │ (Sandbox)  │
                                    └────────────┘
                                          │
                                          ▼
                               AIChartGenerationResponse
```

## Storage Architecture

### Current Implementation (In-Memory with Composite Keys)

The storage system uses composite keys to support multiple Excel sheets per file:

```python
# app/utils/storage.py

# Key format: "file_id" for CSV or "file_id:sheet_name" for Excel sheets
dataframes: Dict[str, pd.DataFrame] = {}

# Original file content for formatted preview
file_contents: Dict[str, Tuple[bytes, str]] = {}  # file_id -> (content, filename)

# Helper functions for composite key management
def get_sheet_key(file_id: str, sheet_name: Optional[str] = None) -> str:
    """Generate composite key: 'file_id' or 'file_id:sheet_name'"""
    if sheet_name:
        return f"{file_id}:{sheet_name}"
    return file_id

def store_dataframe(file_id: str, df: pd.DataFrame, sheet_name: Optional[str] = None):
    """Store dataframe with optional sheet name"""
    key = get_sheet_key(file_id, sheet_name)
    dataframes[key] = df.copy()

def get_dataframe(file_id: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Retrieve dataframe using composite key"""
    key = get_sheet_key(file_id, sheet_name)
    return dataframes[key].copy()

def has_dataframe(file_id: str, sheet_name: Optional[str] = None) -> bool:
    """Check if dataframe exists for file_id + sheet_name"""
    key = get_sheet_key(file_id, sheet_name)
    return key in dataframes
```

### Excel Multi-Sheet Support

When working with Excel files containing multiple sheets:

1. **Upload**: First sheet is loaded and stored with `file_id:sheet_name` key
2. **Sheet Switching**: Frontend requests preview with specific `sheet_name`
3. **Cleaning**: Each sheet is cleaned and stored independently
4. **Charts**: Generated from the currently active sheet

```
Excel File: report.xlsx
├── Sheet1 (Sales)     → stored as "abc123:Sales"
├── Sheet2 (Inventory) → stored as "abc123:Inventory"  
└── Sheet3 (Summary)   → stored as "abc123:Summary"
```

**Pros:**
- Fast access
- Simple implementation
- Independent sheet operations
- No external dependencies

**Cons:**
- Data lost on restart
- Memory constraints
- Not suitable for production at scale

### Production Recommendation
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Redis     │     │  PostgreSQL │     │     S3      │
│  (Cache)    │     │  (Metadata) │     │   (Files)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Security Architecture

### AI Code Execution Sandbox
The AI chart service uses RestrictedPython for safe code execution:

```python
# Blocked
- File system operations
- Network calls
- Module imports
- Dangerous attributes (__class__, __globals__, etc.)
- System commands

# Allowed
- pandas operations
- numpy operations
- plotly.express
- plotly.graph_objects
- Basic Python builtins
```

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## API Versioning Strategy

Current: No versioning (v1 implied)

Recommended for future:
```
/api/v1/upload
/api/v1/charts
/api/v2/charts  # Breaking changes
```

## Error Handling

### Global Exception Handler
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
```

### Service-Level Exceptions
- `HTTPException(400)` - Bad request / validation errors
- `HTTPException(404)` - Resource not found
- `HTTPException(500)` - Internal server errors

## External Dependencies

| Dependency | Purpose |
|------------|---------|
| pandas | Data manipulation |
| openpyxl | Excel file support |
| plotly | Chart generation |
| openai | AI-powered features |
| RestrictedPython | Sandboxed code execution |
| reportlab | PDF export |
| python-pptx | PowerPoint export |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | Yes (for AI features) | OpenAI API key |
| PORT | No | Server port (default: 8000) |

## Performance Considerations

1. **File Size Limits** - Consider nginx/server-level limits
2. **DataFrame Memory** - Large files consume significant memory
3. **AI API Calls** - Rate limiting and caching recommended
4. **Chart Generation** - Complex charts can be CPU-intensive

## Scalability Path

1. **Horizontal Scaling**
   - Move storage to Redis/PostgreSQL
   - Use S3 for file storage
   - Stateless API servers

2. **Async Processing**
   - Celery for long-running tasks
   - Background chart generation
   - File processing queue

3. **Caching**
   - Redis for DataFrame caching
   - Chart result caching
   - API response caching
