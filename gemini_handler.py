from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-pro"

HALEY_STYLE_PROMPT = """
你是海莉的 AI 助理，海莉是 PAUL 法式烘焙的 Branding & Marketing 主管。

【海莉的寫信風格】
- 語氣：專業但親切，帶有法式品牌的優雅感
- 用詞：簡潔有力，不過度冗長
- 結構：問候 → 主旨說明 → 細節 → 行動呼籲 → 結語
- 中文為主，專有名詞可用英文
- 署名：海莉 / Haley

【PAUL 品牌調性】
- 法式烘焙精品，注重品質與美感
- 與店長溝通：較輕鬆，像夥伴關係
- 與廠商溝通：專業，重視細節與時程
- 與同事溝通：簡潔直接，效率優先
"""

async def summarize_email(email_content: str) -> str:
    """生成 50 字以內的信件摘要"""
    prompt = f"""
請用 50 字以內的繁體中文摘要以下信件的重點，只說重點，不要加任何前綴詞：

{email_content}
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


async def generate_reply_draft(
    email_content: str,
    sender_name: str,
    sender_role: str,
    template_content: str = None
) -> str:
    """根據來信內容生成回覆草稿"""

    template_section = ""
    if template_content:
        template_section = f"""
【參考模板】
{template_content}
"""

    prompt = f"""
{HALEY_STYLE_PROMPT}

{template_section}

【來信寄件人】
姓名：{sender_name}
角色：{sender_role}

【來信內容】
{email_content}

請用海莉的語氣，寫一封回覆這封信的草稿。
【重要】回覆語言規則：請偵測來信使用的語言，並用相同語言回覆。
例如對方用英文寫信 → 用英文回；對方用中文 → 用繁體中文回；對方混用 → 以主要語言為準。
只輸出信件內文，不要加任何說明或前綴詞。
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


async def classify_email_importance(subject: str, email_body: str) -> dict:
    """判斷陌生寄件人信件的重要性與是否需要回覆"""
    prompt = f"""你是海莉的 AI 助理，海莉是 PAUL 法式烘焙的 Branding & Marketing 主管。

請判斷以下信件對海莉的重要性：

主旨：{subject}
內文：{email_body[:1500]}

請只回覆 JSON，不要加任何說明：
{{
  "importance": "high" 或 "medium" 或 "low",
  "should_reply": true 或 false,
  "reason": "一句話說明原因（15字以內）",
  "category": "合作邀約" 或 "媒體採訪" 或 "廠商詢問" 或 "客訴" 或 "行政通知" 或 "廣告行銷" 或 "其他"
}}

判斷標準：
- high + should_reply true：需要海莉親自處理（合作、報價、媒體、客戶問題、活動邀約）
- medium + should_reply true：可稍後處理，非緊急
- low + should_reply false：電子報、廣告、系統通知、無需回覆
"""
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        import json
        return json.loads(text.strip())
    except Exception:
        return {"importance": "medium", "should_reply": True, "reason": "無法自動判斷", "category": "其他"}


async def answer_work_question(question: str, context: str = "") -> str:
    """回答海莉的工作相關問題"""

    work_scope = """
你只能回答以下工作範圍內的問題：
1. Gmail 相關（信件數量、信件內容摘要、草稿狀態）
2. Google Calendar 相關（行程查詢、活動資訊）
3. Notion 相關（聯絡人資訊、信件模板）

如果問題超出以上範圍，請回覆：
「這個問題超出我的工作範圍，我只能協助處理信件、行程和聯絡人相關事項。」
"""

    prompt = f"""
{work_scope}

【相關資料】
{context}

【海莉的問題】
{question}

請用繁體中文簡潔回答，語氣親切專業。
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


async def summarize_schedule(events: list) -> str:
    """生成明日行程總結"""

    if not events:
        return "明天沒有排定的行程，可以好好休息或處理其他事務！"

    events_text = "\n".join([
        f"- {e.get('time', '')} {e.get('summary', '')} {('｜' + e.get('location', '')) if e.get('location') else ''}"
        for e in events
    ])

    prompt = f"""
請用繁體中文整理以下明日行程，格式如下：

📅 明天的行程 [日期]

[時間] [活動名稱]｜[地點（如果有）]
...

共 X 個活動

行程資料：
{events_text}

只輸出整理好的內容，不要加任何說明。
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()
