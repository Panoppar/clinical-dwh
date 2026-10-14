"""
Silver transform for NSO population registration + labor force survey.

Parses pop_reg_structure_metadata's raw SDMX-ML XML generically into
silver.pop_indicator_lookup (every codelist, not just the ones used here),
then uses that lookup to decode indicator/age/province names for
population_reference_age_sex, and transforms pop_sur_survey into
labor_force_survey.
"""

import os
import re
from datetime import datetime, timezone

import pymysql

CODE_BLOCK_RE = re.compile(r'<structure:Code id="([^"]+)">(.*?)</structure:Code>', re.S)
CODELIST_RE = re.compile(r'<structure:Codelist id="([^"]+)"[^>]*>(.*?)</structure:Codelist>', re.S)
NAME_EN_RE = re.compile(r'<common:Name xml:lang="en">([^<]*)</common:Name>')
NAME_TH_RE = re.compile(r'<common:Name xml:lang="th">([^<]*)</common:Name>')

AGE_RE_EXACT = re.compile(r"^Y(\d+)$")
AGE_RE_BUCKET = re.compile(r"^Y_(LE|GE|GT|LT)(\d+)$")


def _connect(database="silver"):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def load_pop_indicator_lookup(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT raw_xml FROM bronze.pop_reg_structure_metadata LIMIT 1")
        (raw_xml,) = cur.fetchone()

    rows = []
    for codelist_id, body in CODELIST_RE.findall(raw_xml):
        for code, code_body in CODE_BLOCK_RE.findall(body):
            name_en_match = NAME_EN_RE.search(code_body)
            name_th_match = NAME_TH_RE.search(code_body)
            rows.append((
                codelist_id, code,
                name_en_match.group(1) if name_en_match else None,
                name_th_match.group(1) if name_th_match else None,
            ))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO pop_indicator_lookup (codelist_id, code, name_en, name_th) VALUES (%s,%s,%s,%s)",
            rows,
        )
    conn.commit()
    print(f"[silver_nso] pop_indicator_lookup: loaded {len(rows)} codes across "
          f"{len({r[0] for r in rows})} codelists")
    return len(rows)


def _parse_age(age_code: str):
    """Returns (age_exact, age_qualifier). Same regex this project already
    fixed once for the pre-restart NSO source -- Y_LE/Y_GE/Y_GT/Y_LT
    prefixes are all 4 chars, so the digit portion starts at position 5."""
    if age_code == "_T":
        return None, "total"
    m = AGE_RE_EXACT.match(age_code)
    if m:
        return int(m.group(1)), "exact"
    m = AGE_RE_BUCKET.match(age_code)
    if m:
        qualifier = {"LE": "le", "GE": "ge", "GT": "gt", "LT": "lt"}[m.group(1)]
        return int(m.group(2)), qualifier
    return None, "other"  # e.g. LUNAR


def load_population_reference_age_sex(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT code, name_en FROM pop_indicator_lookup WHERE codelist_id = 'CL_POP_IND'")
        indicator_names = dict(cur.fetchall())
        cur.execute("SELECT code, name_en FROM pop_indicator_lookup WHERE codelist_id = 'CL_CWT'")
        province_names = dict(cur.fetchall())

        rows = []
        for source_level, table in (("national", "pop_reg_national"), ("province", "pop_reg_province")):
            # bronze.pop_reg_national UNIONs two source files by design
            # (confirmed by inspection): AllIndicators covers 2560-2568 but
            # never breaks down by age (always age='_T'); ByAge covers only
            # 2567 but with a full age breakdown that itself includes an
            # age='_T' summary row -- so AllIndicators' 2567 row is an exact
            # duplicate of ByAge's age='_T' row for every (pop_ind, sex).
            # Confirmed: unfiltered SUM() of the 2567 headline total was
            # exactly 2x every other year. Exclude the redundant one.
            where = (
                "WHERE src_file_name NOT LIKE '%AllIndicators%' OR time_period <> '2567'"
                if table == "pop_reg_national" else ""
            )
            cur.execute(
                f"SELECT pop_ind, sex, age, cwt, time_period, obs_value FROM bronze.{table} {where}"
            )
            for pop_ind, sex, age_code, cwt, time_period, obs_value in cur.fetchall():
                age_exact, age_qualifier = _parse_age(age_code)
                year_be = int(time_period)
                rows.append((
                    source_level, pop_ind, indicator_names.get(pop_ind),
                    1 if pop_ind == "DEM_IND24" else 0,
                    sex, age_code, age_exact, age_qualifier,
                    None if cwt == "_T" else cwt,
                    province_names.get(cwt) if cwt != "_T" else None,
                    year_be - 543,
                    None if obs_value in (None, "") else int(float(obs_value)),
                ))

        insert_sql = (
            "INSERT INTO population_reference_age_sex "
            "(source_level, pop_ind, indicator_name_en, is_headline_total, sex, age_code, "
            "age_exact, age_qualifier, province_code, province_name_en, year_ce, obs_value) "
            "VALUES (" + ",".join(["%s"] * 12) + ")"
        )
        cur.executemany(insert_sql, rows)
    conn.commit()
    print(f"[silver_nso] population_reference_age_sex: loaded {len(rows)} rows")
    return len(rows)


def load_labor_force_survey(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT stat_list, `รายการสถิติ`, level_of_edu, `ระดับการศึกษา`, sex, `เพศ`, "
            "age_gp, `กลุ่มอายุ`, area, `พื้นที่ระดับภาค`, cwt, `พื้นที่ระดับจังหวัด`, "
            "municipal, `พื้นที่ระดับเขตการปกครอง`, unit, `หน่วยวัด`, unit_mul, freq, "
            "time_period, obs_value, note "
            "FROM bronze.pop_sur_survey"
        )
        rows = []
        for (stat_list, label_th, level_of_edu, level_of_edu_th, sex, sex_th, age_gp, age_gp_th,
             area, area_th, cwt, cwt_th, municipal, municipal_th, unit, unit_th, unit_mul,
             freq, time_period, obs_value, note) in cur.fetchall():

            year_ce = quarter = None
            if time_period:
                qm = re.match(r"^(\d{4})-Q(\d)$", time_period)
                if qm:
                    year_be, quarter = int(qm.group(1)), int(qm.group(2))
                    year_ce = year_be - 543
                elif time_period.isdigit():
                    year_ce = int(time_period) - 543

            rows.append((
                stat_list, label_th, level_of_edu, level_of_edu_th, sex, sex_th,
                age_gp, age_gp_th, area, area_th, cwt, cwt_th, municipal, municipal_th,
                unit, unit_th,
                None if unit_mul in (None, "") else int(unit_mul),
                freq, time_period, year_ce, quarter,
                None if obs_value in (None, "") else float(obs_value),
                note,
            ))

        insert_sql = (
            "INSERT INTO labor_force_survey "
            "(stat_list, indicator_label_th, level_of_edu, level_of_edu_th, sex, sex_th, "
            "age_gp, age_gp_th, area, area_th, province_code, province_th, municipal, municipal_th, "
            "unit, unit_th, unit_mul, freq, time_period, year_ce, quarter, obs_value, note) "
            "VALUES (" + ",".join(["%s"] * 23) + ")"
        )
        cur.executemany(insert_sql, rows)
    conn.commit()
    print(f"[silver_nso] labor_force_survey: loaded {len(rows)} rows")
    return len(rows)


def run() -> None:
    conn = _connect()
    load_pop_indicator_lookup(conn)
    load_population_reference_age_sex(conn)
    load_labor_force_survey(conn)
    conn.close()
