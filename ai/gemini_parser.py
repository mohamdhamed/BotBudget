"""
ai/gemini_parser.py
-------------------
Uses Google Gemini 2.0 Flash to parse natural-language financial messages
into structured transaction data, with automatic fallback to Groq (Llama 3)
when Gemini quota is exhausted.

Priority: Gemini → Groq (if GROQ_API_KEY is set and Gemini returns 429)
"""

import re
import json
from datetime import date

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from config import GEMINI_API_KEY, GROQ_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

# Configure the Gemini client once at module level
genai.configure(api_key=GEMINI_API_KEY)

# ── System prompt for the AI ─────────────────────────────

_SYSTEM_PROMPT = """أنت مساعد مالي شخصي ذكي. مهمتك الوحيدة هي تحويل رسالة المستخدم العربية
(عامية أو فصحى) إلى JSON يمثل معاملة مالية.

تاريخ اليوم: {today}

## قواعد التحليل:

1. **النوع (type):**
   - "expense" = مصروف → كلمات مثل: صرفت، دفعت، اشتريت، حسابي، فاتورة، إيجار، ثمن
   - "income" = دخل → كلمات مثل: جالي، استلمت، راتب، قبضت، حولولي، كسبت، مرتب، دخل
   - إذا الرسالة فيها مبلغ بدون فعل واضح، اعتبرها "expense"

2. **المبلغ (amount):** استخرج الرقم سواء بالأرقام العربية (٥٠) أو الإنجليزية (50)

3. **الفئة (category):** اختر الأنسب من:
   طعام، مواصلات، سوبرماركت، إيجار، فواتير، اشتراكات، ترفيه، صحة، تعليم، ملابس، هدايا، راتب، تحويل، مطعم، كافيه، بنزين، تأمين، أخرى

4. **التاريخ (date):** إذا ما ذكرش تاريخ → استخدم اليوم. "امبارح/أمس" → أمس. "أول امبارح" → قبل يومين

5. **الوصف (description):** وصف قصير بالعربي

## أمثلة:
- "صرفت ٥٠ سوبرماركت" → {"type":"expense","amount":50,"category":"سوبرماركت","description":"مشتريات سوبرماركت","date":"{today}"}
- "جالي راتب ٢٠٠٠" → {"type":"income","amount":2000,"category":"راتب","description":"راتب شهري","date":"{today}"}
- "٣٥٠ دفعة من الراتب" → {"type":"income","amount":350,"category":"راتب","description":"دفعة من الراتب","date":"{today}"}
- "دفعت إيجار ٨٠٠" → {"type":"expense","amount":800,"category":"إيجار","description":"إيجار","date":"{today}"}
- "100 بنزين" → {"type":"expense","amount":100,"category":"بنزين","description":"بنزين","date":"{today}"}
- "حولولي 500" → {"type":"income","amount":500,"category":"تحويل","description":"تحويل مالي","date":"{today}"}

## التنسيق:
أرجع JSON فقط بدون أي شرح أو markdown:
{"type":"expense|income","amount":<رقم>,"category":"<فئة>","description":"<وصف>","date":"YYYY-MM-DD","confidence":<0.0-1.0>}

حقل confidence: مدى ثقتك في التحليل (1.0 = متأكد تماماً، 0.5 = محتمل، 0.3 = تخمين)

إذا مش واضحة خالص: {"error":"unclear","question":"<سؤال توضيحي بالعربي>"}
"""

_RECURRING_PROMPT_TEMPLATE = """أنت مساعد مالي شخصي. حلل رسالة المستخدم العربية وحولها لـ JSON يمثل دفعة متكررة.

تاريخ اليوم: {today}

## قواعد التحليل:

1. **اسم الدفعة (name):** اسم الاشتراك أو الفاتورة أو الدفعة
2. **المبلغ (amount):** استخرج الرقم (بالعربي أو الإنجليزي)
3. **التكرار (frequency):**
   - "يومي/كل يوم" → "daily"
   - "أسبوعي/كل أسبوع" → "weekly"
   - "شهري/كل شهر" → "monthly" (الافتراضي لو مش مذكور)
   - "سنوي/كل سنة" → "yearly"
4. **موعد الدفعة الجاية (next_due_date):** إذا مش مذكور:
   - شهري → أول الشهر الجاي
   - أسبوعي → بعد أسبوع من اليوم
   - سنوي → بعد سنة من اليوم
5. **الفئة (category):** اختر من: اشتراكات، إيجار، فواتير، تأمين، تعليم، صحة، مواصلات، أخرى

## أمثلة:
- "نتفليكس ١٥ كل شهر" → {{"name":"نتفليكس","amount":15,"frequency":"monthly","next_due_date":"أول الشهر الجاي","category":"اشتراكات"}}
- "إيجار الشقة ٨٠٠ شهري يوم ١" → {{"name":"إيجار الشقة","amount":800,"frequency":"monthly","next_due_date":"أول الشهر الجاي","category":"إيجار"}}
- "تأمين السيارة ٦٠٠ كل سنة" → {{"name":"تأمين السيارة","amount":600,"frequency":"yearly","next_due_date":"بعد سنة","category":"تأمين"}}
- "فاتورة النت ٣٠ شهري" → {{"name":"فاتورة الإنترنت","amount":30,"frequency":"monthly","next_due_date":"أول الشهر الجاي","category":"فواتير"}}

## التنسيق:
أرجع JSON فقط بدون شرح أو markdown:
{{"name":"<اسم>","amount":<رقم>,"frequency":"daily|weekly|monthly|yearly","next_due_date":"YYYY-MM-DD","category":"<فئة>"}}

إذا مش واضحة: {{"error":"unclear","question":"<سؤال توضيحي بالعربي>"}}
"""


