"""
Forecast Service - Time-series forecasting using Prophet
Ported from Multi-Agent-System-for-SMEs
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from datetime import datetime
from fastapi import HTTPException

from prophet import Prophet

from app.utils import get_dataframe
from app.models import (
    ForecastRequest,
    ForecastResponse,
    ForecastPrediction,
    ForecastableColumn,
    ForecastableColumnsResponse
)


# Keywords that indicate forecastable metrics
FORECASTABLE_KEYWORDS = [
    'sales', 'revenue', 'amount', 'total', 'quantity', 'units',
    'transactions', 'orders', 'demand', 'volume', 'count',
    'profit', 'margin', 'price', 'value', 'cost', 'income'
]

# Keywords to skip (ID columns, date parts)
SKIP_KEYWORDS = ['id', 'year', 'month', 'day', 'week', 'quarter', 'index']


def get_forecastable_columns(file_id: str) -> ForecastableColumnsResponse:
    """
    Detect which columns in a dataset can be forecasted.
    Returns date column paired with suitable target columns.
    """
    try:
        df = get_dataframe(file_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File ID {file_id} not found")
    
    forecast_candidates: List[ForecastableColumn] = []
    
    # Find date columns
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    
    # If no datetime columns, try to detect and convert date-like columns
    if not date_cols:
        for col in df.columns:
            if df[col].dtype == 'object':
                sample = df[col].dropna().head(100)
                try:
                    converted = pd.to_datetime(sample, errors='coerce')
                    if converted.notna().sum() / len(converted) > 0.5:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        date_cols.append(col)
                        break
                except:
                    continue
    
    if not date_cols:
        return ForecastableColumnsResponse(
            file_id=file_id,
            forecastable_columns=[],
            message="No date columns found in dataset"
        )
    
    date_col = date_cols[0]
    
    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    for col in numeric_cols:
        col_lower = col.lower()
        
        # Skip ID columns and date part columns
        if any(skip in col_lower for skip in SKIP_KEYWORDS):
            continue
        
        # Check if column name contains forecastable keywords
        is_forecastable = any(keyword in col_lower for keyword in FORECASTABLE_KEYWORDS)
        
        # Also check if it has good variation (not constant)
        unique_count = df[col].nunique()
        if unique_count > 10 and df[col].std() > 0:
            mean_val = df[col].mean()
            if mean_val != 0:
                variation_score = df[col].std() / abs(mean_val)
                if variation_score > 0.01:  # Has meaningful variation
                    is_forecastable = True
        
        if is_forecastable:
            forecast_candidates.append(ForecastableColumn(
                date_column=date_col,
                target_column=col,
                target_dtype=str(df[col].dtype),
                unique_values=unique_count
            ))
    
    return ForecastableColumnsResponse(
        file_id=file_id,
        forecastable_columns=forecast_candidates,
        message=f"Found {len(forecast_candidates)} forecastable columns"
    )


def generate_forecast(request: ForecastRequest) -> ForecastResponse:
    """
    Generate time-series forecast using Prophet.
    
    Args:
        request: ForecastRequest with file_id, optional date/target columns, periods
        
    Returns:
        ForecastResponse with predictions, trend, and summary statistics
    """
    try:
        df = get_dataframe(request.file_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File ID {request.file_id} not found")
    
    # Auto-detect columns if not specified
    date_col = request.date_column
    target_col = request.target_column
    
    if date_col is None or target_col is None:
        forecastable = get_forecastable_columns(request.file_id)
        if not forecastable.forecastable_columns:
            raise HTTPException(
                status_code=400, 
                detail="No forecastable columns detected. Please specify date_column and target_column."
            )
        date_col = forecastable.forecastable_columns[0].date_column
        target_col = forecastable.forecastable_columns[0].target_column
    
    # Validate columns exist
    if date_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Date column '{date_col}' not found in dataset")
    if target_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Target column '{target_col}' not found in dataset")
    
    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        try:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not convert '{date_col}' to datetime: {e}")
    
    # Prepare data for Prophet
    try:
        forecast_df = df[[date_col, target_col]].copy()
        forecast_df.columns = ['ds', 'y']
        forecast_df = forecast_df.dropna()
        
        # Aggregate by date (sum values for each date)
        forecast_df = forecast_df.groupby('ds').agg({'y': 'sum'}).reset_index()
        forecast_df = forecast_df.sort_values('ds')
        
        # Filter out zeros and outliers for better forecasting
        if len(forecast_df) > 10:
            q1 = forecast_df['y'].quantile(0.25)
            q3 = forecast_df['y'].quantile(0.75)
            iqr = q3 - q1
            forecast_df = forecast_df[
                (forecast_df['y'] >= q1 - 1.5 * iqr) &
                (forecast_df['y'] <= q3 + 1.5 * iqr)
            ]
        
        if len(forecast_df) < 10:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient data for forecasting. Need at least 10 data points, got {len(forecast_df)}"
            )
        
        training_points = len(forecast_df)
        
        # Train Prophet model
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=len(forecast_df) > 365
        )
        model.fit(forecast_df)
        
        # Make predictions
        future = model.make_future_dataframe(periods=request.periods)
        forecast = model.predict(future)
        
        # Extract future predictions only
        future_forecast = forecast.tail(request.periods)
        
        predictions = [
            ForecastPrediction(
                date=row['ds'].strftime('%Y-%m-%d'),
                predicted_value=round(float(row['yhat']), 2),
                lower_bound=round(float(row['yhat_lower']), 2),
                upper_bound=round(float(row['yhat_upper']), 2)
            )
            for _, row in future_forecast.iterrows()
        ]
        
        avg_prediction = float(future_forecast['yhat'].mean())
        trend = "increasing" if future_forecast['yhat'].iloc[-1] > future_forecast['yhat'].iloc[0] else "decreasing"
        
        return ForecastResponse(
            file_id=request.file_id,
            date_column=date_col,
            target_column=target_col,
            periods=request.periods,
            predictions=predictions,
            average_prediction=round(avg_prediction, 2),
            trend=trend,
            training_data_points=training_points,
            message=f"Successfully generated {request.periods}-day forecast for {target_col}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating forecast: {str(e)}")
