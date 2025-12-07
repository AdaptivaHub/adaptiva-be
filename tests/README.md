# Adaptiva Backend Tests

This folder contains all tests for the Adaptiva Data Analysis API.

## Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests (isolated, no external deps)
│   ├── test_upload_service.py
│   └── test_chart_service.py
├── integration/          # Integration tests (full API flow)
│   ├── test_upload_endpoint.py
│   └── test_chart_endpoint.py
└── fixtures/             # Test data files
    ├── sample.csv
    └── sample.xlsx
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_upload_service.py -v

# Run specific test
pytest tests/unit/test_upload_service.py::TestProcessFileUpload::test_valid_csv_upload -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

## Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<scenario>_<expected_result>`

Example:
```python
class TestProcessFileUpload:
    def test_valid_csv_returns_file_id(self):
        ...
    
    def test_empty_file_raises_400(self):
        ...
```

## Fixtures

Common fixtures are defined in `conftest.py`:
- `client` - FastAPI TestClient
- `sample_csv_content` - Raw CSV bytes
- `sample_excel_file` - Excel file with formatting
- `uploaded_csv_file` - Pre-uploaded CSV (returns file_id)
- `uploaded_excel_file` - Pre-uploaded Excel (returns file_id)

## Writing Tests

### Unit Tests
- Test individual functions/methods in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test full API request/response flow
- Use real storage (but cleared between tests)
- Test error handling and edge cases

## Test Requirements

Requirements documents in `docs/requirements/` specify:
- Acceptance criteria (what to test)
- Test cases (specific scenarios)
- Expected inputs/outputs
