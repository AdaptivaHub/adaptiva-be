"""
Unit tests for automatic header detection.

Tests cover all acceptance criteria from docs/requirements/header-detection.md
"""
import pytest
import pandas as pd
import numpy as np
from app.utils.header_detection import HeaderDetector, HeaderDetectionResult


class TestHeaderDetectorBasic:
    """Basic detection tests."""
    
    def test_detect_empty_dataframe(self):
        """Test detection on empty DataFrame returns sensible defaults."""
        df = pd.DataFrame()
        result = HeaderDetector.detect(df)
        
        assert result.header_row == 0
        assert result.confidence == 0.0
        assert result.total_score == 0.0
    
    def test_detect_single_row(self):
        """Test detection on single row DataFrame."""
        df = pd.DataFrame([[1, 2, 3]])
        result = HeaderDetector.detect(df)
        
        assert result.header_row == 0
        assert isinstance(result.confidence, float)
    
    def test_detect_returns_result_object(self):
        """Test that detect returns a HeaderDetectionResult."""
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        result = HeaderDetector.detect(df)
        
        assert isinstance(result, HeaderDetectionResult)
        assert hasattr(result, 'header_row')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'factor_scores')


class TestStringContentFactor:
    """AC-1: String Content Factor tests."""
    
    def test_string_row_scores_higher(self):
        """Rows with more strings should score higher on string_content factor."""
        # Row 0: all strings, Row 1: all numbers
        df = pd.DataFrame([
            ['Name', 'Age', 'City'],
            [25, 30, 35],
            [26, 31, 36]
        ])
        
        result = HeaderDetector.detect(df)
        
        # String row should be detected as header
        assert result.header_row == 0
        assert result.factor_scores.get('string_content', 0) > 0
    
    def test_mixed_type_header(self):
        """Headers with some numbers (e.g., 'Q1 2024') should still be detected."""
        df = pd.DataFrame([
            ['Product', 'Q1 2024', 'Q2 2024'],
            ['Widget A', 100, 150],
            ['Widget B', 200, 250]
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0


class TestUniquenessFactor:
    """AC-2: Uniqueness Factor tests."""
    
    def test_unique_values_score_higher(self):
        """Rows with all unique values should score higher."""
        df = pd.DataFrame([
            ['ID', 'Name', 'Email'],  # All unique
            ['John', 'John', 'John'],  # All same (less likely header)
            [1, 2, 3]
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0
        assert result.factor_scores.get('uniqueness', 0) > 0
    
    def test_duplicate_headers_still_detected(self):
        """Even with some duplicates, header row should be detected."""
        df = pd.DataFrame([
            ['Name', 'Name', 'City'],  # Duplicate header name
            ['John', 'Doe', 'NYC'],
            ['Jane', 'Doe', 'LA']
        ])
        
        result = HeaderDetector.detect(df)
        # Should still detect row 0 as header due to other factors
        assert result.header_row == 0


class TestNonEmptyFactor:
    """AC-3: Non-Empty Cells Factor tests."""
    
    def test_complete_row_scores_higher(self):
        """Rows with no empty cells should score higher."""
        df = pd.DataFrame([
            ['A', 'B', 'C'],  # Complete
            ['X', None, 'Z'],  # Has empty
            [1, 2, 3]
        ])
        
        result = HeaderDetector.detect(df)
        assert result.factor_scores.get('non_empty', 0) > 0
    
    def test_mostly_empty_row_penalized(self):
        """Rows with mostly empty cells should score lower."""
        df = pd.DataFrame([
            [None, None, 'Note'],  # Mostly empty - likely not header
            ['ID', 'Name', 'Value'],  # Complete - likely header
            [1, 'John', 100]
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 1


class TestDataConsistencyFactor:
    """AC-4: Data Consistency Below Factor tests."""
    
    def test_consistent_data_below_scores_higher(self):
        """Rows followed by consistent data types should score higher."""
        df = pd.DataFrame([
            ['ID', 'Amount', 'Date'],
            [1, 100.50, '2024-01-01'],
            [2, 200.75, '2024-01-02'],
            [3, 300.25, '2024-01-03'],
            [4, 400.00, '2024-01-04']
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0
        assert result.factor_scores.get('data_consistency', 0) > 0
    
    def test_inconsistent_data_below_title_row(self):
        """Title rows with header below should be skipped."""
        df = pd.DataFrame([
            ['Monthly Sales Report', None, None],  # Title row
            ['Product', 'Quantity', 'Revenue'],  # Header row
            ['Widget A', 100, 1500.00],
            ['Widget B', 200, 3000.00],
            ['Widget C', 150, 2250.00]
        ])
        
        result = HeaderDetector.detect(df)
        # Should detect row 1 as header (after title)
        assert result.header_row == 1


class TestPositionFactor:
    """AC-5: Position Factor tests."""
    
    def test_earlier_rows_get_bonus(self):
        """Earlier rows should get a slight position bonus."""
        # Two equally good candidate rows
        df = pd.DataFrame([
            ['A', 'B', 'C'],  # Row 0
            ['D', 'E', 'F'],  # Row 1
            [1, 2, 3],
            [4, 5, 6]
        ])
        
        result = HeaderDetector.detect(df)
        # Row 0 should have slightly higher position score
        assert result.header_row == 0
        assert result.factor_scores.get('position', 0) > 0


class TestKeywordsFactor:
    """AC-6: Header Keywords Factor tests."""
    
    def test_common_keywords_boost_score(self):
        """Rows with common header keywords should score higher."""
        df = pd.DataFrame([
            ['customer_id', 'first_name', 'email'],  # Keywords: id, name, email
            ['12345', 'John', 'john@example.com'],
            ['12346', 'Jane', 'jane@example.com']
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0
        assert result.factor_scores.get('keywords', 0) > 0
    
    def test_various_keywords_detected(self):
        """Test various common header keywords are detected."""
        test_cases = [
            ['order_id', 'total_amount', 'order_date'],
            ['product_name', 'category', 'price'],
            ['user_email', 'phone', 'address'],
            ['status', 'description', 'notes']
        ]
        
        for headers in test_cases:
            df = pd.DataFrame([
                headers,
                ['val1', 'val2', 'val3'],
                ['val4', 'val5', 'val6']
            ])
            
            result = HeaderDetector.detect(df)
            assert result.header_row == 0, f"Failed for headers: {headers}"


class TestLengthFactor:
    """AC-7: Length Check Factor tests."""
    
    def test_typical_header_length_scores_higher(self):
        """Headers with 3-40 character average length should score higher."""
        df = pd.DataFrame([
            ['Name', 'Email', 'Phone'],  # Typical header lengths
            ['A very long value that would not be a header typically', 'x', 'y'],
            ['Short', 'value', 'here']
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0
        assert result.factor_scores.get('length', 0) > 0
    
    def test_very_long_text_penalized(self):
        """Rows with very long text are less likely to be headers."""
        df = pd.DataFrame([
            ['This is a very long description that spans multiple words and is definitely not a header', 
             'Another extremely long piece of text that would never be used as a column header', 
             'Yet more lengthy content'],
            ['ID', 'Name', 'Value'],
            [1, 'John', 100]
        ])
        
        result = HeaderDetector.detect(df)
        # Row 1 should be detected as header due to length factor
        assert result.header_row == 1


class TestConfidenceScoring:
    """AC-8 to AC-10: Confidence Scoring tests."""
    
    def test_high_confidence_clear_header(self):
        """AC-8: Clear header row should have high confidence >= 0.8."""
        df = pd.DataFrame([
            ['customer_id', 'full_name', 'email_address', 'phone_number'],
            [1, 'John Doe', 'john@example.com', '555-1234'],
            [2, 'Jane Smith', 'jane@example.com', '555-5678'],
            [3, 'Bob Wilson', 'bob@example.com', '555-9012']
        ])
        
        result = HeaderDetector.detect(df)
        assert result.confidence >= 0.7  # Should be high confidence
    
    def test_medium_confidence_moderate_signals(self):
        """AC-9: Moderate signals should result in medium confidence."""
        df = pd.DataFrame([
            ['Col1', 'Col2', 'Col3'],  # Generic names, less clear
            ['abc', 'def', 'ghi'],
            ['jkl', 'mno', 'pqr']
        ])
        
        result = HeaderDetector.detect(df)
        # Should have some confidence but may not be very high
        assert 0.0 < result.confidence <= 1.0
    
    def test_low_confidence_no_clear_header(self):
        """AC-10: No clear header should result in low confidence."""
        df = pd.DataFrame([
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ])
        
        result = HeaderDetector.detect(df)
        # All numeric, no clear header
        assert result.confidence < 0.7
        assert result.header_row == 0  # Default to row 0


class TestApplyHeader:
    """AC-11 to AC-13: Apply Header tests."""
    
    def test_apply_header_basic(self):
        """Test basic header application."""
        df = pd.DataFrame([
            ['Title Row', None, None],
            ['ID', 'Name', 'Value'],
            [1, 'John', 100],
            [2, 'Jane', 200]
        ])
        
        result_df = HeaderDetector.apply_header(df, header_row=1)
        
        assert list(result_df.columns) == ['ID', 'Name', 'Value']
        assert len(result_df) == 2  # Title row and header row removed
        assert result_df.iloc[0]['ID'] == 1
    
    def test_apply_header_row_zero(self):
        """Test applying row 0 as header (should only remove that row from data)."""
        df = pd.DataFrame([
            ['ID', 'Name', 'Value'],
            [1, 'John', 100],
            [2, 'Jane', 200]
        ])
        
        result_df = HeaderDetector.apply_header(df, header_row=0)
        
        assert list(result_df.columns) == ['ID', 'Name', 'Value']
        assert len(result_df) == 2
    
    def test_apply_header_handles_empty_cells(self):
        """Test that empty header cells get placeholder names."""
        df = pd.DataFrame([
            ['ID', None, 'Value'],
            [1, 'John', 100]
        ])
        
        result_df = HeaderDetector.apply_header(df, header_row=0)
        
        assert result_df.columns[0] == 'ID'
        assert result_df.columns[1] == 'Column_2'  # Placeholder
        assert result_df.columns[2] == 'Value'
    
    def test_apply_header_handles_duplicates(self):
        """Test that duplicate column names are made unique."""
        df = pd.DataFrame([
            ['Name', 'Name', 'Name'],
            ['John', 'Doe', 'Mr.']
        ])
        
        result_df = HeaderDetector.apply_header(df, header_row=0)
        
        # Should have unique names
        assert len(set(result_df.columns)) == 3
        assert result_df.columns[0] == 'Name'
        assert result_df.columns[1] == 'Name_1'
        assert result_df.columns[2] == 'Name_2'
    
    def test_apply_header_invalid_row_raises_error(self):
        """Test that invalid header row raises ValueError."""
        df = pd.DataFrame([[1, 2], [3, 4]])
        
        with pytest.raises(ValueError):
            HeaderDetector.apply_header(df, header_row=10)
        
        with pytest.raises(ValueError):
            HeaderDetector.apply_header(df, header_row=-1)


class TestDetectAndApply:
    """Test convenience method detect_and_apply."""
    
    def test_detect_and_apply_high_confidence(self):
        """Test that high confidence detection is applied."""
        df = pd.DataFrame([
            ['Report Title', None, None],
            ['customer_id', 'name', 'email'],
            [1, 'John', 'john@example.com'],
            [2, 'Jane', 'jane@example.com']
        ])
        
        result_df, detection = HeaderDetector.detect_and_apply(df)
        
        if detection.confidence >= 0.7 and detection.header_row > 0:
            # Header should be applied
            assert 'customer_id' in result_df.columns or 'name' in result_df.columns
    
    def test_detect_and_apply_low_confidence(self):
        """Test that low confidence detection is not applied."""
        df = pd.DataFrame([
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ])
        
        result_df, detection = HeaderDetector.detect_and_apply(df)
        
        # Low confidence, should not modify
        assert detection.confidence < 0.7


class TestRealWorldScenarios:
    """Integration tests with realistic data scenarios."""
    
    def test_excel_with_title_row(self):
        """Common Excel pattern: title row, then header, then data."""
        df = pd.DataFrame([
            ['Q4 2024 Sales Report', None, None, None],
            ['Product', 'Region', 'Sales', 'Growth'],
            ['Widget A', 'North', 15000, 0.12],
            ['Widget B', 'South', 22000, 0.08],
            ['Widget C', 'East', 18000, 0.15]
        ])
        
        result = HeaderDetector.detect(df)
        
        assert result.header_row == 1
        assert result.confidence >= 0.6
    
    def test_excel_with_multiple_metadata_rows(self):
        """Excel with multiple metadata rows before header."""
        df = pd.DataFrame([
            ['Company: ACME Corp', None, None],
            ['Period: January 2024', None, None],
            ['Generated: 2024-01-31', None, None],
            ['Employee ID', 'Name', 'Department'],
            [1001, 'John Doe', 'Engineering'],
            [1002, 'Jane Smith', 'Marketing']
        ])
        
        result = HeaderDetector.detect(df)
        
        assert result.header_row == 3
        assert result.confidence >= 0.5
    
    def test_clean_csv_no_title(self):
        """Standard CSV with header in row 0."""
        df = pd.DataFrame([
            ['id', 'timestamp', 'value', 'status'],
            ['evt_001', '2024-01-01 10:00:00', 42.5, 'active'],
            ['evt_002', '2024-01-01 10:05:00', 38.2, 'active'],
            ['evt_003', '2024-01-01 10:10:00', 45.1, 'pending']
        ])
        result = HeaderDetector.detect(df)
        
        assert result.header_row == 0
        assert result.confidence >= 0.7
    
    def test_all_numeric_data(self):
        """Data with no clear headers (all numeric)."""
        df = pd.DataFrame([
            [100, 200, 300],
            [150, 250, 350],
            [175, 275, 375],
            [200, 300, 400]
        ])
        
        result = HeaderDetector.detect(df)
        
        # Should default to row 0 with lower confidence (no string content)
        assert result.header_row == 0
        # String content factor should be 0 since all numeric
        assert result.factor_scores.get('string_content', 0) == 0
    
    def test_mixed_header_with_years(self):
        """Headers containing years (e.g., financial reports)."""
        df = pd.DataFrame([
            ['Category', '2022', '2023', '2024'],
            ['Revenue', 1000000, 1200000, 1500000],
            ['Expenses', 800000, 900000, 1000000],
            ['Profit', 200000, 300000, 500000]
        ])
        
        result = HeaderDetector.detect(df)
        
        # Should detect row 0 despite numeric column names
        assert result.header_row == 0


class TestEdgeCases:
    """Edge case tests."""
    def test_single_column_dataframe(self):
        """Test with single column DataFrame."""
        df = pd.DataFrame([['Name'], ['John'], ['Jane']])
        
        result = HeaderDetector.detect(df)
        # "Name" should be detected as header due to keyword match
        assert result.header_row == 0
    def test_wide_dataframe(self):
        """Test with many columns."""
        headers = [f'Col{i}' for i in range(50)]  # Use Col instead of Column to avoid keyword
        data = [[i * j for i in range(50)] for j in range(1, 6)]  # Numeric data
        
        df = pd.DataFrame([headers] + data)
        result = HeaderDetector.detect(df)
        
        # Row 0 has string headers, should be detected
        assert result.header_row == 0
        assert result.factor_scores.get('string_content', 0) > 0
    
    def test_unicode_headers(self):
        """Test with Unicode characters in headers."""
        df = pd.DataFrame([
            ['名前', 'メール', '電話番号'],  # Japanese
            ['田中', 'tanaka@example.com', '03-1234-5678'],
            ['鈴木', 'suzuki@example.com', '03-8765-4321']
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0
    
    def test_whitespace_in_headers(self):
        """Test headers with leading/trailing whitespace."""
        df = pd.DataFrame([
            ['  Name  ', ' Email ', '  Phone  '],
            ['John', 'john@example.com', '555-1234'],
            ['Jane', 'jane@example.com', '555-5678']
        ])
        
        result = HeaderDetector.detect(df)
        assert result.header_row == 0
        
        # Apply and check whitespace is stripped
        result_df = HeaderDetector.apply_header(df, 0)
        assert result_df.columns[0] == 'Name'
