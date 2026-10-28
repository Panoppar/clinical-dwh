"""Loads bronze.dopa_population_year from the DOPA files landed by
ingest_api_dopa_population.py -- the plain nationwide count file (which
carries numeric province/district/tambon codes but only MALE/FEMALE/TOTAL)
and the 3 target provinces' per-province age-breakdown files (single year
of age x sex, but NO codes -- areas identified by name only).

Code resolution works mainly by POSITION, not name-matching: confirmed
live that both files normally list each province's areas in the identical
order (province row, then every district row, then every subdistrict row
under it) with identical row counts per province (231 rows for Bangkok in
both). Walking them in lockstep lets every age-breakdown row inherit its
area's code from the plain file's row at the same position, with no fuzzy
text matching needed for the common case -- name comparison is used only
to detect and resync past the rare row the two files disagree on (see
run()'s two-pointer loop; confirmed live this happens for exactly one
subdistrict in Chachoengsao, missing from the age-breakdown file only).

Age bands are aggregated here (not landed as single-year-of-age EAV rows)
because bronze.dopa_population_year's column shape (raw_fine_male_0_4 etc.)
already matches what sql/silver/21 + pipeline/transform_silver_dopa_population.py
expect, inherited from kmch-ml's original pre-aggregated CSV export (kmch-ml
input-parity gap 1) -- keeping that shape means this is the only file that
needs to change for Bronze and Silver to keep working unmodified, and a true
single-year-of-age EAV table would be ~100x more rows for data nothing
downstream consumes at that grain.

Unit codes are resolved from bronze.tambon_xwalk directly, not
gold.dim_tambon_unit_xwalk (a straight copy of the same rows) -- this lets
this source run in the normal Bronze-phase position alongside every other
live source, with no dependency on Gold already being built. That
dependency would otherwise be circular: transform_gold_dimensions.
_build_dim_date() reads silver.dopa_population_by_unit_year's year range,
and needs to run before _build_dim_tambon_unit_xwalk() populates
gold.dim_area's FK target within that same function.
"""

import hashlib
import os
import re
from datetime import datetime, timezone

import pymysql

import landing_store

# Strips administrative-level prefixes so e.g. "อำเภอบ้านโพธิ์" (district)
# and "ตำบลบ้านโพธิ์" (subdistrict) both normalize to "บ้านโพธิ์" for name
# comparison during resync -- this makes same-named district/subdistrict
# pairs (a real, common pattern: a district's seat subdistrict often shares
# its name) compare as distinct only via their surrounding position, not
# spuriously via leftover prefix text.
_LEVEL_PREFIX_RE = re.compile(r"^(ตำบล|อำเภอ|แขวง|เขต|ท้องถิ่น|เทศบาล|จังหวัด)+")


def _norm_name(s: str) -> str:
    return _LEVEL_PREFIX_RE.sub("", (s or "").strip()).strip()


def _plain_area_name(fields: list[str]) -> str:
    if fields[5] != "0":
        return fields[6]  # subdistrict
    if fields[3] != "0":
        return fields[4]  # district
    return fields[2]  # province


BATCH_SIZE = 2000
TARGET_PROVINCE_CODES = ["10", "11", "24"]

# Index ranges (inclusive) of single-year ages making up each band, applied
# to both the male and female age series -- see ingest_api_dopa_population.py
# for the field layout these indices are built from.
FINE_BAND_RANGES = [
    ("0_4", range(0, 5)), ("5_9", range(5, 10)), ("10_14", range(10, 15)),
    ("15_17", range(15, 18)), ("18_22", range(18, 23)), ("23_29", range(23, 30)),
    ("30_39", range(30, 40)), ("40_49", range(40, 50)), ("50_59", range(50, 60)),
    ("60_plus", range(60, 102)),
]
COARSE_BAND_RANGES = [
    ("0_14", range(0, 15)), ("15_59", range(15, 60)), ("60_plus", range(60, 102)),
]


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _to_int(s: str) -> int:
    s = (s or "").strip()
    if s in ("", "-"):
        return 0
    return int(s.replace(",", ""))


def _latest_key(stem_prefix: str):
    keys = [k for k in landing_store.list_prefix("dopa_population")
            if k.rsplit("/", 1)[-1].startswith(stem_prefix)]
    if not keys:
        return None
    return sorted(keys, key=lambda k: k.rsplit("__", 1)[-1])[-1]


def _load_tambon_lookup(bronze_conn) -> dict:
    # Reads bronze.tambon_xwalk directly rather than gold.dim_tambon_unit_xwalk
    # -- the latter is itself just this same table copied verbatim for these
    # 3 provinces (confirmed: transform_gold_dimensions._build_dim_tambon_unit_xwalk
    # does a straight SELECT with no transformation), but reading Bronze
    # directly means this source can run in the normal Bronze-phase position
    # alongside every other live source, with no dependency on Gold already
    # being built -- avoiding a real circular ordering problem (dim_date
    # needs silver.dopa_population_by_unit_year's year range, which needs
    # this table's bronze rows, which would otherwise need gold.dim_area to
    # exist first).
    with bronze_conn.cursor() as cur:
        cur.execute(
            "SELECT raw_tambon_code, raw_unit_code FROM tambon_xwalk "
            "WHERE raw_province_code IN ('10','11','24')"
        )
        return dict(cur.fetchall())


