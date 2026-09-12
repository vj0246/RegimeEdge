# decisions.md: pre-registration

Status: **LOCKED v1.0, 2026-09-13. Binding.** `prereg.lock` records the SHA-256 of this file and of `data/manifest.json`, and the commit is tagged `prereg-v1`. From here, changes go only into section 16 (Amendments) with date and reason, and the sealed run reports under both the original and the amended specification.

## 1. Tracks

- **Track S (primary):** short near-month ATM NIFTY straddle (section 5).
- **Track T (secondary, replication of Shu, Yu and Mulvey 2024):** long Nifty 50 TRI (section 6).

Both tracks use the same gate paths (one detector run).

## 2. Periods

- Detector input starts 1995-11-03 (NIFTY 50 base date). Earlier values are back-calculated and not daily.
- Development period: dates up to 2007-12-31. Any analysis is allowed.
- Sealed period: 2008-01-01 to the sample end, defined as the last NIFTY monthly expiry on or before 2026-08-31. Strategy returns in the sealed period are computed once, in the sealed run.
- A straddle cycle belongs to the period that contains its entry date.

## 3. Data (hashes fixed in `data/manifest.json` at lock)

| Series | Source | Use |
| --- | --- | --- |
| NIFTY 50 price index, daily close | niftyindices.com `/BackPage/getHistoricaldatatabletoString` | detector input |
| Nifty 50 TRI, daily | niftyindices.com `/BackPage/getTotalReturnIndexString`, from 1999-06-30 | Track T |
| NIFTY index futures and options, daily | NSE F&O bhavcopy, old format to 2024-07-05, UDiFF from 2024-07-08; NIFTY rows only; from 2004-01-01 | Track S, IV baseline, calendar |
| 91-day T-bill implicit yield at cut-off, per auction | RBI Handbook of Statistics Table 205 (2004 listing: Jan 1993 to Jun 2004), Table 215 (2010-11: Apr 1998 to Jul 2011), Table 218 (2025-26: Jul 2025 to Jun 2026), RBI Bulletin Table 26 via DBIE (Apr 2011 to Apr 2026). Overlaps agree to 0.0005 pp on 375 auctions. Last auction 2026-06-24, carried forward to the sample end | cash leg, excess returns, JM penalty validation |

- Trading calendar: dates with an F&O bhavcopy from 2004; index dates before 2004.
- Monthly expiries: expiry dates of NIFTY index futures contracts, relabelled to the last day on which each month's futures traded (old-format files keep the scheduled date when a holiday moved expiry, e.g. 2008-12-25 to 2008-12-24; Sep 2025 carries both the Thursday and the new Tuesday label). Monthly option contracts take the same relabelling; weekly options are not used.
- Cash accrual: simple interest at the latest 91-day yield auctioned on or before the previous trading day, act/365 over the calendar days between consecutive trading days.

## 4. Gate signal, timing, refits

- Gate state g_t in {0 = invested, 1 = flat}, computed from data up to the close of day t.
- Execution lag: a change in g_t takes effect at the close of t+1 (headline); at the close of t+2 (sensitivity).
- Detector input: r_t = ln(P_t / P_{t-1}) of the NIFTY 50 price index. JM features use excess returns x_t = r_t - rf_t.
- Refits: at the close of every NIFTY monthly expiry, on a rolling window of the last min(3,000, available) trading days. No detector emits a signal before 1,500 days are available. Between refits parameters are frozen and inference runs daily.
- Threshold baselines recompute their thresholds at each refit from the same window (IV baseline: section 8.6).

## 5. Track S: short ATM straddle

