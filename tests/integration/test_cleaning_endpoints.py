"""
Integration tests for the cleaning endpoints.

Tests based on requirements in: docs/requirements/data-cleaning.md
"""
import pytest


class TestCleaningEndpoint:
    """Integration tests for POST /api/cleaning/."""
    
    def test_basic_cleaning_success(self, client, sample_csv_content):
        """TC-1: Basic cleaning with drop_duplicates."""
        # First upload a file
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", sample_csv_content, "text/csv")}
        )
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # Now clean the data
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "drop_duplicates": True,
                "drop_na": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == file_id
        assert "rows_before" in data
        assert "rows_after" in data
        assert "message" in data
    
    def test_cleaning_file_not_found(self, client):
        """TC-2: Cleaning with invalid file_id returns 404."""
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": "invalid-file-id",
                "drop_duplicates": True
            }
        )
        
        assert response.status_code == 404
    
    def test_cleaning_drop_columns(self, client, sample_csv_content):
        """TC-3: Drop specific columns."""
        # First upload a file
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", sample_csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        # Drop a column
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "drop_duplicates": False,
                "columns_to_drop": ["category"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["columns_before"] == 4
        assert data["columns_after"] == 3


class TestEnhancedCleaningEndpoint:
    """Integration tests for enhanced cleaning features on POST /api/cleaning/."""
    
    def test_enhanced_cleaning_normalize_columns(self, client):
        """TC-1: Normalize column names."""
        # Upload CSV with messy column names
        csv_content = b"First Name,LAST NAME, Age ,Created Date\nJohn,Doe,30,2023-01-01\nJane,Smith,25,2023-02-15"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # Clean with column normalization (using unified endpoint)
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": True,
                "remove_empty_rows": False,
                "remove_empty_columns": False,
                "drop_duplicates": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "operations_log" in data
        assert len(data["operations_log"]) > 0
        
        # Check that columns were renamed
        normalize_op = next((op for op in data["operations_log"] if op["operation"] == "normalize_columns"), None)
        assert normalize_op is not None
        assert normalize_op["affected_count"] >= 3
        
        # Check column changes
        assert "column_changes" in data
        assert len(data["column_changes"]["renamed"]) >= 3
    
    def test_enhanced_cleaning_remove_empty_rows(self, client):
        """TC-2: Remove completely empty rows."""
        # Upload CSV with empty rows
        csv_content = b"name,value\nJohn,100\n,,\nJane,200\n,,"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": False,
                "remove_empty_rows": True,
                "remove_empty_columns": False,
                "drop_duplicates": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have removed 2 empty rows
        assert data["rows_before"] == 4
        assert data["rows_after"] == 2
    
    def test_enhanced_cleaning_remove_empty_columns(self, client):
        """TC-3: Remove completely empty columns."""
        # Upload CSV with empty column
        csv_content = b"name,empty_col,value\nJohn,,100\nJane,,200"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": False,
                "remove_empty_rows": False,
                "remove_empty_columns": True,
                "drop_duplicates": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["columns_before"] == 3
        assert data["columns_after"] == 2
        assert "empty_col" in data["column_changes"]["dropped"]
    
    def test_enhanced_cleaning_smart_fill_missing(self, client):
        """TC-4/5: Smart fill missing values with median/mode."""
        # Upload CSV with missing values
        csv_content = b"category,amount\nA,100\nA,200\n,\nB,400"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": False,
                "remove_empty_rows": False,
                "remove_empty_columns": False,
                "drop_duplicates": False,
                "smart_fill_missing": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that values were filled
        fill_op = next((op for op in data["operations_log"] if op["operation"] == "smart_fill_missing"), None)
        assert fill_op is not None
        assert fill_op["affected_count"] >= 1
        
        # Check missing values summary
        assert "missing_values_summary" in data
        assert len(data["missing_values_summary"]["before"]) > 0
    
    def test_enhanced_cleaning_auto_detect_types(self, client):
        """TC-6: Auto-detect and convert date columns."""
        # Upload CSV with date strings
        csv_content = b"name,created_date,amount\nJohn,2023-01-15,100\nJane,2023-02-20,200"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": False,
                "remove_empty_rows": False,
                "remove_empty_columns": False,
                "drop_duplicates": False,
                "auto_detect_types": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that types were converted
        type_op = next((op for op in data["operations_log"] if op["operation"] == "auto_detect_types"), None)
        assert type_op is not None
        assert "created_date" in data["column_changes"]["type_converted"]
    
    def test_enhanced_cleaning_drop_duplicates(self, client):
        """TC-7: Remove duplicate rows."""
        # Upload CSV with duplicates
        csv_content = b"name,value\nJohn,100\nJane,200\nJohn,100\nBob,300"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": False,
                "remove_empty_rows": False,
                "remove_empty_columns": False,
                "drop_duplicates": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["rows_before"] == 4
        assert data["rows_after"] == 3
        
        dup_op = next((op for op in data["operations_log"] if op["operation"] == "drop_duplicates"), None)
        assert dup_op is not None
        assert dup_op["affected_count"] == 1
    
    def test_enhanced_cleaning_combined_operations(self, client):
        """TC-8: All operations combined."""
        # Upload messy CSV
        csv_content = b"First Name,LAST NAME,Empty Col,Amount\nJohn,Doe,,100\nJohn,Doe,,100\nJane,Smith,,\n,,,"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": True,
                "remove_empty_rows": True,
                "remove_empty_columns": True,
                "drop_duplicates": True,
                "smart_fill_missing": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Multiple operations should be logged
        assert len(data["operations_log"]) >= 3
        assert data["message"] != ""
    
    def test_enhanced_cleaning_file_not_found(self, client):
        """TC-9: Cleaning with invalid file_id returns 404."""
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": "non-existent-file-id",
                "normalize_columns": True
            }
        )
        
        assert response.status_code == 404
    
    def test_enhanced_cleaning_no_operations_needed(self, client):
        """TC-10: Clean data requires no operations."""
        # Upload already clean CSV
        csv_content = b"name,value\nJohn,100\nJane,200"
        
        upload_response = client.post(
            "/api/upload/",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        file_id = upload_response.json()["file_id"]
        
        response = client.post(
            "/api/cleaning/",
            json={
                "file_id": file_id,
                "normalize_columns": False,
                "remove_empty_rows": True,
                "remove_empty_columns": True,
                "drop_duplicates": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # No operations should be logged since data is clean
        assert len(data["operations_log"]) == 0
        assert "No cleaning operations were necessary" in data["message"]
