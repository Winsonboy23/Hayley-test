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
    """建立 Google Calendar API 連線"""
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


async def get_tomorrow_events() -> list:
    """取得明天的所有活動"""
    service = get_calendar_service()
    
    now = datetime.now(TAIPEI_TZ)
    tomorrow_start = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    tomorrow_end = tomorrow_start + timedelta(days=1)
    
    events_result = service.events().list(
        calendarId="primary",
        timeMin=tomorrow_start.isoformat(),
        timeMax=tomorrow_end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = []
    for event in events_result.get("items", []):
        start = event.get("start", {})
        time_str = ""
        
        if "dateTime" in start:
            dt = datetime.fromisoformat(start["dateTime"])
            time_str = dt.strftime("%H:%M")
        elif "date" in start:
            time_str = "全天"
        
        events.append({
            "summary": event.get("summary", "（未命名活動）"),
            "time": time_str,
            "location": event.get("location", ""),
            "description": event.get("description", ""),
            "date": tomorrow_start.strftime("%m/%d")
        })
    
    return events


async def get_upcoming_events_today() -> list:
    """取得今天剩餘的活動（用於檢查1小時前提醒）"""
    service = get_calendar_service()
    
    now = datetime.now(TAIPEI_TZ)
    end_of_day = now.replace(hour=23, minute=59, second=59)
    
    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = []
    for event in events_result.get("items", []):
        start = event.get("start", {})
        if "dateTime" not in start:
            continue
        
        dt = datetime.fromisoformat(start["dateTime"])
        diff_minutes = (dt - now).total_seconds() / 60
        
        events.append({
            "summary": event.get("summary", "（未命名活動）"),
            "time": dt.strftime("%H:%M"),
            "location": event.get("location", ""),
            "datetime": dt,
            "minutes_until": diff_minutes
        })
    
    return events


async def get_events_by_date_range(days: int = 7) -> list:
    """取得未來幾天的活動（給 LINE 問答用）"""
    service = get_calendar_service()
    
    now = datetime.now(TAIPEI_TZ)
    end = now + timedelta(days=days)
    
    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = []
    for event in events_result.get("items", []):
        start = event.get("start", {})
        time_str = ""
        date_str = ""
        
        if "dateTime" in start:
            dt = datetime.fromisoformat(start["dateTime"])
            time_str = dt.strftime("%H:%M")
            date_str = dt.strftime("%m/%d")
        elif "date" in start:
            time_str = "全天"
            date_str = start["date"][5:]
        
        events.append({
            "summary": event.get("summary", "（未命名活動）"),
            "time": time_str,
            "date": date_str,
            "location": event.get("location", "")
        })
    
    return events
