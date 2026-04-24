import os
import json
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks.readonly",
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


def get_tasks_service():
    """建立 Google Tasks API 連線（失敗時回傳 None，不中斷主流程）"""
    try:
        token_json = os.getenv("GOOGLE_TOKEN_JSON")
        if not token_json:
            return None
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return None
        return build("tasks", "v1", credentials=creds)
    except Exception as e:
        print(f"[TASKS] 無法建立 Tasks 服務：{e}", flush=True)
        return None


def _fetch_tasks_for_range(time_min: datetime, time_max: datetime) -> list:
    """從 Google Tasks 抓取指定時間範圍內未完成的工作"""
    try:
        service = get_tasks_service()
        if not service:
            return []

        task_lists_result = service.tasklists().list(maxResults=20).execute()
        due_min = time_min.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        due_max = time_max.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        tasks = []
        for task_list in task_lists_result.get("items", []):
            list_id = task_list["id"]
            try:
                result = service.tasks().list(
                    tasklist=list_id,
                    dueMin=due_min,
                    dueMax=due_max,
                    showCompleted=False,
                    showHidden=False
                ).execute()
            except Exception as e:
                print(f"[TASKS] 清單 {list_id} 抓取失敗：{e}", flush=True)
                continue

            for task in result.get("items", []):
                if task.get("status") == "completed":
                    continue
                due = task.get("due", "")
                if not due:
                    continue
                due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                date_str = due_dt.astimezone(TAIPEI_TZ).strftime("%Y-%m-%d")
                tasks.append({
                    "summary": task.get("title", "（未命名工作）"),
                    "calendarId": "__tasks__",
                    "start": {"date": date_str},
                    "end": {"date": date_str},
                    "location": "",
                    "is_task": True,
                })

        print(f"[TASKS] 抓到 {len(tasks)} 筆工作", flush=True)
        return tasks
    except Exception as e:
        print(f"[TASKS] 抓取失敗（可能需重新授權）：{e}", flush=True)
        return []


EXCLUDED_CALENDARS = {"台灣的節慶假日", "台灣節慶假日", "Holidays in Taiwan"}

# 日曆清單快取（每小時更新一次）
_calendar_cache: list = []
_calendar_cache_time: datetime | None = None
_CACHE_TTL = timedelta(hours=1)

def get_all_calendars(service) -> dict:
    """回傳 {cal_id: cal_name}，排除節慶假日與主要日曆"""
    result = service.calendarList().list().execute()
    calendars = {}
    for cal in result.get("items", []):
        name = cal.get("summary", cal["id"])
        print(f"[CAL] 發現日曆：{name!r}", flush=True)
        if name in EXCLUDED_CALENDARS:
            print(f"[CAL] 跳過（節慶）：{name}", flush=True)
            continue
        if "@" in name:
            name = "主要日曆"
        calendars[cal["id"]] = name
    print(f"[CAL] 使用日曆數：{len(calendars)} → {list(calendars.values())}", flush=True)
    return calendars


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
        print(f"[CAL] {cal_name} 抓到 {len(result.get('items', []))} 筆事件", flush=True)
    except Exception as e:
        print(f"[CAL] {cal_name} 抓取失敗：{e}", flush=True)
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


async def create_calendar_event(
    title: str,
    start_date: str,
    end_date: str,
    start_time: str = None,
    location: str = ""
) -> str:
    """建立 Google Calendar 行程，回傳建立結果訊息"""
    service = get_calendar_service()

    if start_time:
        # 有時間：timed event
        start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        start_dt = start_dt.replace(tzinfo=TAIPEI_TZ)
        # 結束時間預設 +1 小時（若多天則結束日當天同時間）
        end_dt = datetime.strptime(f"{end_date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = end_dt.replace(tzinfo=TAIPEI_TZ) + timedelta(hours=1)
        event_body = {
            "summary": title,
            "location": location,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Taipei"},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Taipei"},
        }
    else:
        # 全天 event（end date exclusive，需 +1 天）
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        event_body = {
            "summary": title,
            "location": location,
            "start": {"date": start_date},
            "end":   {"date": end_dt.strftime("%Y-%m-%d")},
        }

    event = service.events().insert(calendarId="primary", body=event_body).execute()
    return event.get("id", "")


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


async def get_events_next_month() -> list:
    service = get_calendar_service()
    calendars = get_all_calendars(service)
    now = datetime.now(TAIPEI_TZ)
    if now.month == 12:
        time_min = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        time_min = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if time_min.month == 12:
        time_max = time_min.replace(year=time_min.year + 1, month=1, day=1)
    else:
        time_max = time_min.replace(month=time_min.month + 1, day=1)

    seen = set()
    events = []
    for cal_id, cal_name in calendars.items():
        events += fetch_events(service, cal_id, cal_name, time_min, time_max, seen)
    events.sort(key=lambda e: (e["date"], e["time"]))
    return events, time_min.month


async def get_events_by_month(month: int) -> list:
    """取得指定月份的行程"""
    service = get_calendar_service()
    calendars = get_all_calendars(service)
    now = datetime.now(TAIPEI_TZ)
    year = now.year if month >= now.month else now.year + 1
    time_min = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if month == 12:
        time_max = time_min.replace(year=year + 1, month=1, day=1)
    else:
        time_max = time_min.replace(month=month + 1, day=1)

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
                    date_str = start["date"][5:].replace("-", "/")
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


