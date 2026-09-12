> Verbatim copy of plan v1 as pasted by the project owner on 2026-09-12. Only line breaks were restored; no words changed. Superseded by PLAN.md.

# Regime gating study: referee review, evidence, and plan

Prepared 12 September 2026. Evidence base: literature verification run this session (two verification agents, one cut off part way but its file survived; one agent failed on a spend limit and its scope was re run by hand), plus a referee versus advocate debate run on the verified findings. Every citation carries one of three labels. **[verified]** means located this session at a URL and the relevant content read. **[exists]** means the bibliographic record was located but the specific claim attributed to it was not read this session. **[recalled]** means from memory, not checked this session; treat the details as possibly wrong. Sentences marked "inference" are mine, not the literature's.

Hyphens are kept inside verbatim paper titles because altering a title is a misquote.

---

## 0. Verdict in six sentences

The design is above the median of the published regime timing literature on inference discipline, because most of that literature reports no significance test at all. Its central weakness is not any protocol choice but the unit of information: the study will have roughly 6,500 daily observations but only 10 to 30 regime episodes, and every honest standard error is set by the episodes. Plausible effect sizes from the closest published templates (a Sharpe gain of 0.1 to 0.3, or 20 to 200 basis points a year) sit inside one standard error of the Sharpe difference at the sample length available. The heuristic baseline as specified cannot separate "the latent state carries information" from "cutting exposure when volatility clusters helps", which is the thing the literature already knows and also knows fails in real time. The known date break test is a floor test, not a validation, because the only breaks known in daily equity data are the large volatility events every detector finds with a two to four week lag. The study is worth doing only if it is pre registered as a power limited replication with a null result accepted as the likely outcome, and if the extensions in section 9 are what carry the portfolio value.

---

## 1. What the published evidence says (negative results first)

**The forecasting literature is negative and the mechanism is understood.** Dacco and Satchell (1999) [verified] show analytically that "even minimal misclassification when predicting which regime will occur can eliminate advantages from knowing the correct model specification", and that nonlinear models with good in sample fit "are usually outperformed by random walks or random walks with drift when used for out-of-sample forecasting". Bessec and Bouabdallah (2005) [verified] confirm by Monte Carlo across a wide range of specifications that "the gain in prediction remains small" and decompose the error: "the main source of error is due to the misclassification of future regimes". Engel (1994) [verified] finds for 18 exchange rates that the Markov model "does not generate superior forecasts to a random walk or the forward rate". Stillwagon and Sullivan (2020) [verified] show that adding regimes does not help: the model "is still unable to outperform a random walk". Clements and Krolzig (1998) [exists] is the standard macro reference that neither MS AR nor threshold AR reliably beats a linear AR out of sample; I could not read the conclusions this session. Hansen (1992) [verified] is the deepest cut: his bounded likelihood ratio test "is unable to reject the hypothesis of an AR(4) in favour of the Markov switching model" on Hamilton's own GNP data, so the founding empirical example of the field does not survive a correct test. Guidolin's 2011 survey [verified] concedes the point: "it remains odd to entertain the possibility that a regime switching model may be useful in certain applications (e.g., portfolio choice, risk management) even though it does not really help that much with forecasting the switching dynamics".

**The positive trading evidence is thinner than it looks.** Sorted by inference quality:

Ang and Bekaert (2002) [verified] is in sample with "no costs for short-selling or rebalancing". Ang and Bekaert (2004) [verified] claims an out of sample win for global equity portfolios but is pre cost, and the value "was added when an investor switched between domestic cash, bonds, and equity", meaning the gain is moving to cash in high volatility states. Guidolin and Timmermann (2007) [verified] claim out of sample economic value; costs are not stated in the abstract. Kritzman, Page and Turkington (2012) [verified] report "backtests", not a real time test, with no cost statement. Nystrup, Hansen, Madsen and Lindström (2015) [verified] is a framing paper. None of these corrects for multiple testing.

Bulla, Mergner, Bulla, Sesboüé and Chesneau (2011) [verified] is the closest published template for your study: 40 years of daily data on US, Japanese and German indices, an HMM gate that cuts exposure in the high volatility state, out of sample, after transaction costs. Result: volatility down about 41 percent, but excess annual return of only "18.5 to 201.6 basis points", with no significance test on the difference. Nystrup, Madsen and Lindström (2018) [verified] use 10 basis point proportional costs, a one day implementation delay, and report Sharpe 0.56 to 0.63 versus 0.30 for buy and hold on MSCI World 1997 to 2015, with point estimates only and no confidence intervals. Shu, Yu and Mulvey (2024) [verified] is the most careful recent one: 10 basis point one way costs, S&P 500 out of sample 1990 to 2023, buy and hold Sharpe 0.48, HMM gate 0.54, statistical jump model gate 0.68. The HMM turned over 141 percent a year against 44 percent for the jump model and produced about two regime shifts a year against under one. No multiple testing correction; the training window was 3,000 days.

So the direct answer to your question: yes, the favourable evidence comes overwhelmingly from studies without a cost model, without real time estimation, or without correction for multiple testing, and the three studies that do include costs show gains measured in tens of basis points for the HMM specifically, with the gain concentrated in risk reduction rather than return. The one study that tests a plain HMM head to head against a modern alternative has the HMM losing.

**The most damaging analogue is volatility management.** Moreira and Muir (2017) [verified] show that scaling exposure by inverse lagged realized variance produces large alphas in spanning regressions. Cederburg, O'Doherty, Wang and Yan (2020) [verified] then implement it in real time with recursive estimation across 103 strategies: 77 of 103 have positive spanning alphas, but in real time only 45 of 103 have higher Sharpe ratios, and significant improvements (7) exactly equal significant declines (7). Their conclusion: "the trading strategies implied by the spanning regressions are not implementable in real time" because parameters "estimated from past data often fail to provide a reliable indication of the future performance". An HMM gate on a return series is, mechanically, a smoothed volatility timer (inference: the high variance state of a Gaussian HMM fitted to returns is identified by variance, so the filtered probability is a nonlinear function of recent squared returns). Cederburg et al. is therefore the paper your referee will cite, and it says the mechanism you are relying on does not survive real time estimation for most strategies.

