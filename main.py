import os
import json
import base64
import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

TAIPEI_TZ = timezone(timedelta(hours=8))

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from gmail_handler import (
    get_email_by_id, create_draft,
    count_today_emails, count_drafts,
    setup_gmail_watch, search_emails, get_drafts_list, get_unread_emails,
    get_recent_emails, get_emails_from_senders, get_new_inbox_messages_since,
)
from calendar_handler import (
    get_tomorrow_events,
    get_flex_today, get_flex_tomorrow, get_flex_range, get_flex_this_week,
    get_flex_this_month, get_flex_next_month,
    get_flex_by_month, search_flex_events,
    create_calendar_event,
    get_all_calendars_status, add_excluded_calendar, remove_excluded_calendar,
)
from flex_builder import (
    build_flex_single, build_flex_carousel,
    build_flex_evening_push, build_flex_morning_summary,
    build_flex_email_notification,
    build_flex_no_events, build_flex_email_summary,
    build_flex_contact, build_flex_tasks, build_flex_menu,
    build_flex_draft_ready,
    build_flex_email_search, build_flex_drafts_list,
    build_flex_unread_emails, build_flex_email_carousel,
    build_flex_add_event_help, build_flex_event_created,
    build_flex_calendar_list,
)
from tasks_handler import get_all_tasks
from notion_handler import (
    find_contact_by_email, get_template_by_role,
    get_contact_info_by_name, get_contact_emails_by_importance,
)
from gemini_handler import (
    generate_reply_draft,
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
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Haley AI Assistant", lifespan=lifespan)

# 已提醒過的活動（避免重複通知）

# Gmail 通知去重快取（避免同一封信重複推播）
PROCESSED_HISTORY_TTL_SECONDS = 600
PROCESSED_EMAIL_TTL_SECONDS = 3600
processed_history_ids = {}
processed_message_ids = {}
gmail_history_cursor = None


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
    global gmail_history_cursor
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
            start_history_id = gmail_history_cursor
            gmail_history_cursor = str(history_id)
            if start_history_id:
                background_tasks.add_task(process_new_email, start_history_id)
            else:
                # First notification after process start has no previous cursor in memory.
                # Fall back to the latest inbox message and rely on message-id dedupe.
                background_tasks.add_task(process_new_email, "test")
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Gmail webhook error: {e}")
        return {"status": "error", "detail": str(e)}



def _parse_add_event(text: str) -> dict | None:
    """
    解析「新增行程」指令，回傳 dict 或 None（格式錯誤）
    格式：新增行程 日期[~結束日] 時間[~結束時間]|全天 標題 [@地點]
    支援：
      日期 - MM/DD、今天/明天/後天、週X/下週X、X月Y日/號（中文或數字）
      時間 - HH:MM、HHMM、全天、[上午|下午|晚上|早上]X點[半|一刻|三刻|X分]（中文數字）
      範圍 - 日期與時間皆可用 ~ 或 ～ 分隔
    """
    import re
    from datetime import date as date_cls

    t = text.strip()
    t = t.replace("～", "~")

    for prefix in ["新增行程", "新增", "+"]:
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
            break
    else:
        return None

    location = ""
    loc_match = re.search(r"@(.+)$", t)
    if loc_match:
        location = loc_match.group(1).strip()
        t = t[:loc_match.start()].strip()

    tokens = t.split()
    if len(tokens) < 3:
        return None

    today = datetime.now(TAIPEI_TZ).date()

    _CN_DIG = {"〇":0,"零":0,"一":1,"二":2,"兩":2,"三":3,"四":4,"五":5,
               "六":6,"七":7,"八":8,"九":9}

    def _cn_to_int(s: str) -> int | None:
        if not s:
            return None
        if s.isdigit():
            return int(s)
        if s == "十":
            return 10
        if len(s) == 2 and s[0] == "十" and s[1] in _CN_DIG:
            return 10 + _CN_DIG[s[1]]
        if len(s) == 2 and s[0] in _CN_DIG and s[1] == "十":
            return _CN_DIG[s[0]] * 10
        if len(s) == 3 and s[0] in _CN_DIG and s[1] == "十" and s[2] in _CN_DIG:
            return _CN_DIG[s[0]] * 10 + _CN_DIG[s[2]]
        if len(s) == 1 and s in _CN_DIG:
            return _CN_DIG[s]
        return None

    def _resolve_date(s: str):
        """將各種日期格式轉成 date 物件"""
        weekday_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
        if s == "今天":
            return today
        if s == "明天":
            return today + timedelta(days=1)
        if s == "後天":
            return today + timedelta(days=2)
        # 週X（本週，已過則仍用本週）
        m = re.match(r"^週([一二三四五六日天])$", s)
        if m:
            target_wd = weekday_map[m.group(1)]
            # 本週一 = today - today.weekday()
            monday = today - timedelta(days=today.weekday())
            return monday + timedelta(days=target_wd)
        # 下週X
        m = re.match(r"下週([一二三四五六日天])", s)
        if m:
            target_wd = weekday_map[m.group(1)]
            monday = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
            return monday + timedelta(days=target_wd)
        # MM/DD
        m = re.match(r"^(\d{1,2})/(\d{1,2})$", s)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = today.year
            try:
                d = date_cls(year, month, day)
                if d < today:
                    d = date_cls(year + 1, month, day)
                return d
            except ValueError:
                return None
        # X月Y日 / X月Y號
        m = re.match(r"^([零〇一二三四五六七八九十\d]{1,4})月([零〇一二兩三四五六七八九十\d]{1,4})[日號]$", s)
        if m:
            month = _cn_to_int(m.group(1))
            day = _cn_to_int(m.group(2))
            if month and day:
                year = today.year
                try:
                    d = date_cls(year, month, day)
                    if d < today:
                        d = date_cls(year + 1, month, day)
                    return d
                except ValueError:
                    return None
        return None

    def _resolve_time(s: str) -> str | None:
        """將時間字串轉成 HH:MM"""
        # HH:MM
        if re.match(r"^\d{1,2}:\d{2}$", s):
            return s.zfill(5)
        # HHMM（省略冒號，3~4 位數字）
        m = re.match(r"^(\d{1,2})(\d{2})$", s)
        if m and len(s) >= 3:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
        # 中文時間：[前綴]X點[半|一刻|三刻|X分|XX分]
        m = re.match(
            r"^(上午|下午|晚上|早上|中午)?"
            r"([零〇一二兩三四五六七八九十\d]{1,3})點"
            r"(半|一刻|三刻|([零〇一二兩三四五六七八九十\d]{1,2})分)?$",
            s
        )
        if m:
            prefix = m.group(1) or ""
            hour = _cn_to_int(m.group(2))
            if hour is None:
                return None
            suffix = m.group(3) or ""
            if suffix == "半":
                minute = 30
            elif suffix == "一刻":
                minute = 15
            elif suffix == "三刻":
                minute = 45
            elif suffix.endswith("分"):
                minute = _cn_to_int(m.group(4)) or 0
            else:
                minute = 0
            if prefix in ("下午", "晚上", "中午"):
                if hour < 12:
                    hour += 12
            elif prefix in ("上午", "早上"):
                if hour == 12:
                    hour = 0
            else:
                if 1 <= hour <= 6:
                    hour += 12
            return f"{hour:02d}:{minute:02d}"
        return None

    # 第一個 token：日期（可能含 ~）
    date_token = tokens[0]
    if "~" in date_token:
        parts = date_token.split("~", 1)
        start_date = _resolve_date(parts[0])
        end_date = _resolve_date(parts[1])
    else:
        start_date = _resolve_date(date_token)
        end_date = start_date

    if not start_date or not end_date:
        return None

    # 第二個 token：時間（可含 ~）或「全天」
    time_token = tokens[1]
    end_time = None
    if time_token == "全天":
        start_time = None
        time_display = "全天"
    elif "~" in time_token:
        parts = time_token.split("~", 1)
        start_time = _resolve_time(parts[0])
        end_time = _resolve_time(parts[1])
        if start_time is None:
            return None
        time_display = f"{start_time}～{end_time}" if end_time else start_time
    else:
        start_time = _resolve_time(time_token)
        if start_time is None:
            return None
        time_display = start_time

    title = " ".join(tokens[2:]).strip()
    if not title:
        return None

    return {
        "title": title,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "start_time": start_time,
        "end_time": end_time,
        "time_display": time_display,
        "location": location,
        "date_display": (
            f"{start_date.strftime('%m/%d')}～{end_date.strftime('%m/%d')}"
            if start_date != end_date else start_date.strftime("%m/%d")
        ),
    }



async def process_new_email(history_id: str):
    """處理新進信件的核心流程（只處理 Notion 聯絡人，依重要度分流）"""
    try:
        from gmail_handler import get_gmail_service
        service = get_gmail_service()

        if history_id == "test":
            results = service.users().messages().list(
                userId="me",
                maxResults=1,
                labelIds=["INBOX"]
            ).execute()
            messages = results.get("messages", [])
        else:
            messages = await get_new_inbox_messages_since(history_id)

        if not messages:
            print(f"[DEBUG] historyId={history_id} 沒有新增 INBOX 信件", flush=True)
            return

        for message in messages:
            await process_email_message(message)

    except Exception as e:
        import traceback
        print(f"process_new_email error: {e}\n{traceback.format_exc()}", flush=True)


async def process_email_message(message: dict):
    """處理單封 Gmail message。"""
    try:
        message_id = message["id"]
        if _mark_once(processed_message_ids, message_id, PROCESSED_EMAIL_TTL_SECONDS):
            print(f"[DEBUG] 略過重複 messageId：{message_id}", flush=True)
            return

        email = await get_email_by_id(message_id)
        print(f"[DEBUG] 新信件：from={email['from_email']} subject={email['subject']}", flush=True)

        # 非聯絡人 → 完全略過
        contact = await find_contact_by_email(email["from_email"])
        if not contact:
            print(f"[SKIP] 非聯絡人：{email['from_email']}", flush=True)
            return

        importance = contact.get("importance", "低")
        sender_name = contact["name"]
        sender_role = contact["role"]
        sender_unit = contact["unit"]
        thread_id = message.get("threadId", message_id)

        print(f"[DEBUG] 聯絡人重要度：{importance} | {sender_name}", flush=True)

        if importance == "高":
            # 自動生成草稿 + 推播
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

            await create_draft(
                to_email=email["from_email"],
                subject=subject,
                body=draft_body,
                reply_to_id=thread_id
            )

            await push_flex(build_flex_email_notification(
                sender_name=sender_name,
                subject=email["subject"],
                sender_role=sender_role,
                sender_unit=sender_unit,
                draft_ready=True,
            ))

        elif importance == "中":
            # 推播通知 + 起草按鈕
            _pending_drafts[message_id] = {
                "email": email,
                "thread_id": thread_id,
                "expires_at": time.time() + 86400
            }
            await push_flex(build_flex_email_notification(
                sender_name=sender_name,
                subject=email["subject"],
                sender_role=sender_role,
                sender_unit=sender_unit,
                should_reply=True,
                message_id=message_id,
            ))

        else:
            # 低（或未填）→ 略過
            print(f"[SKIP] 重要度低：{sender_name}", flush=True)

    except Exception as e:
        import traceback
        print(f"process_email_message error: {e}\n{traceback.format_exc()}", flush=True)


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
        if t in ["今日行程", "今天行程", "今天", "今日", "本日", "本日行程", "行程"]:
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

        # ── 行事曆清單 ──
        if t in ["行事曆清單", "行事曆", "日曆清單"]:
            calendars = await get_all_calendars_status()
            await reply_flex(reply_token, build_flex_calendar_list(calendars))
            return

        # ── 取消顯示 [名稱] ──
        if t.startswith("取消顯示 ") or t.startswith("隱藏 "):
            cal_name = t.split(" ", 1)[1].strip()
            add_excluded_calendar(cal_name)
            await reply_message(reply_token, f"✅ 已隱藏「{cal_name}」的行程，輸入「行事曆清單」確認")
            return

        # ── 顯示 [名稱] ──
        if t.startswith("顯示 ") and not any(t.startswith(k) for k in ["顯示行程", "顯示草稿", "顯示信件"]):
            cal_name = t.split(" ", 1)[1].strip()
            remove_excluded_calendar(cal_name)
            await reply_message(reply_token, f"✅ 已恢復顯示「{cal_name}」的行程，輸入「行事曆清單」確認")
            return

        # ── 本週行程 ──
        if t in ["本週行程", "這週行程", "這週", "本週"]:
            cal_list, events = await get_flex_this_week()
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

        # ── x月行程（支援阿拉伯數字與中文數字，如五月行程、5月行程）──
        _CN_MONTH = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,"十一":11,"十二":12}
        m = re.match(r"^(十[一二]|[一二三四五六七八九十]|\d{1,2})月行程$", t)
        if m:
            ms = m.group(1)
            month = int(ms) if ms.isdigit() else _CN_MONTH.get(ms, 0)
            if 1 <= month <= 12:
                cal_list, events = await get_flex_by_month(month)
                if not events:
                    await reply_flex(reply_token, build_flex_no_events(f"{month}月"))
                else:
                    await reply_flex(reply_token, build_flex_carousel(cal_list, events, f"{month}月"))
            else:
                await reply_message(reply_token, "請輸入 1-12 月")
            return

        # ── 新增行程 ──
        if t.startswith("新增行程") or t.startswith("新增") or t.startswith("+"):
            parsed = _parse_add_event(t)
            if not parsed:
                await reply_flex(reply_token, build_flex_add_event_help("格式有誤，請參考以下範例"))
                return
            try:
                await create_calendar_event(
                    title=parsed["title"],
                    start_date=parsed["start_date"],
                    end_date=parsed["end_date"],
                    start_time=parsed["start_time"],
                    end_time=parsed.get("end_time"),
                    location=parsed["location"]
                )
                await reply_flex(reply_token, build_flex_event_created(
                    title=parsed["title"],
                    date_str=parsed["date_display"],
                    time_str=parsed["time_display"],
                    location=parsed["location"]
                ))
            except Exception as e:
                print(f"create_calendar_event error: {e}", flush=True)
                await reply_message(reply_token, "⚠️ 行程建立失敗，請稍後再試")
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

        # ── 信件 高/中/低（依重要度篩選）──
        if t in ["信件 高", "信件 中", "信件 低"]:
            imp = t.split()[-1]  # 高/中/低
            email_list = await get_contact_emails_by_importance(imp)
            emails = await get_emails_from_senders(email_list, max_results=10)
            imp_label = {"高": "🔴 高重要度", "中": "🟡 中重要度", "低": "⚪ 低重要度"}.get(imp, imp)
            await push_flex(build_flex_email_carousel(emails, f"{imp_label}聯絡人來信"))
            return

        # ── 未讀信件列表 ──
        if t in ["未讀信件", "未讀"]:
            emails = await get_unread_emails(max_results=10)
            await reply_flex(reply_token, build_flex_email_carousel(emails, "未讀信件"))
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

        # ── 信件（近期 10 封）──
        if t in ["信件", "今日信件", "收信", "信件狀況"]:
            emails = await get_recent_emails(max_results=10)
            await reply_flex(reply_token, build_flex_email_carousel(emails, "近期信件"))
            return

        # ── 指令清單 ──
        if t in ["指令", "選單", "menu"]:
            await reply_flex(reply_token, build_flex_menu())
            return

        # ── 不認識的輸入 ──
        await reply_message(reply_token, "輸入『指令』查看可用功能")

    except Exception as e:
        print(f"handle_line_message error: {e}")
        try:
            await reply_message(reply_token, "⚠️ 處理時發生錯誤，請稍後再試。")
        except Exception:
            await push_message("⚠️ 處理時發生錯誤，請稍後再試。")