def _parse_plain_rows(text: str) -> list[list[str]]:
    return [line.split("|") for line in text.splitlines() if line.strip()]


def _age_band_sums(fields: list[str], sex_offset: int) -> tuple[dict, dict]:
    """sex_offset: 1 for male series, 2 for female series (see field layout
    note in ingest_api_dopa_population.py)."""
    fine = {}
    for label, ages in FINE_BAND_RANGES:
        fine[label] = sum(_to_int(fields[sex_offset + 2 * age]) for age in ages)
    coarse = {}
    for label, ages in COARSE_BAND_RANGES:
        coarse[label] = sum(_to_int(fields[sex_offset + 2 * age]) for age in ages)
    return fine, coarse


def run() -> None:
    plain_key = _latest_key("plain_")
    if plain_key is None:
        print("[extract_load_api_dopa_population] no landed plain-count object found, skipping "
              "(run ingest_api_dopa_population first)")
        return
    plain_content = landing_store.read_bytes(plain_key)
    plain_text = plain_content.decode("utf-8-sig")
    plain_rows = _parse_plain_rows(plain_text)
    plain_hash = hashlib.sha256(plain_content).hexdigest()

    bronze_conn = _connect("bronze")
    tambon_lookup = _load_tambon_lookup(bronze_conn)

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"dopa_population_load_{loaded_at:%Y%m%dT%H%M%S}"

    # Keyed by unit_code, not raw tambon_code: several original tambons
    # merge into one gold.dim_area unit (the 7 Bangkok post-2019 khwaeng
    # splits each have 2 tambon_codes sharing 1 unit_code -- confirmed by a
    # UNIQUE (unit_code, year) constraint violation on the first run before
    # this aggregation existed). DOPA's own files are per-original-tambon,
    # so those sibling rows must be summed into one here rather than landed
    # as separate Bronze rows for the same unit.
    accum = {}
    year_be = ref_month = yymm = None
    unmatched = 0

    for cc in TARGET_PROVINCE_CODES:
        age_key = _latest_key(f"age_{cc}_")
        if age_key is None:
            print(f"[extract_load_api_dopa_population] WARNING: no landed age-breakdown object "
                  f"for province {cc}, skipping that province")
            continue
        age_content = landing_store.read_bytes(age_key)
        age_lines = [l for l in age_content.decode("utf-8-sig").splitlines() if l.strip()]

        province_plain_rows = [r for r in plain_rows if r[1] == cc]
        age_names = [line.split("|", 1)[0] for line in age_lines]

        yymm = province_plain_rows[0][0]
        year_be, ref_month = int(yymm[:2]) + 2500, int(yymm[2:])

        # Confirmed live that the two files are normally in lockstep (same
        # row order, same row count), but not always -- Chachoengsao's
        # age-breakdown file is missing exactly one subdistrict row whose
        # name happens to equal its own district's name (ตำบลบ้านโพธิ์ under
        # อำเภอบ้านโพธิ์). A strict zip() would then misattribute every
        # following row by one position. Walking both lists with two
        # pointers and resyncing on a name mismatch (by checking whether
        # advancing just one side recovers alignment) tolerates a single
        # row being missing on either side instead of silently corrupting
        # everything after it.
        pi = ai = 0
        while pi < len(province_plain_rows) and ai < len(age_lines):
            plain_fields = province_plain_rows[pi]
            plain_name = _plain_area_name(plain_fields)
            age_name = age_names[ai]
            if _norm_name(plain_name) != _norm_name(age_name):
                if pi + 1 < len(province_plain_rows) and \
                        _norm_name(_plain_area_name(province_plain_rows[pi + 1])) == _norm_name(age_name):
                    print(f"[extract_load_api_dopa_population] WARNING: province {cc}: plain-file row "
                          f"{plain_name!r} has no counterpart in the age-breakdown file, skipping it "
                          f"(no age-band data available for it this run)")
                    pi += 1
                    continue
                if ai + 1 < len(age_lines) and _norm_name(plain_name) == _norm_name(age_names[ai + 1]):
                    print(f"[extract_load_api_dopa_population] WARNING: province {cc}: age-breakdown row "
                          f"{age_name!r} has no counterpart in the plain-count file, skipping it")
                    ai += 1
                    continue
                raise RuntimeError(
                    f"extract_load_api_dopa_population: province {cc}: cannot resync plain-file row "
                    f"{plain_name!r} (index {pi}) against age-breakdown row {age_name!r} (index {ai}) -- "
                    f"the two files have diverged by more than one row, see module docstring"
                )

            age_line = age_lines[ai]
            pi += 1
            ai += 1

            rcode_code, ccaatt_code = plain_fields[3], plain_fields[5]
            if rcode_code == "0" or ccaatt_code == "0":
                continue  # province- or district-level row, not needed (see module docstring)

            tambon_code = ccaatt_code[:6]
            unit_code = tambon_lookup.get(tambon_code)
            if unit_code is None:
                unmatched += 1
                continue

            age_fields = age_line.split("|")
            fine_male, coarse_male = _age_band_sums(age_fields, 1)
            fine_female, coarse_female = _age_band_sums(age_fields, 2)
            pop_male, pop_female, pop_total = (
                _to_int(age_fields[217]), _to_int(age_fields[218]), _to_int(age_fields[219])
            )

            unit_acc = accum.setdefault(unit_code, {
                "fine_male": {label: 0 for label, _ in FINE_BAND_RANGES},
                "fine_female": {label: 0 for label, _ in FINE_BAND_RANGES},
                "coarse_male": {label: 0 for label, _ in COARSE_BAND_RANGES},
                "coarse_female": {label: 0 for label, _ in COARSE_BAND_RANGES},
                "pop_male": 0, "pop_female": 0, "pop_total": 0,
            })
            for label, v in fine_male.items():
                unit_acc["fine_male"][label] += v
            for label, v in fine_female.items():
                unit_acc["fine_female"][label] += v
            for label, v in coarse_male.items():
                unit_acc["coarse_male"][label] += v
            for label, v in coarse_female.items():
                unit_acc["coarse_female"][label] += v
            unit_acc["pop_male"] += pop_male
            unit_acc["pop_female"] += pop_female
            unit_acc["pop_total"] += pop_total

    if not accum:
        raise RuntimeError("extract_load_api_dopa_population: extracted 0 rows -- "
                            "site layout may have changed, check manually before trusting this run")
    if unmatched:
        print(f"[extract_load_api_dopa_population] WARNING: {unmatched} subdistrict row(s) had no "
              f"matching bronze.tambon_xwalk.raw_tambon_code")

    rows_out = []
    for unit_code, a in accum.items():
        pop_age_known = sum(a["fine_male"].values()) + sum(a["fine_female"].values())
        pop_unknown_age = a["pop_total"] - pop_age_known
        rows_out.append((
            "dopa_population", plain_key, len(rows_out) + 1, plain_hash, batch_id, "DOPA_POPULATION",
            unit_code, str(year_be), str(ref_month),
            str(a["fine_male"]["0_4"]), str(a["fine_female"]["0_4"]),
            str(a["fine_male"]["5_9"]), str(a["fine_female"]["5_9"]),
            str(a["fine_male"]["10_14"]), str(a["fine_female"]["10_14"]),
            str(a["fine_male"]["15_17"]), str(a["fine_female"]["15_17"]),
            str(a["fine_male"]["18_22"]), str(a["fine_female"]["18_22"]),
            str(a["fine_male"]["23_29"]), str(a["fine_female"]["23_29"]),
            str(a["fine_male"]["30_39"]), str(a["fine_female"]["30_39"]),
            str(a["fine_male"]["40_49"]), str(a["fine_female"]["40_49"]),
            str(a["fine_male"]["50_59"]), str(a["fine_female"]["50_59"]),
            str(a["fine_male"]["60_plus"]), str(a["fine_female"]["60_plus"]),
            str(a["coarse_male"]["0_14"]), str(a["coarse_female"]["0_14"]),
            str(a["coarse_male"]["15_59"]), str(a["coarse_female"]["15_59"]),
            str(a["coarse_male"]["60_plus"]), str(a["coarse_female"]["60_plus"]),
            str(a["pop_male"]), str(a["pop_female"]), str(a["pop_total"]),
            str(pop_age_known), str(pop_unknown_age),
            f"live:stat.bora.dopa.go.th/{yymm}",
        ))

    insert_sql = (
        "INSERT INTO dopa_population_year "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, source_system, "
        "raw_unit_code, raw_year_be, raw_ref_month, "
        "raw_fine_male_0_4, raw_fine_female_0_4, raw_fine_male_5_9, raw_fine_female_5_9, "
        "raw_fine_male_10_14, raw_fine_female_10_14, raw_fine_male_15_17, raw_fine_female_15_17, "
        "raw_fine_male_18_22, raw_fine_female_18_22, raw_fine_male_23_29, raw_fine_female_23_29, "
        "raw_fine_male_30_39, raw_fine_female_30_39, raw_fine_male_40_49, raw_fine_female_40_49, "
        "raw_fine_male_50_59, raw_fine_female_50_59, raw_fine_male_60_plus, raw_fine_female_60_plus, "
        "raw_coarse_male_0_14, raw_coarse_female_0_14, raw_coarse_male_15_59, raw_coarse_female_15_59, "
        "raw_coarse_male_60_plus, raw_coarse_female_60_plus, "
        "raw_pop_male, raw_pop_female, raw_pop_total, raw_pop_age_known, raw_pop_unknown_age, raw_source_file) "
        "VALUES (" + ", ".join(["%s"] * 41) + ")"
    )
    with bronze_conn.cursor() as cur:
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
    bronze_conn.commit()
    bronze_conn.close()
    print(f"[extract_load_api_dopa_population] dopa_population_year: loaded {n} rows "
          f"({unmatched} unmatched tambon codes skipped)")


if __name__ == "__main__":
    run()