**Indian market.** No peer reviewed paper was found that tests HMM or Markov switching gated trading on NSE daily data out of sample, net of costs, with multiple testing correction. Ahmad and Bandi (2011) [verified, MPRA working paper] and Chaudhuri and Kumar (2015) [verified] only identify regimes in sample. Parikakis and Merika (2009) [verified] is a warning: Markov switching forecasts that worked for EUR/USD "lose power" on Latin American currencies and "higher volatility... seems to be a critical factor for this failure". The gap is real; the gap is also a hint that the result may be null.

---

## 2. Regime identification methods compared

Notation: T is the number of daily observations available (about 6,500 for Nifty 50 total return index from mid 1999 [recalled: TRI start date, verify on niftyindices.com]; about 7,700 for the price index from November 1995 [recalled]).

| Method | Foundational reference | Data needed | Stability on short samples | Runs without future information? | Published criticism |
|---|---|---|---|---|---|
| Markov switching AR (MS AR) | Hamilton (1989) Econometrica [verified]; Kim (1994) J. Econometrics [verified]; Krolzig (1997) [recalled] | One series; hundreds of observations minimum; regimes must be well separated in mean or variance | Poor below a few hundred observations: Pouzo, Psaradakis and Sola (2022) Econometrica [verified via arXiv] report ML sampling distributions "deviate from the symmetric and mesokurtic distributions predicted by large-sample theory when T <= 200", transition probabilities worst, and bias under misspecification persists at T = 3,200. Psaradakis and Sola (1998) [exists] is the original finite sample study; content not readable this session | Yes via the Hamilton filter (filtered probabilities use data to t). Smoothed probabilities use the full sample and must never gate a trade | Hansen (1992) [verified] and Garcia (1998) [verified]: the likelihood ratio test for the number of regimes has a nonstandard null; naive tests over reject. Carrasco, Hu and Ploberger (2014) [verified] and Qu and Zhuo (2021) [verified] supply valid tests, implemented in the R package MSTest. Dacco and Satchell (1999), Bessec and Bouabdallah (2005): forecast failure through misclassification |
| Gaussian HMM on returns | Rydén, Teräsvirta and Åsbrink (1998) J. Applied Econometrics [verified]; Zucchini, MacDonald and Langrock (2016) [recalled] | One or several series; Rydén et al. used subseries of about 1,700 daily observations and still found parameters "sometimes vary considerably from one subseries to the next" | EM is sensitive to initial values and has local optima: Bulla and Berzel (2008) [verified]; multiple starts required. Nystrup, Lindström and Madsen (2020) [verified]: misestimation "leads to unrealistically rapid switching dynamics" | Yes with the forward filter, subject to the same filtered versus smoothed rule; the label of each state is not identified across refits (Celeux, Hurn and Robert 2000 [verified]; Jasra, Holmes and Stephens 2005 [exists]), so a relabelling rule such as sorting by variance is mandatory | Geometric duration assumption is wrong for financial states: Bulla and Bulla (2006) [exists] propose hidden semi Markov models. Information criteria favour too many states: Pohle, Langrock, van Beest and Schmidt (2017) [verified]. Rydén et al. [recalled detail]: HMM cannot reproduce the slow decay of absolute return autocorrelation |
| Online change point detection (BOCPD, CUSUM) | Adams and MacKay (2007) arXiv [verified]; Fearnhead and Liu (2007) JRSS B [verified]; Page (1954) CUSUM [recalled]; offline: Killick, Fearnhead and Eckley (2012) PELT [verified], Truong, Oudre and Vayatis (2020) review [verified] | One series; needs a hazard rate prior and a conjugate segment model | Depends entirely on hazard and penalty hyperparameters, which are not identified from a short sample | Yes by construction; BOCPD is the only method here designed as online | van den Burg and Williams (2020) [verified, arXiv only]: on 37 annotated real series with default hyperparameters "no method performs significantly better than the zero method" (predict no change points); BOCPD wins only with oracle tuning, which "is not indicative of real-world performance". Adams and MacKay's Dow Jones example has "no explicit validation against ground truth" |
| Clustering on rolling features, statistical jump models | Bemporad, Breschi, Piga and Boyd (2018) Automatica [verified]; Nystrup, Kolm and Lindström (2020) JFDS [verified]; Aydınhan, Kolm, Mulvey and Shu (2024) Annals of OR [verified]; Kritzman and Li (2010) turbulence [verified]; Horvath, Issa and Muguruza (2021) Wasserstein k means [verified, arXiv only]; Botte and Bao (2021) Two Sigma note [verified, not peer reviewed] | Rolling feature vectors (realized volatility, downside deviation, returns at several horizons); a jump penalty that controls switching frequency | Jump estimator is "less sensitive to initialization" and the greedy online classifier yields "significantly more persistent" states than a correctly specified MLE (Nystrup et al. 2020, both papers [verified]). Claimed to work "when regimes are imbalanced and historical data is limited" (Aydınhan et al. 2024, abstract) | Original jump model is offline (dynamic programming over the full window); the greedy online version of Nystrup, Kolm and Lindström is causal. Plain k means or GMM on rolling features is causal only if features are backward looking and the model is refit inside the loop; Botte and Bao state their GMM "is not predictive" | Jump penalty is a tuning parameter with no data driven identification; results in Shu, Yu and Mulvey depend on it. Wasserstein clustering and Two Sigma note report no costed strategy |
| Threshold and smooth transition (TAR, STAR) | Tong (1990) [recalled]; Teräsvirta (1994) JASA [recalled]; Hansen (1996) Econometrica [verified]; Hansen (2000) Econometrica [verified]; van Dijk, Teräsvirta and Franses (2002) survey [recalled] | One series plus an observed transition variable (lagged return, lagged volatility) | Threshold estimate is super consistent but the linearity test needs Hansen (1996) simulated p values; small samples give wide threshold confidence intervals | Yes, and this is the strongest property: the regime is a deterministic function of an observed lagged variable, so there is no latent state uncertainty and no filtered versus smoothed distinction | The regime is only as good as the chosen transition variable, so a TAR on lagged realized volatility is exactly the "cheap heuristic gate", which is the point: it is the correct baseline, not a competitor |
| Regime switching volatility models | Hamilton and Susmel (1994) SWARCH [verified]; Gray (1996) [verified]; Haas, Mittnik and Paolella (2004) [verified] | One series, thousands of observations for the GARCH part | Path dependence requires approximations (Gray) or parallel GARCH processes (Haas et al.); estimation is heavier than plain HMM | Yes via filtering | Same regime count testing problems as MS AR; adds GARCH persistence identification issues |
| Deep learning and transformer detectors | Only arXiv preprints found for 2022 to 2026, e.g. Boukardagha (2026) [verified, not peer reviewed] | Long samples | Unknown; no refit stability metric reported anywhere | Depends on construction | No peer reviewed net of cost out of sample result located; treat as not established |

