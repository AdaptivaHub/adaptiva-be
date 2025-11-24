from fastapi import APIRouter
from app.models import MLModelRequest, MLModelResponse, ErrorResponse
from app.services import train_ml_model

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.post(
    "/train",
    response_model=MLModelResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Train ML model",
    description="Train a machine learning model (Linear Regression or Decision Tree) on the dataset"
)
def train_model(request: MLModelRequest):
    """
    Train a machine learning model on the dataset.
    
    - **file_id**: The file identifier returned from upload
    - **model_type**: Type of model (linear_regression or decision_tree)
    - **target_column**: Column name to predict
    - **feature_columns**: List of column names to use as features
    - **test_size**: Proportion of data to use for testing (0.1 to 0.5)
    
    Returns:
    - Model performance metrics (MSE, RMSE, MAE, R²)
    - Sample predictions
    - Feature importance (if available)
    """
    return train_ml_model(request)
