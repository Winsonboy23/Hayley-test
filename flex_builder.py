CALENDAR_COLORS = {
    "1":  {"main": "#7986cb", "light": "#e8eaf6", "dark": "#3949ab"},
    "2":  {"main": "#33b679", "light": "#e8f5e9", "dark": "#1b5e20"},
    "3":  {"main": "#8e24aa", "light": "#f3e5f5", "dark": "#6a1b9a"},
    "4":  {"main": "#e67c73", "light": "#fce4ec", "dark": "#c62828"},
    "5":  {"main": "#f6bf26", "light": "#fffde7", "dark": "#f57f17"},
    "6":  {"main": "#f4511e", "light": "#fbe9e7", "dark": "#bf360c"},
    "7":  {"main": "#039be5", "light": "#e1f5fe", "dark": "#01579b"},
    "8":  {"main": "#616161", "light": "#f5f5f5", "dark": "#212121"},
    "9":  {"main": "#3f51b5", "light": "#e8eaf6", "dark": "#1a237e"},
    "10": {"main": "#0b8043", "light": "#e8f5e9", "dark": "#1b5e20"},
    "11": {"main": "#d50000", "light": "#ffebee", "dark": "#b71c1c"},
    "default": {"main": "#1a73e8", "light": "#e8f0fe", "dark": "#1558b0"},
}

SEPARATOR = {"type": "separator", "color": "#f0f0f0", "margin": "none"}


def get_calendar_color(calendar: dict) -> dict:
    bg = calendar.get("backgroundColor")
    if bg:
        return {"main": bg, "light": bg + "22", "dark": bg}
    color_id = str(calendar.get("colorId") or "default")
    return CALENDAR_COLORS.get(color_id, CALENDAR_COLORS["default"])


def _parse_date(start: dict) -> str:
    """Return MM/DD from start dict."""
    date_str = start.get("date") or start.get("dateTime", "")
    if "T" in date_str:
        date_str = date_str[:10]
    parts = date_str.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}"
    return date_str


def _parse_time(date_time_str: str) -> str:
    return date_time_str[11:16]


def _is_all_day(event: dict) -> bool:
    return "date" in event.get("start", {})


def _dot(color_hex: str, size: str = "8px", radius: str = "4px") -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "width": size,
        "height": size,
        "cornerRadius": radius,
        "backgroundColor": color_hex,
        "contents": []
    }


def _build_sub_label(text: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#fafafa",
        "paddingTop": "5px",
        "paddingBottom": "5px",
        "paddingStart": "14px",
        "contents": [{"type": "text", "text": text, "size": "xxs", "color": "#aaaaaa"}]
    }


def _build_calendar_header(name: str, color: dict) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#f5f5f5",
        "paddingTop": "7px",
        "paddingBottom": "7px",
        "paddingStart": "14px",
        "paddingEnd": "14px",
        "contents": [{
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {**_dot(color["main"], "10px", "5px"), "offsetTop": "2px"},
                {"type": "text", "text": name, "size": "xxs", "color": "#555555", "weight": "bold"}
            ]
        }]
    }


def _build_event_row(event: dict, color: dict) -> dict:
    """Row with date + optional time badge + title (for carousel)."""
    date_label = _parse_date(event["start"])
    title = event.get("summary", "（無標題）")
    all_day = _is_all_day(event)

    contents = [
        {
            "type": "box",
            "layout": "vertical",
            "width": "8px",
            "contents": [
                {"type": "filler"},
                _dot(color["main"]),
                {"type": "filler"}
            ]
        },
        {
            "type": "text",
            "text": date_label,
            "size": "xs",
            "color": "#555555",
            "weight": "bold",
            "flex": 0,
            "offsetTop": "1px"
        }
    ]

    if not all_day:
        contents.append({
            "type": "box",
            "layout": "vertical",
            "backgroundColor": color["light"],
            "cornerRadius": "4px",
            "paddingTop": "1px",
            "paddingBottom": "1px",
            "paddingStart": "6px",
            "paddingEnd": "6px",
            "flex": 0,
            "contents": [{
                "type": "text",
                "text": _parse_time(event["start"]["dateTime"]),
                "size": "xxs",
                "color": color["dark"]
            }]
        })

    contents.append({
        "type": "text",
        "text": title,
        "size": "sm",
        "color": "#222222",
        "flex": 1,
        "wrap": True
    })

    return {
        "type": "box",
        "layout": "horizontal",
        "paddingTop": "9px",
        "paddingBottom": "9px",
        "paddingStart": "14px",
        "paddingEnd": "14px",
        "spacing": "sm",
        "contents": contents
    }


