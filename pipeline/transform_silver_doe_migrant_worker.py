"""Pivots bronze.doe_migrant_worker_monthly's EAV rows (one row per table x
zone x group x sex) back into silver.doe_migrant_worker_permit_monthly's
(zone, category, nationality) grain -- see sql/silver/23's header.

Category vs. nationality interpretation of a table's "group" column is
decided generically, not from a hardcoded table-number map (Bronze's own
header documents why: these category columns are tied to dated cabinet
resolutions and change every time one is superseded):
  - Every table in scope shares one fixed boilerplate title prefix
    ("...ที่ได้รับอนุญาตทำงานคงเหลือทั่วราชอาณาจักร"). Table 2 (the
    overview table) has NOTHING after that prefix -- it is itself a
    breakdown BY permit category, so each group label (e.g. "มาตรา 59
    MOU") becomes permit_category, nationality=NULL.
  - Every other table's title has something after that prefix (e.g.
    "(มาตรา 59 MOU)", or, with no parens at all, "มาตรา 63/2 ต่ออายุมติ
    ครม. 8 ก.ค 68") -- confirmed live this is NOT reliably wrapped in
    parens, so presence of "(" cannot be the signal. Whenever a suffix
    exists, the table is scoped to that ONE category and its group labels
    are nationalities -- the "ทั้งหมด" (all-nationalities) row becomes the
    nationality=NULL total row, matching the first case's semantics.

Raw category text is then normalized to the 8 official permit categories
under the Alien Employment Management Emergency Decree B.E. 2560 (as
amended B.E. 2561): มาตรา 59 ทั่วไป, มาตรา 59 MOU, มาตรา 61, มาตรา 62,
มาตรา 63, มาตรา 63/1, มาตรา 63/2, มาตรา 64 (see _canonical_category()).
Table 2 on its own already has several raw sub-columns per official
category (e.g. three under มาตรา 62: Single Window / กฎหมายอื่น /
สงเสริมการลงทุน -- the official definition explicitly groups all of these
under section 62), so category-level (nationality=NULL) totals are summed
across every table-2 sub-column that normalizes to the same official
category, using table 2's own values exclusively -- a detail table's own
"ทั้งหมด" (all-nationalities) row for that same category is NOT also
counted, since it would just double the same underlying figure table 2
already reports directly (confirmed live: every detail table's "ทั้งหมด"
row sits under a title-suffix that maps to a raw category already present
as one of table 2's own columns). Detail tables are read only for their
actual per-nationality rows (nationality != "ทั้งหมด").

มาตรา 63/2 carries one extra wrinkle: table 2 has a bare "มาตรา 63/2" /
"มาตรา 63/2 คนต่างด้าวตามมติคณะรัฐมนตรี (ข้อมูลเดิมกรมการจัดหางาน)" column
explicitly labeled as old/legacy DOE data, alongside several
date-stamped Cabinet Resolution round columns (e.g. "มาตรา 63/2
ต่ออายุมติ ครม. 8 ก.ค 68"). The legacy column is excluded --
_canonical_category() returns None for it -- in favor of summing the
date-stamped rounds, which collectively represent the current registered
total under that section.
"""

import os
import re

import pymysql

CATEGORY_ALL_NATIONALITIES_LABEL = "ทั้งหมด"
CATEGORY_GRAND_TOTAL_LABEL = "รวมทั้งสิ้น"
ZONE_NUM_RE = re.compile(r"(\d+)\s*$")
REPORT_DATE_RE = re.compile(r"เดือน\s*(\S+)\s*(\d{4})")
TITLE_BOILERPLATE_PREFIX = "จำนวนคนต่างด้าวที่ได้รับอนุญาตทำงานคงเหลือทั่วราชอาณาจักร"
SECTION_RE = re.compile(r"^มาตรา\s*(\d+)(/\d+)?")
PROVINCE_OFFICE_PREFIX = "สำนักงานจัดหางานจังหวัด"
# Reuses each province's own TIS-1099 province code as its zone_id -- distinct
# from BMA's 1-10 zone numbering by construction (no BMA zone is ever >= 11),
# so both schemes share dim_bma_zone.zone_id unambiguously. See
# transform_gold_dimensions.py's _build_dim_bma_zone() for the matching
# dim_bma_zone/bridge_bma_zone_district rows this resolves against.
PROVINCE_ZONE_ID = {"สมุทรปราการ": 11, "ฉะเชิงเทรา": 24}