# ── 排程：每天 08:00 今日摘要 ──
async def morning_summary():
    try:
        cal_list, events = await get_flex_today()
        await push_flex(build_flex_morning_summary(cal_list, events))
    except Exception as e:
        print(f"morning_summary error: {e}")


# ── 排程：每天 18:00 明日行程 ──
async def daily_schedule_summary():
    try:
        cal_list, events = await get_flex_tomorrow()
        await push_flex(build_flex_evening_push(cal_list, events))
    except Exception as e:
        print(f"daily_schedule_summary error: {e}")


# ── 排程：每分鐘檢查活動 1 小時前提醒 ──

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
    global gmail_history_cursor
    try:
        result = await setup_gmail_watch()
        if result.get("historyId"):
            gmail_history_cursor = str(result["historyId"])
        print(f"[GMAIL WATCH] 已更新，到期：{result.get('expiration')}", flush=True)
    except Exception as e:
        print(f"[GMAIL WATCH] 更新失敗：{e}", flush=True)


@app.get("/setup/gmail-watch")
async def trigger_gmail_watch():
    """手動啟動或更新 Gmail Watch"""
    global gmail_history_cursor
    result = await setup_gmail_watch()
    if result.get("historyId"):
        gmail_history_cursor = str(result["historyId"])
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
