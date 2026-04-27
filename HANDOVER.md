# 📦 BotBudget — وثيقة تسليم المشروع
> **Engineering Handover Document**
> الإصدار: v1.3 (Mini App MVP) · التاريخ: 2026-04-27 · اللغة: العربية + English Technical Terms

<div dir="rtl">

## 📋 جدول المحتويات

1. [نظرة عامة على المشروع](#1-نظرة-عامة)
2. [الحالة الحالية](#2-الحالة-الحالية)
3. [البنية المعمارية (Architecture)](#3-البنية-المعمارية)
4. [التقنيات المستخدمة (Tech Stack)](#4-التقنيات-المستخدمة)
5. [هيكل المستودع (Repository Structure)](#5-هيكل-المستودع)
6. [مخطط قاعدة البيانات (Database Schema)](#6-مخطط-قاعدة-البيانات)
7. [الميزات حسب الإصدار (Feature Matrix)](#7-الميزات-حسب-الإصدار)
8. [الأنظمة الفرعية (Subsystems Deep-Dive)](#8-الأنظمة-الفرعية)
9. [النشر والبيئات (Deployment & Environments)](#9-النشر-والبيئات)
10. [الأمان (Security)](#10-الأمان)
11. [الإعدادات (Configuration)](#11-الإعدادات)
12. [الاختبارات (Testing)](#12-الاختبارات)
13. [الديون التقنية والمشاكل المعروفة (Known Issues)](#13-الديون-التقنية)
14. [خريطة الطريق (Roadmap)](#14-خريطة-الطريق)
15. [دليل التسليم لكل فريق (Team Onboarding)](#15-دليل-التسليم-لكل-فريق)
16. [الملاحق (Appendices)](#16-الملاحق)

---

## 1. نظرة عامة

**BotBudget** بوت تيليجرام عربي ذكي لإدارة المصاريف الشخصية. يستقبل المستخدم رسائل بلغة طبيعية (مصرية/عربية) ويحوّلها إلى معاملات مالية منظّمة عبر AI، مع لوحة إدارة (Admin Dashboard) و Telegram Mini App للتجربة الكاملة.

### المنتج باختصار
- **الإدخال:** نص حر بالعربية → "صرفت 50 سوبرماركت" → معاملة منظّمة بمبلغ وفئة وعملة وتاريخ.
- **التقارير:** يومية / أسبوعية / شهرية / مقارنات / رسوم بيانية / تحليل ذكي / تصدير CSV/Excel.
- **الميزانيات:** حدود لكل فئة + تنبيهات تلقائية.
- **المدفوعات المتكررة:** تذكير قبل موعد الاستحقاق.
- **خطتان:** Free (محدود) + Premium (بلا حدود) مع تجربة 7 أيام للمستخدمين الجدد.

### البوتات الإنتاجية
| البيئة | البوت | الـ DB | الـ Domain |
|---|---|---|---|
| Production | `@Mybudgettracke_bot` | `bot_budget` | `www.botbudget.it` (admin), `app.botbudget.it` (miniapp — قيد الإطلاق) |
| Staging | `@botbudgettest_bot` | `bot_budget_staging` | `app-staging.botbudget.it` (miniapp) |

### المالك
- مطوّر منفرد: محمد حامد (`mohamd.hamed@gmail.com`)
- المشروع Open Source (Public Repo)

---

## 2. الحالة الحالية

### ما هو شغّال (Live in Production)
- ✅ البوت الأساسي (إدخال معاملات / تقارير / ميزانيات / متكرر)
- ✅ نظام Free vs Premium (v1.2)
- ✅ تجربة Premium 7 أيام للمستخدمين الجدد
- ✅ Admin Dashboard على `www.botbudget.it/admin`
- ✅ Auto-deploy يدوي عبر `git pull && docker compose up -d --build`
- ✅ Daily reminders + Weekly reports (للـ Premium فقط)

### ما هو على Staging (لم يُدمج بعد للإنتاج)
- ⏳ **Telegram Mini App (v1.3 MVP)** — Dashboard + Transactions + Add + Pie chart
- ⏳ تختبر حالياً على `@botbudgettest_bot` عبر `app-staging.botbudget.it`

### ما هو غير منجز
- ❌ نظام دفع آلي (الترقية حالياً يدوية: المستخدم يتواصل مع الدعم)
- ❌ CI/CD آلي (GitHub Actions تم إلغاؤه — deploy يدوي SSH)
- ❌ Tests شاملة (unit tests فقط لبعض المحلّلات والـ services)

---

## 3. البنية المعمارية

### مخطط النظام (System Diagram)

```
                                    ┌─────────────────────────────┐
                                    │   Telegram Users (Arabic)   │
                                    └──────────────┬──────────────┘
                                                   │
                            ┌──────────────────────┴──────────────────────┐
                            │                                             │
                    ┌───────▼────────┐                          ┌─────────▼─────────┐
                    │  Telegram Bot  │                          │  Telegram         │
                    │  (PTB polling) │                          │  Mini App (WebView)│
                    └───────┬────────┘                          └─────────┬─────────┘
                            │                                             │
                            │ HTTPS                                       │ HTTPS via
                            │                                             │ Cloudflare Tunnel
        ┌───────────────────▼──────────────────────────────────────────────▼───────────┐
        │                        Server (Ubuntu + Docker)                               │
        │                                                                                │
        │  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────────────────┐  │
        │  │   bot        │   │   dashboard      │   │   webapp (nginx)              │  │
        │  │  (Python)    │   │   (FastAPI)      │   │   /app/ → React SPA           │  │
        │  │              │   │   :8080          │   │   /api/ → proxy → :8080       │  │
        │  │  PTB polling │   │   /admin/* (UI)  │   │   :5174                       │  │
        │  │  Schedulers  │   │   /api/miniapp/* │   │                               │  │
        │  └──────┬───────┘   └────────┬─────────┘   └───────────────────────────────┘  │
        │         │                    │                                                 │
        │         └──────────┬─────────┘                                                 │
        │                    │ async psycopg pool                                        │
        │         ┌──────────▼──────────┐         ┌──────────────────────────┐         │
        │         │   PostgreSQL 16     │         │   AI Providers (cloud)    │         │
        │         │   (native, port     │         │                           │         │
        │         │    5432, host)      │         │   Gemini 2.0 Flash → Groq │         │
        │         │                     │         │   (Llama 3.3 70B)         │         │
        │         │   network_mode:host │         │                           │         │
        │         └─────────────────────┘         └──────────────────────────┘         │
        │                                                                                │
        └────────────────────────────────────────────────────────────────────────────────┘
                                                ▲
                                                │
                                       Cloudflare Tunnel
                                       (cloudflared agent)
                                       www.botbudget.it (admin)
                                       app.botbudget.it (miniapp prod)
                                       app-staging.botbudget.it
```

### المبادئ المعمارية
1. **Layered architecture:** `handlers → services → repositories → db`. كل طبقة تخدم اللي فوقها فقط.
2. **Async everywhere:** `asyncio` + `psycopg` async pool (no blocking I/O in hot path).
3. **Decorator-based access control:** `@authorized_only`, `@check_plan_limit`, `@premium_only`, `@admin_only`, `@rate_limited`.
4. **Single source of truth for config:** `config.py` يقرأ من `.env` (12-factor).
5. **Repositories own SQL:** الـ handlers/services لا تكتب SQL مباشرة.
6. **AI fallback chain:** Gemini → Groq (Llama 3) عند فشل/استنفاد Gemini.

---

## 4. التقنيات المستخدمة

### Backend (Bot + Dashboard)
| التقنية | الإصدار | الاستخدام |
|---|---|---|
| Python | 3.11+ | لغة الـ runtime |
| python-telegram-bot (PTB) | v21+ | البوت + ConversationHandler + JobQueue |
| FastAPI | latest | Dashboard + Mini App API |
| psycopg | v3 (async) | اتصال Postgres عبر AsyncConnectionPool |
| APScheduler | — | Daily/weekly cron jobs (يستخدم PTB JobQueue) |
| google-generativeai | — | Gemini 2.0 Flash للتحليل |
| groq | — | Fallback (Llama 3.3 70B) |
| python-dotenv | — | تحميل `.env` |
| Jinja2 | — | قوالب الـ admin dashboard |
| matplotlib + pandas | — | الرسوم البيانية + تحليلات |
| openpyxl + reportlab | — | تصدير Excel/CSV |
| alembic | — | DB migrations |

### Frontend (Mini App)
| التقنية | الاستخدام |
|---|---|
| React 18 | UI framework |
| Vite | Build tool |
| TypeScript | Type safety |
| TailwindCSS | Styling (RTL) |
| `@telegram-apps/sdk-react` | Telegram WebApp integration |
| axios | HTTP client |
| recharts | Pie/Line charts |
| react-router-dom | Client-side routing |

### Infrastructure
| التقنية | الاستخدام |
|---|---|
| Docker + Compose | عزل الخدمات + التشغيل |
| nginx (alpine) | يخدم الـ React SPA + يعمل proxy لـ `/api` |
| PostgreSQL 16 | DB (native على الـ host، ليس Docker) |
| Cloudflare Tunnel | DNS + TLS + reverse proxy |
| Tailscale | SSH للسيرفر (`hamed.tail5fa62e.ts.net`) |

---

## 5. هيكل المستودع

```
BotBudget/
├── ai/                          # AI parsing layer
│   └── gemini_parser.py        # Gemini → Groq fallback
│
├── alembic/                     # DB migrations
│   ├── env.py
│   └── versions/
│       ├── ac1d4ded0b09_initial_schema.py
│       ├── b2f3a1c4d5e6_add_expense_history.py
│       ├── c3d4e5f6a7b8_add_rate_limit_log.py
│       └── d4e5f6a7b8c9_add_allowed_users.py
│
├── dashboard/                   # FastAPI admin UI + Mini App API
│   ├── main.py                 # App factory + middleware + lifespan
│   ├── auth.py                 # Admin session auth (cookies)
│   ├── miniapp_auth.py         # Telegram initData HMAC verification
│   ├── queries.py              # Aggregate SQL for admin views
│   ├── routers/
│   │   ├── landing.py          # Public landing page
│   │   ├── overview.py         # Stats overview
│   │   ├── users.py            # User list
│   │   ├── subscribers.py      # Subscription management
│   │   ├── broadcast.py        # Send messages to all
│   │   ├── data_mgmt.py        # Backup / export
│   │   └── miniapp.py          # /api/miniapp/* JSON endpoints
│   ├── templates/              # Jinja2 HTML
│   └── static/
│
├── db/
│   ├── connection.py           # AsyncConnectionPool init/close/get
│   └── init_db.py              # Bootstraps tables on startup
│
├── handlers/                    # Telegram command handlers
│   ├── start_handler.py        # /start /help /myid /plan /upgrade_info
│   ├── expense_handler.py      # NLP entry, /today /week /month /balance,
│   │                           # /edit /delete /undo /search /report /compare
│   ├── budget_handler.py       # /budget /setbudget
│   ├── recurring_handler.py    # /recurring /add_recurring /delete_recurring
│   ├── chart_handler.py        # /chart /chart_week
│   ├── insights_handler.py     # /insights (AI-powered)
│   ├── export_handler.py       # /export_csv /export_excel
│   ├── currency_handler.py     # /currency
│   ├── legal_handler.py        # /about /terms /privacy
│   └── admin_handler.py        # /adduser /upgrade /broadcast /subscribers ...
│
├── models/                      # Domain models (dataclasses)
│   ├── expense.py
│   └── recurring.py
│
├── repositories/                # SQL data access layer
│   ├── user_repo.py
│   ├── expense_repo.py         # CRUD + audit trail (expense_history)
│   ├── budget_repo.py
│   ├── recurring_repo.py
│   ├── subscription_repo.py    # plans + trial + month-tx-count
│   └── allowed_users_repo.py   # legacy whitelist (deprecated)
│
├── security/
│   ├── auth.py                 # @authorized_only, @check_plan_limit,
│   │                           # @premium_only, @admin_only
│   └── rate_limiter.py         # @rate_limited (sliding window)
│
├── services/                    # Business logic (orchestrate repos + AI)
│   ├── expense_service.py
│   ├── budget_service.py
│   ├── recurring_service.py
│   ├── chart_service.py
│   ├── insights_service.py
│   └── export_service.py
│
├── tests/                       # pytest
│   ├── ai/
│   ├── models/
│   ├── services/
│   ├── unit/
│   └── conftest.py
│
├── utils/
│   └── logger.py
│
├── webapp/                      # React Mini App (v1.3, NEW)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   └── AddTransaction.tsx
│   │   ├── components/BottomNav.tsx
│   │   ├── lib/api.ts          # axios + initData header injection
│   │   ├── lib/telegram.ts     # SDK init + theme vars
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── Dockerfile              # multi-stage (node build → nginx serve)
│   ├── nginx.conf.template     # envsubst template (PORT-aware)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── main.py                      # Bot entry point
├── config.py                    # Env-driven settings
├── requirements.txt             # prod deps
├── requirements-dev.txt         # test deps
├── pytest.ini
├── alembic.ini
├── Dockerfile                   # bot + dashboard (shared image)
├── docker-compose.yml           # production
├── docker-compose.staging.yml   # staging
├── README.md
├── ROADMAP.md
└── HANDOVER.md                  # ← هذا الملف
```

---

## 6. مخطط قاعدة البيانات

### الجداول الأساسية

```sql
-- المستخدمون
users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    first_name      VARCHAR(100),
    language        VARCHAR(10) DEFAULT 'ar',
    currency        VARCHAR(5) DEFAULT 'EUR',
    created_at      TIMESTAMPTZ DEFAULT NOW()
)

-- المعاملات (دخل/مصروف)
expenses (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    type            VARCHAR(10) CHECK (type IN ('expense','income')),
    amount          NUMERIC(12,2),
    currency        VARCHAR(5) DEFAULT 'EUR',
    category        VARCHAR(50),
    description     TEXT,
    date            DATE DEFAULT CURRENT_DATE,
    raw_text        TEXT,                  -- النص الأصلي قبل تحليل AI
    created_at      TIMESTAMPTZ DEFAULT NOW()
)
INDEX idx_expenses_user_date ON (user_id, date)
INDEX idx_expenses_category  ON (user_id, category)

-- سجل التعديلات (audit trail)
expense_history (
    id              SERIAL PRIMARY KEY,
    expense_id      INT,
    user_id         BIGINT,
    action          VARCHAR(20),  -- create / update / delete
    old_data        JSONB,
    new_data        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
)

-- المدفوعات المتكررة
recurring_payments (
    id                 SERIAL PRIMARY KEY,
    user_id            BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    name               VARCHAR(100),
    amount             NUMERIC(12,2),
    currency           VARCHAR(5) DEFAULT 'EUR',
    frequency          VARCHAR(20) CHECK (frequency IN ('daily','weekly','monthly','yearly')),
    next_due_date      DATE,
    remind_days_before INT DEFAULT 1,
    active             BOOLEAN DEFAULT TRUE,
    created_at         TIMESTAMPTZ DEFAULT NOW()
)

-- الميزانيات
budgets (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    category        VARCHAR(50),
    limit_amount    NUMERIC(12,2),
    UNIQUE (user_id, category)
)

-- الاشتراكات (Free/Premium)
subscriptions (
    user_id         BIGINT PRIMARY KEY,
    plan            VARCHAR(20) DEFAULT 'free',  -- 'free' | 'premium'
    started_at      TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    upgraded_by     BIGINT
)

-- سجل تحديد المعدّل (Rate limiting)
rate_limit_log (
    user_id         BIGINT,
    action          VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW()
)

-- قائمة بيضاء قديمة (deprecated بعد فتح التسجيل الذاتي)
allowed_users (
    user_id     BIGINT PRIMARY KEY,
    first_name  VARCHAR(100),
    added_by    BIGINT,
    added_at    TIMESTAMPTZ DEFAULT NOW()
)
```

### العلاقات
- `expenses.user_id → users.telegram_id`
- `recurring_payments.user_id → users.telegram_id`
- `budgets.user_id → users.telegram_id`
- `subscriptions.user_id → users.telegram_id` (logical, not enforced)
- `expense_history.expense_id → expenses.id` (logical)

### Migrations
المهاجرات بترتيب:
1. `ac1d4ded0b09_initial_schema` → users, expenses, recurring, budgets
2. `b2f3a1c4d5e6_add_expense_history` → audit trail
3. `c3d4e5f6a7b8_add_rate_limit_log` → rate limiting
4. `d4e5f6a7b8c9_add_allowed_users` → legacy whitelist
5. (subscriptions table) — يُنشأ تلقائياً عبر `db/init_db.py` على الـ startup

---

## 7. الميزات حسب الإصدار

### v1.0 — Core (Live)
- إدخال معاملات بـ NLP (Gemini)
- تقارير: `/today`, `/week`, `/month`, `/balance`, `/last`
- بحث + تعديل + حذف + undo
- ميزانيات بالفئة + تنبيهات تجاوز
- مدفوعات متكررة + تذكيرات
- رسوم بيانية (matplotlib)
- تحليل ذكي `/insights`
- مقارنات شهرية `/compare`
- تقارير مخصصة `/report`
- تصدير CSV / Excel
- تنبيه يومي + تقرير أسبوعي

### v1.1 — Robustness (Live)
- AI fallback chain (Gemini → Groq)
- Rate limiting (30 msg/min)
- Audit trail (expense_history)
- Self-service registration (لا يلزم whitelist)

### v1.2 — Plan Tiers + Trial (Live, Apr 2026)
- Free vs Premium tiers:
  - Free: 30 معاملة/شهر، ميزانية واحدة، دفعتين متكررتين
  - Premium: بلا حدود
- مميزات Premium حصرية: `/chart`, `/chart_week`, `/insights`, `/compare`, `/report`, `/export_*`, التقرير الأسبوعي
- التنبيه اليومي **مجاني للجميع**
- تجربة Premium 7 أيام تلقائياً للمستخدمين الجدد
- Quick buttons بعد كل معاملة
- `/broadcast` للأدمن

### v1.2.1 — Security Patch (Live)
- تفعيل Prompt Injection filter (`_DANGEROUS_PATTERNS`)
- تقوية `_clean_json_response` (regex لاستخراج JSON)
- استخدام `DEFAULT_CURRENCY` من config

### v1.3 — Telegram Mini App (Staging)
- ✅ FastAPI endpoints تحت `/api/miniapp/*` مع HMAC auth
- ✅ React + Vite + TS frontend (RTL Arabic)
- ✅ Dashboard / Transactions / Add Transaction / Pie chart
- ✅ Cloudflare Tunnel routing
- ⏳ في انتظار اختبار شامل قبل الترقية للإنتاج

### v1.4 — Planned
- نظام دفع آلي (Telegram Stars MVP أو Stripe)
- 30-day history limit للـ Free (مؤجّل من v1.2)
- Mini App: Budgets + Recurring + Export pages
- نقل DB لـ Docker network (إزالة `network_mode: host`)
- تحديث `google-generativeai` → `google-genai` (الحالي deprecated)

---

## 8. الأنظمة الفرعية

### 8.1 البوت (Telegram Bot)

**الملف الرئيسي:** `main.py`

**نمط التشغيل:** Long Polling (مش Webhook). أبسط للنشر، بدون SSL termination منفصل.

**المكوّنات:**
- `Application` builder من `python-telegram-bot`
- `CommandHandler` لكل أمر `/...`
- `MessageHandler(filters.TEXT)` للنص الحر (يستدعي AI parser)
- `ConversationHandler` للـ flows متعددة الخطوات (إضافة ميزانية، تعديل معاملة...)
- `CallbackQueryHandler` لأزرار الـ inline
- `JobQueue` للجدولة:
  - `send_daily_report` (الساعة 21:00 UTC)
  - `send_weekly_report` (الجمعة، Premium فقط)
  - `send_reminders` (للمدفوعات المتكررة المستحقة)
  - `cleanup_rate_limits` (كل ساعة)

**نقاط مهمة:**
- كل الـ handlers مغلّفة بـ `@authorized_only` على الأقل (تسجّل المستخدم تلقائياً + تمنح trial).
- الـ jobs ملفوفة بـ try/except عشان فشل واحد ما يوقّفش البوت.

### 8.2 محلل الذكاء الاصطناعي (AI Parser)

**الملف:** `ai/gemini_parser.py`

**الواجهة:**
```python
parse_transaction(text: str, user_currency: str) -> dict
parse_recurring(text: str) -> dict
```

**Pipeline:**
1. `_sanitize_input` — قص لـ 500 حرف، إزالة control chars، تحييد كلمات الـ prompt injection (ignore/system/jailbreak/...).
2. بناء system prompt مع `{today}` و `{currency}`.
3. `_parse_with_fallback`:
   - أولاً: Gemini 2.0 Flash (model: `gemini-2.0-flash`)
   - عند فشل (أي exception): Groq (`llama-3.3-70b-versatile`)
4. `_clean_json_response` — regex `\{.*\}` لاستخراج أول JSON object من الرد.
5. `json.loads` + return.

**خرج متوقّع:**
```json
{"type":"expense","amount":50,"currency":"EUR","category":"سوبرماركت",
 "description":"...","date":"2026-04-21","confidence":0.9}
```
أو `{"error":"unclear","question":"..."}` لو الموديل مش متأكد.

**Prompt الكامل** موجود كـ string ثابت داخل الملف نفسه (`_SYSTEM_PROMPT`، `_RECURRING_PROMPT_TEMPLATE`). فيه قواعد مفصّلة للتواريخ النسبية ("امبارح"، "الأسبوع اللي فات") والعملات والفئات.

### 8.3 طبقة البيانات (Repositories)

**النمط:** Repository per aggregate. كل repo يملك SQL لجدوله.

**المشترك:**
```python
async with pool.connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        ...
    await conn.commit()
```

**الـ repos الرئيسية:**
- `UserRepository.ensure_user(user_id, first_name)` — UPSERT
- `ExpenseRepository.add/update/delete/get_by_date_range/search_by_text` — مع audit trail
- `BudgetRepository.set_budget/get_budget/get_all_budgets/check_overspend`
- `RecurringRepository.add/get_all/delete/get_due`
- `SubscriptionRepository.ensure_free/grant_trial_if_new/get_plan/upgrade/downgrade/count_month_transactions`

**ملاحظة:** الـ services أحياناً تشير للـ repo بأسماء مختلفة:
- `BudgetService.budget_repo` ✅
- `RecurringService.repo` ✅ (مختلف عن البودجت)

### 8.4 نظام الاشتراكات (Subscriptions)

**Decorators (في `security/auth.py`):**

| Decorator | الوظيفة | يجب أن يأتي بعد |
|---|---|---|
| `@authorized_only` | تسجيل تلقائي + منح trial | (الأول دائماً) |
| `@rate_limited` | 30 رسالة/60 ثانية | `@authorized_only` |
| `@check_plan_limit` | حد 30 معاملة/شهر للـ Free | `@authorized_only` |
| `@premium_only("feature")` | يمنع Free من الميزة + يعرض زر ترقية | `@authorized_only` |
| `@admin_only` | محصور في `ADMIN_USER_IDS` | (مستقل) |

**الترتيب الصحيح:**
```python
@authorized_only
@rate_limited
@premium_only("الرسوم البيانية")
async def chart_command(update, context): ...
```

**حدود الخطة المجانية (Constants in `auth.py`):**
- `FREE_MONTHLY_LIMIT = 30`
- `FREE_BUDGET_LIMIT = 1`
- `FREE_RECURRING_LIMIT = 2`
- `TRIAL_DAYS = 7`

**Trial logic:**
- داخل `@authorized_only`، نستدعي `grant_trial_if_new(user_id)` الذي يحاول `INSERT ... ON CONFLICT DO NOTHING RETURNING user_id`. لو رجع row → مستخدم جديد، Trial ممنوح.
- نضع `context.user_data["_trial_just_granted"] = True` ليعرض onboarding خاص.

### 8.5 Admin Dashboard

**الـ URL:** `https://www.botbudget.it/admin/...`

**الصفحات:**
- `/admin/overview` — إحصائيات (مستخدمين، معاملات، اشتراكات)
- `/admin/users` — قائمة المستخدمين
- `/admin/subscribers` — إدارة الاشتراكات (ترقية يدوية)
- `/admin/broadcast` — إرسال رسالة لكل المشتركين
- `/admin/data-mgmt` — backups / export

**Auth:** Cookie-based session (تفاصيل في `dashboard/auth.py`).

**التقنية:** Jinja2 templates + Alpine.js (أو vanilla) — مش SPA.

### 8.6 Mini App (v1.3 - NEW)

**Backend** (`dashboard/routers/miniapp.py`):

| Endpoint | الوظيفة |
|---|---|
| `GET /api/miniapp/me` | بيانات المستخدم + خطته |
| `GET /api/miniapp/dashboard` | الرصيد + ملخص الشهر + آخر 5 معاملات |
| `GET /api/miniapp/transactions?limit=&offset=&q=` | قائمة المعاملات + بحث |
| `POST /api/miniapp/transactions` | إنشاء معاملة |
| `DELETE /api/miniapp/transactions/{id}` | حذف (ownership-checked) |
| `GET /api/miniapp/categories/summary?period=month` | تجميع للـ pie chart |

**Auth:** كل endpoint يعتمد على `Depends(get_current_user)` الذي يقرأ `X-Telegram-Init-Data` header ويتحقق منه عبر HMAC-SHA256 ضد `BOT_TOKEN` (المرجع: [Telegram WebApps validation spec](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)).

**CORS:** مفعّل فقط لمسارات `/api/miniapp/*` ومحصور في:
- `https://app.botbudget.it`
- `https://app-staging.botbudget.it`
- `http://localhost:5173` (dev)

**Frontend** (`webapp/src/`):
- `lib/telegram.ts` — يهيئ Telegram SDK، يستخرج `initDataRaw`، يعرض المستخدم.
- `lib/api.ts` — axios instance مع interceptor يضيف header `X-Telegram-Init-Data` تلقائياً.
- `pages/Dashboard.tsx` — كروت + recharts pie chart.
- `pages/Transactions.tsx` — قائمة + بحث + حذف.
- `pages/AddTransaction.tsx` — فورم.
- التيمز عبر CSS variables (`var(--tg-theme-bg-color)` ...) — يتبع تيمز تيليجرام (دارك/فاتح) تلقائياً.

**Deployment:**
- Service `webapp` في docker-compose، nginx يخدم build dist + يعمل proxy لـ `/api`.
- Cloudflare Tunnel: `app.botbudget.it` → `localhost:5174` (prod) / `localhost:5175` (staging).
- BotFather: Menu Button → `https://app.botbudget.it/app/`.

---

## 9. النشر والبيئات

### البيئات

| البيئة | Branch | Compose File | DB | Bot | Dashboard | Webapp |
|---|---|---|---|---|---|---|
| Production | `main` | `docker-compose.yml` | `bot_budget` | `@Mybudgettracke_bot` | `:8080` | `:5174` |
| Staging | `feature/v1.2` | `docker-compose.staging.yml` | `bot_budget_staging` | `@botbudgettest_bot` | `:8081` | `:5175` |

### دورة حياة الإصدار
```
feature/* branch
    ↓ (merge / push)
feature/v1.2 (staging)
    ↓ (deploy + test on @botbudgettest_bot)
main (production)
    ↓ (manual SSH + git pull + docker compose up -d --build)
@Mybudgettracke_bot
```

### أوامر النشر اليدوية

**Staging:**
```bash
ssh hamed@hamed.tail5fa62e.ts.net
cd ~/BotBudget
git checkout feature/v1.2 && git pull
docker compose -f docker-compose.staging.yml up -d --build
docker compose -f docker-compose.staging.yml logs --tail=30 bot-staging
```

**Production:**
```bash
cd ~/BotBudget
git checkout main && git pull
docker compose up -d --build
docker compose logs --tail=30 bot
```

### ⚠️ ملاحظات عن الـ Networking
- كل الـ services تستخدم `network_mode: host` (قرار مقصود).
- السبب: الـ Postgres يعمل **native** على الـ host (PID 1218)، مش داخل Docker، والبوت يتصل بـ `localhost:5432`.
- الـ Docker container `botbudget_db` (في `docker-compose.yml`) **غير مستخدم فعلياً** ويجب حذفه في v1.4.
- البديل النظيف (مؤجّل): نقل Postgres لـ Docker + استخدام bridge network.

### Cloudflare Tunnel
- Tunnel name: `botbudget`
- Tunnel ID: `dc8e1274-226e-4c39-93a6-9093d6c1b7ea`
- Routes:
  - `www.botbudget.it` → `localhost:8080` (admin dashboard)
  - `app-staging.botbudget.it` → `localhost:5175` (miniapp staging)
  - `app.botbudget.it` → `localhost:5174` (miniapp prod) — **يضاف عند ترقية v1.3**

### Backups
- يدوي حالياً (يجب أتمتته في v1.4).
- مكان البيانات: native Postgres على `/var/lib/postgresql/16/main/`.

---

## 10. الأمان

### المصادقة (Authentication)

| الواجهة | الآلية |
|---|---|
| البوت | Telegram delivers `update.effective_user`; نسجّل تلقائياً |
| Admin Dashboard | session cookie (في `dashboard/auth.py`) |
| Mini App | HMAC-SHA256 على `initData` من Telegram (في `miniapp_auth.py`) |

### الصلاحيات (Authorization)
- **ADMIN_USER_IDS** في `.env` (comma-separated). كل أمر admin يستخدم `@admin_only`.
- **Plan tiers** يفرضها `@premium_only`، `@check_plan_limit`.
- **Ownership check** في Mini App: `DELETE /transactions/{id}` يتحقق من `user_id` قبل الحذف.

### Prompt Injection Defense (v1.2.1)
في `ai/gemini_parser.py`:
```python
_DANGEROUS_PATTERNS = re.compile(
    r"\b(ignore|forget|disregard|override|system\s+prompt|"
    r"instructions?|you\s+are|act\s+as|pretend|roleplay|jailbreak|"
    r"developer\s+mode|admin\s+mode)\b",
    re.IGNORECASE,
)
```
لو وُجدت → استبدال بـ `[filtered]` + warning log.

### Rate Limiting
`@rate_limited` في `security/rate_limiter.py`:
- 30 رسالة لكل 60 ثانية لكل user
- مخزّن في جدول `rate_limit_log`
- تنظيف تلقائي كل ساعة عبر job

### الأسرار (Secrets)
- يتم تخزينها فقط في `.env` (و `.env.staging`) على السيرفر.
- ❌ **لا تُرفع لـ Git** (مدرجة في `.gitignore`).
- المفاتيح المطلوبة:
  - `TELEGRAM_BOT_TOKEN`
  - `GEMINI_API_KEY`
  - `GROQ_API_KEY`
  - `DB_*` (host/port/name/user/pass)
  - `ADMIN_USER_IDS`

### مخاوف معروفة
1. **`network_mode: host`** يقلل عزل Docker (راجع [الديون التقنية](#13-الديون-التقنية)).
2. **Public repo**: لا يجب أبداً إضافة self-hosted GitHub runners.
3. **HTTPS**: تنتهي عند Cloudflare; حركة `Cloudflare → Tunnel → localhost` آمنة عبر nغ Tailscale-like layer من `cloudflared`.

---

## 11. الإعدادات

### Environment Variables (`.env`)

```bash
# Telegram
TELEGRAM_BOT_TOKEN=<from BotFather>

# AI providers
GEMINI_API_KEY=<from Google AI Studio>
GROQ_API_KEY=<from console.groq.com>  # optional fallback

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bot_budget               # bot_budget_staging for staging
DB_USER=botbudget_user
DB_PASS=<strong password>

# Security
ADMIN_USER_IDS=123456789,987654321  # Telegram user IDs of admins
ALLOWED_USER_IDS=                    # legacy, leave empty

# Rate limiting
RATE_LIMIT_MESSAGES=30
RATE_LIMIT_WINDOW_SECONDS=60

# Environment marker
ENVIRONMENT=production  # or "staging"

# Dashboard
DASHBOARD_PREFIX=/admin
```

### تشغيل محلي (Dev)

**Backend:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python main.py             # bot
uvicorn dashboard.main:app --reload --port 8080  # dashboard
```

**Frontend (Mini App):**
```bash
cd webapp
npm install
npm run dev                # http://localhost:5173
# الـ Vite proxy يحوّل /api → http://localhost:8080
```

---

## 12. الاختبارات

### الموجود
- `tests/ai/` — اختبارات لـ gemini parser (mocked)
- `tests/services/` — services
- `tests/models/` — domain models
- `tests/unit/` — utilities
- `pytest.ini` يضبط asyncio mode

**التشغيل:**
```bash
pip install -r requirements-dev.txt
pytest -q
```

### الفجوات (Gaps)
- ❌ Integration tests للـ DB (تحتاج fixtures + test DB).
- ❌ Bot handler tests (تحتاج mocking `Update`/`Context`).
- ❌ Mini App E2E (Playwright/Cypress).
- ❌ Frontend unit tests.
- ❌ CI runner (الـ tests محلية فقط).

---

## 13. الديون التقنية

> هذه القائمة مشتقة من Code Review في 2026-04-27، وكلها مرشحة لـ v1.4+.

| # | المشكلة | الموقع | التأثير | الأولوية |
|---|---|---|---|---|
| 1 | `network_mode: host` يلغي عزل Docker | `docker-compose.yml` | أمان متوسط | 🟡 |
| 2 | container `botbudget_db` غير مستخدم (DB native) | `docker-compose.yml` | حيرة وقت الـ debug | 🟢 |
| 3 | `google-generativeai` مهجور (deprecated) | `ai/gemini_parser.py` | يعمل لكن بدون updates | 🟡 |
| 4 | لا يوجد CI/CD آلي | `.github/workflows/` (محذوف) | deploy يدوي عرضة للخطأ | 🟡 |
| 5 | لا توجد integration tests للـ DB | `tests/` | regressions ممكنة | 🟡 |
| 6 | الترقية يدوية (مفيش payment gateway) | — | scaling محدود | 🔴 (عمل تجاري) |
| 7 | لا يوجد backup آلي للـ DB | infra | فقدان بيانات محتمل | 🔴 |
| 8 | لا يوجد monitoring/alerting | infra | downtime يكتشف متأخر | 🟡 |
| 9 | Mini App MVP فقط (لا Budgets/Recurring) | `webapp/src/pages/` | ميزة ناقصة | 🟢 |
| 10 | TODO: 30-day history limit للـ Free | `repositories/expense_repo.py` | حد مؤجّل من v1.2 | 🟢 |

---

## 14. خريطة الطريق

### v1.4 — Stability + Payments (Q3 2026)
- [ ] Payment gateway: Telegram Stars (MVP) أو Stripe
- [ ] PostgreSQL backup script (cron + S3/Backblaze)
- [ ] Monitoring: Uptime Kuma أو healthcheck.io
- [ ] هجرة `google-generativeai` → `google-genai`
- [ ] إزالة `botbudget_db` Docker service غير المستخدم
- [ ] Mini App pages إضافية: Budgets / Recurring / Reports

### v1.5 — Multi-currency + Sharing
- [ ] دعم محافظ متعددة لكل مستخدم
- [ ] عمل تحويلات بين العملات (rate API)
- [ ] مشاركة ميزانية بين عدة مستخدمين (عائلي)

### v1.6 — Insights++
- [ ] AI Coach (نصائح ادخارية أسبوعية)
- [ ] استيراد من بنوك (CSV → AI categorization)
- [ ] PDF reports جميلة

---

## 15. دليل التسليم لكل فريق

### 🔧 Backend Engineer

**المهام الفورية:**
1. اقرأ `main.py` + `handlers/start_handler.py` + `security/auth.py`. (تفاهم الـ decorator chain)
2. شغّل `alembic upgrade head` على DB محلية فاضية.
3. شغّل `pytest -q` ولاحظ الفجوات.
4. ابدأ بمشكلة #6 (payment gateway) — التصميم أولاً (RFC) قبل الكود.

**ملفات يجب فهمها قبل التعديل:**
- `security/auth.py` — كل الـ access control
- `repositories/subscription_repo.py` — منطق الخطط
- `ai/gemini_parser.py` — الـ AI pipeline

**معايير الجودة:**
- استخدم `from utils.logger import get_logger` بدلاً من `print`.
- الـ SQL في الـ repos فقط، مش في الـ handlers/services.
- `async def` كل I/O. لا استخدام `requests`/`time.sleep`.
- type hints كاملة على الواجهات العامة.

### 🎨 Frontend Engineer (Mini App)

**المهام الفورية:**
1. اقرأ `webapp/src/lib/telegram.ts` و `webapp/src/lib/api.ts`.
2. شغّل `npm run dev` محلياً (متطلب: backend شغال).
3. اختبر الـ Mini App على staging (`@botbudgettest_bot`).
4. ابدأ بمشكلة #9: إضافة صفحات Budgets / Recurring (نفس النمط).

**ملفات يجب فهمها قبل التعديل:**
- `webapp/src/App.tsx` — Router + layout
- `webapp/src/components/BottomNav.tsx`
- Theme variables في `index.css` (تتبع تيمز تيليجرام)

**معايير الجودة:**
- RTL أولاً (`dir="rtl"` في الـ root).
- استخدم `var(--tg-theme-*-color)` بدل ألوان hardcoded.
- لا تخزن `initData` في localStorage — يُرسل في كل طلب.
- Loading states + error boundaries لكل صفحة.

### ⚙️ DevOps / SRE

**المهام الفورية:**
1. أنشئ backup cron للـ Postgres (مشكلة #7).
2. ركّب Uptime Kuma أو ما يكافئه (مشكلة #8).
3. خطّط هجرة DB لـ Docker (مشكلة #1) — يحتاج downtime مخطّط.
4. عاود تفكير CI/CD (مشكلة #4) — اقتراح: GitHub Actions + Tailscale + repo secrets كاملة.

**ملفات يجب فهمها:**
- `Dockerfile`, `docker-compose.yml`, `docker-compose.staging.yml`
- `webapp/Dockerfile`, `webapp/nginx.conf.template`
- وثيقة Cloudflare Tunnel (داخلية، عند المالك)

### 🧪 QA Engineer

**المهام الفورية:**
1. ابني test plan شامل من ميزات v1.0–v1.3 (انظر [القسم 7](#7-الميزات-حسب-الإصدار)).
2. اكتب smoke tests للـ Mini App عبر Playwright.
3. اختبارات يدوية للـ AI parsing على نطاق واسع (مجموعة رسائل عربية متنوعة).
4. اختبر تدفّقات الترقية اليدوية + Trial.

**ملاحظات:**
- بيئة الاختبار: `@botbudgettest_bot` + `app-staging.botbudget.it`.
- الـ DB: `bot_budget_staging` (يمكن مسحها بدون مشاكل).

### 🔐 Security Engineer

**المهام الفورية:**
1. مراجعة `dashboard/miniapp_auth.py` (HMAC validation) — تأكد من `max_age` enforcement وعدم وجود timing leaks.
2. مراجعة `ai/gemini_parser.py` `_DANGEROUS_PATTERNS` — هل يغطي كل أنماط الـ injection العربية والإنجليزية؟
3. فحص `security/auth.py` — race conditions في `grant_trial_if_new` (هل يمكن استغلالها لمنح trial متكرر)؟
4. تدقيق `dashboard/auth.py` (admin sessions) — CSRF, secure cookies, session expiry.
5. تأكد من sanitization على المدخلات الموصولة بـ SQL في الـ repos (نستخدم parametrized queries، لكن تأكد).

### 📊 Product Manager

**المعروف:**
- 7-day trial → بحاجة قياس الـ conversion للـ paid.
- التنبيه اليومي مجاني، الأسبوعي Premium → افحص الأثر على retention.
- لا توجد analytics مدمج (لا Mixpanel/Amplitude).

**التوصيات:**
- إضافة Plausible/Umami للـ Mini App.
- أحداث مهمة لتتبعها: signup, first transaction, trial-end, premium-upgrade, churn.

---

## 16. الملاحق

### الأوامر الإدارية للأدمن (داخل البوت)

| الأمر | الوظيفة |
|---|---|
| `/adduser <id> [name]` | (legacy) إضافة لقائمة الأذونات |
| `/removeuser <id>` | (legacy) حذف |
| `/users` | قائمة المستخدمين |
| `/upgrade <id> [days=30]` | ترقية يدوية لـ Premium |
| `/downgrade <id>` | إنزال للخطة المجانية |
| `/subscribers` | قائمة المشتركين |
| `/broadcast` | معاينة الرسالة (نص v1.2 ثابت حالياً) |
| `/broadcast confirm` | إرسال البث للجميع |

### روابط مهمة

| | URL |
|---|---|
| Repo (Public) | https://github.com/mohamdhamed/BotBudget |
| Production Bot | https://t.me/Mybudgettracke_bot |
| Staging Bot | https://t.me/botbudgettest_bot |
| Production Admin | https://www.botbudget.it/admin |
| Staging Mini App | https://app-staging.botbudget.it/app/ |
| Cloudflare Dashboard | https://one.dash.cloudflare.com |
| Server SSH | `hamed@hamed.tail5fa62e.ts.net` (Tailscale) |

### Checklist تسليم
- [ ] الفريق حصل على وصول للـ repo (read أو write حسب الدور)
- [ ] الفريق حصل على نسخة `.env.example` (تخزين الـ secrets الفعلية في password manager مشترك)
- [ ] الفريق حصل على وصول SSH للسيرفر (مفاتيح ed25519 منفصلة لكل مهندس)
- [ ] الفريق حصل على وصول لـ Cloudflare team (Member مع صلاحيات محدودة)
- [ ] جلسة onboarding (1 ساعة) مع شرح [القسم 8](#8-الأنظمة-الفرعية)
- [ ] حساب admin Telegram لكل مهندس (إضافة `user_id` في `ADMIN_USER_IDS`)

### كلمة أخيرة
المشروع مكتوب بأسلوب Clean Architecture قابل للتطوير. الميزات الجديدة المفترض تُضاف عبر إضافة handler/service/repo بنفس النمط، بدون كسر الموجود. أي مساهم يجب يقرأ على الأقل: `main.py`, `handlers/start_handler.py`, `security/auth.py`, واحد من الـ repos.

</div>

---
*آخر تحديث: 2026-04-27 · الإصدار: v1.3 (Mini App MVP on staging)*
