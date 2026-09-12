"""niftyindices.com daily history: price index (OHLC) and total return index."""

import json
import time
from datetime import date

import pandas as pd

from osr.config import settings
from osr.data.dates import format_day_mon_year, parse_day_mon_year
from osr.data.http import fetch, make_session

BASE = "https://www.niftyindices.com"
HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE}/reports/historical-data",
    "Origin": BASE,
}
PRICE = "getHistoricaldatatabletoString"
TRI = "getTotalReturnIndexString"
FIELDS = {
    PRICE: ("HistoricalDate", {"OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close"}),
    TRI: ("Date", {"TotalReturnsIndex": "tri", "NTR_Value": "ntr"}),
}


def cinfo(name: str, start: date, end: date) -> str:
    return (
        f"{{'name':'{name}','startDate':'{format_day_mon_year(start)}',"
        f"'endDate':'{format_day_mon_year(end)}','indexName':'{name}'}}"
    )


def parse_response(text: str) -> list[dict]:
    """Payload is a JSON list or {"d": "<JSON list>"}; an HTML page means the request was rejected."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"niftyindices returned non-JSON: {text[:80]!r}") from None
    return json.loads(payload["d"]) if isinstance(payload, dict) else payload


def to_frame(rows: list[dict], method: str) -> pd.DataFrame:
    date_col, values = FIELDS[method]
    if not rows:
        return pd.DataFrame(columns=["date", *values.values()])
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"date": parse_day_mon_year(df[date_col])})
    for src, dst in values.items():
        out[dst] = pd.to_numeric(df[src].where(df[src] != "-"))
    return out


def fetch_history(name: str, method: str, start: date, end: date) -> pd.DataFrame:
    """One request per calendar year (the site's own UI caps ranges at a year)."""
    session = make_session()
    frames = []
    for year in range(start.year, end.year + 1):
        a, b = max(start, date(year, 1, 1)), min(end, date(year, 12, 31))
        resp = fetch(session, "POST", f"{BASE}/BackPage/{method}", timeout=180, headers=HEADERS,
                     data=json.dumps({"cinfo": cinfo(name, a, b)}))
        frame = to_frame(parse_response(resp.text), method)
        if not frame.empty:
            frames.append(frame)
        time.sleep(settings.request_pause_s)
    df = pd.concat(frames, ignore_index=True)
    return df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
