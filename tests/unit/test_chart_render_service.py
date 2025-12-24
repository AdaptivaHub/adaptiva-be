"""
Unit tests for chart render service.

Tests the ChartSpec → Plotly JSON rendering pipeline.
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime

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
    StylingConfig,
    InteractionConfig,
)
from app.services.chart_render_service import (
    render_chart,
    apply_filters,
    apply_aggregation,
    build_plotly_figure,
    apply_styling,
    ChartRenderError,
)


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for rendering tests."""
    return pd.DataFrame({
        "category": ["A", "B", "C", "D", "A", "B", "C", "D"],
        "region": ["North", "North", "South", "South", "North", "North", "South", "South"],
        "revenue": [1000.0, 2000.0, 1500.0, 2500.0, 1100.0, 2100.0, 1600.0, 2600.0],
        "quantity": [10, 20, 15, 25, 11, 21, 16, 26],
        "date": pd.to_datetime([
            "2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01",
            "2024-02-01", "2024-02-01", "2024-02-01", "2024-02-01"
        ]),
    })


class TestApplyFilters:
    """Tests for data filtering."""

    def test_no_filters_returns_original(self, sample_dataframe):
        """No filters should return the original dataframe."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert len(result) == len(sample_dataframe)

    def test_eq_filter(self, sample_dataframe):
        """Equal filter should work."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[FilterCondition(column="region", operator="eq", value="North")]
            )
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert len(result) == 4
        assert all(result["region"] == "North")

    def test_gt_filter(self, sample_dataframe):
        """Greater than filter should work."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[FilterCondition(column="revenue", operator="gt", value=2000)]
            )
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert all(result["revenue"] > 2000)

    def test_in_filter(self, sample_dataframe):
        """In filter should work with list of values."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[FilterCondition(column="category", operator="in", value=["A", "B"])]
            )
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert all(result["category"].isin(["A", "B"]))

    def test_between_filter(self, sample_dataframe):
        """Between filter should work with value_end."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[FilterCondition(column="revenue", operator="between", value=1500, value_end=2100)]
            )
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert all((result["revenue"] >= 1500) & (result["revenue"] <= 2100))

    def test_and_logic(self, sample_dataframe):
        """Multiple filters with AND logic."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[
                    FilterCondition(column="region", operator="eq", value="North"),
                    FilterCondition(column="revenue", operator="gt", value=1500)
                ],
                logic="and"
            )
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert all((result["region"] == "North") & (result["revenue"] > 1500))

    def test_or_logic(self, sample_dataframe):
        """Multiple filters with OR logic."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            filters=FiltersConfig(
                conditions=[
                    FilterCondition(column="category", operator="eq", value="A"),
                    FilterCondition(column="category", operator="eq", value="D")
                ],
                logic="or"
            )
        )
        
        result = apply_filters(sample_dataframe, spec)
        
        assert all(result["category"].isin(["A", "D"]))


class TestApplyAggregation:
    """Tests for data aggregation."""

    def test_no_aggregation_returns_original(self, sample_dataframe):
        """No aggregation should return the original dataframe."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            aggregation=AggregationConfig(method="none")
        )
        
        result = apply_aggregation(sample_dataframe, spec)
        
        assert len(result) == len(sample_dataframe)

    def test_sum_aggregation(self, sample_dataframe):
        """Sum aggregation should group and sum."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            aggregation=AggregationConfig(method="sum", group_by=["category"])
        )
        
        result = apply_aggregation(sample_dataframe, spec)
        
        # 4 unique categories
        assert len(result) == 4
        # A: 1000 + 1100 = 2100
        a_revenue = result[result["category"] == "A"]["revenue"].iloc[0]
        assert a_revenue == 2100.0

    def test_mean_aggregation(self, sample_dataframe):
        """Mean aggregation should group and average."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            aggregation=AggregationConfig(method="mean", group_by=["category"])
        )
        
        result = apply_aggregation(sample_dataframe, spec)
        
        # A: (1000 + 1100) / 2 = 1050
        a_revenue = result[result["category"] == "A"]["revenue"].iloc[0]
        assert a_revenue == 1050.0

    def test_count_aggregation(self, sample_dataframe):
        """Count aggregation should count rows per group."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            aggregation=AggregationConfig(method="count", group_by=["category"])
        )
        
        result = apply_aggregation(sample_dataframe, spec)
        
        # Each category has 2 rows
        assert all(result["revenue"] == 2)


class TestBuildPlotlyFigure:
    """Tests for Plotly figure building."""

    def test_bar_chart(self, sample_dataframe):
        """Bar chart should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            visual=VisualStructureConfig(title="Test Bar Chart")
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None
        assert fig.layout.title.text == "Test Bar Chart"

    def test_line_chart(self, sample_dataframe):
        """Line chart should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="line",
            x_axis=AxisConfig(column="date"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None

    def test_scatter_chart(self, sample_dataframe):
        """Scatter chart should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="scatter",
            x_axis=AxisConfig(column="revenue"),
            y_axis=YAxisConfig(columns=["quantity"])
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None

    def test_histogram(self, sample_dataframe):
        """Histogram should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="histogram",
            x_axis=AxisConfig(column="revenue")
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None

    def test_pie_chart(self, sample_dataframe):
        """Pie chart should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="pie",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None

    def test_box_chart(self, sample_dataframe):
        """Box chart should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="box",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None

    def test_area_chart(self, sample_dataframe):
        """Area chart should produce valid Plotly figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="area",
            x_axis=AxisConfig(column="date"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        assert fig is not None

    def test_chart_with_series_grouping(self, sample_dataframe):
        """Chart with series grouping should create multiple traces."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            series=SeriesConfig(group_column="region")
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        # Should have 2 traces (North and South)
        assert len(fig.data) == 2

    def test_multiple_y_columns(self, sample_dataframe):
        """Multiple y columns should create multiple traces."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="line",
            x_axis=AxisConfig(column="date"),
            y_axis=YAxisConfig(columns=["revenue", "quantity"])
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        
        # Should have 2 traces
        assert len(fig.data) == 2


class TestApplyStyling:
    """Tests for styling application."""

    def test_color_palette_applied(self, sample_dataframe):
        """Color palette should be applied to figure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            styling=StylingConfig(color_palette="vibrant")
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        fig = apply_styling(fig, spec)
        
        # Figure should have styling applied (check colorway in layout)
        assert fig.layout.colorway is not None

    def test_dark_theme(self, sample_dataframe):
        """Dark theme should be applied."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            styling=StylingConfig(theme="dark")
        )
        
        fig = build_plotly_figure(sample_dataframe, spec)
        fig = apply_styling(fig, spec)
        
        assert fig is not None


