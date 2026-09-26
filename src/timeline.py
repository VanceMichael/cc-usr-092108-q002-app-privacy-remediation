"""期限时间线：通报、顺延等事件一律按发生时间重放。

整改期限自通报次日起数工作日，跳过周末与给定节假日；法定
期限顺延以事件发生时间为准，无论登记先后，重放结果一致。
"""

from datetime import date, timedelta

from .common import ValidationError, parse_instant, require_fields


def add_working_days(start: date, count: int, holidays=frozenset()) -> date:
    """从次日起数 count 个工作日，跳过周末与节假日。"""
    if count < 0:
        raise ValidationError("工作日数不能为负")
    day = start
    remaining = count
    while remaining:
        day += timedelta(days=1)
        if day.weekday() < 5 and day not in holidays:
            remaining -= 1
    return day


def replay_deadline(
    notice_date: date, base_working_days: int, extensions=(), holidays=()
) -> dict:
    """按发生时间重放顺延事件，返回期限时间线与最终期限。"""
    settled = {
        date.fromisoformat(day) if isinstance(day, str) else day for day in holidays
    }
    base = add_working_days(notice_date, base_working_days, settled)
    timeline = [
        {
            "kind": "notice",
            "occurred_at": notice_date.isoformat(),
            "base_working_days": base_working_days,
            "deadline": base.isoformat(),
        }
    ]
    current = base
    ordered = sorted(
        extensions,
        key=lambda e: (e["occurred_at"], e.get("recorded_at", "")),
    )
    for extension in ordered:
        require_fields(
            extension, ("occurred_at", "extra_working_days"), "期限顺延事件"
        )
        parse_instant(extension["occurred_at"])
        current = add_working_days(
            current, extension["extra_working_days"], settled
        )
        timeline.append(
            {
                "kind": "extension",
                "occurred_at": extension["occurred_at"],
                "extra_working_days": extension["extra_working_days"],
                "reason": extension.get("reason", ""),
                "deadline": current.isoformat(),
            }
        )
    return {"timeline": timeline, "final_deadline": current.isoformat()}