# This PDF's text layer decomposes SARA AM into NIKHAHIT+SARA AA and
# reassigns tone marks to inconsistent Private Use Area codepoints per font
# subset -- see extract_load_api_doe_migrant_worker.py's _strip_marks for
# the full explanation. Thai month names carry tone marks too (e.g.
# กุมภาพันธ์ ends in a thanthakhat), so matching them needs the same
# normalization.
_THAI_MARK_RE = re.compile("[ัิ-ฺ็-๎-]")


def _strip_marks(s: str) -> str:
    s = (s or "").replace("ำ", "ํา")
    return _THAI_MARK_RE.sub("", s)


_THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
_THAI_MONTHS_STRIPPED = {_strip_marks(name): num for name, num in _THAI_MONTHS.items()}
_TITLE_BOILERPLATE_STRIPPED = _strip_marks(TITLE_BOILERPLATE_PREFIX)


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _parse_report_month(report_title: str) -> tuple[int, int] | None:
    """-> (report_year_ce, report_month_num), or None if unparseable."""
    m = REPORT_DATE_RE.search(report_title or "")
    if not m:
        return None
    month_num = _THAI_MONTHS_STRIPPED.get(_strip_marks(m.group(1)))
    if month_num is None:
        return None
    year_be = int(m.group(2))
    return year_be - 543, month_num


def _strip_boilerplate_prefix(title: str) -> str | None:
    """-> the text after the fixed boilerplate prefix (possibly ""), or
    None if the prefix isn't found at all (unexpected title shape). Walks
    raw characters one at a time rather than slicing by a fixed length,
    since this PDF's font-level mangling changes how many raw characters a
    given run of mark-stripped text corresponds to from title to title."""
    t = title or ""
    for i in range(1, len(t) + 1):
        stripped = _strip_marks(t[:i])
        if stripped == _TITLE_BOILERPLATE_STRIPPED:
            return t[i:].strip()
        if len(stripped) > len(_TITLE_BOILERPLATE_STRIPPED):
            return None
    return None


def _resolve_zone_id(zone_label: str) -> int | None:
    """-> BMA zone number (1-10) for a Bangkok zone row, the matching
    province code (11/24) for a Samut Prakan/Chachoengsao province-office
    row, or None (the Bangkok-wide/ปริมณฑล/ภาคกลาง/other-province subtotal
    rows this source isn't scoped to -- see module docstring)."""
    stripped = _strip_marks(zone_label or "")
    zone_m = ZONE_NUM_RE.search(stripped)
    if zone_m:
        return int(zone_m.group(1))
    prefix = _strip_marks(PROVINCE_OFFICE_PREFIX)
    if stripped.startswith(prefix):
        province_name = stripped[len(prefix):].strip()
        for name, zid in PROVINCE_ZONE_ID.items():
            if _strip_marks(name) == province_name:
                return zid
    return None


def _category_and_nationality(table_title: str, group_label: str) -> tuple[str, str | None, bool]:
    """-> (raw_category_text, nationality, is_overview). is_overview=True
    means this row came from table 2 directly (the zone x category
    breakdown) -- see module docstring for why only table-2 rows feed the
    nationality=NULL category totals."""
    suffix = _strip_boilerplate_prefix(table_title)
    if not suffix:
        # Boilerplate not found, or found with nothing after it (table 2's
        # own title) -- either way, this table is itself a category
        # breakdown, not a nationality one.
        return group_label, None, True
    if suffix.startswith("(") and suffix.endswith(")"):
        suffix = suffix[1:-1]  # cosmetic only -- strip one outer paren layer, keep any nested ones
    nationality = None if group_label == CATEGORY_ALL_NATIONALITIES_LABEL else group_label
    return suffix, nationality, False


