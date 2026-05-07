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


def _parse_date_range(event: dict) -> str:
    """Return MM/DD or MM/DD～MM/DD for multi-day all-day events."""
    from datetime import date as date_cls, timedelta
    start_str = _parse_date(event.get("start", {}))
    if _is_all_day(event):
        end_date = event.get("end", {}).get("date", "")
        if end_date:
            parts = end_date.split("-")
            if len(parts) == 3:
                # Google Calendar end date is exclusive, subtract 1 day
                end_dt = date_cls(int(parts[0]), int(parts[1]), int(parts[2])) - timedelta(days=1)
                end_str = f"{end_dt.month:02d}/{end_dt.day:02d}"
                if end_str != start_str:
                    return f"{start_str}～{end_str}"
    return start_str


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
    date_label = _parse_date_range(event)
    title = event.get("summary", "（無標題）")
    all_day = _is_all_day(event)
    is_task = event.get("is_task", False)

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

    if is_task or not all_day:
        badge_text = "☑ 工作" if is_task else _parse_time(event["start"]["dateTime"])
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
                "text": badge_text,
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
    is_task = event.get("is_task", False)
    if is_task:
        time_text = "☑ 工作"
    elif all_day:
        time_text = "全天"
    else:
        time_text = _parse_time(event["start"]["dateTime"])

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
    MAX_EVENTS = 10
    body = []
    body.append(_build_calendar_header(calendar_name, color))

    # 合併後限制總筆數
    all_events = all_day_events + timed_events
    hidden_count = max(0, len(all_events) - MAX_EVENTS)
    all_day_events = all_day_events[:MAX_EVENTS]
    timed_events = timed_events[:max(0, MAX_EVENTS - len(all_day_events))]

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

    if hidden_count > 0:
        body.append({"type": "text", "text": f"⋯ 還有 {hidden_count} 件未顯示", "size": "xxs", "color": "#aaaaaa", "margin": "sm"})

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


def _build_week_event_row(event: dict, color: dict, cal_name: str = "") -> dict:
    """週視圖的行程列：彩色點 + 日期 + 時間badge + 標題 + 日曆名稱"""
    date_label = _parse_date_range(event)
    title = event.get("summary", "（無標題）")
    all_day = _is_all_day(event)
    is_task = event.get("is_task", False)

    if is_task:
        badge_text = "☑"
    elif all_day:
        badge_text = "全天"
    else:
        badge_text = _parse_time(event["start"]["dateTime"])

    # 標題 + 日曆名稱（小字）
    title_contents = [
        {"type": "text", "text": title, "size": "sm", "color": "#222222", "wrap": True}
    ]
    if cal_name:
        title_contents.append({
            "type": "text", "text": cal_name, "size": "xxs", "color": "#aaaaaa", "margin": "xs"
        })

    return {
        "type": "box",
        "layout": "horizontal",
        "paddingTop": "8px",
        "paddingBottom": "8px",
        "paddingStart": "14px",
        "paddingEnd": "14px",
        "spacing": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "width": "8px",
                "contents": [{"type": "filler"}, _dot(color["main"]), {"type": "filler"}]
            },
            {
                "type": "text",
                "text": date_label,
                "size": "xs",
                "color": "#555555",
                "weight": "bold",
                "flex": 0,
                "offsetTop": "1px"
            },
            {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": color["light"],
                "cornerRadius": "4px",
                "paddingTop": "1px",
                "paddingBottom": "1px",
                "paddingStart": "5px",
                "paddingEnd": "5px",
                "flex": 0,
                "contents": [{"type": "text", "text": badge_text, "size": "xxs", "color": color["dark"]}]
            },
            {
                "type": "box",
                "layout": "vertical",
                "flex": 1,
                "contents": title_contents
            }
        ]
    }


