from fastapi import APIRouter
from app.models import (
    DataCleaningRequest, 
    DataCleaningResponse, 
    ErrorResponse
)
from app.services import clean_data

router = APIRouter(prefix="/cleaning", tags=["Data Cleaning"])


@router.post(
    "/",
    response_model=DataCleaningResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Clean dataset with Excel Copilot-like features",
    description="Perform comprehensive data cleaning with column normalization, smart missing value handling, type detection, and detailed operation logging"
)
def clean_dataset(request: DataCleaningRequest):
    """
    Perform comprehensive data cleaning with Excel Copilot-like features.
    
    Uses composite key (file_id:sheet_name) for Excel files to ensure
    the correct sheet is cleaned.
    
    **Basic Options:**
    - **file_id**: The file identifier returned from upload (required)
    - **sheet_name**: Sheet name for Excel files (optional, uses composite key)
    - **drop_duplicates**: Remove duplicate rows (default: True)
    - **drop_na**: Remove rows with any missing values (default: False)
    - **fill_na**: Manual fill values per column (dict of column: value)
    - **columns_to_drop**: List of column names to drop
    
    **Advanced Options:**
    - **normalize_columns**: Normalize column names to lowercase with underscores (default: False)
    - **remove_empty_rows**: Remove rows where all values are null (default: True)
    - **remove_empty_columns**: Remove columns where all values are null (default: True)
    - **smart_fill_missing**: Smart fill missing values - median for numeric, mode for categorical (default: False)
    - **auto_detect_types**: Auto-detect and convert data types like dates and numbers (default: False)
    
    Returns detailed information about all cleaning operations performed.
    """
    return clean_data(request)