def _build_single_event_row(event: dict, color: dict) -> dict:
    """Row for single-day view: colored dot + time/全天 badge + title."""
    title = event.get("summary", "（無標題）")
    all_day = _is_all_day(event)
    time_text = "全天" if all_day else _parse_time(event["start"]["dateTime"])

    return {
        "type": "box",
        "layout": "horizontal",
        "paddingTop": "10px",
        "paddingBottom": "10px",
        "paddingStart": "14px",
        "paddingEnd": "14px",
        "spacing": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "width": "8px",
                "contents": [
                    {"type": "filler"},
                    _dot(color["main"]),
                    {"type": "filler"}
                ]
            },
            {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": color["light"],
                "cornerRadius": "4px",
                "paddingTop": "1px",
                "paddingBottom": "1px",
                "paddingStart": "6px",
                "paddingEnd": "6px",
                "flex": 0,
                "contents": [{
                    "type": "text",
                    "text": time_text,
                    "size": "xxs",
                    "color": color["dark"]
                }]
            },
            {
                "type": "text",
                "text": title,
                "size": "sm",
                "color": "#222222",
                "flex": 1,
                "wrap": True
            }
        ]
    }


def _build_header(title_text: str, subtitle: str, page_label: str = "") -> dict:
    header_contents = [
        {
            "type": "box",
            "layout": "vertical",
            "flex": 1,
            "contents": [
                {"type": "text", "text": title_text, "color": "#ffffff", "size": "md", "weight": "bold"},
                {"type": "text", "text": subtitle, "color": "#c7dcfc", "size": "xxs", "margin": "xs"}
            ]
        }
    ]
    if page_label:
        header_contents.append({
            "type": "text",
            "text": page_label,
            "color": "#c7dcfc",
            "size": "xxs",
            "align": "end",
            "gravity": "bottom"
        })
    return {
        "type": "box",
        "layout": "horizontal",
        "backgroundColor": "#1a73e8",
        "paddingAll": "14px",
        "contents": header_contents
    }


def _build_bubble(*, calendar_name, color, all_day_events, timed_events,
                  page_label, month_label, total_count, calendar_count) -> dict:
    body = []
    body.append(_build_calendar_header(calendar_name, color))

    if all_day_events:
        body.append(_build_sub_label("全天"))
        for i, ev in enumerate(all_day_events):
            body.append(_build_event_row(ev, color))
            if i < len(all_day_events) - 1 or timed_events:
                body.append(SEPARATOR)

    if timed_events:
        body.append(_build_sub_label("有時間"))
        for i, ev in enumerate(timed_events):
            body.append(_build_event_row(ev, color))
            if i < len(timed_events) - 1:
                body.append(SEPARATOR)

    footer_text = "滑動查看其他日曆 →" if calendar_count > 1 else f"{month_label} 全部行程"

    return {
        "type": "bubble",
        "size": "kilo",
        "header": _build_header(
            f"📅 {month_label}行程",
            f"共 {total_count} 件・{calendar_count} 個日曆",
            page_label
        ),
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "0px",
            "spacing": "none",
            "contents": body
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#f5f5f5",
            "paddingAll": "10px",
            "contents": [
                {"type": "text", "text": footer_text, "size": "xxs", "color": "#aaaaaa", "align": "center"}
            ]
        }
    }


def build_flex_carousel(calendar_list: list, event_list: list, month_label: str) -> dict:
    """Carousel: one bubble per calendar."""
    calendar_map = {cal["id"]: cal for cal in calendar_list}

    groups: dict = {}
    for event in event_list:
        cid = event.get("calendarId", "primary")
        groups.setdefault(cid, []).append(event)

    def sort_key(e):
        s = e.get("start", {})
        return s.get("date") or s.get("dateTime", "")

    total_count = len(event_list)
    calendar_count = len(groups)
    bubbles = []

    for page_index, (cid, events) in enumerate(groups.items()):
        cal = calendar_map.get(cid, {"id": cid, "summary": cid})
        color = get_calendar_color(cal)
        sorted_events = sorted(events, key=sort_key)
        all_day = [e for e in sorted_events if _is_all_day(e)]
        timed = [e for e in sorted_events if not _is_all_day(e)]

        bubbles.append(_build_bubble(
            calendar_name=cal.get("summary", cid),
            color=color,
            all_day_events=all_day,
            timed_events=timed,
            page_label=f"{page_index + 1} / {calendar_count}",
            month_label=month_label,
            total_count=total_count,
            calendar_count=calendar_count
        ))

    return {
        "type": "flex",
        "altText": f"📅 {month_label}行程（共 {total_count} 件）",
        "contents": {"type": "carousel", "contents": bubbles}
    }


