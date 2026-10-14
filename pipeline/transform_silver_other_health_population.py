"""
Silver transform for other_health's 3 population tables:
  - population_by_age_subdistrict_bkk: unpivots bronze's 219-key JSON
    payload into (component_type, sex, age_exact, age_qualifier) rows.
  - population_by_tambon_national: dedupes the unflagged triplication and
    flags embedded rollup rows (same pattern as DOPA).
  - elderly_dependency_by_district: straight BE->CE cast.
"""

import json
import os
import re

import pymysql

AGE_LT_RE = re.compile(r"^(ชาย|หญิง) < 1 ปี$")
AGE_GT_RE = re.compile(r"^(ชาย|หญิง) > 100 ปี$")
AGE_EXACT_RE = re.compile(r"^(ชาย|หญิง) (\d+) ปี$")


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


def _sex_of(key: str) -> str:
    if key.startswith("ชาย") or "ประชากรชาย" in key:
        return "male"
    if key.startswith("หญิง") or "ประชากรหญิง" in key:
        return "female"
    if key.startswith("ผลรวม"):
        return "total"
    raise ValueError(f"cannot determine sex for key {key!r}")


def _parse_age_sex_key(key: str):
    """Returns (component_type, sex, age_exact, age_qualifier) for one of
    the 219 age_sex_data JSON keys."""
    m = AGE_LT_RE.match(key)
    if m:
        return "age_bracket", _sex_of(key), 0, "lt"
    m = AGE_GT_RE.match(key)
    if m:
        return "age_bracket", _sex_of(key), 100, "gt"
    m = AGE_EXACT_RE.match(key)
    if m:
        return "age_bracket", _sex_of(key), int(m.group(2)), "exact"
    if "จันทรคติ" in key:
        return "lunar_birth", _sex_of(key), None, None
    if "ทะเบียนบ้านกลาง" in key:
        return "central_house_reg", _sex_of(key), None, None
    if "มิใช่สัญชาติไทย" in key:
        return "non_thai_national", _sex_of(key), None, None
    if "ระหว่างการย้าย" in key:
        return "mid_move", _sex_of(key), None, None
    if "ทั้งหมด" in key:
        return "grand_total", _sex_of(key), None, None
    raise ValueError(f"unrecognized age_sex_data key {key!r}")


def load_population_by_age_subdistrict_bkk(conn) -> int:
    insert_sql = (
        "INSERT INTO population_by_age_subdistrict_bkk "
        "(year_ce, month, province_code, province_name, registrar_code, registrar_name, "
        "tambon_code, tambon_name, village_code, village_name, component_type, sex, "
        "age_exact, age_qualifier, is_headline_total, population_count) "
        "VALUES (" + ",".join(["%s"] * 16) + ")"
    )
    rows = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT `ปีเดือน`, `รหัสจังหวัด`, `ชื่อจังหวัด`, `รหัสสำนักทะเบียน`, `ชื่อสำนักทะเบียน`, "
            "`รหัสตำบล`, `ชื่อตำบล`, `รหัสหมู่บ้าน`, `ชื่อหมู่บ้าน`, age_sex_data "
            "FROM bronze.population_by_age_subdistrict_bkk"
        )
        for (yymm, prov_code, prov_name, reg_code, reg_name,
             tambon_code, tambon_name, village_code, village_name, age_sex_json) in cur.fetchall():
            yymm = (yymm or "").lstrip("﻿")
            year_be, month = int(yymm[:2]) + 2500, int(yymm[2:])
            year_ce = year_be - 543

            payload = json.loads(age_sex_json)
            for key, raw_value in payload.items():
                component_type, sex, age_exact, age_qualifier = _parse_age_sex_key(key)
                is_headline_total = 1 if (component_type == "grand_total" and sex == "total") else 0
                value = None if raw_value in (None, "") else int(str(raw_value).replace(",", ""))
                rows.append((
                    year_ce, month, prov_code, prov_name, reg_code, reg_name,
                    tambon_code, tambon_name, village_code, village_name,
                    component_type, sex, age_exact, age_qualifier, is_headline_total, value,
                ))
        cur.executemany(insert_sql, rows)
    conn.commit()
    print(f"[silver_other_health_pop] population_by_age_subdistrict_bkk: loaded {len(rows)} rows")
    return len(rows)


