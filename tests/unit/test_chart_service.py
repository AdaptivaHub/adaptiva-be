"""
Unit tests for the chart service.

Tests based on requirements in: docs/requirements/chart-generation.md
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import json

from app.services.chart_service import generate_chart
from app.models import ChartGenerationRequest, ChartGenerationResponse, ChartType


class TestGenerateChart:
    """Unit tests for generate_chart function."""
    
    @pytest.fixture
    def mock_dataframe(self):
        """Create a mock dataframe for chart testing."""
        return pd.DataFrame({
            'category': ['A', 'B', 'C', 'D'],
            'value': [10, 20, 15, 25],
            'count': [100, 200, 150, 250],
            'group': ['X', 'X', 'Y', 'Y']
        })
    
    def test_bar_chart_generation(self, mock_dataframe):
        """TC-1: Bar chart generates valid Plotly JSON."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category",
                y_column="value",
                title="Test Bar Chart"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.message == "Chart generated successfully"
            assert "data" in response.chart_json
            assert "layout" in response.chart_json
            # Verify it's a bar chart
            assert response.chart_json["data"][0]["type"] == "bar"
    
    def test_line_chart_generation(self, mock_dataframe):
        """TC-2: Line chart generates valid Plotly JSON."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.LINE,
                x_column="category",
                y_column="value",
                title="Test Line Chart"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.chart_json["data"][0]["type"] == "scatter"
            assert response.chart_json["data"][0]["mode"] == "lines"
    
    def test_scatter_chart_generation(self, mock_dataframe):
        """TC-3: Scatter plot generates valid Plotly JSON."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.SCATTER,
                x_column="value",
                y_column="count",
                title="Test Scatter Plot"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.chart_json["data"][0]["type"] == "scatter"
            assert response.chart_json["data"][0]["mode"] == "markers"
    
    def test_histogram_generation(self, mock_dataframe):
        """TC-4: Histogram generates valid Plotly JSON."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.HISTOGRAM,
                x_column="value",
                title="Test Histogram"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.chart_json["data"][0]["type"] == "histogram"
    
    def test_box_chart_generation(self, mock_dataframe):
        """TC-5: Box plot generates valid Plotly JSON."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BOX,
                x_column="group",
                y_column="value",
                title="Test Box Plot"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.chart_json["data"][0]["type"] == "box"
    
    def test_pie_chart_generation(self, mock_dataframe):
        """TC-6: Pie chart generates valid Plotly JSON."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.PIE,
                x_column="category",
                y_column="value",
                title="Test Pie Chart"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.chart_json["data"][0]["type"] == "pie"
    
    def test_pie_chart_without_y_uses_value_counts(self, mock_dataframe):
        """TC-6 variant: Pie chart without y_column uses value counts."""
        # Create dataframe with repeated categories
        df = pd.DataFrame({
            'category': ['A', 'A', 'B', 'B', 'B', 'C'],
            'value': [1, 2, 3, 4, 5, 6]
        })
        
        with patch('app.services.chart_service.get_dataframe', return_value=df):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.PIE,
                x_column="category",
                title="Category Distribution"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            assert response.chart_json["data"][0]["type"] == "pie"
    
    def test_chart_with_color_grouping(self, mock_dataframe):
        """TC-7: Chart with color_column groups data by color."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category",
                y_column="value",
                color_column="group",
                title="Grouped Bar Chart"
            )
            
            response = generate_chart(request)
            
            assert isinstance(response, ChartGenerationResponse)
            # Should have multiple traces for different groups
            assert len(response.chart_json["data"]) >= 1
    
    def test_custom_title_applied(self, mock_dataframe):
        """TC-11: Custom title is applied to chart."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category",
                y_column="value",
                title="My Custom Title"
            )
            
            response = generate_chart(request)
            
            assert response.chart_json["layout"]["title"]["text"] == "My Custom Title"
    
    def test_missing_y_column_for_bar_raises_400(self, mock_dataframe):
        """TC-8: Bar chart without y_column raises HTTPException 400."""
        from fastapi import HTTPException
        
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 400
            assert "y_column is required" in exc_info.value.detail
    
    def test_missing_y_column_for_line_raises_400(self, mock_dataframe):
        """Line chart without y_column raises HTTPException 400."""
        from fastapi import HTTPException
        
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.LINE,
                x_column="category"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 400
            assert "y_column is required" in exc_info.value.detail
    
    def test_missing_y_column_for_scatter_raises_400(self, mock_dataframe):
        """Scatter plot without y_column raises HTTPException 400."""
        from fastapi import HTTPException
        
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.SCATTER,
                x_column="category"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 400
            assert "y_column is required" in exc_info.value.detail
    
    def test_invalid_x_column_raises_400(self, mock_dataframe):
        """TC-9: Invalid x_column raises HTTPException 400."""
        from fastapi import HTTPException
        
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.HISTOGRAM,
                x_column="nonexistent_column"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 400
            assert "not found" in exc_info.value.detail
    
    def test_invalid_y_column_raises_400(self, mock_dataframe):
        """Invalid y_column raises HTTPException 400."""
        from fastapi import HTTPException
        
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category",
                y_column="nonexistent_column"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 400
            assert "not found" in exc_info.value.detail
    
    def test_invalid_color_column_raises_400(self, mock_dataframe):
        """Invalid color_column raises HTTPException 400."""
        from fastapi import HTTPException
        
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category",
                y_column="value",
                color_column="nonexistent_column"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 400
            assert "not found" in exc_info.value.detail
    
    def test_invalid_file_id_raises_404(self):
        """TC-10: Invalid file_id raises HTTPException 404."""
        from fastapi import HTTPException
        
        # Don't mock get_dataframe - let it raise ValueError
        request = ChartGenerationRequest(
            file_id="nonexistent-id",
            chart_type=ChartType.BAR,
            x_column="category",
            y_column="value"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            generate_chart(request)
        
        assert exc_info.value.status_code == 404


class TestChartJsonStructure:
    """Tests for Plotly JSON structure."""
    
    @pytest.fixture
    def mock_dataframe(self):
        return pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [10, 20, 15, 25, 30]
        })
    
    def test_chart_json_has_required_keys(self, mock_dataframe):
        """Chart JSON contains 'data' and 'layout' keys."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.LINE,
                x_column="x",
                y_column="y"
            )
            
            response = generate_chart(request)
            
            assert "data" in response.chart_json
            assert "layout" in response.chart_json
            assert isinstance(response.chart_json["data"], list)
            assert len(response.chart_json["data"]) > 0
    
    def test_chart_json_is_serializable(self, mock_dataframe):
        """Chart JSON can be serialized to string."""
        with patch('app.services.chart_service.get_dataframe', return_value=mock_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="x",
                y_column="y"
            )
            
            response = generate_chart(request)
            
            # Should not raise
            json_str = json.dumps(response.chart_json)
            assert isinstance(json_str, str)
            
            # Should be valid JSON
            parsed = json.loads(json_str)
            assert parsed == response.chart_json


