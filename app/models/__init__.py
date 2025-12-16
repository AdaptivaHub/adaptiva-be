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


class DataCleaningRequest(BaseModel):
    """Request for data cleaning"""
    file_id: str
    drop_duplicates: bool = Field(default=True, description="Remove duplicate rows")
    drop_na: bool = Field(default=False, description="Remove rows with missing values")
    fill_na: Optional[Dict[str, Any]] = Field(default=None, description="Fill missing values with specified values")
    columns_to_drop: Optional[List[str]] = Field(default=None, description="List of columns to drop")


class DataCleaningResponse(BaseModel):
    """Response for data cleaning"""
    file_id: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    message: str


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
    user_instructions: Optional[str] = Field(
        default=None, 
        description="User's instructions for what kind of chart to create"
    )
    base_prompt: Optional[str] = Field(
        default=None,
        description="System-level base prompt to guide AI behavior"
    )


class AIChartGenerationResponse(BaseModel):
    """Response for AI-powered chart generation"""
    chart_json: Dict[str, Any]
    generated_code: str
    explanation: str
    message: str


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
# AGENT SYSTEM MODELS
# ============================================================================

class ForecastRequest(BaseModel):
    """Request for time-series forecast"""
    file_id: str
    date_column: Optional[str] = Field(default=None, description="Date column to use (auto-detected if not specified)")
    target_column: Optional[str] = Field(default=None, description="Target column to forecast (auto-detected if not specified)")
    periods: int = Field(default=30, ge=1, le=365, description="Number of periods to forecast")


class ForecastPrediction(BaseModel):
    """Individual forecast prediction"""
    date: str
    predicted_value: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    """Response for time-series forecast"""
    file_id: str
    date_column: str
    target_column: str
    periods: int
    predictions: List[ForecastPrediction]
    average_prediction: float
    trend: str = Field(description="'increasing' or 'decreasing'")
    training_data_points: int
    message: str


class ForecastableColumn(BaseModel):
    """A column that can be forecasted"""
    date_column: str
    target_column: str
    target_dtype: str
    unique_values: int


class ForecastableColumnsResponse(BaseModel):
    """Response listing forecastable columns"""
    file_id: str
    forecastable_columns: List[ForecastableColumn]
    message: str


class MarketingStrategyRequest(BaseModel):
    """Request for marketing strategy generation"""
    file_id: str
    business_name: Optional[str] = Field(default=None, description="Name of the business")
    business_type: Optional[str] = Field(default=None, description="Type of business (e.g., retail, e-commerce)")
    target_audience: Optional[str] = Field(default=None, description="Target audience description")
    forecast_trend: Optional[str] = Field(default=None, description="Forecast trend from previous analysis")
    additional_context: Optional[str] = Field(default=None, description="Any additional business context")


class MarketingCampaign(BaseModel):
    """Individual marketing campaign"""
    campaign_name: str
    theme: str
    timing: str
    tactics: List[str]
    target_audience: str
    expected_outcome: str
    budget_recommendation: Optional[str] = None


class MarketingStrategyResponse(BaseModel):
    """Response for marketing strategy"""
    file_id: str
    strategy_summary: str
    campaigns: List[MarketingCampaign]
    key_insights: List[str]
    message: str


class ContentGenerationRequest(BaseModel):
    """Request for ad content generation"""
    campaign_name: str
    campaign_theme: str
    target_audience: str
    tactics: List[str]
    platform: str = Field(default="social_media", description="Platform: social_media, email, website")
    tone: str = Field(default="professional", description="Tone: professional, casual, exciting, urgent")
    include_image: bool = Field(default=True, description="Generate image URL using Pollinations AI")


class AdContent(BaseModel):
    """Generated ad content"""
    headline: str
    main_caption: str
    long_description: str
    hashtags: List[str]
    call_to_action: str
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None


class ContentGenerationResponse(BaseModel):
    """Response for content generation"""
    campaign_name: str
    platform: str
    content: AdContent
    generated_at: str
    message: str


class AgentPipelineRequest(BaseModel):
    """Request for full agent pipeline"""
    file_id: str
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[str] = None
    run_forecast: bool = Field(default=True, description="Include forecasting step")
    run_marketing: bool = Field(default=True, description="Include marketing strategy step")
    run_content: bool = Field(default=True, description="Include content generation step")
    forecast_periods: int = Field(default=30, ge=1, le=365)


class AgentPipelineResponse(BaseModel):
    """Response for full agent pipeline"""
    file_id: str
    steps_completed: List[str]
    insights_summary: Optional[str] = None
    forecast_summary: Optional[Dict[str, Any]] = None
    marketing_strategy: Optional[Dict[str, Any]] = None
    ad_content: Optional[Dict[str, Any]] = None
    message: str


# ============================================================================
# RATE LIMITING MODELS
# ============================================================================

class RateLimitError(BaseModel):
    """Rate limit exceeded error response"""
    error: str = "Rate limit exceeded"
    message: str
    daily_limit_cents: float
    used_cents: float
    remaining_cents: float
    reset: str = "midnight UTC"


class UsageStatsResponse(BaseModel):
    """Response for usage statistics"""
    ip: str
    date: str
    cost_cents: float
    requests: int
    limit_cents: float
    remaining_cents: float
    message: str
