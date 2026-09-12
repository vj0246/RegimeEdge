"""NSE F&O bhavcopy: download, keep NIFTY index futures and options, normalise both file formats."""

import io
import logging
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from osr.config import settings
from osr.data.dates import MONTHS, parse_day_mon_year
from osr.data.http import fetch, make_session

log = logging.getLogger(__name__)

BASE = "https://nsearchives.nseindia.com/content"
UDIFF_FROM = date(2024, 7, 8)  # old format discontinued after 2024-07-05 (NSE circular 62424)
SYMBOL = "NIFTY"

COLUMNS = ["date", "instrument", "expiry", "strike", "opt_type", "open", "high", "low",
           "close", "settle", "volume", "oi", "underlying"]
NUMERIC = ["strike", "open", "high", "low", "close", "settle", "volume", "oi", "underlying"]
OLD = {"TIMESTAMP": "date", "INSTRUMENT": "instrument", "EXPIRY_DT": "expiry", "STRIKE_PR": "strike",
       "OPTION_TYP": "opt_type", "OPTIONTYPE": "opt_type", "OPEN": "open", "HIGH": "high", "LOW": "low",
       "CLOSE": "close", "SETTLE_PR": "settle", "CONTRACTS": "volume", "OPEN_INT": "oi"}
UDIFF = {"TradDt": "date", "FinInstrmTp": "instrument", "FininstrmActlXpryDt": "expiry", "StrkPric": "strike",
         "OptnTp": "opt_type", "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close",
         "SttlmPric": "settle", "TtlTradgVol": "volume", "OpnIntrst": "oi", "UndrlygPric": "underlying"}
INSTRUMENT = {"FUTIDX": "FUT", "OPTIDX": "OPT", "IDF": "FUT", "IDO": "OPT"}


def bhavcopy_url(d: date) -> str:
    if d < UDIFF_FROM:
        mon = MONTHS[d.month - 1]
        return f"{BASE}/historical/DERIVATIVES/{d.year}/{mon}/fo{d.day:02d}{mon}{d.year}bhav.csv.zip"
    return f"{BASE}/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"


def read_zip_csv(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        (name,) = [n for n in z.namelist() if n.lower().endswith(".csv")]
        lines = z.read(name).decode("utf-8", errors="replace").splitlines()
    return pd.read_csv(io.StringIO("\n".join(repair_lines(lines))), dtype=str)


def repair_lines(lines: list[str]) -> list[str]:
    """Drop blank lines; split lines on which an old-format file glued several records (seen 2002-03-19).
    Old-format rows end with a comma, so a glued line holds an exact multiple of the header's commas."""
    width = lines[0].count(",")
    out = [lines[0]]
    for line in lines[1:]:
        commas = line.count(",")
        if commas == width:
            out.append(line)
        elif lines[0].endswith(",") and commas and commas % width == 0:
            fields = line.split(",")
            out += [",".join(fields[i : i + width]) + "," for i in range(0, commas, width)]
        elif line.strip():
            raise ValueError(f"unparseable bhavcopy line: {line[:80]!r}")
    return out


def filter_nifty(raw: pd.DataFrame) -> pd.DataFrame:
    """NIFTY index futures and options rows, original columns, whitespace stripped."""
    df = raw.rename(columns=str.strip)
    df = df.loc[:, [c for c in df.columns if not c.startswith("Unnamed")]]
    df = df.apply(lambda col: col.str.strip())
    if "INSTRUMENT" in df.columns:
        keep = df["INSTRUMENT"].isin(["FUTIDX", "OPTIDX"]) & (df["SYMBOL"] == SYMBOL)
    else:
        keep = df["FinInstrmTp"].isin(["IDF", "IDO"]) & (df["TckrSymb"] == SYMBOL)
    return df.loc[keep].reset_index(drop=True)


def normalize(rows: pd.DataFrame, trade_date: date) -> pd.DataFrame:
    """Map either bhavcopy format onto COLUMNS; raise if the rows belong to another date.

    Some 2002-2003 files list their records two or three times, once with an all-zero copy of a future
    (2003-10-01); one row per contract is kept, the one with the highest volume."""
    if rows.empty:
        return pd.DataFrame(columns=COLUMNS)
    old = "INSTRUMENT" in rows.columns
    df = rows.rename(columns=OLD if old else UDIFF)
    if old:
        df["date"] = parse_day_mon_year(df["date"])
        df["expiry"] = parse_day_mon_year(df["expiry"])
        df["underlying"] = float("nan")
    else:
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
        df["expiry"] = pd.to_datetime(df["expiry"], format="%Y-%m-%d")
    if (df["date"] != pd.Timestamp(trade_date)).any():
        raise ValueError(f"bhavcopy for {trade_date} holds rows dated {sorted(df['date'].unique())}")
    df["instrument"] = df["instrument"].map(INSTRUMENT)
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c])
    fut = df["instrument"] == "FUT"
    df.loc[fut, "strike"] = float("nan")
    df.loc[fut, "opt_type"] = None
    contract = ["instrument", "expiry", "strike", "opt_type"]
    df = df.sort_values("volume", ascending=False, kind="stable").drop_duplicates(contract).sort_index()
    return df[COLUMNS].reset_index(drop=True)


