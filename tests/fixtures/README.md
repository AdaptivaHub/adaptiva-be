# Test Fixtures

This folder contains test data files used across tests.

## Files

### sample.csv
A simple CSV file with product data:
- id: Integer identifier
- name: Product name
- value: Numeric price
- category: Category (Electronics, Clothing, Home)
- date: Date string

### sample.xlsx (generated programmatically)
Excel files are generated in `conftest.py` fixtures to include:
- Number formatting (currency, percentages)
- Multiple data types
- Multiple sheets (for some fixtures)

## Usage

These files can be used directly in tests or as templates for fixture generation.

```python
# Using static CSV file
with open("tests/fixtures/sample.csv", "rb") as f:
    content = f.read()

# Using programmatic fixtures (preferred)
def test_something(sample_csv_content):
    # sample_csv_content is bytes from conftest.py
    pass
```
