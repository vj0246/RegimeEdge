# Results and write-up (Phase 6)

Status: **partial.** This document reports only what the committed ledger supports: the summary metrics of the single sealed run (`run_id` 20261006T141900Z, 78 rows). The confirmatory tests, selection-bias statistics, stability analyses and ablations of `decisions.md` sections 10 to 12 are produced by `report.run` from the sealed daily return and gate files. Those files live in `data/results/sealed/20261006T141900Z/` on the machine that ran the study and are not in the repository, so none of those quantities are reported here. They are listed as missing in section 5 rather than estimated.

All numbers below are copied from `ledger.jsonl`. No number is a confirmatory result: nothing here carries a p-value, an interval or a Holm adjustment, so none of it supports a claim that one gate beats another.

## 1. Question and design

Does a causal regime gate (HMM, statistical jump model, BOCPD) improve a systematic short near-month ATM NIFTY straddle (Track S, primary) and a long Nifty 50 TRI position (Track T, replication), net of costs, beyond simple volatility gates (RV and IV thresholds)? The specification is `decisions.md` (locked v1.0, no amendments). The sealed period starts 2008-01-01. Headline settings: 1-day execution lag, 20-day majority smoothing on every gate, Track T futures-based costs, Track S half-spread of 1% of premium.

Power statement (from `docs/plan_v1.md` and `PLAN.md`, kept): the sealed sample is too short to detect Sharpe differences of the size gates typically produce, so a null result is the expected outcome and is not evidence that the gates are useless.

## 2. Track T: long Nifty 50 TRI (sealed period, lag 1, headline costs)

| Arm | Sharpe | Ann. return | Ann. vol | Max drawdown | CVaR 95% | Skew |
| --- | --- | --- | --- | --- | --- | --- |
| Ungated | 0.213 | 9.1% | 20.2% | -59.5% | -3.0% | 0.02 |
| RV threshold | 0.125 | 7.4% | 16.0% | -39.5% | -2.4% | -0.79 |
| HMM-2 | 0.036 | 6.0% | 15.2% | -31.7% | -2.3% | -0.58 |
| HMM-3 | 0.152 | 7.9% | 18.5% | -59.8% | -2.7% | 0.11 |
| JM | 0.313 | 10.5% | 14.7% | -38.3% | -2.2% | 0.65 |
| BOCPD | 0.047 | 6.2% | 15.6% | -39.3% | -2.4% | -1.01 |

Point estimates only:

- Every gate except HMM-3 cuts volatility, CVaR and maximum drawdown relative to ungated. HMM-3 leaves the drawdown essentially unchanged (-59.8%).
- Only JM has a higher Sharpe ratio than ungated (0.313 against 0.213). HMM-2, BOCPD and RV are below ungated. With a sample this short and a gap of 0.1 Sharpe units, the data cannot separate JM from ungated; the test is in section 5.
- JM is the only arm with positive skew.
- Costs do not drive the ranking. JM's Sharpe is 0.313, 0.301 and 0.282 under the headline, delivery-basket and stress tiers. HMM-2's is 0.036, 0.029 and 0.019.
- A 2-day lag lowers JM's Sharpe to 0.271 (headline costs); the others move by less than 0.03.

## 3. Track S: short ATM straddle (sealed period, lag 1)

MPPM (rho = 3, daily, annualised) is the primary metric. Higher is better.

| Arm | MPPM low spread | MPPM headline | MPPM high spread | Sharpe (headline) | Ann. return (headline) | Max drawdown (headline) | CVaR 95% | Skew |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ungated | -0.028 | -0.032 | -0.042 | -0.060 | 5.0% | -28.9% | -2.0% | -1.86 |
| RV threshold | -0.056 | -0.059 | -0.068 | -0.459 | 1.5% | -39.8% | -1.6% | -2.81 |
| IV threshold | -0.047 | -0.050 | -0.059 | -0.349 | 2.5% | -38.1% | -1.7% | -2.59 |
| HMM-2 | -0.037 | -0.040 | -0.049 | -0.292 | 3.4% | -33.4% | -1.6% | -1.78 |
| HMM-3 | -0.051 | -0.055 | -0.065 | -0.314 | 2.3% | -39.0% | -1.9% | -2.12 |
| JM | -0.017 | -0.019 | -0.026 | -0.096 | 5.4% | -28.6% | -1.4% | -3.63 |
| BOCPD | -0.053 | -0.056 | -0.065 | -0.433 | 1.8% | -39.1% | -1.6% | -2.97 |

Point estimates only:

