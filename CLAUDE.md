# Options Strategy Regime (osr)

Pre-registered, power-limited study: does a causal regime gate (HMM, statistical jump model, BOCPD) improve a systematic short near-month ATM NIFTY straddle (primary track) and a long Nifty 50 TRI position (replication track), net of costs, beyond simple volatility gates? Plan: `PLAN.md`. Binding spec: `decisions.md` (locked via `prereg.lock` + git tag `prereg-v1`). Original review: `docs/plan_v1.md`.

## Stack
Python 3.12 (uv-managed `.venv`), numpy 2.5, pandas 3.0, scipy, scikit-learn 1.9, statsmodels 0.15, hmmlearn 0.3.3, jumpmodels 0.1.1, arch 8.0, pyarrow, pydantic 2 + pydantic-settings, pytest.

## Commands
- Setup: `uv venv .venv --python 3.12 && uv pip install --python .venv -e ".[dev]"`
- Tests: `.venv/Scripts/python -m pytest -q`
- Data: `.venv/Scripts/python -m osr.data.fetch {fo,panel,indices,rates}` (fo is ~8k requests, run in background; idempotent), then `-m osr.data.validate` (checks a-f) and `-m osr.data.manifest`
- Detector validation: `-m osr.validation {synthetic,stability}` (synthetic uses a process pool, ~40 min)
- Runs: `-m osr.walkforward dev` (inputs truncated at 2007-12-31); `-m osr.walkforward sealed` only after `-m osr.lock create` + commit + tag `prereg-v1`

## Layout
- `src/osr/data/` downloaders (NSE F&O bhavcopy, niftyindices, RBI T-bills), validation checks, manifest
- `src/osr/detectors/` causal gates behind `fit`/`stressed` (+ `score`, `insample_stressed`); `gate_path` does refits
- `src/osr/strategies/` Track S straddle engine (`build_plan`/`simulate`, ATM IV), Track T TRI gate, Black-76
- `src/osr/engine/` costs (2026 schedule), stats (MPPM, LW test, circular shift, DSR, PBO), append-only ledger
- `src/osr/{validation,walkforward,report,lock,synthetic}.py` Phase 3 validation, runner, sealed stats, prereg lock, DGPs
- `tests/` pytest; a look-ahead perturbation test is mandatory for every detector
- `data/` gitignored: NIFTY-filtered raw rows + processed parquet
- `docs/plan_v1.md` verbatim v1 plan

## Env vars (names only)
`OSR_DATA_DIR` (default `./data`), `OSR_USER_AGENT` (optional override), `OSR_REQUEST_PAUSE_S` (default 0.3)
Kite (in `.env`, never read by Claude: deny rules in `~/.claude/settings.json` and `.claude/settings.json`): `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN` (written daily by `-m osr.live.session login`), `KITE_LIVE_TRADING` (default false), `KITE_MAX_LOTS` (default 1)

## Gotchas
- Sealed period: never evaluate a strategy on dates >= 2008-01-01 before the prereg lock. Dev work uses <= 2007-12-31 plus synthetic data.
- Gate only on filtered/online states, never smoothed or full-sample Viterbi paths. Signal at close t trades at close t+1.
- NSE F&O bhavcopy: old format `fo{DD}{MON}{YYYY}bhav.csv.zip` through 2024-07-05, UDiFF `BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip` from 2024-01 (overlap) on. Host `nsearchives.nseindia.com` (archives.nseindia.com returns 403). Needs a Mozilla User-Agent. Column `OPTION_TYP` is `OPTIONTYPE` in some 2005-2006 files.
- niftyindices: endpoints are `/BackPage/<method>` (old `Backpage.aspx/` paths return HTML). TRI response is a plain JSON list.
- rbidocs.rbi.org.in serves XLS/XLSX only with cookies from rbi.org.in (GET the publications page first, send it as Referer); otherwise it returns HTML. Older Handbook editions list via ASP.NET postback (`hdnYear`).
- Kite (`src/osr/live/`, separate from the locked study): run `session login`/`recorder` in your own terminal; tests use a fake client and `_env_file=None`. Quote API allows 1 request/s. Since 1 Apr 2026 API order placement needs a static IP registered in the Kite developer console, and market orders need market protection.
- STT changed 1 Apr 2026 (futures 0.05% sell, options 0.15% of premium on sell). Cost model applies the current schedule to the full history.
- pandas 3: copy-on-write and the string dtype are defaults.
- Repo lives in OneDrive: `.venv/` and `data/` sync unless excluded.
