from datetime import date

import pandas as pd

from osr.data.dates import format_day_mon_year, parse_day_mon_year


def test_parse_day_mon_year_variants():
    s = pd.Series(["26-Jul-2001", "24-OCT-2008", "14-May-12", "03 Jul 1990"], dtype=str)
    assert parse_day_mon_year(s).tolist() == [pd.Timestamp(d) for d in ("2001-07-26", "2008-10-24", "2012-05-14", "1990-07-03")]


def test_format_day_mon_year():
    assert format_day_mon_year(date(1999, 1, 1)) == "01-Jan-1999"
