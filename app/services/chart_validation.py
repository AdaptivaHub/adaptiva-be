# filepath: c:\GitHub\adaptiva-be\app\services\chart_validation.py
"""
Chart validation service.

Provides validation logic for ChartSpec objects, checking:
- Column existence in the dataframe
- Chart-type-specific requirements
- Column type compatibility
"""
from typing import List, Optional
from dataclasses import dataclass, field
import pandas as pd

from app.models.chart_spec import ChartSpec
from app.utils.storage import get_dataframe


# Chart types that require a y_axis to be specified
CHARTS_REQUIRING_Y_AXIS = {"bar", "line", "scatter", "area", "heatmap"}

# Chart types that work without y_axis (use distribution/counts)
CHARTS_NOT_REQUIRING_Y_AXIS = {"histogram", "pie", "box"}


@dataclass
class ValidationError:
    """Represents a validation error or warning."""
    field: str
    code: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating a ChartSpec."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)


def validate_columns_exist(spec: ChartSpec, df: pd.DataFrame) -> List[ValidationError]:
    """
    Validate that all columns referenced in the spec exist in the dataframe.
    
    Args:
        spec: The ChartSpec to validate
        df: The pandas DataFrame to check against
        
    Returns:
        List of ValidationError for missing columns
    """
    errors: List[ValidationError] = []
    available_columns = set(df.columns)
    
    # Check x_axis column
    if spec.x_axis and spec.x_axis.column not in available_columns:
        errors.append(ValidationError(
            field="x_axis.column",
            code="column_not_found",
            message=f"Column '{spec.x_axis.column}' not found in data"
        ))
    
    # Check y_axis columns
    if spec.y_axis and spec.y_axis.columns:
        for i, col in enumerate(spec.y_axis.columns):
            if col not in available_columns:
                errors.append(ValidationError(
                    field=f"y_axis.columns[{i}]",
                    code="column_not_found",
                    message=f"Column '{col}' not found in data"
                ))
    
    # Check series.group_column
    if spec.series and spec.series.group_column:
        if spec.series.group_column not in available_columns:
            errors.append(ValidationError(
                field="series.group_column",
                code="column_not_found",
                message=f"Column '{spec.series.group_column}' not found in data"
            ))
    
    # Check series.size_column
    if spec.series and spec.series.size_column:
        if spec.series.size_column not in available_columns:
            errors.append(ValidationError(
                field="series.size_column",
                code="column_not_found",
                message=f"Column '{spec.series.size_column}' not found in data"
            ))
    
    # Check filter columns
    if spec.filters and spec.filters.conditions:
        for i, condition in enumerate(spec.filters.conditions):
            if condition.column not in available_columns:
                errors.append(ValidationError(
                    field=f"filters.conditions[{i}].column",
                    code="column_not_found",
                    message=f"Column '{condition.column}' not found in data"
                ))
    
    # Check aggregation.group_by columns
    if spec.aggregation and spec.aggregation.group_by:
        for i, col in enumerate(spec.aggregation.group_by):
            if col not in available_columns:
                errors.append(ValidationError(
                    field=f"aggregation.group_by[{i}]",
                    code="column_not_found",
                    message=f"Column '{col}' not found in data"
                ))
    
    return errors


def validate_chart_type_requirements(spec: ChartSpec) -> List[ValidationError]:
    """
    Validate chart-type-specific requirements.
    
    Args:
        spec: The ChartSpec to validate
        
    Returns:
        List of ValidationError for unmet requirements
    """
    errors: List[ValidationError] = []
    
    # Check if chart type requires y_axis
    if spec.chart_type in CHARTS_REQUIRING_Y_AXIS:
        if spec.y_axis is None or not spec.y_axis.columns:
            errors.append(ValidationError(
                field="y_axis",
                code="missing_required_field",
                message=f"Chart type '{spec.chart_type}' requires y_axis to be specified"
            ))
    
    return errors


def validate_column_types(spec: ChartSpec, df: pd.DataFrame) -> List[ValidationError]:
    """
    Validate column type compatibility with chart requirements.
    
    Returns warnings (not errors) for type mismatches that may still render
    but could produce unexpected results.
    
    Args:
        spec: The ChartSpec to validate
        df: The pandas DataFrame to check against
        
    Returns:
        List of ValidationError warnings for type mismatches
    """
    warnings: List[ValidationError] = []
    
    # For bar/line/scatter/area charts, y_axis should typically be numeric
    if spec.chart_type in {"bar", "line", "scatter", "area"}:
        if spec.y_axis and spec.y_axis.columns:
            for col in spec.y_axis.columns:
                if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                    warnings.append(ValidationError(
                        field=f"y_axis.columns",
                        code="type_mismatch",
                        message=f"Column '{col}' is not numeric; chart may not render as expected"
                    ))
    
    # For histogram, x should typically be numeric
    if spec.chart_type == "histogram":
        if spec.x_axis and spec.x_axis.column in df.columns:
            if not pd.api.types.is_numeric_dtype(df[spec.x_axis.column]):
                warnings.append(ValidationError(
                    field="x_axis.column",
                    code="type_mismatch",
                    message=f"Histogram x_axis column '{spec.x_axis.column}' is not numeric"
                ))
    
    return warnings


def validate_chart_spec(spec: ChartSpec, df: Optional[pd.DataFrame] = None) -> ValidationResult:
    """
    Main validation function - validates a ChartSpec against its data source.
    
    This function:
    1. Loads the dataframe from storage (if not provided)
    2. Validates chart type requirements
    3. Validates column existence
    4. Checks column type compatibility
    
    Args:
        spec: The ChartSpec to validate
        df: Optional pre-loaded dataframe. If provided, skips loading from storage.
          Returns:
        ValidationResult with valid flag, errors, and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    
    # Load the dataframe if not provided
    if df is None:
        try:
            df = get_dataframe(spec.file_id, spec.sheet_name)
        except ValueError as e:
            errors.append(ValidationError(
                field="file_id",
                code="file_not_found",
                message=str(e)
            ))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
    
    # Validate chart type requirements (doesn't need dataframe)
    errors.extend(validate_chart_type_requirements(spec))
    
    # Validate columns exist
    errors.extend(validate_columns_exist(spec, df))
    
    # Validate column types (warnings only)
    warnings.extend(validate_column_types(spec, df))
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
