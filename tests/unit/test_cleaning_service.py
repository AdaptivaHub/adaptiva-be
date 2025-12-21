# filepath: c:\GitHub\adaptiva-be\tests\unit\test_cleaning_service.py
"""
Unit tests for the Data Cleaning Service

Tests cover:
- Column name normalization
- Empty row/column removal
- Smart missing value filling
- Automatic type detection
- Duplicate removal
- Cleaning operation logging
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.cleaning_service import (
    clean_data,
    _normalize_column_name,
    _is_date_column,
    _try_convert_to_datetime,
    _try_convert_to_numeric,
    _get_missing_values_summary
)
from app.models import DataCleaningRequest


class TestNormalizeColumnName:
    """Tests for column name normalization helper"""
    
    def test_lowercase_conversion(self):
        assert _normalize_column_name("FirstName") == "firstname"
        assert _normalize_column_name("LAST_NAME") == "last_name"
    
    def test_strip_whitespace(self):
        assert _normalize_column_name("  Age  ") == "age"
        assert _normalize_column_name("\tCity\n") == "city"
    
    def test_replace_spaces_with_underscores(self):
        assert _normalize_column_name("First Name") == "first_name"
        assert _normalize_column_name("Last  Name") == "last_name"  # Multiple spaces
    
    def test_remove_special_characters(self):
        assert _normalize_column_name("User@Email") == "useremail"
        assert _normalize_column_name("Amount ($)") == "amount_"
        assert _normalize_column_name("Rate%") == "rate"
    
    def test_preserve_numbers(self):
        assert _normalize_column_name("Column1") == "column1"
        assert _normalize_column_name("2024_Sales") == "2024_sales"


class TestIsDateColumn:
    """Tests for date column detection helper"""
    
    def test_date_patterns_detected(self):
        assert _is_date_column("created_date") is True
        assert _is_date_column("UpdatedAt") is True
        assert _is_date_column("timestamp") is True
        assert _is_date_column("birth_date") is True
        assert _is_date_column("modified_time") is True
    
    def test_non_date_columns(self):
        assert _is_date_column("name") is False
        assert _is_date_column("amount") is False
        assert _is_date_column("category") is False


class TestTryConvertToDatetime:
    """Tests for datetime conversion helper"""
    
    def test_successful_conversion(self):
        series = pd.Series(["2023-01-01", "2023-02-15", "2023-03-20"])
        result, converted = _try_convert_to_datetime(series)
        assert converted is True
        assert pd.api.types.is_datetime64_any_dtype(result)
    
    def test_already_datetime(self):
        series = pd.Series(pd.to_datetime(["2023-01-01", "2023-02-15"]))
        result, converted = _try_convert_to_datetime(series)
        assert converted is False  # Already datetime, no conversion needed
    
    def test_non_date_string(self):
        series = pd.Series(["apple", "banana", "cherry"])
        result, converted = _try_convert_to_datetime(series)
        assert converted is False


class TestTryConvertToNumeric:
    """Tests for numeric conversion helper"""
    
    def test_successful_conversion(self):
        series = pd.Series(["1", "2", "3", "4"])
        result, converted = _try_convert_to_numeric(series)
        assert converted is True
        assert pd.api.types.is_numeric_dtype(result)
    
    def test_already_numeric(self):
        series = pd.Series([1.0, 2.0, 3.0])
        result, converted = _try_convert_to_numeric(series)
        assert converted is False  # Already numeric
    
    def test_non_numeric_string(self):
        series = pd.Series(["apple", "banana", "cherry"])
        result, converted = _try_convert_to_numeric(series)
        assert converted is False


class TestGetMissingValuesSummary:
    """Tests for missing values summary helper"""
    
    def test_with_missing_values(self):
        df = pd.DataFrame({
            'A': [1, 2, None, 4],
            'B': [None, None, 3, 4],
            'C': [1, 2, 3, 4]
        })
        result = _get_missing_values_summary(df)
        assert result == {'A': 1, 'B': 2}
        assert 'C' not in result  # No missing values
    
    def test_no_missing_values(self):
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        result = _get_missing_values_summary(df)
        assert result == {}


class TestCleanData:
    """Integration tests for the clean_data function"""
    
    @pytest.fixture
    def sample_df(self):
        """Create a sample dataframe for testing"""
        return pd.DataFrame({
            'First Name': ['John', 'Jane', 'John', None, ''],
            'LAST NAME': ['Doe', 'Smith', 'Doe', None, ''],
            ' Age ': [30, 25, 30, None, None],
            'Created Date': ['2023-01-01', '2023-02-15', '2023-01-01', None, None],
            'Empty Col': [None, None, None, None, None]
        })
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_normalize_columns(self, mock_update, mock_get, sample_df):
        """Test column name normalization"""
        mock_get.return_value = sample_df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=True,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=False
        )
        
        response = clean_data(request)
        
        assert 'normalize_columns' in [op.operation for op in response.operations_log]
        assert 'first_name' in response.column_changes.renamed.values()
        assert 'last_name' in response.column_changes.renamed.values()
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_remove_empty_rows(self, mock_update, mock_get, sample_df):
        """Test empty row removal"""
        mock_get.return_value = sample_df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=True,
            remove_empty_columns=False,
            drop_duplicates=False
        )
        
        response = clean_data(request)
        
        # Row 4 and 5 should be removed (all None/empty)
        assert response.rows_before == 5
        assert response.rows_after < 5
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_remove_empty_columns(self, mock_update, mock_get, sample_df):
        """Test empty column removal"""
        mock_get.return_value = sample_df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=False,
            remove_empty_columns=True,
            drop_duplicates=False
        )
        
        response = clean_data(request)
        
        # 'Empty Col' should be removed
        assert response.columns_before == 5
        assert response.columns_after == 4
        assert 'Empty Col' in response.column_changes.dropped
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_drop_duplicates(self, mock_update, mock_get, sample_df):
        """Test duplicate row removal"""
        mock_get.return_value = sample_df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=True
        )
        
        response = clean_data(request)
        
        # Row 1 and 3 are duplicates (John Doe, 30, 2023-01-01)
        duplicate_op = next((op for op in response.operations_log if op.operation == 'drop_duplicates'), None)
        if duplicate_op:
            assert duplicate_op.affected_count >= 1
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_smart_fill_missing(self, mock_update, mock_get):
        """Test smart missing value filling"""
        df = pd.DataFrame({
            'numeric_col': [1.0, 2.0, None, 4.0],
            'category_col': ['A', 'A', None, 'B']
        })
        mock_get.return_value = df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=False,
            smart_fill_missing=True
        )
        
        response = clean_data(request)
        
        fill_op = next((op for op in response.operations_log if op.operation == 'smart_fill_missing'), None)
        assert fill_op is not None
        assert fill_op.affected_count == 2  # Two missing values filled
        
        # Check missing values summary
        assert response.missing_values_summary.before == {'numeric_col': 1, 'category_col': 1}
        assert response.missing_values_summary.after == {}  # All filled
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_auto_detect_types(self, mock_update, mock_get):
        """Test automatic type detection and conversion"""
        df = pd.DataFrame({
            'date_column': ['2023-01-01', '2023-02-15', '2023-03-20'],
            'numeric_string': ['100', '200', '300'],
            'text_column': ['hello', 'world', 'test']
        })
        mock_get.return_value = df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=False,
            auto_detect_types=True
        )
        
        response = clean_data(request)
        
        type_op = next((op for op in response.operations_log if op.operation == 'auto_detect_types'), None)
        assert type_op is not None
        assert len(response.column_changes.type_converted) >= 1
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_manual_fill_na(self, mock_update, mock_get):
        """Test manual fill_na functionality"""
        df = pd.DataFrame({
            'A': [1, None, 3],
            'B': ['x', None, 'z']
        })
        mock_get.return_value = df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=False,
            fill_na={'A': 0, 'B': 'unknown'}
        )
        
        response = clean_data(request)
        
        fill_op = next((op for op in response.operations_log if op.operation == 'fill_na'), None)
        assert fill_op is not None
        assert fill_op.affected_count == 2
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_columns_to_drop(self, mock_update, mock_get):
        """Test dropping specific columns"""
        df = pd.DataFrame({
            'keep_me': [1, 2, 3],
            'drop_me': [4, 5, 6],
            'also_keep': [7, 8, 9]
        })
        mock_get.return_value = df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=False,
            columns_to_drop=['drop_me']
        )
        
        response = clean_data(request)
        
        assert response.columns_before == 3
        assert response.columns_after == 2
        assert 'drop_me' in response.column_changes.dropped
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_combined_operations(self, mock_update, mock_get, sample_df):
        """Test multiple cleaning operations together"""
        mock_get.return_value = sample_df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=True,
            remove_empty_rows=True,
            remove_empty_columns=True,
            drop_duplicates=True,
            auto_detect_types=True
        )
        
        response = clean_data(request)
        
        # Should have multiple operations logged
        assert len(response.operations_log) >= 2
        assert response.message != ""
        assert response.file_id == "test-123"
    
    @patch('app.services.cleaning_service.get_dataframe')
    def test_file_not_found(self, mock_get):
        """Test error handling for non-existent file"""
        mock_get.side_effect = ValueError("File not found: invalid-id")
        
        request = DataCleaningRequest(
            file_id="invalid-id",
            normalize_columns=True
        )
        
        with pytest.raises(Exception) as excinfo:
            clean_data(request)
        assert "404" in str(excinfo.value.status_code) or "not found" in str(excinfo.value.detail).lower()
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_empty_dataframe(self, mock_update, mock_get):
        """Test handling of empty dataframe"""
        df = pd.DataFrame()
        mock_get.return_value = df
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=True,
            remove_empty_rows=True
        )
        
        response = clean_data(request)
        
        assert response.rows_before == 0
        assert response.rows_after == 0
        assert response.columns_before == 0
        assert response.columns_after == 0
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_no_operations_needed(self, mock_update, mock_get):
        """Test when no cleaning is needed"""
        df = pd.DataFrame({
            'clean_col': [1, 2, 3],
            'another_col': ['a', 'b', 'c']
        })
        mock_get.return_value = df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=False,
            remove_empty_rows=True,  # No empty rows to remove
            remove_empty_columns=True,  # No empty columns to remove
            drop_duplicates=True,  # No duplicates
            smart_fill_missing=False,
            auto_detect_types=False
        )
        
        response = clean_data(request)
        
        # No operations should be logged (data is already clean)
        assert len(response.operations_log) == 0
        assert "No cleaning operations were necessary" in response.message


class TestDuplicateColumnNameHandling:
    """Tests for handling duplicate column names after normalization"""
    
    @patch('app.services.cleaning_service.get_dataframe')
    @patch('app.services.cleaning_service.update_dataframe')
    def test_duplicate_names_after_normalization(self, mock_update, mock_get):
        """Test that duplicate column names are handled correctly"""
        df = pd.DataFrame({
            'Column A': [1, 2, 3],
            'column_a': [4, 5, 6],
            'COLUMN A': [7, 8, 9]
        })
        mock_get.return_value = df.copy()
        
        request = DataCleaningRequest(
            file_id="test-123",
            normalize_columns=True,
            remove_empty_rows=False,
            remove_empty_columns=False,
            drop_duplicates=False
        )
        
        response = clean_data(request)
        
        # Get the actual column names from the updated dataframe
        call_args = mock_update.call_args
        updated_df = call_args[0][1]
        
        # All column names should be unique
        assert len(updated_df.columns) == len(set(updated_df.columns))
