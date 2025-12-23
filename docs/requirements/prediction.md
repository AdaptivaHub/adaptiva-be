# Feature: Predictive Models

## Overview
Enable users to build and visualize simple predictive models (Linear Regression and Decision Trees) on their uploaded data. Models can be used to predict values, understand feature relationships, and enhance chart visualizations with trend lines and forecasts.

## User Story
As a data analyst,
I want to train predictive models on my uploaded data,
So that I can forecast values, identify patterns, and gain insights into feature relationships.

## Sub-Features

### 1. Linear Regression Models
Train regression models to predict continuous numerical values and visualize relationships through trend lines on charts.

### 2. Decision Tree Models
Train decision tree models for classification or regression tasks, with tree diagram visualization and feature importance analysis.

### 3. Model-Enhanced Charts
Overlay predictions, trend lines, and decision boundaries on existing chart visualizations.

### 4. Predictions Export
Export model predictions to CSV or include them in the data preview/spreadsheet view.

---

## Functional Requirements

### FR-1: Multiple Feature Support
- System must handle multiple input variables (X₁, X₂, …, Xₙ) per target variable (Y)
- Users can select any combination of columns as feature inputs
- System validates that selected features are compatible with the chosen model type

### FR-2: Target Variable Selection
- User can choose which column to predict (target/dependent variable)
- System validates that target column exists and is appropriate for model type:
  - Linear Regression: Numerical columns only
  - Decision Tree: Numerical (regression) or categorical (classification) columns

### FR-3: Data Validation & Cleaning
- Automatically detect categorical vs numerical features
- Handle categorical features via label encoding or one-hot encoding
- Remove rows with missing values in selected columns (with count notification)
- Warn about potential data issues:
  - Insufficient data points (< 10 rows after cleaning)
  - High percentage of missing values (> 50% in any selected column)
  - Low variance columns (single unique value)

### FR-4: Model Training & Evaluation
Train models on uploaded data and provide appropriate evaluation metrics:

**Linear Regression Metrics:**
- R² Score (coefficient of determination)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- Model coefficients with feature names

**Decision Tree Metrics:**
- For Classification:
  - Accuracy score
  - Confusion matrix
  - Cross-validation scores (5-fold)
  - Per-class precision/recall (optional)
- For Regression:
  - R² Score
  - MAE, RMSE
  - Cross-validation scores (5-fold)

### FR-5: Predictions Export
- WIP

### FR-6: Visualization of Models

**Linear Regression Visualization:**
- Regression line overlay on scatter plots
- Display equation (y = mx + b) and R² on chart
- Support for multiple regression (show partial regression plots)
- Residual plots (optional)

**Decision Tree Visualization:**
- Tree diagram showing decision nodes and splits
- Maximum depth limit for readability (configurable, default 4)
- Node labels with feature names, thresholds, and sample counts
- Color-coded by class (classification) or value range (regression)

### FR-7: Basic Explainability

**For Decision Trees:**
- Feature importance bar chart
- Percentage contribution of each feature
- Decision path for individual predictions (optional)

**For Linear Regression:**
- Coefficient values for each feature
- Coefficient interpretation (positive/negative impact)
- Standardized coefficients for feature comparison (optional)

---

## Acceptance Criteria

### Linear Regression

#### AC-1: Train Linear Regression Model
- **Given**: A dataset with numerical columns
- **When**: User selects target column, feature columns, and requests linear regression training
- **Then**: Model is trained and metrics (R², MAE, RMSE) are returned

#### AC-2: Multiple Features Support
- **Given**: A dataset with multiple numerical columns
- **When**: User selects 3+ feature columns for linear regression
- **Then**: Model trains successfully with all features and returns per-feature coefficients

#### AC-3: Regression Line on Scatter Plot
- **Given**: A trained linear regression model with single feature
- **When**: User requests scatter plot with trend line
- **Then**: Chart displays data points with regression line overlay and equation annotation

#### AC-4: Invalid Target Column
- **Given**: A categorical column selected as target for linear regression
- **When**: Training is requested
- **Then**: 400 error returned with message about numerical target requirement

