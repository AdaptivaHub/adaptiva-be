"""
Enhanced Data Cleaning Service

Provides Excel Copilot-like data cleaning functionality including:
- Column name normalization
- Empty row/column removal
- Smart missing value detection and filling
- Automatic type detection
- Duplicate removal
- Comprehensive operation logging
"""
import re
import pandas as pd
from typing import List, Dict, Any, Tuple
from fastapi import HTTPException

from app.utils import get_dataframe, update_dataframe
from app.models import (
    EnhancedCleaningRequest,
    EnhancedCleaningResponse,
    CleaningOperation,
    ColumnChanges,
    MissingValuesSummary
)


def _normalize_column_name(name: str) -> str:
    """
    Normalize a column name:
    - Convert to lowercase
    - Strip whitespace
    - Replace spaces with underscores
    - Remove special characters except underscores
    """
    name = str(name).strip().lower()
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name


def _is_date_column(column_name: str) -> bool:
    """Check if column name suggests it contains date/time data"""
    date_patterns = ['date', 'time', 'created', 'updated', 'modified', 'timestamp', 'dt', 'dob']
    column_lower = column_name.lower()
    return any(pattern in column_lower for pattern in date_patterns)


def _try_convert_to_datetime(series: pd.Series) -> Tuple[pd.Series, bool]:
    """Try to convert a series to datetime, return (series, converted)"""
    if series.dtype == 'datetime64[ns]':
        return series, False
    
    try:
        converted = pd.to_datetime(series, errors='coerce')
        # Only consider successful if at least 50% of non-null values converted
        non_null_original = series.notna().sum()
        non_null_converted = converted.notna().sum()
        if non_null_original > 0 and non_null_converted / non_null_original >= 0.5:
            return converted, True
    except Exception:
        pass
    
    return series, False


def _try_convert_to_numeric(series: pd.Series) -> Tuple[pd.Series, bool]:
    """Try to convert a series to numeric, return (series, converted)"""
    if pd.api.types.is_numeric_dtype(series):
        return series, False
    
    try:
        converted = pd.to_numeric(series, errors='coerce')
        # Only consider successful if at least 50% of non-null values converted
        non_null_original = series.notna().sum()
        non_null_converted = converted.notna().sum()
        if non_null_original > 0 and non_null_converted / non_null_original >= 0.5:
            return converted, True
    except Exception:
        pass
    
    return series, False


def _get_missing_values_summary(df: pd.DataFrame) -> Dict[str, int]:
    """Get count of missing values per column"""
    return {col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0}


