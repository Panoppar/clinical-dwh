"""Fetches DOPA's (stat.bora.dopa.go.th) population-by-area snapshots and
lands them raw in the landing zone. Live, not file-based -- replaces the
earlier external-inputs/dim_population_year.csv one-time export (kmch-ml
input-parity gap 1).

HISTORY WINDOW (added 2026-11-04): DOPA's own year-list page serves every
year back to 2536 BE (confirmed live) -- far more than this project needs.
Walks every year from MIN_YEAR_BE (2560) through whatever the plain-count
dataset's own site menu lists as latest (usually 1 year behind the
age-breakdown dataset -- confirmed live on 2026-10-28 the age-breakdown
already had 2569 BE while plain counts still topped out at 2568 BE), since
the plain-count file is what determines which subdistrict/tambon CODES are
available for the age-breakdown's name-only rows to be matched against (see
extract_load_api_dopa_population.py). Each year lands as its own distinct
object (stem includes the year), so a full historical run only re-fetches
years not already landed -- re-running after the latest year is published
just adds that one new year's objects.

Two DOPA datasets are combined per year:
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
MIN_YEAR_BE_2DIGIT = 60  # 2560 BE -- this project's catchment history floor
# The year list itself is a JS accordion with empty hrefs (confirmed live) --
# every year's nested download links are already present in the page's raw
# HTML regardless, just CSS-hidden, so matching the tambon-level text-file
# link pattern directly is simpler and more robust than trying to parse the
# accordion structure.
STAT_T_LINK_RE = re.compile(r"stat_t(\d{2})\.txt")
PROVINCE_LINK_RE = re.compile(r'<a href="(\.\./file/(\d+)/\d+cc(\d+)\.txt)">')


def _available_plain_count_years(session: requests.Session) -> list[str]:
    """-> 2-digit BE year strings (e.g. '60' for 2560), ascending, confirmed
    present on the year-list page, filtered to >= MIN_YEAR_BE_2DIGIT."""
    resp = session.get(YEAR_LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    years = sorted(set(STAT_T_LINK_RE.findall(resp.text)))
    years = [y for y in years if int(y) >= MIN_YEAR_BE_2DIGIT]
    if not years:
        raise RuntimeError(f"ingest_api_dopa_population: no stat_t{{YY}}.txt link >= 25{MIN_YEAR_BE_2DIGIT} "
                            f"found on {YEAR_LIST_URL} (page layout may have changed)")
    return years


def _ingest_year(session: requests.Session, yy: str) -> None:
    plain_url = f"https://stat.bora.dopa.go.th/new_stat/file/{yy}/stat_t{yy}.txt"
    resp = session.get(plain_url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    key, is_new = landing_store.save_version("dopa_population", f"plain_{yy}", "txt", resp.content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_api_dopa_population] plain counts (25{yy}): {status}: {key}")

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
        # A year this old may simply not have an age-breakdown grid for
        # every province yet -- warn and continue with whichever provinces
        # ARE available, rather than failing the whole historical walk over
        # one thin year (the plain-count file for this year still lands).
        print(f"[ingest_api_dopa_population] WARNING: 25{yy} province grid at {province_grid_url} "
              f"is missing codes {missing} -- skipping those provinces for this year")

    for cc, (yymm, url) in province_urls.items():
        resp = session.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        key, is_new = landing_store.save_version("dopa_population", f"age_{cc}_{yymm}", "txt", resp.content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_dopa_population] age breakdown, province {cc} (25{yy}): {status}: {key}")


def run() -> None:
    session = requests.Session()
    years = _available_plain_count_years(session)
    print(f"[ingest_api_dopa_population] fetching {len(years)} years: "
          f"{'25' + years[0]}-{'25' + years[-1]}")
    for yy in years:
        _ingest_year(session, yy)


if __name__ == "__main__":
    run()
