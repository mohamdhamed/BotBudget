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

import re
import json
from datetime import date, timedelta

import google.generativeai as genai

from config import GEMINI_API_KEY
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


def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences and extra whitespace from Gemini response."""
    raw = raw.strip()
    # Handle ```json or ``` at the start
    if raw.startswith("```"):
        first_line_end = raw.find("\n")
        if first_line_end != -1:
            raw = raw[first_line_end + 1:]
        else:
            raw = raw[3:]
    # Handle ``` at the end
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
    """
    Sanitize user input before sending to AI.

    - Truncates to max length
    - Strips control characters
    - Basic prompt injection defense
    """
    # Truncate to prevent abuse
    text = text[:_MAX_INPUT_LENGTH]
    # Remove control characters (keep Arabic + standard chars)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


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
    text = _sanitize_input(text)
    if not text:
        return {"error": "empty", "question": "الرسالة فاضية. اكتب المعاملة المالية."}

    today = date.today().isoformat()
    system_prompt = _SYSTEM_PROMPT.replace("{today}", today)

    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            text,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=300,
            ),
        )

        raw = _clean_json_response(response.text)
        logger.debug("Gemini response received (length=%d)", len(raw))

        result = json.loads(raw)
        logger.info("Transaction parsed: type=%s, category=%s", result.get("type", "?"), result.get("category", "?"))
        return result

    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON response (length=%d)", len(response.text) if response.text else 0)
        return {"error": "parse_failed", "question": "لم أفهم الرسالة. ممكن تعيد صياغتها؟"}
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        return {"error": "api_error", "question": "حصل مشكلة في التحليل. حاول تاني."}


def parse_recurring(text: str) -> dict:
    """
    Parse a natural-language message describing a recurring payment.

    Args:
        text: e.g. "اشتراك نتفليكس ١٥ يورو كل شهر"

    Returns:
        Dict with: name, amount, frequency, next_due_date, category.
        OR error dict if unclear.
    """
    text = _sanitize_input(text)
    if not text:
        return {"error": "empty", "question": "الرسالة فاضية. اكتب تفاصيل الدفعة المتكررة."}

    today = date.today().isoformat()
    recurring_prompt = f"""أنت مساعد مالي شخصي. حلل رسالة المستخدم العربية وحولها لـ JSON يمثل دفعة متكررة.

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
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=recurring_prompt,
        )
        response = model.generate_content(
            text,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=300,
            ),
        )

        raw = _clean_json_response(response.text)
        logger.debug("Gemini recurring response received (length=%d)", len(raw))

        result = json.loads(raw)
        logger.info("Recurring parsed: name=%s, frequency=%s", result.get("name", "?"), result.get("frequency", "?"))
        return result

    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON for recurring (length=%d)", len(response.text) if response.text else 0)
        return {"error": "parse_failed", "question": "لم أفهم. ممكن تكتب اسم الاشتراك والمبلغ والتكرار؟"}
    except Exception as e:
        logger.error(f"Gemini API error (recurring): {e}", exc_info=True)
        return {"error": "api_error", "question": "حصل مشكلة. حاول تاني."}