def enhanced_clean_data(request: EnhancedCleaningRequest) -> EnhancedCleaningResponse:
    """
    Perform enhanced data cleaning with Excel Copilot-like features
    
    Args:
        request: EnhancedCleaningRequest with cleaning parameters
        
    Returns:
        EnhancedCleaningResponse with detailed cleaning results and log
    """
    try:
        # Get the dataframe
        df = get_dataframe(request.file_id)
        
        # Store original dimensions
        rows_before = len(df)
        columns_before = len(df.columns)
        
        # Initialize tracking
        operations_log: List[CleaningOperation] = []
        column_changes = ColumnChanges()
        missing_before = _get_missing_values_summary(df)
        
        # 1. Normalize column names
        if request.normalize_columns:
            old_columns = list(df.columns)
            new_columns = [_normalize_column_name(col) for col in old_columns]
            
            # Handle duplicate column names after normalization
            seen = {}
            final_columns = []
            for col in new_columns:
                if col in seen:
                    seen[col] += 1
                    final_columns.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    final_columns.append(col)
            
            renamed_count = sum(1 for old, new in zip(old_columns, final_columns) if old != new)
            column_changes.renamed = {old: new for old, new in zip(old_columns, final_columns) if old != new}
            df.columns = final_columns
            
            if renamed_count > 0:
                operations_log.append(CleaningOperation(
                    operation="normalize_columns",
                    details=f"Normalized {renamed_count} column names to lowercase with underscores",
                    affected_count=renamed_count
                ))
        
        # 2. Drop specified columns
        if request.columns_to_drop:
            cols_to_drop = [col for col in request.columns_to_drop if col in df.columns]
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
                column_changes.dropped.extend(cols_to_drop)
                operations_log.append(CleaningOperation(
                    operation="drop_columns",
                    details=f"Dropped columns: {', '.join(cols_to_drop)}",
                    affected_count=len(cols_to_drop)
                ))
        
        # 3. Remove empty columns (all null values)
        if request.remove_empty_columns:
            empty_cols = df.columns[df.isna().all()].tolist()
            if empty_cols:
                df = df.drop(columns=empty_cols)
                column_changes.dropped.extend(empty_cols)
                operations_log.append(CleaningOperation(
                    operation="remove_empty_columns",
                    details=f"Removed empty columns: {', '.join(empty_cols)}",
                    affected_count=len(empty_cols)
                ))
        
        # 4. Remove empty rows (all null values)
        if request.remove_empty_rows:
            rows_with_data = df.dropna(how='all')
            empty_rows_count = len(df) - len(rows_with_data)
            if empty_rows_count > 0:
                df = rows_with_data
                operations_log.append(CleaningOperation(
                    operation="remove_empty_rows",
                    details=f"Removed {empty_rows_count} completely empty rows",
                    affected_count=empty_rows_count
                ))
        
        # 5. Auto-detect and convert types
        if request.auto_detect_types:
            type_conversions = {}
            
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Try date conversion first for likely date columns
                    if _is_date_column(col):
                        new_series, converted = _try_convert_to_datetime(df[col])
                        if converted:
                            df[col] = new_series
                            type_conversions[col] = 'datetime64[ns]'
                            continue
                    
                    # Try numeric conversion
                    new_series, converted = _try_convert_to_numeric(df[col])
                    if converted:
                        df[col] = new_series
                        type_conversions[col] = str(new_series.dtype)
                        continue
                    
                    # Try date conversion for non-date-named columns
                    if not _is_date_column(col):
                        new_series, converted = _try_convert_to_datetime(df[col])
                        if converted:
                            df[col] = new_series
                            type_conversions[col] = 'datetime64[ns]'
            
            if type_conversions:
                column_changes.type_converted = type_conversions
                operations_log.append(CleaningOperation(
                    operation="auto_detect_types",
                    details=f"Converted types for columns: {', '.join(type_conversions.keys())}",
                    affected_count=len(type_conversions)
                ))
        
        # 6. Smart fill missing values
        if request.smart_fill_missing:
            filled_count = 0
            fill_details = []
            
            for col in df.columns:
                if df[col].isna().sum() > 0:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        # Use median for numeric columns
                        median_val = df[col].median()
                        if pd.notna(median_val):
                            missing_count = df[col].isna().sum()
                            df[col] = df[col].fillna(median_val)
                            filled_count += missing_count
                            fill_details.append(f"{col}(median={median_val:.2f})")
                    else:
                        # Use mode for categorical columns
                        mode_val = df[col].mode()
                        if len(mode_val) > 0:
                            fill_value = mode_val.iloc[0]
                        else:
                            fill_value = 'Unknown'
                        missing_count = df[col].isna().sum()
                        df[col] = df[col].fillna(fill_value)
                        filled_count += missing_count
                        fill_details.append(f"{col}(mode={fill_value})")
            
            if filled_count > 0:
                operations_log.append(CleaningOperation(
                    operation="smart_fill_missing",
                    details=f"Filled {filled_count} missing values: {', '.join(fill_details[:5])}{'...' if len(fill_details) > 5 else ''}",
                    affected_count=filled_count
                ))
        
        # 7. Manual fill missing values
        if request.fill_na:
            filled_count = 0
            for column, value in request.fill_na.items():
                if column in df.columns:
                    missing_count = df[column].isna().sum()
                    df[column] = df[column].fillna(value)
                    filled_count += missing_count
            
            if filled_count > 0:
                operations_log.append(CleaningOperation(
                    operation="fill_na",
                    details=f"Manually filled {filled_count} values in columns: {', '.join(request.fill_na.keys())}",
                    affected_count=filled_count
                ))
        
        # 8. Drop duplicates
        if request.drop_duplicates:
            rows_before_dedup = len(df)
            df = df.drop_duplicates()
            duplicates_removed = rows_before_dedup - len(df)
            
            if duplicates_removed > 0:
                operations_log.append(CleaningOperation(
                    operation="drop_duplicates",
                    details=f"Removed {duplicates_removed} duplicate rows",
                    affected_count=duplicates_removed
                ))
        
        # 9. Drop all rows with any NA (if enabled)
        if request.drop_na:
            rows_before_dropna = len(df)
            df = df.dropna()
            rows_dropped = rows_before_dropna - len(df)
            
            if rows_dropped > 0:
                operations_log.append(CleaningOperation(
                    operation="drop_na",
                    details=f"Removed {rows_dropped} rows with missing values",
                    affected_count=rows_dropped
                ))
        
        # Store updated dimensions
        rows_after = len(df)
        columns_after = len(df.columns)
        
        # Get missing values after cleaning
        missing_after = _get_missing_values_summary(df)
        
        # Update the stored dataframe
        update_dataframe(request.file_id, df)
        
        # Build summary message
        operations_count = len(operations_log)
        rows_changed = rows_before - rows_after
        cols_changed = columns_before - columns_after
        
        message_parts = [f"Data cleaning completed with {operations_count} operations."]
        if rows_changed > 0:
            message_parts.append(f"Removed {rows_changed} rows.")
        if cols_changed > 0:
            message_parts.append(f"Removed {cols_changed} columns.")
        if not operations_log:
            message_parts = ["No cleaning operations were necessary."]
        
        return EnhancedCleaningResponse(
            file_id=request.file_id,
            rows_before=rows_before,
            rows_after=rows_after,
            columns_before=columns_before,
            columns_after=columns_after,
            operations_log=operations_log,
            column_changes=column_changes,
            missing_values_summary=MissingValuesSummary(
                before=missing_before,
                after=missing_after
            ),
            message=" ".join(message_parts)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning data: {str(e)}")
