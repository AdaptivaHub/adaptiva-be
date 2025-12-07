from fastapi import APIRouter, HTTPException
from app.models import PreviewRequest, PreviewResponse, ErrorResponse
from app.services import get_formatted_preview

router = APIRouter(prefix="/preview", tags=["Data Preview"])


@router.post(
    "/",
    response_model=PreviewResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get formatted data preview",
    description="Get a preview of the uploaded data with Excel formatting preserved"
)
async def preview_data(request: PreviewRequest):
    """
    Get a formatted preview of uploaded data.
    
    - **file_id**: ID of the uploaded file
    - **max_rows**: Maximum number of rows to return (default: 100, max: 1000)
    
    Returns data with formatting preserved (dates, currencies, percentages, etc.)
    """
    return await get_formatted_preview(request.file_id, request.max_rows)
