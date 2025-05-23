from datetime import datetime
import re


def normalize_date(date_str: str) -> datetime:
    """
    Chuyển các định dạng ngày giờ thường gặp sang datetime.
    """
    date_str = date_str.strip()
    # dd/mm/YYYY, HH:MM
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4}),?\s*(\d{1,2}):(\d{2})", date_str)
    if m:
        day, month, year, hour, minute = m.groups()
        return datetime(int(year), int(month), int(day), int(hour), int(minute))
    # dd-mm-YYYY HH:MM
    m = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})", date_str)
    if m:
        day, month, year, hour, minute = m.groups()
        return datetime(int(year), int(month), int(day), int(hour), int(minute))
    # ISO 8601
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        pass
    # Fallback: now
    return datetime.now()