Recommendation from this table, stated as my inference: the detector set for the study should be Gaussian HMM (canonical baseline, two and three states), statistical jump model (the current best published performer), BOCPD (the only native online method), and a realized volatility threshold as the TAR style heuristic. MS AR adds little over the HMM on daily returns because the autoregressive term in daily equity returns is negligible.

---

## 3. Instability on a few hundred daily observations, quantified

**What sample sizes the published studies use.** Hamilton (1989): about 135 quarterly observations [recalled]. Ang and Bekaert (2002, JBES): 267 monthly observations in sample [verified]. Rydén et al. (1998): about 17,000 daily observations split into ten subseries of about 1,700 [verified]. Bulla et al. (2011): about 40 years of daily data per index, roughly 10,000 observations [verified]. Nystrup et al. (2018): 4,943 daily observations with a two year initialisation [verified]. Shu, Yu and Mulvey (2024): 3,000 day training windows, about 12 years, with 8 year validation windows [verified]. The modern practice is a training window of 3,000 to 5,000 daily observations. Your total sample is about 6,500. A 3,000 day training window leaves about 14 years of out of sample data on the index, which contains perhaps 8 to 15 high volatility episodes (inference).

**What happens across refits.** Rydén et al.: parameter estimates "sometimes vary considerably from one subseries to the next" at 1,700 daily observations [verified]. Pouzo, Psaradakis and Sola (2022): transition probability estimates are the worst behaved parameter, non normal sampling distributions at T <= 200, and bias that persists at T = 3,200 under misspecification [verified]. Nystrup, Lindström and Madsen (2020): the practical symptom is "unrealistically rapid switching dynamics" [verified]; Shu, Yu and Mulvey measure it as about two shifts a year for the HMM versus under one for the jump model, and as 141 percent versus 44 percent annual turnover [verified]. Label switching: state labels are not identified across refits at all (Celeux, Hurn and Robert 2000 [verified]; Stephens 2000 [exists]), so any rolling refit must impose an ordering, and a state whose variance rank changes between refits silently flips the gate.

**What is not in the literature.** No published study was found that quantifies rolling refit stability of decoded state sequences on financial data with an adjusted Rand index, Hamming distance, or label flip rate. This is a gap you can fill cheaply, and it is the single most original figure the project can produce.

**Diagnostics for whether a fitted regime is real.** (a) Regime count tests with correct null distributions: Hansen (1992), Garcia (1998), Carrasco, Hu and Ploberger (2014), Qu and Zhuo (2021) [all verified], with the last two implemented in MSTest. (b) Regime Classification Measure of Ang and Bekaert (2002, JBES) [verified]: RCM = 400 times the time average of p_t(1 minus p_t) on smoothed probabilities, 0 is perfect classification, 100 is no information. Multi state generalisation is Baele (2005) [recalled]. (c) Pseudo residual checks from Zucchini, MacDonald and Langrock [recalled]: if the model is right, the forecast pseudo residuals are iid standard normal. (d) Cross validated likelihood for the number of states (Celeux and Durand 2008 [verified]) rather than BIC, which over selects (Pohle et al. 2017 [verified]). (e) Expected state durations from the transition matrix compared with the durations of the decoded states; a large gap indicates rapid switching artefacts. (f) Rolling refit stability, as above. (g) Bootstrap confidence intervals for transition probabilities (Bulla and Berzel 2008 [verified]; Ho 2001 [verified]).

---

## 4. Evaluation protocols as tradeoffs

**Walk forward with one out of sample window versus combinatorial purged cross validation (CPCV).** Walk forward is the only protocol that reproduces live deployment: expanding window, refit on a fixed schedule, filtered probability, one day execution lag. What it establishes: the return path an investor would actually have seen. What it cannot establish: whether the sign of the result depends on which 5 to 10 regime episodes fell after the cutoff date, because one split gives one draw. Arian, Norouzi and Seco (2024, Knowledge Based Systems) [verified] compare k fold, purged k fold, walk forward and CPCV in a synthetic environment with regime switching and jump diffusion models and find CPCV has lower probability of backtest overfitting and better deflated Sharpe behaviour, while walk forward "exhibited notable shortcomings in false discovery prevention". CPCV (López de Prado 2018 [recalled]) establishes a distribution of out of sample paths from combinations of purged, embargoed blocks. What it cannot establish: independence. The paths resample the same 10 to 30 episodes, so the path count overstates the information; and with regime durations of weeks to months the embargo needed to prevent leakage between adjacent blocks eats a meaningful share of a 6,500 day sample (inference from both debate agents). I found no peer reviewed critique of CPCV that quantifies path dependence; treat that criticism as inference. Resolution: walk forward is the headline table because it is what the strategy would have done; CPCV is a mandatory gate, with a pre registered rule that PBO above 0.5 disqualifies the configuration regardless of the walk forward number.

**Deflated Sharpe ratio (DSR) versus probability of backtest overfitting (PBO).** DSR (Bailey and López de Prado 2014, JPM [exists]) is the probabilistic Sharpe ratio evaluated at the expected maximum Sharpe of N unskilled trials, with inputs N, variance of trial Sharpes, skew, kurtosis and track length. What it establishes: whether the best configuration's Sharpe clears the bar expected from luck alone across N attempts. What it cannot establish: anything, if N is wrong. The shared ledger is right in spirit but its raw count is not the right N: gated variants of one strategy are highly correlated, so the expected maximum under the null is lower than for independent trials, and pooling a break detection exercise with a trading rule violates the exchangeability the formula assumes (inference, agreed by both debate agents). López de Prado and Lewis (2019, Quantitative Finance) [verified record] give the fix: cluster trials by return correlation and use the effective number of clusters as N. PBO (Bailey, Borwein, López de Prado and Zhu 2017, J. Computational Finance) [verified record] uses combinatorially symmetric cross validation to estimate the probability that the in sample best configuration underperforms the median out of sample. What it establishes: whether selection is doing the work. What it cannot establish: the size of any real edge. Resolution: DSR with clustered effective N per application family is the headline statistic; PBO from the same ledger is the second mandatory gate; report the raw ledger count too so a reader can recompute.

