"""
Automatic header detection for spreadsheet files.

This module provides intelligent detection of header rows in DataFrames
using multi-factor heuristic scoring. It handles files with title rows,
metadata, or inconsistent formatting.

Usage:
    from app.utils.header_detection import HeaderDetector
    
    result = HeaderDetector.detect(df)
    if result.confidence >= 0.7:
        df = HeaderDetector.apply_header(df, result.header_row)
"""
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional


@dataclass
class HeaderDetectionResult:
    """Result of header row detection."""
    
    header_row: int
    """0-indexed row number identified as the most likely header."""
    
    confidence: float
    """Confidence score from 0.0 to 1.0. >= 0.7 is considered reliable."""
    
    total_score: float
    """Raw score before normalization to confidence."""
    
    factor_scores: Dict[str, float] = field(default_factory=dict)
    """Breakdown of scores by factor for debugging/transparency."""
    
    all_row_scores: List[Tuple[int, float]] = field(default_factory=list)
    """Scores for all analyzed rows: [(row_idx, score), ...]."""


class HeaderDetector:
    """
    Intelligent header detection for uploaded spreadsheet files.
    
    Uses multi-factor heuristic scoring to identify the most likely
    header row, handling common scenarios like:
    - Title rows above headers
    - Metadata/notes in top rows
    - Multi-row headers (detects last header row)
    - Files with no clear header
    
    Scoring Factors:
        - String Content (weight: 2.0): Headers are typically strings
        - Uniqueness (weight: 2.0): Column names should be unique
        - Non-Empty (weight: 1.5): Headers usually label all columns
        - Data Consistency Below (weight: 3.0): Data below header has consistent types
        - Position (weight: 0.5): Headers are usually near the top
        - Header Keywords (weight: 1.5): Common terms like 'id', 'name', 'date'
        - Length Check (weight: 1.0): Header text is typically 3-40 characters
    """
    
    # Common header keywords (lowercase)
    HEADER_KEYWORDS = {
        'id', 'name', 'date', 'time', 'type', 'category', 'status',
        'total', 'amount', 'price', 'cost', 'quantity', 'qty', 'count',
        'email', 'phone', 'address', 'city', 'state', 'country', 'zip',
        'description', 'desc', 'notes', 'comment', 'comments',
        'first', 'last', 'full', 'user', 'customer', 'client', 'vendor',
        'product', 'item', 'sku', 'code', 'number', 'num', 'no',
        'created', 'updated', 'modified', 'deleted', 'active',
        'start', 'end', 'from', 'to', 'value', 'rate', 'percent',
        'year', 'month', 'day', 'week', 'quarter', 'period',
        'sales', 'revenue', 'profit', 'margin', 'budget', 'actual',
        'region', 'territory', 'department', 'division', 'unit',
        'order', 'invoice', 'transaction', 'payment', 'balance',
        'age', 'gender', 'title', 'role', 'position', 'level',
        'source', 'channel', 'medium', 'campaign', 'ref', 'reference'
    }
    
    # Scoring weights
    WEIGHT_STRING_CONTENT = 2.0
    WEIGHT_UNIQUENESS = 2.0
    WEIGHT_NON_EMPTY = 1.5
    WEIGHT_DATA_CONSISTENCY = 3.0
    WEIGHT_POSITION = 0.5
    WEIGHT_KEYWORDS = 1.5
    WEIGHT_LENGTH = 1.0
    
    # Maximum score for normalization (sum of all weights)
    MAX_SCORE = 11.5
    
    @classmethod
    def detect(
        cls,
        df: pd.DataFrame,
        max_search_rows: int = 10,
        min_data_rows_below: int = 3
    ) -> HeaderDetectionResult:
        """
        Detect the most likely header row in a DataFrame.
        
        Args:
            df: Input DataFrame (raw, with potential metadata rows)
            max_search_rows: Maximum rows from top to analyze (default: 10)
            min_data_rows_below: Minimum rows needed below for consistency scoring (default: 3)
            
        Returns:
            HeaderDetectionResult with detected row, confidence, and scoring details
            
        Example:
            >>> result = HeaderDetector.detect(df)
            >>> print(f"Header at row {result.header_row} (confidence: {result.confidence:.2f})")
            >>> if result.confidence >= 0.7:
            ...     df = HeaderDetector.apply_header(df, result.header_row)
        """
        if df.empty:
            return HeaderDetectionResult(
                header_row=0,
                confidence=0.0,
                total_score=0.0,
                factor_scores={},
                all_row_scores=[]
            )
        
        # Limit search to available rows
        search_limit = min(max_search_rows, len(df))
        
        # Score each candidate row
        all_scores: List[Tuple[int, float, Dict[str, float]]] = []
        
        for row_idx in range(search_limit):
            score, factors = cls._score_row(
                df=df,
                row_idx=row_idx,
                max_search_rows=search_limit,
                min_data_rows_below=min_data_rows_below
            )
            all_scores.append((row_idx, score, factors))
        
        # Find best scoring row
        if not all_scores:
            return HeaderDetectionResult(
                header_row=0,
                confidence=0.0,
                total_score=0.0,
                factor_scores={},
                all_row_scores=[]
            )
        
        best_row, best_score, best_factors = max(all_scores, key=lambda x: x[1])
        
        # Normalize score to confidence (0.0 - 1.0)
        confidence = min(best_score / cls.MAX_SCORE, 1.0)
        
        # Prepare simplified row scores for result
        row_scores = [(row_idx, score) for row_idx, score, _ in all_scores]
        
        return HeaderDetectionResult(
            header_row=best_row,
            confidence=round(confidence, 3),
            total_score=round(best_score, 3),
            factor_scores={k: round(v, 3) for k, v in best_factors.items()},
            all_row_scores=row_scores
        )
    
    @classmethod
    def _score_row(
        cls,
        df: pd.DataFrame,
        row_idx: int,
        max_search_rows: int,
        min_data_rows_below: int
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate header likelihood score for a single row.
        
        Returns:
            Tuple of (total_score, factor_breakdown_dict)
        """
        row = df.iloc[row_idx]
        factors: Dict[str, float] = {}
        
        # Factor 1: String Content
        # Headers are typically strings, not numbers
        string_count = sum(1 for val in row if isinstance(val, str) and str(val).strip())
        string_ratio = string_count / len(row) if len(row) > 0 else 0
        factors['string_content'] = string_ratio * cls.WEIGHT_STRING_CONTENT
        
        # Factor 2: Uniqueness
        # Column names should be unique
        non_null_values = [v for v in row if pd.notna(v)]
        unique_count = len(set(str(v).strip().lower() for v in non_null_values))
        unique_ratio = unique_count / len(row) if len(row) > 0 else 0
        factors['uniqueness'] = unique_ratio * cls.WEIGHT_UNIQUENESS
        
        # Factor 3: Non-Empty Cells
        # Headers usually label all columns
        non_empty_count = sum(
            1 for val in row 
            if pd.notna(val) and str(val).strip() != ''
        )
        non_empty_ratio = non_empty_count / len(row) if len(row) > 0 else 0
        factors['non_empty'] = non_empty_ratio * cls.WEIGHT_NON_EMPTY
        
        # Factor 4: Data Consistency Below
        # Data below the header should have consistent types per column
        if row_idx < len(df) - min_data_rows_below:
            consistency_score = cls._check_data_consistency(
                df, row_idx, min_data_rows_below
            )
            factors['data_consistency'] = consistency_score * cls.WEIGHT_DATA_CONSISTENCY
        else:
            # Not enough rows below, give partial score based on position
            factors['data_consistency'] = 0.3 * cls.WEIGHT_DATA_CONSISTENCY
        
        # Factor 5: Position
        # Earlier rows are more likely to be headers (slight bonus)
        position_score = (max_search_rows - row_idx) / max_search_rows
        factors['position'] = position_score * cls.WEIGHT_POSITION
        
        # Factor 6: Header Keywords
        # Check for common header terminology
        keyword_matches = 0
        for val in row:
            if isinstance(val, str):
                val_lower = val.lower().strip()
                # Check if value contains any header keyword
                for keyword in cls.HEADER_KEYWORDS:
                    if keyword in val_lower:
                        keyword_matches += 1
                        break  # One match per cell is enough
        
        keyword_ratio = keyword_matches / len(row) if len(row) > 0 else 0
        factors['keywords'] = keyword_ratio * cls.WEIGHT_KEYWORDS
        
        # Factor 7: Length Check
        # Headers typically have short-to-medium length text (3-40 chars)
        lengths = [len(str(val).strip()) for val in row if pd.notna(val)]
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            # Sweet spot: 3-40 characters
            if 3 <= avg_length <= 40:
                length_score = 1.0
            elif avg_length < 3:
                length_score = avg_length / 3  # Ramp up to 3
            else:
                # Ramp down from 40 to 100
                length_score = max(0, 1 - (avg_length - 40) / 60)
            factors['length'] = length_score * cls.WEIGHT_LENGTH
        else:
            factors['length'] = 0.0
        
        total_score = sum(factors.values())
        return total_score, factors
    
    @classmethod
    def _check_data_consistency(
        cls,
        df: pd.DataFrame,
        header_row_idx: int,
        min_rows: int
    ) -> float:
        """
        Check if rows below the candidate header have consistent data types.
        
        A high consistency score suggests the candidate row is indeed a header,
        as data rows typically have consistent types per column.
        
        Returns:
            Score from 0.0 to 1.0 indicating type consistency below.
        """
        # Get rows below the candidate header
        start_idx = header_row_idx + 1
        end_idx = min(start_idx + min_rows + 2, len(df))  # Check a few extra rows
        
        if end_idx - start_idx < min_rows:
            return 0.5  # Not enough rows to determine
        
        below_rows = df.iloc[start_idx:end_idx]
        
        if below_rows.empty:
            return 0.5
        
        consistent_columns = 0
        
        for col_idx in range(len(df.columns)):
            col_values = below_rows.iloc[:, col_idx].dropna()
            
            if len(col_values) == 0:
                consistent_columns += 0.5  # Empty column, partial credit
                continue
            
            # Determine types of values
            types = []
            for val in col_values:
                if isinstance(val, bool):
                    types.append('bool')
                elif isinstance(val, (int, float)):
                    types.append('numeric')
                elif isinstance(val, str):
                    # Try to detect if string is actually a number or date
                    val_stripped = val.strip()
                    try:
                        float(val_stripped.replace(',', ''))
                        types.append('numeric')
                    except ValueError:
                        types.append('string')
                else:
                    types.append('other')
            
            # Calculate consistency: ratio of most common type
            if types:
                most_common_count = max(types.count(t) for t in set(types))
                consistency_ratio = most_common_count / len(types)
                
                if consistency_ratio >= 0.7:  # 70%+ same type
                    consistent_columns += 1
                elif consistency_ratio >= 0.5:
                    consistent_columns += 0.5
        
        return consistent_columns / len(df.columns) if len(df.columns) > 0 else 0
    
    @classmethod
    def apply_header(
        cls,
        df: pd.DataFrame,
        header_row: int,
        drop_above: bool = True
    ) -> pd.DataFrame:
        """
        Apply detected header row to DataFrame.
        
        This method:
        1. Sets the specified row as the column headers
        2. Optionally drops rows above the header (title rows, metadata)
        3. Drops the header row itself from data
        4. Cleans up column names (strips whitespace)
        5. Resets the index
        
        Args:
            df: Input DataFrame
            header_row: 0-indexed row to use as header
            drop_above: Whether to drop rows above header (default: True)
            
        Returns:
            New DataFrame with header applied
            
        Example:
            >>> result = HeaderDetector.detect(df)
            >>> clean_df = HeaderDetector.apply_header(df, result.header_row)
        """
        if header_row < 0 or header_row >= len(df):
            raise ValueError(f"header_row {header_row} is out of bounds for DataFrame with {len(df)} rows")
        
        # Create a copy to avoid modifying the original
        df = df.copy()
        
        # Extract new column names from the header row
        new_columns = []
        for idx, val in enumerate(df.iloc[header_row]):
            if pd.isna(val) or str(val).strip() == '':
                # Generate a placeholder for empty headers
                new_columns.append(f"Column_{idx + 1}")
            else:
                col_name = str(val).strip()
                new_columns.append(col_name)
        
        # Handle duplicate column names
        seen = {}
        final_columns = []
        for col in new_columns:
            if col in seen:
                seen[col] += 1
                final_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                final_columns.append(col)
        
        # Apply new column names
        df.columns = final_columns
        
        # Drop rows at and above the header
        if drop_above:
            df = df.iloc[header_row + 1:]
        else:
            df = df.iloc[header_row + 1:]
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df
    
    @classmethod
    def detect_and_apply(
        cls,
        df: pd.DataFrame,
        confidence_threshold: float = 0.7,
        max_search_rows: int = 10
    ) -> Tuple[pd.DataFrame, HeaderDetectionResult]:
        """
        Convenience method to detect and optionally apply header in one call.
        
        Args:
            df: Input DataFrame
            confidence_threshold: Minimum confidence to auto-apply (default: 0.7)
            max_search_rows: Maximum rows to search for header
            
        Returns:
            Tuple of (processed_dataframe, detection_result)
            
        Example:
            >>> clean_df, result = HeaderDetector.detect_and_apply(df)
            >>> print(f"Applied header from row {result.header_row}" 
            ...       if result.confidence >= 0.7 else "Used default header")
        """
        result = cls.detect(df, max_search_rows=max_search_rows)
        
        if result.confidence >= confidence_threshold and result.header_row > 0:
            # Apply detected header
            processed_df = cls.apply_header(df, result.header_row)
        else:
            # Keep original (row 0 is already header or low confidence)
            processed_df = df.copy()
        
        return processed_df, result
