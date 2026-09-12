"""Transaction costs on the 1 Apr 2026 schedule (decisions.md section 7), as fractions."""

SEBI = 0.000001  # Rs 10 per crore
GST = 0.18
SLIPPAGE = 0.0001

# Track S: per option leg per trade, fraction of premium, before the half-spread.
OPT_NSE = 0.0003553
OPT_SELL = 0.0015 + OPT_NSE + SEBI + GST * (OPT_NSE + SEBI)  # STT on premium
OPT_BUY = 0.00003 + OPT_NSE + SEBI + GST * (OPT_NSE + SEBI)  # stamp duty
HALF_SPREAD = {"low": 0.0025, "headline": 0.01, "high": 0.03}

# Track T: per one-way switch, fraction of notional, including slippage. (buy, sell)
FUT_NSE = 0.0000183
EQ_NSE = 0.0000307
TRI_TIERS = {
    "headline": (0.00002 + FUT_NSE + SEBI + GST * (FUT_NSE + SEBI) + SLIPPAGE,
                 0.0005 + FUT_NSE + SEBI + GST * (FUT_NSE + SEBI) + SLIPPAGE),
    "delivery": (0.001 + 0.00015 + EQ_NSE + SEBI + GST * (EQ_NSE + SEBI) + SLIPPAGE,
                 0.001 + EQ_NSE + SEBI + GST * (EQ_NSE + SEBI) + SLIPPAGE),
    "stress": (0.0025, 0.0025),
}
