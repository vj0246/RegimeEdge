"""Locale-independent parsing of the day-month-year strings used by NSE and niftyindices."""

from datetime import date

import pandas as pd

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTHS)}


def parse_day_mon_year(s: pd.Series) -> pd.Series:
    """'26-Jul-2001', '24-OCT-2008', '14-May-12' (one 2012 NSE file) or '03 Jul 1990' -> datetime64."""
    parts = s.str.upper().str.split(r"[- ]", regex=True, expand=True)
    year = parts[2].astype(int)
    return pd.to_datetime(
        pd.DataFrame(
            {"year": year.where(year >= 100, year + 2000), "month": parts[1].map(MONTH_NUM), "day": parts[0].astype(int)}
        )
    )


def format_day_mon_year(d: date) -> str:
    """date -> '01-Jan-1999', the format niftyindices expects."""
    return f"{d.day:02d}-{MONTHS[d.month - 1].title()}-{d.year}"