def raw_path(root: Path, d: date) -> Path:
    return root / "raw" / "fo" / str(d.year) / f"{d:%Y%m%d}.csv.gz"


def missing_marker(root: Path, d: date) -> Path:
    return root / "raw" / "fo" / str(d.year) / f"{d:%Y%m%d}.404"


def download_range(start: date, end: date, root: Path) -> tuple[int, int]:
    """Fetch every calendar day (special weekend sessions exist); a 404 means no session that day.

    Idempotent: days with a saved file or a 404 marker are skipped. Returns (saved, absent).
    """
    session = make_session()
    saved = absent = 0
    unpublished_after = date.today() - timedelta(days=3)  # recent 404s may just be unpublished files
    for d in pd.date_range(start, end).date:
        path, marker = raw_path(root, d), missing_marker(root, d)
        if path.exists() or marker.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        resp = fetch(session, "GET", bhavcopy_url(d), missing_ok=True)
        if resp is None:
            absent += 1
            if d < unpublished_after:
                marker.touch()
        else:
            tmp = path.with_suffix(".tmp")
            filter_nifty(read_zip_csv(resp.content)).to_csv(tmp, index=False, compression="gzip")
            tmp.replace(path)
            saved += 1
            if saved % 250 == 0:
                log.info("saved %d files, last %s", saved, d)
        time.sleep(settings.request_pause_s)
    return saved, absent


def align_monthly_expiries(panel: pd.DataFrame) -> pd.DataFrame:
    """Relabel monthly contracts with the day they actually expired.

    Old-format files keep a contract's scheduled expiry when a holiday moves it (2008-12-25 traded last on
    2008-12-24), and some months carry two labels (Sep 2025: Thursday to Tuesday switch). Every label used by a
    futures contract is mapped to the last date on which its month's futures traded; weekly option labels,
    which no future carries, are untouched. Months whose latest label is after the panel's last date are open.
    """
    fut = panel[panel["instrument"] == "FUT"]
    last = fut.groupby("expiry")["date"].max()
    month = last.index.to_period("M")
    closed = pd.Series(last.index, index=last.index).groupby(month).transform("max") <= panel["date"].max()
    actual = last.groupby(month).transform("max")
    mapping = actual[closed.to_numpy()]
    out = panel.copy()
    out["expiry"] = out["expiry"].map(mapping).fillna(out["expiry"])
    key = ["date", "instrument", "expiry", "strike", "opt_type"]
    if out.duplicated(key).any():
        raise ValueError(f"relabelling made duplicate contracts: {out[out.duplicated(key, keep=False)].head()}")
    return out


def build_panel(root: Path) -> pd.DataFrame:
    frames = []
    for path in sorted((root / "raw" / "fo").glob("*/*.csv.gz")):
        d = date(int(path.name[:4]), int(path.name[4:6]), int(path.name[6:8]))
        frame = normalize(pd.read_csv(path, dtype=str), d)
        if not frame.empty:
            frames.append(frame)
    return align_monthly_expiries(pd.concat(frames, ignore_index=True))
