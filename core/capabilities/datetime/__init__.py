from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

try:
    import zoneinfo
    _ZONEINFO_AVAILABLE = True
except ImportError:
    _ZONEINFO_AVAILABLE = False

from core.capabilities.base import Capability, Skill, object_schema
from core.capabilities.registry import register
from core.capabilities.result import CapabilityResult

# Common IANA timezone aliases for user-friendly input
_IANA_ALIASES = {
    # US timezones
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "AKST": "America/Anchorage",
    "AKDT": "America/Anchorage",
    "HST": "Pacific/Honolulu",
    "HDT": "Pacific/Honolulu",
    # Common colloquial names
    "NEW_YORK": "America/New_York",
    "CHICAGO": "America/Chicago",
    "DENVER": "America/Denver",
    "LOS_ANGELES": "America/Los_Angeles",
    "SAN_FRANCISCO": "America/Los_Angeles",
    "SEATTLE": "America/Los_Angeles",
    "PHOENIX": "America/Phoenix",
    "ANCHORAGE": "America/Anchorage",
    "HONOLULU": "Pacific/Honolulu",
    # European timezones
    "GMT": "Europe/London",
    "BST": "Europe/London",
    "UTC": "UTC",
    "CET": "Europe/Berlin",
    "CEST": "Europe/Berlin",
    "EET": "Europe/Helsinki",
    "EEST": "Europe/Helsinki",
    "WET": "Europe/Lisbon",
    "WEST": "Europe/Lisbon",
    "LONDON": "Europe/London",
    "PARIS": "Europe/Paris",
    "BERLIN": "Europe/Berlin",
    "ROME": "Europe/Rome",
    "MADRID": "Europe/Madrid",
    "AMSTERDAM": "Europe/Amsterdam",
    "BRUSSELS": "Europe/Brussels",
    "VIENNA": "Europe/Vienna",
    "WARSAW": "Europe/Warsaw",
    "MOSCOW": "Europe/Moscow",
    "KYIV": "Europe/Kyiv",
    "ISTANBUL": "Europe/Istanbul",
    # Asian timezones
    "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo",
    "KST": "Asia/Seoul",
    "CST_CHINA": "Asia/Shanghai",
    "HKT": "Asia/Hong_Kong",
    "SINGAPORE": "Asia/Singapore",
    "BANGKOK": "Asia/Bangkok",
    "DUBAI": "Asia/Dubai",
    "TEL_AVIV": "Asia/Jerusalem",
    # Oceanic
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
    "ACST": "Australia/Adelaide",
    "ACDT": "Australia/Adelaide",
    "AWST": "Australia/Perth",
    "NZST": "Pacific/Auckland",
    "NZDT": "Pacific/Auckland",
    "SYDNEY": "Australia/Sydney",
    "MELBOURNE": "Australia/Melbourne",
    "BRISBANE": "Australia/Brisbane",
    "PERTH": "Australia/Perth",
    "AUCKLAND": "Pacific/Auckland",
    "WELLINGTON": "Pacific/Auckland",
}


def _resolve_iana_zone(tz_name: str) -> str:
    """Resolve a timezone name to an IANA zone identifier."""
    upper = tz_name.upper().strip().replace(" ", "_")
    if upper in _IANA_ALIASES:
        return _IANA_ALIASES[upper]
    # Check if it's already a valid IANA zone
    if _ZONEINFO_AVAILABLE:
        try:
            zoneinfo.ZoneInfo(upper)
            return upper
        except Exception:
            pass
    # Try case-insensitive match
    if _ZONEINFO_AVAILABLE:
        for zone in zoneinfo.available_timezones():
            if zone.upper() == upper:
                return zone
    raise ValueError(
        f"Unknown timezone: {tz_name}. Use IANA names like 'America/New_York', 'Europe/London', etc."
    )