def build_flex_single(calendar_list: list, event_list: list, label: str) -> dict:
    """Single bubble for today/tomorrow — all calendars merged, sorted by time."""
    calendar_map = {cal["id"]: cal for cal in calendar_list}

    def sort_key(e):
        s = e.get("start", {})
        return s.get("date") or s.get("dateTime", "")

    sorted_events = sorted(event_list, key=sort_key)
    total = len(sorted_events)
    body = []

    for i, ev in enumerate(sorted_events):
        cid = ev.get("calendarId", "primary")
        cal = calendar_map.get(cid, {"id": cid})
        color = get_calendar_color(cal)
        body.append(_build_single_event_row(ev, color))
        if i < total - 1:
            body.append(SEPARATOR)

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": _build_header(f"📅 {label}行程", f"共 {total} 件"),
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "0px",
            "spacing": "none",
            "contents": body
        }
    }

    return {
        "type": "flex",
        "altText": f"📅 {label}行程（共 {total} 件）",
        "contents": bubble
    }


def build_flex_evening_push(calendar_list: list, event_list: list, unread_count: int) -> dict:
    """晚上推播：明日行程（單張）+ 未讀信件數"""
    from datetime import datetime, timezone, timedelta
    TAIPEI_TZ = timezone(timedelta(hours=8))
    now = datetime.now(TAIPEI_TZ)
    tomorrow = now + timedelta(days=1)
    date_str = tomorrow.strftime("%m/%d")
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekdays[tomorrow.weekday()]

    calendar_map = {cal["id"]: cal for cal in calendar_list}

    def sort_key(e):
        s = e.get("start", {})
        return s.get("date") or s.get("dateTime", "")

    sorted_events = sorted(event_list, key=sort_key)
    total = len(sorted_events)

    stats_row = {
        "type": "box",
        "layout": "horizontal",
        "margin": "md",
        "spacing": "sm",
        "contents": [
            {
                "type": "box", "layout": "vertical", "flex": 1,
                "backgroundColor": "#e8f0fe", "cornerRadius": "8px", "paddingAll": "10px",
                "contents": [
                    {"type": "text", "text": str(total), "size": "xl", "weight": "bold",
                     "color": "#1a73e8", "align": "center"},
                    {"type": "text", "text": "件行程", "size": "xxs", "color": "#555555", "align": "center"}
                ]
            },
            {
                "type": "box", "layout": "vertical", "flex": 1,
                "backgroundColor": "#fce4ec", "cornerRadius": "8px", "paddingAll": "10px",
                "contents": [
                    {"type": "text", "text": str(unread_count), "size": "xl", "weight": "bold",
                     "color": "#d50000", "align": "center"},
                    {"type": "text", "text": "封未讀", "size": "xxs", "color": "#555555", "align": "center"}
                ]
            }
        ]
    }

    body_contents = [stats_row]

    if sorted_events:
        body_contents.append({"type": "separator", "margin": "md"})
        display = sorted_events[:5]
        for i, ev in enumerate(display):
            cid = ev.get("calendarId", "primary")
            cal = calendar_map.get(cid, {"id": cid})
            color = get_calendar_color(cal)
            body_contents.append(_build_single_event_row(ev, color))
            if i < len(display) - 1:
                body_contents.append(SEPARATOR)
        if len(sorted_events) > 5:
            body_contents.append({
                "type": "text",
                "text": f"還有 {len(sorted_events) - 5} 件...",
                "size": "xxs", "color": "#aaaaaa", "margin": "sm", "align": "center"
            })

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1a73e8",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "📅 明日行程", "color": "#ffffff", "size": "md", "weight": "bold"},
                {"type": "text", "text": f"{date_str} 星期{weekday}", "color": "#c7dcfc", "size": "xxs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "14px",
            "contents": body_contents
        }
    }

    return {
        "type": "flex",
        "altText": f"📅 明日行程 {total} 件・未讀 {unread_count} 封",
        "contents": bubble
    }


