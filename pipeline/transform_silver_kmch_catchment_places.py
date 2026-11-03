"""Silver transform for bronze.kmch_catchment_places -> silver.kmch_catchment_places.
Casts distance/travel-time to numeric, trims text, and splits
market_potential into market_tier + market_detail.

Split rule: "<tier>" or "<tier> (<detail>)" -- confirmed by direct
inspection that all 13 distinct source values fit this shape. tier is NOT
a fixed High/Medium/Low enum: most are, but "Medium to High" and
"Strategic Partner" are genuinely different content the source actually
uses, not errors to normalize away.
"""

import os
import re

import pymysql

BATCH_SIZE = 2000
_TIER_DETAIL_RE = re.compile(r"^(.+?)(?:\s*\((.+)\))?$")


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _to_decimal(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _split_market_potential(raw: str) -> tuple[str | None, str | None]:
    raw = (raw or "").strip()
    if not raw:
        return None, None
    m = _TIER_DETAIL_RE.match(raw)
    if not m:
        return raw, None
    tier, detail = m.group(1).strip(), m.group(2)
    return tier, (detail.strip() if detail else None)


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    insert_sql = (
        "INSERT INTO kmch_catchment_places "
        "(category, place_name_th, place_name_en, address, subdistrict, district, province, "
        "avg_distance_km, avg_travel_time_min, market_tier, market_detail) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_category, raw_place_name_th, raw_place_name_en, raw_address, raw_subdistrict, "
            "raw_district, raw_province, raw_avg_distance_km, raw_avg_travel_time_min, raw_market_potential "
            "FROM kmch_catchment_places"
        )
        rows = []
        total = 0
        with write_conn.cursor() as wcur:
            for (category, name_th, name_en, address, subdistrict, district, province,
                 dist, travel_time, market_potential) in rcur:
                category_clean = (category or "").strip()
                name_th_clean = (name_th or "").strip()
                subdistrict_clean = (subdistrict or "").strip()
                district_clean = (district or "").strip()
                province_clean = (province or "").strip()
                if not category_clean or not name_th_clean or not subdistrict_clean or not district_clean or not province_clean:
                    continue

                tier, detail = _split_market_potential(market_potential)

                rows.append((
                    category_clean, name_th_clean, (name_en or "").strip() or None,
                    (address or "").strip() or None, subdistrict_clean, district_clean, province_clean,
                    _to_decimal(dist), _to_decimal(travel_time), tier, detail,
                ))
                if len(rows) >= BATCH_SIZE:
                    wcur.executemany(insert_sql, rows)
                    write_conn.commit()
                    total += len(rows)
                    rows = []
            if rows:
                wcur.executemany(insert_sql, rows)
                write_conn.commit()
                total += len(rows)

    read_conn.close()
    write_conn.close()
    print(f"[silver_kmch_catchment_places] kmch_catchment_places: loaded {total} rows")


if __name__ == "__main__":
    run()
