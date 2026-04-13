<div align="center">

# 🤖 BotBudget

### بوت تيليجرام ذكي لإدارة المصاريف الشخصية

[![CI](https://github.com/mohamdhamed/BotBudget/actions/workflows/ci.yml/badge.svg)](https://github.com/mohamdhamed/BotBudget/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://core.telegram.org/bots)

**أرسل رسالة عادية بالعربي — والبوت يفهمها ويسجلها تلقائياً بالذكاء الاصطناعي** 🧠

</div>

---

## 📖 نظرة عامة

**BotBudget** هو بوت تيليجرام شخصي بيساعدك تتابع مصاريفك ودخلك بأسهل طريقة ممكنة. بدل ما تكتب أرقام في جداول، كل اللي عليك تبعتله رسالة عادية بالعربي زي:

> "دفعت 50 يورو سوبرماركت"
> "راتب 3000 يورو"
> "غداء 15 يورو مطعم"

والبوت بيفهم الرسالة عن طريق **Google Gemini AI** ويصنفها ويسجلها أوتوماتيك! 🚀

---

## ✨ الميزات

### 📝 تسجيل ذكي
- تسجيل المصاريف والدخل **بالكتابة الطبيعية بالعربي**
- التصنيف التلقائي (طعام، مواصلات، إيجار، ...)
- دعم الأرقام العربية والإنجليزية

### 📊 تقارير وتحليلات
- ملخص يومي `/today` — أسبوعي `/week` — شهري `/month`
- مقارنة شهرية `/compare`
- تقرير بفترة مخصصة `/report`
- عرض الرصيد الكلي `/balance`
- بحث في المعاملات `/search`
- عرض حسب الفئة `/category`

### 📈 رسوم بيانية
- رسم بياني دائري للمصاريف الشهرية `/chart`
- رسم بياني أعمدة لآخر 7 أيام `/chart_week`
- دعم النصوص العربية في الرسومات

### 💰 إدارة الميزانية
- تحديد ميزانية لكل فئة `/budget set طعام 200`
- تنبيهات عند تجاوز 80% و 100% من الميزانية
- شريط تقدم مرئي لحالة الميزانية

### 🔁 مدفوعات متكررة
- إضافة دفعات متكررة (يومي/أسبوعي/شهري/سنوي)
- تذكيرات يومية تلقائية بالمواعيد القادمة
- تقرير أسبوعي تلقائي كل يوم أحد

### 📤 تصدير البيانات
- تصدير CSV `/export_csv`
- تصدير Excel `/export_excel` مع ملخص تلقائي

### 🔒 الأمان
- نظام Whitelist — بس المستخدمين المصرح لهم
- Rate Limiting — حماية من الاستخدام المفرط
- تنظيف المدخلات (Input Sanitization)

---

## 🏗️ هيكل المشروع

```
BotBudget/
├── main.py                  # 🚀 نقطة الدخول الرئيسية
├── config.py                # ⚙️ إعدادات التطبيق
├── requirements.txt         # 📦 المكتبات المطلوبة
├── Dockerfile               # 🐳 صورة Docker
├── docker-compose.yml       # 🐳 تشغيل Docker
│
├── ai/                      # 🧠 وحدة الذكاء الاصطناعي
│   └── gemini_parser.py     #    تحليل النصوص عبر Gemini
│
├── db/                      # 🗄️ طبقة قاعدة البيانات
│   ├── connection.py        #    AsyncConnectionPool (psycopg3)
│   └── init_db.py           #    إنشاء الجداول
│
├── models/                  # 📋 النماذج (Domain Models)
│   ├── expense.py           #    نموذج المصروف/الدخل
│   └── recurring.py         #    نموذج الدفعة المتكررة
│
├── repositories/            # 💾 طبقة الوصول للبيانات (async)
│   ├── expense_repo.py      #    CRUD للمصاريف
│   ├── budget_repo.py       #    CRUD للميزانيات
│   ├── recurring_repo.py    #    CRUD للدفعات المتكررة
│   └── user_repo.py         #    CRUD للمستخدمين
│
├── services/                # ⚙️ طبقة منطق التطبيق (async)
│   ├── expense_service.py   #    منطق المصاريف
│   ├── budget_service.py    #    منطق الميزانية
│   ├── recurring_service.py #    منطق الدفعات المتكررة
│   ├── chart_service.py     #    توليد الرسوم البيانية
│   └── export_service.py    #    تصدير البيانات
│
├── handlers/                # 📱 طبقة التعامل مع تيليجرام
│   ├── expense_handler.py   #    أوامر المصاريف
│   ├── budget_handler.py    #    أوامر الميزانية
│   ├── recurring_handler.py #    أوامر الدفعات المتكررة
│   ├── chart_handler.py     #    أوامر الرسوم البيانية
│   ├── export_handler.py    #    أوامر التصدير
│   └── start_handler.py     #    أوامر البداية والمساعدة
│
├── security/                # 🔒 طبقة الحماية
│   ├── auth.py              #    التحقق من الصلاحيات
│   └── rate_limiter.py      #    تحديد معدل الاستخدام
│
├── alembic/                 # 🔄 ترقيات قاعدة البيانات
│   └── versions/            #    ملفات الترقيات
│
├── tests/                   # 🧪 اختبارات الوحدة
│   ├── ai/                  #    اختبارات الـ AI Parser
│   ├── models/              #    اختبارات النماذج
│   └── services/            #    اختبارات الخدمات
│
└── utils/                   # 🔧 أدوات مساعدة
    └── logger.py            #    نظام التسجيل (Logging)
```

---

## 🚀 التشغيل

### المتطلبات
- **Python 3.12+**
- **PostgreSQL 14+**
- **حساب Telegram Bot** — من [@BotFather](https://t.me/BotFather)
- **Google Gemini API Key** — من [Google AI Studio](https://aistudio.google.com)

### الطريقة الأولى: Docker (موصى بها) 🐳

```bash
# 1. استنساخ المشروع
git clone https://github.com/mohamdhamed/BotBudget.git
cd BotBudget

# 2. إنشاء ملف الإعدادات
cp .env.example .env
# عدّل ملف .env وأضف البيانات المطلوبة (انظر الإعدادات أدناه)

# 3. تشغيل البوت
sudo docker compose up -d --build

# 4. مراقبة السجلات
sudo docker compose logs -f --tail=50
```

### الطريقة الثانية: تشغيل محلي

```bash
# 1. استنساخ المشروع
git clone https://github.com/mohamdhamed/BotBudget.git
cd BotBudget

# 2. إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/macOS
# أو: venv\Scripts\activate  # Windows

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. إنشاء ملف الإعدادات
cp .env.example .env
# عدّل ملف .env

# 5. تأكد من تشغيل PostgreSQL وإنشاء قاعدة البيانات
createdb bot_budget

# 6. تشغيل البوت
python main.py
```

---

## ⚙️ الإعدادات

أنشئ ملف `.env` بالمتغيرات التالية:

```env
# === Telegram Bot ===
TELEGRAM_BOT_TOKEN=your_bot_token_here

# === Google Gemini AI ===
GEMINI_API_KEY=your_gemini_api_key_here

# === PostgreSQL Database ===
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bot_budget
DB_USER=botbudget_user
DB_PASS=your_secure_password_here

# === Security ===
ALLOWED_USER_IDS=123456789          # أرقام تيليجرام (مفصولة بفاصلات)

# === Rate Limiting (اختياري) ===
RATE_LIMIT_MESSAGES=30              # عدد الرسائل المسموح بها
RATE_LIMIT_WINDOW_SECONDS=60        # في كم ثانية
```

> 💡 **نصيحة:** استخدم أمر `/myid` في البوت لمعرفة رقم الـ Telegram ID بتاعك.

---

## 📱 أوامر البوت

| الأمر | الوصف |
|-------|-------|
| `/start` | 🚀 بدء البوت |
| `/help` | 📖 عرض المساعدة |
| `/myid` | 🆔 عرض رقم حسابك |
| `/today` | 📅 ملخص النهاردة |
| `/week` | 📆 ملخص آخر ٧ أيام |
| `/month` | 📊 ملخص الشهر |
| `/category <فئة>` | 🏷️ عرض حسب الفئة |
| `/edit <رقم> مبلغ:<قيمة>` | ✏️ تعديل معاملة |
| `/delete <رقم>` | 🗑️ حذف عملية |
| `/compare` | 🔄 مقارنة شهرية |
| `/search <كلمة>` | 🔍 بحث في المعاملات |
| `/report <من> <إلى>` | 📋 تقرير مخصص |
| `/balance` | 🏦 الرصيد الكلي |
| `/budget set <فئة> <مبلغ>` | 💰 تحديد ميزانية |
| `/budget` | 💰 حالة الميزانية |
| `/recurring` | 🔁 المدفوعات المتكررة |
| `/add_recurring` | ➕ إضافة دفعة متكررة |
| `/delete_recurring <رقم>` | ❌ حذف دفعة متكررة |
| `/chart` | 📊 رسم بياني شهري |
| `/chart_week` | 📈 رسم بياني أسبوعي |
| `/export_csv` | 📄 تصدير CSV |
| `/export_excel` | 📊 تصدير Excel |

---

## 🧪 الاختبارات

```bash
# تثبيت أدوات الاختبار
pip install -r requirements-dev.txt

# تشغيل جميع الاختبارات
pytest tests/ -v

# مع تقرير التغطية
pytest tests/ -v --cov=./
```

**الاختبارات تشمل:**
- اختبارات الـ AI Parser (تنظيف المدخلات، المحاكاة)
- اختبارات النماذج (Expense, RecurringPayment)
- اختبارات الخدمات (ExpenseService مع AsyncMock)

---

## 🔄 ترقيات قاعدة البيانات (Migrations)

المشروع يستخدم **Alembic** لإدارة تغييرات الـ Schema:

```bash
# إنشاء ترقية جديدة
alembic revision -m "وصف التغيير"

# تطبيق جميع الترقيات
alembic upgrade head

# التراجع خطوة واحدة
alembic downgrade -1

# عرض الحالة الحالية
alembic current
```

---

## 🛠️ التقنيات المستخدمة

| التقنية | الاستخدام |
|---------|-----------|
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | التواصل مع Telegram API |
| [Google Gemini AI](https://ai.google.dev/) | تحليل النصوص العربية بالذكاء الاصطناعي |
| [psycopg3](https://www.psycopg.org/psycopg3/) | اتصال غير متزامن بـ PostgreSQL |
| [Alembic](https://alembic.sqlalchemy.org/) | إدارة ترقيات قاعدة البيانات |
| [pandas](https://pandas.pydata.org/) | تصدير البيانات (CSV/Excel) |
| [matplotlib](https://matplotlib.org/) | توليد الرسوم البيانية |
| [Docker](https://www.docker.com/) | الحاويات والنشر |
| [GitHub Actions](https://github.com/features/actions) | التكامل المستمر (CI/CD) |
| [pytest](https://pytest.org/) | اختبارات الوحدة |
| [ruff](https://github.com/astral-sh/ruff) | فحص وتنسيق الكود |

---

## 📐 المعمارية (Architecture)

```
┌─────────────────────────────────────────────────┐
│                  Telegram User                   │
│              (رسالة عربية طبيعية)                 │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              Handlers Layer                      │
│         (أوامر + معالجة الرسائل)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Security │ │  Auth    │ │  Rate Limiter    │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              Services Layer                      │
│           (منطق الأعمال - async)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Expense  │ │ Budget   │ │   Recurring      │ │
│  │ Service  │ │ Service  │ │   Service        │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└────┬───────────────────────────────────┬────────┘
     │                                   │
     ▼                                   ▼
┌────────────────┐            ┌──────────────────┐
│   Gemini AI    │            │  Repositories    │
│  (NLP Parser)  │            │     (async)      │
└────────────────┘            └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │   PostgreSQL     │
                              │  (AsyncPool)     │
                              └──────────────────┘
```

---

## 🤝 المساهمة

المساهمات مرحب بها! لو حابب تساهم:

1. Fork المشروع
2. أنشئ Branch جديد (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push للـ Branch (`git push origin feature/amazing-feature`)
5. افتح Pull Request

---

## 📄 الرخصة

هذا المشروع مرخص تحت [MIT License](LICENSE).

---

<div align="center">

**صنع بـ ❤️ لتبسيط إدارة المصاريف الشخصية**

</div>