#### AC-5: Insufficient Data
- **Given**: A dataset with fewer than 10 valid rows after cleaning
- **When**: Training is requested
- **Then**: 400 error returned with message about insufficient data

### Decision Tree

#### AC-6: Train Decision Tree Classifier
- **Given**: A dataset with categorical target column
- **When**: User selects target and features for decision tree classification
- **Then**: Model trains and returns accuracy, confusion matrix, and cross-validation scores

#### AC-7: Train Decision Tree Regressor
- **Given**: A dataset with numerical target column
- **When**: User selects target and features for decision tree regression
- **Then**: Model trains and returns R², MAE, RMSE, and cross-validation scores

#### AC-8: Feature Importance
- **Given**: A trained decision tree model
- **When**: Model training completes
- **Then**: Response includes feature importance dictionary with percentage values

#### AC-9: Tree Diagram Generation
- **Given**: A trained decision tree model
- **When**: User requests tree visualization
- **Then**: A tree diagram is returned showing decision nodes, thresholds, and outcomes

#### AC-10: Categorical Feature Handling
- **Given**: A dataset with mix of categorical and numerical features
- **When**: Decision tree training is requested
- **Then**: Categorical features are automatically encoded and model trains successfully

### Predictions & Export

#### AC-11: Generate Predictions
- **Given**: A trained model (linear regression or decision tree)
- **When**: User requests predictions for the dataset
- **Then**: Predictions are generated for all rows

#### AC-12: Export Predictions CSV
- **Given**: Generated predictions
- **When**: User requests CSV export
- **Then**: CSV file is downloaded with original data plus prediction column

#### AC-13: Classification Probabilities
- **Given**: A trained decision tree classifier
- **When**: Predictions are generated
- **Then**: Response includes probability scores for each class

### Data Validation

#### AC-14: Missing Value Warning
- **Given**: A dataset with > 20% missing values in selected columns
- **When**: Training is initiated
- **Then**: Warning is included in response about data quality

#### AC-15: Categorical Detection
- **Given**: A column with string/object dtype
- **When**: Data validation occurs
- **Then**: Column is identified as categorical in the data info response

#### AC-16: Low Variance Warning
- **Given**: A feature column with single unique value
- **When**: Training is attempted with this feature
- **Then**: Warning returned about low variance feature

---

## API Contract

### Train Model

#### Endpoint: `POST /api/predictions/train`

**Request:**
```json
{
  "file_id": "uuid-string",
  "sheet_name": "Sheet1 (optional - for Excel files)",
  "model_type": "linear_regression | decision_tree_classifier | decision_tree_regressor",
  "target_column": "column_name",
  "feature_columns": ["column1", "column2", "column3"],
  "test_size": 0.2,
  "tree_max_depth": 5
}
```

**Response (Success - 200):**
```json
{
  "model_id": "uuid-string",
  "model_type": "linear_regression",
  "metrics": {
    "r2_score": 0.87,
    "mae": 1234.56,
    "rmse": 1567.89
  },
  "feature_info": {
    "coefficients": {
      "feature1": 2.34,
      "feature2": -0.56,
      "intercept": 1500.0
    }
  },
  "data_quality": {
    "rows_used": 450,
    "rows_dropped": 50,
    "warnings": ["20% of rows had missing values and were excluded"]
  },
  "predictions_sample": [1234.5, 2345.6, 3456.7, 4567.8, 5678.9],
  "message": "Model trained successfully with R² = 0.87"
}
```

**Response (Decision Tree Classifier - 200):**
```json
{
  "model_id": "uuid-string",
  "model_type": "decision_tree_classifier",
  "metrics": {
    "accuracy": 0.92,
    "confusion_matrix": [[45, 5], [3, 47]],
    "cross_validation_scores": [0.89, 0.91, 0.93, 0.90, 0.92],
    "cv_mean": 0.91,
    "cv_std": 0.014
  },
  "feature_info": {
    "feature_importance": {
      "feature1": 0.45,
      "feature2": 0.35,
      "feature3": 0.20
    }
  },
  "class_labels": ["Low", "High"],
  "data_quality": {
    "rows_used": 500,
    "rows_dropped": 0,
    "warnings": []
  },
  "message": "Model trained successfully with accuracy = 92%"
}
```

