from __future__ import annotations

import base64
from datetime import datetime, date
from typing import Optional

from jobspy.model import Location, Country, JobType, Compensation, CompensationInterval


def offset_to_cursor(offset: int) -> str:
    """Encode a page offset as a relay cursor (base64 of the integer string)."""
    return base64.b64encode(str(offset).encode()).decode()


def decode_relay_id(relay_id: str) -> str:
    """
    Decode a relay global ID like "Sm9iLTEwODAzNzI0" → "Job-10803724" → "10803724".
    Falls back to returning the raw id if decoding fails.
    """
    try:
        decoded = base64.b64decode(relay_id + "==").decode()
        # format is "TypeName-integer"
        if "-" in decoded:
            return decoded.split("-", 1)[1]
    except Exception:
        pass
    return relay_id


def parse_location(location_obj: dict | str | None) -> Location:
    if not location_obj:
        return Location()
    if isinstance(location_obj, str):
        parts = [p.strip() for p in location_obj.split(",")]
        if len(parts) >= 3:
            country_str = parts[2]
            try:
                country = Country.from_string(country_str)
            except ValueError:
                country = country_str
            return Location(city=parts[0], state=parts[1], country=country)
        elif len(parts) == 2:
            return Location(city=parts[0], state=parts[1])
        return Location(city=parts[0])
    # dict from GraphQL locations array
    city = location_obj.get("city")
    state = location_obj.get("state")
    country_str = location_obj.get("country")
    country = None
    if country_str:
        try:
            country = Country.from_string(country_str)
        except ValueError:
            country = country_str
    return Location(city=city, state=state, country=country)


def parse_date(date_str: str | None) -> Optional[date]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


_INTERVAL_MAP = {
    "hourly": CompensationInterval.HOURLY,
    "hour": CompensationInterval.HOURLY,
    "daily": CompensationInterval.DAILY,
    "day": CompensationInterval.DAILY,
    "weekly": CompensationInterval.WEEKLY,
    "week": CompensationInterval.WEEKLY,
    "monthly": CompensationInterval.MONTHLY,
    "month": CompensationInterval.MONTHLY,
    "yearly": CompensationInterval.YEARLY,
    "year": CompensationInterval.YEARLY,
    "annual": CompensationInterval.YEARLY,
}


def parse_compensation(salary_range: dict | None) -> Optional[Compensation]:
    if not salary_range:
        return None
    min_amount = salary_range.get("min")
    max_amount = salary_range.get("max")
    if min_amount is None and max_amount is None:
        return None
    currency = salary_range.get("currency", "USD")
    pay_schedule = salary_range.get("paySchedule") or {}
    interval_key = (pay_schedule.get("behaviorIdentifier") or "").lower()
    interval = _INTERVAL_MAP.get(interval_key)
    return Compensation(
        min_amount=min_amount,
        max_amount=max_amount,
        currency=currency,
        interval=interval,
    )


def parse_job_type(job_type_obj: dict | None) -> list[JobType] | None:
    if not job_type_obj:
        return None
    name = (job_type_obj.get("name") or "").lower().replace(" ", "").replace("-", "")
    for jt in JobType:
        if any(alias == name for alias in jt.value):
            return [jt]
    return None


def is_job_remote(
    remote: bool | None,
    hybrid: bool | None,
    title: str | None,
    description: str | None = None,
) -> bool:
    if remote:
        return True
    remote_keywords = ("remote", "work from home", "wfh")
    for text in (title, description):
        if text and any(kw in text.lower() for kw in remote_keywords):
            return True
    return False
