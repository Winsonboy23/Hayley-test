import os
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


async def push_message(text: str):
    """主動推播訊息給海莉"""
    async with AsyncApiClient(configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)
        await line_bot_api.push_message(
            PushMessageRequest(
                to=LINE_USER_ID,
                messages=[TextMessage(text=text)]
            )
        )


async def reply_message(reply_token: str, text: str):
    """回覆海莉的訊息"""
    async with AsyncApiClient(configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )


def format_new_email_notification(
    sender_name: str,
    sender_role: str,
    sender_unit: str,
    summary: str,
    is_unknown: bool = False
) -> str:
    """格式化新信件通知訊息"""
    
    if sender_role and sender_unit:
        sender_info = f"{sender_name}（{sender_unit} {sender_role}）"
    elif sender_name:
        sender_info = sender_name
    else:
        sender_info = "未知寄件人"
    
    warning = "\n⚠️ 此寄件人不在聯絡人名單中" if is_unknown else ""
    
    return f"""📩 新信件

寄件人：{sender_info}{warning}

摘要：{summary}

草稿已備妥，請至 Gmail 確認 ✉️"""


def format_event_reminder(event_name: str, event_time: str, location: str = "") -> str:
    """格式化活動提醒訊息"""
    location_text = f"\n地點：{location}" if location else ""
    
    return f"""⏰ 活動提醒

再 1 小時後
{event_name} {event_time}{location_text}

請準備相關資料！"""


def format_daily_summary(summary_text: str) -> str:
    """格式化每日行程總結"""
    return summary_text