**Response (Error - 400):**
```json
{
  "error": "Invalid target column",
  "detail": "Column 'category' is categorical. Linear regression requires a numerical target column."
}
```

---

### Generate Predictions

#### Endpoint: `POST /api/predictions/predict`

**Request:**
```json
{
  "model_id": "uuid-string",
  "file_id": "uuid-string",
  "sheet_name": "Sheet1 (optional)",
  "include_probabilities": true
}
```

**Response (Success - 200):**
```json
{
  "model_id": "uuid-string",
  "predictions": [1234.5, 2345.6, 3456.7],
  "probabilities": null,
  "prediction_column_name": "predicted_sales",
  "rows_predicted": 500,
  "message": "Generated 500 predictions"
}
```

**Response (Classification with Probabilities - 200):**
```json
{
  "model_id": "uuid-string",
  "predictions": ["High", "Low", "High"],
  "probabilities": [
    {"High": 0.85, "Low": 0.15},
    {"High": 0.23, "Low": 0.77},
    {"High": 0.91, "Low": 0.09}
  ],
  "prediction_column_name": "predicted_category",
  "rows_predicted": 500,
  "message": "Generated 500 predictions"
}
```

---

### Export Predictions

#### Endpoint: `POST /api/predictions/export`

**Request:**
```json
{
  "model_id": "uuid-string",
  "file_id": "uuid-string",
  "sheet_name": "Sheet1 (optional)",
  "include_original_data": true,
  "include_probabilities": false
}
```

**Response (Success - 200):**
Returns CSV file download with `Content-Disposition: attachment; filename="predictions_export.csv"`

---

### Visualize Regression

#### Endpoint: `POST /api/predictions/chart/regression`

**Request:**
```json
{
  "file_id": "uuid-string",
  "sheet_name": "Sheet1 (optional)",
  "x_column": "feature_column",
  "y_column": "target_column",
  "show_trend_line": true,
  "show_equation": true,
  "show_confidence_interval": false,
  "title": "Sales vs Marketing Spend"
}
```

**Response (Success - 200):**
```json
{
  "chart_json": {
    "data": [...],
    "layout": {...}
  },
  "regression_info": {
    "equation": "y = 2.34x + 1500",
    "r2_score": 0.87,
    "slope": 2.34,
    "intercept": 1500.0
  },
  "message": "Scatter plot with regression line generated"
}
```

---

### Visualize Decision Tree

#### Endpoint: `POST /api/predictions/chart/tree`

**Request:**
```json
{
  "model_id": "uuid-string",
  "max_depth_display": 4,
  "show_feature_importance": true
}
```

**Response (Success - 200):**
```json
{
  "tree_diagram": {
    "format": "svg",
    "content": "<svg>...</svg>"
  },
  "feature_importance_chart": {
    "data": [...],
    "layout": {...}
  },
  "tree_rules": "Decision tree rules in text format...",
  "message": "Decision tree visualization generated"
}
```

---

### What-If Prediction

#### Endpoint: `POST /api/predictions/what-if`

**Request:**
```json
{
  "model_id": "uuid-string",
  "input_values": {
    "feature1": 50000,
    "feature2": "Summer",
    "feature3": 3.5
  }
}
```

**Response (Success - 200):**
```json
{
  "predicted_value": 127500.0,
  "prediction_class": null,
  "probabilities": null,
  "feature_contributions": {
    "feature1": 45000.0,
    "feature2": 12500.0,
    "feature3": 5000.0,
    "intercept": 65000.0
  },
  "message": "Prediction generated for custom input"
}
```

---

## Test Cases

