import pandas as pd
from fastapi import UploadFile, HTTPException
from typing import Tuple, List, Optional
import io
import openpyxl

from app.utils import generate_file_id, store_dataframe, store_file_content
from app.models import FileUploadResponse


def get_excel_sheet_names(content: bytes) -> List[str]:
    """
    Get list of sheet names from an Excel file.
    
    Args:
        content: Raw bytes of the Excel file
        
    Returns:
        List of sheet names
    """
    workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    sheet_names = workbook.sheetnames
    workbook.close()
    return sheet_names


async def process_file_upload(file: UploadFile) -> FileUploadResponse:
    """
    Process uploaded CSV or XLSX file and convert to pandas DataFrame
    
    Args:
        file: The uploaded file
        
    Returns:
        FileUploadResponse with file metadata
    """
    # Read file content
    content = await file.read()
      # Determine file type and read accordingly
    filename = file.filename.lower()
    sheets: Optional[List[str]] = None
    active_sheet: Optional[str] = None
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # Get sheet names first
            sheets = get_excel_sheet_names(content)
            active_sheet = sheets[0] if sheets else None
            # Read the first sheet
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Only CSV and XLSX files are supported."
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Validate DataFrame
    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty"
        )
      # Generate file ID and store dataframe
    file_id = generate_file_id()
    store_dataframe(file_id, df)
    
    # Store original file content for formatted preview
    store_file_content(file_id, content, file.filename)
      # Prepare response
    response = FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=df.columns.tolist(),
        message="File uploaded successfully",
        sheets=sheets,
        active_sheet=active_sheet
    )
    
    return response