def _build_week_bubble(week_label: str, date_range_label: str, events: list,
                       calendar_map: dict, page_label: str, total_count: int) -> dict:
    """一週的行程 bubble，最多顯示 10 筆"""
    MAX_PER_WEEK = 10

    def sort_key(e):
        s = e.get("start", {})
        return s.get("date") or s.get("dateTime", "")

    sorted_events = sorted(events, key=sort_key)
    hidden = max(0, len(sorted_events) - MAX_PER_WEEK)
    shown = sorted_events[:MAX_PER_WEEK]

    body = []
    for i, ev in enumerate(shown):
        cid = ev.get("calendarId", "primary")
        cal = calendar_map.get(cid, {"id": cid})
        color = get_calendar_color(cal)
        cal_name = cal.get("summary", "")
        body.append(_build_week_event_row(ev, color, cal_name))
        if i < len(shown) - 1:
            body.append(SEPARATOR)

    if hidden > 0:
        body.append({
            "type": "text",
            "text": f"⋯ 還有 {hidden} 件",
            "size": "xxs",
            "color": "#aaaaaa",
            "margin": "sm",
            "paddingStart": "14px"
        })

    if not body:
        body.append({
            "type": "text",
            "text": "本週無行程",
            "size": "sm",
            "color": "#aaaaaa",
            "align": "center",
            "paddingAll": "20px"
        })

    return {
        "type": "bubble",
        "size": "kilo",
        "header": _build_header(f"📅 {week_label}", date_range_label, page_label),
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
            "paddingAll": "8px",
            "contents": [{"type": "text", "text": f"共 {total_count} 件・滑動查看其他週 →",
                          "size": "xxs", "color": "#aaaaaa", "align": "center"}]
        }
    }


