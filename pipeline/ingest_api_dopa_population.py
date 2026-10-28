"""Fetches DOPA's (stat.bora.dopa.go.th) population-by-area snapshot and
lands it raw in the landing zone. Live, not file-based -- replaces the
earlier external-inputs/dim_population_year.csv one-time export (kmch-ml
input-parity gap 1).

Two DOPA datasets are combined, confirmed live to be on DIFFERENT
publication schedules (the age-breakdown dataset is ahead of the plain
count dataset -- e.g. on 2026-10-28 the age-breakdown already had year
2569 BE while the plain count dataset still topped out at 2568 BE), so
this always targets whichever year the PLAIN COUNT dataset's own site
menu lists as latest -- that's the one both datasets are guaranteed to
have, since it determines which subdistrict/tambon CODES are available
for the age-breakdown's name-only rows to be matched against (see
extract_load_api_dopa_population.py):
  - "จำนวนประชากร" (plain counts, nationwide in one file, HAS numeric
    province/district/tambon codes) -> stat_t{YY}.txt
  - "จำนวนประชากรแยกรายอายุ" (single-year-of-age x sex breakdown, one file
    PER PROVINCE, NO codes -- area identified by name only) ->
    {YYMM}cc{province_code}.txt

Scoped to this project's 3-province catchment (Bangkok=10, Samut
Prakan=11, Chachoengsao=24 -- the same provinces
gold.dim_tambon_unit_xwalk already covers) rather than all 77 provinces,
since that's all any downstream table needs.
"""

import re

import requests

import landing_store

YEAR_LIST_URL = "https://stat.bora.dopa.go.th/new_stat/webPage/statByYear.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 clinical-dwh/1.0"}
TARGET_PROVINCE_CODES = ["10", "11", "24"]
# The year list itself is a JS accordion with empty hrefs (confirmed live) --
# every year's nested download links are already present in the page's raw
# HTML regardless, just CSS-hidden, so matching the tambon-level text-file
# link pattern directly is simpler and more robust than trying to parse the
# accordion structure.
STAT_T_LINK_RE = re.compile(r"stat_t(\d{2})\.txt")
PROVINCE_LINK_RE = re.compile(r'<a href="(\.\./file/(\d+)/\d+cc(\d+)\.txt)">')


def _latest_plain_count_year(session: requests.Session) -> str:
    resp = session.get(YEAR_LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    # Listed newest-first (confirmed live); first match wins.
    m = STAT_T_LINK_RE.search(resp.text)
    if not m:
        raise RuntimeError(f"ingest_api_dopa_population: no stat_t{{YY}}.txt link found on {YEAR_LIST_URL} "
                            f"(page layout may have changed)")
    return m.group(1)


def run() -> None:
    session = requests.Session()
    yy = _latest_plain_count_year(session)
    print(f"[ingest_api_dopa_population] latest plain-count year: 25{yy} BE")

    plain_url = f"https://stat.bora.dopa.go.th/new_stat/file/{yy}/stat_t{yy}.txt"
    resp = session.get(plain_url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    key, is_new = landing_store.save_version("dopa_population", f"plain_{yy}", "txt", resp.content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_api_dopa_population] plain counts ({yy}): {status}: {key}")

    province_grid_url = f"https://stat.bora.dopa.go.th/new_stat/webPage/statByProvince.php?year={yy}"
    resp = session.get(province_grid_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    province_urls = {}
    for _href, yymm, cc in PROVINCE_LINK_RE.findall(resp.text):
        if cc in TARGET_PROVINCE_CODES:
            # Build the absolute URL directly rather than resolving the page's
            # own "../file/..." relative href -- simpler and avoids depending
            # on which directory the link happens to be relative from.
            province_urls[cc] = (yymm, f"https://stat.bora.dopa.go.th/new_stat/file/{yymm}/{yymm}cc{cc}.txt")
    missing = set(TARGET_PROVINCE_CODES) - set(province_urls)
    if missing:
        raise RuntimeError(f"ingest_api_dopa_population: province grid at {province_grid_url} "
                            f"is missing codes {missing} (page layout may have changed)")

    for cc, (yymm, url) in province_urls.items():
        resp = session.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        key, is_new = landing_store.save_version("dopa_population", f"age_{cc}_{yymm}", "txt", resp.content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_dopa_population] age breakdown, province {cc} ({yymm}): {status}: {key}")


if __name__ == "__main__":
    run()
