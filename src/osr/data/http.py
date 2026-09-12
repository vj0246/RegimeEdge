"""HTTP with a browser User-Agent, bounded retries and exponential backoff."""

import time

import requests

from osr.config import settings

RETRY_STATUS = {429, 500, 502, 503, 504}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = settings.user_agent
    return session


def fetch(
    session: requests.Session,
    method: str,
    url: str,
    *,
    missing_ok: bool = False,
    retries: int = 4,
    timeout: float = 60.0,
    **kwargs,
) -> requests.Response | None:
    """Return the response, or None on 404 when missing_ok. Retries connection errors, 429 and 5xx."""
    for attempt in range(retries + 1):
        try:
            resp = session.request(method, url, timeout=timeout, **kwargs)
        except (requests.ConnectionError, requests.Timeout):
            if attempt == retries:
                raise
        else:
            if resp.status_code == 404 and missing_ok:
                return None
            if resp.status_code not in RETRY_STATUS or attempt == retries:
                resp.raise_for_status()
                return resp
        time.sleep(2**attempt)
    raise AssertionError("unreachable")
