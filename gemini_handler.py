import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest")

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
    response = model.generate_content(prompt)
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
只輸出信件內文，不要加任何說明或前綴詞。
"""
    response = model.generate_content(prompt)
    return response.text.strip()


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
    response = model.generate_content(prompt)
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
    response = model.generate_content(prompt)
    return response.text.strip()
