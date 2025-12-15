# Adaptiva Backend - Project Checklist

## Phase One Features

### File Upload
- [x] CSV file upload (AC-1)
- [x] Excel file upload with sheet detection (AC-2, AC-8)
- [x] File format validation (AC-3)
- [x] Empty file validation (AC-4)
- [x] Corrupted file handling (AC-5)
- [x] Metadata response (AC-7)
- [ ] File size limit configuration (AC-6)

### Data Preview
- [x] Preview uploaded files (AC-1)
- [x] Configurable row limit (AC-2)
- [x] Excel formatting preservation (AC-3)
- [x] CSV file support (AC-4)
- [x] File not found handling (AC-5)
- [x] Sheet selection for Excel (AC-7, AC-8)
- [x] Invalid sheet name handling (AC-9)

### Data Cleaning
- [x] Remove duplicates
- [x] Handle missing values (drop/fill)
- [x] Drop columns

### Data Insights
- [] Summary statistics
- [] Missing values analysis
- [] Data types info
- [] Duplicate detection

### Chart Generation
- [x] Bar chart (AC-1)
- [x] Line chart (AC-2)
- [x] Scatter plot (AC-3)
- [x] Histogram (AC-4)
- [x] Box plot (AC-5)
- [x] Pie chart (AC-6)
- [x] Color grouping (AC-7)
- [x] Invalid file/column handling (AC-8, AC-9)
- [x] Execution timeout (AC-16)

### AI Chart Generation
- [x] Automatic chart selection (AC-10)
- [x] User instructions support (AC-11)
- [x] Generated code return (AC-12)
- [x] Explanation return (AC-13)
- [x] Sandboxed execution (AC-14, AC-15)

### Machine Learning
- [] Linear regression model
- [] Decision tree model
- [] Model metrics (MSE, RMSE, MAE, R²)
- [] Sample predictions

### Export
- [] PDF export
- [] PowerPoint export
- [ ] Include charts in export

---

## Testing

### Unit Tests
- [x] Upload service tests
- [x] Chart service tests
- [ ] Cleaning service tests
- [ ] Insights service tests
- [ ] ML service tests
- [ ] Export service tests
- [ ] Preview service tests
- [] AI chart service tests

### Integration Tests
- [x] Upload endpoint tests
- [x] Preview endpoint tests
- [x] Chart endpoint tests
- [ ] Cleaning endpoint tests
- [ ] Insights endpoint tests
- [ ] ML endpoint tests
- [ ] Export endpoint tests

---

## Documentation

- [x] File upload requirements
- [x] Chart generation requirements
- [x] Data preview requirements
- [ ] Data cleaning requirements
- [ ] Insights requirements
- [ ] ML requirements
- [ ] Export requirements
- [x] Architecture overview
- [x] API specs (OpenAPI)

---

## Production Readiness

- [ ] Move to Redis/PostgreSQL storage
- [ ] Rate limiting for AI calls
- [ ] Response caching
- [ ] Authentication and security