**Ablation against a heuristic gate versus against a random gate.** The heuristic gate (realized volatility threshold, or a 200 day moving average trend filter, Faber 2007 [recalled]) establishes the economic question: does anyone need the HMM. It cannot establish whether the filtered probability carries information beyond lagged volatility, because the heuristic and the HMM are driven by the same volatility clustering. The random gate matched on time in market and turnover, generated by a stationary block bootstrap of the gate series (Politis and Romano 1994 [recalled]) so that persistence is preserved, establishes the statistical question: is the HMM gate's Sharpe outside the distribution of gates that cut exposure on an equally persistent but uninformed schedule. This is the modern form of the market timing tests of Henriksson and Merton (1981) [recalled] and Cumby and Modest (1987) [exists], and of the permutation tests Aronson (2006) [verified] applies to trading rules, and it is what isolates the detector's contribution. It cannot establish economic relevance, because beating random is a low bar. Both are required. A third ablation is cheaper and sharper than either (inference): regress the filtered probability on lagged realized volatility and gate on the residual; if the residual gate has no value, the latent state adds nothing beyond volatility.

**Paired inference.** The gated and ungated series are the same strategy on 70 to 90 percent of days, so the Sharpe difference has a much smaller standard error than either level. Use the Ledoit and Wolf (2008) studentized bootstrap for the difference [verified abstract], not Jobson and Korkie (1981) [recalled], which is invalid under fat tails and serial dependence.

---

## 5. Is a known structural break an established ground truth?

Yes as a benchmarking convention in change point statistics, no as a validation of detector quality in finance, and the precedents are mostly illustrations rather than tests.

Cobb (1978, Biometrika) [verified record] on Nile flows around the 1898 Aswan dam and the coal mining disasters series (Jarrett 1979 [recalled]) are the classic known change benchmarks; they are single series with a single agreed break and are used to show a method works at all, not to measure reliability. Adams and MacKay (2007) [verified] apply BOCPD to Dow Jones daily returns from July 1972 to June 1975 and mark the Liddy and McCord conviction, the OPEC embargo and Nixon's resignation, but "the paper provides no explicit validation against ground truth"; it observes that run length probability changes near those dates and makes no quantitative claim. van den Burg and Williams (2020) [verified] built the first proper benchmark: 37 series, five annotators each, median inter annotator agreement about 0.8 on the covering metric, and the conclusion that with default hyperparameters no method beats predicting no change points, because most methods over fire; only oracle tuning makes BOCPD the best, and the authors say that is "not indicative of real-world performance". Bucci and Ciciretti (2022, Economic Modelling) [verified record and arXiv abstract] validate regime detectors on artificially generated data where regimes are predetermined and then through a trading strategy, and pick a vector logistic STAR model over hierarchical clustering. Shu, Yu and Mulvey (2024) [verified] examine the COVID crash of February to June 2020 explicitly and report that both the HMM and the jump model took "approximately half a month in detecting both the onset and conclusion of the market crash", which they describe as comparable to prior studies reporting median detection lags of around 25 calendar days (I did not verify which prior studies). Kole and van Dijk (2017) [verified] use rule based bull and bear dating (in the tradition of Pagan and Sossounov 2003 and Lunde and Timmermann 2004 [both recalled]) as the reference and find "rule-based methods are preferable for (in-sample) identification of the market state, but regime-switching models for (out-of-sample) forecasting".

What the precedent authors concluded about reliability: where anyone quantified it, detectors find the largest volatility event in the sample with a lag of two to four weeks, over fire at default settings, and the reference labels themselves disagree at the 20 percent level. Nobody concluded that passing a known date test certifies a detector.

Consequences for your design. A single known date is an n of 1 test with no false alarm rate. The only equity breaks known with certainty at daily frequency are large volatility events, which every variance sensitive detector finds, so passing is uninformative and failing is disqualifying: it is a floor test. Demonetisation (8 November 2016) is a poor choice because its equity market impact was modest and coincided with the US election; I would not expect a clean return distribution break there (inference). Replace the single date with a pre registered list of six to eight Indian volatility events (2008 September to October, 2011 August, 2013 August taper episode, 2016 November, 2020 March, 2022 February to June, plus any you add before looking), and report per event and per detector: detection within a fixed window, detection delay in trading days to the first threshold crossing of the filtered probability, and the full sample false alarm count at the same threshold. Frame it in the quality control vocabulary of Page (1954) and Lorden (1971) [both recalled]: average run length to false alarm versus detection delay. Then add the only place ground truth truly exists: simulate from a fitted two state model with known states and produce delay versus false alarm curves for each detector (the Bucci and Ciciretti approach).

---

## 6. Minimum number of independent trades or events

No peer reviewed source gives a minimum trade count; the practitioner rules of thumb (30 trades, 100 to 300 trades, 200 to 500 trades) are attributed to Pardo (2008) [exists; the specific rule could not be confirmed from the text], Aronson (2006) [verified; gives no number, only that data mining bias falls with sample size and rises with the number of rules tested], and a commercial blog. Do not cite a trade count.

What the literature does give is a track length for a Sharpe ratio, and it is set by calendar time, not trade count. Lo (2002) [verified]: the standard error of the Sharpe ratio under iid returns is sqrt((1 + SR squared over 2) over T), so the annualized standard error with daily data is approximately sqrt(252 over T): about 0.32 for 10 years, 0.22 for 20 years, 0.20 for the full 26 year Nifty TRI history (my arithmetic). Bailey and López de Prado (2012) [verified]: minimum track record length; "a 2.73 years track record is required for an annualized Sharpe of 2 to be considered greater than 1 at a 95% confidence level" under normality, and 4.99 years with realistic skew and kurtosis. Harvey, Liu and Zhu (2016) [verified]: a new claim "needs to clear a much higher hurdle, with a t-statistic greater than 3.0"; since t equals annualized Sharpe times root years, a strategy with true Sharpe 0.5 needs 36 years and one with Sharpe 1.0 needs 9 years to reach t of 3, before any haircut. Harvey and Liu (2014) [verified]: worked example where an observed t of 2.92 fails a required 3.66 and the haircut is 91 percent.