- Every arm, including ungated, has negative MPPM. The ungated short straddle has a negative Sharpe ratio (-0.06) after costs at the headline spread, and every gate that earns a lower return than ungated also has a lower MPPM.
- JM first and ungated second at every spread tier and both lags (headline: -0.019 and -0.032 at lag 1, -0.022 and -0.032 at lag 2). HMM-2 and IV follow; at lag 1 RV, BOCPD and HMM-3 are last, at lag 2 the four non-JM gates are within 0.009 of each other.
- Gating reduces daily CVaR (from -2.0% to between -1.4% and -1.9%) but, for RV, IV, HMM-3 and BOCPD, increases maximum drawdown (-38% to -40% against -29% for ungated). A gate that is flat during high-volatility periods forgoes the premium collected after volatility spikes and still takes the loss on the cycles it enters, which is the pattern `PLAN.md` section 6 recorded as the expected outcome before data.
- JM has the lowest volatility and the best MPPM, and also the most negative skew (-3.63 against -1.86 ungated). Lower volatility with a fatter left tail is not an improvement in downside risk. This is the first thing the episode attribution (section 5) should explain.
- The cost sensitivity is modest. Moving from the 0.25% to the 3% half-spread lowers JM's MPPM from -0.017 to -0.026.

Comparison with the pre-registered expectation (`PLAN.md` section 6):

| Expectation | Ledger point estimates |
| --- | --- |
| Track T: risk reduction; Sharpe difference against the RV threshold not significant; JM turns over less than HMM | Risk reduction: holds for all gates except HMM-3 on drawdown. Sharpe test: not run. Turnover: not in the ledger. |
| Track S: gates cut drawdown and left-tail loss | CVaR falls for all gates. Maximum drawdown rises for four of six gates and skew is worse for five of six. Partly contradicted. |
| Track S: MPPM gain over ungated uncertain | No gate beats ungated on MPPM. Consistent. |
| No latent-state gate beats the IV threshold significantly | HMM-2 and JM sit above IV on MPPM; HMM-3 and BOCPD below. Significance: not tested. |

## 4. What the data may and may not be used to claim

- Claimable now: the descriptive statements in sections 2 and 3, labelled as sealed-period point estimates.
- Not claimable now: that JM beats ungated, RV or IV in either track; that any gate improves the straddle; that any difference survives multiple-testing correction. Those require the section 10 and 11 outputs.
- Even with those outputs, the pre-registered minimum detectable effect (`decisions.md` section 10) applies. A non-significant result must be read as "not detected at this power", not as "no effect".

## 5. Missing items required to finish the project

Each needs `data/results/sealed/20261006T141900Z/` (returns, gates, report output) or a rerun of `python -m osr.walkforward sealed`:

1. Section 10: eight Track S and six Track T tests (paired circular block bootstrap, circular-shift null, Holm, 95% intervals, minimum detectable effects).
2. Section 11: deflated Sharpe ratios with effective trial counts, and PBO by CSCV.
3. Section 12: synthetic delay against false-alarm curves (`python -m osr.validation synthetic`, about 40 minutes); rolling-refit stability (ARI, label flips, switches per year); known-event table; orthogonalised-HMM ablation; episode attribution; cost curves.
4. Figures: label stability, break-even cost curves, delay against false alarms, drawdown comparison.
5. Track T turnover and fraction of days flat, expected against realised regime durations.

## 6. Integrity notes on the sealed run (for the reader to weigh)

These come from the ledger and the repository state, and decisions.md section 13 makes them relevant:

- 77 of the 78 sealed rows record `dirty: true`. Section 13 says the sealed run refuses to run on a dirty tree. The cause is not determinable from the repository; the owner should confirm what was uncommitted at run time.
- The recorded `git_sha` 7728e18 is not an object in this repository's history, so the exact code that produced the sealed numbers cannot be checked out. The lock commit is b27772c. Source files changed after it (commits ce2a35c, b662337, 240ff26).
- The git tag `prereg-v1` exists neither locally nor on `origin`. `decisions.md` and `prereg.lock` carry the same hash today, so the specification itself is unchanged since the lock.
- The ledger's `data_manifest_sha256` (33cb4e42...) differs from the manifest hash in `prereg.lock` (edd207a5...). The lock normalises line endings and the ledger hashes raw bytes, so a CRLF checkout on Windows would explain this. It is unverified because the manifest is not in the repository.
- All sealed return paths point to a Windows OneDrive folder. Without those files a third party cannot reproduce any statistic here from the repository.

These do not change the ledger numbers above, but until the owner resolves them the sealed run should not be cited as satisfying section 13.
