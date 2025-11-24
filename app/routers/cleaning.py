from fastapi import APIRouter
from app.models import DataCleaningRequest, DataCleaningResponse, ErrorResponse
from app.services import clean_data

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