class TestChartGenerationTimeout:
    """Tests for chart generation timeout behavior."""
    
    def test_timeout_raises_408_error(self):
        """TC-16: Chart generation timeout raises HTTPException 408."""
        from fastapi import HTTPException
        import time
        
        def slow_get_dataframe(file_id):
            """Simulate a very slow dataframe retrieval."""
            time.sleep(35)  # Longer than 30 second timeout
            return pd.DataFrame({'x': [1], 'y': [2]})
        
        with patch('app.services.chart_service.get_dataframe', side_effect=slow_get_dataframe):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="x",
                y_column="y"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                generate_chart(request)
            
            assert exc_info.value.status_code == 408
            assert "timed out" in exc_info.value.detail.lower()
            assert "30 seconds" in exc_info.value.detail
    
    def test_fast_chart_generation_succeeds(self):
        """Chart generation within timeout succeeds normally."""
        df = pd.DataFrame({
            'category': ['A', 'B', 'C'],
            'value': [10, 20, 30]
        })
        
        with patch('app.services.chart_service.get_dataframe', return_value=df):
            request = ChartGenerationRequest(
                file_id="test-id",
                chart_type=ChartType.BAR,
                x_column="category",
                y_column="value"
            )
            
            # Should complete without timeout
            response = generate_chart(request)
            
            assert response.message == "Chart generated successfully"
            assert "data" in response.chart_json
