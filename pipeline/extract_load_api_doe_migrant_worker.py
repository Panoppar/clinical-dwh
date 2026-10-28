"""Loads bronze.doe_migrant_worker_monthly from the latest DOE PDF landed
by ingest_api_doe_migrant_worker.py. Walks every table in the report's
"คงเหลือ" (remaining-permits) section -- stops once the "ได้รับอนุญาตทำงาน
ใหม่" (newly-permitted) section begins, confirmed live to start right
after the remaining-permits section's own table numbering resets to 1
again with a different title. Any table that has no Bangkok-zone rows
(e.g. table 3's by-business-sector breakdown) is silently skipped -- this
makes the extraction robust to next month's exact table count/order
changing, since nothing here is hardcoded to a specific table number.
"""

import hashlib
import io
import os
import re
from datetime import datetime, timezone

import pdfplumber
import pymysql

import landing_store

BATCH_SIZE = 2000
_ZONE_LABEL_PREFIX = "สำนักงานจัดหางานกรุงเทพมหานครพื้นที่"
TABLE_HEADER_RE = re.compile(r"ตารางที่\s*(\d+)\s+(.+)")
# Confirmed live: the cover-page title string doe.go.th shows on its listing
# page ("สถิติการทำงานของคนต่างด้าวประจำเดือน...") does not actually appear
# verbatim inside the PDF body -- the PDF instead stamps every table page
# with "ข้อมูล ณ เดือน <month> <year(BE)>", which is what we key off of.
REPORT_DATE_RE = re.compile(r"เดือน\s*(\S+)\s*(\d{4})")
BKK_TOTAL_ZONE = "กรุงเทพมหานคร"
SEX_LABELS = {"รวม", "ชาย", "หญิง"}

# This PDF's embedded Thai font subsets reassign combining vowels/tone marks
# to Private Use Area codepoints, inconsistently per subset (confirmed live:
# mai ek alone shows up as both U+F70A and U+F705 in different tables of the
# same file). Stripping every combining mark -- real Unicode range (U+0E31,
# U+0E34-U+0E3A, U+0E47-U+0E4E) or PUA (U+F700-U+F7FF) -- from both sides
# before substring-matching sidesteps needing an exact per-codepoint table,
# and is safe here because none of the words being matched differ only by a
# combining mark.
_THAI_MARK_RE = re.compile("[ัิ-ฺ็-๎-]")


def _strip_marks(s: str) -> str:
    # Separately (not a font bug): this PDF spells SARA AM using the legacy
    # decomposed form NIKHAHIT+SARA AA instead of the precomposed U+0E33
    # used in ordinary typed Thai -- confirmed live ("thamngan" always
    # extracts with the decomposed vowel). Decomposing it the same way in
    # our own literals before stripping marks puts both sides on equal
    # footing (the nikhahit then strips out like any other mark).
    s = (s or "").replace("ำ", "ํา")
    return _THAI_MARK_RE.sub("", s)


def _strip_continuation_suffix(title: str) -> str:
    """A multi-page table's continuation pages repeat the same title with a
    trailing "(ต่อ)" ("continued") -- confirmed live that it's appended to
    the FULL title (e.g. "...ทั่วราชอาณาจักร (ต่อ)"), not a bare "(ต่อ)" on
    its own, so a prefix/equality check against the whole title can't
    detect it; a suffix-window search independent of exact length handles
    this PDF's per-subset PUA re-encoding of "่" the same way _strip_marks
    does elsewhere."""
    target = _strip_marks("(ต่อ)")
    t = (title or "").rstrip()
    for n in range(4, 8):
        if len(t) < n:
            break
        if _strip_marks(t[-n:]) == target:
            return t[:-n].rstrip()
    return t


# ZONE_RE is built from the already-mark-stripped prefix so matching can
# compare like-for-like against zone_label after it too goes through
# _strip_marks (see the ZONE_RE.match call below) -- the raw literal above
# uses composed "ำ", but this PDF's text layer always extracts the
# decomposed form, so a direct match against the raw literal silently
# matches nothing.
ZONE_RE = re.compile(_strip_marks(_ZONE_LABEL_PREFIX) + r"\s*(\d+)$")


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _clean_number(s: str) -> str:
    """Strips thousands-commas AND any stray internal whitespace -- confirmed
    live that pdfplumber occasionally splits one number across two text
    fragments on this PDF's narrower columns (e.g. "3 9,405" -> "39405"),
    never a legitimate feature of these comma-grouped figures."""
    s = (s or "").strip()
    if s in ("", "-"):
        return "0"
    return re.sub(r"\s+", "", s).replace(",", "")


def _build_column_map(header_rows: list[list]) -> list[tuple[str, str]]:
    """header_rows = the table's first 2 rows (group-label row with merged
    cells as None, then sex-label row). -> [(group_label, sex_label), ...]
    aligned 1:1 with every data column after the first (zone-label) column."""
    group_row, sex_row = header_rows[0][1:], header_rows[1][1:]
    groups = []
    last = None
    for cell in group_row:
        if cell:
            last = cell.strip()
        groups.append(last)
    # Keep the sex label in its original (unstripped) spelling for storage
    # -- _strip_marks is only for matching against SEX_LABELS below.
    sexes = [c.strip() if c else None for c in sex_row]
    return list(zip(groups, sexes))


