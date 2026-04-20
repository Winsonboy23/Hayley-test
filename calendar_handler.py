import os
import json
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]

TAIPEI_TZ = timezone(timedelta(hours=8))


def get_calendar_service():
    creds = None
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Google Token 無效，請重新授權")
    return build("calendar", "v3", credentials=creds)


def get_all_calendars(service) -> dict:
    """回傳 {cal_id: cal_name} 的對照表"""
    result = service.calendarList().list().execute()
    return {cal["id"]: cal.get("summary", cal["id"]) for cal in result.get("items", [])}


def fetch_events(service, cal_id: str, cal_name: str, time_min, time_max, seen: set) -> list:
    """從單一日曆抓事件，回傳格式化後的 list"""
    try:
        result = service.events().list(
            calendarId=cal_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()
    except Exception:
        return []

    events = []
    for event in result.get("items", []):
        key = event.get("id", "")
        if key in seen:
            continue
        seen.add(key)
        start = event.get("start", {})
        if "dateTime" in start:
            dt = datetime.fromisoformat(start["dateTime"])
            time_str = dt.strftime("%H:%M")
            date_str = dt.strftime("%m/%d")
        elif "date" in start:
            time_str = "全天"
            date_str = start["date"][5:]
        else:
            continue
        events.append({
            "summary": event.get("summary", "（未命名活動）"),
            "time": time_str,
            "date": date_str,
            "location": event.get("location", ""),
            "calendar": cal_name,
        })
    return events


async def get_tomorrow_events() -> list:
    service = get_calendar_service()
    calendars = get_all_calendars(service)
    now = datetime.now(TAIPEI_TZ)
    time_min = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    time_max = time_min + timedelta(days=1)

    seen = set()
    events = []
    for cal_id, cal_name in calendars.items():
        events += fetch_events(service, cal_id, cal_name, time_min, time_max, seen)
    events.sort(key=lambda e: (e["date"], e["time"]))
    return events


async def get_upcoming_events_today() -> list:
    service = get_calendar_service()
    now = datetime.now(TAIPEI_TZ)
    time_min = now
    time_max = now.replace(hour=23, minute=59, second=59)

    seen = set()
    all_events = []
    calendars = get_all_calendars(service)
    for cal_id, cal_name in calendars.items():
        try:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            for event in result.get("items", []):
                key = event.get("id", "")
                if key in seen:
                    continue
                seen.add(key)
                start = event.get("start", {})
                if "dateTime" not in start:
                    continue
                dt = datetime.fromisoformat(start["dateTime"])
                diff_minutes = (dt - now).total_seconds() / 60
                all_events.append({
                    "summary": event.get("summary", "（未命名活動）"),
                    "time": dt.strftime("%H:%M"),
                    "location": event.get("location", ""),
                    "calendar": cal_name,
                    "datetime": dt,
                    "minutes_until": diff_minutes
                })
        except Exception:
            continue
    return all_events


async def get_events_by_date_range(days: int = 7) -> list:
    service = get_calendar_service()
    calendars = get_all_calendars(service)
    now = datetime.now(TAIPEI_TZ)
    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
    time_max = time_min + timedelta(days=days)

    seen = set()
    events = []
    for cal_id, cal_name in calendars.items():
        events += fetch_events(service, cal_id, cal_name, time_min, time_max, seen)
    events.sort(key=lambda e: (e["date"], e["time"]))
    return events


async def get_events_this_month() -> list:
    service = get_calendar_service()
    calendars = get_all_calendars(service)
    now = datetime.now(TAIPEI_TZ)
    time_min = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # 下個月第一天
    if now.month == 12:
        time_max = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        time_max = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

    seen = set()
    events = []
    for cal_id, cal_name in calendars.items():
        events += fetch_events(service, cal_id, cal_name, time_min, time_max, seen)
    events.sort(key=lambda e: (e["date"], e["time"]))
    return events


async def search_events(keyword: str) -> list:
    """全日曆不限時間搜尋關鍵字"""
    service = get_calendar_service()
    calendars = get_all_calendars(service)
    now = datetime.now(TAIPEI_TZ)
    # 搜尋範圍：過去 1 年到未來 1 年
    time_min = now - timedelta(days=365)
    time_max = now + timedelta(days=365)

    seen = set()
    events = []
    for cal_id, cal_name in calendars.items():
        try:
            result = service.events().list(
                calendarId=cal_id,
                q=keyword,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            for event in result.get("items", []):
                key = event.get("id", "")
                if key in seen:
                    continue
                seen.add(key)
                start = event.get("start", {})
                if "dateTime" in start:
                    dt = datetime.fromisoformat(start["dateTime"])
                    time_str = dt.strftime("%H:%M")
                    date_str = dt.strftime("%m/%d")
                elif "date" in start:
                    time_str = "全天"
                    date_str = start["date"][5:]
                else:
                    continue
                events.append({
                    "summary": event.get("summary", "（未命名活動）"),
                    "time": time_str,
                    "date": date_str,
                    "location": event.get("location", ""),
                    "calendar": cal_name,
                })
        except Exception:
            continue
    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
