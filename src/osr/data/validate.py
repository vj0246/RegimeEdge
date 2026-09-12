"""Phase 1 data checks (PLAN.md section 4). Prints a report; exits 1 if any check fails.

  python -m osr.data.validate
"""

import sys

import numpy as np
import pandas as pd

from osr.config import settings

FO_START = pd.Timestamp("2004-01-01")  # options study period; earlier F&O files only supply expiry dates
EXPIRY_START = pd.Timestamp("2001-01-01")  # first detector refits
TRI_START = pd.Timestamp("2001-01-01")  # first TRI use (JM penalty validation)
SETTLE_TOL = 0.05  # index points
PARITY_TOL = 0.0025  # |C - P - (F - K)| / F
PARITY_PASS_SHARE = 0.95
MAX_MISSING_WEEKDAYS = 4
DIVIDEND_BAND = (0.003, 0.03)  # yearly growth of TRI / price
TRI_FALL_TOL = 1e-4  # daily fall of TRI / price above rounding noise (observed 2002-2009 noise <= 5.5e-5)
KNOWN_FO_GAPS = {pd.Timestamp("2013-10-09"), pd.Timestamp("2021-03-30")}  # absent from both NSE archive formats
TBILL_TOL = 0.005  # percentage points between sources reporting the same auction
MAX_AUCTION_GAP_DAYS = 31


def calendar_mismatches(fo_dates: pd.Series, index_dates: pd.Series) -> tuple[list, list]:
    """Dates in one calendar but not the other, over the F&O date range."""
    lo, hi = fo_dates.min(), fo_dates.max()
    fo, ix = set(fo_dates), set(index_dates[(index_dates >= lo) & (index_dates <= hi)])
    return sorted(fo - ix), sorted(ix - fo)


def expiry_settlement_gaps(panel: pd.DataFrame, close: pd.Series) -> pd.DataFrame:
    """Settlement price of each expiring future on its expiry day against the index close."""
    fut = panel.loc[(panel["instrument"] == "FUT") & (panel["date"] == panel["expiry"]), ["date", "settle"]]
    out = fut.merge(close.rename("close"), left_on="date", right_index=True, how="left")
    out["gap"] = (out["settle"] - out["close"]).abs()
    return out.reset_index(drop=True)


def tri_ratio_problems(price: pd.Series, tri: pd.Series) -> tuple[pd.Series, pd.Series]:
    """(days where TRI / price falls, full calendar years whose ratio growth leaves the dividend band)."""
    ratio = (tri / price).dropna()
    falls = ratio[ratio.pct_change() < -TRI_FALL_TOL]
    yearly = ratio.groupby(ratio.index.year).agg(["first", "last", "count"])
    yearly = yearly[yearly["count"] >= 200]
    growth = yearly["last"] / yearly["first"] - 1
    return falls, growth[(growth < DIVIDEND_BAND[0]) | (growth > DIVIDEND_BAND[1])]


def parity_deviation(panel: pd.DataFrame) -> pd.Series:
    """Per date, |C - P - (F - K)| / F for the traded near-month monthly pair nearest the forward."""
    fut = panel.loc[(panel["instrument"] == "FUT") & (panel["expiry"] > panel["date"]), ["date", "expiry", "settle"]]
    fut = fut.sort_values("expiry").groupby("date").head(1).rename(columns={"settle": "F"})
    opt = panel.loc[(panel["instrument"] == "OPT") & (panel["volume"] > 0)]
    wide = (opt.pivot_table(index=["date", "expiry", "strike"], columns="opt_type", values="close")
            .dropna().reset_index())
    m = wide.merge(fut, on=["date", "expiry"])
    m["dist"] = (m["strike"] - m["F"]).abs()
    atm = m.sort_values(["date", "dist", "strike"]).groupby("date").head(1)
    dev = ((atm["CE"] - atm["PE"]) - (atm["F"] - atm["strike"])).abs() / atm["F"]
    return pd.Series(dev.to_numpy(), index=pd.DatetimeIndex(atm["date"]), name="parity_dev").sort_index()


def expiry_calendar_problems(expiries: pd.DatetimeIndex, trading: pd.DatetimeIndex, start: pd.Timestamp,
                             end: pd.Timestamp) -> list[str]:
    """Months in [start, end] without exactly one monthly expiry, or whose expiry is not a trading day."""
    exp = expiries[(expiries >= start) & (expiries <= end)]
    counts = pd.Series(1, index=exp).groupby(exp.to_period("M")).size()
    months = pd.period_range(start, end, freq="M")
    bad = [f"{m}: {counts.get(m, 0)} expiries" for m in months if counts.get(m, 0) != 1]
    return bad + [f"{e.date()}: not a trading day" for e in exp if e not in trading]


