import pandas as pd
from fastapi import HTTPException

from app.utils import get_dataframe, update_dataframe
from app.models import DataCleaningRequest, DataCleaningResponse


def clean_data(request: DataCleaningRequest) -> DataCleaningResponse:
    """
    Clean the dataset based on specified operations
    
    Args:
        request: DataCleaningRequest with cleaning parameters
        
    Returns:
        DataCleaningResponse with cleaning results
    """
    try:
        # Get the dataframe
        df = get_dataframe(request.file_id)
        
        # Store original dimensions
        rows_before = len(df)
        columns_before = len(df.columns)
        
        # Drop specified columns
        if request.columns_to_drop:
            cols_to_drop = [col for col in request.columns_to_drop if col in df.columns]
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
        
        # Drop duplicates
        if request.drop_duplicates:
            df = df.drop_duplicates()
        
        # Handle missing values
        if request.drop_na:
            df = df.dropna()
        elif request.fill_na:
            for column, value in request.fill_na.items():
                if column in df.columns:
                    df[column] = df[column].fillna(value)
        
        # Store updated dimensions
        rows_after = len(df)
        columns_after = len(df.columns)
        
        # Update the stored dataframe
        update_dataframe(request.file_id, df)
        
        # Prepare response
        response = DataCleaningResponse(
            file_id=request.file_id,
            rows_before=rows_before,
            rows_after=rows_after,
            columns_before=columns_before,
            columns_after=columns_after,
            message=f"Data cleaned successfully. Removed {rows_before - rows_after} rows and {columns_before - columns_after} columns."
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning data: {str(e)}")
