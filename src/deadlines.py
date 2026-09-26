"""限期复核：十五个工作日期限与法定期限顺延事件。

期限自通报发布次日起按工作日计算；顺延事件按发生时间应用，
发生在当前期限之后的顺延不影响已确定的期限。
"""

from datetime import date, datetime, timedelta

BASE_WORKING_DAYS = 15


def add_working_days(start: date, count: int, holidays=()) -> date:
    """从次日起数 count 个工作日（跳过周末与给定节假日）。"""
    skip = {day if isinstance(day, date) else _to_date(day) for day in holidays}
    day, remaining = start, count
    while remaining:
        day += timedelta(days=1)
        if day.weekday() < 5 and day not in skip:
            remaining -= 1
    return day


def compute_deadline(notice_published_at: str, extensions=(), holidays=()) -> dict:
    """按发生时间应用顺延事件，返回期限信息。"""
    notice_date = _to_date(notice_published_at)
    due = add_working_days(notice_date, BASE_WORKING_DAYS, holidays)
    applied = []
    for extension in sorted(extensions, key=lambda e: e["occurred_at"]):
        if _to_date(extension["occurred_at"]) <= due:
            due = add_working_days(due, int(extension["working_days"]), holidays)
            applied.append(dict(extension))
    return {
        "notice_date": notice_date.isoformat(),
        "base_working_days": BASE_WORKING_DAYS,
        "extensions_applied": applied,
        "due": due.isoformat(),
    }


def _to_date(text) -> date:
    if isinstance(text, date):
        return text
    return datetime.fromisoformat(text).date()
