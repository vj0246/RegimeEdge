"""Track S: short near-month ATM NIFTY straddle, one cycle per monthly expiry (decisions.md section 5)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from osr.engine.costs import OPT_BUY, OPT_SELL
from osr.strategies.black76 import straddle_iv

MAX_STRIKE_GAP = 0.02
IV_MIN_DAYS = 7


@dataclass(frozen=True)
class Plan:
    """Cycle data aligned to trading dates; built once and reused for every gate."""

    dates: pd.DatetimeIndex
    rf: np.ndarray  # simple cash return over the gap ending at each date
    cycle: np.ndarray  # cycle whose entry..expiry covers the date, -1 if none
    entry: np.ndarray  # True on a tradable cycle's entry date
    mark: np.ndarray  # settlement value of call + put at the covering cycle's strike
    exit_px: np.ndarray  # buy-back price of call + put: close if the leg traded that day, else settlement
    forward: np.ndarray  # per cycle
    premium: np.ndarray  # per cycle, entry closes of call + put
    payoff: np.ndarray  # per cycle, |S_E - K|
    expiry_pos: np.ndarray  # per cycle, position of the expiry in dates
    cycles: pd.DataFrame  # per-cycle log


def monthly_expiries(panel: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(panel.loc[panel["instrument"] == "FUT", "expiry"].unique()))


def build_plan(panel: pd.DataFrame, rf: pd.Series) -> Plan:
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    pos = pd.Series(np.arange(len(dates)), index=dates)
    fut_settle = panel.loc[panel["instrument"] == "FUT"].set_index(["date", "expiry"])["settle"]
    expiries = monthly_expiries(panel)
    expiries = expiries[expiries.isin(dates)]
    opt = (panel.loc[(panel["instrument"] == "OPT") & panel["expiry"].isin(expiries)]
           .set_index(["expiry", "strike"]).sort_index())

    n = len(dates)
    cycle, entry = np.full(n, -1), np.zeros(n, dtype=bool)
    mark, exit_px = np.full(n, np.nan), np.full(n, np.nan)
    per_cycle, log = [], []
    for prev_exp, exp in zip(expiries[:-1], expiries[1:]):
        d = dates[dates > prev_exp][0]
        rec = {"entry": d, "expiry": exp}
        forward = fut_settle.get((d, exp), np.nan)
        chain = opt.loc[exp]
        chain = chain[(chain["date"] == d) & (chain["volume"] > 0)]
        both = chain.reset_index().pivot_table(index="strike", columns="opt_type", values="close").dropna()
        if np.isnan(forward) or both.empty or not {"CE", "PE"} <= set(both.columns):
            log.append({**rec, "status": "no liquid pair"})
            continue
        strike = both.index[np.argmin(np.abs(both.index.to_numpy() - forward))]  # ties: lower strike first
        if abs(strike - forward) / forward > MAX_STRIKE_GAP:
            log.append({**rec, "forward": forward, "strike": strike, "status": "strike too far"})
            continue
        span = dates[(dates >= d) & (dates < exp)]
        legs = opt.loc[(exp, strike)].pivot_table(index="date", columns="opt_type",
                                                  values=["close", "settle", "volume"])
        gaps = int((~span.isin(legs.index)).sum())
        legs = legs.reindex(span).ffill()
        settle, close, traded = legs["settle"], legs["close"], legs["volume"] > 0
        c = len(per_cycle)
        mark[pos[span]] = (settle["CE"] + settle["PE"]).to_numpy()
        exit_px[pos[span]] = (close.where(traded, settle)[["CE", "PE"]].sum(axis=1)).to_numpy()
        cycle[pos[d] : pos[exp] + 1] = c
        entry[pos[d]] = True
        s_e = fut_settle.get((exp, exp), np.nan)
        premium = both.loc[strike, "CE"] + both.loc[strike, "PE"]
        per_cycle.append((forward, premium, abs(s_e - strike), pos[exp]))
        log.append({**rec, "forward": forward, "strike": strike, "call": both.loc[strike, "CE"],
                    "put": both.loc[strike, "PE"], "settlement": s_e, "mark_gaps": gaps, "status": "ok"})
    fwd, prem, payoff, exp_pos = (np.array(v) for v in zip(*per_cycle))
    return Plan(dates, np.nan_to_num(rf.reindex(dates).to_numpy()), cycle, entry, mark, exit_px,
                fwd, prem, payoff, exp_pos.astype(int), pd.DataFrame(log))


def simulate(plan: Plan, gate: np.ndarray | None = None, lag: int = 1, half_spread: float = 0.01) -> pd.Series:
    """Daily account returns. gate[t] = 1 at the close of t means flat, acted on at the close of t+lag:
    no entry on a cycle's entry day, and an open straddle is bought back. No re-entry before the next cycle."""
    g = np.zeros(len(plan.dates)) if gate is None else np.nan_to_num(np.asarray(gate, dtype=float))
    keep, pay = 1 - OPT_SELL - half_spread, 1 + OPT_BUY + half_spread
    cash, units, held, v_prev = 1.0, 0.0, -1, 1.0
    out = np.empty(len(plan.dates))
    for t in range(len(plan.dates)):
        cash *= 1 + plan.rf[t]
        signal = g[t - lag] if t >= lag else 0.0
        if units:
            if t == plan.expiry_pos[held]:
                cash -= units * plan.payoff[held]
                units = 0.0
            elif signal == 1:
                cash -= units * plan.exit_px[t] * pay
                units = 0.0
        if plan.entry[t] and not units and signal != 1:
            held = plan.cycle[t]
            units = cash / plan.forward[held]
            cash += units * plan.premium[held] * keep
        v = cash - units * plan.mark[t] if units else cash
        out[t] = v / v_prev - 1
        v_prev = v
    return pd.Series(out, index=plan.dates, name="ret")


