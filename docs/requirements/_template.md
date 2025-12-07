# Feature: [Feature Name]

## Overview
Brief description of the feature.

## User Story
As a [type of user],
I want [goal/desire],
So that [benefit/value].

## Acceptance Criteria

### AC-1: [Criterion Name]
- **Given**: [Initial context]
- **When**: [Action taken]
- **Then**: [Expected result]

### AC-2: [Criterion Name]
- **Given**: [Initial context]
- **When**: [Action taken]
- **Then**: [Expected result]

## API Contract

### Endpoint: `[METHOD] /api/[path]`

**Request:**
```json
{
  "field": "type - description"
}
```

**Response (Success - 200):**
```json
{
  "field": "type - description"
}
```

**Response (Error - 4xx/5xx):**
```json
{
  "error": "string",
  "detail": "string"
}
```

## Test Cases

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-1 | Happy path | Valid input | Success response |
| TC-2 | Invalid input | Missing field | 400 error |
| TC-3 | Edge case | Empty data | Appropriate handling |

## Dependencies
- List any dependencies on other features or services

## Notes
- Additional context or implementation notes
