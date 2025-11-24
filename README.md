# Adaptiva Data Analysis API

A comprehensive FastAPI backend for data analysis with support for file upload, data cleaning, insights generation, chart creation, machine learning models, and export capabilities.

## Features

- **File Upload**: Upload CSV and XLSX files for analysis
- **Data Cleaning**: Remove duplicates, handle missing values, drop columns
- **Data Insights**: Get statistical summaries, column information, and data quality metrics
- **Chart Generation**: Create interactive charts using Plotly (bar, line, scatter, histogram, box, pie)
- **Machine Learning**: Train Linear Regression and Decision Tree models
- **Export**: Export data and insights to PDF or PowerPoint presentations

## Project Structure

```
adaptiva-be/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models/              # Pydantic models for request/response
│   │   └── __init__.py
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── cleaning.py
│   │   ├── insights.py
│   │   ├── charts.py
│   │   ├── ml.py
│   │   └── export.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── upload_service.py
│   │   ├── cleaning_service.py
│   │   ├── insights_service.py
│   │   ├── chart_service.py
│   │   ├── ml_service.py
│   │   └── export_service.py
│   └── utils/               # Utility functions
│       ├── __init__.py
│       └── storage.py
├── uploads/                 # Directory for uploaded and exported files
├── requirements.txt         # Python dependencies
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jfernando02/adaptiva-be.git
cd adaptiva-be
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. File Upload
**POST** `/api/upload/`

Upload a CSV or XLSX file for analysis.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (CSV or XLSX file)

**Response:**
```json
{
  "file_id": "uuid-string",
  "filename": "data.csv",
  "rows": 1000,
  "columns": 10,
  "column_names": ["col1", "col2", ...],
  "message": "File uploaded successfully"
}
```

### 2. Data Cleaning
**POST** `/api/cleaning/`

Clean the dataset by removing duplicates, handling missing values, or dropping columns.

**Request:**
```json
{
  "file_id": "uuid-string",
  "drop_duplicates": true,
  "drop_na": false,
  "fill_na": {"column_name": 0},
  "columns_to_drop": ["col1", "col2"]
}
```

**Response:**
```json
{
  "file_id": "uuid-string",
  "rows_before": 1000,
  "rows_after": 950,
  "columns_before": 10,
  "columns_after": 8,
  "message": "Data cleaned successfully..."
}
```

### 3. Data Insights
**GET** `/api/insights/{file_id}`

Get comprehensive insights about the dataset.

**Response:**
```json
{
  "file_id": "uuid-string",
  "rows": 950,
  "columns": 8,
  "column_info": {
    "column_name": {
      "dtype": "float64",
      "non_null_count": 950,
      "null_count": 0,
      "unique_values": 100
    }
  },
  "numerical_summary": {
    "column_name": {
      "mean": 50.5,
      "std": 15.2,
      "min": 0,
      "max": 100
    }
  },
  "missing_values": {"col1": 0, "col2": 5},
  "duplicates_count": 0
}
```

### 4. Chart Generation
**POST** `/api/charts/`

Generate interactive Plotly charts.

**Request:**
```json
{
  "file_id": "uuid-string",
  "chart_type": "bar",
  "x_column": "category",
  "y_column": "value",
  "title": "My Chart",
  "color_column": "group"
}
```

**Chart Types:** `bar`, `line`, `scatter`, `histogram`, `box`, `pie`

**Response:**
```json
{
  "chart_json": { ... },  // Plotly JSON specification
  "message": "Chart generated successfully"
}
```

### 5. Machine Learning
**POST** `/api/ml/train`

Train a machine learning model.

**Request:**
```json
{
  "file_id": "uuid-string",
  "model_type": "linear_regression",
  "target_column": "price",
  "feature_columns": ["feature1", "feature2"],
  "test_size": 0.2
}
```

**Model Types:** `linear_regression`, `decision_tree`

**Response:**
```json
{
  "model_type": "linear_regression",
  "metrics": {
    "mse": 10.5,
    "rmse": 3.24,
    "mae": 2.5,
    "r2_score": 0.85
  },
  "predictions_sample": [1.2, 3.4, 5.6],
  "feature_importance": {"feature1": 0.7, "feature2": 0.3},
  "message": "Model trained successfully..."
}
```

### 6. Export
**POST** `/api/export/`

Export data and insights to PDF or PowerPoint.

**Request:**
```json
{
  "file_id": "uuid-string",
  "export_format": "pdf",
  "include_insights": true,
  "include_charts": false
}
```

**Export Formats:** `pdf`, `pptx`

**Response:** File download

## Dependencies

- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing
- **Scikit-learn**: Machine learning
- **Plotly**: Interactive charts
- **ReportLab**: PDF generation
- **python-pptx**: PowerPoint generation
- **OpenPyXL**: Excel file support
- **Python-multipart**: File upload support
- **Pydantic**: Data validation

## Usage Example

```python
import requests

# 1. Upload a file
with open('data.csv', 'rb') as f:
    response = requests.post('http://localhost:8000/api/upload/', files={'file': f})
    file_id = response.json()['file_id']

# 2. Get insights
insights = requests.get(f'http://localhost:8000/api/insights/{file_id}')
print(insights.json())

# 3. Clean data
clean_response = requests.post('http://localhost:8000/api/cleaning/', json={
    'file_id': file_id,
    'drop_duplicates': True
})

# 4. Generate chart
chart_response = requests.post('http://localhost:8000/api/charts/', json={
    'file_id': file_id,
    'chart_type': 'bar',
    'x_column': 'category',
    'y_column': 'value'
})

# 5. Train ML model
ml_response = requests.post('http://localhost:8000/api/ml/train', json={
    'file_id': file_id,
    'model_type': 'linear_regression',
    'target_column': 'target',
    'feature_columns': ['feature1', 'feature2']
})

# 6. Export to PDF
export_response = requests.post('http://localhost:8000/api/export/', json={
    'file_id': file_id,
    'export_format': 'pdf',
    'include_insights': True
})
with open('export.pdf', 'wb') as f:
    f.write(export_response.content)
```

## Development

The application uses an in-memory storage system for uploaded dataframes. For production use, consider implementing:
- Database storage for persistence
- File storage service (S3, etc.)
- Authentication and authorization
- Rate limiting
- Caching
- Background tasks for long-running operations

## License

MIT License
