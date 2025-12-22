from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class MLModelType(str, Enum):
    """ML model types supported"""
    LINEAR_REGRESSION = "linear_regression"
    DECISION_TREE = "decision_tree"


class ChartType(str, Enum):
    """Chart types supported"""
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"
    PIE = "pie"


class ExportFormat(str, Enum):
    """Export format types"""
    PDF = "pdf"
    PPTX = "pptx"


class FileUploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str
    filename: str
    rows: int
    columns: int
    column_names: List[str]
    message: str
    sheets: Optional[List[str]] = Field(default=None, description="List of sheet names (Excel only)")
    active_sheet: Optional[str] = Field(default=None, description="Sheet used for metadata (Excel only)")
    header_row: Optional[int] = Field(default=None, description="Detected header row index (0-based)")
    header_confidence: Optional[float] = Field(default=None, description="Confidence score for header detection (0.0-1.0)")


class DataCleaningRequest(BaseModel):
    """
    Request for comprehensive data cleaning with Excel Copilot-like features.
    
    Uses composite key (file_id:sheet_name) for Excel files to ensure
    the correct sheet is cleaned.
    """
    file_id: str = Field(description="UUID of uploaded file")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name for Excel files (uses composite key file_id:sheet_name)")
    normalize_columns: bool = Field(default=False, description="Normalize column names (lowercase, strip, replace spaces)")
    remove_empty_rows: bool = Field(default=True, description="Remove rows where all values are null")
    remove_empty_columns: bool = Field(default=True, description="Remove columns where all values are null")
    drop_duplicates: bool = Field(default=True, description="Remove duplicate rows")
    drop_na: bool = Field(default=False, description="Remove rows with any missing values")
    smart_fill_missing: bool = Field(default=False, description="Smart fill missing values (median for numeric, mode for categorical)")
    auto_detect_types: bool = Field(default=False, description="Auto-detect and convert data types (dates, numbers)")
    fill_na: Optional[Dict[str, Any]] = Field(default=None, description="Manual fill values per column")
    columns_to_drop: Optional[List[str]] = Field(default=None, description="List of column names to drop")


class CleaningOperation(BaseModel):
    """Single cleaning operation log entry"""
    operation: str = Field(description="Name of the operation performed")
    details: str = Field(description="Details about the operation")
    affected_count: int = Field(default=0, description="Number of items affected")


class ColumnChanges(BaseModel):
    """Summary of column changes during cleaning"""
    renamed: Dict[str, str] = Field(default_factory=dict, description="Old name to new name mapping")
    dropped: List[str] = Field(default_factory=list, description="List of dropped columns")
    type_converted: Dict[str, str] = Field(default_factory=dict, description="Column to new type mapping")


class MissingValuesSummary(BaseModel):
    """Missing values before and after cleaning"""
    before: Dict[str, int] = Field(default_factory=dict, description="Missing values per column before")
    after: Dict[str, int] = Field(default_factory=dict, description="Missing values per column after")


class DataCleaningResponse(BaseModel):
    """
    Response for data cleaning with detailed operation log.
    
    Includes comprehensive information about all cleaning operations performed.
    """
    file_id: str = Field(description="File identifier")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name that was cleaned (Excel only)")
    rows_before: int = Field(description="Original row count")
    rows_after: int = Field(description="Final row count")
    columns_before: int = Field(description="Original column count")
    columns_after: int = Field(description="Final column count")
    operations_log: List[CleaningOperation] = Field(default_factory=list, description="Log of all operations performed")
    column_changes: ColumnChanges = Field(default_factory=ColumnChanges, description="Summary of column changes")
    missing_values_summary: MissingValuesSummary = Field(default_factory=MissingValuesSummary, description="Missing values before/after")
    message: str = Field(description="Summary message")


class DataInsightsResponse(BaseModel):
    """Response for data insights"""
    file_id: str
    rows: int
    columns: int
    column_info: Dict[str, Any]
    numerical_summary: Dict[str, Any]
    missing_values: Dict[str, int]
    duplicates_count: int