- Cycle m runs from entry day d_m (first trading day after monthly expiry E_{m-1}) to expiry E_m.
- Forward F = settlement price on d_m of the NIFTY future expiring E_m.
- Strike K_m = the listed strike nearest F among strikes whose E_m call and put both traded (volume > 0) on d_m; ties go to the lower strike. If no such strike lies within 2% of F, the cycle is skipped in every arm.
- Entry: sell n = V / F units of the K_m call and put at their closing prices, where V is the account value before the trade (1x notional, fully cash-collateralised).
- Account: cash earns the cash rate. V_t = cash_t - n (C_t + P_t), legs marked at daily settlement prices. On E_m the position settles at n |S_E - K_m|, where S_E is the settlement price on E_m of the future expiring E_m (the options' final settlement price).
- Daily return r_t = V_t / V_{t-1} - 1.
- Gated arm: enter on d_m only if the gate signal from the close of E_{m-1} is 0 (with the 2-day lag, the signal from the day before). While holding, a signal of 1 at the close of t means both legs are bought back at the close of t+1, at the closing price if the leg traded that day, else the settlement price. No re-entry before d_{m+1}.

## 6. Track T: long TRI

- Position held over day u: 1 - g_{u-2} (headline lag), i.e. a signal at the close of t moves the position at the close of t+1.
- Daily return: position x TRI return + (1 - position) x cash return, less switching costs on days the position changes.
- Ungated arm: buy and hold the TRI, no costs.

## 7. Costs (1 Apr 2026 schedule applied to the whole history)

Track S, per leg per trade, as a fraction of premium:

| Trade | Statutory and exchange charges | Half-spread tiers: low / headline / high |
| --- | --- | --- |
| Sell (entry) | STT 0.15% + NSE 0.03553% + SEBI 0.0001% + GST 18% on (NSE + SEBI) = 0.19204% | 0.25% / 1.0% / 3.0% |
| Buy (gate exit) | stamp 0.003% + NSE 0.03553% + SEBI 0.0001% + GST 18% on (NSE + SEBI) = 0.04504% | 0.25% / 1.0% / 3.0% |
| Expiry settlement | none for the seller (exercise STT is paid by the buyer) | none |

Brokerage (Rs 20 per order) is excluded: under 1 bp a year of notional for accounts of Rs 1 crore or more.

Track T, per one-way switch, as a fraction of notional:

| Tier | Buy | Sell |
| --- | --- | --- |
| Headline: index futures | stamp 0.002% + NSE 0.00183% + SEBI + GST + 1 bp slippage = 0.0143% | STT 0.05% + NSE 0.00183% + SEBI + GST + 1 bp slippage = 0.0623% |
| Delivery basket | STT 0.1% + stamp 0.015% + NSE 0.00307% + SEBI + GST + 1 bp = 0.1287% | STT 0.1% + NSE 0.00307% + SEBI + GST + 1 bp = 0.1137% |
| Stress | 0.25% | 0.25% |

Cost curves: Track T one-way cost 0 to 100 bp in 5 bp steps; Track S half-spread 0% to 5% of premium in 0.25% steps.

## 8. Gates

"Stressed" means flat (g = 1). Labels are ordered at every refit. Every gate in 8.1 to 8.6 is smoothed as in 8.8 before it is traded or compared.

- **8.1 HMM-2 (headline).** hmmlearn `GaussianHMM(n_components=2, covariance_type="diag", n_iter=1000, tol=1e-6)` on 100 r_t over the window; 10 fits with `random_state` 0 to 9, keep the highest log-likelihood; stressed = the highest-variance state. Inference: forward filter from the window start through t with frozen parameters. g_t = 1 iff P(stressed | data to t) > 0.5.
- **8.2 HMM-3 (secondary).** As 8.1 with 3 states; stressed = the highest-variance state only.
- **8.3 JM (co-headline).** jumpmodels `JumpModel(n_components=2, cont=False)`. Features (Shu et al. 2024, Table 2), computed causally on the full history from x_t: DD10 = sqrt(EWM_hl10(x^2 1{x<0})); Sortino20 = EWM_hl20(x) / sqrt(EWM_hl20(x^2 1{x<0})); Sortino60 likewise with halflife 60. Standardised with the window mean and standard deviation. Parameters refit at every sixth monthly expiry (January and July cycles). Jump penalty chosen at every monthly expiry from {1, 2, 5, 10, 20, 50, 100, 200, 500} (owner decision 2026-09-13, after the development period selected the floor of the earlier grid on every day): the value whose Track T gate (headline cost tier, 1-day lag) had the highest Sharpe ratio over the trailing 8 years, or over all available history if shorter with a minimum of 3 years; every candidate's path is computed causally and smoothed as in 8.8 before it is scored. States labelled by cumulative excess return over the training window; the lower one is stressed (owner decision 2026-09-13, kept although a short window can hand the label to the calm state; flips are reported under section 12). Inference: the online DP state at t with frozen parameters (last state of the DP over the window ending at t).
- **8.4 BOCPD (secondary).** Adams and MacKay (2007): Gaussian observations with unknown mean and variance, normal-inverse-gamma prior (mu0 = 0, kappa0 = 1, alpha0 = 2, beta0 = window variance of r, so the prior mean of the variance equals the window variance), constant hazard 1/250, run length truncated at 1,000. Output: s_t = posterior mean of the variance averaged over run lengths (the predictive variance does not exist when alpha = 1, hence alpha0 = 2). g_t = 1 iff s_t exceeds the 80th percentile of s over the window. Re-run over the window at each refit, then online.
- **8.5 RV threshold (baseline, both tracks).** v_t = sqrt(252 x mean of r^2 over t-20..t). g_t = 1 iff v_t exceeds the 80th percentile of v over the window.
- **8.6 IV threshold (baseline, Track S).** IV_t = Black-76 volatility equating model and market value of the ATM straddle of the first monthly expiry at least 7 calendar days after t (weekly expiries ignored; strike nearest the future's settlement price among strikes with both legs traded, closing prices; else settlement prices), maturity in calendar days / 365, discounted at the latest 91-day yield. g_t = 1 iff IV_t exceeds the 80th percentile of IV over all dates from 2004-01-01 to the refit date; no signal before 250 days of IV history.
- **8.7 Ungated.** g = 0 always.
- **8.8 Smoothing (owner decision 2026-09-13).** Every gate passes through the 20-day majority filter of Shu, Yu and Mulvey (2024): g_t = 1 only when more than half of the last 20 raw states were 1; no signal before 20 raw states exist. Adopted because the raw gates switched 12 to 31 times a year in the development period (HMM-2 21.7, IV 30.8, BOCPD 12.1), which would make trading costs, not information, decide the comparisons. Applied uniformly so that no gate is advantaged. Known cost: about 10 days of lag; on NIFTY-fitted synthetic data the filtered HMM-2 misses 52% to 83% of short stressed episodes.

## 9. Metrics

- Track S primary: MPPM with rho = 3 on daily returns, MPPM = [1 / ((1 - rho) dt)] ln( mean_t [ ((1 + r_t) / (1 + rf_t))^(1 - rho) ] ), dt = 1/252 (Goetzmann, Ingersoll, Spiegel and Welch 2007).
- Track T primary: annualised Sharpe ratio of daily excess returns.
- Secondary, both tracks: the other track's primary metric, annualised return and volatility, maximum drawdown, daily CVaR at 95%, skewness, fraction of days flat, gate switches per year, annual turnover, expected against realised regime durations.

## 10. Confirmatory tests

For detector D in {HMM-2, JM}, with difference dM = M(D) - M(comparator) in the track's primary metric, sealed period only:

- Track S: comparators ungated, RV threshold, IV threshold, plus the circular-shift null of D: 8 tests.
- Track T: comparators ungated, RV threshold, plus the circular-shift null of D: 6 tests.

Inference:

- Differences: paired circular block bootstrap of daily returns, block length by Politis and White (2004) on the difference series, 10,000 resamples, seed 20260912. Two-sided p-value: share of resamples with |dM* - dM| >= |dM|. Track T's Sharpe difference is studentised with HAC standard errors (Ledoit and Wolf 2008).
- Circular shift: 999 rotations of D's sealed-period gate path by offsets drawn uniformly from [252, T - 252], strategy re-run on each rotated gate. One-sided p = (1 + #{M_null >= M_obs}) / 1000.
- Holm-Bonferroni within each track, familywise 5%.
- Reported with each test: 95% bootstrap interval and the minimum detectable effect 2.8 sqrt(2 (1 - rho_hat) / years) in Sharpe units, rho_hat being the realised correlation of gated and ungated daily returns.

## 11. Selection-bias statistics

- Families: Track S = {ungated, RV, IV, HMM-2, HMM-3, JM, BOCPD}; Track T = {ungated, RV, HMM-2, HMM-3, JM, BOCPD}. Sensitivities (2-day lag, cost tiers, cost curves) are not trials.
- Deflated Sharpe ratio (Bailey and Lopez de Prado 2014) for HMM-2 and JM, with N = effective number of trials from correlation clustering of the family's sealed-period returns (Lopez de Prado and Lewis 2019); raw N also reported.
- PBO by CSCV (Bailey, Borwein, Lopez de Prado and Zhu 2017), 16 contiguous blocks, on the family's sealed-period daily return matrix, statistic = the track's primary metric. If PBO > 0.5 the report makes no claim that the best family member is best.

## 12. Descriptive analyses (no confirmatory claims)

- **Synthetic validation.** DGPs fitted to development-period returns: (a) 2-state Gaussian HMM; (b) 2-state hidden semi-Markov model, Student-t emissions with 4 degrees of freedom, negative-binomial durations; (c) GARCH(1,1) with Student-t innovations and no regimes. 100 paths of 6,000 days per DGP; detectors refit every 250 days on a rolling 3,000-day window (the DGPs are stationary). HMM-2 at probability cuts 0.3 to 0.9, RV and BOCPD at window percentiles 70 to 95, JM at fixed penalties 10, 50 and 200; HMM-3 is left out for compute (about 9 s per fit). Metrics: detection delay (trading days from an episode's start to the first stressed signal inside it), miss rate, false alarms per calm year; under (c), switches per year and time flat.
- **Rolling-refit stability (sealed run).** Adjusted Rand index and label-flip rate between consecutive refits on overlapping dates; switches per year.
- **Known events (sealed run).** Dates fixed now, from memory [recalled], each moved to the next trading day if needed: 2008-01-21, 2008-09-15, 2008-10-24, 2009-05-18 (upside), 2011-08-08, 2013-08-16, 2015-08-24, 2016-11-09, 2018-09-21, 2020-02-24, 2020-03-23, 2022-02-24, 2024-06-04. Development period: 2004-05-17, 2006-05-22. Per event and detector: stressed signal within 20 trading days (yes or no) and delay in trading days.
- **Ablations.** Orthogonalised HMM gate: at each refit regress logit P(stressed) on log v over the window, gate on the residual above the quantile that matches HMM-2's in-window flat fraction, smoothed as in 8.8. Episode attribution: sealed-period stressed runs of HMM-2, merged across gaps under 21 days, each run's contribution to dM against ungated. Cost curves, 2-day lag, cost tiers.

## 13. Integrity

- Ledger: `ledger.jsonl`, append-only, committed. One row per engine run: UTC timestamp, git SHA and dirty flag, canonical config JSON and its SHA-256, data manifest SHA-256, track, family member, period, lag, cost tier, path of the daily return file, summary metrics. Rows are never deleted or edited.
- Lock: `prereg.lock` holds the SHA-256 of this file and of `data/manifest.json`; committed and tagged `prereg-v1`. The sealed-run command refuses to run if either hash differs or the working tree is dirty.
- Stopping rule: one sealed run. A bug found afterwards is fixed, the run repeated, and both runs reported with a description of the fix.

## 14. Declared deviations from Shu, Yu and Mulvey (2024)

- HMM gates on the filtered probability, not the Viterbi last state, and refits monthly, not daily. The 20-day filter is applied to every gate, not to the HMM only.
- JM jump-penalty grid is stated here; the paper does not report its grid.
- Cash is the Indian 91-day T-bill; costs are the Indian 2026 schedule, not 10 bp.

## 15. Known limitations

- Bhavcopy has no quotes: half-spreads are assumed; untraded legs are marked at exchange settlement prices.
- 1x-notional collateral is not a margin model; returns are per unit of notional.
- The 2026 cost schedule is applied to 2004 to 2026.
- Index history before 1995-11-03 is not used.
- The NSE archive has no F&O file for 2013-10-09 or 2021-03-30 (index traded both days); Track S skips those dates and carries marks forward. F&O archive gaps in 2000 fall before the first refit.

## 16. Amendments

None.
