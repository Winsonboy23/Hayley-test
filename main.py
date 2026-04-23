import os
import json
import base64
import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from gmail_handler import (
    get_email_by_id, create_draft,
    count_today_emails, count_drafts, count_unread_emails,
    setup_gmail_watch, search_emails, get_drafts_list, get_unread_emails
)
from calendar_handler import (
    get_tomorrow_events, get_upcoming_events_today,
    get_flex_today, get_flex_tomorrow, get_flex_range,
    get_flex_this_month, get_flex_next_month,
    get_flex_by_month, search_flex_events,
)
from flex_builder import (
    build_flex_single, build_flex_carousel,
    build_flex_evening_push, build_flex_morning_summary,
    build_flex_email_notification,
    build_flex_no_events, build_flex_email_summary,
    build_flex_contact, build_flex_tasks, build_flex_menu,
    build_flex_event_reminder, build_flex_draft_ready,
    build_flex_email_search, build_flex_drafts_list,
    build_flex_unread_emails,
)
from tasks_handler import get_all_tasks
from notion_handler import (
    find_contact_by_email, get_template_by_role,
    get_contact_info_by_name
)
from gemini_handler import (
    generate_reply_draft, classify_email_importance,
    answer_work_question, summarize_schedule
)
from line_handler import (
    push_message, push_flex, reply_message, reply_flex, handler,
    format_new_email_notification
)

from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

# 已處理的信件 ID（防止 Pub/Sub 重複推送）
_processed_message_ids: set = set()

