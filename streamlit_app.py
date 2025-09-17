# streamlit_app.py
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei", "Noto Sans CJK TC"]
# 允許負號正常顯示
matplotlib.rcParams["axes.unicode_minus"] = False
import pandas as pd
from datetime import datetime

from extract_expense import extract_expense
from db import init_db, insert_expense, get_all_expenses
from gemma3_test import chat_fn   # 你在 main.py 定義好的 LLM 呼叫函式

# 初始化資料庫
init_db()

st.title("💰 SmartLedger 記帳助理")

# --- 輸入區 ---
user_text = st.text_input("輸入一筆消費紀錄（例如：昨天買咖啡 65 元）")

if st.button("新增紀錄") and user_text.strip():
    clean, raw = extract_expense(user_text, chat_fn, today=datetime.now())
    if clean["date"] and clean["amount"] and clean["category"]:
        insert_expense(clean["date"], clean["amount"], clean["category"], clean["note"])
        st.success(f"已新增：{clean}")
    else:
        st.error("解析失敗，請再試一次")

# --- 顯示所有紀錄 ---
st.subheader("📋 所有紀錄")
df = get_all_expenses()
st.dataframe(df)

if not df.empty:
    # --- 分類統計 ---
    st.subheader("📊 分類支出統計")

    # 長條圖
    fig, ax = plt.subplots()
    df.groupby("category")["amount"].sum().plot(kind="bar", ax=ax, color="skyblue")
    ax.set_ylabel("金額")
    ax.set_title("各類別支出總額")
    st.pyplot(fig)

    # 圓餅圖
    fig2, ax2 = plt.subplots()
    df.groupby("category")["amount"].sum().plot(kind="pie", autopct="%1.1f%%", ax=ax2)
    ax2.set_ylabel("")
    ax2.set_title("支出分布")
    st.pyplot(fig2)