class ChartGenerationRequest(BaseModel):
    """Request for chart generation"""
    file_id: str
    sheet_name: Optional[str] = Field(
        default=None,
        description="Sheet name for Excel files (uses composite key file_id:sheet_name)"
    )
    chart_type: ChartType
    x_column: str
    y_column: Optional[str] = None
    title: Optional[str] = "Chart"
    color_column: Optional[str] = None


class ChartGenerationResponse(BaseModel):
    """Response for chart generation"""
    chart_json: Dict[str, Any]
    message: str


class MLModelRequest(BaseModel):
    """Request for ML model training"""
    file_id: str
    model_type: MLModelType
    target_column: str
    feature_columns: List[str]
    test_size: float = Field(default=0.2, ge=0.1, le=0.5, description="Test data proportion")


class MLModelResponse(BaseModel):
    """Response for ML model training"""
    model_type: str
    metrics: Dict[str, float]
    predictions_sample: List[float]
    feature_importance: Optional[Dict[str, float]] = None
    message: str


class ExportRequest(BaseModel):
    """Request for data export"""
    file_id: str
    export_format: ExportFormat
    include_insights: bool = Field(default=True, description="Include data insights")
    include_charts: bool = Field(default=False, description="Include charts")
    chart_configs: Optional[List[Dict[str, Any]]] = Field(default=None, description="Chart configurations")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None


class AIChartGenerationRequest(BaseModel):
    """Request for AI-powered chart generation"""
    file_id: str
    sheet_name: Optional[str] = Field(
        default=None,
        description="Sheet name for Excel files (uses composite key file_id:sheet_name)"
    )
    user_instructions: Optional[str] = Field(
        default=None, 
        description="User's instructions for what kind of chart to create"
    )
    base_prompt: Optional[str] = Field(
        default=None,
        description="System-level base prompt to guide AI behavior"
    )


class ChartSettings(BaseModel):
    """Extracted chart settings for the Chart Editor"""
    chart_type: Optional[str] = Field(default=None, description="Type of chart (bar, line, scatter, histogram, box, pie)")
    x_column: Optional[str] = Field(default=None, description="Column used for x-axis")
    y_column: Optional[str] = Field(default=None, description="Column used for y-axis")
    color_column: Optional[str] = Field(default=None, description="Column used for color grouping")
    group_by: Optional[str] = Field(default=None, description="Column used for grouping data")
    title: Optional[str] = Field(default=None, description="Chart title")
    aggregation: Optional[str] = Field(default=None, description="Aggregation function (sum, mean, count, etc.)")


class AIChartGenerationResponse(BaseModel):
    """Response for AI-powered chart generation"""
    chart_json: Dict[str, Any]
    generated_code: str
    explanation: str
    message: str
    chart_settings: Optional[ChartSettings] = Field(
        default=None,
        description="Extracted chart settings for the Chart Editor"
    )


class PreviewRequest(BaseModel):
    """Request for data preview"""
    file_id: str
    max_rows: int = Field(default=100, ge=1, le=1000, description="Maximum rows to preview")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name to preview (Excel only)")


class PreviewResponse(BaseModel):
    """Response for data preview with formatted values"""
    file_id: str
    headers: List[str]
    data: List[Dict[str, str]]
    total_rows: int
    preview_rows: int
    formatted: bool = Field(description="Whether Excel formatting was preserved")
    message: str
    sheet_name: Optional[str] = Field(default=None, description="Sheet being previewed (Excel only)")
    available_sheets: Optional[List[str]] = Field(default=None, description="Available sheets (Excel only)")


# ============================================================================
# Authentication Models
# ============================================================================

class UserCreate(BaseModel):
    """Request for user registration"""
    email: str = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (minimum 8 characters)")
    full_name: Optional[str] = Field(default=None, description="User's full name")


class UserLogin(BaseModel):
    """Request for user login"""
    email: str = Field(description="User email address")
    password: str = Field(description="User password")


class UserResponse(BaseModel):
    """User information response (without password)"""
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response containing JWT tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Combined response for login/register with user and tokens"""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str = Field(description="Valid refresh token")


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str


class RateLimitExceededResponse(BaseModel):
    """Response when anonymous rate limit is exceeded"""
    detail: str = "Daily AI query limit reached"
    queries_used: int
    queries_limit: int
    reset_at: str
    message: str = "Sign up for free to get unlimited AI queries!"
