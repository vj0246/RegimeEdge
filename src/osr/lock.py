"""Pre-registration lock (decisions.md section 13).

  python -m osr.lock create    write prereg.lock from decisions.md and data/manifest.json (owner action)
  python -m osr.lock verify
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from osr.config import settings
from osr.engine.ledger import git_state

LOCK, DECISIONS, TAG = Path("prereg.lock"), Path("decisions.md"), "prereg-v1"


def digest(path: Path) -> str:
    """SHA-256 with line endings normalised, so a checkout on another OS hashes the same."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def current(decisions: Path = DECISIONS, manifest: Path | None = None) -> dict[str, str]:
    manifest = manifest or settings.data_dir / "manifest.json"
    return {"decisions.md": digest(decisions), "data/manifest.json": digest(manifest)}


def create(lock: Path = LOCK, **paths) -> dict[str, str]:
    record = current(**paths)
    lock.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def verify(lock: Path = LOCK, check_git: bool = True, **paths) -> None:
    if not lock.exists():
        raise RuntimeError("prereg.lock missing: the sealed run needs a locked pre-registration")
    if json.loads(lock.read_text(encoding="utf-8")) != current(**paths):
        raise RuntimeError("decisions.md or data/manifest.json changed since the lock")
    if check_git:
        if git_state()[1]:
            raise RuntimeError("working tree is dirty")
        if subprocess.run(["git", "rev-parse", "--verify", TAG], capture_output=True).returncode != 0:
            raise RuntimeError(f"git tag {TAG} not found")


if __name__ == "__main__":
    if sys.argv[1:] == ["create"]:
        print(create())
    elif sys.argv[1:] == ["verify"]:
        verify()
        print("lock verified")
    else:
        sys.exit(__doc__)
