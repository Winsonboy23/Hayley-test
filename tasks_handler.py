import os
import json
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly"
]

TAIPEI_TZ = timezone(timedelta(hours=8))


def get_tasks_service():
    creds = None
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Google Token 無效，請重新授權")
    return build("tasks", "v1", credentials=creds)


async def get_all_tasks() -> list:
    """取得所有待辦清單中的未完成任務"""
    service = get_tasks_service()
    tasklists = service.tasklists().list().execute().get("items", [])

    tasks = []
    for tl in tasklists:
        print(f"[TASKS] 清單：{tl.get('title')} id={tl['id']}", flush=True)
        result = service.tasks().list(
            tasklist=tl["id"],
            showCompleted=False,
            showHidden=True,
            maxResults=100
        ).execute()
        print(f"[TASKS] 項目數：{len(result.get('items', []))}", flush=True)
        for item in result.get("items", []):
            print(f"[TASKS]   - {item.get('title')} status={item.get('status')}", flush=True)
        for task in result.get("items", []):
            title = task.get("title", "").strip()
            if not title:
                continue
            due = task.get("due", "")
            due_str = ""
            if due:
                dt = datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(TAIPEI_TZ)
                due_str = dt.strftime("%m/%d")
            tasks.append({
                "title": title,
                "due": due_str,
                "list": tl.get("title", "待辦"),
                "notes": task.get("notes", "")
            })
    return tasks