def atm_iv(panel: pd.DataFrame, auctions: pd.DataFrame) -> pd.Series:
    """Per date, Black-76 volatility of the ATM straddle of the first monthly expiry at least IV_MIN_DAYS
    calendar days away: strike nearest the future's settlement among strikes with both legs traded (closing
    prices), else among all strikes (settlement prices). Discounted at the latest 91-day yield."""
    expiries = monthly_expiries(panel)
    fut_settle = panel.loc[panel["instrument"] == "FUT"].set_index(["date", "expiry"])["settle"]
    opt = panel.loc[(panel["instrument"] == "OPT") & panel["expiry"].isin(expiries)]
    by_day = dict(tuple(opt.groupby(["date", "expiry"])))
    y = auctions.set_index("date")["yield_pct"].sort_index() / 100
    out = {}
    for d in sorted(panel["date"].unique()):
        later = expiries[expiries >= d + pd.Timedelta(days=IV_MIN_DAYS)]
        if later.empty or (d, later[0]) not in by_day:
            continue
        e = later[0]
        forward, rate = fut_settle.get((d, e), np.nan), y[:d].iloc[-1] if (y.index <= d).any() else np.nan
        chain = by_day[(d, e)]
        traded = chain[chain["volume"] > 0].pivot_table(index="strike", columns="opt_type", values="close").dropna()
        table = traded if {"CE", "PE"} <= set(traded.columns) and len(traded) else \
            chain.pivot_table(index="strike", columns="opt_type", values="settle").dropna()
        if np.isnan(forward) or np.isnan(rate) or table.empty or not {"CE", "PE"} <= set(table.columns):
            continue
        k = table.index[np.argmin(np.abs(table.index.to_numpy() - forward))]
        out[d] = straddle_iv(table.loc[k, "CE"] + table.loc[k, "PE"], forward, k, (e - d).days / 365, rate)
    return pd.Series(out, name="iv").sort_index()
