# DateTime capability

The built-in `datetime` capability provides evidence from the system clock for
current time, timezone conversion, and date arithmetic. Version 1.1 accepts
IANA timezone identifiers and applies the timezone database's historical and
daylight-saving rules.

## Identifiers

Use an IANA identifier when local civil-time rules matter:

```text
America/Chicago
Europe/London
Asia/Tokyo
```

The legacy fixed abbreviations remain compatible: `UTC`, `GMT`, `EST`, `CST`,
`MST`, `PST`, `CET`, `EET`, `IST`, `JST`, `AEST`, and `NZST`. They retain their
original fixed offsets and intentionally do not change for daylight saving.
For example, `CST` is always UTC-6, whereas `America/Chicago` is UTC-6 in
winter and UTC-5 in summer.

IdentityOS depends on Python's first-party `tzdata` package so IANA data is
available on systems that do not provide an operating-system timezone
database. Unknown identifiers return structured failure evidence rather than
falling back to a guessed offset.

## Conversion behavior

A naive `dt_str` is interpreted as a wall time in `from_tz`. Most inputs can use
the existing format:

```python
runtime.capability_registry.call(
    identity_id,
    "datetime.convert",
    dt_str="2026-07-01 12:00:00",
    from_tz="America/Chicago",
    to_tz="UTC",
)
```

Some daylight-saving transitions create wall times that either never occurred
or occurred twice. The capability rejects nonexistent times. It also rejects
an ambiguous naive time instead of silently choosing an occurrence. Include an
ISO-8601 UTC offset to disambiguate a repeated time:

```text
2026-11-01T01:30:00-05:00
2026-11-01T01:30:00-06:00
```

This is backward compatible with 1.0 callers: skill names, parameters, result
fields, defaults, and fixed-abbreviation behavior are unchanged. IANA support
is additive, so the capability uses a minor version bump to 1.1.0.
