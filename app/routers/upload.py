from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models import FileUploadResponse, ErrorResponse
from app.services import process_file_upload

router = APIRouter(prefix="/upload", tags=["File Upload"])


@router.post(
    "/",
    response_model=FileUploadResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Upload CSV or XLSX file",
    description="Upload a CSV or XLSX file and convert it to a pandas DataFrame for analysis"
)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a data file for analysis.
    
    - **file**: CSV or XLSX file to upload
    
    Returns file_id to use in subsequent operations.
    """
    return await process_file_upload(file)
