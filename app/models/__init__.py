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


class PreviewResponse(BaseModel):
    """Response for data preview with formatted values"""
    file_id: str
    headers: List[str]
    data: List[Dict[str, str]]
    total_rows: int
    preview_rows: int
    formatted: bool = Field(description="Whether Excel formatting was preserved")
    message: str