def build_flex_morning_summary(calendar_list: list, event_list: list, unread_count: int) -> dict:
    """早晨推播：今日行程件數 + 未讀信件數 + 事件列表"""
    from datetime import datetime, timezone, timedelta
    TAIPEI_TZ = timezone(timedelta(hours=8))
    now = datetime.now(TAIPEI_TZ)
    date_str = now.strftime("%m/%d")
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekdays[now.weekday()]

    calendar_map = {cal["id"]: cal for cal in calendar_list}

    def sort_key(e):
        s = e.get("start", {})
        return s.get("date") or s.get("dateTime", "")

    sorted_events = sorted(event_list, key=sort_key)
    total = len(sorted_events)

    stats_row = {
        "type": "box",
        "layout": "horizontal",
        "margin": "md",
        "spacing": "sm",
        "contents": [
            {
                "type": "box", "layout": "vertical", "flex": 1,
                "backgroundColor": "#e8f0fe", "cornerRadius": "8px", "paddingAll": "10px",
                "contents": [
                    {"type": "text", "text": str(total), "size": "xl", "weight": "bold",
                     "color": "#1a73e8", "align": "center"},
                    {"type": "text", "text": "件行程", "size": "xxs", "color": "#555555", "align": "center"}
                ]
            },
            {
                "type": "box", "layout": "vertical", "flex": 1,
                "backgroundColor": "#fce4ec", "cornerRadius": "8px", "paddingAll": "10px",
                "contents": [
                    {"type": "text", "text": str(unread_count), "size": "xl", "weight": "bold",
                     "color": "#d50000", "align": "center"},
                    {"type": "text", "text": "封未讀", "size": "xxs", "color": "#555555", "align": "center"}
                ]
            }
        ]
    }

    body_contents = [stats_row]

    if sorted_events:
        body_contents.append({"type": "separator", "margin": "md"})
        display = sorted_events[:5]
        for i, ev in enumerate(display):
            cid = ev.get("calendarId", "primary")
            cal = calendar_map.get(cid, {"id": cid})
            color = get_calendar_color(cal)
            body_contents.append(_build_single_event_row(ev, color))
            if i < len(display) - 1:
                body_contents.append(SEPARATOR)
        if len(sorted_events) > 5:
            body_contents.append({
                "type": "text",
                "text": f"還有 {len(sorted_events) - 5} 件...",
                "size": "xxs", "color": "#aaaaaa", "margin": "sm", "align": "center"
            })

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1a73e8",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "☀️ 早安，今日摘要", "color": "#ffffff", "size": "md", "weight": "bold"},
                {"type": "text", "text": f"{date_str} 星期{weekday}", "color": "#c7dcfc", "size": "xxs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "14px",
            "contents": body_contents
        }
    }

    return {
        "type": "flex",
        "altText": f"☀️ 早安！今天 {total} 件行程・未讀 {unread_count} 封",
        "contents": bubble
    }


# ── Email 通知 Flex 卡片 ───────────────────────────────────────────

_IMPORTANCE_MAP = {
    "high":   {"emoji": "🔴", "label": "高", "color": "#c62828", "bg": "#ffebee"},
    "medium": {"emoji": "🟡", "label": "中", "color": "#e65100", "bg": "#fff3e0"},
    "low":    {"emoji": "⚪", "label": "低", "color": "#757575", "bg": "#f5f5f5"},
}


