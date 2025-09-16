# extract_expense.py
from __future__ import annotations
import re, json
from datetime import datetime, timedelta
from typing import Optional, Tuple, Callable, Dict, Any

# ---------- 相對週日期解析：上/這/下 週 + 週幾 ----------
WEEKIDX = {"一":0,"二":1,"三":2,"四":3,"五":4,"六":5,"日":6,"天":6,"1":0,"2":1,"3":2,"4":3,"5":4,"6":5,"7":6}
WEEK_PAT = re.compile(r"(上|這|本|下)\s*(週|周|禮拜)\s*([一二三四五六日天1-7])")

def resolve_relative_week(text: str, today: datetime) -> Optional[str]:
    m = WEEK_PAT.search(text)
    if not m:
        return None
    pre, _, wd = m.groups()
    woff = {"上":-1, "這":0, "本":0, "下":1}[pre]
    idx = WEEKIDX.get(wd)
    if idx is None:
        return None
    # 以週一為起點
    start = today - timedelta(days=today.weekday()) + timedelta(days=7*woff)
    dt = start + timedelta(days=idx)
    return dt.strftime("%Y-%m-%d")

CATEGORIES = ["餐飲","交通","購物","住房","娛樂","其他"]

def system_prompt(today_str: str) -> str:
    return f"""你是記帳抽取助手。只輸出 JSON（不可有多餘文字）。
若輸入包含 [DATE:YYYY-MM-DD]，請直接使用此日期，不要重新推算。
欄位：
- date: ISO 8601（YYYY-MM-DD）。若是相對日期（今天/昨天/上週五），以「今天={today_str}」換算。
- amount: 只保留數字（整數或小數），不含單位。
- category: 從 {{餐飲, 交通, 購物, 住房, 娛樂, 其他}} 中選一；不確定填「其他」。
- note: 可選，<=20字。
輸出格式：
{{"date":"YYYY-MM-DD","amount":數字,"category":"餐飲|交通|購物|住房|娛樂|其他","note":"..."}}"""

def build_messages(user_text: str, today: datetime) -> Tuple[list[dict], Optional[str]]:
    """依需求建立 messages；若偵測到相對週日期，附上 [DATE:...] hint。"""
    today_str = today.strftime("%Y-%m-%d")
    date_hint = resolve_relative_week(user_text, today)
    text_with_hint = f"{user_text} [DATE:{date_hint}]" if date_hint else user_text
    messages = [
        {"role":"system","content":[{"type":"text","text":system_prompt(today_str)}]},
        {"role":"user","content":[{"type":"text","text":text_with_hint}]},
    ]
    return messages, date_hint

_JSON_BLOCK = re.compile(r"\{.*?\}", flags=re.S)

def extract_first_json(s: str) -> Optional[dict]:
    m = _JSON_BLOCK.search(s)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def clean_amount(val) -> Optional[float]:
    try:
        num = re.sub(r"[^\d.]", "", str(val))
        if not num:
            return None
        if num.count(".") > 1:
            head, *rest = num.split(".")
            num = head + "." + "".join(rest)
        return float(num)
    except Exception:
        return None

def normalize_category(cat: str) -> str:
    return cat if cat in CATEGORIES else "其他"

def extract_expense(user_text: str,
                    chat_fn: Callable[[list[dict]], str],
                    today: Optional[datetime] = None) -> Tuple[Dict[str, Any], str]:
    """
    以你提供的 chat_fn(messages)->raw_text 呼叫 LLM。
    回傳: (clean_dict, raw_text)
    """
    today = today or datetime.now()
    messages, date_hint = build_messages(user_text, today)

    raw_text = chat_fn(messages)  # <-- 由 main 提供的函式

    parsed = extract_first_json(raw_text) or {}
    date_val = parsed.get("date") or date_hint
    amt_val  = clean_amount(parsed.get("amount"))
    cat_val  = normalize_category(parsed.get("category") or "其他")
    note_val = parsed.get("note") or ""

    clean = {"date": date_val, "amount": amt_val, "category": cat_val, "note": note_val}
    return clean, raw_text

def pretty_print(user_text: str, clean: dict, raw: str):
    print("USER:", user_text)
    print("RAW :\n", raw)
    print("JSON:\n", json.dumps(clean, ensure_ascii=False, indent=2))
