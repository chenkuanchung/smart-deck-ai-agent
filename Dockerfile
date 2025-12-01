# 使用官方 Python 3.10 精簡版映像檔
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統層級依賴 (chromadb 有時需要 C++ 編譯器，但 slim 通常夠用，保險起見裝一下 build-essential)
RUN apt-get update && apt-get install -u \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製需求檔並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 開放 Streamlit 預設 Port
EXPOSE 8501

# 啟動指令 (使用 Streamlit 啟動 src/app.py)

CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0"]