### Linear Regression

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Train single feature | 1 feature + target | 200, R², MAE, RMSE, coefficient |
| TC-2 | Train multiple features | 3 features + target | 200, metrics + all coefficients |
| TC-3 | Categorical target | String column as target | 400, "numerical target required" |
| TC-4 | Missing feature column | Non-existent column name | 400, "column not found" |
| TC-5 | Scatter with trend line | file_id, x, y, show_trend_line | 200, chart with regression line |
| TC-6 | Insufficient data | < 10 rows | 400, "insufficient data" |
| TC-7 | All features null | Features with 100% null | 400, "no valid data" |

### Decision Tree

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-8 | Classification training | Categorical target | 200, accuracy, confusion matrix |
| TC-9 | Regression training | Numerical target | 200, R², MAE, RMSE |
| TC-10 | Feature importance | Any trained tree | 200, importance dict |
| TC-11 | Tree diagram | model_id | 200, SVG tree diagram |
| TC-12 | Mixed feature types | Categorical + numerical features | 200, auto-encoded |
| TC-13 | Cross-validation | Any training request | 200, CV scores in response |
| TC-14 | Deep tree warning | max_depth > 10 | Warning about overfitting |

### Predictions & Export

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-15 | Generate predictions | Valid model_id | 200, prediction array |
| TC-16 | Invalid model_id | Non-existent model | 404, "model not found" |
| TC-17 | Export CSV | model_id + file_id | 200, CSV file download |
| TC-18 | Classification probs | Classifier + include_probs | 200, probabilities array |
| TC-19 | What-if prediction | Input values dict | 200, single prediction |
| TC-20 | What-if missing feature | Incomplete input values | 400, "missing feature" |

### Data Validation

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-21 | High missing values | > 50% nulls | Warning in response |
| TC-22 | Low variance feature | Single unique value | Warning about feature |
| TC-23 | Categorical encoding | String features | Auto-encoded, success |
| TC-24 | Date column | Datetime feature | Converted to numeric |

---

## Dependencies

### Backend
- **scikit-learn**: LinearRegression, DecisionTreeClassifier, DecisionTreeRegressor
- **pandas**: Data manipulation and encoding
- **numpy**: Numerical operations
- **plotly**: Chart generation with trend lines
- **graphviz** (optional): Tree diagram generation

### Frontend
- **plotly.js**: Chart rendering
- **React components**: PredictionPanel, TreeViewer, TrendLineToggle

### Existing Services
- `storage.py`: DataFrame access via file_id
- `chart_service.py`: Base chart generation (extended for trend lines)

---

## Model Persistence

### In-Memory Storage (Current Scale)
```python
# app/utils/storage.py additions
trained_models: Dict[str, Any] = {}  # model_id -> trained model object
model_metadata: Dict[str, Dict] = {}  # model_id -> {type, features, target, metrics}
```

### Future Consideration
- Redis for model caching
- Database for model metadata and training history
- S3 for serialized model files (pickle/joblib)

---

## Security Considerations

### Model Training Limits
- Maximum features: 50 columns
- Maximum rows: 100,000 (for in-memory processing)
- Maximum tree depth: 20 (prevent memory issues)
- Training timeout: 60 seconds

### Input Validation
- Validate all column names exist in dataset
- Sanitize column names in equations/labels
- Prevent code injection in what-if inputs

---

## UI/UX Considerations

### Prediction Panel Location
- Accessible from ChartEditor as new tab/section
- Or standalone panel in data analysis view

### Model Training Flow
```
1. Select "Predictions" tab
2. Choose model type (Linear Regression / Decision Tree)
3. Select target column from dropdown
4. Multi-select feature columns
5. Click "Train Model"
6. View metrics and visualizations
7. Generate predictions or export
```

### Visual Feedback
- Loading spinner during training
- Success toast with key metric
- Warning banners for data quality issues
- Interactive coefficient/importance display

---

## Notes

- Model IDs are UUIDs, valid only for current session (in-memory storage)
- Predictions are generated on-demand, not stored permanently
- Tree diagrams may be simplified for display (max_depth_display vs actual max_depth)
- Cross-validation uses 5-fold by default
- Categorical encoding uses label encoding (ordinal) - consider one-hot for trees
- For time-series forecasting, see separate "Forecasting" feature spec (future)
