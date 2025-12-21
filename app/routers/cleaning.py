from fastapi import APIRouter
from app.models import (
    DataCleaningRequest, 
    DataCleaningResponse, 
    EnhancedCleaningRequest,
    EnhancedCleaningResponse,
    ErrorResponse
)
from app.services import clean_data, enhanced_clean_data

router = APIRouter(prefix="/cleaning", tags=["Data Cleaning"])


@router.post(
    "/",
    response_model=DataCleaningResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Clean dataset",
    description="Perform data cleaning operations like removing duplicates, handling missing values, and dropping columns"
)
def clean_dataset(request: DataCleaningRequest):
    """
    Clean the dataset based on specified operations.
    
    - **file_id**: The file identifier returned from upload
    - **drop_duplicates**: Remove duplicate rows
    - **drop_na**: Remove rows with missing values
    - **fill_na**: Fill missing values with specified values (dict of column: value)
    - **columns_to_drop**: List of column names to drop
    
    Returns information about the cleaning operation.
    """
    return clean_data(request)


@router.post(
    "/enhanced",
    response_model=EnhancedCleaningResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Enhanced data cleaning (Excel Copilot-like)",
    description="Perform intelligent data cleaning with column normalization, smart missing value handling, type detection, and detailed operation logging"
)
def enhanced_clean_dataset(request: EnhancedCleaningRequest):
    """
    Perform enhanced data cleaning with Excel Copilot-like features.
    
    - **file_id**: The file identifier returned from upload
    - **normalize_columns**: Normalize column names (lowercase, strip, replace spaces with underscores)
    - **remove_empty_rows**: Remove rows where all values are null
    - **remove_empty_columns**: Remove columns where all values are null
    - **drop_duplicates**: Remove duplicate rows
    - **drop_na**: Remove rows with any missing values
    - **smart_fill_missing**: Smart fill missing values (median for numeric, mode for categorical)
    - **auto_detect_types**: Auto-detect and convert data types (dates, numbers)
    - **fill_na**: Manual fill values per column (dict of column: value)
    - **columns_to_drop**: List of column names to drop
    
    Returns detailed information about all cleaning operations performed.
    """
    return enhanced_clean_data(request)
