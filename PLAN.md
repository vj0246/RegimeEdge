# PLAN v2: Regime gating of NIFTY short volatility

Status: active plan as of 2026-09-12. Supersedes plan v1 (`docs/plan_v1.md`, the referee review). v1's literature assessment, power analysis and "accept a null" framing stand. This file records what was re-verified, what changed and why, and the phases. The binding study specification is `decisions.md` (pre-registration), locked before any sealed-period evaluation.

## 1. Question

- **Track S (primary):** does a causal regime gate improve a systematic short near-month ATM NIFTY straddle, net of costs, and does it beat simple observable-volatility gates?
- **Track T (secondary):** the same gates on a long Nifty 50 TRI position. This is a replication of Shu, Yu and Mulvey (2024) and Bulla et al. (2011) on Indian data, and it anchors the engine to a published template.

Claims are sized to power. The expected outcome is on record in section 6.

## 2. Re-verification of v1 (this session)

| v1 item | Result | Source |
| --- | --- | --- |
| Shu, Yu, Mulvey (2024): S&P 500 Sharpe 0.48 / 0.54 / 0.68, turnover 141% vs 44%, 10 bp one-way, 3,000-day window | Confirmed. Also DAX 0.30 / 0.35 / 0.44 and Nikkei 0.12 / 0.19 / 0.31. JM features: EWM downside deviation (halflife 10), EWM Sortino ratio (halflives 20 and 60). Parameters refit every 6 months on a rolling 3,000-day window; jump penalty re-selected monthly by 8-year validation Sharpe; HMM uses the Viterbi last state plus a k-day rolling-mean filter; 3-month T-bill as cash; signal at t applied from t+2 | arXiv 2402.05272v2 |
| Cederburg et al. (2020): 77/103 positive spanning alphas; 45/103 higher real-time Sharpe; 7 vs 7 significant | Confirmed with a correction: 45/103 refers to real-time combination portfolios, and the 7 vs 7 counts CER differences, not Sharpe. Direct comparisons split 53 vs 50 | JFE 138(1), full text |
| Bulla et al. (2011): volatility -41%, excess return 18.5 to 201.6 bp, after costs | Confirmed | MPRA 21154 abstract |
| Nifty 50 TRI starts mid-1999 | Confirmed: first value 30 Jun 1999 | niftyindices API |
| Futures STT 0.02% on sell | **Stale.** Union Budget 2026, effective 1 Apr 2026: futures 0.05% on sell; options 0.15% of premium on sell; 0.15% of intrinsic value on exercised options (paid by the buyer). NSE transaction charges: futures 0.00183%, options 0.03553% of premium; delivery 0.00307% (v1 correct) | ICICI Direct, HDFC Bank, Zerodha charges page |
| Free NSE daily data | Confirmed for F&O: `nsearchives.nseindia.com`, old bhavcopy format 12 Jun 2000 to 5 Jul 2024, UDiFF format from Jan 2024 (overlap) to date. On sampled days (2004-06-15, 2008-01-15) near-month NIFTY options within about 8% of the forward traded; next-month ATM options did not trade on either day | probes this session |
| 91-day T-bill via RBI DBIE | DBIE covers Apr 2011 to Apr 2026 only. Full series (1993-01-08 to 2026-06-24, 1,734 auctions) stitched from RBI Handbook Tables 205 (2004 listing), 215 (2010-11) and 218 (2025-26) plus DBIE; overlapping sources agree to 0.0005 pp | RBI Handbook archive, DBIE |
| Power arithmetic | Re-derived and correct. Binomial episode counts by normal approximation are 37 (one-sided) and 47 (two-sided) against v1's 39 and 49; immaterial | own arithmetic |

## 3. Changes from v1 and why

