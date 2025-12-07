# API Specifications

## Overview

The Adaptiva API follows RESTful conventions and uses JSON for request/response bodies (except file uploads which use multipart/form-data).

## Base URL

- Development: `http://localhost:8000/api`
- Production: `https://adaptiva-be.onrender.com/api`

## Authentication

Currently: None (open API)
Future: JWT or API key authentication recommended

## Common Response Formats

### Success Response
```json
{
  "field": "value",
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

Or for structured errors:
```json
{
  "error": "Error type",
  "detail": "Detailed error message"
}
```

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/upload/ | Upload CSV/XLSX file |
| POST | /api/preview/ | Get formatted data preview |
| POST | /api/cleaning/ | Clean data (remove duplicates, fill NA, etc.) |
| GET | /api/insights/{file_id} | Get data insights and statistics |
| POST | /api/charts/ai | Generate chart (AI-powered) |
| POST | /api/export/ | Export data to PDF |

## Content Types

| Endpoint | Request Content-Type | Response Content-Type |
|----------|---------------------|----------------------|
| /api/upload/ | multipart/form-data | application/json |
| All others | application/json | application/json |
| /api/export/ | application/json | application/pdf |

## Rate Limiting

Currently: None
Recommended: 100 requests/minute per IP

## File Size Limits

- Maximum file size: 10MB (configurable)
- Maximum rows: No hard limit (memory dependent)

## Detailed Endpoint Documentation

See requirements documents for detailed request/response schemas:
- [File Upload](../requirements/file-upload.md)
- [Chart Generation](../requirements/chart-generation.md)
