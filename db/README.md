# 🗄️ Database Layer

طبقة قاعدة البيانات المسؤولة عن الاتصال بـ PostgreSQL وإنشاء الجداول.

## الملفات
| الملف | الوصف |
|---|---|
| `connection.py` | إدارة Connection Pool |
| `init_db.py` | إنشاء الجداول (Schema) |

## الجداول
- `users` - بيانات المستخدمين
- `expenses` - المعاملات المالية
- `recurring_payments` - المدفوعات المتكررة
- `budgets` - حدود الميزانية بالفئة

## الاستخدام
```python
from db.connection import init_pool, get_connection, release_connection

init_pool()
conn = get_connection()
# ... use connection ...
release_connection(conn)
```
