"""
Loads the NSO bronze tables: pop_reg_national, pop_reg_province,
pop_reg_structure_metadata (raw XML, not parsed), pop_sur_survey, and the
ingestion_log that the other four reference.
"""

import csv
import os
import re
from datetime import datetime, timezone

import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/nso"
BATCH_SIZE = 2000

POP_REG_NATIONAL_FILES = [
    "01_National_AllYears_BySex/POP_REG_National_BySex_AllIndicators_2560-2568.csv",
    "02_National_2567_ByAge/POP_REG_National_2567_ByAge.csv",
]
POP_REG_PROVINCE_FILE = "03_ByProvince_2567/POP_REG_ByProvince_2567.csv"
STRUCTURE_XML_FILE = "04_Structure_Metadata/POP_REG_StructureMetadata_SDMX.xml"
POP_SUR_FILE = "POP_SUR/POP_SUR_LaborForceSurvey_AllPeriods_2563-2567.csv"


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database="bronze",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _insert_batch(cur, insert_sql, rows):
    row_count = 0
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
            batch.clear()
    if batch:
        cur.executemany(insert_sql, batch)
        row_count += len(batch)
    return row_count


def _log_ingestion(cur, src_file_name, target_table, row_count, dataflow_id=None):
    cur.execute(
        "INSERT INTO ingestion_log (src_file_name, src_dataflow_id, target_table, row_count) "
        "VALUES (%s,%s,%s,%s)",
        (src_file_name, dataflow_id, target_table, row_count),
    )
    return cur.lastrowid


def _load_csv_rows(path, n_cols):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for i, row in enumerate(reader, start=1):
            if not row or not any(row):
                continue
            row = (row + [None] * n_cols)[:n_cols]
            yield i, row


def load_pop_reg_national(conn) -> int:
    total = 0
    with conn.cursor() as cur:
        for rel_path in POP_REG_NATIONAL_FILES:
            filename = os.path.basename(rel_path)
            path = os.path.join(EXTERNAL_SOURCES_ROOT, rel_path)
            rows = list(_load_csv_rows(path, 14))
            dataflow_id = rows[0][1][0] if rows else None
            ingestion_id = _log_ingestion(cur, filename, "pop_reg_national", len(rows), dataflow_id)
            insert_sql = (
                "INSERT INTO pop_reg_national "
                "(dataflow, pop_subj, pop_ind, sex, age, cwt, amphoe, tambon, unit, freq, "
                "time_period, obs_value, source, note, src_file_name, src_row_number, ingestion_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            batch = [(*row, filename, i, ingestion_id) for i, row in rows]
            n = _insert_batch(cur, insert_sql, batch)
            total += n
            print(f"[nso] pop_reg_national: loaded {n} rows from {filename}")
    conn.commit()
    return total


def load_pop_reg_province(conn) -> int:
    filename = os.path.basename(POP_REG_PROVINCE_FILE)
    path = os.path.join(EXTERNAL_SOURCES_ROOT, POP_REG_PROVINCE_FILE)
    rows = list(_load_csv_rows(path, 15))
    with conn.cursor() as cur:
        dataflow_id = rows[0][1][0] if rows else None
        ingestion_id = _log_ingestion(cur, filename, "pop_reg_province", len(rows), dataflow_id)
        insert_sql = (
            "INSERT INTO pop_reg_province "
            "(dataflow, pop_subj, pop_ind, sex, age, cwt, amphoe, tambon, unit, freq, "
            "time_period, obs_value, source, note, v, src_file_name, src_row_number, ingestion_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        batch = [(*row, filename, i, ingestion_id) for i, row in rows]
        n = _insert_batch(cur, insert_sql, batch)
    conn.commit()
    print(f"[nso] pop_reg_province: loaded {n} rows from {filename}")
    return n


def load_structure_metadata(conn) -> int:
    filename = os.path.basename(STRUCTURE_XML_FILE)
    path = os.path.join(EXTERNAL_SOURCES_ROOT, STRUCTURE_XML_FILE)
    with open(path, "r", encoding="utf-8-sig") as f:
        raw_xml = f.read()

    id_match = re.search(r'<structure:Dataflow id="([^"]+)" agencyID="[^"]*" version="([^"]+)"', raw_xml)
    structure_id, structure_version = id_match.groups() if id_match else (None, None)
    prepared_match = re.search(r"<message:Prepared>([^<]+)</message:Prepared>", raw_xml)
    file_prepared_at = None
    if prepared_match:
        # SDMX timestamp e.g. 2026-10-04T18:01:17.9391607+00:00 -- trim sub-microsecond
        # digits and the offset so MySQL TIMESTAMP (no tz) can parse it.
        ts = prepared_match.group(1)
        ts = re.sub(r"\.\d+", "", ts)
        ts = re.sub(r"[+-]\d{2}:\d{2}$", "", ts)
        file_prepared_at = ts

    with conn.cursor() as cur:
        ingestion_id = _log_ingestion(cur, filename, "pop_reg_structure_metadata", 1, structure_id)
        cur.execute(
            "INSERT INTO pop_reg_structure_metadata "
            "(structure_id, structure_version, raw_xml, file_prepared_at, src_file_name, ingestion_id) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (structure_id, structure_version, raw_xml, file_prepared_at, filename, ingestion_id),
        )
    conn.commit()
    print(f"[nso] pop_reg_structure_metadata: loaded 1 row from {filename}")
    return 1


def load_pop_sur_survey(conn) -> int:
    filename = os.path.basename(POP_SUR_FILE)
    path = os.path.join(EXTERNAL_SOURCES_ROOT, POP_SUR_FILE)
    rows = list(_load_csv_rows(path, 34))
    with conn.cursor() as cur:
        dataflow_id = rows[0][1][1] if rows else None  # structure_id column
        ingestion_id = _log_ingestion(cur, filename, "pop_sur_survey", len(rows), dataflow_id)
        insert_sql = (
            "INSERT INTO pop_sur_survey ("
            "structure, structure_id, structure_name, action, stat_list, `รายการสถิติ`, "
            "list_status, `สถานะรายการ`, level_of_edu, `ระดับการศึกษา`, sex, `เพศ`, "
            "age_gp, `กลุ่มอายุ`, area, `พื้นที่ระดับภาค`, cwt, `พื้นที่ระดับจังหวัด`, "
            "municipal, `พื้นที่ระดับเขตการปกครอง`, unit, `หน่วยวัด`, unit_mul, `หน่วยวัดตัวคูณ`, "
            "freq, `ความถี่ในการเผยแพร่`, time_period, `ช่วงเวลา`, obs_value, `ค่าสังเกต`, "
            "note, `หมายเหตุ`, source, `แหล่งที่มา`, "
            "src_file_name, src_row_number, ingestion_id) "
            "VALUES (" + ",".join(["%s"] * 37) + ")"
        )
        batch = [(*row, filename, i, ingestion_id) for i, row in rows]
        n = _insert_batch(cur, insert_sql, batch)
    conn.commit()
    print(f"[nso] pop_sur_survey: loaded {n} rows from {filename}")
    return n


def run() -> None:
    conn = _connect()
    total = 0
    total += load_pop_reg_national(conn)
    total += load_pop_reg_province(conn)
    total += load_structure_metadata(conn)
    total += load_pop_sur_survey(conn)
    conn.close()
    print(f"[nso] total rows loaded: {total}")
