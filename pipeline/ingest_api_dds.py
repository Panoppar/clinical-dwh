"""Fetches DDS's priority-disease-ranking PDF report for the 3 target
provinces and lands each province's raw PDF bytes in the landing zone.
Does not parse -- that's extract_load_api_dds.py's job.

DDS keeps no server-side archive: once a reporting year closes, that PDF
cannot be re-fetched. This is the landing zone's main reason to exist for
this source -- once landed, the PDF survives even if DDS later stops
serving that year.

Adapted from kmch-ml's dds_get_token()/dds_detect_current_year()/
dds_finished_year_range()/fetch_dds_disease_ranking() (Paiiyahh/kmch-ml,
private repo). DDS's "priority" endpoint serves only ONE reporting year at
a time, and that year is not a fixed calendar offset -- it switches on its
own schedule -- so the year is auto-detected by probing outward from
today's calendar year rather than hardcoded.

NOT YET LIVE-VERIFIED in this build: DDS's own backend is currently
returning a server-side error ("could not find driver", pgsql/PDO,
confirmed by direct testing on 2026-10-25) for every year/province probed
-- a real outage on DDS's end, unrelated to this code. This module mirrors
kmch-ml's already-proven-working logic; re-run it once DDS recovers to
confirm end-to-end.
"""

import datetime
import re
import time

import requests

import landing_store

DDS_BASE_URL = "https://doe.moph.go.th/dds-report"
DDS_STORE_URL = f"{DDS_BASE_URL}/priority/store"
DDS_PROVINCE_NAMES = {"10": "กรุงเทพมหานคร", "11": "สมุทรปราการ", "24": "ฉะเชิงเทรา"}
DDS_FULL_YEAR_RANGES = ("1-53", "1-52")  # a finished year is weeks 1-53, or 1-52 in a 52-week year


def _get_token(session: requests.Session) -> str:
    resp = session.get(DDS_BASE_URL, timeout=30)
    resp.raise_for_status()
    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', resp.text)
    if not match:
        raise RuntimeError("DDS: could not find CSRF token on main page")
    return match.group(1)


def _fetch_province_pdf(session: requests.Session, token: str, province_code: str, year_ce: int, week_range: str) -> bytes:
    payload = {"_token": token, "level": "prov", "f_prov": province_code, "f_year": str(year_ce),
               "date_type": "gen", "f_wk_start_end": week_range}
    headers = {"X-CSRF-TOKEN": token, "X-Requested-With": "XMLHttpRequest"}
    resp = session.post(DDS_STORE_URL, data=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    if "pdf" not in resp.headers.get("Content-Type", ""):
        raise RuntimeError(f"DDS: expected PDF for province {province_code} year {year_ce} range {week_range}, got {resp.headers.get('Content-Type')}")
    return resp.content


def _detect_current_year(session: requests.Session, token: str, probe_province_code: str = "10") -> int:
    current_ce = datetime.date.today().year
    candidates = [current_ce + 1, current_ce, current_ce - 1, current_ce - 2]
    for year_ce in candidates:
        for week_range in DDS_FULL_YEAR_RANGES:
            try:
                _fetch_province_pdf(session, token, probe_province_code, year_ce, week_range)
                return year_ce
            except Exception:
                time.sleep(1.0)
                continue
    raise RuntimeError(f"DDS: none of the probed years {candidates} returned data -- check the site manually, its year scheme may have changed")


def _finished_year_range(session: requests.Session, token: str, year_ce: int, probe_province_code: str = "10") -> str:
    for week_range in DDS_FULL_YEAR_RANGES:
        try:
            _fetch_province_pdf(session, token, probe_province_code, year_ce, week_range)
            return week_range
        except Exception:
            time.sleep(0.6)
    raise RuntimeError(f"DDS: year {year_ce} did not accept either full-year week range {DDS_FULL_YEAR_RANGES}")


def run() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 kmch-phase3-dds/1.0"})
    token = _get_token(session)

    year_ce = _detect_current_year(session, token)
    print(f"[ingest_api_dds] auto-detected current reporting year = {year_ce}")
    week_range = _finished_year_range(session, token, year_ce)

    for province_code, province_name in DDS_PROVINCE_NAMES.items():
        content = _fetch_province_pdf(session, token, province_code, year_ce, week_range)
        key, is_new = landing_store.save_version("dds", f"{year_ce}_{province_code}", "pdf", content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_dds] {province_name} ({province_code}) year {year_ce}: {status}: {key}")


if __name__ == "__main__":
    run()
