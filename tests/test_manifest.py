import hashlib

import pandas as pd

from osr.data.manifest import build_manifest


def test_manifest_hashes_and_ranges(tmp_path):
    pd.DataFrame({"date": pd.to_datetime(["2020-01-02", "2020-01-01"]), "x": [1.0, 2.0]}).to_parquet(tmp_path / "a.parquet")
    (tmp_path / "notes.txt").write_text("ignored")
    m = build_manifest(tmp_path)
    assert list(m) == ["a.parquet"]
    assert m["a.parquet"]["sha256"] == hashlib.sha256((tmp_path / "a.parquet").read_bytes()).hexdigest()
    assert (m["a.parquet"]["rows"], m["a.parquet"]["first"], m["a.parquet"]["last"]) == (2, "2020-01-01", "2020-01-02")
