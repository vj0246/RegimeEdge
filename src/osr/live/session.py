"""Kite session: a client holding the day's access token, and the daily login that creates it.

  python -m osr.live.session login   opens the login page; paste the request_token; the token goes into .env
  python -m osr.live.session check   confirms the saved token works (prints the user id only)

Run these in your own terminal. Nothing here prints a secret.
"""

import re
import sys
import webbrowser
from pathlib import Path

from kiteconnect import KiteConnect

from osr.live.settings import ENV_FILE, KiteSettings


def client(settings: KiteSettings | None = None) -> KiteConnect:
    s = settings or KiteSettings()
    token = s.access_token.get_secret_value() if s.access_token else ""
    if not token:
        raise RuntimeError("KITE_ACCESS_TOKEN is empty: run `python -m osr.live.session login` first")
    kite = KiteConnect(api_key=s.api_key.get_secret_value())
    kite.set_access_token(token)
    return kite


def save_token(token: str, env_file: Path = ENV_FILE) -> None:
    """Replace the KITE_ACCESS_TOKEN line, keeping every other line of the file."""
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    lines = [line for line in lines if not line.startswith("KITE_ACCESS_TOKEN=")]
    env_file.write_text("\n".join([*lines, f"KITE_ACCESS_TOKEN={token}"]) + "\n", encoding="utf-8")


def login() -> None:
    s = KiteSettings()
    kite = KiteConnect(api_key=s.api_key.get_secret_value())
    print("Log in, then copy request_token from the address bar after the redirect:\n" + kite.login_url())
    webbrowser.open(kite.login_url())
    request_token = input("request_token: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9]{8,64}", request_token):
        raise SystemExit("that does not look like a request_token")
    data = kite.generate_session(request_token, api_secret=s.api_secret.get_secret_value())
    save_token(data["access_token"])
    print(f"Saved today's access token to {ENV_FILE} for user {data.get('user_id', '?')}.")


def check() -> None:
    print(f"Token valid for user {client().profile()['user_id']}.")


if __name__ == "__main__":
    commands = {"login": login, "check": check}
    if sys.argv[1:2] and sys.argv[1] in commands:
        commands[sys.argv[1]]()
    else:
        sys.exit(__doc__)
