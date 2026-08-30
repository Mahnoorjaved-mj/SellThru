"""Pakistan holiday calendar features.

Eid al-Fitr and Eid al-Adha follow the lunar Hijri calendar and shift ~11
days earlier each Gregorian year, so they can't be computed with a fixed
rule — this is a lookup table of publicly published dates. Independence Day
(Aug 14) and the Ramadan window are included too. A per-organization custom
holiday list (Section 8 of the build brief) is a Settings-page feature that
doesn't exist yet — this table is the global default until then.
"""
from __future__ import annotations

from datetime import date, timedelta

# (start, end) inclusive date ranges, approximate public holiday windows.
_HOLIDAY_RANGES: list[tuple[date, date, str]] = [
    # Ramadan (fasting month — informative feature, not a public holiday itself)
    (date(2023, 3, 23), date(2023, 4, 20), "ramadan"),
    (date(2024, 3, 11), date(2024, 4, 9), "ramadan"),
    (date(2025, 3, 1), date(2025, 3, 29), "ramadan"),
    (date(2026, 2, 18), date(2026, 3, 19), "ramadan"),
    (date(2027, 2, 8), date(2027, 3, 8), "ramadan"),
    # Eid al-Fitr
    (date(2023, 4, 21), date(2023, 4, 23), "eid_fitr"),
    (date(2024, 4, 10), date(2024, 4, 12), "eid_fitr"),
    (date(2025, 3, 30), date(2025, 4, 1), "eid_fitr"),
    (date(2026, 3, 20), date(2026, 3, 22), "eid_fitr"),
    (date(2027, 3, 9), date(2027, 3, 11), "eid_fitr"),
    # Eid al-Adha
    (date(2023, 6, 28), date(2023, 7, 1), "eid_adha"),
    (date(2024, 6, 16), date(2024, 6, 19), "eid_adha"),
    (date(2025, 6, 6), date(2025, 6, 9), "eid_adha"),
    (date(2026, 5, 27), date(2026, 5, 30), "eid_adha"),
    (date(2027, 5, 16), date(2027, 5, 19), "eid_adha"),
]


def holiday_flags(d: date) -> dict:
    """Return {is_holiday, is_ramadan} for a given date."""
    is_holiday = d.month == 8 and d.day == 14  # Independence Day
    is_ramadan = False
    for start, end, kind in _HOLIDAY_RANGES:
        if start <= d <= end:
            if kind in ("eid_fitr", "eid_adha"):
                is_holiday = True
            elif kind == "ramadan":
                is_ramadan = True
    return {"is_holiday": is_holiday, "is_ramadan": is_ramadan}
