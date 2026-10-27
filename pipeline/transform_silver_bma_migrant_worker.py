"""Melts bronze.bma_migrant_general/mou_import/renewal/illegal into
silver.bma_migrant_worker_permit -- see sql/silver/22's header for the
grain and nationality-NULL design.
"""

import os

import pymysql

# category label -> (bronze column prefix). Order matches bma_migrant_general's own column layout.
GENERAL_CATEGORIES = [
    ("ทั่วไป", "general"),
    ("นำเข้าตาม MOU", "mou_import"),
    ("ส่งเสริมการลงทุน", "investment"),
    ("ชนกลุ่มน้อย", "minority"),
    ("ต่ออายุ", "renewal"),
    ("จดทะเบียนสถานะไม่ถูกกฎหมาย", "illegal"),
]
NATIONALITIES = [
    ("เมียนมา", "myanmar"),
    ("ลาว", "laos"),
    ("กัมพูชา", "cambodia"),
    ("เวียดนาม", "vietnam"),
]
# nationality-breakdown bronze table -> the bma_migrant_general category it details
NATIONALITY_TABLES = [
    ("bma_migrant_mou_import", "นำเข้าตาม MOU"),
    ("bma_migrant_renewal", "ต่ออายุ"),
    ("bma_migrant_illegal", "จดทะเบียนสถานะไม่ถูกกฎหมาย"),
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


def _zone_id(label: str) -> int | None:
    # "พื้นที่ N" -> N; the grand-total row's label is empty -- skipped (see sql/silver/22 header).
    label = (label or "").strip()
    if not label.startswith("พื้นที่"):
        return None
    return int(label.replace("พื้นที่", "").strip())


def run() -> None:
    bronze_conn = _connect("bronze")
    silver_conn = _connect("silver")
    rows = []

    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_zone_label, raw_general_total, raw_general_male, raw_general_female, "
            "raw_mou_import_total, raw_mou_import_male, raw_mou_import_female, "
            "raw_investment_total, raw_investment_male, raw_investment_female, "
            "raw_minority_total, raw_minority_male, raw_minority_female, "
            "raw_renewal_total, raw_renewal_male, raw_renewal_female, "
            "raw_illegal_total, raw_illegal_male, raw_illegal_female FROM bma_migrant_general"
        )
        for rec in bcur.fetchall():
            zone_id = _zone_id(rec[0])
            if zone_id is None:
                continue  # grand-total row
            for i, (cat_th, _prefix) in enumerate(GENERAL_CATEGORIES):
                total, male, female = rec[1 + i * 3], rec[2 + i * 3], rec[3 + i * 3]
                rows.append((zone_id, cat_th, None, _to_int(total), _to_int(male), _to_int(female)))

        for table, category_th in NATIONALITY_TABLES:
            bcur.execute(
                f"SELECT raw_zone_label, raw_myanmar_total, raw_myanmar_male, raw_myanmar_female, "
                f"raw_laos_total, raw_laos_male, raw_laos_female, "
                f"raw_cambodia_total, raw_cambodia_male, raw_cambodia_female, "
                f"raw_vietnam_total, raw_vietnam_male, raw_vietnam_female FROM {table}"
            )
            for rec in bcur.fetchall():
                zone_id = _zone_id(rec[0])
                if zone_id is None:
                    continue  # grand-total row
                for i, (nat_th, _prefix) in enumerate(NATIONALITIES):
                    total, male, female = rec[1 + i * 3], rec[2 + i * 3], rec[3 + i * 3]
                    rows.append((zone_id, category_th, nat_th, _to_int(total), _to_int(male), _to_int(female)))

    insert_sql = (
        "INSERT INTO bma_migrant_worker_permit (zone_id, permit_category, nationality, total, male, female) "
        "VALUES (%s,%s,%s,%s,%s,%s)"
    )
    with silver_conn.cursor() as scur:
        scur.executemany(insert_sql, rows)
    silver_conn.commit()
    print(f"[silver_bma_migrant_worker] bma_migrant_worker_permit: {len(rows)} rows")

    bronze_conn.close()
    silver_conn.close()


if __name__ == "__main__":
    run()