For your comparison the relevant quantity is the difference, and it is less hopeless than the level. With correlation rho between gated and ungated daily returns, the annualized standard error of the Sharpe difference is approximately sqrt(2(1 minus rho) over years) (my derivation from the Jobson and Korkie variance, small Sharpe approximation). Gated versus ungated on the same index have rho of roughly 0.7 to 0.85 (inference: the gate removes the high variance days, which carry a disproportionate share of variance). That gives a standard error of the difference of 0.17 to 0.25 with 10 years out of sample and 0.12 to 0.17 with 20 years. A true difference of 0.3 is then 1.2 to 2.5 standard errors; a difference of 0.1, which is where Bulla et al.'s basis point gains sit, is undetectable. Multiple testing raises the bar further.

Counting episodes instead (inference): the gate makes one decision per regime episode, so the effective sample for a hit rate is the number of episodes, perhaps 15 to 30 on the index. To distinguish a 70 percent hit rate from 50 percent with 80 percent power needs about 39 episodes one sided and 49 two sided (standard binomial power calculation). The study is underpowered on that metric too. The way to get more episodes is not more years, which you do not have, but more series: 8 to 10 NSE sector total return indices give quasi replications, though they share the market factor and are not independent (advocate agent's extension, my caveat).

---

## 7. The strongest argument that the study is not worth doing

Stated as the referee would state it.

This paper's unit of statistical information is not the 6,500 daily returns it reports but the 10 to 30 regime episodes those returns are drawn from, and no design choice in the manuscript, walk forward or CPCV, Gaussian HMM or jump model, deflated Sharpe or probability of overfitting, changes that number. The published cost inclusive templates the authors cite put the plausible effect of an HMM gate at 20 to 200 basis points a year or a Sharpe gain of 0.1 to 0.3; the standard error of that gain at the sample length available is 0.12 to 0.25. The study is therefore asked to distinguish signal from noise with a couple of dozen independent regime realisations, and a positive, exploitable result reported from this dataset is more likely a Type I error than a discovery, particularly since the shared ledger's trial count is set by a logging convention the reader cannot audit and nothing in the design stops the authors searching over detectors, state counts and windows until one clears the bar, which is precisely the failure documented by Sullivan, Timmermann and White (1999) [verified], where the best rule survives an in sample reality check and fails in the ten year post sample. Moreover the closest analogue with real time estimation, Cederburg et al. (2020), finds the mechanism the gate relies on does not survive recursive estimation for most strategies, and the heuristic baseline shares that mechanism, so a win over the heuristic would not identify the latent state as the source. The honest outcome of this design is a wide, non rejecting confidence interval. The paper does not need a better detector; it needs either ten times the regime episodes it does not have, or a pre registered commitment to report and accept a null result.

My assessment: the referee is right about power and about the heuristic confound, and the answer is to change what the study claims, not to abandon it (section 9).

---

## 8. Attacks on the design not yet covered above

**The signal series and the strategy are the same series.** If the HMM is fitted on Nifty returns and gates a Nifty long position, the high variance state is identified by the very returns being traded, and the gate is a smoothed volatility filter. That is the Bulla and Nystrup design and it is already published on three developed markets; the Indian replication is the contribution, and it must be labelled as a replication. If instead the base strategy is a cross sectional strategy such as momentum, the prior for regime gating is stronger, because momentum crashes cluster in high volatility rebounds (Daniel and Moskowitz 2016; Barroso and Santa Clara 2015 [both recalled]), and the regime signal and the traded returns are different series. Which strategy you gate is the most consequential open decision in the project.

**Filtered probability plus execution lag.** The filtered probability at t uses the close at t; the earliest execution is the close at t plus 1. Nystrup et al. (2018) used a one day delay. Report the headline with a one day lag and the sensitivity at two days; a result that dies at two days is a microstructure artefact (inference).

**Hyperparameters chosen on the full sample are leakage.** Number of states, window length, jump penalty, BOCPD hazard, volatility threshold: every one must be either fixed before the out of sample period or selected inside the walk forward loop on training data only. Pre register the grid and log every point in the ledger, including abandoned ones.

**The cash leg.** Indian short rates have been 4 to 8 percent over the sample [recalled]. A gate that is in cash 20 percent of the time earns material carry; if the cash leg is modelled as zero return the gate is understated, and if modelled as the overnight rate without the T bill data it is misstated. Use 91 day Treasury bill yields from the RBI database [recalled: available on RBI DBIE] and report the gate's return split into equity leg and cash leg.

**Costs depend on the instrument, and the instrument is unspecified.** Delivery equity on Zerodha as of this month [verified]: zero brokerage, STT 0.1 percent on buy and sell, NSE transaction charge 0.00307 percent, stamp duty 0.015 percent on the buy side, SEBI fee 10 rupees per crore, GST 18 percent on charges, DP charge 15.34 rupees per scrip on sale. That is 11.9 basis points to buy and 10.4 to sell, 22.2 round trip before impact and DP charges (my arithmetic). Nifty futures carry STT of 0.02 percent on the sell side only after the October 2024 change [recalled: verify], and equity ETFs carry STT of 0.001 percent on sale [recalled: verify], so an index gate executed in futures or ETFs costs a few basis points a round trip, an order of magnitude less than delivery stocks. At Shu et al.'s HMM turnover of 141 percent a year, the delivery cost tier alone is roughly 15 to 30 basis points a year depending on how turnover is counted, which is the same size as Bulla et al.'s low end gain. Define three cost tiers and run all three.

**Survivorship in free single stock data.** Ranse (2026) [verified, arXiv] reconstructs NIFTY Smallcap 250 from bhavcopy including delisted securities and finds survivor only data overstates annual return by 4.94 percentage points and Sharpe by 0.097. Index level total return series avoid this entirely; any single stock strategy needs historical constituent lists, which are not cleanly free.

**Data.** NSE bhavcopy is free and goes back to the mid 1990s [recalled]; Nifty 50 TRI is on niftyindices.com from mid 1999 [recalled: verify]; sector TRIs are available for later start dates [recalled]. Reconcile TRI against the price index plus dividend yield before use; a mismatch means a data problem.

**Trial ledger validity.** The ledger must record every configuration run, the family it belongs to, and the correlation of its returns with other trials, so effective N can be computed by clustering. A ledger that records only "kept" configurations is worse than no ledger, because it presents a corrected number that is not corrected.

---

## 9. Extensions that carry the portfolio value

Ranked by the ratio of hiring manager signal to effort. The first three came from the advocate agent; four to six are mine.

1. **Pre registered power statement in the abstract.** State the minimum detectable Sharpe difference given the sample and the correlation between gated and ungated returns, and the minimum track record length needed to confirm the observed difference. A hiring manager reads "we could detect a difference of 0.35 at 80 percent power and observed 0.12 with a 95 percent interval of minus 0.15 to 0.39" as maturity; they read a bare Sharpe of 0.9 as a red flag.

2. **Rolling refit label stability.** Refit each detector monthly on an expanding window, decode the state path, relabel by variance rank, and compute the adjusted Rand index and the label flip rate between consecutive refits. Nobody has published this on financial data. One figure: ARI over time for HMM versus jump model versus BOCPD, with a table of switching frequency and expected versus realised state durations.

3. **Cost sensitivity and break even cost.** Net Sharpe of gated, ungated and heuristic against one way cost from 2 to 100 basis points, with the cost at which the gate's advantage over the heuristic reaches zero marked. This is the question a fund asks and the design does not answer.

4. **Incremental information ablation.** Gate on the HMM probability, on lagged realized volatility, and on the HMM probability orthogonalised to lagged realized volatility. If the third has no value the latent state is a volatility filter, and that is a clean, publishable finding.

5. **Episode attribution.** For every regime episode in the out of sample period, the contribution to the Sharpe difference. If March 2020 carries the whole result, the figure shows it. This is the honest version of "does it work".

6. **Synthetic ground truth.** Simulate from the fitted two state model with known states, run all detectors, and report detection delay against false alarm rate as a curve per detector. This is the only place a detector's quality can be measured, and it replaces the single known date test.

---

## 10. Plan

No code in this phase. Each step ends with a verification that must pass before the next starts.

**Phase 0, week 1: pre registration (decisions.md).** Write the base strategy, universe, instrument and three cost tiers, cash leg source, detector set with fixed hyperparameter grids, refit schedule, execution lag, evaluation protocol (walk forward headline, CPCV gate), primary statistic (DSR with clustered effective N, PBO gate, Ledoit and Wolf paired test), the known event list, the synthetic validation design, the ledger schema, the power calculation, and the stopping rule (one pre registered run of the out of sample analysis). Verify: a second reader can predict every table in the final report from this document alone.

**Phase 1, week 2: data.** Nifty 50 TRI, 8 to 10 sector TRIs, 91 day T bill yields, trading calendar. Verify: TRI reconciles to price index plus dividend yield within tolerance; no gaps; holiday calendar matches NSE.

**Phase 2, weeks 3 to 4: regime interface and detectors.** One interface: input a series up to t, output filtered probability at t. Detectors: Gaussian HMM (2 and 3 states, multiple EM starts, variance rank relabelling), statistical jump model (online greedy variant), BOCPD, realized volatility threshold. Verify: a look ahead test that perturbs data after t and asserts the output at t is unchanged, for every detector; a label consistency test across refits.

**Phase 3, week 5: detector validation.** Synthetic delay versus false alarm curves; known event table; rolling refit ARI. Verify: curves are monotone in the threshold; ARI is computed on aligned dates only.

**Phase 4, weeks 6 to 7: evaluation engine.** Walk forward with expanding window and monthly refits, one and two day lags, three cost tiers, cash leg; CPCV with pre registered embargo; matched random gates by stationary block bootstrap (several hundred draws); Ledoit and Wolf paired bootstrap; trial ledger with correlation clustering; DSR and PBO. Verify: a random gate run recovers a DSR percentile near 50; the ungated strategy under the engine reproduces the published index return.

**Phase 5, week 8: the one pre registered run.** Headline tables, sector replications, cost curve, ablation, episode attribution. Verify: every number in the report traces to a ledger row.

**Phase 6, weeks 9 to 10: write up.** Claims sized to the power calculation. If the gate does not beat the heuristic, the claim is: for this signal series and sample, a latent state gate built and evaluated to institutional standard adds no measurable net of cost value over a volatility threshold; the modelling sophistication is not repaid. That claim is defensible and is what the literature predicts.

Expected outcome, stated now so it is on record: risk reduction is real and likely significant; the Sharpe difference versus the volatility threshold is not significant; the jump model beats the HMM on turnover; the HMM's rolling refit ARI is the most interesting figure in the report.

---

## 11. Open decisions

Defaults chosen; you can overturn any of them.

1. Base strategy to gate. Default: long Nifty 50 TRI with the cash leg at the 91 day T bill rate, because it is the published template and the data is clean. Alternative: cross sectional momentum on Nifty 100 or 200 constituents, stronger prior for regime gating but needs survivorship free constituent history that free data does not supply cleanly.
2. Instrument and headline cost tier. Default: index via futures or ETF at a low tier for the headline, delivery stock tier as sensitivity.
3. Primary detector. Default: Gaussian HMM as headline because that is your framing and the canonical baseline, with the jump model mandatory in every headline table. The evidence says the jump model should win; if you want the headline to be the best detector rather than the canonical one, swap them.
4. Known break test. Default: replace the single date with the pre registered event list plus synthetic ground truth. If you want demonetisation kept, keep it as one row of the table, not as the test.
5. Scope. Default: index and sector indices only, no single stocks, in 10 weeks.

---

## 12. References with verification status

| Reference | Venue | Status |
|---|---|---|
| Adams, MacKay (2007) Bayesian Online Changepoint Detection | arXiv 0710.3742 | verified |
| Ahmad, Bandi (2011) Identifying regime shifts in Indian stock market: A Markov switching approach | MPRA 37174 | verified |
| Ang, Bekaert (2002) International Asset Allocation With Regime Shifts | Review of Financial Studies 15(4) | verified |
| Ang, Bekaert (2002) Regime Switches in Interest Rates | J. Business and Economic Statistics 20(2) | verified |
| Ang, Bekaert (2004) How Regimes Affect Asset Allocation | Financial Analysts Journal 60(2) | verified |
| Ang, Timmermann (2012) Regime Changes and Financial Markets | Annual Review of Financial Economics 4 | verified |
| Arian, Norouzi, Seco (2024) Backtest overfitting in the machine learning era: A comparison of out-of-sample testing methods in a synthetic controlled environment | Knowledge-Based Systems 305 | verified |
| Aronson (2006) Evidence-Based Technical Analysis | Wiley | verified via published review |
| Aydınhan, Kolm, Mulvey, Shu (2024) Identifying patterns in financial markets: extending the statistical jump model for regime identification | Annals of Operations Research | verified |
| Baele (2005) multi regime RCM | J. Financial and Quantitative Analysis | recalled |
| Bailey, López de Prado (2012) The Sharpe Ratio Efficient Frontier | Journal of Risk 15(2) | verified |
| Bailey, López de Prado (2014) The Deflated Sharpe Ratio | J. Portfolio Management 40(5) | exists |
| Bailey, Borwein, López de Prado, Zhu (2017) The Probability of Backtest Overfitting | J. Computational Finance 20(4) | exists |
| Barroso, Santa-Clara (2015) Momentum has its moments | J. Financial Economics | recalled |
| Bemporad, Breschi, Piga, Boyd (2018) Fitting jump models | Automatica 96 | verified |
| Bessec, Bouabdallah (2005) What Causes the Forecasting Failure of Markov-Switching Models? A Monte Carlo Study | Studies in Nonlinear Dynamics and Econometrics 9(2) | verified |
| Botte, Bao (2021) A Machine Learning Approach to Regime Modeling | Two Sigma research note, not peer reviewed | verified |
| Boukardagha (2026) Explainable Regime-Aware Investing | arXiv 2603.04441, not peer reviewed | verified |
| Bucci, Ciciretti (2022) Market regime detection via realized covariances | Economic Modelling 111 | verified record, arXiv abstract read |
| Bulla, Bulla (2006) Stylized facts of financial time series and hidden semi-Markov models | Computational Statistics and Data Analysis 51(4) | exists |
| Bulla, Berzel (2008) Computational issues in parameter estimation for stationary hidden Markov models | Computational Statistics 23 | verified |
| Bulla, Mergner, Bulla, Sesboüé, Chesneau (2011) Markov-switching asset allocation: Do profitable strategies exist? | J. Asset Management 12(5) | verified |
| Carrasco, Hu, Ploberger (2014) Optimal Test for Markov Switching Parameters | Econometrica 82(2) | verified |
| Carter, Steigerwald (2012) Testing for Regime Switching: A Comment | Econometrica | verified |
| Cederburg, O'Doherty, Wang, Yan (2020) On the performance of volatility-managed portfolios | J. Financial Economics 138(1) | verified |
| Celeux, Durand (2008) Selecting hidden Markov model state number with cross-validated likelihood | Computational Statistics 23(4) | verified |
| Celeux, Hurn, Robert (2000) Computational and Inferential Difficulties with Mixture Posterior Distributions | JASA 95(451) | verified |
| Chaudhuri, Kumar (2015) A Markov-Switching Model for Indian Stock Price and Volume | J. Emerging Market Finance 14(3) | verified |
| Cho, White (2007) Testing for Regime Switching | Econometrica 75(6) | verified |
| Clements, Krolzig (1998) A comparison of the forecast performance of Markov-switching and threshold autoregressive models of US GNP | Econometrics Journal 1(1) | exists |
| Cobb (1978) The problem of the Nile: Conditional solution to a changepoint problem | Biometrika 65(2) | verified record |
| Cumby, Modest (1987) Testing for market timing ability: A framework for forecast evaluation | J. Financial Economics | exists |
| Dacco, Satchell (1999) Why do regime-switching models forecast so badly? | Journal of Forecasting 18(1) | verified |
| Daniel, Moskowitz (2016) Momentum crashes | J. Financial Economics | recalled |
| Dueker, Neely (2007) Can Markov switching models predict excess foreign exchange returns? | J. Banking and Finance 31(2) | verified |
| Engel (1994) Can the Markov switching model forecast exchange rates? | J. International Economics 36 | verified |
| Faber (2007) A Quantitative Approach to Tactical Asset Allocation | J. Wealth Management | recalled |
| Fearnhead, Liu (2007) On-line Inference for Multiple Changepoint Problems | JRSS B 69(4) | verified |
| Garcia (1998) Asymptotic Null Distribution of the Likelihood Ratio Test in Markov Switching Models | International Economic Review 39(3) | verified |
| Gray (1996) Modeling the conditional distribution of interest rates as a regime-switching process | J. Financial Economics 42(1) | verified |
| Guidolin (2011) Markov Switching Models in Empirical Finance | Advances in Econometrics 27B | verified |
| Guidolin, Hyde, McMillan, Ono (2009) Non-linear predictability in stock and bond returns: When and where is it exploitable? | International J. Forecasting 25(2) | verified |
| Guidolin, Timmermann (2007) Asset allocation under multivariate regime switching | J. Economic Dynamics and Control 31(11) | verified |
| Guidolin, Timmermann (2008) International asset allocation under regime switching, skew, and kurtosis preferences | Review of Financial Studies 21(2) | exists |
| Haas, Mittnik, Paolella (2004) A New Approach to Markov-Switching GARCH Models | J. Financial Econometrics 2(4) | verified |
| Hamilton (1989) A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle | Econometrica 57(2) | verified |
| Hamilton (1996) Specification testing in Markov-switching time-series models | J. Econometrics 70(1) | verified |
| Hamilton, Susmel (1994) Autoregressive conditional heteroskedasticity and changes in regime | J. Econometrics 64 | verified |
| Hansen (1992) The Likelihood Ratio Test under Nonstandard Conditions: Testing the Markov Switching Model of GNP | J. Applied Econometrics 7(S) | verified |
| Hansen (1996) Inference When a Nuisance Parameter Is Not Identified Under the Null Hypothesis | Econometrica 64(2) | verified |
| Hansen (2000) Sample Splitting and Threshold Estimation | Econometrica 68(3) | verified |
| Harvey, Liu (2014) Evaluating Trading Strategies | J. Portfolio Management 40(5) | verified |
| Harvey, Liu, Zhu (2016) ... and the Cross-Section of Expected Returns | Review of Financial Studies 29(1) | verified |
| Henriksson, Merton (1981) On Market Timing and Investment Performance II | J. Business | recalled |
| Ho (2001) Finite-sample properties of the bootstrap estimator in a Markov-switching model | J. Applied Statistics 28(7) | verified |
| Horvath, Issa, Muguruza (2021) Clustering Market Regimes using the Wasserstein Distance | arXiv 2110.11848, not peer reviewed | verified |
| Jarrett (1979) coal mining disasters data | Biometrika | recalled |
| Jasra, Holmes, Stephens (2005) MCMC Methods and the Label Switching Problem in Bayesian Mixture Modeling | Statistical Science 20(1) | exists |
| Jobson, Korkie (1981) Performance Hypothesis Testing with the Sharpe and Treynor Measures | J. Finance | recalled |
| Killick, Fearnhead, Eckley (2012) Optimal Detection of Changepoints With a Linear Computational Cost | JASA 107(500) | verified |
| Kim (1994) Dynamic linear models with Markov-switching | J. Econometrics 60 | verified |
| Kole, van Dijk (2017) How to Identify and Forecast Bull and Bear Markets? | J. Applied Econometrics 32(1) | verified |
| Kritzman, Li (2010) Skulls, Financial Turbulence, and Risk Management | Financial Analysts Journal 66(5) | verified |
| Kritzman, Page, Turkington (2012) Regime Shifts: Implications for Dynamic Strategies | Financial Analysts Journal 68(3) | verified |
| Krolzig (1997) Markov-Switching Vector Autoregressions | Springer | recalled |
| Ledoit, Wolf (2008) Robust performance hypothesis testing with the Sharpe ratio | J. Empirical Finance 15(5) | verified abstract |
| Lo (2002) The Statistics of Sharpe Ratios | Financial Analysts Journal 58(4) | verified |
| López de Prado (2018) Advances in Financial Machine Learning | Wiley | recalled |
| López de Prado, Lewis (2019) Detection of false investment strategies using unsupervised learning methods | Quantitative Finance 19(9) | verified record |
| Lorden (1971) Procedures for Reacting to a Change in Distribution | Annals of Mathematical Statistics | recalled |
| Lunde, Timmermann (2004) Duration Dependence in Stock Prices | J. Business and Economic Statistics | recalled |
| Moreira, Muir (2017) Volatility-Managed Portfolios | J. Finance 72(4) | verified |
| Mulvey, Liu (2016) Identifying Economic Regimes: Reducing Downside Risks for University Endowments and Foundations | J. Portfolio Management 43(1) | verified |
| Nguyen (2018) Hidden Markov Model for Stock Trading | International J. Financial Studies 6(2) | verified |
| Nystrup, Hansen, Madsen, Lindström (2015) Regime-Based Versus Static Asset Allocation: Letting the Data Speak | J. Portfolio Management 42(1) | verified |
| Nystrup, Kolm, Lindström (2020) Greedy Online Classification of Persistent Market States Using Realized Intraday Volatility Features | J. Financial Data Science 2(3) | verified |
| Nystrup, Lindström, Madsen (2020) Learning hidden Markov models with persistent states by penalizing jumps | Expert Systems with Applications 150 | verified |
| Nystrup, Madsen, Lindström (2018) Dynamic portfolio optimization across hidden market regimes | Quantitative Finance 18(1) | verified |
| Page (1954) Continuous Inspection Schemes | Biometrika 41 | recalled |
| Pagan, Sossounov (2003) A simple framework for analysing bull and bear markets | J. Applied Econometrics | recalled |
| Pardo (2008) The Evaluation and Optimization of Trading Strategies | Wiley | exists |
| Parikakis, Merika (2009) Evaluating volatility dynamics and the forecasting ability of Markov switching models | Journal of Forecasting 28(8) | verified |
| Pettenuzzo, Timmermann (2011) Predictability of stock returns and asset allocation under structural breaks | J. Econometrics 164(1) | verified |
| Pohle, Langrock, van Beest, Schmidt (2017) Selecting the Number of States in Hidden Markov Models: Pragmatic Solutions Illustrated Using Animal Movement | JABES 22 | verified |
| Politis, Romano (1994) The Stationary Bootstrap | JASA | recalled |
| Pouzo, Psaradakis, Sola (2022) Maximum likelihood estimation in Markov regime-switching models with covariate-dependent transition probabilities | Econometrica 90(4); arXiv 1612.04932 | verified |
| Psaradakis, Sola (1998) Finite-sample properties of the maximum likelihood estimator in autoregressive models with Markov switching | J. Econometrics 86(2) | exists |
| Qu, Zhuo (2021) Likelihood Ratio-Based Tests for Markov Regime Switching | Review of Economic Studies 88(2) | verified |
| Ranse (2026) Survivorship Bias in Emerging Market Small-Cap Indices: Evidence from India's NIFTY Smallcap 250 | arXiv 2603.19380, not peer reviewed | verified |
| Rydén, Teräsvirta, Åsbrink (1998) Stylized Facts of Daily Return Series and the Hidden Markov Model | J. Applied Econometrics 13(3) | verified |
| Shu, Mulvey (2024) Dynamic Asset Allocation with Asset-Specific Regime Forecasts | Annals of Operations Research | verified |
| Shu, Yu, Mulvey (2024) Downside risk reduction using regime-switching signals: a statistical jump model approach | J. Asset Management 25(5) | verified |
| Stephens (2000) Dealing with label switching in mixture models | JRSS B 62(4) | exists |
| Stillwagon, Sullivan (2020) Markov switching in exchange rate models: will more regimes help? | Empirical Economics 59(1) | verified |
| Sullivan, Timmermann, White (1999) Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | J. Finance 54(5) | verified |
| Teräsvirta (1994) Specification, Estimation, and Evaluation of Smooth Transition Autoregressive Models | JASA 89 | recalled |
| Tong (1990) Non-linear Time Series: A Dynamical System Approach | Oxford University Press | recalled |
| Truong, Oudre, Vayatis (2020) Selective review of offline change point detection methods | Signal Processing 167 | verified |
| van den Burg, Williams (2020) An Evaluation of Change Point Detection Algorithms | arXiv 2003.06222, not peer reviewed | verified |
| van Dijk, Teräsvirta, Franses (2002) Smooth Transition Autoregressive Models: A Survey of Recent Developments | Econometric Reviews 21(1) | recalled |
| Zerodha equity charges page, September 2026 | zerodha.com/charges | verified |
| Zucchini, MacDonald, Langrock (2016) Hidden Markov Models for Time Series, 2nd ed. | Chapman and Hall/CRC | recalled |

Not verified this session and deliberately not cited as fact: the exact start date of Nifty 50 TRI on niftyindices.com; current STT on index futures and on ETF units; the availability path for 91 day T bill yields on the RBI database; the Pardo trade count rule; which prior studies Shu, Yu and Mulvey cite for the 25 day median detection lag.
