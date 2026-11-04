"""Fetches DOE's (doe.go.th) monthly foreign-worker-permit PDF reports and
lands them raw in the landing zone. Live, not file-based -- replaces the
earlier external-inputs/bma_migrant_worker_2568.csv one-time snapshot
(kmch-ml input-parity gap 2).

HISTORY WINDOW (added 2026-11-04): walks every report currently listed, not
just the latest. DOE's own listing page only carries a rolling recent
window -- confirmed live on 2026-11-04 it had exactly 20 months, back to
2567-06 (มิถุนายน 2567), nowhere near the 10-year-back request this project
would otherwise target; there is no older archive page to page through
(confirmed by inspecting the listing page's own pagination, which has
none). This is a real, external limitation of the source, not a
self-imposed scope cut -- documented here so it isn't mistaken for an
oversight later. Each report lands as its own distinct object (stem
includes year+month), so re-running only fetches months not already
landed -- the common case is one new month appearing at a time.

The listing page is scraped (not a fixed URL template) because each
month's download id is not sequential/predictable -- confirmed live
(ids found: 121944, 121945, 122524, ... 151235, no fixed stride).
Report items are listed newest-first.
"""

import re

import requests
from bs4 import BeautifulSoup

import landing_store

THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
TITLE_MONTH_YEAR_RE = re.compile(r"เดือน\s*(\S+)\s*พ\.ศ\.(\d{4})")

LISTING_URL = (
    "https://www.doe.go.th/prd/alien/statistic/param/site/152/cat/82/sub/73"
    "/pull/sub_category/view/list-label"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 clinical-dwh/1.0"}
TITLE_PREFIX = "สถิติการทำงานของคนต่างด้าวประจำเดือน"


def _find_all_report_urls(session: requests.Session) -> list[tuple[str, str]]:
    """-> [(title, href), ...] for every report link found, newest-first
    (the order the listing page itself uses)."""
    resp = session.get(LISTING_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    reports = [
        (a["title"].strip(), a["href"])
        for a in soup.find_all("a", title=True)
        if a["title"].strip().startswith(TITLE_PREFIX) and a.get("href")
    ]
    if not reports:
        raise RuntimeError(f"ingest_api_doe_migrant_worker: no report links found on {LISTING_URL} "
                            f"(page layout may have changed)")
    return reports


def _stem_for(title: str) -> str:
    # Stem includes the report title's own year(BE)/month so distinct months
    # land as distinct, inspectable objects, not just content hashes -- a plain
    # ASCII-only sanitize of the full (all-Thai) title strips everything except
    # the year digits, so different months would collide on the same stem;
    # parsing year+month out explicitly avoids that.
    date_m = TITLE_MONTH_YEAR_RE.search(title)
    if date_m:
        month_num = THAI_MONTHS.get(date_m.group(1))
        return f"{date_m.group(2)}_{month_num:02d}" if month_num else date_m.group(2)
    return re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")


def run() -> None:
    session = requests.Session()
    reports = _find_all_report_urls(session)
    print(f"[ingest_api_doe_migrant_worker] {len(reports)} report(s) listed "
          f"(oldest: {reports[-1][0]!r}, newest: {reports[0][0]!r})")

    for title, pdf_url in reports:
        stem = _stem_for(title)
        resp = session.get(pdf_url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        key, is_new = landing_store.save_version("doe_migrant_worker", stem, "pdf", resp.content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_doe_migrant_worker] {title}: {status}: {key}")


if __name__ == "__main__":
    run()
