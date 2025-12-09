"""
Integration tests for the preview endpoint.

Tests based on requirements in: docs/requirements/data-preview.md
"""
import pytest


class TestPreviewEndpoint:
    """Integration tests for POST /api/preview/."""

    def test_preview_csv_success(self, client, uploaded_csv_file):
        """TC-2: Happy path - CSV file returns 200 with data."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_csv_file}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_id"] == uploaded_csv_file
        assert "headers" in data
        assert "data" in data
        assert data["formatted"] is False  # CSV has no formatting
        assert data.get("sheet_name") is None
        assert data.get("available_sheets") is None

    def test_preview_excel_success(self, client, uploaded_excel_file):
        """TC-1: Happy path - Excel file returns 200 with formatted data."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_excel_file}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_id"] == uploaded_excel_file
        assert data["formatted"] is True

    def test_preview_custom_row_limit(self, client, uploaded_large_csv):
        """TC-3: Custom row limit returns up to specified rows."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_large_csv, "max_rows": 50}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["preview_rows"] == 50
        assert len(data["data"]) == 50

    def test_preview_max_row_limit(self, client, uploaded_large_csv):
        """TC-4: Maximum row limit (1000) works correctly."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_large_csv, "max_rows": 1000}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["preview_rows"] == 1000

    def test_preview_row_limit_too_low(self, client, uploaded_csv_file):
        """TC-5: Row limit of 0 returns 422 validation error."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_csv_file, "max_rows": 0}
        )

        assert response.status_code == 422

    def test_preview_row_limit_too_high(self, client, uploaded_csv_file):
        """TC-6: Row limit > 1000 returns 422 validation error."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_csv_file, "max_rows": 1001}
        )

        assert response.status_code == 422

    def test_preview_file_not_found(self, client):
        """TC-7: Invalid file_id returns 404 error."""
        response = client.post(
            "/api/preview/",
            json={"file_id": "non-existent-id"}
        )

        assert response.status_code == 404


class TestPreviewMultiSheet:
    """Tests for multi-sheet Excel preview functionality."""

    @pytest.fixture
    def uploaded_multi_sheet_excel(self, client, excel_with_multiple_sheets) -> dict:
        """Upload a multi-sheet Excel file and return the response data."""
        response = client.post(
            "/api/upload/",
            files={"file": ("multi.xlsx", excel_with_multiple_sheets, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        assert response.status_code == 200
        return response.json()

    def test_preview_default_sheet(self, client, uploaded_multi_sheet_excel):
        """TC-17: Preview without sheet_name returns data from first sheet."""
        file_id = uploaded_multi_sheet_excel["file_id"]

        response = client.post(
            "/api/preview/",
            json={"file_id": file_id}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return first sheet data
        assert data["sheet_name"] == "Sales"
        assert "Region" in data["headers"]
        assert "Sales" in data["headers"]
        
        # Should include available sheets
        assert data["available_sheets"] == ["Sales", "Costs"]

    def test_preview_specific_sheet(self, client, uploaded_multi_sheet_excel):
        """TC-16: Preview with sheet_name returns data from specified sheet."""
        file_id = uploaded_multi_sheet_excel["file_id"]

        response = client.post(
            "/api/preview/",
            json={"file_id": file_id, "sheet_name": "Costs"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return Costs sheet data
        assert data["sheet_name"] == "Costs"
        assert "Category" in data["headers"]
        assert "Cost" in data["headers"]
        
        # Should still include all available sheets
        assert data["available_sheets"] == ["Sales", "Costs"]

    def test_preview_invalid_sheet_name(self, client, uploaded_multi_sheet_excel):
        """TC-18: Invalid sheet_name returns 400 error with available sheets."""
        file_id = uploaded_multi_sheet_excel["file_id"]

        response = client.post(
            "/api/preview/",
            json={"file_id": file_id, "sheet_name": "NonExistentSheet"}
        )

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        
        # Error message should indicate sheet not found
        assert "not found" in error_detail.lower() or "NonExistentSheet" in error_detail
        # Should mention available sheets
        assert "Sales" in error_detail or "available" in error_detail.lower()

    def test_preview_csv_ignores_sheet_name(self, client, uploaded_csv_file):
        """TC-19: Sheet selection for CSV - parameter is ignored."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_csv_file, "sheet_name": "SomeSheet"}
        )

        assert response.status_code == 200
        data = response.json()

        # CSV should work normally, ignoring the sheet_name
        assert data["sheet_name"] is None
        assert data["available_sheets"] is None
        assert len(data["data"]) > 0

    def test_preview_available_sheets_in_response(self, client, uploaded_multi_sheet_excel):
        """TC-20: Multi-sheet Excel includes available_sheets in response."""
        file_id = uploaded_multi_sheet_excel["file_id"]

        response = client.post(
            "/api/preview/",
            json={"file_id": file_id}
        )

        assert response.status_code == 200
        data = response.json()

        assert "available_sheets" in data
        assert isinstance(data["available_sheets"], list)
        assert len(data["available_sheets"]) == 2
        assert "Sales" in data["available_sheets"]
        assert "Costs" in data["available_sheets"]
