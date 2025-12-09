"""
Integration tests for the upload endpoint.

Tests based on requirements in: docs/requirements/file-upload.md
"""
import pytest


class TestUploadEndpoint:
    """Integration tests for POST /api/upload/."""
    
    def test_upload_csv_success(self, client, sample_csv_content):
        """TC-1: Valid CSV upload returns 200 with metadata."""
        response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", sample_csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "file_id" in data
        assert len(data["file_id"]) == 36  # UUID format
        assert data["filename"] == "test.csv"
        assert data["rows"] == 3
        assert data["columns"] == 4
        assert data["column_names"] == ["id", "name", "value", "category"]
        assert data["message"] == "File uploaded successfully"
    
    def test_upload_xlsx_success(self, client, sample_excel_file):
        """TC-2: Valid XLSX upload returns 200 with metadata."""
        response = client.post(
            "/api/upload/",
            files={"file": ("test.xlsx", sample_excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "file_id" in data
        assert data["filename"] == "test.xlsx"
        assert data["rows"] == 2
        assert data["columns"] == 4
        assert "ID" in data["column_names"]
    
    def test_upload_empty_csv_returns_400(self, client, sample_csv_with_headers_only):
        """TC-3: Empty CSV returns 400 error."""
        response = client.post(
            "/api/upload/",
            files={"file": ("empty.csv", sample_csv_with_headers_only, "text/csv")}
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    def test_upload_empty_xlsx_returns_400(self, client, empty_excel_file):
        """TC-4: Empty Excel file returns 400 error."""
        response = client.post(
            "/api/upload/",
            files={"file": ("empty.xlsx", empty_excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    def test_upload_unsupported_format_returns_400(self, client):
        """TC-5: Unsupported file format returns 400 error."""
        response = client.post(
            "/api/upload/",
            files={"file": ("test.txt", b"some text content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]
    
    def test_upload_corrupted_file_returns_400(self, client):
        """TC-6: Corrupted file returns 400 error."""
        # Random binary that's not valid CSV or Excel
        corrupted_content = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        
        response = client.post(
            "/api/upload/",
            files={"file": ("corrupted.csv", corrupted_content, "text/csv")}
        )
        
        assert response.status_code == 400
        # Implementation may return "empty" or "error" message for garbage data
        assert "detail" in response.json()
    
    def test_upload_large_file_success(self, client, large_csv_content):
        """TC-7: Large file (1000 rows) uploads successfully."""
        response = client.post(
            "/api/upload/",
            files={"file": ("large.csv", large_csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == 1000
    
    def test_upload_special_characters_in_headers(self, client, csv_with_special_characters):
        """TC-8: Special characters in headers are preserved."""
        response = client.post(
            "/api/upload/",
            files={"file": ("special.csv", csv_with_special_characters, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Name (Full)" in data["column_names"]
        assert "Value ($)" in data["column_names"]
        assert "Percentage %" in data["column_names"]
    
    def test_upload_generates_unique_file_ids(self, client, sample_csv_content):
        """Each upload generates a unique file_id."""
        response1 = client.post(
            "/api/upload/",
            files={"file": ("test1.csv", sample_csv_content, "text/csv")}
        )
        
        response2 = client.post(
            "/api/upload/",
            files={"file": ("test2.csv", sample_csv_content, "text/csv")}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["file_id"] != response2.json()["file_id"]
    
    def test_upload_no_file_returns_422(self, client):
        """Missing file in request returns 422 error."""
        response = client.post("/api/upload/")
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_excel_first_sheet_only(self, client, excel_with_multiple_sheets):
        """Excel with multiple sheets only processes the first sheet."""
        response = client.post(
            "/api/upload/",
            files={"file": ("multi.xlsx", excel_with_multiple_sheets, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        # First sheet has "Region" and "Sales" columns
        assert "Region" in data["column_names"]
        assert "Sales" in data["column_names"]
        # Second sheet columns should NOT be present
        assert "Category" not in data["column_names"]

    def test_upload_multi_sheet_excel_returns_sheet_names(self, client, excel_with_multiple_sheets):
        """TC-11: Multi-sheet Excel returns sheets array with all sheet names."""
        response = client.post(
            "/api/upload/",
            files={"file": ("multi.xlsx", excel_with_multiple_sheets, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include sheets array
        assert "sheets" in data
        assert data["sheets"] == ["Sales", "Costs"]
        
        # Should indicate which sheet was used for metadata
        assert "active_sheet" in data
        assert data["active_sheet"] == "Sales"

    def test_upload_single_sheet_excel_returns_sheet_names(self, client, sample_excel_file):
        """TC-12: Single-sheet Excel returns sheets array with 1 name."""
        response = client.post(
            "/api/upload/",
            files={"file": ("single.xlsx", sample_excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include sheets array with single sheet
        assert "sheets" in data
        assert len(data["sheets"]) == 1
        assert data["active_sheet"] == data["sheets"][0]

    def test_upload_csv_has_null_sheets(self, client, sample_csv_content):
        """CSV files should have null sheets and active_sheet fields."""
        response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", sample_csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # CSV files should have null for sheet-related fields
        assert data.get("sheets") is None
        assert data.get("active_sheet") is None


class TestUploadedDataPersistence:
    """Tests that uploaded data persists for subsequent operations."""
    
    def test_uploaded_file_can_be_previewed(self, client, uploaded_csv_file):
        """Uploaded file can be retrieved via preview endpoint."""
        response = client.post(
            "/api/preview/",
            json={"file_id": uploaded_csv_file}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == uploaded_csv_file
        assert len(data["data"]) == 3  # 3 rows
    
    def test_uploaded_file_can_generate_charts(self, client, uploaded_csv_file):
        """Uploaded file can be used for chart generation."""
        response = client.post(
            "/api/charts/",
            json={
                "file_id": uploaded_csv_file,
                "chart_type": "histogram",
                "x_column": "value"
            }
        )
        
        assert response.status_code == 200
        assert "chart_json" in response.json()
