from huggingface_hub import login
import torch, json, re
from datetime import datetime
from transformers import AutoTokenizer, Gemma3ForCausalLM, BitsAndBytesConfig
from extract_expense import extract_expense, pretty_print

# ---- 若尚未在 CLI 登入，放開下面一行並貼上你的 token ----
# login("XXXXXXXX")

MODEL_ID = "google/gemma-3-1b-it"

def load_model():
    quant = BitsAndBytesConfig(load_in_8bit=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    mdl = Gemma3ForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=quant, device_map="auto"
    ).eval()
    return tok, mdl

# 全域只載一次
TOKENIZER, MODEL = load_model()

def chat_fn(messages: list[dict]) -> str:
    """把 messages 丟給已載入的模型，回傳 raw 文字。"""
    inputs = TOKENIZER.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    )
    inputs = {k: v.to(MODEL.device) for k, v in inputs.items()}
    with torch.inference_mode():
        out_ids = MODEL.generate(
            **inputs,
            max_new_tokens=128,
            do_sample=False,
            temperature=0.2,
            eos_token_id=TOKENIZER.eos_token_id,
            pad_token_id=TOKENIZER.eos_token_id,
        )
    new_ids = out_ids[0, inputs["input_ids"].shape[1]:]
    raw = TOKENIZER.decode(new_ids, skip_special_tokens=True).strip()
    return raw

if __name__ == "__main__":
    tests = [
        "我今天花了200元搭計程車",
        "昨天在超商買咖啡 65 元",
        "上週五請客吃晚餐 1,250 元",
        "6/30 家樂福採購 843 元",
        "2025-09-10 在全聯買早餐 89 元",
        "這個月房租 12000 元已繳",
    ]
    for t in tests:
        clean, raw = extract_expense(t, chat_fn, today=datetime.now())
        pretty_print(t, clean, raw)
        print("-" * 60)