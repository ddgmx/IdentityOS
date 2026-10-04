from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from core.capabilities.datetime import DateTimeCapability


def test_now_accepts_iana_timezone_and_observes_current_offset():
    capability = DateTimeCapability()

    result = capability.call("datetime.now", tz_name="America/Chicago")

    assert result.success is True
    assert result.data["timezone"] == "America/Chicago"
    observed = datetime.fromisoformat(result.data["datetime"]).replace(
        tzinfo=ZoneInfo("America/Chicago")
    )
    assert result.data["utc_offset_hours"] == (
        observed.utcoffset().total_seconds() / 3600
    )


def test_convert_iana_timezone_applies_daylight_saving_rules():
    capability = DateTimeCapability()

    summer = capability.call(
        "datetime.convert",
        dt_str="2026-07-01 12:00:00",
        from_tz="America/Chicago",
        to_tz="UTC",
    )
    winter = capability.call(
        "datetime.convert",
        dt_str="2026-01-01 12:00:00",
        from_tz="America/Chicago",
        to_tz="UTC",
    )

    assert summer.success is True
    assert summer.data["output"] == {
        "datetime": "2026-07-01 17:00:00",
        "timezone": "UTC",
    }
    assert summer.data["difference_hours"] == 5
    assert winter.success is True
    assert winter.data["output"] == {
        "datetime": "2026-01-01 18:00:00",
        "timezone": "UTC",
    }
    assert winter.data["difference_hours"] == 6


def test_convert_rejects_nonexistent_dst_wall_time():
    result = DateTimeCapability().call(
        "datetime.convert",
        dt_str="2026-03-08 02:30:00",
        from_tz="America/Chicago",
        to_tz="UTC",
    )

    assert result.success is False
    assert result.error["type"] == "ValueError"
    assert "Nonexistent local time" in result.error["message"]


def test_convert_requires_offset_for_ambiguous_dst_wall_time():
    capability = DateTimeCapability()
    ambiguous = capability.call(
        "datetime.convert",
        dt_str="2026-11-01 01:30:00",
        from_tz="America/Chicago",
        to_tz="UTC",
    )
    daylight = capability.call(
        "datetime.convert",
        dt_str="2026-11-01T01:30:00-05:00",
        from_tz="America/Chicago",
        to_tz="UTC",
    )
    standard = capability.call(
        "datetime.convert",
        dt_str="2026-11-01T01:30:00-06:00",
        from_tz="America/Chicago",
        to_tz="UTC",
    )

    assert ambiguous.success is False
    assert ambiguous.error["type"] == "ValueError"
    assert "Ambiguous local time" in ambiguous.error["message"]
    assert "explicit UTC offset" in ambiguous.error["message"]
    assert daylight.success is True
    assert daylight.data["output"]["datetime"] == "2026-11-01 06:30:00"
    assert standard.success is True
    assert standard.data["output"]["datetime"] == "2026-11-01 07:30:00"


def test_fixed_abbreviations_remain_backward_compatible():
    result = DateTimeCapability().call(
        "datetime.convert",
        dt_str="2026-07-01 12:00:00",
        from_tz="UTC",
        to_tz="CST",
    )

    assert result.success is True
    assert result.data["output"] == {
        "datetime": "2026-07-01 06:00:00",
        "timezone": "CST",
    }
    assert result.data["difference_hours"] == -6


def test_invalid_timezone_fails_with_actionable_error():
    result = DateTimeCapability().call("datetime.now", tz_name="Mars/Olympus_Mons")

    assert result.success is False
    assert result.error["type"] == "ValueError"
    assert "IANA timezone" in result.error["message"]


def test_zones_explains_iana_and_legacy_identifier_support():
    result = DateTimeCapability().call("datetime.zones")

    assert result.success is True
    assert result.data["iana_timezones_supported"] is True
    assert "CST" in result.data["timezones"]
    assert "America/Chicago" in result.data["iana_examples"]
