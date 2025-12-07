import pandas as pd
from fastapi import UploadFile, HTTPException
from typing import Tuple
import io

from app.utils import generate_file_id, store_dataframe, store_file_content
from app.models import FileUploadResponse


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
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))
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
        message="File uploaded successfully"
    )
    
    return response
