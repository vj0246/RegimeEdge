"""data/manifest.json: SHA-256, row count and date range of each processed file; hashed into prereg.lock.

  python -m osr.data.manifest
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

from osr.config import settings


def build_manifest(processed: Path) -> dict[str, dict]:
    out = {}
    for path in sorted(processed.glob("*.parquet")):
        dates = pd.read_parquet(path, columns=["date"])["date"]
        out[path.name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": int(len(dates)),
            "first": str(dates.min().date()),
            "last": str(dates.max().date()),
        }
    return out


def main() -> None:
    manifest = build_manifest(settings.data_dir / "processed")
    path = settings.data_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{path}: {len(manifest)} files")


if __name__ == "__main__":
    main()