def tbill_conflicts(raw: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    """(auction dates reported more than once, those whose yields differ by more than TBILL_TOL)."""
    spread = raw.groupby("date")["yield_pct"].agg(["min", "max", "count"])
    multi = spread[spread["count"] > 1]
    return len(multi), multi[multi["max"] - multi["min"] > TBILL_TOL]


def long_gaps(dates: pd.Series) -> pd.DataFrame:
    """Consecutive trading dates with more than MAX_MISSING_WEEKDAYS weekdays between them."""
    d = pd.Series(sorted(dates.unique()))
    missing = np.busday_count(d[:-1].to_numpy().astype("datetime64[D]"), d[1:].to_numpy().astype("datetime64[D]")) - 1
    gaps = pd.DataFrame({"from": d[:-1].to_numpy(), "to": d[1:].to_numpy(), "missing_weekdays": missing})
    return gaps[gaps["missing_weekdays"] > MAX_MISSING_WEEKDAYS].reset_index(drop=True)


def main() -> None:
    p = settings.data_dir / "processed"
    panel = pd.read_parquet(p / "nifty_fo.parquet")
    price = pd.read_parquet(p / "nifty50_price.parquet").set_index("date")["close"]
    tri = pd.read_parquet(p / "nifty50_tri.parquet").set_index("date")["tri"]
    all_dates = pd.Series(panel["date"].unique())
    fo_dates = all_dates[all_dates >= FO_START]
    failed = []

    expiries = pd.DatetimeIndex(sorted(panel.loc[panel["instrument"] == "FUT", "expiry"].unique()))
    closed = expiries[expiries <= all_dates.max()]
    problems = expiry_calendar_problems(expiries, pd.DatetimeIndex(all_dates), EXPIRY_START, closed.max())
    print(f"(g) expiry calendar {EXPIRY_START.date()} to {closed.max().date()}: {len(problems)} problems {problems[:10]}")
    if problems:
        failed.append("g")

    early_only_ix = calendar_mismatches(all_dates[all_dates < FO_START], pd.Series(price.index))[1]
    print(f"    (pre-{FO_START.year} F&O archive gaps, expiry dates only: {len(early_only_ix)} index-only dates)")
    only_fo, only_ix = calendar_mismatches(fo_dates, pd.Series(price.index))
    unexplained = [d for d in only_ix if d not in KNOWN_FO_GAPS]
    print(f"(a) calendar: {len(only_fo)} F&O-only dates, {len(only_ix)} index-only dates "
          f"({len(only_ix) - len(unexplained)} documented archive gaps)")
    for label, ds in (("F&O only", only_fo), ("index only, unexplained", unexplained)):
        if ds:
            print(f"    {label}: {[str(x.date()) for x in ds[:20]]}{' ...' if len(ds) > 20 else ''}")
    if only_fo or unexplained:
        failed.append("a")

    gaps = expiry_settlement_gaps(panel[panel["date"] >= FO_START], price)
    bad = gaps[~(gaps["gap"] <= SETTLE_TOL)]
    print(f"(b) expiry settlement: {len(gaps)} expiries, {len(bad)} with |settle - close| > {SETTLE_TOL} or no close")
    if len(bad):
        print(bad.head(20).to_string(index=False))
        failed.append("b")

    falls, off_band = tri_ratio_problems(price[price.index >= TRI_START], tri[tri.index >= TRI_START])
    print(f"(c) TRI/price: {len(falls)} falls, {len(off_band)} full years outside {DIVIDEND_BAND}")
    if len(falls) or len(off_band):
        print(falls.head(10).to_string(), off_band.to_string(), sep="\n")
        failed.append("c")

    dev = parity_deviation(panel[panel["date"] >= FO_START])
    share = (dev <= PARITY_TOL).mean()
    print(f"(d) put-call parity: {len(dev)} dates, {share:.1%} within {PARITY_TOL:.2%} of F "
          f"(median {dev.median():.3%}, p99 {dev.quantile(0.99):.3%})")
    if share < PARITY_PASS_SHARE:
        failed.append("d")

    lg = long_gaps(fo_dates)
    print(f"(e) gaps: {len(lg)} gaps of more than {MAX_MISSING_WEEKDAYS} missing weekdays")
    if len(lg):
        print(lg.to_string(index=False))
        failed.append("e")

    raw = pd.read_parquet(p / "tbill91_raw.parquet")
    auctions = pd.read_parquet(p / "tbill91.parquet")
    n_multi, conflicts = tbill_conflicts(raw)
    gap = auctions["date"].diff().dt.days
    print(f"(f) T-bill: {len(auctions)} auctions {auctions['date'].min().date()} to {auctions['date'].max().date()}; "
          f"{n_multi} dates in several sources, {len(conflicts)} differ by > {TBILL_TOL} pp; "
          f"longest gap {gap.max():.0f} days")
    if len(conflicts) or gap.max() > MAX_AUCTION_GAP_DAYS:
        print(conflicts.to_string())
        failed.append("f")

    print("FAILED: " + ", ".join(failed) if failed else "ALL CHECKS PASSED")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