def build_flex_carousel(calendar_list: list, event_list: list, month_label: str) -> dict:
    """月份行程：按週分組，每週一張 bubble"""
    from datetime import date as date_cls, timedelta

    calendar_map = {cal["id"]: cal for cal in calendar_list}
    total_count = len(event_list)

    def sort_key(e):
        s = e.get("start", {})
        return s.get("date") or s.get("dateTime", "")

    # 按週分組（以週一為起點）
    week_groups: dict = {}
    for event in sorted(event_list, key=sort_key):
        date_str = sort_key(event)[:10]
        try:
            parts = date_str.split("-")
            d = date_cls(int(parts[0]), int(parts[1]), int(parts[2]))
            week_start = d - timedelta(days=d.weekday())  # 該週週一
            week_groups.setdefault(week_start, []).append(event)
        except Exception:
            week_groups.setdefault(date_cls.today(), []).append(event)

    bubbles = []
    sorted_weeks = sorted(week_groups.keys())
    total_weeks = len(sorted_weeks)

    week_names = ["第一週", "第二週", "第三週", "第四週", "第五週", "第六週"]

    for i, week_start in enumerate(sorted_weeks):
        week_end = week_start + timedelta(days=6)
        date_range = f"{week_start.month}/{week_start.day} - {week_end.month}/{week_end.day}"
        week_name = week_names[i] if i < len(week_names) else f"第{i+1}週"
        events = week_groups[week_start]

        bubbles.append(_build_week_bubble(
            week_label=f"{month_label}{week_name}",
            date_range_label=date_range,
            events=events,
            calendar_map=calendar_map,
            page_label=f"{i + 1} / {total_weeks}",
            total_count=total_count
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


def build_flex_evening_push(calendar_list: list, event_list: list) -> dict:
    """晚上推播：明日行程（單張）"""
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
        "altText": f"📅 明日行程 {total} 件",
        "contents": bubble
    }


def build_flex_morning_summary(calendar_list: list, event_list: list) -> dict:
    """早晨推播：今日行程件數 + 事件列表"""
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
        "altText": f"☀️ 早安！今天 {total} 件行程",
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
    sender_role: str = "",
    sender_unit: str = "",
    draft_ready: bool = False,
    should_reply: bool = False,
    message_id: str = "",
) -> dict:
    """聯絡人來信通知卡片
    高重要度：draft_ready=True（草稿已備妥）
    中重要度：should_reply=True（顯示起草按鈕）
    """
    if sender_role and sender_unit:
        sender_display = f"{sender_name}（{sender_unit} {sender_role}）"
    elif sender_role:
        sender_display = f"{sender_name}（{sender_role}）"
    else:
        sender_display = sender_name

    body = [
        {
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "paddingTop": "12px", "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": "寄件人", "size": "xs", "color": "#888888", "flex": 0},
                {"type": "text", "text": sender_display, "size": "sm", "color": "#222222",
                 "flex": 1, "wrap": True},
            ]
        },
        {
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "paddingTop": "6px", "paddingBottom": "12px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": "主旨", "size": "xs", "color": "#888888", "flex": 0},
                {"type": "text", "text": subject, "size": "sm", "color": "#333333",
                 "flex": 1, "wrap": True},
            ]
        },
    ]

    if draft_ready:
        footer = {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#e8f5e9", "paddingAll": "12px",
            "contents": [{"type": "text", "text": "✉️ 草稿已備妥，請至 Gmail 確認",
                          "size": "xs", "color": "#2e7d32", "align": "center"}]
        }
    elif should_reply:
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

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#1a73e8", "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "📩 新信件", "color": "#ffffff",
                 "size": "md", "weight": "bold"},
                {"type": "text", "text": "聯絡人來信", "color": "#c7dcfc",
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
        header_contents = [
            {"type": "text", "text": title,
             "color": "#ffffff", "size": "md", "weight": "bold"}
        ]
        if subtitle:
            header_contents.append(
                {"type": "text", "text": subtitle,
                 "color": "#ffffff99", "size": "xxs", "margin": "xs"}
            )
        return {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": header_color, "paddingAll": "14px",
                "contents": header_contents
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
        subtitle="",
        cmds=[
            ("📅", "今日行程", "今天的行程", None, True),
            ("📅", "明日行程", "明天的行程", None, True),
            ("📅", "本週行程", "本週一到週日", None, True),
            ("📅", "本月行程", "本月全部（依週顯示）", None, True),
            ("📅", "N月行程", "指定月份，如：五月行程", None, False),
            ("➕", "新增行程", "查看新增格式", None, True),
            ("🔍", "搜尋 關鍵字", "搜尋行程", None, False),
        ]
    )
    cal_bubble["footer"] = {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#f5f5f5",
        "paddingAll": "10px",
        "contents": [{
            "type": "text",
            "text": "小撇步： 直接輸入「今日」即可查看當日行程。",
            "size": "xxs", "color": "#888888", "wrap": True
        }]
    }

    email_bubble = _bubble(
        header_color="#d50000",
        title="📩 信件指令",
        subtitle="",
        cmds=[
            ("📩", "信件", "近期 10 封信件", None, True),
            ("📩", "未讀信件", "列出 10 封未讀信件", None, True),
            ("📝", "信件草稿", "列出所有待發草稿", None, True),
            ("🔴", "信件 高", "重要度高聯絡人的來信", None, True),
            ("🟡", "信件 中", "重要度中聯絡人的來信", None, True),
            ("⚪", "信件 低", "重要度低聯絡人的來信", None, True),
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


# ── 信件列表（共用 2 張卡片輪播）────────────────────────────────────
def build_flex_email_carousel(emails: list, title: str) -> dict:
    """信件列表輪播：最多 10 封，分 2 張卡片，每張 5 封"""

    def _email_row(email):
        sender = email.get("from_name") or email.get("from_email", "未知")
        subject = email.get("subject", "（無主旨）")
        date_str = (email.get("date") or "")[:10]
        return {
            "type": "box", "layout": "vertical",
            "paddingTop": "9px", "paddingBottom": "9px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": subject, "size": "sm", "color": "#222222",
                 "weight": "bold", "wrap": True},
                {"type": "box", "layout": "horizontal", "margin": "xs", "spacing": "sm",
                 "contents": [
                     {"type": "text", "text": sender, "size": "xs", "color": "#888888",
                      "flex": 1, "wrap": False},
                     {"type": "text", "text": date_str, "size": "xs", "color": "#aaaaaa",
                      "flex": 0}
                 ]}
            ]
        }

    def _build_bubble(batch, page_num, total_pages):
        body_contents = []
        for i, email in enumerate(batch):
            body_contents.append(_email_row(email))
            if i < len(batch) - 1:
                body_contents.append(SEPARATOR)
        header_contents = [
            {"type": "text", "text": f"📩 {title}", "color": "#ffffff",
             "size": "md", "weight": "bold"},
        ]
        if total_pages > 1:
            header_contents.append(
                {"type": "text", "text": f"{page_num} / {total_pages}",
                 "color": "#c7dcfc", "size": "xxs", "margin": "xs"}
            )
        return {
            "type": "bubble", "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#d50000", "paddingAll": "14px",
                "contents": header_contents
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body_contents
            }
        }

    if not emails:
        return {
            "type": "flex",
            "altText": f"📩 {title}",
            "contents": {
                "type": "bubble", "size": "kilo",
                "header": {
                    "type": "box", "layout": "vertical",
                    "backgroundColor": "#d50000", "paddingAll": "14px",
                    "contents": [{"type": "text", "text": f"📩 {title}",
                                  "color": "#ffffff", "size": "md", "weight": "bold"}]
                },
                "body": {
                    "type": "box", "layout": "vertical", "paddingAll": "24px",
                    "contents": [{"type": "text", "text": "沒有找到信件",
                                  "size": "sm", "color": "#888888", "align": "center"}]
                }
            }
        }

    chunks = [emails[i:i+5] for i in range(0, min(len(emails), 10), 5)]
    total_pages = len(chunks)
    bubbles = [_build_bubble(chunk, i + 1, total_pages) for i, chunk in enumerate(chunks)]

    return {
        "type": "flex",
        "altText": f"📩 {title}（共 {len(emails)} 封）",
        "contents": {"type": "carousel", "contents": bubbles}
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


def build_flex_add_event_help(error_hint: str = "") -> dict:
    """新增行程格式說明卡片"""
    def _fmt_row(situation, example):
        return {
            "type": "box", "layout": "vertical",
            "paddingTop": "8px", "paddingBottom": "8px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": situation, "size": "xs", "color": "#888888"},
                {"type": "text", "text": example, "size": "sm", "color": "#1a73e8",
                 "weight": "bold", "wrap": True, "margin": "xs"}
            ]
        }

    rows = [
        _fmt_row("單天 + 時間", "新增行程 明天 14:00 品牌會議"),
        {"type": "separator", "color": "#f0f0f0"},
        _fmt_row("單天 + 全天", "新增行程 05/01 全天 法國假期"),
        {"type": "separator", "color": "#f0f0f0"},
        _fmt_row("連續多天 + 全天", "新增行程 05/01~05/03 全天 法國出差"),
        {"type": "separator", "color": "#f0f0f0"},
        _fmt_row("連續多天 + 時間", "新增行程 05/01~05/03 09:00 展覽佈置"),
        {"type": "separator", "color": "#f0f0f0"},
        _fmt_row("加地點（@）", "新增行程 明天 14:00 品牌會議 @台北辦公室"),
        {"type": "separator", "color": "#f0f0f0"},
        {
            "type": "box", "layout": "vertical",
            "paddingTop": "8px", "paddingBottom": "8px",
            "paddingStart": "14px", "paddingEnd": "14px",
            "contents": [
                {"type": "text", "text": "日期格式", "size": "xs", "color": "#888888"},
                {"type": "text", "text": "MM/DD・今天・明天・後天・下週一～下週日",
                 "size": "xs", "color": "#555555", "wrap": True, "margin": "xs"}
            ]
        }
    ]

    if error_hint:
        rows.insert(0, {
            "type": "box", "layout": "horizontal",
            "backgroundColor": "#fff3e0", "paddingAll": "10px",
            "contents": [
                {"type": "text", "text": f"⚠️ {error_hint}",
                 "size": "xs", "color": "#e65100", "wrap": True}
            ]
        })
        rows.insert(1, {"type": "separator", "color": "#f0f0f0"})

    return {
        "type": "flex",
        "altText": "📅 新增行程格式說明",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#1a73e8", "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "📅 新增行程",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": "指令格式參考",
                     "color": "#c7dcfc", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": rows
            }
        }
    }


