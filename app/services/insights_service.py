import pandas as pd
from fastapi import HTTPException
from typing import Dict, Any

from app.utils import get_dataframe
from app.models import DataInsightsResponse


def get_data_insights(file_id: str) -> DataInsightsResponse:
    """
    Generate basic insights about the dataset
    
    Args:
        file_id: The file identifier
        
    Returns:
        DataInsightsResponse with insights
    """
    try:
        # Get the dataframe
        df = get_dataframe(file_id)
        
        # Column information
        column_info = {}
        for col in df.columns:
            column_info[col] = {
                "dtype": str(df[col].dtype),
                "non_null_count": int(df[col].count()),
                "null_count": int(df[col].isna().sum()),
                "unique_values": int(df[col].nunique())
            }
        
        # Numerical summary
        numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
        numerical_summary = {}
        
        if numerical_cols:
            stats = df[numerical_cols].describe()
            for col in numerical_cols:
                numerical_summary[col] = {
                    "mean": float(stats[col]['mean']) if 'mean' in stats.index else None,
                    "std": float(stats[col]['std']) if 'std' in stats.index else None,
                    "min": float(stats[col]['min']) if 'min' in stats.index else None,
                    "25%": float(stats[col]['25%']) if '25%' in stats.index else None,
                    "50%": float(stats[col]['50%']) if '50%' in stats.index else None,
                    "75%": float(stats[col]['75%']) if '75%' in stats.index else None,
                    "max": float(stats[col]['max']) if 'max' in stats.index else None
                }
        
        # Missing values
        missing_values = df.isna().sum().to_dict()
        missing_values = {k: int(v) for k, v in missing_values.items()}
        
        # Duplicates count
        duplicates_count = int(df.duplicated().sum())
        
        # Prepare response
        response = DataInsightsResponse(
            file_id=file_id,
            rows=len(df),
            columns=len(df.columns),
            column_info=column_info,
            numerical_summary=numerical_summary,
            missing_values=missing_values,
            duplicates_count=duplicates_count
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")
