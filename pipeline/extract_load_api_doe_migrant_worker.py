"""Loads bronze.doe_migrant_worker_monthly from every DOE PDF landed by
ingest_api_doe_migrant_worker.py (one row set per report month -- see
module-level HISTORY note below). Walks every table in each report's
"คงเหลือ" (remaining-permits) section -- stops once the "ได้รับอนุญาตทำงาน
ใหม่" (newly-permitted) section begins, confirmed live to start right
after the remaining-permits section's own table numbering resets to 1
again with a different title. Any table that has no matching area rows
(e.g. table 3's by-business-sector breakdown) is silently skipped -- this
makes the extraction robust to next month's exact table count/order
changing, since nothing here is hardcoded to a specific table number.

PROVINCE SCOPE (added 2026-11-04): this report is explicitly nationwide
("...ทั่วราชอาณาจักร") -- every table carries a "ปริมณฑล" (greater-Bangkok)
section with its own "สำนักงานจัดหางานจังหวัด<province>" row per province,
confirmed live to include both Samut Prakan and Chachoengsao (this
project's other 2 catchment provinces) with the exact same มาตรา-category
column structure as Bangkok's own 10 zones. Only those 2 are captured
here (PROVINCE_LABELS below) -- every other province's row is left
unextracted, this isn't a general nationwide ingest.

HISTORY (added 2026-11-04): processes every PDF currently landed (see
ingest_api_doe_migrant_worker.py's own history-window note for why that's
a ~20-month rolling window, not the 10 years this project would otherwise
target -- a real limit of what DOE's own listing page publishes, not a
scope cut made here).
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
_PROVINCE_OFFICE_PREFIX = "สำนักงานจัดหางานจังหวัด"
# Only this project's other 2 catchment provinces -- not a general
# nationwide capture, see module docstring's PROVINCE SCOPE note.
PROVINCE_LABELS = {"สมุทรปราการ", "ฉะเชิงเทรา"}
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


# ZONE_RE/PROVINCE_RE are built from already-mark-stripped literals so
# matching can compare like-for-like against zone_label after it too goes
# through _strip_marks (see the .match calls below) -- the raw literals
# above use composed "ำ", but this PDF's text layer always extracts the
# decomposed form, so a direct match against the raw literal silently
# matches nothing.
ZONE_RE = re.compile(_strip_marks(_ZONE_LABEL_PREFIX) + r"\s*(\d+)$")
_PROVINCE_LABELS_STRIPPED = {_strip_marks(p) for p in PROVINCE_LABELS}
PROVINCE_RE = re.compile(
    _strip_marks(_PROVINCE_OFFICE_PREFIX) + r"\s*(" + "|".join(_PROVINCE_LABELS_STRIPPED) + r")\s*$"
)


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


# No single category/zone/sex cell in this report plausibly exceeds this --
# the largest real figure seen live is the nationwide grand total column
# (~4.2 million, itself excluded upstream) -- confirmed live a value this
# large (one cell: 2,810,251,410) is a pdfplumber column-extraction glitch
# on a specific province row/table combination, not a real count.
_MAX_PLAUSIBLE_VALUE = 10_000_000


def _clean_number(s: str) -> str | None:
    """Strips thousands-commas AND any stray internal whitespace -- confirmed
    live that pdfplumber occasionally splits one number across two text
    fragments on this PDF's narrower columns (e.g. "3 9,405" -> "39405"),
    never a legitimate feature of these comma-grouped figures. -> None (not
    "0") for a value outside _MAX_PLAUSIBLE_VALUE, so the caller can skip
    the cell and warn rather than silently writing 0 or a huge garbage
    number into a real worker-count column."""
    s = (s or "").strip()
    if s in ("", "-"):
        return "0"
    cleaned = re.sub(r"\s+", "", s).replace(",", "")
    try:
        if abs(int(cleaned)) > _MAX_PLAUSIBLE_VALUE:
            return None
    except ValueError:
        return None
    return cleaned


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


def _extract_pdf(key: str, batch_id: str) -> list[tuple]:
    """-> bronze row tuples for one landed PDF."""
    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()

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
                stripped_label = _strip_marks(zone_label)
                is_area = (
                    ZONE_RE.match(stripped_label) or PROVINCE_RE.match(stripped_label)
                    or stripped_label == _strip_marks(BKK_TOTAL_ZONE)
                )
                if not is_area:
                    continue
                for col_idx, (group_label, sex_label) in enumerate(col_map, start=1):
                    if col_idx >= len(row) or group_label is None or sex_label is None:
                        continue
                    value = row[col_idx]
                    if value is None:
                        continue
                    cleaned = _clean_number(value)
                    if cleaned is None:
                        print(f"[extract_load_api_doe_migrant_worker] {key}: WARNING: implausible value "
                              f"{value!r} for zone={zone_label!r} group={group_label!r} sex={sex_label!r} "
                              f"(table {current_table_num}), skipping this cell")
                        continue
                    rows_out.append((
                        "doe_migrant_worker", key, len(rows_out) + 1, file_hash, batch_id, "DOE_MIGRANT_WORKER",
                        report_title, current_table_num, current_table_title, zone_label, group_label, sex_label,
                        cleaned,
                    ))

    if not rows_out:
        # Older reports in the history window can use a layout this
        # extraction doesn't recognize at all (confirmed live: the oldest
        # available report, 2567-06, yields 0 rows -- a real source-side
        # format difference, not a bug in a specific row's data). Warn and
        # skip that one report rather than losing every other month over
        # it -- see run()'s own "zero PDFs succeeded" check for the actual
        # hard-failure condition.
        print(f"[extract_load_api_doe_migrant_worker] {key}: WARNING: extracted 0 rows -- "
              f"this report's PDF layout may differ from newer ones, skipping it")
        return []
    print(f"[extract_load_api_doe_migrant_worker] {key}: {len(rows_out)} rows (report: {report_title!r})")
    return rows_out


def run() -> None:
    keys = landing_store.list_prefix("doe_migrant_worker")
    if not keys:
        print("[extract_load_api_doe_migrant_worker] no landed objects found, skipping "
              "(run ingest_api_doe_migrant_worker first)")
        return

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"doe_migrant_worker_load_{loaded_at:%Y%m%dT%H%M%S}"

    all_rows: list[tuple] = []
    n_ok = 0
    for key in sorted(keys):
        rows = _extract_pdf(key, batch_id)
        if rows:
            n_ok += 1
        all_rows.extend(rows)

    if n_ok == 0:
        raise RuntimeError("extract_load_api_doe_migrant_worker: every landed PDF extracted 0 rows -- "
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
        for row in all_rows:
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
          f"from {n_ok}/{len(keys)} report(s) ({len(keys) - n_ok} skipped, 0 rows extracted)")


if __name__ == "__main__":
    run()