def build_flex_email_notification(
    sender_name: str,
    subject: str,
    is_unknown: bool,
    message_id: str = "",
    sender_role: str = "",
    sender_unit: str = "",
    draft_ready: bool = False,
    importance: str = "",
    reason: str = "",
    should_reply: bool = False,
) -> dict:
    """Email 通知卡片：已知聯絡人顯示草稿提示，陌生人顯示重要度 + 起草按鈕"""

    # 寄件人顯示名稱
    if sender_role and sender_unit:
        sender_display = f"{sender_name}（{sender_unit} {sender_role}）"
    elif sender_role:
        sender_display = f"{sender_name}（{sender_role}）"
    else:
        sender_display = sender_name

    imp = _IMPORTANCE_MAP.get(importance, {})

    body = []

    # 寄件人列
    sender_contents = [
        {"type": "text", "text": "寄件人", "size": "xs", "color": "#888888", "flex": 0},
        {"type": "text", "text": sender_display, "size": "sm", "color": "#222222",
         "flex": 1, "wrap": True},
    ]
    if is_unknown:
        sender_contents.append({"type": "text", "text": "⚠️", "size": "sm", "flex": 0})
    body.append({
        "type": "box", "layout": "horizontal", "spacing": "sm",
        "paddingTop": "12px", "paddingStart": "14px", "paddingEnd": "14px",
        "contents": sender_contents
    })

    # 主旨列
    body.append({
        "type": "box", "layout": "horizontal", "spacing": "sm",
        "paddingTop": "6px", "paddingBottom": "4px",
        "paddingStart": "14px", "paddingEnd": "14px",
        "contents": [
            {"type": "text", "text": "主旨", "size": "xs", "color": "#888888", "flex": 0},
            {"type": "text", "text": subject, "size": "sm", "color": "#333333",
             "flex": 1, "wrap": True},
        ]
    })

    # 重要度列（陌生人）
    if is_unknown and importance and imp:
        body.append({"type": "separator", "margin": "sm", "color": "#f0f0f0"})
        body.append({
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "paddingTop": "10px", "paddingBottom": "4px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {
                    "type": "box", "layout": "vertical", "flex": 0,
                    "backgroundColor": imp["bg"], "cornerRadius": "4px",
                    "paddingTop": "2px", "paddingBottom": "2px",
                    "paddingStart": "8px", "paddingEnd": "8px",
                    "contents": [{"type": "text", "text": f"{imp['emoji']} 重要度 {imp['label']}",
                                  "size": "xxs", "color": imp["color"], "weight": "bold"}]
                },
                {"type": "text", "text": reason, "size": "xs",
                 "color": "#666666", "flex": 1, "wrap": True}
            ]
        })

    body.append({"type": "box", "layout": "vertical", "height": "8px", "contents": []})

    # Footer
    if draft_ready:
        footer = {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#e8f5e9", "paddingAll": "12px",
            "contents": [{"type": "text", "text": "✉️ 草稿已備妥，請至 Gmail 確認",
                          "size": "xs", "color": "#2e7d32", "align": "center"}]
        }
    elif is_unknown and should_reply:
        footer = {
            "type": "box", "layout": "vertical", "paddingAll": "10px",
            "contents": [{
                "type": "button",
                "style": "primary",
                "color": "#1a73e8",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": "✍️ 幫我起草回信",
                    "data": f"action=draft&id={message_id}",
                    "displayText": "幫我起草這封信的回信"
                }
            }]
        }
    else:
        footer = None

    # Header 顏色
    if is_unknown:
        header_color = {"high": "#c62828", "medium": "#e65100", "low": "#546e7a"}.get(importance, "#546e7a")
        subtitle = "陌生寄件人"
    else:
        header_color = "#1a73e8"
        subtitle = "聯絡人來信"

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": header_color, "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "📩 新信件", "color": "#ffffff",
                 "size": "md", "weight": "bold"},
                {"type": "text", "text": subtitle, "color": "#ffffff99",
                 "size": "xxs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical",
            "paddingAll": "0px", "spacing": "none",
            "contents": body
        }
    }
    if footer:
        bubble["footer"] = footer

    return {
        "type": "flex",
        "altText": f"📩 新信件：{sender_name}",
        "contents": bubble
    }


# ── 無行程空狀態 ──────────────────────────────────────────────────────
def build_flex_no_events(label: str, extra: str = "") -> dict:
    """無行程 / 無搜尋結果的空狀態卡片"""
    body_text = extra if extra else f"{label} 沒有排定的行程"
    return {
        "type": "flex",
        "altText": body_text,
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1a73e8",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": f"📅 {label}行程",
                     "color": "#ffffff", "size": "md", "weight": "bold"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "24px",
                "contents": [
                    {"type": "text", "text": body_text,
                     "size": "sm", "color": "#888888", "align": "center"}
                ]
            }
        }
    }


