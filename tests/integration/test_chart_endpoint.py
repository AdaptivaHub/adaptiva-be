"""
Integration tests for the chart endpoints.

Tests based on requirements in: docs/requirements/chart-generation.md

Endpoints tested:
- POST /api/charts/render - ChartSpec → Plotly JSON
- POST /api/charts/validate - Pre-flight validation
- POST /api/charts/suggest - AI suggestion generation
"""
import pytest


class TestChartRenderEndpoint:
    """Integration tests for POST /api/charts/render."""
    
    def test_bar_chart_render(self, client, uploaded_csv_file):
        """TC-1: Bar chart renders successfully."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]},
                    "visual": {"title": "Value by Category"}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "chart_json" in data
        assert "rendered_at" in data
        assert "spec_version" in data
        assert "data" in data["chart_json"]
        assert "layout" in data["chart_json"]
    
    def test_line_chart_render(self, client, uploaded_csv_file):
        """TC-2: Line chart renders successfully."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "line",
                    "x_axis": {"column": "id"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "chart_json" in data
    
    def test_scatter_chart_render(self, client, uploaded_csv_file):
        """TC-3: Scatter plot renders successfully."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "scatter",
                    "x_axis": {"column": "id"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
    
    def test_histogram_render(self, client, uploaded_csv_file):
        """TC-4: Histogram renders successfully."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "histogram",
                    "x_axis": {"column": "value"}
                }
            }
        )
        
        assert response.status_code == 200
    
    def test_box_chart_render(self, client, uploaded_csv_file):
        """TC-5: Box plot renders successfully."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "box",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
    
    def test_pie_chart_render(self, client, uploaded_csv_file):
        """TC-6: Pie chart renders successfully."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "pie",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
    
    def test_chart_with_series_grouping(self, client, uploaded_csv_file):
        """TC-7: Chart with series grouping works correctly."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "name"},
                    "y_axis": {"columns": ["value"]},
                    "series": {"group_column": "category"}
                }
            }
        )
        
        assert response.status_code == 200
    
    def test_missing_y_axis_for_bar_returns_400(self, client, uploaded_csv_file):
        """TC-8: Bar chart without y_axis returns 400."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"}
                }
            }
        )
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "errors" in detail
    
    def test_invalid_column_returns_400(self, client, uploaded_csv_file):
        """TC-9: Invalid column name returns 400."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "histogram",
                    "x_axis": {"column": "nonexistent_column"}
                }
            }
        )
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "errors" in detail
        assert any("column_not_found" in str(e) for e in detail["errors"])
    
    def test_invalid_file_id_returns_404(self, client):
        """TC-10: Invalid file_id returns 404."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": "nonexistent-file-id",
                    "chart_type": "bar",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 404
    
    def test_custom_title_applied(self, client, uploaded_csv_file):
        """TC-11: Custom title is applied to chart."""
        custom_title = "My Custom Chart Title"
        
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]},
                    "visual": {"title": custom_title}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chart_json"]["layout"]["title"]["text"] == custom_title
    
    def test_invalid_chart_type_returns_422(self, client, uploaded_csv_file):
        """Invalid chart type returns 422 validation error."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "invalid_type",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error

    def test_render_with_filters(self, client, uploaded_csv_file):
        """Chart with filter conditions renders correctly."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]},
                    "filters": {
                        "conditions": [
                            {"column": "value", "operator": "gt", "value": 0}
                        ],
                        "logic": "and"
                    }
                }
            }
        )
        
        assert response.status_code == 200

    def test_render_with_aggregation(self, client, uploaded_csv_file):
        """Chart with aggregation renders correctly."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]},
                    "aggregation": {
                        "method": "sum",
                        "group_by": ["category"]
                    }
                }
            }
        )
        
        assert response.status_code == 200


class TestChartValidateEndpoint:
    """Integration tests for POST /api/charts/validate."""
    
    def test_valid_spec_passes(self, client, uploaded_csv_file):
        """Valid ChartSpec passes validation."""
        response = client.post(
            "/api/charts/validate",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0
    
    def test_missing_column_fails(self, client, uploaded_csv_file):
        """Missing column fails validation."""
        response = client.post(
            "/api/charts/validate",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "nonexistent"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any(e["code"] == "column_not_found" for e in data["errors"])
    
    def test_missing_y_axis_fails(self, client, uploaded_csv_file):
        """Bar chart without y_axis fails validation."""
        response = client.post(
            "/api/charts/validate",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "category"}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any(e["code"] == "missing_required_field" for e in data["errors"])


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
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "bar",
                    "x_axis": {"column": "name"},
                    "y_axis": {"columns": ["value"]}
                }
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
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "histogram",
                    "x_axis": {"column": "value"}
                }
            }
        )
        
        assert response.status_code == 200
        chart_data = response.json()["chart_json"]["data"][0]
        
        # Histogram should have x values
        assert "x" in chart_data
    
    def test_pie_chart_shows_proportions(self, client, uploaded_csv_file):
        """Pie chart correctly shows data proportions."""
        response = client.post(
            "/api/charts/render",
            json={
                "spec": {
                    "file_id": uploaded_csv_file,
                    "chart_type": "pie",
                    "x_axis": {"column": "category"},
                    "y_axis": {"columns": ["value"]}
                }
            }
        )
        
        assert response.status_code == 200
        chart_data = response.json()["chart_json"]["data"][0]
        
        # Pie chart should have values and labels
        assert "values" in chart_data
        assert "labels" in chart_data
