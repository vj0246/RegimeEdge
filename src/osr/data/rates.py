"""91-day T-bill implicit yield at cut-off, per auction, stitched from official RBI tables.

Sources, in priority order for auction dates present in more than one:
  Handbook of Statistics (2004 listing) Table 205: Jan 1993 to Mar 2004, one sheet per fiscal year
  Handbook of Statistics 2010-11 Table 215: Apr 1998 to Jul 2011
  Handbook of Statistics 2025-26 Table 218: Jul 2025 to Jun 2026
  RBI Bulletin Table 26 via DBIE: Apr 2011 to Apr 2026
Overlaps between sources are checked in osr.data.validate.
"""

import io
import re
from datetime import datetime

import numpy as np
import pandas as pd

from osr.data.dates import parse_day_mon_year
from osr.data.http import fetch, make_session

HANDBOOK_PAGE = "https://rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook+of+Statistics+on+Indian+Economy"
DOCS = "https://rbidocs.rbi.org.in/rdocs/Publications/DOCs/"
SOURCES = {
    "hb2004_t205": DOCS + "56525.xls",
    "hb2011_t215": DOCS + "215T_HBS120911.xls",
    "hb2026_t218": DOCS + "218T_HBIE31072026D5086AE4949E4B9E80DEE6FC431C0761.XLSX",
    "dbie_bulletin_t26": "https://dbie.rbihub.in/government/treasury-bill-auctions",
}
EXCEL_MAGIC = (b"PK", b"\xd0\xcf\x11\xe0")


def parse_handbook_sheet(sheet: pd.DataFrame) -> pd.DataFrame:
    """One Handbook auction sheet -> (date, yield_pct); columns located by their header text."""
    text = sheet.astype(str)
    header = next(i for i in range(len(sheet)) if text.iloc[i].str.contains("date of auction", case=False).any())
    labels = text.iloc[header]
    date_col = labels[labels.str.contains("date of auction", case=False)].index[0]
    yield_col = labels[labels.str.contains("implicit yield", case=False)].index[0]
    body = sheet.iloc[header + 1 :]
    is_date = body[date_col].map(lambda v: isinstance(v, datetime))
    dates = pd.to_datetime(body.loc[is_date, date_col])
    yields = pd.to_numeric(body.loc[is_date, yield_col], errors="coerce")
    keep = yields.notna()
    return pd.DataFrame({"date": dates[keep].to_numpy(), "yield_pct": yields[keep].to_numpy()})


def parse_dbie(html: str) -> pd.DataFrame:
    """91-day rows of the auction records embedded in the DBIE page."""
    rows = re.findall(r'\{"tenor":"91-day","auction_date":"([^"]+)"[^{}]*?"implicit_yield":([0-9.]+)',
                      html.replace('\\"', '"'))
    return pd.DataFrame({
        "date": parse_day_mon_year(pd.Series([d for d, _ in rows], dtype=str)),
        "yield_pct": [float(y) for _, y in rows],
    })


def fetch_all() -> pd.DataFrame:
    """Every source's rows with a source column; duplicates across sources are kept."""
    session = make_session()
    fetch(session, "GET", HANDBOOK_PAGE)  # rbidocs serves files only with the site's cookies
    frames = []
    for name, url in SOURCES.items():
        resp = fetch(session, "GET", url, headers={"Referer": HANDBOOK_PAGE})
        if name.startswith("dbie"):
            df = parse_dbie(resp.text)
        else:
            if not resp.content.startswith(EXCEL_MAGIC):
                raise ValueError(f"{name}: expected an Excel file, got {resp.content[:40]!r}")
            sheets = pd.read_excel(io.BytesIO(resp.content), header=None, sheet_name=None)
            df = pd.concat([parse_handbook_sheet(s) for s in sheets.values()], ignore_index=True)
        if df.empty:
            raise ValueError(f"{name}: no auctions parsed")
        frames.append(df.assign(source=name))
    return pd.concat(frames, ignore_index=True)


def stitch(raw: pd.DataFrame) -> pd.DataFrame:
    """One yield per auction date; the first source in SOURCES order wins."""
    rank = raw["source"].map({name: i for i, name in enumerate(SOURCES)})
    out = raw.assign(rank=rank).sort_values(["date", "rank"]).drop_duplicates("date")
    return out.drop(columns="rank").reset_index(drop=True)


def daily_cash_return(auctions: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    """Simple interest (act/365) over each gap between trading days, at the latest yield auctioned on or
    before the previous trading day. NaN for the first date and before the first auction."""
    y = auctions.set_index("date")["yield_pct"].sort_index()
    prev = dates[:-1]
    rate = y.reindex(y.index.union(prev)).ffill().reindex(prev).to_numpy() / 100
    days = (dates[1:] - prev).days.to_numpy()
    return pd.Series(np.r_[np.nan, rate * days / 365], index=dates, name="rf")
