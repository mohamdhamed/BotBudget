"""
ai/gemini_parser.py
-------------------
Uses Google Gemini 2.5 Flash to parse natural-language financial messages
into structured transaction data.

Responsibilities:
    - Understand Arabic (colloquial & formal) financial text.
    - Extract: type, amount, category, description, date.
    - Return a clean JSON dict ready for the Service layer.
"""

import json
from datetime import date, timedelta

import google.generativeai as genai

from config import GEMINI_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

# Configure the Gemini client once at module level
genai.configure(api_key=GEMINI_API_KEY)

_model = genai.GenerativeModel("gemini-2.5-flash")

# ── System prompt for the AI ─────────────────────────────

_SYSTEM_PROMPT = f"""You are a personal finance assistant. Your ONLY job is to parse
the user's Arabic text message into a structured JSON object representing a financial
transaction.

Today's date is: {{today}}

Rules:
1. Determine if this is an "expense" or "income".
2. Extract the amount as a number.
3. Determine the category from this list:
   طعام, مواصلات, سوبرماركت, إيجار, فواتير, اشتراكات, ترفيه, صحة, تعليم, ملابس, هدايا, راتب, تحويل, أخرى
4. Extract or infer the date. If the user says "امبارح" use yesterday, "النهاردة" use today, etc.
5. Extract a short description if mentioned.
6. Currency is always EUR.

IMPORTANT:
- Reply ONLY with valid JSON, no markdown, no explanation.
- If you cannot parse the message, return: {{"error": "unclear", "question": "<ask a clarifying question in Arabic>"}}

JSON format:
{{
    "type": "expense" | "income",
    "amount": <number>,
    "category": "<category>",
    "description": "<short description or null>",
    "date": "YYYY-MM-DD"
}}
"""


def parse_transaction(text: str) -> dict:
    """
    Send a natural-language financial message to Gemini and get structured data back.

    Args:
        text: The raw Arabic text from the user, e.g. "صرفت ٥٠ يورو سوبرماركت".

    Returns:
        A dict with keys: type, amount, category, description, date.
        OR a dict with keys: error, question (if the message is unclear).

    Raises:
        ValueError: If the AI response cannot be parsed as JSON.
    """
    today = date.today().isoformat()
    prompt = _SYSTEM_PROMPT.replace("{today}", today)

    try:
        response = _model.generate_content(
            [
                {"role": "user", "parts": [{"text": prompt}]},
                {"role": "user", "parts": [{"text": text}]},
            ],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=300,
            ),
        )

        raw = response.text.strip()

        # Clean markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        result = json.loads(raw)
        logger.info(f"Gemini parsed: {result}")
        return result

    except json.JSONDecodeError:
        logger.warning(f"Gemini returned non-JSON: {response.text}")
        return {"error": "parse_failed", "question": "لم أفهم الرسالة. ممكن تعيد صياغتها؟"}
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {"error": "api_error", "question": "حصل مشكلة في التحليل. حاول تاني."}


def parse_recurring(text: str) -> dict:
    """
    Parse a natural-language message describing a recurring payment.

    Args:
        text: e.g. "اشتراك نتفليكس ١٥ يورو كل شهر"

    Returns:
        Dict with: name, amount, frequency, next_due_date.
        OR error dict if unclear.
    """
    today = date.today().isoformat()
    recurring_prompt = f"""You are a personal finance assistant. Parse the user's Arabic message
into a recurring payment JSON.

Today's date is: {today}

Rules:
1. Extract the payment name.
2. Extract the amount as a number.
3. Determine frequency: "daily", "weekly", "monthly", or "yearly".
4. Determine or infer the next payment date. If not mentioned, assume it's the 1st of next month for monthly.
5. Currency is EUR.

Reply ONLY with valid JSON:
{{
    "name": "<payment name>",
    "amount": <number>,
    "frequency": "daily" | "weekly" | "monthly" | "yearly",
    "next_due_date": "YYYY-MM-DD"
}}

If unclear, return: {{"error": "unclear", "question": "<clarifying question in Arabic>"}}
"""
    try:
        response = _model.generate_content(
            [
                {"role": "user", "parts": [{"text": recurring_prompt}]},
                {"role": "user", "parts": [{"text": text}]},
            ],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=300,
            ),
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        result = json.loads(raw)
        logger.info(f"Gemini parsed recurring: {result}")
        return result

    except json.JSONDecodeError:
        logger.warning(f"Gemini returned non-JSON for recurring: {response.text}")
        return {"error": "parse_failed", "question": "لم أفهم. ممكن تكتب اسم الاشتراك والمبلغ والتكرار؟"}
    except Exception as e:
        logger.error(f"Gemini API error (recurring): {e}")
        return {"error": "api_error", "question": "حصل مشكلة. حاول تاني."}
