import pandas as pd
from fastapi import UploadFile, HTTPException
from typing import List, Optional
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
    Process uploaded CSV or XLSX file and convert to pandas DataFrame.
    
    For Excel files, loads ALL sheets into memory using composite keys
    (file_id:sheet_name) for instant sheet switching.
    
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
    loaded_sheets_count = 0
    
    # Generate file ID upfront
    file_id = generate_file_id()
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
            
            # Validate DataFrame
            if df.empty:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file is empty"
                )
            
            # Store single dataframe for CSV (no sheet_name)
            store_dataframe(file_id, df, sheet_name=None)
            loaded_sheets_count = 1
            
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # Get all sheet names
            sheets = get_excel_sheet_names(content)
            
            if not sheets:
                raise HTTPException(
                    status_code=400,
                    detail="The Excel file contains no sheets"
                )
            
            active_sheet = sheets[0]
            
            # Load ALL sheets into memory with composite keys
            # Using pd.ExcelFile to read the file only once
            excel_file = pd.ExcelFile(io.BytesIO(content))
            
            primary_df = None
            for sheet_name in sheets:
                try:
                    sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    
                    # Skip completely empty sheets
                    if sheet_df.empty:
                        continue
                    
                    # Store with composite key: file_id:sheet_name
                    store_dataframe(file_id, sheet_df, sheet_name)
                    loaded_sheets_count += 1
                    
                    # Keep reference to first non-empty sheet for response
                    if primary_df is None:
                        primary_df = sheet_df
                        active_sheet = sheet_name
                        
                except Exception as sheet_error:
                    # Log but don't fail on individual sheet errors
                    print(f"Warning: Could not load sheet '{sheet_name}': {sheet_error}")
                    continue
            
            excel_file.close()
            
            if primary_df is None or loaded_sheets_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="The Excel file contains no valid data sheets"
                )
            
            df = primary_df
            
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Only CSV and XLSX files are supported."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Store original file content for formatted preview
    store_file_content(file_id, content, file.filename)
    
    # Prepare response
    response = FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=df.columns.tolist(),
        message=f"File uploaded successfully. Loaded {loaded_sheets_count} sheet(s).",
        sheets=sheets,
        active_sheet=active_sheet
    )
    
    return response
