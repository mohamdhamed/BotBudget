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
