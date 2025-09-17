# streamlit_app.py
import streamlit as st
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from calendar import monthrange
from datetime import datetime, date

# 避免圖表中文字變亂碼
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft JhengHei", "Microsoft YaHei", "SimHei", "Noto Sans CJK TC"
]
matplotlib.rcParams["axes.unicode_minus"] = False

from db import (
    init_db, insert_expense, get_all_expenses, get_expenses_between,
    delete_all, delete_by_ids, delete_by_date_range
)

# 你的 LLM 呼叫與抽取（模型初始化請放在 main.py，只載一次）
from main import chat_fn
from extract_expense import extract_expense

# -------------------- 初始化 --------------------
st.set_page_config(page_title="SmartLedger 記帳助理", layout="wide")
init_db()

st.title("💰 SmartLedger 記帳助理")

# -------------------- 輸入區 --------------------
with st.container():
    c1, c2 = st.columns([5, 1])
    with c1:
        user_text = st.text_input("輸入一筆消費紀錄（例如：昨天買咖啡 65 元）", key="input_expense")
    with c2:
        add_clicked = st.button("新增紀錄", type="primary", use_container_width=True)

    if add_clicked and user_text.strip():
        clean, raw = extract_expense(user_text, chat_fn, today=datetime.now())
        if clean["date"] and clean["amount"] and clean["category"]:
            insert_expense(clean["date"], clean["amount"], clean["category"], clean.get("note", ""))
            st.success(f"已新增：{clean}")
            st.rerun()
        else:
            st.error("解析失敗，請再試一次。")

# -------------------- 側邊欄：篩選 & 匯出 --------------------
st.sidebar.header("🔎 篩選 / 匯出")

_df_all = get_all_expenses()
df = _df_all.copy()  # 預設顯示全部
use_filter = st.sidebar.checkbox("啟用篩選", value=False)

start_date = None
end_date = None

if use_filter and not _df_all.empty:
    months = sorted({_d[:7] for _d in _df_all["date"]})
    default_month = datetime.now().strftime("%Y-%m")

    mode = st.sidebar.radio("篩選模式", ["依月份", "自訂區間"], horizontal=True)

    if mode == "依月份":
        options = [default_month] + [m for m in months if m != default_month]
        pick_month = st.sidebar.selectbox("選擇月份", options=options)
        y, m = map(int, pick_month.split("-"))
        start_date = date(y, m, 1)
        end_date = date(y, m, monthrange(y, m)[1])
        df = get_expenses_between(str(start_date), str(end_date))
    else:
        col_a, col_b = st.sidebar.columns(2)
        with col_a:
            start_date = st.sidebar.date_input("開始", value=date.today().replace(day=1))
        with col_b:
            end_date = st.sidebar.date_input("結束", value=date.today())
        if start_date > end_date:
            st.sidebar.error("開始日期不可大於結束日期")
        else:
            df = get_expenses_between(str(start_date), str(end_date))

    st.sidebar.info(f"目前顯示：{start_date} ~ {end_date}，共 {len(df)} 筆")
else:
    st.sidebar.info(f"目前顯示全部，共 {len(df)} 筆")

# ---- 匯出 CSV（目前顯示的資料 & 全部資料）----
st.sidebar.subheader("📤 匯出")
csv_current = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
fname_current = "expenses_all.csv"
if use_filter and start_date and end_date:
    fname_current = f"expenses_{start_date}_{end_date}.csv"

st.sidebar.download_button(
    label="下載目前顯示的紀錄 (CSV)",
    data=csv_current,
    file_name=fname_current,
    mime="text/csv",
    use_container_width=True,
)

csv_all = _df_all.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.sidebar.download_button(
    label="下載全部紀錄 (CSV)",
    data=csv_all,
    file_name="expenses_full.csv",
    mime="text/csv",
    use_container_width=True,
)

st.sidebar.divider()

# -------------------- 表格（可勾選刪除） --------------------
st.subheader("📋 紀錄")
if df.empty:
    st.info("目前沒有資料可顯示")
else:
    df_view = df.copy()
    df_view.insert(0, "選取", False)  # 勾選欄位在最左
    edited = st.data_editor(
        df_view,
        key="editor",
        use_container_width=True,
        column_config={"選取": st.column_config.CheckboxColumn(required=False)},
        num_rows="fixed",
        height=360,
    )

    # -------------------- 清除/刪除功能 --------------------
    st.divider()
    st.subheader("🧹 清除/刪除紀錄")

    tab1, tab2, tab3 = st.tabs(["勾選刪除", "依日期區間", "全部清空"])

    # 勾選刪除
    with tab1:
        picked_ids = edited.loc[edited["選取"] == True, "id"].tolist()
        st.write(f"已選取：{len(picked_ids)} 筆")
        if st.button("刪除選取的紀錄", type="primary", disabled=(len(picked_ids) == 0)):
            delete_by_ids(picked_ids)
            st.success(f"已刪除 {len(picked_ids)} 筆")
            st.rerun()

    # 依日期區間刪除（不受上方篩選限制，可跨區間）
    with tab2:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            d1 = st.date_input("起始日期", key="del_start")
        with c2:
            d2 = st.date_input("結束日期", key="del_end")
        with c3:
            confirm = st.text_input("輸入 DEL 確認", placeholder="DEL", key="del_confirm")
        disabled = not (d1 and d2 and confirm == "DEL" and d1 <= d2)
        if st.button("刪除區間紀錄", disabled=disabled):
            delete_by_date_range(str(d1), str(d2))
            st.success(f"已刪除 {d1} ~ {d2} 的紀錄")
            st.rerun()

    # 全部清空
    with tab3:
        st.warning("此操作會刪除所有紀錄且無法復原。")
        confirm_all = st.text_input("輸入 DELETE 以確認", placeholder="DELETE", key="del_all")
        if st.button("全部清空", type="secondary", disabled=(confirm_all != "DELETE")):
            delete_all()
            st.success("已刪除所有紀錄")
            st.rerun()

# -------------------- 圖表（左右並排） --------------------
st.subheader("📊 分類支出統計")
if df.empty:
    st.info("沒有資料可統計")
else:
    grouped = df.groupby("category")["amount"].sum().sort_values(ascending=False)

    col1, col2 = st.columns(2)

    # 左：長條圖
    with col1:
        fig, ax = plt.subplots()
        grouped.plot(kind="bar", ax=ax, color="skyblue")
        ax.set_xlabel("category")
        ax.set_ylabel("金額")
        ax.set_title("各類別支出總額")
        st.pyplot(fig)

    # 右：圓餅圖
    with col2:
        fig2, ax2 = plt.subplots()
        grouped.plot(kind="pie", autopct="%1.1f%%", startangle=90, ax=ax2)
        ax2.set_ylabel("")  # 移除 y label
        ax2.set_title("支出分布")
        st.pyplot(fig2)
