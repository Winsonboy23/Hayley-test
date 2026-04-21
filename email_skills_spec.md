# Email Agent Skills 規格書 - Phase 1

> 核心 Skills 設計文件，確認後再實作程式碼

---

## 總覽

| Skill | 輸入 | 輸出 | 用途 |
|-------|------|------|------|
| `classify_urgency` | 郵件內容 | 緊急程度 | 決定通知樣式 |
| `classify_category` | 郵件內容 | 郵件類型 | 分類管理 |
| `detect_action_required` | 郵件內容 | 是否需行動 | 過濾 FYI 信件 |
| `generate_smart_reply` | 郵件 + 寄件者資訊 | 回覆草稿 | 取代純模板 |

---

## Skill 1: classify_urgency

### 功能
判斷郵件的緊急程度

### 輸入
```python
{
    "subject": "郵件主旨",
    "body": "郵件內容",
    "sender": "寄件者 email"
}
```

### 輸出
```python
{
    "level": "urgent" | "normal" | "low",
    "reason": "判斷原因（簡短）"
}
```

### 判斷邏輯
| 等級 | 條件 |
|------|------|
| `urgent` | 包含「急」「盡快」「今天」「馬上」「ASAP」「緊急」 |
| `urgent` | 來自老闆、主管、重要客戶 |
| `low` | 廣告、電子報、自動通知 |
| `normal` | 其他 |

### LINE 通知顯示
- 🔴 `urgent` → 紅色標籤
- 🟡 `normal` → 黃色標籤
- ⚪ `low` → 灰色標籤

---

## Skill 2: classify_category

### 功能
判斷郵件的類型/目的

### 輸入
```python
{
    "subject": "郵件主旨",
    "body": "郵件內容"
}
```

### 輸出
```python
{
    "category": "類型",
    "confidence": 0.0 ~ 1.0
}
```

### 類型列表
| 類型 | 說明 | 範例 |
|------|------|------|
| `工作請求` | 需要你做某件事 | 「請幫我準備...」「麻煩協助...」 |
| `會議邀請` | 邀請開會或討論 | 「想約個時間...」「會議通知」 |
| `資訊通知` | FYI、不需回覆 | 「通知您...」「公告」 |
| `問題詢問` | 詢問問題、需回答 | 「請問...」「想了解...」 |
| `進度回報` | 回報進度、狀態更新 | 「目前進度...」「已完成...」 |
| `廠商聯繫` | 廠商、供應商來信 | 報價、合作洽談 |
| `客戶服務` | 客戶問題、客訴 | 客戶反映、意見回饋 |
| `其他` | 無法分類 | - |

---

## Skill 3: detect_action_required

### 功能
判斷這封信是否需要你採取行動（回覆、處理）

### 輸入
```python
{
    "subject": "郵件主旨",
    "body": "郵件內容",
    "category": "郵件類型（來自 skill 2）"
}
```

### 輸出
```python
{
    "action_required": true | false,
    "action_type": "回覆" | "處理" | "審核" | "轉寄" | null,
    "suggested_deadline": "2024-04-25" | null
}
```

### 判斷邏輯
| action_required | 條件 |
|-----------------|------|
| `true` | category 是「工作請求」「問題詢問」「客戶服務」 |
| `true` | 內容包含「請回覆」「麻煩回信」「等您回覆」 |
| `true` | 內容包含截止日期 |
| `false` | category 是「資訊通知」「進度回報」 |
| `false` | 自動發送的系統信 |

---

## Skill 4: generate_smart_reply

### 功能
根據郵件內容 + 寄件者資訊 + 上下文，生成智慧回覆（不只是套模板）

### 輸入
```python
{
    "subject": "郵件主旨",
    "body": "郵件內容",
    "sender": {
        "email": "xxx@example.com",
        "name": "王小明",
        "title": "廠商",
        "company": "ABC 公司"
    },
    "category": "工作請求",
    "urgency": "urgent",
    "template_hint": "Notion 模板內容（參考用）"
}
```

### 輸出
```python
{
    "reply_draft": "完整回覆內容",
    "tone": "formal" | "friendly" | "apologetic",
    "key_points": ["回覆重點1", "回覆重點2"]
}
```

### 生成邏輯

1. **分析郵件意圖**：對方想要什麼？
2. **參考模板**：但不照抄，根據實際內容調整
3. **語氣匹配**：
   - 老闆/主管 → 正式、簡潔
   - 同事 → 友善、輕鬆
   - 廠商 → 專業、禮貌
   - 客戶 → 親切、重視
4. **內容結構**：
   ```
   稱呼
   感謝/回應開頭
   針對對方問題的回覆
   下一步行動（如果有）
   結尾
   署名
   ```

---

## 整合後的通知格式

### LINE Flex Message 結構

```
┌─────────────────────────────┐
│ 🔴 緊急 │ 工作請求 │ 需回覆  │  ← 三個標籤
├─────────────────────────────┤
│ 寄件人：王小明（ABC 廠商）    │
│ 主　旨：報價單確認           │
├─────────────────────────────┤
│ ⏰ 建議回覆：今天 18:00 前    │  ← 如果有截止日
├─────────────────────────────┤
│ ✅ 已建立草稿                │
└─────────────────────────────┘
```

---

## 程式架構

### 新增檔案
```
email_skills.py    # 所有 skills 的實作
```

### 修改檔案
```
main.py            # process_new_email() 整合 skills
flex_builder.py    # 新增帶標籤的郵件通知樣式
```

### 呼叫流程
```python
# main.py - process_new_email()

async def process_new_email(email_data):
    # 1. 分類
    urgency = await classify_urgency(email_data)
    category = await classify_category(email_data)
    action = await detect_action_required(email_data, category)

    # 2. 查詢寄件者
    sender_info = query_contact(email_data["sender"])
    template = get_template(sender_info["title"])

    # 3. 生成回覆
    reply = await generate_smart_reply(
        email_data,
        sender_info,
        category,
        urgency,
        template
    )

    # 4. 建立草稿
    draft = create_draft(reply["reply_draft"], email_data)

    # 5. 發送通知（包含分類資訊）
    send_email_notification(
        email_data,
        urgency=urgency["level"],
        category=category["category"],
        action_required=action["action_required"],
        deadline=action["suggested_deadline"]
    )
```

---

## 確認事項

請確認以下內容是否符合你的需求：

1. **緊急程度分類** - 三個等級夠用嗎？
2. **郵件類型** - 8 種類型是否涵蓋你的工作情境？
3. **通知格式** - 標籤 + 主旨的呈現方式 OK 嗎？
4. **回覆生成** - 要完全自動還是只是草稿參考？

確認後我會開始寫 `email_skills.py`。
