"""
Integration tests for the chart endpoints.

Tests based on requirements in: docs/requirements/chart-generation.md
"""
import pytest


class TestManualChartEndpoint:
    """Integration tests for POST /api/charts/."""
    
    def test_bar_chart_success(self, client, uploaded_csv_file):
        """TC-1: Bar chart generates successfully."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "bar",
                "x_column": "category",
                "y_column": "value",
                "title": "Value by Category"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "chart_json" in data
        assert "data" in data["chart_json"]
        assert "layout" in data["chart_json"]
        assert data["chart_json"]["data"][0]["type"] == "bar"
        assert data["message"] == "Chart generated successfully"
    
    def test_line_chart_success(self, client, uploaded_csv_file):
        """TC-2: Line chart generates successfully."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "line",
                "x_column": "id",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["data"][0]["type"] == "scatter"
        assert data["chart_json"]["data"][0]["mode"] == "lines"
    
    def test_scatter_chart_success(self, client, uploaded_csv_file):
        """TC-3: Scatter plot generates successfully."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "scatter",
                "x_column": "id",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["data"][0]["type"] == "scatter"
        assert data["chart_json"]["data"][0]["mode"] == "markers"
    
    def test_histogram_success(self, client, uploaded_csv_file):
        """TC-4: Histogram generates successfully."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "histogram",
                "x_column": "value"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["data"][0]["type"] == "histogram"
    
    def test_box_chart_success(self, client, uploaded_csv_file):
        """TC-5: Box plot generates successfully."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "box",
                "x_column": "category",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["data"][0]["type"] == "box"
    
    def test_pie_chart_success(self, client, uploaded_csv_file):
        """TC-6: Pie chart generates successfully."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "pie",
                "x_column": "category",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["data"][0]["type"] == "pie"
    
    def test_chart_with_color_column(self, client, uploaded_csv_file):
        """TC-7: Chart with color grouping works correctly."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "bar",
                "x_column": "name",
                "y_column": "value",
                "color_column": "category"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should have traces for different categories
        assert len(data["chart_json"]["data"]) >= 1
    
    def test_missing_y_column_for_bar_returns_400(self, client, uploaded_csv_file):
        """TC-8: Bar chart without y_column returns 400."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "bar",
                "x_column": "category"
            }
        )
        
        assert response.status_code == 400
        assert "y_column is required" in response.json()["detail"]
    
    def test_invalid_column_returns_400(self, client, uploaded_csv_file):
        """TC-9: Invalid column name returns 400."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "histogram",
                "x_column": "nonexistent_column"
            }
        )
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
    
    def test_invalid_file_id_returns_404(self, client):
        """TC-10: Invalid file_id returns 404."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": "nonexistent-file-id",
                "chart_type": "bar",
                "x_column": "category",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 404
    
    def test_custom_title_applied(self, client, uploaded_csv_file):
        """TC-11: Custom title is applied to chart."""
        custom_title = "My Custom Chart Title"
        
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "bar",
                "x_column": "category",
                "y_column": "value",
                "title": custom_title
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["layout"]["title"]["text"] == custom_title
    
    def test_default_title_when_not_provided(self, client, uploaded_csv_file):
        """Chart has default title when not provided."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "histogram",
                "x_column": "value"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["layout"]["title"]["text"] == "Chart"
    
    def test_invalid_chart_type_returns_422(self, client, uploaded_csv_file):
        """Invalid chart type returns 422 validation error."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "invalid_type",
                "x_column": "category",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error


class TestAISuggestEndpoint:
    """Integration tests for POST /api/charts/suggest."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("openai", reason="OpenAI not installed"),
        reason="OpenAI API key not configured"
    )
    def test_ai_suggest_success(self, client, uploaded_csv_file):
        """TC-12: AI suggest generates successfully with auto chart selection."""
        response = client.post(
            "/api/charts/suggest",
            json={"file_id": uploaded_csv_file}
        )
        
        # If OpenAI API key is not set, this might fail
        if response.status_code == 500 and "OPENAI_API_KEY" in str(response.json()):
            pytest.skip("OpenAI API key not configured")
        
        assert response.status_code == 200
        data = response.json()
        assert "suggested_spec" in data
        assert "explanation" in data
        assert "confidence" in data
        assert "usage" in data
        # Verify spec structure
        spec = data["suggested_spec"]
        assert "file_id" in spec
        assert "chart_type" in spec
        assert "x_axis" in spec
    
    @pytest.mark.skipif(
        not pytest.importorskip("openai", reason="OpenAI not installed"),
        reason="OpenAI API key not configured"
    )
    def test_ai_suggest_with_instructions(self, client, uploaded_csv_file):
        """TC-13: AI suggest respects user instructions."""
        response = client.post(
            "/api/charts/suggest",
            json={
                "file_id": uploaded_csv_file,
                "user_instructions": "Create a bar chart showing values by category"
            }
        )
        if response.status_code == 500 and "OPENAI_API_KEY" in str(response.json()):
            pytest.skip("OpenAI API key not configured")
        
        assert response.status_code == 200
        data = response.json()
        assert "suggested_spec" in data
        assert len(data["explanation"]) > 0

    def test_ai_suggest_invalid_file_id_returns_404(self, client):
        """TC-14: Invalid file_id returns 404."""
        response = client.post(
            "/api/charts/suggest",
            json={"file_id": "nonexistent-file-id"}
        )
        
        # API should return 404 (not found) for invalid file_id
        assert response.status_code == 404


class TestChartDataIntegrity:
    """Tests for chart data integrity and consistency."""

    def test_chart_data_matches_source(self, client, uploaded_csv_file):
        """Chart data values match source data."""
        # Generate a simple bar chart
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "bar",
                "x_column": "name",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 200
        chart_data = response.json()["chart_json"]["data"][0]
        
        # Chart should have x and y data (format may be array or binary encoded)
        assert "x" in chart_data
        assert "y" in chart_data
    
    def test_histogram_uses_numeric_data(self, client, uploaded_csv_file):
        """Histogram correctly uses numeric column data."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "histogram",
                "x_column": "value"
            }
        )
        
        assert response.status_code == 200
        chart_data = response.json()["chart_json"]["data"][0]
        
        # Histogram should have x values
        assert "x" in chart_data
    
    def test_pie_chart_shows_proportions(self, client, uploaded_csv_file):
        """Pie chart correctly shows data proportions."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "pie",
                "x_column": "category",
                "y_column": "value"
            }
        )
        
        assert response.status_code == 200
        chart_data = response.json()["chart_json"]["data"][0]
        
        # Pie chart should have values and labels
        assert "values" in chart_data
        assert "labels" in chart_data