def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences and extra whitespace from AI response."""
    raw = raw.strip()
    if raw.startswith("```"):
        first_line_end = raw.find("\n")
        if first_line_end != -1:
            raw = raw[first_line_end + 1:]
        else:
            raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


# ── Security constants ────────────────────────────────
_MAX_INPUT_LENGTH = 500
_DANGEROUS_PATTERNS = re.compile(
    r"(ignore|forget|disregard|system|prompt|instruction)",
    re.IGNORECASE,
)


def _sanitize_input(text: str) -> str:
    """Truncate, strip control chars, basic prompt injection defense."""
    text = text[:_MAX_INPUT_LENGTH]
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


def _call_groq(system_prompt: str, user_text: str) -> str:
    """Call Groq API (OpenAI-compatible) and return raw response text."""
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.1,
        max_tokens=300,
    )
    return response.choices[0].message.content


def _call_gemini(model_name: str, system_prompt: str, user_text: str) -> str:
    """Call Gemini API and return raw response text. Raises ResourceExhausted on 429."""
    model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
    response = model.generate_content(
        user_text,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=300,
        ),
    )
    return response.text


def _parse_with_fallback(system_prompt: str, user_text: str, context_name: str) -> str:
    """
    Try Gemini first; fall back to Groq on quota exhaustion.
    Returns raw AI response text.
    """
    try:
        raw = _call_gemini("gemini-2.0-flash", system_prompt, user_text)
        logger.debug("Used Gemini for %s", context_name)
        return raw
    except ResourceExhausted:
        if not GROQ_API_KEY:
            logger.error("Gemini quota exceeded and no GROQ_API_KEY configured.")
            raise
        logger.warning("Gemini quota exceeded — falling back to Groq for %s", context_name)
        return _call_groq(system_prompt, user_text)


def parse_transaction(text: str) -> dict:
    """
    Parse a natural-language Arabic financial message into structured data.

    Returns:
        Dict with keys: type, amount, category, description, date, confidence.
        OR dict with keys: error, question (if unclear).
    """
    text = _sanitize_input(text)
    if not text:
        return {"error": "empty", "question": "الرسالة فاضية. اكتب المعاملة المالية."}

    today = date.today().isoformat()
    system_prompt = _SYSTEM_PROMPT.replace("{today}", today)

    try:
        raw = _parse_with_fallback(system_prompt, text, "parse_transaction")
        raw = _clean_json_response(raw)
        result = json.loads(raw)
        logger.info("Transaction parsed: type=%s, category=%s", result.get("type", "?"), result.get("category", "?"))
        return result
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON response")
        return {"error": "parse_failed", "question": "لم أفهم الرسالة. ممكن تعيد صياغتها؟"}
    except Exception as e:
        logger.error(f"AI API error: {e}", exc_info=True)
        return {"error": "api_error", "question": "حصل مشكلة في التحليل. حاول تاني."}


def parse_recurring(text: str) -> dict:
    """
    Parse a natural-language message describing a recurring payment.

    Returns:
        Dict with: name, amount, frequency, next_due_date, category.
        OR error dict if unclear.
    """
    text = _sanitize_input(text)
    if not text:
        return {"error": "empty", "question": "الرسالة فاضية. اكتب تفاصيل الدفعة المتكررة."}

    today = date.today().isoformat()
    system_prompt = _RECURRING_PROMPT_TEMPLATE.format(today=today)

    try:
        raw = _parse_with_fallback(system_prompt, text, "parse_recurring")
        raw = _clean_json_response(raw)
        result = json.loads(raw)
        logger.info("Recurring parsed: name=%s, frequency=%s", result.get("name", "?"), result.get("frequency", "?"))
        return result
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON for recurring")
        return {"error": "parse_failed", "question": "لم أفهم. ممكن تكتب اسم الاشتراك والمبلغ والتكرار؟"}
    except Exception as e:
        logger.error(f"AI API error (recurring): {e}", exc_info=True)
        return {"error": "api_error", "question": "حصل مشكلة. حاول تاني."}
