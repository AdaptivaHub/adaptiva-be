# Adaptiva Data Analysis API

A comprehensive FastAPI backend for data analysis with support for file upload, data cleaning, insights generation, chart creation and export capabilities.

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

## License

MIT License
