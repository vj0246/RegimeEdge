"""Data CLI.

  python -m osr.data.fetch fo [--start 2004-01-01] [--end YYYY-MM-DD]   NIFTY rows of every F&O bhavcopy
  python -m osr.data.fetch panel                                        data/processed/nifty_fo.parquet
  python -m osr.data.fetch indices [--end YYYY-MM-DD]                   NIFTY 50 price, TRI, 1D rate
  python -m osr.data.fetch rates                                        RBI 91-day T-bill auction yields
"""

import argparse
import logging
from datetime import date, timedelta

from osr.config import settings
from osr.data import niftyindices, nse_fo, rates

INDICES = {
    "nifty50_price": ("NIFTY 50", niftyindices.PRICE, date(1990, 7, 1)),
    "nifty50_tri": ("NIFTY 50", niftyindices.TRI, date(1999, 6, 1)),
    "nifty_1d_rate": ("NIFTY 1D RATE INDEX", niftyindices.PRICE, date(2000, 1, 1)),
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["fo", "panel", "indices", "rates"])
    parser.add_argument("--start", type=date.fromisoformat, default=date(2004, 1, 1), help="fo only")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today() - timedelta(days=1))
    args = parser.parse_args()

    processed = settings.data_dir / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    if args.what == "fo":
        saved, absent = nse_fo.download_range(args.start, args.end, settings.data_dir)
        logging.info("fo: saved %d files, %d days without a file", saved, absent)
    elif args.what == "panel":
        df = nse_fo.build_panel(settings.data_dir)
        df.to_parquet(processed / "nifty_fo.parquet", index=False)
        logging.info("panel: %d rows, %s to %s", len(df), df["date"].min().date(), df["date"].max().date())
    elif args.what == "rates":
        raw = rates.fetch_all()
        raw.to_parquet(processed / "tbill91_raw.parquet", index=False)
        auctions = rates.stitch(raw)
        auctions.to_parquet(processed / "tbill91.parquet", index=False)
        logging.info("rates: %d auctions, %s to %s; rows per source %s", len(auctions),
                     auctions["date"].min().date(), auctions["date"].max().date(),
                     raw["source"].value_counts().to_dict())
    else:
        for key, (name, method, start) in INDICES.items():
            df = niftyindices.fetch_history(name, method, start, args.end)
            df.to_parquet(processed / f"{key}.parquet", index=False)
            logging.info("%s: %d rows, %s to %s", key, len(df), df["date"].min().date(), df["date"].max().date())


if __name__ == "__main__":
    main()
