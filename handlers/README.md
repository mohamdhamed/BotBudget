# 📡 Handlers

طبقة العرض. كل Handler يستقبل رسائل تيليجرام ويوجهها للـ Service المناسب.

## الملفات
| الملف | الوصف |
|---|---|
| `start_handler.py` | أوامر `/start`, `/help`, `/myid` |
| `expense_handler.py` | معالجة النصوص + `/today`, `/month`, `/delete` |
| `recurring_handler.py` | `/recurring`, `/add_recurring`, `/delete_recurring` |
| `export_handler.py` | `/export_csv`, `/export_excel` |
