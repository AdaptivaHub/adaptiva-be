"""
Unit tests for chart validation service.

Tests validation logic that applies to all ChartSpecs regardless of source
(manual or AI-generated).
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from app.models.chart_spec import (
    ChartSpec,
    AxisConfig,
    YAxisConfig,
    SeriesConfig,
    AggregationConfig,
    FiltersConfig,
    FilterCondition,
)
from app.services.chart_validation import (
    validate_chart_spec,
    validate_columns_exist,
    validate_chart_type_requirements,
    validate_column_types,
    ValidationError,
    ValidationResult,
)


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for validation tests."""
    return pd.DataFrame({
        "category": ["A", "B", "C", "D"],
        "region": ["North", "South", "East", "West"],
        "revenue": [1000.0, 2000.0, 1500.0, 2500.0],
        "quantity": [10, 20, 15, 25],
        "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"]),
    })


class TestValidateColumnsExist:
    """Tests for column existence validation."""

    def test_valid_columns_pass(self, sample_dataframe):
        """All referenced columns exist - should pass."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        errors = validate_columns_exist(spec, sample_dataframe)
        
        assert len(errors) == 0

    def test_invalid_x_column_fails(self, sample_dataframe):
        """Non-existent x_axis column should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="nonexistent"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        errors = validate_columns_exist(spec, sample_dataframe)
        
        assert len(errors) == 1
        assert errors[0].field == "x_axis.column"
        assert errors[0].code == "column_not_found"
        assert "nonexistent" in errors[0].message

    def test_invalid_y_column_fails(self, sample_dataframe):
        """Non-existent y_axis column should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["nonexistent"])
        )
        
        errors = validate_columns_exist(spec, sample_dataframe)
        
        assert len(errors) == 1
        assert errors[0].field == "y_axis.columns[0]"

    def test_invalid_group_column_fails(self, sample_dataframe):
        """Non-existent series.group_column should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            series=SeriesConfig(group_column="nonexistent")
        )
        
        errors = validate_columns_exist(spec, sample_dataframe)
        
        assert len(errors) == 1
        assert errors[0].field == "series.group_column"

    def test_invalid_filter_column_fails(self, sample_dataframe):
        """Non-existent filter column should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[FilterCondition(column="nonexistent", operator="eq", value=1)]
            )
        )
        
        errors = validate_columns_exist(spec, sample_dataframe)
        
        assert len(errors) == 1
        assert "filters" in errors[0].field

    def test_multiple_invalid_columns_all_reported(self, sample_dataframe):
        """Multiple invalid columns should all be reported."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="bad_x"),
            y_axis=YAxisConfig(columns=["bad_y"]),
            series=SeriesConfig(group_column="bad_group")
        )
        
        errors = validate_columns_exist(spec, sample_dataframe)
        
        assert len(errors) == 3


class TestValidateChartTypeRequirements:
    """Tests for chart-type-specific validation."""

    def test_bar_chart_requires_y_axis(self, sample_dataframe):
        """Bar chart without y_axis should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category")
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 1
        assert errors[0].code == "missing_required_field"
        assert "y_axis" in errors[0].message

    def test_bar_chart_with_y_axis_passes(self, sample_dataframe):
        """Bar chart with y_axis should pass."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 0

    def test_line_chart_requires_y_axis(self, sample_dataframe):
        """Line chart without y_axis should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="line",
            x_axis=AxisConfig(column="date")
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 1

    def test_scatter_chart_requires_y_axis(self, sample_dataframe):
        """Scatter chart without y_axis should fail."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="scatter",
            x_axis=AxisConfig(column="revenue")
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 1

    def test_histogram_does_not_require_y_axis(self, sample_dataframe):
        """Histogram without y_axis should pass."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="histogram",
            x_axis=AxisConfig(column="revenue")
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 0

    def test_pie_does_not_require_y_axis(self, sample_dataframe):
        """Pie chart can work without y_axis (uses value counts)."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="pie",
            x_axis=AxisConfig(column="category")
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 0

    def test_box_does_not_require_y_axis(self, sample_dataframe):
        """Box plot without y_axis should pass (uses x distribution)."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="box",
            x_axis=AxisConfig(column="revenue")
        )
        
        errors = validate_chart_type_requirements(spec)
        
        assert len(errors) == 0


class TestValidateColumnTypes:
    """Tests for column type compatibility warnings."""

    def test_numeric_y_axis_passes(self, sample_dataframe):
        """Numeric y_axis column should pass without warning."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        warnings = validate_column_types(spec, sample_dataframe)
        
        assert len(warnings) == 0

    def test_non_numeric_y_axis_warns(self, sample_dataframe):
        """Non-numeric y_axis for bar/line/scatter should warn."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="revenue"),
            y_axis=YAxisConfig(columns=["category"])  # categorical, not numeric
        )
        
        warnings = validate_column_types(spec, sample_dataframe)
        
        assert len(warnings) == 1
        assert warnings[0].code == "type_mismatch"

    def test_histogram_numeric_x_passes(self, sample_dataframe):
        """Histogram with numeric x should pass."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="histogram",
            x_axis=AxisConfig(column="revenue")
        )
        
        warnings = validate_column_types(spec, sample_dataframe)
        
        assert len(warnings) == 0


class TestValidateChartSpec:
    """Tests for the main validation function."""

    def test_valid_spec_returns_success(self, sample_dataframe):
        """Valid spec should return success result."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        with patch('app.services.chart_validation.get_dataframe', return_value=sample_dataframe):
            result = validate_chart_spec(spec)
        
        assert result.valid is True
        assert len(result.errors) == 0

    def test_invalid_spec_returns_errors(self, sample_dataframe):
        """Invalid spec should return errors."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="nonexistent")
        )
        
        with patch('app.services.chart_validation.get_dataframe', return_value=sample_dataframe):
            result = validate_chart_spec(spec)
        
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validation_includes_warnings(self, sample_dataframe):
        """Validation should include warnings for type mismatches."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="revenue"),
            y_axis=YAxisConfig(columns=["category"])  # categorical y for bar
        )
        
        with patch('app.services.chart_validation.get_dataframe', return_value=sample_dataframe):
            result = validate_chart_spec(spec)
        
        # Should pass but with warnings
        assert result.valid is True
        assert len(result.warnings) > 0

    def test_file_not_found_returns_error(self):
        """Non-existent file should return error."""
        spec = ChartSpec(
            file_id="nonexistent-file",
            chart_type="bar",
            x_axis=AxisConfig(column="category")
        )
        
        with patch('app.services.chart_validation.get_dataframe', side_effect=ValueError("File not found")):
            result = validate_chart_spec(spec)
        
        assert result.valid is False
        assert any(e.code == "file_not_found" for e in result.errors)


class TestValidationResult:
    """Tests for ValidationResult structure."""

    def test_validation_result_structure(self):
        """ValidationResult should have expected structure."""
        result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[ValidationError(field="test", code="test_warn", message="Test warning")]
        )
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.warnings[0].field == "test"

    def test_validation_error_with_suggestion(self):
        """ValidationError can include suggestion."""
        error = ValidationError(
            field="x_axis.column",
            code="column_not_found",
            message="Column 'reveneu' not found",
            suggestion="Did you mean 'revenue'?"
        )
        
        assert error.suggestion == "Did you mean 'revenue'?"
