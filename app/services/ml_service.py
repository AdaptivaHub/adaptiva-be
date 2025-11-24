import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from typing import Dict

from app.utils import get_dataframe
from app.models import MLModelRequest, MLModelResponse, MLModelType


def train_ml_model(request: MLModelRequest) -> MLModelResponse:
    """
    Train a machine learning model
    
    Args:
        request: MLModelRequest with model parameters
        
    Returns:
        MLModelResponse with model results
    """
    try:
        # Get the dataframe
        df = get_dataframe(request.file_id)
        
        # Validate columns exist
        if request.target_column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Target column '{request.target_column}' not found in dataset"
            )
        
        missing_features = [col for col in request.feature_columns if col not in df.columns]
        if missing_features:
            raise HTTPException(
                status_code=400,
                detail=f"Feature columns not found in dataset: {', '.join(missing_features)}"
            )
        
        # Prepare data
        X = df[request.feature_columns].copy()
        y = df[request.target_column].copy()
        
        # Handle non-numeric data
        for col in X.columns:
            if X[col].dtype == 'object':
                # Simple label encoding for categorical variables
                X[col] = pd.Categorical(X[col]).codes
        
        if y.dtype == 'object':
            y = pd.Categorical(y).codes
        
        # Remove rows with NaN values
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        if len(X) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid data after removing missing values"
            )
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=request.test_size, random_state=42
        )
        
        # Train model
        if request.model_type == MLModelType.LINEAR_REGRESSION:
            model = LinearRegression()
        elif request.model_type == MLModelType.DECISION_TREE:
            model = DecisionTreeRegressor(random_state=42, max_depth=5)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model type: {request.model_type}"
            )
        
        model.fit(X_train, y_train)
        
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        metrics = {
            "mse": float(mse),
            "rmse": float(rmse),
            "mae": float(mae),
            "r2_score": float(r2)
        }
        
        # Get feature importance (if available)
        feature_importance = None
        if hasattr(model, 'feature_importances_'):
            importance_dict = dict(zip(request.feature_columns, model.feature_importances_))
            feature_importance = {k: float(v) for k, v in importance_dict.items()}
        elif hasattr(model, 'coef_'):
            coef_dict = dict(zip(request.feature_columns, model.coef_))
            feature_importance = {k: float(abs(v)) for k, v in coef_dict.items()}
        
        # Sample predictions (first 10)
        predictions_sample = y_pred[:10].tolist()
        
        # Prepare response
        response = MLModelResponse(
            model_type=request.model_type.value,
            metrics=metrics,
            predictions_sample=predictions_sample,
            feature_importance=feature_importance,
            message=f"Model trained successfully with R² score of {r2:.4f}"
        )
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error training model: {str(e)}")
