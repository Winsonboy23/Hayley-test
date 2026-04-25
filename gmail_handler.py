import os
import json
import base64
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify"
]


def get_gmail_service():
    """建立 Gmail API 連線"""
    creds = None
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Google Token 無效，請重新授權")
    
    return build("gmail", "v1", credentials=creds)


async def get_recent_emails(max_results: int = 10) -> list:
    """取得最近 N 封信件（寄件人 + 主旨，不含內文）"""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        labelIds=["INBOX"]
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        from_raw = headers.get("From", "")

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "（無主旨）"),
            "from_name": extract_sender_name(from_raw),
            "from_email": extract_email_address(from_raw),
            "date": headers.get("Date", "")[:16],
        })

    return emails


async def get_emails_from_senders(email_list: list, max_results: int = 10) -> list:
    """取得指定寄件人的來信列表（用於信件 高/中/低 指令）"""
    if not email_list:
        return []

    service = get_gmail_service()
    from_query = " OR ".join([f"from:{e}" for e in email_list])

    results = service.users().messages().list(
        userId="me",
        q=f"({from_query}) in:inbox",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        from_raw = headers.get("From", "")

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "（無主旨）"),
            "from_name": extract_sender_name(from_raw),
            "from_email": extract_email_address(from_raw),
            "date": headers.get("Date", "")[:16],
        })

    return emails


async def get_email_by_id(message_id: str) -> dict:
    """取得單封信件內容"""
    service = get_gmail_service()
    detail = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()
    
    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
    body = extract_email_body(detail["payload"])
    sender_email = extract_email_address(headers.get("From", ""))
    
    return {
        "id": message_id,
        "subject": headers.get("Subject", "（無主旨）"),
        "from_raw": headers.get("From", ""),
        "from_email": sender_email,
        "from_name": extract_sender_name(headers.get("From", "")),
        "date": headers.get("Date", ""),
        "body": body[:3000]
    }


async def create_draft(
    to_email: str,
    subject: str,
    body: str,
    reply_to_id: str = None
) -> str:
    """建立 Gmail 草稿"""
    service = get_gmail_service()
    
    message = MIMEMultipart()
    message["to"] = to_email
    message["subject"] = subject
    
    msg_body = MIMEText(body, "plain", "utf-8")
    message.attach(msg_body)
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {"message": {"raw": raw}}
    
    if reply_to_id:
        draft_body["message"]["threadId"] = reply_to_id
    
    draft = service.users().drafts().create(
        userId="me",
        body=draft_body
    ).execute()
    
    return draft["id"]


async def count_today_emails() -> int:
    """計算今天收到幾封信"""
    service = get_gmail_service()
    from datetime import date
    today = date.today().strftime("%Y/%m/%d")
    
    results = service.users().messages().list(
        userId="me",
        q=f"after:{today} in:inbox"
    ).execute()
    
    return results.get("resultSizeEstimate", 0)


async def count_unread_emails() -> int:
    """計算收件匣未讀信件數"""
    service = get_gmail_service()
    label = service.users().labels().get(userId="me", id="INBOX").execute()
    return label.get("messagesUnread", 0)


async def count_drafts() -> int:
    """計算草稿數量"""
    service = get_gmail_service()
    results = service.users().drafts().list(userId="me").execute()
    drafts = results.get("drafts", [])
    return len(drafts)


async def get_unread_emails(max_results: int = 10) -> list:
    """取得未讀信件列表（寄件人 + 主旨）"""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me",
        q="is:unread in:inbox",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        from_raw = headers.get("From", "")

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "（無主旨）"),
            "from_name": extract_sender_name(from_raw),
            "from_email": extract_email_address(from_raw),
            "date": headers.get("Date", "")[:16],
        })

    return emails


async def get_drafts_list(max_results: int = 10) -> list:
    """取得草稿列表（含主旨、收件人）"""
    service = get_gmail_service()
    results = service.users().drafts().list(userId="me").execute()
    drafts = results.get("drafts", [])[:max_results]

    draft_list = []
    for d in drafts:
        detail = service.users().drafts().get(
            userId="me",
            id=d["id"],
            format="full"
        ).execute()
        payload = detail.get("message", {}).get("payload", {})
        # header name 可能是大寫或小寫（MIMEMultipart 產生的草稿為小寫），統一轉小寫比對
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        draft_list.append({
            "id": d["id"],
            "subject": headers.get("subject", "（無主旨）"),
            "to": headers.get("to", ""),
        })
    return draft_list


async def search_emails(keyword: str, max_results: int = 5) -> list:
    """用關鍵字搜尋信件，回傳摘要列表（不含內文，不消耗 AI token）"""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me",
        q=keyword,
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        from_raw = headers.get("From", "")

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "（無主旨）"),
            "from_name": extract_sender_name(from_raw),
            "from_email": extract_email_address(from_raw),
            "date": headers.get("Date", "")[:16],
        })

    return emails


async def setup_gmail_watch() -> dict:
    """設定 Gmail Push Notification（監聽新信）"""
    service = get_gmail_service()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
    topic = f"projects/{project_id}/topics/gmail-notifications"
    
    result = service.users().watch(
        userId="me",
        body={
            "labelIds": ["INBOX"],
            "topicName": topic
        }
    ).execute()
    return result


def extract_email_body(payload: dict) -> str:
    """從 Gmail payload 提取信件內文"""
    body = ""
    
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                if part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break
            elif part.get("mimeType") == "text/html" and not body:
                if part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    
    return body.strip()


def extract_email_address(from_header: str) -> str:
    """從 From header 提取 email 地址"""
    if "<" in from_header and ">" in from_header:
        return from_header.split("<")[1].split(">")[0].strip()
    return from_header.strip()


def extract_sender_name(from_header: str) -> str:
    """從 From header 提取寄件人姓名"""
    if "<" in from_header:
        return from_header.split("<")[0].strip().strip('"')
    return from_header.strip()
