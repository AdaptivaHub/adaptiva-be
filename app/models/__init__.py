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
    sheet_name: Optional[str] = Field(default=None, description="Sheet name for Excel files (uses composite key file_id:sheet_name)")
    drop_duplicates: bool = Field(default=True, description="Remove duplicate rows")
    drop_na: bool = Field(default=False, description="Remove rows with missing values")
    fill_na: Optional[Dict[str, Any]] = Field(default=None, description="Fill missing values with specified values")
    columns_to_drop: Optional[List[str]] = Field(default=None, description="List of columns to drop")


class DataCleaningResponse(BaseModel):
    """Response for data cleaning"""
    file_id: str
    sheet_name: Optional[str] = Field(default=None, description="Sheet name that was cleaned (Excel only)")
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    message: str


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


class EnhancedCleaningRequest(BaseModel):
    """Request for enhanced data cleaning with Excel Copilot-like features"""
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


class EnhancedCleaningResponse(BaseModel):
    """Response for enhanced data cleaning with detailed log"""
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
