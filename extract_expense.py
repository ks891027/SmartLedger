# extract_expense.py
from __future__ import annotations
import re, json
from datetime import datetime, timedelta
from typing import Optional, Tuple, Callable, Dict, Any

# -----------------------------
# 日期前處理（先算好再提示給 LLM）
# -----------------------------

# 週幾解析：上/這/下 週 + 週一~週日 / 1~7
WEEKIDX = {"一":0,"二":1,"三":2,"四":3,"五":4,"六":5,"日":6,"天":6,
           "1":0,"2":1,"3":2,"4":3,"5":4,"6":5,"7":6}
WEEK_PAT = re.compile(r"(上|這|本|下)\s*(週|周|禮拜|星期)\s*([一二三四五六日天1-7])")

def resolve_relative_week(text: str, today: datetime) -> Optional[str]:
    m = WEEK_PAT.search(text)
    if not m:
        return None
    pre, _, wd = m.groups()
    woff = {"上":-1, "這":0, "本":0, "下":1}[pre]
    idx = WEEKIDX.get(wd)
    if idx is None:
        return None
    start = today - timedelta(days=today.weekday()) + timedelta(days=7*woff)  # 週一為起點
    dt = start + timedelta(days=idx)
    return dt.strftime("%Y-%m-%d")

def parse_date_text(text: str, today: datetime) -> Optional[str]:
    """
    盡力從中文輸入抽取/推算日期，回傳 YYYY-MM-DD
    規則：
      - 明確日期：YYYY-MM-DD / YYYY/MM/DD
      - 無年份：M/D 或 M-D、X月Y日 → 一律補今年
      - 今天/昨天/前天
      - 這個月/本月（回月初 01 日）；上個月/下個月同理
      - 上/這/下 週 + 週幾（交給 resolve_relative_week）
    """
    # 明確 YYYY-MM-DD / YYYY/MM/DD
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"

    # 無年份：M/D 或 M-D
    m = re.search(r"(\d{1,2})[/-](\d{1,2})", text)
    if m:
        mo, d = map(int, m.groups())
        return f"{today.year:04d}-{mo:02d}-{d:02d}"

    # 無年份：X月Y日
    m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if m:
        mo, d = map(int, m.groups())
        return f"{today.year:04d}-{mo:02d}-{d:02d}"

    # 今天/昨天/前天
    if "今天" in text:
        return today.strftime("%Y-%m-%d")
    if "昨天" in text:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if "前天" in text:
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")

    # 這個月/本月/上個月/下個月 → 取月初（需要別的規則可自行改）
    if "這個月" in text or "本月" in text or "這月" in text:
        return f"{today.year:04d}-{today.month:02d}-01"
    if "上個月" in text or "上月" in text:
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
        return f"{year:04d}-{month:02d}-01"
    if "下個月" in text or "下月" in text:
        year = today.year if today.month < 12 else today.year + 1
        month = today.month + 1 if today.month < 12 else 1
        return f"{year:04d}-{month:02d}-01"

    # 上/這/下 週 + 週幾
    w = resolve_relative_week(text, today)
    if w:
        return w

    return None

# -----------------------------
# Prompt 與輸出清理
# -----------------------------

CATEGORIES = ["餐飲", "交通", "購物", "住房", "娛樂"]

def system_prompt(today_str: str) -> str:
    return f"""你是記帳抽取助手。請將使用者輸入的消費紀錄轉換為 JSON，並且一定要符合以下規則：

1) 只輸出 JSON，不要有多餘文字。
2) 欄位：
   - date: ISO 8601（YYYY-MM-DD）。若是相對日期（今天/昨天/上週五），以「今天={today_str}」換算。
   - amount: 只保留數字（整數或小數），不含單位。
   - category: 必須從 {{餐飲, 交通, 購物, 住房, 娛樂}} 中擇一；不允許其他選項。
   - note: 可選，<=20字。

3) 分類原則：
   - 餐飲：與吃、喝、餐點、飲料、咖啡等有關。
   - 交通：搭車、捷運、公車、高鐵、計程車、油費、停車等。
   - 購物：購物、日用品、超商、全聯、家樂福等。
   - 住房：房租、水電、瓦斯、管理費、居住相關。
   - 娛樂：電影、唱歌、遊戲、旅遊、演唱會等。

輸出格式：
{{"date":"YYYY-MM-DD","amount":數字,"category":"餐飲|交通|購物|住房|娛樂","note":"..."}}"""