@register
class DateTimeCapability(Capability):
    id = "datetime"
    name = "DateTime"
    version = "2.0.0"
    author = "IdentityOS"
    license = "MIT"
    homepage = "https://github.com/lacebx/IdentityOS"
    description = "Get current time in any IANA timezone, convert between zones, calculate date differences (full DST support)"
    permissions = ["public"]

    def __init__(self, config: Optional[dict] = None) -> None:
        super().__init__(config)

    def install(self, identity_id: str, storage: Any) -> None:
        storage.save(identity_id, "capability.datetime", {"installed_at": None})

    def uninstall(self, identity_id: str, storage: Any) -> None:
        storage.delete(identity_id, "capability.datetime")

    def prompts(self, identity_id: str) -> list[str]:
        return [
            "## DateTime Skills (MANDATORY — use when asked about time/date)",
            "When the user asks for the current time, date, or timezone conversion, you MUST use the skills below.",
            "Do NOT say you don't have real-time access. You DO. Use the skills.",
            "Timezone names should be IANA format (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo').",
            "Common aliases like 'EST', 'PST', 'CET', 'London', 'Tokyo' are auto-resolved.",
        ]

    _SKILLS = [
        Skill(
            name="datetime.now",
            description="Get current date and time in an IANA timezone (e.g., 'America/New_York', 'Europe/London')",
            permission="public",
            input_schema=object_schema({"tz_name": {"type": "string", "default": "UTC"}}),
            verification_params={"tz_name": "UTC"},
        ),
        Skill(
            name="datetime.convert",
            description="Convert a time between IANA timezones with full DST support",
            permission="public",
            input_schema=object_schema(
                {"dt_str": {"type": "string"}, "from_tz": {"type": "string"}, "to_tz": {"type": "string"}},
                required=("dt_str", "from_tz", "to_tz"),
            ),
        ),
        Skill(
            name="datetime.diff",
            description="Calculate days between two dates",
            permission="public",
            input_schema=object_schema(
                {"date1": {"type": "string"}, "date2": {"type": "string"}}, required=("date1", "date2")
            ),
        ),
        Skill(
            name="datetime.zones",
            description="List common IANA timezone identifiers",
            permission="public",
            input_schema=object_schema(),
        ),
    ]

    def skills(self) -> list[Skill]:
        return list(self._SKILLS)

    def call(self, skill_name: str, **params: Any) -> CapabilityResult:
        import time as _time
        _t0 = _time.monotonic()
        try:
            dispatch = {
                "datetime.now": self._now,
                "datetime.convert": self._convert,
                "datetime.diff": self._diff,
                "datetime.zones": self._zones,
            }
            handler = dispatch.get(skill_name)
            if handler is None:
                return CapabilityResult.fail("datetime", skill_name, "unknown_skill", f"Unknown skill: {skill_name}")
            data = handler(**params)
            return CapabilityResult.from_data("datetime", skill_name, data, source="system clock", duration_ms=(_time.monotonic() - _t0) * 1000)
        except Exception as e:
            return CapabilityResult.fail("datetime", skill_name, type(e).__name__, str(e), duration_ms=(_time.monotonic() - _t0) * 1000)

    def _now(self, tz_name: Optional[str] = "UTC", **kwargs: Any) -> dict[str, Any]:
        if tz_name is None:
            tz_name = "UTC"
        iana_zone = _resolve_iana_zone(tz_name)
        if _ZONEINFO_AVAILABLE:
            tz = zoneinfo.ZoneInfo(iana_zone)
            now = datetime.now(tz)
            offset = now.utcoffset()
            offset_hours = offset.total_seconds() / 3600 if offset else 0
            is_dst = bool(now.dst()) if hasattr(now, 'dst') else False
            return {
                "timezone": iana_zone,
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "utc_offset_hours": offset_hours,
                "weekday": now.strftime("%A"),
                "is_dst": is_dst,
                "tz_abbrev": now.tzname() or iana_zone,
            }
        else:
            # Fallback if zoneinfo not available
            offset = self._legacy_utc_offset(tz_name)
            tz = timezone(timedelta(hours=offset))
            now = datetime.now(tz)
            return {
                "timezone": tz_name.upper(),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "utc_offset_hours": offset,
                "weekday": now.strftime("%A"),
                "is_dst": False,
            }

    def _convert(self, dt_str: str = "", from_tz: str = "UTC", to_tz: str = "UTC", **kwargs: Any) -> dict[str, Any]:
        from_zone = _resolve_iana_zone(from_tz)
        to_zone = _resolve_iana_zone(to_tz)
        if _ZONEINFO_AVAILABLE:
            from_tz_obj = zoneinfo.ZoneInfo(from_zone)
            to_tz_obj = zoneinfo.ZoneInfo(to_zone)
            if dt_str:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=from_tz_obj)
            else:
                dt = datetime.now(from_tz_obj)
            converted = dt.astimezone(to_tz_obj)
            from_offset = dt.utcoffset().total_seconds() / 3600 if dt.utcoffset() else 0
            to_offset = converted.utcoffset().total_seconds() / 3600 if converted.utcoffset() else 0
            is_dst_from = bool(dt.dst()) if hasattr(dt, 'dst') else False
            is_dst_to = bool(converted.dst()) if hasattr(converted, 'dst') else False
            return {
                "input": {"datetime": dt.strftime("%Y-%m-%d %H:%M:%S"), "timezone": from_zone},
                "output": {
                    "datetime": converted.strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone": to_zone,
                },
                "difference_hours": to_offset - from_offset,
                "from_dst": is_dst_from,
                "to_dst": is_dst_to,
            }
        else:
            # Fallback
            return self._legacy_convert(dt_str, from_tz, to_tz)

    def _legacy_utc_offset(self, tz_name: str) -> float:
        upper = tz_name.upper().strip()
        legacy_map = {
            "UTC": 0, "GMT": 0, "EST": -5, "CST": -6, "MST": -7, "PST": -8,
            "CET": 1, "EET": 2, "IST": 5.5, "JST": 9, "AEST": 10, "NZST": 12,
        }
        if upper in legacy_map:
            return legacy_map[upper]
        raise ValueError(f"Unknown timezone: {tz_name}")

    def _legacy_convert(self, dt_str: str, from_tz: str, to_tz: str) -> dict[str, Any]:
        from_offset = self._legacy_utc_offset(from_tz)
        to_offset = self._legacy_utc_offset(to_tz)
        dt = datetime.fromisoformat(dt_str) if dt_str else datetime.now()
        delta = to_offset - from_offset
        converted = dt + timedelta(hours=delta)
        return {
            "input": {"datetime": dt_str, "timezone": from_tz.upper()},
            "output": {"datetime": converted.strftime("%Y-%m-%d %H:%M:%S"), "timezone": to_tz.upper()},
            "difference_hours": delta,
        }

    def _diff(self, date1: str = "", date2: str = "", **kwargs: Any) -> dict[str, Any]:
        d1 = datetime.strptime(date1, "%Y-%m-%d") if date1 else datetime.now()
        d2 = datetime.strptime(date2, "%Y-%m-%d") if date2 else datetime.now()
        diff = abs((d2 - d1).days)
        return {
            "date1": d1.strftime("%Y-%m-%d"),
            "date2": d2.strftime("%Y-%m-%d"),
            "days_between": diff,
            "weeks_between": round(diff / 7, 1),
        }

    def _zones(self, **kwargs: Any) -> dict[str, Any]:
        if _ZONEINFO_AVAILABLE:
            # Return a curated list of common zones
            common_zones = sorted(set(_IANA_ALIASES.values()))
            return {"timezones": common_zones, "count": len(common_zones), "note": "Use IANA identifiers (e.g., 'America/New_York'). Full list available via zoneinfo.available_timezones()."}
        else:
            return {"timezones": list(_IANA_ALIASES.values())}