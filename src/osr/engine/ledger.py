"""Append-only run ledger (decisions.md section 13). Rows are never edited or deleted."""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path("ledger.jsonl")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_state() -> tuple[str, bool]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    return (head.stdout.strip() if head.returncode == 0 else "no-commit"), bool(status.stdout.strip())


def append(config: dict, data_manifest_sha256: str, returns_file: str, metrics: dict, path: Path = LEDGER) -> dict:
    sha, dirty = git_state()
    row = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": sha,
        "dirty": dirty,
        "config": config,
        "config_sha256": sha256_text(canonical(config)),
        "data_manifest_sha256": data_manifest_sha256,
        "returns_file": returns_file,
        "metrics": metrics,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(canonical(row) + "\n")
    return row