# ── 信件查詢 ──────────────────────────────────────────────────────────
def build_flex_email_summary(unread_count: int, draft_count: int) -> dict:
    """信件狀況卡片：未讀信件 + 待發草稿"""
    return {
        "type": "flex",
        "altText": f"📩 未讀 {unread_count} 封・草稿 {draft_count} 封",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1a73e8",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "📩 信件狀況",
                     "color": "#ffffff", "size": "md", "weight": "bold"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "horizontal",
                "paddingAll": "16px",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box", "layout": "vertical", "flex": 1,
                        "backgroundColor": "#fce4ec", "cornerRadius": "8px", "paddingAll": "14px",
                        "contents": [
                            {"type": "text", "text": str(unread_count), "size": "xxl",
                             "weight": "bold", "color": "#d50000", "align": "center"},
                            {"type": "text", "text": "未讀信件", "size": "xxs",
                             "color": "#555555", "align": "center", "margin": "xs"}
                        ]
                    },
                    {
                        "type": "box", "layout": "vertical", "flex": 1,
                        "backgroundColor": "#fff8e1", "cornerRadius": "8px", "paddingAll": "14px",
                        "contents": [
                            {"type": "text", "text": str(draft_count), "size": "xxl",
                             "weight": "bold", "color": "#f57f17", "align": "center"},
                            {"type": "text", "text": "待發草稿", "size": "xxs",
                             "color": "#555555", "align": "center", "margin": "xs"}
                        ]
                    }
                ]
            }
        }
    }


# ── 聯絡人名片 ────────────────────────────────────────────────────────
def build_flex_contact(name: str, role: str, unit: str, email: str) -> dict:
    """聯絡人名片卡片"""
    if unit and role:
        subtitle = f"{unit}・{role}"
    elif role:
        subtitle = role
    elif unit:
        subtitle = unit
    else:
        subtitle = ""

    body_contents = [
        {"type": "text", "text": name, "size": "lg", "weight": "bold", "color": "#222222"}
    ]
    if subtitle:
        body_contents.append(
            {"type": "text", "text": subtitle, "size": "sm", "color": "#666666", "margin": "xs"}
        )
    body_contents.append({"type": "separator", "margin": "md", "color": "#f0f0f0"})
    body_contents.append({
        "type": "box", "layout": "horizontal",
        "margin": "md", "spacing": "sm",
        "contents": [
            {"type": "text", "text": "📧", "size": "sm", "flex": 0},
            {"type": "text", "text": email, "size": "sm", "color": "#1a73e8",
             "flex": 1, "wrap": True}
        ]
    })

    return {
        "type": "flex",
        "altText": f"👤 {name}",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#2e7d32",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "👤 聯絡人查詢",
                     "color": "#ffffff", "size": "md", "weight": "bold"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "16px", "spacing": "none",
                "contents": body_contents
            }
        }
    }


# ── 待辦事項 ──────────────────────────────────────────────────────────
def build_flex_tasks(tasks: list) -> dict:
    """待辦事項清單卡片"""
    body_contents = []
    for i, task in enumerate(tasks):
        meta_parts = []
        if task.get("due"):
            meta_parts.append(f"📅 {task['due']}")
        if task.get("list"):
            meta_parts.append(f"📂 {task['list']}")

        item_contents = [
            {"type": "text", "text": task["title"], "size": "sm",
             "color": "#222222", "wrap": True}
        ]
        if meta_parts:
            item_contents.append({
                "type": "text", "text": "  ".join(meta_parts),
                "size": "xxs", "color": "#999999", "margin": "xs", "wrap": True
            })

        body_contents.append({
            "type": "box", "layout": "horizontal",
            "spacing": "sm",
            "paddingTop": "10px", "paddingBottom": "10px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": "☐", "size": "sm", "color": "#888888", "flex": 0},
                {"type": "box", "layout": "vertical", "flex": 1, "contents": item_contents}
            ]
        })
        if i < len(tasks) - 1:
            body_contents.append(SEPARATOR)

    return {
        "type": "flex",
        "altText": f"✅ 待辦事項（{len(tasks)} 項）",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#e65100",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "✅ 待辦事項",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": f"共 {len(tasks)} 項未完成",
                     "color": "#ffccbc", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body_contents
            }
        }
    }


