# Agent.md - 海莉 AI 工作助理

> 供 AI 助手快速了解專案的摘要文件

## 專案概述

為 PAUL 品牌行銷經理「海莉」設計的 AI 工作助理，自動處理郵件、行事曆、LINE 通知。

## 技術架構

| 項目 | 技術 |
|------|------|
| 框架 | FastAPI + Uvicorn |
| AI | Gemini API (`gemini-2.5-flash`) |
| 排程 | APScheduler (AsyncIOScheduler) |
| 部署 | Railway |
| 時區 | Asia/Taipei |

## 檔案結構

```
main.py              # FastAPI 主程式、webhook、排程任務
├── gmail_handler.py     # Gmail API：讀取郵件、建立草稿、Gmail Watch
├── calendar_handler.py  # Google Calendar：取得行程、多日曆合併
├── gemini_handler.py    # Gemini AI：生成回信、工作問答
├── line_handler.py      # LINE Bot：推播訊息
├── flex_builder.py      # LINE Flex Message 建構器
├── notion_handler.py    # Notion：查詢聯絡人、信件模板
├── tasks_handler.py     # Google Tasks：待辦事項
└── setup_google_auth.py # OAuth 設定腳本（本地執行）
```

## 環境變數

```
GEMINI_API_KEY          # Google AI API key
GOOGLE_CLOUD_PROJECT_ID # GCP 專案 ID（用於 Gmail Watch Pub/Sub）
GOOGLE_TOKEN_JSON       # Google OAuth token（JSON 字串）
LINE_CHANNEL_SECRET     # LINE Bot channel secret
LINE_CHANNEL_ACCESS_TOKEN # LINE Bot access token
LINE_USER_ID            # 接收推播的 LINE user ID
NOTION_API_KEY          # Notion integration token
NOTION_CONTACTS_DB_ID   # Notion 聯絡人資料庫 ID
NOTION_TEMPLATES_DB_ID  # Notion 信件模板資料庫 ID
```

## API 端點

| 方法 | 路徑 | 用途 |
|------|------|------|
| GET | `/` | Health check |
| POST | `/webhook/gmail` | Gmail Push Notification |
| POST | `/webhook/line` | LINE Bot webhook |
| GET | `/setup/gmail-watch` | 手動設定 Gmail Watch |
| GET | `/test/morning-summary` | 測試早晨推播 |
| GET | `/test/daily-summary` | 測試晚間推播 |
| GET | `/test/new-email` | 測試處理最新郵件 |

## 排程任務

| 時間 | 任務 | 函數 |
|------|------|------|
| 每分鐘 | 檢查 1 小時內行程提醒 | `check_upcoming_events()` |
| 08:00 | 早晨摘要推播 | `send_morning_summary()` |
| 18:00 | 晚間摘要推播 | `send_daily_summary()` |
| 每 6 天 | 更新 Gmail Watch | `renew_gmail_watch()` |

## LINE Bot 指令

| 指令 | 功能 |
|------|------|
| `今日行程` / `今天` | 今日行程 |
| `明日行程` / `明天` | 明日行程 |
| `本週行程` | 本週行程 |
| `本月行程` | 本月行程 |
| `下個月行程` | 下月行程 |
| `N月行程` | 指定月份（1-12） |
| `搜尋 關鍵字` | 搜尋行程 |
| `信件` / `草稿` | 郵件統計 |
| `聯絡人 姓名` | 查詢聯絡人 |
| `待辦事項` / `任務` | 待辦清單 |
| `指令` | 顯示選單 |

## 核心流程

### 郵件處理流程
```
Gmail Push → /webhook/gmail → 取得郵件內容
    → Gemini 生成回信草稿
    → 查詢 Notion 聯絡人/模板
    → 建立 Gmail 草稿
    → LINE 推播通知（含主旨）
```

### 行程提醒流程
```
每分鐘檢查 → 55-65 分鐘內的行程 → 排除已提醒 → LINE 推播
```

## 已知問題 / TODO

- [ ] Gemini API 無錯誤處理（429/503 會崩潰）
- [ ] Gmail 草稿建立無錯誤處理
- [ ] Tasks 需重新授權 scope
- [ ] 無 API 超時設定
- [ ] 使用 print() 而非 logging 模組

## Notion 資料庫 Schema

### 聯絡人 (NOTION_CONTACTS_DB_ID)
- `email`: Email（用於比對寄件者）
- `姓名`: 聯絡人姓名
- `單位`: 所屬單位
- `職稱`: 職稱/角色

### 信件模板 (NOTION_TEMPLATES_DB_ID)
- `角色`: 對應聯絡人職稱
- `內容`: 回信模板（Notion block content）

## 注意事項

1. **快取**: Calendar list 快取 1 小時（`_calendar_cache`）
2. **郵件截斷**: 郵件內容最多 3000 字元
3. **行程顯示**: 早晚推播最多顯示 5 筆
4. **排除行事曆**: `台灣節日`, `Contacts`, `Birthdays`, `Weeks`
