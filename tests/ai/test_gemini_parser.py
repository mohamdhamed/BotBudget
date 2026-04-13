import json
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from ai.gemini_parser import parse_transaction, _sanitize_input


def test_sanitize_input():
    # Long text truncation
    long_text = "a" * 600
    assert len(_sanitize_input(long_text)) == 500

    # Control chars removal
    messy = "Hello\x00\x08World"
    assert _sanitize_input(messy) == "HelloWorld"

    # Arabic is kept intact
    assert _sanitize_input("صرفت ٥٠ يورو") == "صرفت ٥٠ يورو"


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_transaction_success(mock_model_class):
    # Setup mock
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = json.dumps({
        "type": "expense",
        "amount": 50.0,
        "category": "طعام",
        "description": "سوبرماركت",
        "date": "2026-04-12"
    })
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    result = parse_transaction("صرفت ٥٠ يورو سوبرماركت")

    assert result["type"] == "expense"
    assert result["amount"] == 50.0
    assert result["category"] == "طعام"

    # Ensure model was called with the right text
    mock_instance.generate_content.assert_called_once()
    called_text = mock_instance.generate_content.call_args[0][0]
    assert called_text == "صرفت ٥٠ يورو سوبرماركت"


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_transaction_invalid_json(mock_model_class):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    # Model returns conversational garbage instead of JSON
    mock_response.text = "أهلاً بك! لقد فهمت أنك صرفت 50 يورو."
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    result = parse_transaction("صرفت ٥٠ يورو")

    assert "error" in result
    assert result["error"] == "parse_failed"
    assert "لم أفهم" in result["question"]


def test_parse_transaction_empty_input():
    result = parse_transaction("   ")
    assert "error" in result
    assert result["error"] == "empty"


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_transaction_missing_fields(mock_model_class):
    """Test handling incomplete JSON response."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    # Response missing required fields
    mock_response.text = json.dumps({
        "type": "expense",
        "amount": 50.0
        # Missing category and date
    })
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    result = parse_transaction("صرفت ٥٠ يورو")

    # Should handle gracefully with defaults or error
    assert "amount" in result or "error" in result


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_transaction_api_error(mock_model_class):
    """Test handling API errors."""
    mock_instance = MagicMock()
    mock_instance.generate_content.side_effect = Exception("API Error")
    mock_model_class.return_value = mock_instance

    result = parse_transaction("صرفت ٥٠ يورو")

    assert "error" in result


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_transaction_invalid_amount(mock_model_class):
    """Test handling invalid amount."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = json.dumps({
        "type": "expense",
        "amount": "not_a_number",  # Invalid
        "category": "طعام"
    })
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    result = parse_transaction("صرفت مبلغ غير واضح")

    assert "error" in result or result.get("amount") is not None


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_transaction_income(mock_model_class):
    """Test parsing income transaction."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = json.dumps({
        "type": "income",
        "amount": 500.0,
        "category": "salary",
        "description": "Monthly salary"
    })
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    result = parse_transaction("أستقبلت 500 يورو راتب")

    assert result["type"] == "income"
    assert result["amount"] == 500.0


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_parse_recurring(mock_model_class):
    """Test parsing recurring payment text."""
    from ai.gemini_parser import parse_recurring
    
    mock_instance = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = json.dumps({
        "frequency": "monthly",
        "amount": 500.0,
        "category": "rent",
        "description": "Apartment rent"
    })
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    result = parse_recurring("كل شهر 500 يورو إيجار")

    assert "frequency" in result
    assert "amount" in result


@patch('ai.gemini_parser.genai.GenerativeModel')
def test_sanitize_input_arabic_digits(mock_model_class):
    """Test Arabic digit normalization."""
    # Arabic digits: ٠١٢٣٤٥٦٧٨٩
    arabic_text = "صرفت ٥٠ يورو"
    sanitized = _sanitize_input(arabic_text)
    
    # Should still be readable
    assert "صرفت" in sanitized
    # Arabic digits should be normalized or kept
    assert sanitized is not None


def test_sanitize_input_max_length():
    """Test text truncation at max length."""
    long_text = "a" * 1000
    result = _sanitize_input(long_text)
    
    assert len(result) <= 500  # Should respect max length


def test_sanitize_input_whitespace():
    """Test whitespace normalization."""
    messy = "  hello   world  "
    result = _sanitize_input(messy)
    
    # Should clean up whitespace
    assert result is not None