def load_population_by_tambon_national(conn) -> int:
    insert_sql = (
        "INSERT INTO population_by_tambon_national "
        "(yymm, year_be, year_ce, month, cc_code, cc_desc, rcode_code, rcode_desc, "
        "ccaatt_code, ccaatt_desc, ccaattmm_code, ccaattmm_desc, male, female, total, house, is_rollup_row) "
        "SELECT "
        "`YYMM`, 2500 + CAST(LEFT(`YYMM`,2) AS UNSIGNED), "
        "2500 + CAST(LEFT(`YYMM`,2) AS UNSIGNED) - 543, CAST(RIGHT(`YYMM`,2) AS UNSIGNED), "
        "`CC-CODE`, `CC-DESC`, `RCODE-CODE`, `RCODE-DESC`, `CCAATT-CODE`, `CCAATT-DESC`, "
        "`CCAATTMM-CODE`, `CCAATTMM-DESC`, "
        "CAST(NULLIF(REPLACE(`MALE`,',',''),'') AS SIGNED), "
        "CAST(NULLIF(REPLACE(`FEMALE`,',',''),'') AS SIGNED), "
        "CAST(NULLIF(REPLACE(`TOTAL`,',',''),'') AS SIGNED), "
        "CAST(NULLIF(REPLACE(`HOUSE`,',',''),'') AS SIGNED), "
        "IF(`CCAATT-CODE` = '0', 1, 0) "
        "FROM bronze.population_by_tambon_national "
        "WHERE source_row_number <= 11386"  # first of the 3 unflagged triplicate copies
    )
    with conn.cursor() as cur:
        n = cur.execute(insert_sql)
    conn.commit()
    print(f"[silver_other_health_pop] population_by_tambon_national: loaded {n} rows")
    return n


def load_elderly_dependency_by_district(conn) -> int:
    insert_sql = (
        "INSERT INTO elderly_dependency_by_district "
        "(fiscal_year_be, fiscal_year_ce, district_name, bedridden_count, homebound_count, "
        "socially_isolated_count, unit, source_attribution, is_aggregate_row) "
        "SELECT "
        "CAST(`ปีงบประมาณ` AS UNSIGNED), CAST(`ปีงบประมาณ` AS UNSIGNED) - 543, `อำเภอ`, "
        "CAST(NULLIF(REPLACE(`ผู้สูงอายุติดเตียง`,',',''),'') AS SIGNED), "
        "CAST(NULLIF(REPLACE(`ผู้สูงอายุติดบ้าน`,',',''),'') AS SIGNED), "
        "CAST(NULLIF(REPLACE(`ผู้สูงอายุติดสังคม`,',',''),'') AS SIGNED), "
        "`หน่วย`, `ที่มา`, "
        "IF(`อำเภอ` = 'รวม', 1, 0) "
        "FROM bronze.elderly_dependency_by_district "
        # The "_2566" file is a strict subset of "_2568" (confirmed by
        # inspection: identical BE2566/BE2567 figures, just a different
        # district-name prefix) -- use "_2568" exclusively to avoid
        # double-loading the 2 overlapping fiscal years.
        "WHERE source_file_name LIKE '%2568%'"
    )
    with conn.cursor() as cur:
        n = cur.execute(insert_sql)
    conn.commit()
    print(f"[silver_other_health_pop] elderly_dependency_by_district: loaded {n} rows")
    return n


def run() -> None:
    conn = _connect()
    load_population_by_age_subdistrict_bkk(conn)
    load_population_by_tambon_national(conn)
    load_elderly_dependency_by_district(conn)
    conn.close()
