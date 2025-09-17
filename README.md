# 🖥️ SmartLedger: Expense Tracker + AI Assistant

這是一個基於 **Streamlit** 的 Web App，整合了資料庫紀錄管理與 AI 模型推論。  

---

## 📌 功能特色

### 💰 記帳功能
- **新增紀錄**：輸入日期、金額、類別，紀錄支出  
- **清除紀錄**：一鍵清除資料庫所有紀錄  
- **篩選顯示**：可依日期/類別篩選（預設顯示全部）  
- **匯出功能**：將所有紀錄匯出為 CSV  

### 📊 視覺化功能
- **長條圖**：顯示各類別支出分布  
- **圓餅圖**：顯示支出比例  
- **左右並排顯示**，更直觀比較  

### 🤖 AI 模型支援
- **Transformers 模型推論**：可載入 Hugging Face 模型進行測試  
- **Accelerate + Bitsandbytes**：支援 GPU 加速與低精度推論（4bit/8bit），大幅減少顯存使用


## 📷 介面展示 (Screenshots)

### 記帳介面
![SmartLedger 記帳介面](./example/1.png)

### 視覺化圖表
![SmartLedger 視覺化圖表](./example/2.png)

## ⚙️ 安裝與使用

### 1. 建立虛擬環境
```bash
conda create -n expense_ai python=3.12 -y
conda activate expense_ai
```

### 2. 安裝需求套件
```bash
pip install -r requirements.txt
```

### 3. 執行 Streamlit App
```bash
streamlit run streamlit_app.py
```