def _canonical_category(raw_label: str) -> str | None:
    """-> one of the 8 official permit categories, or None if raw_label
    isn't a permit-category row (the grand total, or มาตรา 63/2's legacy
    baseline column -- see module docstring for both)."""
    s = _strip_marks(raw_label or "").strip()
    m = SECTION_RE.match(s)
    if not m:
        return None
    section, sub = m.group(1), m.group(2) or ""
    if section == "59":
        return "มาตรา 59 MOU" if "mou" in s.lower() else "มาตรา 59 ทั่วไป"
    if section == "61":
        return "มาตรา 61"
    if section == "62":
        return "มาตรา 62"
    if section == "63" and sub == "/1":
        return "มาตรา 63/1"
    if section == "63" and sub == "/2":
        if "ขอมูลเดิม" in s or s == "มาตรา 63/2":
            return None  # legacy baseline, superseded by the date-stamped rounds
        return "มาตรา 63/2"
    if section == "63":
        return "มาตรา 63"
    if section == "64":
        return "มาตรา 64"
    return None


def run() -> None:
    bronze_conn = _connect("bronze")
    silver_conn = _connect("silver")

    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_report_title, raw_table_title, raw_zone_label, raw_group_label, raw_sex_label, raw_value "
            "FROM doe_migrant_worker_monthly"
        )
        bronze_rows = bcur.fetchall()
    bronze_conn.close()

    # Report period is resolved per ROW (not once globally) since bronze now
    # carries multiple report months at once -- one extract_load_api_doe_
    # migrant_worker.py pass per landed PDF, all landing into the same
    # table (see that module's HISTORY note). Memoized since every row
    # from the same PDF shares the same raw_report_title string.
    _period_cache: dict[str, tuple[int, int] | None] = {}

    def period_of(report_title: str) -> tuple[int, int] | None:
        if report_title not in _period_cache:
            _period_cache[report_title] = _parse_report_month(report_title)
        return _period_cache[report_title]

    pivoted = {}  # (zone_id, year_ce, month_num, canonical_category, nationality) -> {sex_label: int_value}
    unparseable_periods = 0
    unresolved_zones = 0

    for report_title, table_title, zone_label, group_label, sex_label, value in bronze_rows:
        period = period_of(report_title)
        if period is None:
            unparseable_periods += 1
            continue
        year_ce, month_num = period

        zone_id = _resolve_zone_id(zone_label)
        if zone_id is None:
            unresolved_zones += 1
            continue  # Bangkok-wide/ปริมณฑล/ภาคกลาง/other-province subtotal row, out of scope (see module docstring)

        raw_category, nationality, is_overview = _category_and_nationality(table_title, group_label)
        if nationality is None and raw_category == CATEGORY_GRAND_TOTAL_LABEL:
            continue  # table 2's own grand-total-across-categories row, exactly the sum of every other category -- same convention as the zone grand-total exclusion above
        if not is_overview and nationality is None:
            continue  # a detail table's own "ทั้งหมด" row -- same figure as one of table 2's own columns, see module docstring; only table-2 rows feed category totals

        category = _canonical_category(raw_category)
        if category is None:
            continue  # unparseable, or มาตรา 63/2's excluded legacy baseline column

        key = (zone_id, year_ce, month_num, category, nationality)
        bucket = pivoted.setdefault(key, {})
        bucket[sex_label] = bucket.get(sex_label, 0) + int(value)

    if not pivoted:
        raise RuntimeError("transform_silver_doe_migrant_worker: pivoted 0 rows -- "
                            "check bronze.doe_migrant_worker_monthly has data and report titles parse")
    if unparseable_periods:
        print(f"[silver_doe_migrant_worker] WARNING: {unparseable_periods} bronze row(s) had an "
              f"unparseable report_title, skipped")

    rows = [
        (zone_id, year_ce, month_num, category, nationality,
         sexes.get("รวม", 0), sexes.get("ชาย", 0), sexes.get("หญิง", 0))
        for (zone_id, year_ce, month_num, category, nationality), sexes in pivoted.items()
    ]
    n_periods = len({(r[1], r[2]) for r in rows})

    insert_sql = (
        "INSERT INTO doe_migrant_worker_permit_monthly "
        "(zone_id, report_year_ce, report_month_num, permit_category, nationality, total, male, female) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with silver_conn.cursor() as scur:
        scur.executemany(insert_sql, rows)
    silver_conn.commit()
    silver_conn.close()
    print(f"[silver_doe_migrant_worker] doe_migrant_worker_permit_monthly: {len(rows)} rows "
          f"across {n_periods} report period(s) ({unresolved_zones} out-of-scope zone rows skipped)")


if __name__ == "__main__":
    run()
