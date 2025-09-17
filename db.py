# db.py
import sqlite3
import pandas as pd

DB_PATH = "expenses.db"

def _connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,         -- YYYY-MM-DD
        amount REAL NOT NULL,       -- 金額
        category TEXT NOT NULL,     -- 餐飲/交通/購物/住房/娛樂
        note TEXT                   -- 備註
    )
    """)
    conn.commit()
    conn.close()

def insert_expense(date: str, amount: float, category: str, note: str = "") -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (date, amount, category, note) VALUES (?, ?, ?, ?)",
        (date, float(amount), category, note),
    )
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def get_all_expenses() -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql_query(
        "SELECT id, date, amount, category, note "
        "FROM expenses ORDER BY date DESC, id DESC",
        conn
    )
    conn.close()
    return df

def get_expenses_between(start_date: str, end_date: str) -> pd.DataFrame:
    """回傳 [start_date, end_date]（皆含）的紀錄；日期格式需 'YYYY-MM-DD'。"""
    conn = _connect()
    df = pd.read_sql_query(
        "SELECT id, date, amount, category, note "
        "FROM expenses WHERE date BETWEEN ? AND ? "
        "ORDER BY date DESC, id DESC",
        conn,
        params=(start_date, end_date),
    )
    conn.close()
    return df

# ---------- 刪除功能 ----------
def delete_all():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()

def delete_by_ids(ids: list[int]):
    if not ids:
        return
    qmarks = ",".join("?" * len(ids))
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM expenses WHERE id IN ({qmarks})", ids)
    conn.commit()
    conn.close()

def delete_by_date_range(start_date: str, end_date: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE date BETWEEN ? AND ?", (start_date, end_date))
    conn.commit()
    conn.close()