def _looks_like_header(rows: list[list]) -> bool:
    if len(rows) < 2:
        return False
    sex_row = rows[1][1:]
    non_null = [_strip_marks(c.strip()) for c in sex_row if c]
    return bool(non_null) and all(c in {_strip_marks(x) for x in SEX_LABELS} for c in non_null)


def run() -> None:
    # latest_version() needs a fixed stem, but this source's stem varies by
    # report month -- list the whole prefix and take the most recently
    # written object instead. Keys are "<stem>__<YYYYMMDD>_<hash>.pdf";
    # sorting lands on the latest date for same-month re-runs too.
    keys = landing_store.list_prefix("doe_migrant_worker")
    if not keys:
        print("[extract_load_api_doe_migrant_worker] no landed object found, skipping "
              "(run ingest_api_doe_migrant_worker first)")
        return
    key = sorted(keys, key=lambda k: k.rsplit("__", 1)[-1])[-1]

    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"doe_migrant_worker_load_{loaded_at:%Y%m%dT%H%M%S}"

    rows_out = []
    report_title = None
    current_table_num, current_table_title = None, None
    max_table_num_seen = 0
    stopped = False

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            if stopped:
                break
            text = page.extract_text() or ""
            if report_title is None:
                date_m = REPORT_DATE_RE.search(text)
                if date_m:
                    report_title = f"เดือน {date_m.group(1)} {date_m.group(2)}"

            m = TABLE_HEADER_RE.search(text)
            if m:
                table_num = m.group(1)
                raw_title = m.group(2).strip()
                # The "คงเหลือ" (remaining-permits) section numbers its tables
                # 1..20 contiguously; the following "ได้รับอนุญาตทำงานใหม่"
                # (newly-permitted) section restarts at 1. Table 1 itself is
                # a dual overview that cycles between both framings on pages
                # 10-12 (before 2..20 even start), so a number *reset* -- not
                # a title-text match -- is the only boundary signal immune to
                # that overview and to this PDF's font-level Thai mangling.
                if table_num == "1" and max_table_num_seen > 1:
                    stopped = True
                    break
                # A multi-page table's continuation pages repeat the same
                # "ตารางที่ N" header with a trailing "(ต่อ)" ("continued")
                # appended to the title -- confirmed live (table 2 spans
                # pages 15 and 17). Strip it so downstream Silver parsing
                # doesn't misread the suffix as a real category name (it's
                # parenthesized, just like "(มาตรา 59 MOU)" is).
                current_table_title = _strip_continuation_suffix(raw_title)
                current_table_num = table_num
                try:
                    max_table_num_seen = max(max_table_num_seen, int(table_num))
                except ValueError:
                    pass

            tables = page.extract_tables()
            if not tables:
                continue
            table = tables[0]
            if not _looks_like_header(table):
                continue  # this page's table isn't zone/group/sex-shaped (e.g. by-business-sector)

            col_map = _build_column_map(table[:2])
            for row in table[2:]:
                if not row or not row[0]:
                    continue
                zone_label = row[0].strip().replace("\n", "")
                is_zone = ZONE_RE.match(_strip_marks(zone_label)) or _strip_marks(zone_label) == _strip_marks(BKK_TOTAL_ZONE)
                if not is_zone:
                    continue
                for col_idx, (group_label, sex_label) in enumerate(col_map, start=1):
                    if col_idx >= len(row) or group_label is None or sex_label is None:
                        continue
                    value = row[col_idx]
                    if value is None:
                        continue
                    rows_out.append((
                        "doe_migrant_worker", key, len(rows_out) + 1, file_hash, batch_id, "DOE_MIGRANT_WORKER",
                        report_title, current_table_num, current_table_title, zone_label, group_label, sex_label,
                        _clean_number(value),
                    ))

    if not rows_out:
        raise RuntimeError("extract_load_api_doe_migrant_worker: extracted 0 rows -- "
                            "PDF layout may have changed, check manually before trusting this run")

    insert_sql = (
        "INSERT INTO doe_migrant_worker_monthly "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, source_system, "
        "raw_report_title, raw_table_number, raw_table_title, raw_zone_label, raw_group_label, raw_sex_label, raw_value) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    conn = _connect()
    with conn.cursor() as cur:
        n = 0
        batch = []
        for row in rows_out:
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                cur.executemany(insert_sql, batch)
                n += len(batch)
                batch.clear()
        if batch:
            cur.executemany(insert_sql, batch)
            n += len(batch)
    conn.commit()
    conn.close()
    print(f"[extract_load_api_doe_migrant_worker] doe_migrant_worker_monthly: loaded {n} rows "
          f"from {key} (report: {report_title!r})")


if __name__ == "__main__":
    run()
