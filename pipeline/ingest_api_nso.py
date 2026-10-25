"""Fetches NSO's household-income table (SFD_SPB0802_66) and lands the raw
CSV bytes in the landing zone. Does not parse -- that's extract_load_api_nso.py's job.

Adapted from kmch-ml's fetch_nso_income() (Paiiyahh/kmch-ml, private repo).
The endpoint sits behind a WAF that blocks requests without a browser-like
User-Agent (confirmed by direct testing: default python-requests/curl UA
gets an HTTP 418 block page instead of the CSV).
"""

import requests

import landing_store

NSO_DATA_BASE = "https://catalogapi.nso.go.th/api/index"
NSO_TABLE = "SFD_SPB0802_66"


def run() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 kmch-phase3-nso/1.0"})
    resp = session.get(NSO_DATA_BASE, params={"table": NSO_TABLE, "format": "csv"}, timeout=30)
    resp.raise_for_status()

    key, is_new = landing_store.save_version("nso", NSO_TABLE, "csv", resp.content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_api_nso] {status}: {key}")


if __name__ == "__main__":
    run()
