"""
Cross-server copy: source-db.vaccinework -> warehouse-db.bronze.

source-db and warehouse-db are separate MySQL server containers, so this
step can't be plain SQL (no FEDERATED engine configured). Each source table
is read in full and batch-inserted into its 1:1 Bronze replica, stamped with
lineage columns `_bronze_loaded_at` / `_source_system`.

Assumes sql/bronze/01_create_bronze_tables.sql has already (re)created empty
bronze tables in this run — see run_pipeline.py for ordering.
"""

import os
import sys
from datetime import datetime, timezone

import pymysql
import pymysql.cursors

SOURCE_SYSTEM_NAME = "vaccinework_portal"

# Explicit column order per source table — mirrors the CREATE TABLE order in
# the source dump and in sql/bronze/01_create_bronze_tables.sql. Using an
# explicit column list (rather than SELECT *) guarantees column order can't
# silently drift if the source schema is altered.
TABLES: dict[str, list[str]] = {
    "Company": [
        "company_id", "company_name", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Company_Employee": [
        "employee_id", "company_id", "patient_id", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Contact": [
        "contact_id", "company_id", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Employee": [
        "employee_id", "patient_id", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "External_Person": [
        "external_id", "patient_id", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Patient": [
        "patient_id", "document_type", "id_card", "passport_id", "line_id",
        "patient_type", "sex", "prefix", "first_name", "last_name", "tel_no",
        "email", "underlying_disease", "age", "address", "zip_code",
        "created_at", "created_by", "updated_at", "updated_by",
        "deleted_at", "deleted_by",
    ],
    "Screening_Question": [
        "question_id", "question_text", "is_active", "display_order",
        "created_at", "created_by", "updated_at", "updated_by",
        "deleted_at", "deleted_by",
    ],
    "Screening_Record": [
        "record_id", "patient_id", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Screening_Answer": [
        "record_id", "question_id", "answer", "remark", "created_at",
        "created_by", "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Student": [
        "student_id", "patient_id", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "System_Audit_Log": [
        "audit_id", "table_name", "record_id", "action_type", "old_values",
        "new_values", "changed_by", "changed_at",
    ],
    "Vaccine": [
        "vaccine_id", "vaccine_name", "created_at", "created_by",
        "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
    "Vaccine_Lot": [
        "lot_id", "vaccine_id", "lot_number", "initial_quantity",
        "remaining_quantity", "created_at", "created_by", "updated_at",
        "updated_by", "deleted_at", "deleted_by",
    ],
    "Vaccination_Record": [
        "vaccination_id", "patient_id", "lot_id", "shot_date", "created_at",
        "created_by", "updated_at", "updated_by", "deleted_at", "deleted_by",
    ],
}

BATCH_SIZE = 500


def _connect(host: str, port: int, user: str, password: str, database: str | None, streaming: bool = False):
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        # Streaming (server-side) cursor for the source read, so we never
        # buffer a full table in memory; the target just needs a plain
        # cursor to issue batched INSERTs.
        cursorclass=pymysql.cursors.SSCursor if streaming else pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def run() -> None:
    source_conn = _connect(
        host=os.environ["SOURCE_DB_HOST"],
        port=int(os.environ["SOURCE_DB_PORT"]),
        user=os.environ["SOURCE_DB_USER"],
        password=os.environ["SOURCE_DB_PASSWORD"],
        database=os.environ["SOURCE_DB_NAME"],
        streaming=True,
    )
    target_conn = _connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database="bronze",
    )

    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        for table, columns in TABLES.items():
            col_list_sql = ", ".join(f"`{c}`" for c in columns)
            select_sql = f"SELECT {col_list_sql} FROM `{table}`"

            insert_cols_sql = col_list_sql + ", `_bronze_loaded_at`, `_source_system`"
            placeholders = ", ".join(["%s"] * (len(columns) + 2))
            insert_sql = f"INSERT INTO `{table}` ({insert_cols_sql}) VALUES ({placeholders})"

            with source_conn.cursor() as src_cur:
                src_cur.execute(select_sql)

                row_count = 0
                batch = []
                with target_conn.cursor() as tgt_cur:
                    for row in src_cur:
                        batch.append((*row, loaded_at, SOURCE_SYSTEM_NAME))
                        if len(batch) >= BATCH_SIZE:
                            tgt_cur.executemany(insert_sql, batch)
                            row_count += len(batch)
                            batch.clear()
                    if batch:
                        tgt_cur.executemany(insert_sql, batch)
                        row_count += len(batch)
                target_conn.commit()

            print(f"[bronze] {table}: {row_count} rows loaded")
    finally:
        source_conn.close()
        target_conn.close()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001 - top-level batch job, surface and exit non-zero
        print(f"[bronze] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
