import io
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from osr.data import nse_fo

FIXTURES = Path(__file__).parent / "fixtures"
CASES = [
    ("fo_old_2008-10-24.csv", date(2008, 10, 24)),
    ("fo_old_2005-06-15.csv", date(2005, 6, 15)),  # OPTIONTYPE header variant
    ("fo_udiff_2025-09-02.csv", date(2025, 9, 2)),
]


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES / name, dtype=str)


def test_url_switches_format_at_udiff_cutover():
    assert nse_fo.bhavcopy_url(date(2024, 7, 5)).endswith("/historical/DERIVATIVES/2024/JUL/fo05JUL2024bhav.csv.zip")
    assert nse_fo.bhavcopy_url(date(2024, 7, 8)).endswith("/fo/BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv.zip")


@pytest.mark.parametrize("name,_", CASES)
def test_filter_keeps_only_nifty_index_derivatives(name, _):
    raw = load(name)
    out = nse_fo.filter_nifty(raw)
    symbol = "SYMBOL" if "SYMBOL" in out.columns else "TckrSymb"
    assert len(out) == 4 < len(raw)
    assert set(out[symbol]) == {"NIFTY"}


@pytest.mark.parametrize("name,trade_date", CASES)
def test_normalize_maps_both_formats(name, trade_date):
    df = nse_fo.normalize(nse_fo.filter_nifty(load(name)), trade_date)
    assert list(df.columns) == nse_fo.COLUMNS
    assert (df["date"] == pd.Timestamp(trade_date)).all()
    assert set(df["instrument"]) == {"FUT", "OPT"}
    fut, opt = df[df["instrument"] == "FUT"], df[df["instrument"] == "OPT"]
    assert fut["strike"].isna().all() and fut["opt_type"].isna().all()
    assert set(opt["opt_type"]) == {"CE", "PE"} and (opt["strike"] > 0).all()
    assert (df["expiry"] >= pd.Timestamp(trade_date)).all()
    assert (df["settle"] > 0).all() and (opt["volume"] > 0).all()


def test_normalize_keeps_one_row_per_contract_highest_volume():
    rows = nse_fo.filter_nifty(load("fo_old_2008-10-24.csv"))
    fut = rows[rows["INSTRUMENT"] == "FUTIDX"].iloc[[0]]
    zero = fut.copy()
    zero[["OPEN", "HIGH", "LOW", "CLOSE", "SETTLE_PR", "CONTRACTS", "OPEN_INT"]] = "0"
    doubled = pd.concat([zero, rows, rows], ignore_index=True)
    out = nse_fo.normalize(doubled, date(2008, 10, 24))
    expected = nse_fo.normalize(rows, date(2008, 10, 24))
    assert len(out) == len(expected)
    pd.testing.assert_frame_equal(out.sort_values(["expiry", "strike", "opt_type"]).reset_index(drop=True),
                                  expected.sort_values(["expiry", "strike", "opt_type"]).reset_index(drop=True))


def test_normalize_rejects_rows_for_another_date():
    with pytest.raises(ValueError):
        nse_fo.normalize(nse_fo.filter_nifty(load("fo_old_2008-10-24.csv")), date(2008, 10, 23))


def test_normalize_empty_day():
    empty = load("fo_old_2008-10-24.csv").iloc[0:0]
    assert list(nse_fo.normalize(empty, date(2008, 10, 24)).columns) == nse_fo.COLUMNS


def test_read_zip_csv_splits_glued_records_and_drops_blank_lines():
    header = ("INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,VAL_INLAKH,"
              "OPEN_INT,CHG_IN_OI,TIMESTAMP,")
    nifty = "FUTIDX,NIFTY,28-Mar-2002,0,XX,1,1,1,1,1,5,1,1,1,19-MAR-2002,"
    glued = ("OPTSTK,BAJAJAUTO,30-May-2002,440,CA,0,0,0,46.65,66.2,0,0,0,0,19-MAR-2002,"
             "OPTSTK,INFOSYSTCH,25-Apr-2002,3600,CA,0,0,0,575.7,495.6,0,0,0,0,19-MAR-2002,")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("fo19MAR2002bhav.csv", "\n".join([header, nifty, glued, "", ""]))
    df = nse_fo.read_zip_csv(buf.getvalue())
    assert df["SYMBOL"].tolist() == ["NIFTY", "BAJAJAUTO", "INFOSYSTCH"]
    assert df["SETTLE_PR"].tolist() == ["1", "66.2", "495.6"]


def test_read_zip_csv_rejects_unknown_damage():
    with pytest.raises(ValueError):
        nse_fo.repair_lines(["A,B,C,", "1,2,3,", "1,2"])


def test_align_monthly_expiries_moves_holiday_labels_only():
    D = pd.Timestamp
    rows = []
    for d in ("2008-12-22", "2008-12-23", "2008-12-24"):  # 25 Dec holiday: the Dec contract last traded on the 24th
        rows += [(D(d), "FUT", D("2008-12-25"), None, None), (D(d), "OPT", D("2008-12-25"), 3000.0, "CE"),
                 (D(d), "FUT", D("2009-01-29"), None, None), (D(d), "OPT", D("2008-12-31"), 3000.0, "PE")]
    rows += [(D("2009-01-29"), "FUT", D("2009-01-29"), None, None), (D("2009-01-29"), "FUT", D("2009-02-26"), None, None)]
    panel = pd.DataFrame(rows, columns=["date", "instrument", "expiry", "strike", "opt_type"])
    out = nse_fo.align_monthly_expiries(panel)
    assert set(out.loc[out["expiry"] < D("2009-01-01"), "expiry"]) == {D("2008-12-24"), D("2008-12-31")}
    assert (out.loc[panel["expiry"] == D("2008-12-25"), "expiry"] == D("2008-12-24")).all()
    assert (out.loc[panel["expiry"] == D("2008-12-31"), "expiry"] == D("2008-12-31")).all()  # weekly-style label
    assert (out.loc[panel["expiry"] == D("2009-01-29"), "expiry"] == D("2009-01-29")).all()
    assert (out.loc[panel["expiry"] == D("2009-02-26"), "expiry"] == D("2009-02-26")).all()  # still open


def test_align_monthly_expiries_merges_two_labels_in_a_month():
    D = pd.Timestamp
    rows = [(D("2025-08-29"), "FUT", D("2025-09-25"), None, None), (D("2025-08-29"), "OPT", D("2025-09-25"), 100.0, "CE"),
            (D("2025-09-01"), "FUT", D("2025-09-30"), None, None), (D("2025-09-01"), "OPT", D("2025-09-30"), 100.0, "CE"),
            (D("2025-09-30"), "FUT", D("2025-09-30"), None, None), (D("2025-10-01"), "FUT", D("2025-10-28"), None, None)]
    panel = pd.DataFrame(rows, columns=["date", "instrument", "expiry", "strike", "opt_type"])
    out = nse_fo.align_monthly_expiries(panel)
    assert set(out.loc[out["date"] <= D("2025-09-30"), "expiry"]) == {D("2025-09-30")}


def test_read_zip_csv():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("BhavCopy.csv", (FIXTURES / "fo_udiff_2025-09-02.csv").read_text())
    assert len(nse_fo.read_zip_csv(buf.getvalue())) == len(load("fo_udiff_2025-09-02.csv"))
