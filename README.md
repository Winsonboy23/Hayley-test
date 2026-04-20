# 海莉 AI 工作助理

PAUL Branding & Marketing 主管海莉的私人 AI 秘書。

## 功能

- 📩 新信件自動生成回覆草稿 + LINE 通知
- ⏰ 活動前 1 小時 LINE 提醒
- 📅 每天 18:00 推送明日行程總結
- 💬 LINE 工作問答（信件、行程、聯絡人）

## 技術架構

- **後端**：Python + FastAPI
- **AI**：Gemini 1.5 Flash
- **部署**：Railway / Zeabur
- **資料**：Notion（聯絡人 + 信件模板）

## 環境設定

### 1. 安裝套件

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env` 並填入所有金鑰：

```bash
cp .env .env.local
```

### 3. Google OAuth 授權

```bash
python setup_google_auth.py
```

授權完成後將輸出的 JSON 填入 `GOOGLE_TOKEN_JSON`。

### 4. 本地測試

```bash
uvicorn app.main:app --reload --port 8000
```

測試端點：
- `GET /` — 健康檢查
- `GET /test/daily-summary` — 測試每日總結
- `GET /test/new-email` — 測試最新信件處理

### 5. 部署到 Railway

1. 推送程式碼到 GitHub
2. Railway 連接 GitHub Repository
3. 填入所有環境變數
4. 部署完成

## 環境變數說明

| 變數 | 說明 |
|------|------|
| `GEMINI_API_KEY` | Google AI Studio 的 API Key |
| `LINE_CHANNEL_SECRET` | LINE Bot Channel Secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Access Token |
| `LINE_USER_ID` | 海莉的 LINE User ID |
| `GOOGLE_TOKEN_JSON` | Google OAuth Token（執行 setup_google_auth.py 取得）|
| `NOTION_API_KEY` | Notion Integration API Key |
| `NOTION_CONTACTS_DB_ID` | Notion 聯絡人資料庫 ID |
| `NOTION_TEMPLATES_DB_ID` | Notion 信件模板資料庫 ID |

## LINE Webhook 設定

部署完成後，將以下 URL 填入 LINE Developers Console：

```
https://你的域名.railway.app/webhook/line
```

## Gmail Push Notification 設定

需要在 Google Cloud Console 設定 Pub/Sub，詳見文件。

