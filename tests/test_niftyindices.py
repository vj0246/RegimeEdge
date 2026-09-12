import json
from datetime import date

import pandas as pd
import pytest

from osr.data import niftyindices as ni

PRICE_ROWS = [
    {"RequestNumber": "x", "Index Name": "", "INDEX_NAME": "Nifty 50", "HistoricalDate": "11 Sep 2026",
     "OPEN": "23270.3", "HIGH": "23448.1", "LOW": "23231.4", "CLOSE": "23398.10"},
    {"RequestNumber": "x", "Index Name": "", "INDEX_NAME": "NIFTY 50", "HistoricalDate": "03 Jul 1990",
     "OPEN": "-", "HIGH": "-", "LOW": "-", "CLOSE": "279.02"},
]
TRI_ROWS = [{"RequestNumber": "x", "Index Name": "Nifty 50", "Date": "30 Jun 1999",
             "TotalReturnsIndex": "1256.38", "NTR_Value": "-"}]


def test_cinfo_format():
    assert ni.cinfo("NIFTY 50", date(1999, 1, 1), date(1999, 12, 31)) == (
        "{'name':'NIFTY 50','startDate':'01-Jan-1999','endDate':'31-Dec-1999','indexName':'NIFTY 50'}"
    )


@pytest.mark.parametrize("text", [json.dumps(PRICE_ROWS), json.dumps({"d": json.dumps(PRICE_ROWS)})])
def test_parse_response_accepts_both_payload_shapes(text):
    assert ni.parse_response(text) == PRICE_ROWS


def test_parse_response_rejects_html():
    with pytest.raises(ValueError):
        ni.parse_response("<!DOCTYPE html><html></html>")


def test_price_frame_treats_dash_as_missing():
    df = ni.to_frame(PRICE_ROWS, ni.PRICE)
    assert df.loc[1, "date"] == pd.Timestamp("1990-07-03")
    assert pd.isna(df.loc[1, "open"]) and df.loc[1, "close"] == 279.02
    assert df.loc[0, "close"] == 23398.10


def test_tri_frame():
    df = ni.to_frame(TRI_ROWS, ni.TRI)
    assert df.loc[0, "date"] == pd.Timestamp("1999-06-30")
    assert df.loc[0, "tri"] == 1256.38 and pd.isna(df.loc[0, "ntr"])


def test_empty_rows():
    assert list(ni.to_frame([], ni.TRI).columns) == ["date", "tri", "ntr"]
