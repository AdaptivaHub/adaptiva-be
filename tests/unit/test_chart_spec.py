"""
Unit tests for ChartSpec model and chart validation service.

Tests the canonical ChartSpec schema that serves as the single source of truth
for all chart configurations (manual and AI-generated).
"""
import pytest
import pandas as pd
from typing import Dict, Any

from app.models.chart_spec import (
    ChartSpec,
    AxisConfig,
    YAxisConfig,
    SeriesConfig,
    AggregationConfig,
    FiltersConfig,
    FilterCondition,
    VisualStructureConfig,
    LegendConfig,
    InteractionConfig,
    StylingConfig,
)


class TestChartSpecModel:
    """Tests for ChartSpec Pydantic model validation."""

    def test_minimal_valid_spec(self):
        """Minimal valid ChartSpec with only required fields."""
        spec = ChartSpec(
            file_id="test-file-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category")
        )
        
        assert spec.file_id == "test-file-123"
        assert spec.chart_type == "bar"
        assert spec.x_axis.column == "category"
        assert spec.y_axis is None
        assert spec.version == "1.0"

    def test_full_valid_spec(self):
        """Full ChartSpec with all optional fields populated."""
        spec = ChartSpec(
            file_id="test-file-123",
            sheet_name="Sales",
            chart_type="bar",
            x_axis=AxisConfig(column="region", label="Sales Region"),
            y_axis=YAxisConfig(columns=["revenue", "profit"], label="Amount ($)"),
            series=SeriesConfig(group_column="quarter"),
            aggregation=AggregationConfig(method="sum", group_by=["region", "quarter"]),
            filters=FiltersConfig(
                conditions=[
                    FilterCondition(column="year", operator="eq", value=2024)
                ],
                logic="and"
            ),
            visual=VisualStructureConfig(
                title="Revenue by Region",
                stacking="grouped",
                secondary_y_axis=False
            ),
            legend=LegendConfig(visible=True, position="right"),
            interaction=InteractionConfig(
                zoom_scroll=True,
                responsive=True,
                modebar="hover",
                export_formats=["png", "svg"],
                tooltip_detail="summary"
            ),
            styling=StylingConfig(
                color_palette="vibrant",
                theme="light",
                show_data_labels=False
            )
        )
        
        assert spec.sheet_name == "Sales"
        assert spec.y_axis.columns == ["revenue", "profit"]
        assert spec.aggregation.method == "sum"
        assert spec.filters.conditions[0].value == 2024
        assert spec.visual.title == "Revenue by Region"
        assert spec.styling.color_palette == "vibrant"

    def test_invalid_chart_type_rejected(self):
        """Invalid chart_type should raise validation error."""
        with pytest.raises(ValueError):
            ChartSpec(
                file_id="test-file-123",
                chart_type="invalid_type",
                x_axis=AxisConfig(column="category")
            )

    def test_invalid_aggregation_method_rejected(self):
        """Invalid aggregation method should raise validation error."""
        with pytest.raises(ValueError):
            ChartSpec(
                file_id="test-file-123",
                chart_type="bar",
                x_axis=AxisConfig(column="category"),
                aggregation=AggregationConfig(method="invalid_agg")
            )

    def test_invalid_theme_rejected(self):
        """Invalid theme should raise validation error."""
        with pytest.raises(ValueError):
            ChartSpec(
                file_id="test-file-123",
                chart_type="bar",
                x_axis=AxisConfig(column="category"),
                styling=StylingConfig(theme="invalid_theme")
            )

    def test_defaults_applied_correctly(self):
        """Default values should be applied for optional configs."""
        spec = ChartSpec(
            file_id="test-file-123",
            chart_type="histogram",
            x_axis=AxisConfig(column="value")
        )
        
        # Check defaults
        assert spec.aggregation.method == "none"
        assert spec.legend.visible is True
        assert spec.legend.position == "right"
        assert spec.interaction.zoom_scroll is True
        assert spec.interaction.modebar == "hover"
        assert spec.styling.theme == "light"
        assert spec.styling.color_palette == "default"
        assert spec.styling.show_data_labels is False

    def test_filter_operators_valid(self):
        """All filter operators should be accepted."""
        operators = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "between", "contains"]
        
        for op in operators:
            condition = FilterCondition(column="test", operator=op, value=1)
            assert condition.operator == op

    def test_between_filter_with_value_end(self):
        """Between filter should accept value_end."""
        condition = FilterCondition(
            column="price",
            operator="between",
            value=100,
            value_end=500
        )
        
        assert condition.value == 100
        assert condition.value_end == 500

    def test_in_filter_with_list_value(self):
        """In filter should accept list values."""
        condition = FilterCondition(
            column="status",
            operator="in",
            value=["active", "pending", "completed"]
        )
        
        assert condition.value == ["active", "pending", "completed"]


class TestAxisConfig:
    """Tests for axis configuration models."""

    def test_x_axis_minimal(self):
        """X-axis with only column."""
        axis = AxisConfig(column="date")
        assert axis.column == "date"
        assert axis.label is None

    def test_x_axis_with_label(self):
        """X-axis with custom label."""
        axis = AxisConfig(column="date", label="Transaction Date")
        assert axis.label == "Transaction Date"

    def test_y_axis_single_column(self):
        """Y-axis with single column."""
        axis = YAxisConfig(columns=["revenue"])
        assert axis.columns == ["revenue"]

    def test_y_axis_multiple_columns(self):
        """Y-axis with multiple columns for multi-series."""
        axis = YAxisConfig(columns=["revenue", "profit", "costs"])
        assert len(axis.columns) == 3


class TestSeriesConfig:
    """Tests for series/grouping configuration."""

    def test_series_with_group_column(self):
        """Series config with group column."""
        series = SeriesConfig(group_column="category")
        assert series.group_column == "category"
        assert series.size_column is None

    def test_series_with_size_column(self):
        """Series config with size column for scatter/bubble."""
        series = SeriesConfig(group_column="category", size_column="population")
        assert series.size_column == "population"


class TestChartSpecSerialization:
    """Tests for serialization/deserialization."""

    def test_to_dict(self):
        """ChartSpec should serialize to dict."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="line",
            x_axis=AxisConfig(column="date"),
            y_axis=YAxisConfig(columns=["value"])
        )
        
        data = spec.model_dump()
        
        assert isinstance(data, dict)
        assert data["file_id"] == "test-123"
        assert data["chart_type"] == "line"
        assert data["x_axis"]["column"] == "date"

    def test_from_dict(self):
        """ChartSpec should deserialize from dict."""
        data = {
            "file_id": "test-123",
            "chart_type": "scatter",
            "x_axis": {"column": "x_val"},
            "y_axis": {"columns": ["y_val"]},
            "styling": {"theme": "dark"}
        }
        
        spec = ChartSpec.model_validate(data)
        
        assert spec.file_id == "test-123"
        assert spec.chart_type == "scatter"
        assert spec.styling.theme == "dark"

    def test_to_json(self):
        """ChartSpec should serialize to JSON string."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="pie",
            x_axis=AxisConfig(column="category")
        )
        
        json_str = spec.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "test-123" in json_str
        assert "pie" in json_str