# ── 指令選單 ──────────────────────────────────────────────────────────
def build_flex_menu() -> dict:
    """可用指令選單：行事曆 + 信件 兩張卡片輪播"""
    def _row(icon, cmd, desc, send_text=None, clickable=True):
        row = {
            "type": "box", "layout": "horizontal",
            "paddingTop": "9px", "paddingBottom": "9px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": icon, "size": "sm", "flex": 0},
                {"type": "text", "text": cmd, "size": "sm",
                 "color": "#1a73e8" if clickable else "#aaaaaa",
                 "weight": "bold", "flex": 0},
                {"type": "text", "text": desc, "size": "xs", "color": "#888888",
                 "flex": 1, "wrap": True, "align": "end"}
            ]
        }
        if clickable:
            row["action"] = {
                "type": "message",
                "label": cmd,
                "text": send_text or cmd
            }
        return row

    def _bubble(header_color, title, subtitle, cmds):
        body = []
        for i, (icon, cmd, desc, send_text, clickable) in enumerate(cmds):
            body.append(_row(icon, cmd, desc, send_text, clickable))
            if i < len(cmds) - 1:
                body.append(SEPARATOR)
        return {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": header_color, "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": title,
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": subtitle,
                     "color": "#ffffff99", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body
            }
        }

    cal_bubble = _bubble(
        header_color="#1a73e8",
        title="📅 行事曆指令",
        subtitle="滑動查看信件指令 →",
        cmds=[
            ("📅", "今日行程", "今天的行程", None, True),
            ("📅", "明日行程", "明天的行程", None, True),
            ("📅", "本週行程", "未來 7 天", None, True),
            ("📅", "本月行程", "本月全部", None, True),
            ("📅", "5月行程", "指定月份", None, True),
            ("🔍", "搜尋 關鍵字", "搜尋行程", None, False),
        ]
    )

    email_bubble = _bubble(
        header_color="#d50000",
        title="📩 信件指令",
        subtitle="滑動查看行事曆指令 →",
        cmds=[
            ("📩", "信件", "未讀封數 + 草稿數量", None, True),
            ("📩", "未讀信件", "列出所有未讀信件", None, True),
            ("📝", "信件草稿", "列出所有待發草稿", None, True),
            ("🔍", "搜尋信件 關鍵字", "搜尋信件", None, False),
        ]
    )

    return {
        "type": "flex",
        "altText": "📋 可用指令清單",
        "contents": {
            "type": "carousel",
            "contents": [cal_bubble, email_bubble]
        }
    }


# ── 活動提醒 ──────────────────────────────────────────────────────────
def build_flex_event_reminder(event_name: str, event_time: str, location: str = "") -> dict:
    """活動 1 小時前提醒卡片"""
    body_contents = [
        {"type": "text", "text": event_name, "size": "md", "weight": "bold",
         "color": "#222222", "wrap": True},
        {
            "type": "box", "layout": "horizontal",
            "margin": "md", "spacing": "sm",
            "contents": [
                {"type": "text", "text": "🕐", "size": "sm", "flex": 0},
                {"type": "text", "text": event_time, "size": "sm", "color": "#555555"}
            ]
        }
    ]
    if location:
        body_contents.append({
            "type": "box", "layout": "horizontal",
            "margin": "sm", "spacing": "sm",
            "contents": [
                {"type": "text", "text": "📍", "size": "sm", "flex": 0},
                {"type": "text", "text": location, "size": "sm",
                 "color": "#555555", "flex": 1, "wrap": True}
            ]
        })

    return {
        "type": "flex",
        "altText": f"⏰ 1小時後：{event_name}",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#f57c00",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "⏰ 活動提醒",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": "1 小時後即將開始",
                     "color": "#ffe0b2", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "16px", "spacing": "none",
                "contents": body_contents
            }
        }
    }


# ── 草稿完成通知 ──────────────────────────────────────────────────────
def build_flex_unread_emails(emails: list) -> dict:
    """未讀信件列表卡片"""
    body_contents = []
    for i, email in enumerate(emails):
        sender = email["from_name"] or email["from_email"]
        body_contents.append({
            "type": "box", "layout": "vertical",
            "paddingTop": "10px", "paddingBottom": "10px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": email["subject"],
                 "size": "sm", "color": "#222222", "weight": "bold", "wrap": True},
                {"type": "box", "layout": "horizontal",
                 "margin": "xs", "spacing": "sm",
                 "contents": [
                     {"type": "text", "text": sender, "size": "xs",
                      "color": "#888888", "flex": 1, "wrap": True},
                     {"type": "text", "text": email["date"],
                      "size": "xs", "color": "#aaaaaa", "flex": 0}
                 ]}
            ]
        })
        if i < len(emails) - 1:
            body_contents.append(SEPARATOR)

    return {
        "type": "flex",
        "altText": f"📩 未讀信件（{len(emails)} 封）",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#d50000", "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "📩 未讀信件",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": f"共 {len(emails)} 封未讀",
                     "color": "#ffcdd2", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body_contents
            }
        }
    }


