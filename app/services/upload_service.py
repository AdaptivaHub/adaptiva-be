import pandas as pd
from fastapi import UploadFile, HTTPException
from typing import List, Optional, Tuple
import io
import openpyxl

from app.utils import generate_file_id, store_dataframe, store_file_content, HeaderDetector
from app.models import FileUploadResponse


# Confidence threshold for auto-applying detected headers
HEADER_CONFIDENCE_THRESHOLD = 0.7


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


def _detect_and_apply_header(
    df: pd.DataFrame,
    confidence_threshold: float = HEADER_CONFIDENCE_THRESHOLD
) -> Tuple[pd.DataFrame, int, float]:
    """
    Detect header row and apply it if confidence is high enough.
    
    Args:
        df: Raw DataFrame from file
        confidence_threshold: Minimum confidence to auto-apply header
        
    Returns:
        Tuple of (processed_df, header_row, confidence)
    """
    result = HeaderDetector.detect(df)
    
    if result.confidence >= confidence_threshold and result.header_row > 0:
        # Apply detected header
        df = HeaderDetector.apply_header(df, result.header_row)
    
    return df, result.header_row, result.confidence


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
    
    # Header detection results (for the primary/first sheet)
    header_row: Optional[int] = None
    header_confidence: Optional[float] = None
    
    try:
        if filename.endswith('.csv'):
            # Read CSV without assuming first row is header
            df = pd.read_csv(io.BytesIO(content), header=None)
            
            # Validate DataFrame
            if df.empty:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file is empty"
                )
            
            # Detect and apply header
            df, header_row, header_confidence = _detect_and_apply_header(df)
            
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
                    # Read without assuming first row is header
                    sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                    
                    # Skip completely empty sheets
                    if sheet_df.empty:
                        continue
                    
                    # Detect and apply header for this sheet
                    sheet_df, sheet_header_row, sheet_confidence = _detect_and_apply_header(sheet_df)
                    
                    # Store with composite key: file_id:sheet_name
                    store_dataframe(file_id, sheet_df, sheet_name)
                    loaded_sheets_count += 1
                    
                    # Keep reference to first non-empty sheet for response
                    if primary_df is None:
                        primary_df = sheet_df
                        active_sheet = sheet_name
                        header_row = sheet_header_row
                        header_confidence = sheet_confidence
                        
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
    
    # Build message with header detection info
    message = f"File uploaded successfully. Loaded {loaded_sheets_count} sheet(s)."
    if header_row is not None and header_confidence is not None:
        if header_confidence >= HEADER_CONFIDENCE_THRESHOLD and header_row > 0:
            message += f" Header detected at row {header_row + 1} (confidence: {header_confidence:.0%})."
        elif header_row == 0:
            message += f" Using row 1 as header (confidence: {header_confidence:.0%})."
      # Prepare response
    # Ensure column names are strings (may be integers if header detection didn't apply)
    column_names = [str(col) for col in df.columns.tolist()]
    
    response = FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=column_names,
        message=message,
        sheets=sheets,
        active_sheet=active_sheet,
        header_row=header_row,
        header_confidence=round(header_confidence, 3) if header_confidence is not None else None
    )
    
    return response