class TestRenderChart:
    """Tests for the main render function."""

    def test_render_returns_valid_response(self, sample_dataframe):
        """Render should return chart_json and metadata."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"])
        )
        
        with patch('app.utils.storage.get_dataframe', return_value=sample_dataframe):
            result = render_chart(spec)
        
        assert "chart_json" in result
        assert "rendered_at" in result
        assert "spec_version" in result
        assert result["spec_version"] == "1.0"

    def test_render_with_full_pipeline(self, sample_dataframe):
        """Render with filters and aggregation."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="category"),
            y_axis=YAxisConfig(columns=["revenue"]),
            filters=FiltersConfig(
                conditions=[FilterCondition(column="region", operator="eq", value="North")]
            ),
            aggregation=AggregationConfig(method="sum", group_by=["category"])
        )
        
        with patch('app.utils.storage.get_dataframe', return_value=sample_dataframe):
            result = render_chart(spec)
        
        assert "chart_json" in result

    def test_render_file_not_found_raises(self):
        """Render should raise when file not found."""
        spec = ChartSpec(
            file_id="nonexistent",
            chart_type="bar",
            x_axis=AxisConfig(column="category")
        )
        
        with patch('app.utils.storage.get_dataframe', side_effect=ValueError("File not found")):
            with pytest.raises(ChartRenderError) as exc_info:
                render_chart(spec)
        
        assert "file" in str(exc_info.value).lower()

    def test_render_validation_failure_raises(self, sample_dataframe):
        """Render should raise on validation failure."""
        spec = ChartSpec(
            file_id="test-123",
            chart_type="bar",
            x_axis=AxisConfig(column="nonexistent")  # Invalid column
        )
        
        with patch('app.utils.storage.get_dataframe', return_value=sample_dataframe):
            with pytest.raises(ChartRenderError) as exc_info:
                render_chart(spec)
        
        assert "validation" in str(exc_info.value).lower() or "column" in str(exc_info.value).lower()
