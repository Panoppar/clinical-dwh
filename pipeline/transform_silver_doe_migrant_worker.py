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
"""

import os
import re

import pymysql

CATEGORY_ALL_NATIONALITIES_LABEL = "ทั้งหมด"
CATEGORY_GRAND_TOTAL_LABEL = "รวมทั้งสิ้น"
ZONE_NUM_RE = re.compile(r"(\d+)\s*$")
REPORT_DATE_RE = re.compile(r"เดือน\s*(\S+)\s*(\d{4})")
TITLE_BOILERPLATE_PREFIX = "จำนวนคนต่างด้าวที่ได้รับอนุญาตทำงานคงเหลือทั่วราชอาณาจักร"

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


def _category_and_nationality(table_title: str, group_label: str) -> tuple[str, str | None]:
    suffix = _strip_boilerplate_prefix(table_title)
    if not suffix:
        # Boilerplate not found, or found with nothing after it (table 2's
        # own title) -- either way, this table is itself a category
        # breakdown, not a nationality one.
        return group_label, None
    if suffix.startswith("(") and suffix.endswith(")"):
        suffix = suffix[1:-1]  # cosmetic only -- strip one outer paren layer, keep any nested ones
    nationality = None if group_label == CATEGORY_ALL_NATIONALITIES_LABEL else group_label
    return suffix, nationality


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

    report_period = None
    pivoted = {}  # (zone_id, category, nationality) -> {sex_label: int_value}

    for report_title, table_title, zone_label, group_label, sex_label, value in bronze_rows:
        if report_period is None:
            report_period = _parse_report_month(report_title)

        zone_m = ZONE_NUM_RE.search(zone_label or "")
        if not zone_m:
            continue  # Bangkok-wide grand-total row, excluded (see sql/silver/23 header)
        zone_id = int(zone_m.group(1))

        category, nationality = _category_and_nationality(table_title, group_label)
        if nationality is None and category == CATEGORY_GRAND_TOTAL_LABEL:
            continue  # table 2's own grand-total-across-categories row, exactly the sum of every other category -- same convention as the zone grand-total exclusion above
        key = (zone_id, category, nationality)
        pivoted.setdefault(key, {})[sex_label] = int(value)

    if report_period is None:
        raise RuntimeError("transform_silver_doe_migrant_worker: could not parse report month/year "
                            "from bronze.doe_migrant_worker_monthly.raw_report_title")
    report_year_ce, report_month_num = report_period

    rows = [
        (zone_id, report_year_ce, report_month_num, category, nationality,
         sexes.get("รวม", 0), sexes.get("ชาย", 0), sexes.get("หญิง", 0))
        for (zone_id, category, nationality), sexes in pivoted.items()
    ]

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
          f"(report period {report_year_ce}-{report_month_num:02d})")


if __name__ == "__main__":
    run()
