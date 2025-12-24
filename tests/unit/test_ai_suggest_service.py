"""
Unit tests for AI Suggest Service.

Tests cover:
- Data schema extraction
- LLM prompt building
- ChartSpec parsing from LLM response
- Error handling
- Rate limiting integration
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd
import json

from app.models.chart_spec import ChartSpec, AISuggestRequest, AISuggestResponse
from app.services.ai_suggest_service import (
    extract_data_schema,
    build_llm_prompt,
    parse_llm_response,
    generate_chart_suggestion,
    AISuggestError,
    CHARTSPEC_JSON_SCHEMA,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_df():
    """Sample dataframe for testing."""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=12, freq="M"),
        "category": ["A", "B", "C"] * 4,
        "revenue": [100, 200, 150, 300, 250, 180, 220, 350, 280, 190, 310, 420],
        "quantity": [10, 20, 15, 30, 25, 18, 22, 35, 28, 19, 31, 42],
    })


@pytest.fixture
def complex_df():
    """More complex dataframe with various types."""
    return pd.DataFrame({
        "product_id": range(1, 101),
        "product_name": [f"Product {i}" for i in range(1, 101)],
        "price": [10.99 + i * 0.5 for i in range(100)],
        "category": ["Electronics", "Clothing", "Home", "Sports", "Books"] * 20,
        "stock": [i * 2 for i in range(100)],
        "created_at": pd.date_range("2024-01-01", periods=100),
    })


@pytest.fixture
def valid_llm_response():
    """Valid LLM response with ChartSpec JSON."""
    return {
        "chart_type": "line",
        "x_axis": {"column": "date", "label": "Date"},
        "y_axis": {"columns": ["revenue"], "label": "Revenue ($)"},
        "series": {"group_column": "category"},
        "visual": {"title": "Revenue Trends by Category"},
        "styling": {"color_palette": "colorblind_safe"},
        "explanation": "Line chart shows revenue trends over time, grouped by category.",
        "confidence": 0.85,
        "alternatives": [
            {"chart_type": "area", "reason": "Area chart emphasizes cumulative totals"}
        ]
    }


# =============================================================================
# Extract Data Schema Tests
# =============================================================================

class TestExtractDataSchema:
    """Tests for extracting data schema from dataframes."""

    def test_basic_schema_extraction(self, sample_df):
        """Should extract column names, types, and sample values."""
        schema = extract_data_schema(sample_df)
        
        assert "columns" in schema
        assert len(schema["columns"]) == 4
        assert schema["row_count"] == 12
        
        # Check column details
        date_col = next(c for c in schema["columns"] if c["name"] == "date")
        assert date_col["dtype"] == "datetime64[ns]"
        assert len(date_col["sample_values"]) <= 5
        
        category_col = next(c for c in schema["columns"] if c["name"] == "category")
        assert category_col["dtype"] == "object"
        assert set(category_col["unique_values"]) == {"A", "B", "C"}

    def test_numeric_column_stats(self, sample_df):
        """Should include min/max for numeric columns."""
        schema = extract_data_schema(sample_df)
        
        revenue_col = next(c for c in schema["columns"] if c["name"] == "revenue")
        assert "min" in revenue_col
        assert "max" in revenue_col
        assert revenue_col["min"] == 100
        assert revenue_col["max"] == 420

    def test_large_unique_values_truncated(self, complex_df):
        """Should truncate unique values for high-cardinality columns."""
        schema = extract_data_schema(complex_df)
        
        product_name_col = next(c for c in schema["columns"] if c["name"] == "product_name")
        # Should indicate high cardinality, not list all 100 values
        assert product_name_col["cardinality"] == 100
        assert "unique_values" not in product_name_col or len(product_name_col.get("unique_values", [])) <= 10

    def test_datetime_format_detection(self, sample_df):
        """Should detect datetime columns."""
        schema = extract_data_schema(sample_df)
        
        date_col = next(c for c in schema["columns"] if c["name"] == "date")
        assert date_col["dtype"] == "datetime64[ns]"


# =============================================================================
# Build LLM Prompt Tests
# =============================================================================

class TestBuildLLMPrompt:
    """Tests for building LLM prompts."""

    def test_prompt_includes_schema(self, sample_df):
        """Should include data schema in prompt."""
        schema = extract_data_schema(sample_df)
        prompt = build_llm_prompt(schema, user_instructions=None)
        
        assert "date" in prompt
        assert "category" in prompt
        assert "revenue" in prompt

    def test_prompt_includes_user_instructions(self, sample_df):
        """Should include user instructions when provided."""
        schema = extract_data_schema(sample_df)
        instructions = "Show revenue trends by category over time"
        prompt = build_llm_prompt(schema, user_instructions=instructions)
        
        assert instructions in prompt

    def test_prompt_includes_chartspec_schema(self, sample_df):
        """Should include ChartSpec JSON schema."""
        schema = extract_data_schema(sample_df)
        prompt = build_llm_prompt(schema, user_instructions=None)
        
        # Should mention chart types
        assert "bar" in prompt.lower()
        assert "line" in prompt.lower()
        assert "scatter" in prompt.lower()

    def test_prompt_format_is_json(self, sample_df):
        """Should request JSON output."""
        schema = extract_data_schema(sample_df)
        prompt = build_llm_prompt(schema, user_instructions=None)
        
        assert "JSON" in prompt or "json" in prompt


# =============================================================================
# Parse LLM Response Tests
# =============================================================================

class TestParseLLMResponse:
    """Tests for parsing LLM responses into ChartSpec."""

    def test_parse_valid_response(self, valid_llm_response):
        """Should parse valid LLM response into ChartSpec."""
        file_id = "test-file-123"
        result = parse_llm_response(json.dumps(valid_llm_response), file_id)
        
        assert isinstance(result, dict)
        assert "spec" in result
        assert isinstance(result["spec"], ChartSpec)
        assert result["spec"].file_id == file_id
        assert result["spec"].chart_type == "line"
        assert result["spec"].x_axis.column == "date"
        assert result["spec"].y_axis.columns == ["revenue"]
        assert result["explanation"] == "Line chart shows revenue trends over time, grouped by category."
        assert result["confidence"] == 0.85

    def test_file_id_always_injected(self, valid_llm_response):
        """Should always inject file_id, never trust LLM."""
        # LLM might return a different file_id - should be overwritten
        valid_llm_response["file_id"] = "malicious-file-id"
        file_id = "correct-file-id"
        
        result = parse_llm_response(json.dumps(valid_llm_response), file_id)
        assert result["spec"].file_id == file_id

    def test_parse_invalid_json(self):
        """Should raise error for invalid JSON."""
        with pytest.raises(AISuggestError) as exc_info:
            parse_llm_response("not valid json", "file-123")
        
        assert "parse" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()

    def test_parse_missing_required_fields(self):
        """Should raise error for missing required fields."""
        incomplete = {"chart_type": "bar"}  # Missing x_axis
        
        with pytest.raises(AISuggestError):
            parse_llm_response(json.dumps(incomplete), "file-123")

    def test_parse_invalid_chart_type(self):
        """Should raise error for invalid chart type."""
        invalid = {
            "chart_type": "invalid_type",
            "x_axis": {"column": "date"},
            "y_axis": {"columns": ["revenue"]}
        }
        
        with pytest.raises(AISuggestError):
            parse_llm_response(json.dumps(invalid), "file-123")

    def test_parse_extracts_metadata(self, valid_llm_response):
        """Should extract explanation, confidence, alternatives."""
        result = parse_llm_response(json.dumps(valid_llm_response), "file-123")
        
        assert result["explanation"] == "Line chart shows revenue trends over time, grouped by category."
        assert result["confidence"] == 0.85
        assert len(result["alternatives"]) == 1
        assert result["alternatives"][0]["chart_type"] == "area"

    def test_parse_with_markdown_wrapper(self, valid_llm_response):
        """Should handle JSON wrapped in markdown code blocks."""
        wrapped = f"```json\n{json.dumps(valid_llm_response)}\n```"
        
        result = parse_llm_response(wrapped, "file-123")
        assert result["spec"].chart_type == "line"

    def test_parse_defaults_for_optional_metadata(self):
        """Should provide defaults for optional metadata."""
        minimal = {
            "chart_type": "bar",
            "x_axis": {"column": "category"},
            "y_axis": {"columns": ["revenue"]}
        }
        
        result = parse_llm_response(json.dumps(minimal), "file-123")
        assert result["explanation"] == ""
        assert result["confidence"] == 0.5  # Default confidence
        assert result["alternatives"] == []

    def test_parse_validates_column_names(self):
        """Should reject invalid column names when valid_columns provided."""
        response = {
            "chart_type": "bar",
            "x_axis": {"column": "0"},  # Index, not name
            "y_axis": {"columns": ["1"]}  # Index, not name
        }
        valid_columns = ["date", "revenue", "category"]
        
        with pytest.raises(AISuggestError) as exc_info:
            parse_llm_response(
                json.dumps(response), 
                "file-123",
                valid_columns=valid_columns
            )
        
        assert exc_info.value.code == "invalid_columns"
        assert "0" in str(exc_info.value) or "1" in str(exc_info.value)

    def test_parse_accepts_valid_column_names(self):
        """Should accept valid column names when validation enabled."""
        response = {
            "chart_type": "bar",
            "x_axis": {"column": "category"},
            "y_axis": {"columns": ["revenue"]}
        }
        valid_columns = ["date", "revenue", "category"]
        
        result = parse_llm_response(
            json.dumps(response), 
            "file-123",
            valid_columns=valid_columns
        )
        
        assert result["spec"].x_axis.column == "category"
        assert result["spec"].y_axis.columns == ["revenue"]


# =============================================================================
# Generate Chart Suggestion (Integration) Tests
# =============================================================================

class TestGenerateChartSuggestion:
    """Tests for the main generate_chart_suggestion function."""

    def test_successful_suggestion(self, sample_df, valid_llm_response):
        """Should generate suggestion when LLM call succeeds."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(valid_llm_response)))
        ]
        mock_response.usage = MagicMock(
            prompt_tokens=450,
            completion_tokens=120
        )
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch("app.services.ai_suggest_service.get_openai_client", return_value=mock_client):
            with patch("app.utils.storage.get_dataframe", return_value=sample_df):
                request = AISuggestRequest(file_id="test-123")
                result = generate_chart_suggestion(request)
        
        assert isinstance(result, AISuggestResponse)
        assert result.suggested_spec.file_id == "test-123"
        assert result.usage["prompt_tokens"] == 450
        assert result.usage["completion_tokens"] == 120
        assert result.usage["model"] == "gpt-4o-mini"

    def test_file_not_found(self):
        """Should raise error when file not found."""
        with patch("app.utils.storage.get_dataframe", side_effect=ValueError("Dataframe not found")):
            request = AISuggestRequest(file_id="nonexistent")
            
            with pytest.raises(AISuggestError) as exc_info:
                generate_chart_suggestion(request)
            
            assert "not found" in str(exc_info.value).lower()

    def test_llm_api_error(self, sample_df):
        """Should raise error when LLM API fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch("app.services.ai_suggest_service.get_openai_client", return_value=mock_client):
            with patch("app.utils.storage.get_dataframe", return_value=sample_df):
                request = AISuggestRequest(file_id="test-123")
                
                with pytest.raises(AISuggestError) as exc_info:
                    generate_chart_suggestion(request)
                
                assert "api" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    def test_uses_user_instructions(self, sample_df, valid_llm_response):
        """Should pass user instructions to LLM."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(valid_llm_response)))
        ]
        mock_response.usage = MagicMock(prompt_tokens=450, completion_tokens=120)
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch("app.services.ai_suggest_service.get_openai_client", return_value=mock_client):
            with patch("app.utils.storage.get_dataframe", return_value=sample_df):
                request = AISuggestRequest(
                    file_id="test-123",
                    user_instructions="Show revenue by category"
                )
                generate_chart_suggestion(request)
            
            # Verify the call included user instructions
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
            prompt_content = " ".join(m["content"] for m in messages)
            assert "Show revenue by category" in prompt_content

    def test_respects_sheet_name(self, sample_df, valid_llm_response):
        """Should use sheet_name when loading data."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(valid_llm_response)))
        ]
        mock_response.usage = MagicMock(prompt_tokens=450, completion_tokens=120)
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch("app.services.ai_suggest_service.get_openai_client", return_value=mock_client):
            with patch("app.utils.storage.get_dataframe", return_value=sample_df) as mock_get_df:
                request = AISuggestRequest(
                    file_id="test-123",
                    sheet_name="Sales"
                )
                result = generate_chart_suggestion(request)
                
                mock_get_df.assert_called_once_with("test-123", "Sales")
                assert result.suggested_spec.sheet_name == "Sales"


# =============================================================================
# ChartSpec JSON Schema Tests
# =============================================================================

class TestChartSpecJSONSchema:
    """Tests for the JSON schema used in LLM prompts."""

    def test_schema_is_valid_json(self):
        """Schema should be valid JSON."""
        schema = json.loads(CHARTSPEC_JSON_SCHEMA)
        assert isinstance(schema, dict)

    def test_schema_includes_all_chart_types(self):
        """Schema should include all supported chart types."""
        schema = json.loads(CHARTSPEC_JSON_SCHEMA)
        chart_types = ["bar", "line", "scatter", "histogram", "box", "pie", "area", "heatmap"]
        
        # Should be in the schema somewhere
        schema_str = CHARTSPEC_JSON_SCHEMA.lower()
        for chart_type in chart_types:
            assert chart_type in schema_str


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_ai_suggest_error_message(self):
        """AISuggestError should have descriptive message."""
        error = AISuggestError("Test error message", code="test_error")
        assert str(error) == "Test error message"
        assert error.code == "test_error"

    def test_ai_suggest_error_with_details(self):
        """AISuggestError should support additional details."""
        error = AISuggestError(
            "Validation failed",
            code="validation_error",
            details={"field": "x_axis", "issue": "column not found"}
        )
        assert error.details["field"] == "x_axis"