# ── Flex Message 專用資料函式 ──────────────────────────────────────

def _get_calendars_info(service) -> list:
    """Return [{id, summary, colorId, backgroundColor}]，排除節慶假日；結果快取 1 小時"""
    global _calendar_cache, _calendar_cache_time
    now = datetime.now(TAIPEI_TZ)
    if _calendar_cache and _calendar_cache_time and (now - _calendar_cache_time) < _CACHE_TTL:
        return _calendar_cache

    result = service.calendarList().list().execute()
    calendars = []
    for cal in result.get("items", []):
        name = cal.get("summary", cal["id"])
        if name in EXCLUDED_CALENDARS:
            continue
        if "@" in name:
            name = "主要日曆"
        calendars.append({
            "id": cal["id"],
            "summary": name,
            "colorId": cal.get("colorId"),
            "backgroundColor": cal.get("backgroundColor"),
        })
    _calendar_cache = calendars
    _calendar_cache_time = now
    return calendars


def _fetch_raw_events(service, cal_id: str, time_min, time_max, seen: set, q: str = None) -> list:
    """回傳原始事件格式（含 calendarId），供 Flex builder 使用"""
    try:
        params = dict(
            calendarId=cal_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        )
        if q:
            params["q"] = q
        result = service.events().list(**params).execute()
    except Exception as e:
        print(f"[CAL] fetch_raw_events {cal_id} error: {e}", flush=True)
        return []

    events = []
    for event in result.get("items", []):
        key = event.get("id", "")
        if key in seen:
            continue
        seen.add(key)
        start = event.get("start", {})
        if "dateTime" not in start and "date" not in start:
            continue
        events.append({
            "summary": event.get("summary", "（未命名活動）"),
            "calendarId": cal_id,
            "start": start,
            "end": event.get("end", {}),
            "location": event.get("location", ""),
        })
    return events


def _fetch_raw_events_isolated(cal_id: str, time_min, time_max, q: str = None) -> list:
    """每個 thread 各自建立獨立 service，避免 SSL 共用問題"""
    service = get_calendar_service()
    return _fetch_raw_events(service, cal_id, time_min, time_max, set(), q)


async def _flex_fetch(time_min, time_max, q: str = None):
    import asyncio
    service = get_calendar_service()
    calendar_list = _get_calendars_info(service)

    # 平行抓行事曆事件（+ 若非搜尋模式則同時抓 Tasks）
    gather_targets = [
        asyncio.to_thread(_fetch_raw_events_isolated, cal["id"], time_min, time_max, q)
        for cal in calendar_list
    ]
    if not q:
        gather_targets.append(asyncio.to_thread(_fetch_tasks_for_range, time_min, time_max))

    results = await asyncio.gather(*gather_targets)

    seen = set()
    events = []
    cal_results = results[:-1] if not q else results
    task_results = results[-1] if not q else []

    for batch in cal_results:
        for ev in batch:
            key = f"{ev['summary']}_{ev['start'].get('dateTime') or ev['start'].get('date')}"
            if key not in seen:
                seen.add(key)
                events.append(ev)

    # 合併 Tasks，並加入虛擬「工作」日曆
    if task_results:
        tasks_cal = {
            "id": "__tasks__",
            "summary": "工作",
            "colorId": None,
            "backgroundColor": "#2e7d32",  # 深綠色
        }
        calendar_list = list(calendar_list) + [tasks_cal]
        for task in task_results:
            key = f"{task['summary']}_{task['start'].get('date')}"
            if key not in seen:
                seen.add(key)
                events.append(task)

    return calendar_list, events


async def get_flex_today():
    now = datetime.now(TAIPEI_TZ)
    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
    time_max = time_min + timedelta(days=1)
    return await _flex_fetch(time_min, time_max)


async def get_flex_tomorrow():
    now = datetime.now(TAIPEI_TZ)
    time_min = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    time_max = time_min + timedelta(days=1)
    return await _flex_fetch(time_min, time_max)


async def get_flex_range(days: int):
    now = datetime.now(TAIPEI_TZ)
    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
    time_max = time_min + timedelta(days=days)
    return await _flex_fetch(time_min, time_max)


async def get_flex_this_month():
    now = datetime.now(TAIPEI_TZ)
    time_min = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        time_max = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        time_max = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    cal_list, events = await _flex_fetch(time_min, time_max)
    return cal_list, events, now.month


async def get_flex_next_month():
    now = datetime.now(TAIPEI_TZ)
    if now.month == 12:
        time_min = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        time_min = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if time_min.month == 12:
        time_max = time_min.replace(year=time_min.year + 1, month=1, day=1)
    else:
        time_max = time_min.replace(month=time_min.month + 1, day=1)
    cal_list, events = await _flex_fetch(time_min, time_max)
    return cal_list, events, time_min.month


async def get_flex_by_month(month: int):
    now = datetime.now(TAIPEI_TZ)
    year = now.year if month >= now.month else now.year + 1
    time_min = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if month == 12:
        time_max = time_min.replace(year=year + 1, month=1, day=1)
    else:
        time_max = time_min.replace(month=month + 1, day=1)
    return await _flex_fetch(time_min, time_max)


async def search_flex_events(keyword: str):
    now = datetime.now(TAIPEI_TZ)
    time_min = now - timedelta(days=365)
    time_max = now + timedelta(days=365)
    return await _flex_fetch(time_min, time_max, q=keyword)
