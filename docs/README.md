# Adaptiva Backend Documentation

This folder contains all documentation for the Adaptiva Data Analysis API.

## Structure

```
docs/
├── requirements/          # Feature requirements and specifications
│   ├── _template.md      # Template for new requirements
│   ├── file-upload.md    # File upload feature requirements
│   └── chart-generation.md # Chart generation requirements
├── api-specs/            # API specifications
│   └── openapi.md        # OpenAPI documentation notes
└── architecture/         # System architecture documents
    └── overview.md       # System architecture overview
```

## Quick Links

- [Architecture Overview](./architecture/overview.md)
- [File Upload Requirements](./requirements/file-upload.md)
- [Chart Generation Requirements](./requirements/chart-generation.md)

## For AI Assistants

When implementing features:
1. **First** read the relevant requirements document in `requirements/`
2. **Then** check existing tests in `tests/` for expected behavior
3. **Finally** implement the feature following the patterns in the codebase
