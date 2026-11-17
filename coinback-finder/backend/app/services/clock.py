from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ist_day_start_utc(moment: datetime | None = None) -> datetime:
    local = (moment or utcnow()).astimezone(IST)
    return datetime.combine(local.date(), time.min, tzinfo=IST).astimezone(timezone.utc)


def range_start(range_key: str, now: datetime | None = None) -> datetime:
    now = now or utcnow()
    if range_key == "today":
        return ist_day_start_utc(now)
    days = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}.get(range_key, 30)
    return ist_day_start_utc(now) - timedelta(days=days - 1)


def format_ist(moment: datetime | None, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    if moment is None:
        return "Not available"
    return moment.astimezone(IST).strftime(fmt) + " IST"
