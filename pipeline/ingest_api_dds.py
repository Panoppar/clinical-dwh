"""Fetches DDS's priority-disease-ranking PDF report for every Thai province
and lands each one's raw PDF bytes in the landing zone. Does not parse --
that's extract_load_api_dds.py's job.

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

PROVINCE SCOPE: originally hardcoded to kmch-ml's own 3-province catchment
area (Bangkok/Samut Prakan/Chachoengsao) -- a deliberate scope match to
that project, not a DDS API limitation. Widened 2026-11-03 to all 77
provinces at this warehouse's own scope (not kmch-ml's), using the
code->Thai-name mapping from Thailand's canonical ADM1 boundary dataset
(DevelopedbyWill/thailand-canonical-admin-names, ADM1_PCODE "TH10" etc. --
same codes DDS's own f_prov parameter already used for the original 3,
confirmed matching: 10=Bangkok, 11=Samut Prakan, 24=Chachoengsao). NOT
LIVE-VERIFIED beyond those original 3 -- DDS's backend has been down since
2026-10-25 (see below), so there has been no way to confirm the other 74
provinces actually return data under this same f_prov scheme. Re-run this
module once DDS recovers; if any province code 404s or errors, that's a
signal that code genuinely isn't recognized by this endpoint, not a bug
here, and ingest continues past it (each province is caught independently
the same way run_pipeline.run_live_source() isolates whole-source failures).

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

# Full 77-province code->Thai-name map, derived from Thailand's canonical
# ADM1 boundary dataset (ADM1_PCODE "TH10" -> "10", ADM1_TH "กรุงเทพมหานคร").
# DDS's own f_prov parameter already used this same numeric scheme for the
# original 3 provinces (10/11/24 below, confirmed matching) -- widening
# this dict assumes (not yet live-verified) the other 74 codes work the
# same way against DDS's endpoint.
DDS_PROVINCE_NAMES = {
    "10": "กรุงเทพมหานคร", "11": "สมุทรปราการ", "12": "นนทบุรี", "13": "ปทุมธานี",
    "14": "พระนครศรีอยุธยา", "15": "อ่างทอง", "16": "ลพบุรี", "17": "สิงห์บุรี",
    "18": "ชัยนาท", "19": "สระบุรี", "20": "ชลบุรี", "21": "ระยอง", "22": "จันทบุรี",
    "23": "ตราด", "24": "ฉะเชิงเทรา", "25": "ปราจีนบุรี", "26": "นครนายก",
    "27": "สระแก้ว", "30": "นครราชสีมา", "31": "บุรีรัมย์", "32": "สุรินทร์",
    "33": "ศรีสะเกษ", "34": "อุบลราชธานี", "35": "ยโสธร", "36": "ชัยภูมิ",
    "37": "อำนาจเจริญ", "38": "บึงกาฬ", "39": "หนองบัวลำภู", "40": "ขอนแก่น",
    "41": "อุดรธานี", "42": "เลย", "43": "หนองคาย", "44": "มหาสารคาม",
    "45": "ร้อยเอ็ด", "46": "กาฬสินธุ์", "47": "สกลนคร", "48": "นครพนม",
    "49": "มุกดาหาร", "50": "เชียงใหม่", "51": "ลำพูน", "52": "ลำปาง",
    "53": "อุตรดิตถ์", "54": "แพร่", "55": "น่าน", "56": "พะเยา", "57": "เชียงราย",
    "58": "แม่ฮ่องสอน", "60": "นครสวรรค์", "61": "อุทัยธานี", "62": "กำแพงเพชร",
    "63": "ตาก", "64": "สุโขทัย", "65": "พิษณุโลก", "66": "พิจิตร", "67": "เพชรบูรณ์",
    "70": "ราชบุรี", "71": "กาญจนบุรี", "72": "สุพรรณบุรี", "73": "นครปฐม",
    "74": "สมุทรสาคร", "75": "สมุทรสงคราม", "76": "เพชรบุรี", "77": "ประจวบคีรีขันธ์",
    "80": "นครศรีธรรมราช", "81": "กระบี่", "82": "พังงา", "83": "ภูเก็ต",
    "84": "สุราษฎร์ธานี", "85": "ระนอง", "86": "ชุมพร", "90": "สงขลา", "91": "สตูล",
    "92": "ตรัง", "93": "พัทลุง", "94": "ปัตตานี", "95": "ยะลา", "96": "นราธิวาส",
}
DDS_FULL_YEAR_RANGES = ("1-53", "1-52")  # a finished year is weeks 1-53, or 1-52 in a 52-week year
DDS_MIN_DELAY_S = 0.6  # courtesy throttle across 77 sequential requests, matching ingest_api_diw.py's convention


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

    failed = []
    for i, (province_code, province_name) in enumerate(DDS_PROVINCE_NAMES.items()):
        if i > 0:
            time.sleep(DDS_MIN_DELAY_S)
        try:
            content = _fetch_province_pdf(session, token, province_code, year_ce, week_range)
        except Exception as exc:  # noqa: BLE001 -- one bad province code must not abort the other 76
            failed.append(province_code)
            print(f"[ingest_api_dds] {province_name} ({province_code}) year {year_ce}: FAILED, skipping ({type(exc).__name__}: {exc})")
            continue
        key, is_new = landing_store.save_version("dds", f"{year_ce}_{province_code}", "pdf", content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_dds] {province_name} ({province_code}) year {year_ce}: {status}: {key}")

    if failed:
        print(f"[ingest_api_dds] {len(failed)}/{len(DDS_PROVINCE_NAMES)} province codes failed (unverified beyond the "
              f"original 3): {failed}")


if __name__ == "__main__":
    run()
