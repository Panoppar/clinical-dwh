"""Silver transform for bronze.geo_boundary_{subdistrict,district} ->
silver.geo_boundary_{subdistrict,district}. Casts coordinates/area to
DECIMAL; trims text. No polygon table in Silver (see sql/silver/19)."""

import os

import pymysql


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


def _to_int(s):
    d = _to_decimal(s)
    return int(d) if d is not None else None


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_tis1099_subdistrict_code, raw_parent_district_tis1099_code, "
            "raw_parent_province_tis1099_code, raw_name_en, raw_name_th, raw_centroid_lat, "
            "raw_centroid_lon, raw_postal_code FROM geo_boundary_subdistrict"
        )
        rows = []
        for (code, dcode, pcode, name_en, name_th, lat, lon, postal) in rcur:
            if not code or not name_th:
                continue
            rows.append((code, dcode, pcode, (name_en or "").strip() or None, name_th.strip(),
                         _to_decimal(lat), _to_decimal(lon), (postal or "").strip() or None))
    with write_conn.cursor() as wcur:
        wcur.executemany(
            "INSERT INTO geo_boundary_subdistrict (subdistrict_code, district_code, province_code, "
            "name_en, name_th, centroid_lat, centroid_lon, postal_code) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
    write_conn.commit()
    print(f"[silver_geo_boundary] geo_boundary_subdistrict: loaded {len(rows)} rows")

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_tis1099_district_code, raw_parent_province_tis1099_code, raw_name_en, raw_name_th, "
            "raw_centroid_lat, raw_centroid_lon, raw_area_km2, raw_num_tambon, raw_postal_code_prefixes "
            "FROM geo_boundary_district"
        )
        rows = []
        for (code, pcode, name_en, name_th, lat, lon, area, num_tambon, postal_prefixes) in rcur:
            if not code or not name_th:
                continue
            rows.append((code, pcode, (name_en or "").strip() or None, name_th.strip(),
                         _to_decimal(lat), _to_decimal(lon), _to_decimal(area), _to_int(num_tambon),
                         (postal_prefixes or "").strip() or None))
    with write_conn.cursor() as wcur:
        wcur.executemany(
            "INSERT INTO geo_boundary_district (district_code, province_code, name_en, name_th, "
            "centroid_lat, centroid_lon, area_km2, num_tambon, postal_code_prefixes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
    write_conn.commit()
    print(f"[silver_geo_boundary] geo_boundary_district: loaded {len(rows)} rows")

    read_conn.close()
    write_conn.close()


if __name__ == "__main__":
    run()
