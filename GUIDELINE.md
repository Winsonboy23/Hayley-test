# 海莉 AI 助理 — 功能指南

---

## 一、LINE 指令（手動查詢）

在 LINE 對話框直接輸入以下文字：

### 📅 行事曆

| 指令 | 說明 |
|------|------|
| `今日行程` | 今天的所有行程（單張卡片） |
| `明日行程` | 明天的所有行程（單張卡片） |
| `本週行程` | 未來 7 天行程（依日曆分頁輪播） |
| `本月行程` | 本月所有行程（依日曆分頁輪播） |
| `下個月行程` | 下個月所有行程 |
| `5月行程` | 指定月份行程（1–12 月皆可） |
| `新增行程 日期 時間 標題` | 新增 Google Calendar 行程 |
| `搜尋 關鍵字` | 搜尋前後一年內含關鍵字的行程 |

> 行程卡片依 Google Calendar 日曆顏色分類，可左右滑動切換日曆。
> 多筆新增可用換行或分號分隔，例如：`新增行程 明天 14:00 會議；後天 全天 活動`

---

### 📩 信件

| 指令 | 說明 |
|------|------|
| `信件` | 今天收到幾封信 + 草稿區幾封待發 |

---

### 👤 聯絡人

| 指令 | 說明 |
|------|------|
| `聯絡人 姓名` | 查詢 Notion 聯絡人的職稱、單位、email |

> 範例：`聯絡人 王小明`

---

### ✅ 待辦事項

| 指令 | 說明 |
|------|------|
| `待辦事項` | 列出 Google Tasks 所有清單的未完成任務（含截止日） |

---

## 二、每日行程推播

不需要主動查詢，系統會在固定時間推送行程：

### ☀️ 今日行程（每天 08:00）

- 今天行程件數
- 最多顯示前 5 筆今日行程
- 依 Google Calendar 日曆顏色標示

### 📅 明日行程（每天 18:00）

- 明天行程件數
- 最多顯示前 5 筆明日行程
- 依 Google Calendar 日曆顏色標示

---

## 三、新信件自動處理

當 Gmail 收到新信，系統會自動：

1. **比對寄件人** — 在 Notion 聯絡人資料庫中查詢寄件人 email
2. **已知聯絡人** → 根據對方職稱找對應信件模板，由 AI 生成回覆草稿存入 Gmail 草稿夾，LINE 通知含摘要與草稿提示
3. **陌生寄件人** → 僅推播 LINE 通知（顯示 ⚠️ 警示），不生成草稿

> LINE 通知格式：
> ```
> 📩 新信件
> 寄件人：XXX（單位 職稱）
> 主旨：信件主旨
> 草稿已備妥，請至 Gmail 確認 ✉️
> ```

---

## 四、Notion 資料庫說明

### 聯絡人資料庫
| 欄位 | 說明 |
|------|------|
| 姓名 | 聯絡人名稱 |
| Email | 用於比對寄件人（必填） |
| 職稱 / 角色 | 用於查找對應信件模板 |
| 單位 | 顯示於通知中 |

### 信件模板資料庫
| 欄位 | 說明 |
|------|------|
| 角色 | 對應聯絡人的職稱 |
| 內容 | 回覆草稿的撰寫風格與範本 |

> 聯絡人的「角色」需與模板的「角色」一致，才能正確配對。

---

## 五、系統維護

### Google Token 過期
Token 有效期約數週至數月，過期後需重新授權：
1. 在本機執行 `python setup_google_auth.py`
2. 完成授權後，將新的 token JSON 更新到 Railway 環境變數 `GOOGLE_TOKEN_JSON`

### Gmail Watch 續期
Gmail Watch 有效期 7 天，系統每 6 天會自動續期（排程任務）。
若需手動更新：
```
GET https://web-production-3c43d.up.railway.app/setup/gmail-watch
```

### 手動測試端點
| 網址 | 功能 |
|------|------|
| `/test/morning-summary` | 觸發早晨摘要推播 |
| `/test/daily-summary` | 觸發晚間行程推播 |
| `/test/new-email` | 手動觸發最新一封信的處理流程 |

---

## 六、環境變數一覽

| 變數名稱 | 說明 |
|----------|------|
| `LINE_CHANNEL_SECRET` | LINE Bot 頻道密鑰 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot 存取 Token |
| `LINE_USER_ID` | 海莉的 LINE 使用者 ID |
| `GOOGLE_TOKEN_JSON` | Google OAuth Token（JSON 格式） |
| `GOOGLE_CLOUD_PROJECT_ID` | GCP 專案 ID（Pub/Sub 用） |
| `GEMINI_API_KEY` | Google AI Studio API 金鑰 |
| `NOTION_TOKEN` | Notion Integration Token |
| `NOTION_CONTACTS_DB_ID` | Notion 聯絡人資料庫 ID |
| `NOTION_TEMPLATES_DB_ID` | Notion 信件模板資料庫 ID |