1. **Base strategy (owner decision, 2026-09-12).** Track S is a short near-month ATM NIFTY straddle, entered the day after each monthly expiry, held to expiry, cash-collateralised at 1x notional. The TRI gate becomes the replication track. Why: the project targets index options; the regime signal (NIFTY returns) is no longer the traded P&L (implied minus realised variance), which answers v1 section 8's same-series objection; short-volatility losses concentrate in volatility expansions, so the prior for gating is stronger than for an equity gate. Cost: end-of-day data without quotes, and the natural baseline becomes implied volatility, an observable forward-looking variable, which raises the bar for a latent state.
2. **Costs.** The current (1 Apr 2026) charge schedule is applied to the whole history as the headline, because it is what a strategy deployed today pays. Sensitivity is a cost curve: 0 to 100 bp one-way for Track T, 0 to 5% of premium per leg for Track S. Option half-spreads are an explicit assumption in three tiers, because bhavcopy carries no bid or ask.
3. **PBO by CSCV on walk-forward returns instead of CPCV refits.** Combinatorially symmetric cross-validation needs only the matrix of out-of-sample trial returns. Refitting regime models on combinatorial folds trains on future blocks, which tells the model which regimes exist (for example the 2020 variance level); purging and embargo do not remove that, and it multiplies compute.
4. **Random-gate null by circular shift.** Rotating the realised gate path preserves time in market, turnover and the run-length distribution exactly, and destroys only the alignment with returns. The stationary block bootstrap stays as a secondary null.
5. **Synthetic ground truth from three data-generating processes.** A 2-state Gaussian HMM fitted to NIFTY favours the HMM because it is correctly specified. Add a 2-state hidden semi-Markov model with Student-t emissions (duration and tail misspecification) and a GARCH(1,1)-t with no regimes. The GARCH null measures how often each detector reports regimes that are only volatility clustering, which is v1's central confound.
6. **Primary metric per track.** Track S uses the manipulation-proof performance measure (MPPM, rho = 3; Goetzmann, Ingersoll, Spiegel and Welch 2007 [recalled]) because selling options inflates the Sharpe ratio through negative skew; the Sharpe difference is secondary. Track T keeps the Ledoit-Wolf Sharpe difference for comparability with Shu et al.
7. **Integrity enforced in code.** Every engine run appends to an append-only ledger (config hash, git SHA, data manifest hash, family, period, return-series file). The sealed run refuses to start unless `decisions.md` matches the SHA-256 in `prereg.lock`, committed under git tag `prereg-v1`.
8. **Development versus sealed data.** Engineering, debugging and detector validation on real data use dates up to 2007-12-31 (straddle cycles 2004 to 2007) plus synthetic data. From 2008-01-01 the sample is sealed until the single pre-registered run. The known-event table moves into the sealed run.
9. **Small, fixed trial budget.** Per track: candidates HMM-2 (headline), JM (co-headline), HMM-3 and BOCPD (secondary); baselines realised-volatility threshold (both tracks) and ATM implied-volatility threshold (Track S); ungated. Hyperparameters are fixed from the literature or chosen inside the walk-forward loop by a fixed rule. No grid search outside the loop.
10. **Rolling 3,000-day windows, monthly refits aligned to expiries.** Follows the Shu et al. template. One detector run produces the gate path used by both tracks.
11. **Weekly options excluded.** Short history and rule changes in the contract itself (SEBI one-weekly-expiry rule from late 2024; NSE expiry day moved to Tuesday from 1 Sep 2025). Monthly contracts only.
12. **Uniform 20-day majority filter on every gate (owner decision 2026-09-13).** Development data showed raw gates switching 12 to 31 times a year (HMM-2 21.7, IV 30.8, BOCPD 12.1). Shu et al.'s k = 20 is applied to all gates so costs do not decide the comparison. Trade-off on record: about 10 days of lag, and on NIFTY-fitted synthetic data the filtered HMM-2 misses 52% to 83% of short stressed episodes.
13. **JM penalty grid {1, 2, ..., 500}, log-spaced (owner decision 2026-09-13).** The earlier grid's floor (5) was selected on every development day.

## 4. Phases

Each phase ends with a check that must pass before the next starts.

**Phase 0: pre-registration.** Draft `decisions.md`; owner review; lock (`prereg.lock`, tag `prereg-v1`). Check: a second reader can predict every table of the final report from `decisions.md` alone.

**Phase 1: data (outcome-blind, may run before the lock).** NIFTY index futures and options rows from F&O bhavcopy, 2004 to present; NIFTY 50 price index from the earliest available date; Nifty 50 TRI from 30 Jun 1999; 91-day T-bill yields. Checks, over the ranges the study uses (F&O from 2004; earlier F&O files only supply expiry dates; TRI from 2001): (a) the F&O trading calendar matches index dates, every mismatch listed; (b) at each monthly expiry the expiring future's settlement price equals the index close within 0.05 points; (c) TRI divided by the price index never falls by more than rounding noise (1e-4 a day), and its annual growth sits in a plausible dividend-yield band; (d) put-call parity on the ATM near-month pair, C - P against the discounted (F - K), holds within tolerance on at least 95% of days; (e) no gap longer than 5 trading days; (f) T-bill sources agree where they overlap; (g) exactly one monthly expiry per month from 2001, each a trading day.

**Phase 2: detectors and causality harness.** One interface: fit on a window, emit the gate state at each t from data up to t only. HMM-2 and HMM-3 (hmmlearn, multiple EM starts, variance-ordered labels, forward filter), JM (jumpmodels, Shu et al. features, online inference), BOCPD (normal-inverse-gamma conjugate), and the two threshold baselines. Checks: a perturbation test for every detector (changing data after t leaves every output at or before t unchanged); a label-consistency test across refits.

**Phase 3: detector validation (synthetic and development data only).** Delay against false-alarm curves under the three DGPs; rolling-refit adjusted Rand index and label-flip rate; expected against realised durations. Checks: curves are monotone in the threshold; ARI uses aligned dates only.

**Phase 4: strategies and evaluation engine.** Straddle cycle engine with daily marks, TRI gate, cost schedules, cash leg, walk-forward runner, nulls, statistics (Ledoit-Wolf bootstrap, MPPM, DSR with clustered effective N, CSCV PBO), ledger. Checks on development data only: the ungated TRI arm reproduces the index return exactly; three straddle cycles, including May 2004, reconcile by hand; random gates give a DSR percentile near 50 in simulation.

**Phase 5: the sealed run.** One execution of everything in `decisions.md`. Check: every reported number traces to a ledger row.

**Phase 6: write-up.** Claims sized to the power statement; null results reported as such.

## 5. What carries the portfolio value (v1 section 9, kept)

Power statement in the abstract; rolling-refit label stability (the most original figure); break-even cost curves; the incremental-information ablation (gate on the HMM probability orthogonalised to lagged realised volatility); episode attribution; synthetic delay against false-alarm curves, now including the no-regime null.

## 6. Expected outcome, on record before data

- Track T: as v1. Risk reduction likely significant; Sharpe difference against the volatility threshold not significant; JM turns over less than HMM.
- Track S: gates cut drawdown and left-tail loss. The MPPM gain over ungated is uncertain, because the variance risk premium tends to be largest just after volatility spikes, which is when a gate is flat (inference). No latent-state gate beats the implied-volatility threshold significantly.

## 7. Status

Phases 0 to 4 complete on development data (2026-09-13): Phase 1 checks (a) to (g) pass; detectors pass look-ahead tests; synthetic curves are monotone; the TRI arm reproduces the index, three straddle cycles reconcile by hand, and the circular-shift null is calibrated at sealed length. Pre-registration locked under git tag `prereg-v1`. Next: Phase 5, the single sealed run.
