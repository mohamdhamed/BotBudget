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

_SYSTEM_PROMPT = f"""أنت مساعد مالي شخصي ذكي. مهمتك الوحيدة هي تحويل رسالة المستخدم العربية
(عامية أو فصحى) إلى JSON يمثل معاملة مالية.

تاريخ اليوم: {{today}}

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
- "صرفت ٥٠ سوبرماركت" → {{"type":"expense","amount":50,"category":"سوبرماركت","description":"مشتريات سوبرماركت","date":"{{today}}"}}
- "جالي راتب ٢٠٠٠" → {{"type":"income","amount":2000,"category":"راتب","description":"راتب شهري","date":"{{today}}"}}
- "٣٥٠ دفعة من الراتب" → {{"type":"income","amount":350,"category":"راتب","description":"دفعة من الراتب","date":"{{today}}"}}
- "دفعت إيجار ٨٠٠" → {{"type":"expense","amount":800,"category":"إيجار","description":"إيجار","date":"{{today}}"}}
- "100 بنزين" → {{"type":"expense","amount":100,"category":"بنزين","description":"بنزين","date":"{{today}}"}}
- "حولولي 500" → {{"type":"income","amount":500,"category":"تحويل","description":"تحويل مالي","date":"{{today}}"}}

## التنسيق:
أرجع JSON فقط بدون أي شرح أو markdown:
{{"type":"expense|income","amount":<رقم>,"category":"<فئة>","description":"<وصف>","date":"YYYY-MM-DD"}}

إذا مش واضحة خالص: {{"error":"unclear","question":"<سؤال توضيحي بالعربي>"}}
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
        Dict with: name, amount, frequency, next_due_date, category.
        OR error dict if unclear.
    """
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

