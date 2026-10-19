from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


def _date_clause(start_date, end_date):
    # Only these fixed fragments are concatenated; values stay ? parameters.
    sql, params = "", []
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    return sql, params


# ---- [SECTION 1: transaction history] ---------------------------- #
def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    clause, params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *params, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "date": row["date"],
            "description": row["description"] or "",
            "category": row["category"],
            "amount": float(row["amount"]),
        }
        for row in rows
    ]
# ---- [END SECTION 1] --------------------------------------------- #


# ---- [SECTION 2: summary stats] ---------------------------------- #
def get_summary_stats(user_id, start_date=None, end_date=None):
    clause, params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?" + clause,
            (user_id, *params),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + clause + " "
            "GROUP BY category ORDER BY SUM(amount) DESC, category LIMIT 1",
            (user_id, *params),
        ).fetchone()
    finally:
        conn.close()
    return {
        "total_spent": totals["total"],
        "transaction_count": totals["count"],
        "top_category": top["category"] if top else "—",
    }
# ---- [END SECTION 2] --------------------------------------------- #


# ---- [SECTION 3: category breakdown] ----------------------------- #
def get_category_breakdown(user_id, start_date=None, end_date=None):
    clause, params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS amount FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category ORDER BY amount DESC, category",
            (user_id, *params),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return []
    total = sum(r["amount"] for r in rows)
    result = [
        {
            "name": r["category"],
            "amount": float(r["amount"]),
            "pct": int(round(r["amount"] / total * 100)),
        }
        for r in rows
    ]
    result[0]["pct"] += 100 - sum(c["pct"] for c in result)
    return result
# ---- [END SECTION 3] --------------------------------------------- #