def build_flex_drafts_list(drafts: list) -> dict:
    """草稿列表卡片"""
    body_contents = []
    for i, draft in enumerate(drafts):
        to_display = draft["to"] if draft["to"] else "（未填收件人）"
        body_contents.append({
            "type": "box", "layout": "vertical",
            "paddingTop": "10px", "paddingBottom": "10px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": draft["subject"],
                 "size": "sm", "color": "#222222", "weight": "bold", "wrap": True},
                {"type": "box", "layout": "horizontal",
                 "margin": "xs", "spacing": "sm",
                 "contents": [
                     {"type": "text", "text": "寄給", "size": "xs",
                      "color": "#aaaaaa", "flex": 0},
                     {"type": "text", "text": to_display, "size": "xs",
                      "color": "#888888", "flex": 1, "wrap": True}
                 ]}
            ]
        })
        if i < len(drafts) - 1:
            body_contents.append(SEPARATOR)

    return {
        "type": "flex",
        "altText": f"📝 草稿列表（{len(drafts)} 封）",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#f57f17", "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "📝 信件草稿",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": f"共 {len(drafts)} 封待發",
                     "color": "#ffe0b2", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body_contents
            }
        }
    }


def build_flex_email_search(emails: list, keyword: str) -> dict:
    """信件搜尋結果卡片"""
    body_contents = []
    for i, email in enumerate(emails):
        body_contents.append({
            "type": "box", "layout": "vertical",
            "paddingTop": "10px", "paddingBottom": "10px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {
                    "type": "text", "text": email["subject"],
                    "size": "sm", "color": "#222222", "weight": "bold", "wrap": True
                },
                {
                    "type": "box", "layout": "horizontal",
                    "margin": "xs", "spacing": "sm",
                    "contents": [
                        {"type": "text", "text": email["from_name"] or email["from_email"],
                         "size": "xs", "color": "#888888", "flex": 1, "wrap": True},
                        {"type": "text", "text": email["date"],
                         "size": "xs", "color": "#aaaaaa", "flex": 0, "wrap": False}
                    ]
                }
            ]
        })
        if i < len(emails) - 1:
            body_contents.append(SEPARATOR)

    return {
        "type": "flex",
        "altText": f"📩 搜尋「{keyword}」找到 {len(emails)} 封信",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#1a73e8", "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "📩 信件搜尋",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": f"「{keyword}」共 {len(emails)} 封",
                     "color": "#c7dcfc", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body_contents
            }
        }
    }


def build_flex_draft_ready(sender_name: str, subject: str) -> dict:
    """草稿完成通知卡片（按下「幫我起草」後的推播）"""
    return {
        "type": "flex",
        "altText": f"✉️ 草稿已備妥：{subject}",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#2e7d32",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "✉️ 草稿已備妥",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": "請至 Gmail 確認並發送",
                     "color": "#c8e6c9", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "14px", "spacing": "none",
                "contents": [
                    {
                        "type": "box", "layout": "horizontal",
                        "spacing": "sm", "paddingBottom": "8px",
                        "contents": [
                            {"type": "text", "text": "寄件人", "size": "xs",
                             "color": "#888888", "flex": 0},
                            {"type": "text", "text": sender_name, "size": "sm",
                             "color": "#222222", "flex": 1, "wrap": True}
                        ]
                    },
                    SEPARATOR,
                    {
                        "type": "box", "layout": "horizontal",
                        "spacing": "sm", "paddingTop": "8px",
                        "contents": [
                            {"type": "text", "text": "主旨", "size": "xs",
                             "color": "#888888", "flex": 0},
                            {"type": "text", "text": subject, "size": "sm",
                             "color": "#333333", "flex": 1, "wrap": True}
                        ]
                    }
                ]
            }
        }
    }
