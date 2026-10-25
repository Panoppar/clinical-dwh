"""Crawls HDC's health-status report catalog (4 subcategories -> ~116
reports, each with its own exposed fiscal years) across the 2 target
zones (13 = Bangkok, 06 = Samut Prakan/Chachoengsao's zone) and lands every
raw JSON response in the landing zone. Does not shred -- that's
extract_load_api_hdc.py's job.

This is the most-requests source of the 5 (catalog discovery + per-report
info + per-report/year/zone data: roughly 1,100-1,300 throttled requests
for a full run), so it's built last, after the landing-zone mechanics were
proven on the simpler sources.

Adapted from kmch-ml's hdc_discover_health_status_reports()/
hdc_get_report_info()/hdc_data() (Paiiyahh/kmch-ml, private repo). Unlike
kmch-ml's own elaborate empty-answer-confirmation/stale-cache-fallback
logic (built for its own local disk cache across many repeated runs),
this ingest step just lands whatever HDC returns once per (report, year,
zone) -- the landing zone's own content-addressing already makes a rerun
a no-op for anything unchanged, and Bronze's shred step is responsible for
telling an empty answer apart from a populated one, not this step.
"""

import json
import re
import time

import requests

import landing_store

HDC_CATALOG_API = "https://api-center-hdc.moph.go.th/v1"
HDC_DATA_API = "https://api-hdc.moph.go.th/v1"
HDC_HEALTH_STATUS_SUBCATALOGS: dict[str, str] = {
    "การป่วยด้วยโรคไม่ติดต่อที่สำคัญ": "6a1fdf282fd28180eed7d1cfe0155e11",
    "สาเหตุการป่วย-ตาย": "491672679818600345dc1833920051b2",
    "โรคจากการประกอบอาชีพและสิ่งแวดล้อม": "f16421e617aed29602f9f09d951cce68",
    "การป่วยด้วยโรคจากมลพิษทางอากาศ": "9c647c1f31ac73f4396c2cf987e7448a",
}
# Reports confirmed (kmch-ml, 2026-09-30) to crash deterministically server-side on every
# year/zone (HTTP 502, "Cannot read properties of undefined") -- not a connection problem.
HDC_EXCLUDE_REPORT_CODES: set[str] = {
    "b4ea22252bb533f3f9225dfcab83d43a",
    "ffce687efcb5268eb4189a9c929bb9f4",
    "5968980caf87d4518aa9f0263a9299c6",
}
HDC_TARGET_ZONES = ("13", "06")  # 13 = Bangkok alone; 06 = Samut Prakan(11)/Chachoengsao(24)'s zone
HDC_MIN_DELAY_S = 0.6


class _Throttle:
    def __init__(self, min_delay: float):
        self.min_delay = min_delay
        self.last = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last = time.monotonic()


def _get_with_retry(session: requests.Session, url: str, throttle: _Throttle, max_attempts: int = 4, **kwargs) -> requests.Response | None:
    for attempt in range(1, max_attempts + 1):
        throttle.wait()
        try:
            resp = session.get(url, timeout=90, **kwargs)
        except requests.RequestException:
            resp = None
        if resp is not None and resp.status_code == 200:
            return resp
        if resp is not None and resp.status_code < 500 and resp.status_code not in (408, 429):
            return resp  # final 4xx, no point retrying
        if attempt < max_attempts:
            time.sleep(2 * attempt)
    return resp


def _expand_report_nodes(nodes: list, out: list[dict[str, str]], subcat_id: str, subcat_name: str) -> None:
    for node in nodes:
        children = node.get("children") or []
        if children:
            _expand_report_nodes(children, out, subcat_id, subcat_name)
            continue
        code = node.get("report_code")
        if code:
            out.append({"report_code": code, "subcatalog_id": subcat_id, "subcatalog_name": subcat_name, "catalog_label": node.get("label", "")})


