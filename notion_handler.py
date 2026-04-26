import os
import httpx

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
CONTACTS_DB_ID = os.getenv("NOTION_CONTACTS_DB_ID")
TEMPLATES_DB_ID = os.getenv("NOTION_TEMPLATES_DB_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


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
        "email": email,
        "importance": props.get("重要度", {}).get("select", {}).get("name", "低"),
    }


async def get_contact_emails_by_importance(importance: str) -> list[str]:
    """取得特定重要度的所有聯絡人 email 清單"""
    url = f"https://api.notion.com/v1/databases/{CONTACTS_DB_ID}/query"
    payload = {
        "filter": {
            "property": "重要度",
            "select": {"equals": importance}
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=HEADERS, json=payload)
        data = res.json()

    emails = []
    for result in data.get("results", []):
        props = result["properties"]
        email_val = props.get("Email", {}).get("email", "")
        if email_val:
            emails.append(email_val)
    return emails


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
    if not TEMPLATES_DB_ID:
        return None
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
