from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from osr.data import rates


def test_parse_handbook_sheet_locates_columns_by_header():
    sheet = pd.DataFrame([
        [None, "TABLE 215 : AUCTIONS OF 91-DAY GOVERNMENT OF INDIA TREASURY BILLS", None, None],
        [None, "Date of Auction", "Notified Amount", "Implicit Yield at Cut-off Price (per cent)"],
        [None, 1, 2, 3],
        [None, "1998-99", None, None],
        ["1998-99", datetime(1998, 4, 3), 100, 7.332],
        [None, datetime(1998, 4, 7), 100, "7.3320"],
        [None, "Note : 1) The notified amount ...", None, None],
    ])
    out = rates.parse_handbook_sheet(sheet)
    assert out["date"].tolist() == [pd.Timestamp("1998-04-03"), pd.Timestamp("1998-04-07")]
    assert out["yield_pct"].tolist() == [7.332, 7.332]


def test_parse_dbie_keeps_only_91_day_rows():
    html = ('x{\\"tenor\\":\\"91-day\\",\\"auction_date\\":\\"06-Apr-2011\\",\\"notified\\":4000,'
            '\\"implicit_yield\\":7.1443,\\"wavg_price\\":98.25},'
            '{\\"tenor\\":\\"182-day\\",\\"auction_date\\":\\"06-Apr-2011\\",\\"implicit_yield\\":7.5,\\"x\\":1}')
    out = rates.parse_dbie(html)
    assert out["date"].tolist() == [pd.Timestamp("2011-04-06")] and out["yield_pct"].tolist() == [7.1443]


def test_stitch_prefers_earlier_source():
    raw = pd.DataFrame({"date": pd.to_datetime(["2011-04-06", "2011-04-06", "2011-04-13"]),
                        "yield_pct": [7.14, 7.20, 7.18],
                        "source": ["dbie_bulletin_t26", "hb2011_t215", "dbie_bulletin_t26"]})
    out = rates.stitch(raw)
    assert out["yield_pct"].tolist() == [7.20, 7.18]
    assert out["source"].tolist() == ["hb2011_t215", "dbie_bulletin_t26"]


def test_daily_cash_return_uses_yield_known_at_previous_close():
    auctions = pd.DataFrame({"date": pd.to_datetime(["2020-01-06", "2020-01-13"]), "yield_pct": [6.0, 7.0]})
    dates = pd.DatetimeIndex(["2020-01-10", "2020-01-13", "2020-01-14"])
    rf = rates.daily_cash_return(auctions, dates)
    assert np.isnan(rf.iloc[0])
    assert rf.iloc[1] == pytest.approx(0.06 * 3 / 365)  # Fri to Mon at the 6 Jan yield
    assert rf.iloc[2] == pytest.approx(0.07 * 1 / 365)  # 13 Jan auction known at that close
