import os
import time
import httpx

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
CONTACTS_DB_ID = os.getenv("NOTION_CONTACTS_DB_ID")
TEMPLATES_DB_ID = os.getenv("NOTION_TEMPLATES_DB_ID")
BLACKLIST_DB_ID = os.getenv("NOTION_BLACKLIST_DB_ID", "f37b1c4a8f524c5fbd8254ad85285f0d")

# 黑名單快取（10 分鐘更新一次，避免頻繁打 Notion API）
_blacklist_cache: set = set()
_blacklist_cache_time: float = 0
_BLACKLIST_TTL = 600  # 秒

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


async def get_email_blacklist() -> set:
    """從 Notion 黑名單 DB 取得所有封鎖的 email（10 分鐘快取）"""
    global _blacklist_cache, _blacklist_cache_time
    if time.time() - _blacklist_cache_time < _BLACKLIST_TTL:
        return _blacklist_cache

    url = f"https://api.notion.com/v1/databases/{BLACKLIST_DB_ID}/query"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=HEADERS, json={})
            data = res.json()
        emails = set()
        for result in data.get("results", []):
            email_val = result["properties"].get("Email", {}).get("email", "")
            if email_val:
                emails.add(email_val.lower().strip())
        _blacklist_cache = emails
        _blacklist_cache_time = time.time()
        print(f"[BLACKLIST] 已更新，共 {len(emails)} 筆", flush=True)
    except Exception as e:
        print(f"[BLACKLIST] 載入失敗：{e}", flush=True)
    return _blacklist_cache


async def find_contact_by_email(email: str) -> dict | None:
    """從 Notion 聯絡人 DB 用 email 查詢聯絡人"""
    url = f"https://api.notion.com/v1/databases/{CONTACTS_DB_ID}/query"
    payload = {
        "filter": {
            "property": "Email",
            "email": {"equals": email}
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=HEADERS, json=payload)
        data = res.json()
    
    results = data.get("results", [])
    if not results:
        return None
    
    props = results[0]["properties"]
    return {
        "name": props.get("姓名", {}).get("title", [{}])[0].get("plain_text", "未知"),
        "role": props.get("角色", {}).get("select", {}).get("name", "未知"),
        "unit": props.get("店／單位", {}).get("rich_text", [{}])[0].get("plain_text", ""),
        "email": email
    }


async def find_contacts_by_role(role: str) -> list:
    """從 Notion 聯絡人 DB 依角色查詢所有聯絡人"""
    url = f"https://api.notion.com/v1/databases/{CONTACTS_DB_ID}/query"
    payload = {
        "filter": {
            "property": "角色",
            "select": {"equals": role}
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=HEADERS, json=payload)
        data = res.json()
    
    contacts = []
    for result in data.get("results", []):
        props = result["properties"]
        email_val = props.get("Email", {}).get("email", "")
        if email_val:
            contacts.append({
                "name": props.get("姓名", {}).get("title", [{}])[0].get("plain_text", "未知"),
                "role": role,
                "unit": props.get("店／單位", {}).get("rich_text", [{}])[0].get("plain_text", ""),
                "email": email_val
            })
    return contacts


async def get_template_by_role(role: str) -> dict | None:
    """從 Notion 模板 DB 依角色查詢對應模板"""
    url = f"https://api.notion.com/v1/databases/{TEMPLATES_DB_ID}/query"
    payload = {
        "filter": {
            "property": "適用對象角色",
            "select": {"equals": role}
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=HEADERS, json=payload)
        data = res.json()
    
    results = data.get("results", [])
    if not results:
        return None
    
    props = results[0]["properties"]
    page_id = results[0]["id"]
    
    # 取得模板內文（Page Content）
    content_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    async with httpx.AsyncClient() as client:
        content_res = await client.get(content_url, headers=HEADERS)
        content_data = content_res.json()
    
    content_text = ""
    for block in content_data.get("results", []):
        block_type = block.get("type", "")
        if block_type == "paragraph":
            texts = block["paragraph"].get("rich_text", [])
            content_text += "".join([t.get("plain_text", "") for t in texts]) + "\n"
    
    return {
        "name": props.get("模板名稱", {}).get("title", [{}])[0].get("plain_text", ""),
        "subject": props.get("主旨範本", {}).get("rich_text", [{}])[0].get("plain_text", ""),
        "content": content_text.strip()
    }


async def get_contact_info_by_name(name: str) -> dict | None:
    """從 Notion 聯絡人 DB 用姓名查詢（給 LINE 問答用）"""
    url = f"https://api.notion.com/v1/databases/{CONTACTS_DB_ID}/query"
    payload = {
        "filter": {
            "property": "姓名",
            "title": {"contains": name}
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=HEADERS, json=payload)
        data = res.json()
    
    results = data.get("results", [])
    if not results:
        return None
    
    props = results[0]["properties"]
    return {
        "name": props.get("姓名", {}).get("title", [{}])[0].get("plain_text", ""),
        "role": props.get("角色", {}).get("select", {}).get("name", ""),
        "unit": props.get("店／單位", {}).get("rich_text", [{}])[0].get("plain_text", ""),
        "email": props.get("Email", {}).get("email", "")
    }