def build_flex_event_created(title: str, date_str: str, time_str: str, location: str = "") -> dict:
    """行程建立成功通知卡片"""
    body = [
        {"type": "box", "layout": "horizontal", "spacing": "sm",
         "paddingTop": "12px", "paddingBottom": "6px",
         "paddingStart": "14px", "paddingEnd": "14px",
         "contents": [
             {"type": "text", "text": "標題", "size": "xs", "color": "#888888", "flex": 0},
             {"type": "text", "text": title, "size": "sm", "color": "#222222",
              "flex": 1, "wrap": True, "weight": "bold"}
         ]},
        {"type": "separator", "color": "#f0f0f0"},
        {"type": "box", "layout": "horizontal", "spacing": "sm",
         "paddingTop": "6px", "paddingBottom": "6px",
         "paddingStart": "14px", "paddingEnd": "14px",
         "contents": [
             {"type": "text", "text": "日期", "size": "xs", "color": "#888888", "flex": 0},
             {"type": "text", "text": date_str, "size": "sm", "color": "#333333", "flex": 1}
         ]},
    ]
    if time_str:
        body.append({"type": "separator", "color": "#f0f0f0"})
        body.append({"type": "box", "layout": "horizontal", "spacing": "sm",
                     "paddingTop": "6px", "paddingBottom": "6px",
                     "paddingStart": "14px", "paddingEnd": "14px",
                     "contents": [
                         {"type": "text", "text": "時間", "size": "xs", "color": "#888888", "flex": 0},
                         {"type": "text", "text": time_str, "size": "sm", "color": "#333333", "flex": 1}
                     ]})
    if location:
        body.append({"type": "separator", "color": "#f0f0f0"})
        body.append({"type": "box", "layout": "horizontal", "spacing": "sm",
                     "paddingTop": "6px", "paddingBottom": "10px",
                     "paddingStart": "14px", "paddingEnd": "14px",
                     "contents": [
                         {"type": "text", "text": "地點", "size": "xs", "color": "#888888", "flex": 0},
                         {"type": "text", "text": location, "size": "sm", "color": "#333333",
                          "flex": 1, "wrap": True}
                     ]})

    return {
        "type": "flex",
        "altText": f"✅ 行程已建立：{title}",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#2e7d32", "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "✅ 行程已建立",
                     "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": "已加入 Google 日曆",
                     "color": "#c8e6c9", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "paddingAll": "0px", "spacing": "none",
                "contents": body
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


def build_flex_calendar_list(calendars: list) -> dict:
    """顯示所有行事曆狀態的 Flex bubble"""
    rows = []
    for i, cal in enumerate(calendars):
        visible = cal["visible"]
        color = cal["backgroundColor"]
        status_text = "✅ 顯示中" if visible else "❌ 已隱藏"
        status_color = "#34a853" if visible else "#ea4335"

        row = {
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
                    "width": "10px",
                    "contents": [{"type": "filler"}, _dot(color, "10px", "5px"), {"type": "filler"}]
                },
                {
                    "type": "text",
                    "text": cal["name"],
                    "size": "sm",
                    "color": "#222222",
                    "flex": 1,
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": status_text,
                    "size": "xs",
                    "color": status_color,
                    "flex": 0,
                    "align": "end"
                }
            ]
        }
        rows.append(row)
        if i < len(calendars) - 1:
            rows.append(SEPARATOR)

    return {
        "type": "flex",
        "altText": "📅 行事曆清單",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": _build_header("📅 行事曆清單", f"共 {len(calendars)} 個日曆"),
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "0px",
                "spacing": "none",
                "contents": rows
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#f5f5f5",
                "paddingAll": "10px",
                "contents": [{"type": "text",
                              "text": "取消顯示 [名稱] 隱藏・顯示 [名稱] 恢復",
                              "size": "xxs", "color": "#aaaaaa", "align": "center", "wrap": True}]
            }
        }
    }