def _discover_reports(session: requests.Session, throttle: _Throttle) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for subcat_name, subcat_id in HDC_HEALTH_STATUS_SUBCATALOGS.items():
        resp = _get_with_retry(session, f"{HDC_CATALOG_API}/system/subcatalog/info", throttle,
                                params={"subcatalogId": subcat_id}, headers={"domain": ""})
        if resp is None or resp.status_code != 200:
            print(f"[ingest_api_hdc] WARNING: could not fetch catalog for subcatalog '{subcat_name}', skipping")
            continue
        key, _ = landing_store.save_version("hdc", f"catalog_{subcat_id}", "json", resp.content)
        print(f"[ingest_api_hdc] landed catalog: {key}")
        body = resp.json()
        rows = body.get("rows")
        raw_reports = (rows[0].get("reports") if isinstance(rows, list) and rows else []) or []
        _expand_report_nodes(raw_reports, out, subcat_id, subcat_name)
    seen: set[str] = set()
    deduped = []
    for r in out:
        if r["report_code"] in seen:
            continue
        seen.add(r["report_code"])
        deduped.append(r)
    return deduped


def _hdc_data_url(report_code: str, year: int, zone: str) -> str:
    zone = str(zone).zfill(2)
    params = (f"table_display=province&year={year}&month=ALL&zone={zone}"
              f"&province_code=ALL&district_code=ALL&subdistrict_code=ALL&department_code=ALL"
              f"&organization_type=ALL&ministry=ALL&hospital=ALL&service_plan=ALL"
              f"&jurisdiction_code=ALL&freeze_month=ALL&mental_code=ALL&mental_group_code=ALL&custom=[]")
    return f"{HDC_DATA_API}/reports/province/data/{report_code}?{params}"


def run() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 kmch-phase3-hdc/1.0"})
    throttle = _Throttle(HDC_MIN_DELAY_S)

    reports = _discover_reports(session, throttle)
    print(f"[ingest_api_hdc] {len(reports)} unique reports discovered")

    for i, rep in enumerate(reports, 1):
        code = rep["report_code"]
        if code in HDC_EXCLUDE_REPORT_CODES:
            print(f"[ingest_api_hdc] ({i}/{len(reports)}) {code}: excluded (known server-side crash)")
            continue

        resp = _get_with_retry(session, f"{HDC_CATALOG_API}/report-public/info", throttle,
                                params={"reportCode": code, "subCatalogId": rep["subcatalog_id"]}, headers={"domain": ""})
        if resp is None or resp.status_code != 200:
            print(f"[ingest_api_hdc] ({i}/{len(reports)}) {code}: info request failed, skipping")
            continue
        key, _ = landing_store.save_version("hdc", f"info_{code}", "json", resp.content)
        info_body = resp.json()
        info_rows = info_body.get("rows") or {}
        if isinstance(info_rows, list):
            info_rows = info_rows[0] if info_rows else {}
        years = sorted({int(y) for y in (info_rows.get("byear_list") or []) if str(y).isdigit()}, reverse=True)
        if info_body.get("ok") is False or not years:
            print(f"[ingest_api_hdc] ({i}/{len(reports)}) {code}: inactive or no years, skipping data fetch")
            continue

        for year in years:
            for zone in HDC_TARGET_ZONES:
                resp = _get_with_retry(session, _hdc_data_url(code, year, zone), throttle, headers={"domain": ""})
                if resp is None or resp.status_code != 200:
                    print(f"[ingest_api_hdc] ({i}/{len(reports)}) {code} {year} zone{zone}: data request failed, skipping")
                    continue
                key, is_new = landing_store.save_version("hdc", f"data_{code}_{year}_{zone}", "json", resp.content)
                status = "landed new version" if is_new else "unchanged"
                print(f"[ingest_api_hdc] ({i}/{len(reports)}) {code} {year} zone{zone}: {status}")


if __name__ == "__main__":
    run()