# （可選）少量 few-shot，幫 1B 模型穩住格式與分類邏輯
FEW_SHOT = [
    {"role":"user","content":[{"type":"text","text":"昨天在超商買咖啡 65 元"}]},
    {"role":"assistant","content":[{"type":"text","text":'{"date":"{TODAY_MINUS_1}","amount":65,"category":"餐飲","note":"咖啡屬飲品"}'}]},
    {"role":"user","content":[{"type":"text","text":"今天搭計程車 200 元"}]},
    {"role":"assistant","content":[{"type":"text","text":'{"date":"{TODAY}","amount":200,"category":"交通","note":"計程車屬交通"}'}]},
]

def build_messages(user_text: str, today: datetime) -> tuple[list[dict], Optional[str]]:
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    date_hint = parse_date_text(user_text, today)

    # few-shot 文字中的日期占位替換
    few_shot = []
    for turn in FEW_SHOT:
        t = json.dumps(turn) \
             .replace("{TODAY}", today_str) \
             .replace("{TODAY_MINUS_1}", yesterday_str)
        few_shot.append(json.loads(t))

    text_with_hint = f"{user_text} [DATE:{date_hint}]" if date_hint else user_text
    messages = [
        {"role":"system","content":[{"type":"text","text":system_prompt(today_str)}]},
        *few_shot,
        {"role":"user","content":[{"type":"text","text":text_with_hint}]},
    ]
    return messages, date_hint

_JSON_BLOCK = re.compile(r"\{.*?\}", flags=re.S)

def extract_first_json(s: str) -> Optional[dict]:
    m = _JSON_BLOCK.search(s)
    if not m: return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def clean_amount(val) -> Optional[float]:
    try:
        num = re.sub(r"[^\d.]", "", str(val))
        if not num: return None
        if num.count(".") > 1:
            head, *rest = num.split(".")
            num = head + "." + "".join(rest)
        return float(num)
    except Exception:
        return None

def category_is_valid(cat: Optional[str]) -> bool:
    return isinstance(cat, str) and (cat in CATEGORIES)

# -----------------------------
# 主流程：若分類不在五大類，會「重問一次」請模型修正
# -----------------------------
def extract_expense(user_text: str,
                    chat_fn: Callable[[list[dict]], str],
                    today: Optional[datetime] = None) -> tuple[Dict[str, Any], str]:
    today = today or datetime.now()
    messages, date_hint = build_messages(user_text, today)

    # 第一次生成
    raw_text = chat_fn(messages)
    parsed = extract_first_json(raw_text) or {}

    # 檢查分類；若不合法，用一次 guard 要求模型修正（仍只靠 LLM，無關鍵字硬套）
    if not category_is_valid(parsed.get("category")):
        guard = {
            "role": "system",
            "content": [{"type":"text","text":
                "你剛剛的 category 不在 {餐飲, 交通, 購物, 住房, 娛樂} 之內。請只回傳修正後的 JSON，且必須填入上述五類之一，其他欄位照原判斷即可。"}]
        }
        # 把第一次的 JSON 當作「基準」
        user_fix = {
            "role": "user",
            "content": [{"type":"text","text": json.dumps(parsed, ensure_ascii=False)}]
        }
        raw_text2 = chat_fn([guard, user_fix])
        parsed2 = extract_first_json(raw_text2) or {}
        # 若第二次仍不合法，就保留原本（實務上 1B 幾乎會修正好）
        if category_is_valid(parsed2.get("category")):
            raw_text = raw_text2
            parsed = parsed2

    # 後處理／補齊
    date_val = parsed.get("date") or date_hint
    amt_val  = clean_amount(parsed.get("amount"))
    cat_val  = parsed.get("category") if category_is_valid(parsed.get("category")) else None
    note_val = parsed.get("note") or ""

    clean = {"date": date_val, "amount": amt_val, "category": cat_val, "note": note_val}
    return clean, raw_text

def pretty_print(user_text: str, clean: dict, raw: str):
    print("USER:", user_text)
    print("RAW :\n", raw)
    print("JSON:\n", json.dumps(clean, ensure_ascii=False, indent=2))
