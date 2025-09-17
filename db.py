# db.py
import sqlite3
import pandas as pd

DB_PATH = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        note TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_expense(date: str, amount: float, category: str, note: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO expenses (date, amount, category, note) VALUES (?, ?, ?, ?)",
                (date, amount, category, note))
    conn.commit()
    conn.close()

def get_all_expenses():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT date, amount, category, note FROM expenses ORDER BY date DESC", conn)
    conn.close()
    return df
