from fastapi import APIRouter
from app.models import DataInsightsResponse, ErrorResponse
from app.services import get_data_insights

router = APIRouter(prefix="/insights", tags=["Data Insights"])


@router.get(
    "/{file_id}",
    response_model=DataInsightsResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get data insights",
    description="Generate basic statistical insights about the dataset including summary statistics, missing values, and data types"
)
def get_insights(file_id: str):
    """
    Get comprehensive insights about the dataset.
    
    - **file_id**: The file identifier returned from upload
    
    Returns:
    - Column information (data types, null counts, unique values)
    - Numerical summary statistics
    - Missing values count per column
    - Duplicate rows count
    """
    return get_data_insights(file_id)
