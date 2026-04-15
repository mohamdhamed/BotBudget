"""
dashboard/queries.py
---------------------
SQL queries for the admin dashboard — read-mostly.
All functions use the shared async DB pool from db.connection.
"""

from datetime import date, timedelta

from db.connection import get_pool


async def get_overview_stats() -> dict:
    """High-level stats for the dashboard home page."""
    pool = get_pool()
    today = date.today()
    month_start = date(today.year, today.month, 1)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Total users
            await cur.execute("SELECT COUNT(*) FROM users;")
            total_users = (await cur.fetchone())[0]

            # Users by plan
            await cur.execute(
                "SELECT plan, COUNT(*) FROM subscriptions GROUP BY plan;"
            )
            plan_counts = {r[0]: r[1] for r in await cur.fetchall()}
            premium = plan_counts.get("premium", 0)
            free = plan_counts.get("free", 0)

            # Transactions today
            await cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE date = %s AND type='expense';",
                (today,),
            )
            row = await cur.fetchone()
            tx_today, sum_today = row[0], float(row[1])

            # Transactions this month
            await cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE date >= %s AND type='expense';",
                (month_start,),
            )
            row = await cur.fetchone()
            tx_month, sum_month = row[0], float(row[1])

            # New users last 7 days
            await cur.execute(
                "SELECT COUNT(*) FROM users WHERE created_at >= %s;",
                (today - timedelta(days=7),),
            )
            new_users_7d = (await cur.fetchone())[0]

            # Active users today (had at least 1 transaction)
            await cur.execute(
                "SELECT COUNT(DISTINCT user_id) FROM expenses WHERE date = %s;",
                (today,),
            )
            active_today = (await cur.fetchone())[0]

    return {
        "total_users": total_users,
        "premium": premium,
        "free": free,
        "tx_today": tx_today,
        "sum_today": sum_today,
        "tx_month": tx_month,
        "sum_month": sum_month,
        "new_users_7d": new_users_7d,
        "active_today": active_today,
    }


async def get_user_growth_chart(days: int = 30) -> list[dict]:
    """Daily new-user counts for the last N days."""
    pool = get_pool()
    start = date.today() - timedelta(days=days - 1)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT DATE(created_at) as d, COUNT(*) as c
                   FROM users
                   WHERE created_at >= %s
                   GROUP BY d ORDER BY d;""",
                (start,),
            )
            rows = await cur.fetchall()
    data_map = {r[0]: r[1] for r in rows}
    result = []
    for i in range(days):
        d = start + timedelta(days=i)
        result.append({"date": d.isoformat(), "count": data_map.get(d, 0)})
    return result


async def get_all_users(search: str = "", limit: int = 100) -> list[dict]:
    """List all users with their plan and transaction count."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            sql = """
                SELECT u.telegram_id, u.first_name, u.created_at,
                       COALESCE(s.plan, 'free') as plan,
                       s.expires_at,
                       (SELECT COUNT(*) FROM expenses e WHERE e.user_id = u.telegram_id) as tx_count
                FROM users u
                LEFT JOIN subscriptions s ON s.user_id = u.telegram_id
            """
            params = []
            if search:
                sql += " WHERE CAST(u.telegram_id AS TEXT) ILIKE %s OR u.first_name ILIKE %s"
                p = f"%{search}%"
                params = [p, p]
            sql += " ORDER BY u.created_at DESC LIMIT %s;"
            params.append(limit)
            await cur.execute(sql, params)
            rows = await cur.fetchall()

    return [
        {
            "user_id": r[0],
            "name": r[1],
            "created_at": r[2].strftime("%Y-%m-%d") if r[2] else "",
            "plan": r[3],
            "expires_at": (r[4].date() if r[4] and hasattr(r[4], "date") else r[4]).strftime("%Y-%m-%d") if r[4] else None,
            "tx_count": r[5],
        }
        for r in rows
    ]


async def get_subscribers() -> list[dict]:
    """List all premium subscribers with expiry dates."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT s.user_id, u.first_name, s.plan, s.started_at, s.expires_at
                   FROM subscriptions s
                   LEFT JOIN users u ON u.telegram_id = s.user_id
                   WHERE s.plan = 'premium'
                   ORDER BY s.expires_at ASC NULLS LAST;"""
            )
            rows = await cur.fetchall()

    today = date.today()
    result = []
    for r in rows:
        expires = r[4]
        expires_date = expires.date() if expires and hasattr(expires, "date") else expires
        days_left = (expires_date - today).days if expires_date else None
        result.append({
            "user_id": r[0],
            "name": r[1] or "—",
            "plan": r[2],
            "started_at": r[3].strftime("%Y-%m-%d") if r[3] else "",
            "expires_at": expires_date.strftime("%Y-%m-%d") if expires_date else "—",
            "days_left": days_left,
            "expiring_soon": days_left is not None and 0 <= days_left <= 7,
        })
    return result


async def get_top_categories(days: int = 30) -> list[dict]:
    """Most-used categories across all users."""
    pool = get_pool()
    start = date.today() - timedelta(days=days)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT category, COUNT(*) as cnt, SUM(amount) as total
                   FROM expenses
                   WHERE type='expense' AND date >= %s
                   GROUP BY category ORDER BY cnt DESC LIMIT 10;""",
                (start,),
            )
            rows = await cur.fetchall()
    return [{"category": r[0], "count": r[1], "total": float(r[2])} for r in rows]


async def get_daily_activity(days: int = 30) -> list[dict]:
    """Daily transaction counts for activity chart."""
    pool = get_pool()
    start = date.today() - timedelta(days=days - 1)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT date, COUNT(*) as c, SUM(amount) as total
                   FROM expenses
                   WHERE type='expense' AND date >= %s
                   GROUP BY date ORDER BY date;""",
                (start,),
            )
            rows = await cur.fetchall()
    data_map = {r[0]: (r[1], float(r[2])) for r in rows}
    result = []
    for i in range(days):
        d = start + timedelta(days=i)
        c, t = data_map.get(d, (0, 0.0))
        result.append({"date": d.isoformat(), "count": c, "total": t})
    return result


async def get_all_user_ids() -> list[int]:
    """All registered user IDs (for broadcast)."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT telegram_id FROM users;")
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_premium_user_ids() -> list[int]:
    """Premium user IDs (for broadcast)."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT user_id FROM subscriptions WHERE plan='premium';"
            )
            rows = await cur.fetchall()
    return [r[0] for r in rows]