# 等待起草的陌生信件（message_id → {email, expires_at}）
_pending_drafts: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 每天 08:00 推送今日摘要
    scheduler.add_job(
        morning_summary,
        CronTrigger(hour=8, minute=0, timezone="Asia/Taipei"),
        id="morning_summary"
    )
    # 每天 18:00 推送明日行程
    scheduler.add_job(
        daily_schedule_summary,
        CronTrigger(hour=18, minute=0, timezone="Asia/Taipei"),
        id="daily_summary"
    )
    # 每 6 天更新一次 Gmail Watch（有效期 7 天）
    scheduler.add_job(
        renew_gmail_watch,
        CronTrigger(day="*/6", hour=9, minute=0, timezone="Asia/Taipei"),
        id="gmail_watch_renew"
    )
    # 每分鐘檢查是否有活動快開始（1小時前提醒）
    scheduler.add_job(
        check_upcoming_events,
        IntervalTrigger(minutes=1),
        id="event_reminder"
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Haley AI Assistant", lifespan=lifespan)

# 已提醒過的活動（避免重複通知）
reminded_events = set()

# Gmail 通知去重快取（避免同一封信重複推播）
PROCESSED_HISTORY_TTL_SECONDS = 600
PROCESSED_EMAIL_TTL_SECONDS = 3600
processed_history_ids = {}
processed_message_ids = {}


def _cleanup_cache(cache: dict, ttl_seconds: int) -> None:
    now = time.time()
    expired_keys = [key for key, ts in cache.items() if now - ts > ttl_seconds]
    for key in expired_keys:
        cache.pop(key, None)


def _mark_once(cache: dict, key: str, ttl_seconds: int) -> bool:
    """Return True if key already exists in ttl window, else mark and return False."""
    _cleanup_cache(cache, ttl_seconds)
    if key in cache:
        return True
    cache[key] = time.time()
    return False


# ── 健康檢查 ──
@app.get("/")
async def root():
    return {"status": "ok", "message": "海莉 AI 助理運作中 🤖"}


@app.get("/test/models")
async def list_models():
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    models = [m.name for m in client.models.list()]
    return {"models": models}


# ── Gmail Webhook（收新信觸發）──
@app.post("/webhook/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """接收 Gmail Push Notification"""
    try:
        body = await request.json()
        message_data = body.get("message", {})
        
        if not message_data:
            return {"status": "no message"}
        
        # 解碼 Gmail 通知
        data = base64.b64decode(message_data.get("data", "")).decode("utf-8")
        notification = json.loads(data)
        
        history_id = notification.get("historyId")
        email_address = notification.get("emailAddress")

        if history_id and _mark_once(processed_history_ids, str(history_id), PROCESSED_HISTORY_TTL_SECONDS):
            print(f"[DEBUG] 略過重複 historyId：{history_id}", flush=True)
            return {"status": "duplicate_history_ignored"}
        
        if history_id:
            background_tasks.add_task(process_new_email, history_id)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Gmail webhook error: {e}")
        return {"status": "error", "detail": str(e)}


# ── 規則前置過濾（避免明顯廣告信消耗 AI token）──
_SKIP_SUBJECT_KEYWORDS = [
    "unsubscribe", "newsletter", "no-reply", "noreply", "do-not-reply", "donotreply",
    "電子報", "訂閱通知", "系統通知", "優惠", "促銷", "折扣", "限時",
    "notification", "alert", "automated", "auto-reply", "do not reply",
    "account activity", "security alert", "verify your", "confirm your",
]
_SKIP_SENDER_KEYWORDS = [
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "newsletter", "notification", "mailer", "automated",
]

def _is_obviously_low(subject: str, from_email: str) -> bool:
    """規則判斷是否為明顯低重要度信件，是則跳過 AI，直接忽略"""
    subject_lower = subject.lower()
    email_lower = from_email.lower()
    if any(kw in subject_lower for kw in _SKIP_SUBJECT_KEYWORDS):
        return True
    if any(kw in email_lower for kw in _SKIP_SENDER_KEYWORDS):
        return True
    return False


async def process_new_email(history_id: str):
    """處理新進信件的核心流程"""
    try:
        from gmail_handler import get_gmail_service
        service = get_gmail_service()
        
        # 取得最新一封信
        results = service.users().messages().list(
            userId="me",
            maxResults=1,
            labelIds=["INBOX"]
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return

        latest_message = messages[0]
        message_id = latest_message["id"]
        if _mark_once(processed_message_ids, message_id, PROCESSED_EMAIL_TTL_SECONDS):
            print(f"[DEBUG] 略過重複 messageId：{message_id}", flush=True)
            return
        
        # 取得信件內容
        email = await get_email_by_id(message_id)
        print(f"[DEBUG] 最新信件：from={email['from_email']} subject={email['subject']}", flush=True)

        # 查詢寄件人是否在 Notion 聯絡人名單
        contact = await find_contact_by_email(email["from_email"])
        is_unknown = contact is None
        print(f"[DEBUG] Notion 查詢結果：{'找到' if contact else '陌生人'}", flush=True)

        # 黑名單聯絡人 → 直接略過，不通知、不消耗 AI token
        if contact and contact.get("blacklisted"):
            print(f"[BLACKLIST] 黑名單略過：{email['from_email']} | {email['subject']}", flush=True)
            return

        if is_unknown:
            sender_name = email["from_name"] or email["from_email"]

            # 規則前置過濾：明顯廣告 / 系統信 → 直接略過，不消耗 AI token
            if _is_obviously_low(email["subject"], email["from_email"]):
                print(f"[FILTER] 規則過濾略過：{email['from_email']} | {email['subject']}", flush=True)
                return

            # 陌生人 → AI 判斷重要性
            try:
                classification = await classify_email_importance(
                    subject=email["subject"],
                    email_body=email["body"]
                )
            except Exception:
                classification = {"importance": "medium", "should_reply": True, "reason": "無法自動判斷", "category": "其他"}

            importance   = classification.get("importance", "medium")
            should_reply = classification.get("should_reply", True)
            reason       = classification.get("reason", "")

            # 若需要回覆，暫存等待使用者按按鈕
            if should_reply:
                _pending_drafts[message_id] = {
                    "email": email,
                    "thread_id": latest_message.get("threadId", message_id),
                    "expires_at": time.time() + 86400
                }

            flex = build_flex_email_notification(
                sender_name=sender_name,
                subject=email["subject"],
                is_unknown=True,
                message_id=message_id,
                importance=importance,
                reason=reason,
                should_reply=should_reply,
            )
            await push_flex(flex)

        else:
            # 已知聯絡人 → 自動生成草稿
            sender_name = contact["name"]
            sender_role = contact["role"]
            sender_unit = contact["unit"]

            template = await get_template_by_role(sender_role)
            template_content = template["content"] if template else None

            draft_body = await generate_reply_draft(
                email_content=email["body"],
                sender_name=sender_name,
                sender_role=sender_role,
                template_content=template_content
            )

            subject = email["subject"]
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            thread_id = latest_message.get("threadId", message_id)
            await create_draft(
                to_email=email["from_email"],
                subject=subject,
                body=draft_body,
                reply_to_id=thread_id
            )

            flex = build_flex_email_notification(
                sender_name=sender_name,
                subject=email["subject"],
                is_unknown=False,
                sender_role=sender_role,
                sender_unit=sender_unit,
                draft_ready=True,
            )
            await push_flex(flex)
        
    except Exception as e:
        import traceback
        print(f"process_new_email error: {e}\n{traceback.format_exc()}", flush=True)


# ── LINE Webhook（接收海莉的訊息）──
@app.post("/webhook/line")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    """接收 LINE 訊息"""
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    
    # 驗證簽名
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    hash_val = hmac.new(
        channel_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected_sig = base64.b64encode(hash_val).decode("utf-8")
    
    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    body_str = body.decode("utf-8")
    events = json.loads(body_str).get("events", [])
    
    for event in events:
        user_id = event.get("source", {}).get("userId", "")
        if user_id:
            print(f"==== LINE User ID: {user_id} ====", flush=True)
        if event.get("type") == "message" and event.get("message", {}).get("type") == "text":
            background_tasks.add_task(
                handle_line_message,
                event["message"]["text"],
                event["replyToken"]
            )
        elif event.get("type") == "postback":
            background_tasks.add_task(
                handle_postback,
                event.get("postback", {}).get("data", ""),
                event.get("replyToken", "")
            )
    
    return {"status": "ok"}


async def handle_line_message(text: str, reply_token: str):
    """處理海莉在 LINE 上的訊息"""
    try:
        t = text.strip()

        import re

        # ── 今日行程 ──
        if t in ["今日行程", "今天行程", "今天", "行程"]:
            cal_list, events = await get_flex_today()
            if not events:
                await reply_flex(reply_token, build_flex_no_events("今日"))
            else:
                await reply_flex(reply_token, build_flex_single(cal_list, events, "今日"))
            return

        # ── 明日行程 ──
        if t in ["明日行程", "明天行程", "明天"]:
            cal_list, events = await get_flex_tomorrow()
            if not events:
                await reply_flex(reply_token, build_flex_no_events("明日"))
            else:
                await reply_flex(reply_token, build_flex_single(cal_list, events, "明日"))
            return

        # ── 本週行程 ──
        if t in ["本週行程", "這週行程", "這週", "本週"]:
            cal_list, events = await get_flex_range(days=7)
            if not events:
                await reply_flex(reply_token, build_flex_no_events("本週"))
            else:
                await reply_flex(reply_token, build_flex_carousel(cal_list, events, "本週"))
            return

        # ── 本月行程 ──
        if t in ["本月行程", "這個月行程", "本月"]:
            cal_list, events, month = await get_flex_this_month()
            if not events:
                await reply_flex(reply_token, build_flex_no_events(f"{month}月"))
            else:
                await reply_flex(reply_token, build_flex_carousel(cal_list, events, f"{month}月"))
            return

        # ── 下個月行程 ──
        if t in ["下個月行程", "下月行程", "下個月", "下月"]:
            cal_list, events, month = await get_flex_next_month()
            if not events:
                await reply_flex(reply_token, build_flex_no_events(f"{month}月"))
            else:
                await reply_flex(reply_token, build_flex_carousel(cal_list, events, f"{month}月"))
            return

        # ── x月行程 ──
        m = re.match(r"^(\d{1,2})月行程$", t)
        if m:
            month = int(m.group(1))
            if 1 <= month <= 12:
                cal_list, events = await get_flex_by_month(month)
                if not events:
                    await reply_flex(reply_token, build_flex_no_events(f"{month}月"))
                else:
                    await reply_flex(reply_token, build_flex_carousel(cal_list, events, f"{month}月"))
            else:
                await reply_message(reply_token, "請輸入 1-12 月")
            return

        # ── 搜尋行程 ──
        if t.startswith("搜尋"):
            keyword = t.replace("搜尋", "").strip()
            if not keyword:
                await reply_message(reply_token, "請輸入：搜尋 關鍵字")
                return
            cal_list, events = await search_flex_events(keyword)
            if not events:
                await reply_flex(reply_token, build_flex_no_events(
                    "搜尋結果", extra=f"找不到含「{keyword}」的行程"))
            else:
                await reply_flex(reply_token, build_flex_carousel(cal_list, events, f"搜尋：{keyword}"))
            return

        # ── 未讀信件列表 ──
        if t in ["未讀信件", "未讀"]:
            emails = await get_unread_emails()
            if not emails:
                await reply_message(reply_token, "📩 目前沒有未讀信件")
            else:
                await reply_flex(reply_token, build_flex_unread_emails(emails))
            return

        # ── 信件草稿列表 ──
        if t in ["信件草稿", "草稿列表", "草稿"]:
            drafts = await get_drafts_list()
            if not drafts:
                await reply_message(reply_token, "📝 目前沒有草稿")
            else:
                await reply_flex(reply_token, build_flex_drafts_list(drafts))
            return

        # ── 搜尋信件 ──
        if t.startswith("搜尋信件"):
            keyword = t.replace("搜尋信件", "").strip()
            if not keyword:
                await reply_message(reply_token, "請輸入：搜尋信件 關鍵字")
                return
            emails = await search_emails(keyword)
            if not emails:
                await reply_message(reply_token, f"找不到含「{keyword}」的信件")
            else:
                await reply_flex(reply_token, build_flex_email_search(emails, keyword))
            return

        # ── 信件 / 草稿狀況 ──
        if t in ["信件", "今日信件", "收信", "草稿", "信件狀況"]:
            unread_count = await count_unread_emails()
            draft_count = await count_drafts()
            await reply_flex(reply_token, build_flex_email_summary(unread_count, draft_count))
            return

        # ── 指令清單 / 不認識的輸入 ──
        await reply_flex(reply_token, build_flex_menu())

    except Exception as e:
        print(f"handle_line_message error: {e}")
        await reply_message(reply_token, "⚠️ 處理時發生錯誤，請稍後再試。")


# ── 排程：每天 08:00 今日摘要 ──
async def morning_summary():
    try:
        cal_list, events = await get_flex_today()
        unread = await count_unread_emails()
        await push_flex(build_flex_morning_summary(cal_list, events, unread))
    except Exception as e:
        print(f"morning_summary error: {e}")


# ── 排程：每天 18:00 明日行程 ──
async def daily_schedule_summary():
    try:
        cal_list, events = await get_flex_tomorrow()
        unread = await count_unread_emails()
        await push_flex(build_flex_evening_push(cal_list, events, unread))
    except Exception as e:
        print(f"daily_schedule_summary error: {e}")


# ── 排程：每分鐘檢查活動 1 小時前提醒 ──
async def check_upcoming_events():
    """每分鐘檢查是否有活動需要提醒"""
    try:
        events = await get_upcoming_events_today()
        
        for event in events:
            minutes = event["minutes_until"]
            event_key = f"{event['summary']}_{event['time']}"
            
            # 55–65 分鐘內且尚未提醒過
            if 55 <= minutes <= 65 and event_key not in reminded_events:
                reminded_events.add(event_key)
                await push_flex(build_flex_event_reminder(
                    event_name=event["summary"],
                    event_time=event["time"],
                    location=event.get("location", "")
                ))
    except Exception as e:
        print(f"check_upcoming_events error: {e}")


# ── 手動觸發測試用 ──
async def handle_postback(data: str, reply_token: str):
    """處理 LINE 按鈕點擊（postback）"""
    try:
        params = dict(p.split("=", 1) for p in data.split("&") if "=" in p)
        if params.get("action") != "draft":
            return

        message_id = params.get("id", "")
        pending = _pending_drafts.get(message_id)

        if not pending or time.time() > pending.get("expires_at", 0):
            _pending_drafts.pop(message_id, None)
            await reply_message(reply_token, "⚠️ 此信件已過期（超過 24 小時），請直接在 Gmail 回覆")
            return

        await reply_message(reply_token, "⏳ 草稿生成中，請稍候…")

        email = pending["email"]
        thread_id = pending.get("thread_id", message_id)
        sender_name = email["from_name"] or email["from_email"]

        draft_body = await generate_reply_draft(
            email_content=email["body"],
            sender_name=sender_name,
            sender_role="",
            template_content=None
        )

        subject = email["subject"]
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"

        await create_draft(
            to_email=email["from_email"],
            subject=subject,
            body=draft_body,
            reply_to_id=thread_id
        )

        _pending_drafts.pop(message_id, None)
        await push_flex(build_flex_draft_ready(
            sender_name=sender_name,
            subject=email["subject"]
        ))

    except Exception as e:
        import traceback
        print(f"handle_postback error: {e}\n{traceback.format_exc()}", flush=True)
        await push_message("⚠️ 草稿生成失敗，請稍後再試")


async def renew_gmail_watch():
    try:
        result = await setup_gmail_watch()
        print(f"[GMAIL WATCH] 已更新，到期：{result.get('expiration')}", flush=True)
    except Exception as e:
        print(f"[GMAIL WATCH] 更新失敗：{e}", flush=True)


@app.get("/setup/gmail-watch")
async def trigger_gmail_watch():
    """手動啟動或更新 Gmail Watch"""
    result = await setup_gmail_watch()
    return {"status": "ok", "expiration": result.get("expiration"), "historyId": result.get("historyId")}


@app.get("/test/morning-summary")
async def test_morning_summary():
    await morning_summary()
    return {"status": "ok", "message": "已發送今日早晨摘要"}


@app.get("/test/daily-summary")
async def test_daily_summary():
    await daily_schedule_summary()
    return {"status": "ok", "message": "已發送明日行程推播"}


@app.get("/test/new-email")
async def test_new_email():
    """手動觸發最新一封信的處理流程（測試用）"""
    await process_new_email("test")
    return {"status": "ok", "message": "已處理最新一封信"}
