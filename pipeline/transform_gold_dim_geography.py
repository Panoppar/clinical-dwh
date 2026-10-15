"""
Builds gold.dim_geography from every Stage-1 Silver source that carries a
geography.

Real government admin codes (DOPA's province/district/subdistrict scheme)
are the primary, reliable join key -- confirmed by inspection that
population_by_age_subdistrict_bkk's codes line up exactly with DOPA's
(province 10 = กรุงเทพมหานคร in both; district 1001 = เขตพระนคร in both,
just a shorter display name). Only one Stage-1 source has no codes at all
(elderly_dependency_by_district, Samut Prakan อำเภอ level) -- its district
names match DOPA's rcode_desc verbatim (confirmed: "อำเภอบางบ่อ" etc. are
literally the same strings), so it's matched by exact name against
province_code='11' rather than needing fuzzy normalization.
"""

import os

import pymysql


def _connect(database="gold"):
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


def run() -> None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SET SESSION group_concat_max_len = 1000000")

        # 1. Country node (Thailand) -- parent for every province.
        cur.execute(
            "INSERT INTO dim_geography (admin_level, province_name_th, source_system) "
            "VALUES ('country', 'ประเทศไทย', 'manual')"
        )
        country_key = cur.lastrowid

        # 2. Provinces, from DOPA (the richest, most complete source).
        #    One row per code, not per (code, name) -- confirmed by
        #    inspection that admin names genuinely change over this
        #    source's 30+ year span (e.g. a district reclassified from
        #    เทศบาลเมือง to เทศบาลนคร, same code) -- picking distinct
        #    (code, name) pairs would create duplicate dimension rows for
        #    the same real place and silently double-count every fact
        #    that joins on code alone. GROUP_CONCAT+SUBSTRING_INDEX picks
        #    the name from the latest yymm per code, with a guaranteed
        #    single row per code even if two names tie at the same yymm
        #    (unlike a correlated MAX(yymm) subquery, which wouldn't).
        cur.execute(
            "SELECT cc_code, "
            "SUBSTRING_INDEX(GROUP_CONCAT(TRIM(cc_desc) ORDER BY yymm DESC SEPARATOR '\x01'), '\x01', 1) "
            "FROM silver.population_by_area_month "
            "WHERE admin_level='province' AND is_rollup_row=0 AND cc_code IS NOT NULL "
            "GROUP BY cc_code"
        )
        province_rows = cur.fetchall()
        province_key_by_code = {}
        for code, name in province_rows:
            cur.execute(
                "INSERT INTO dim_geography (admin_level, province_code, province_name_th, "
                "parent_geo_key, source_system) VALUES ('province', %s, %s, %s, 'dopa')",
                (code, name, country_key),
            )
            province_key_by_code[code] = cur.lastrowid
        print(f"[gold_dim_geography] provinces: {len(province_key_by_code)}")

        # 3. Districts, from DOPA. One row per (province_code, district_code),
        #    same latest-name-wins rule as provinces above.
        cur.execute(
            "SELECT cc_code, rcode_code, "
            "SUBSTRING_INDEX(GROUP_CONCAT(TRIM(rcode_desc) ORDER BY yymm DESC SEPARATOR '\x01'), '\x01', 1) "
            "FROM silver.population_by_area_month "
            "WHERE admin_level='district' AND is_rollup_row=0 AND rcode_code IS NOT NULL "
            "GROUP BY cc_code, rcode_code"
        )
        district_key_by_code = {}  # (province_code, district_code) -> geo_key
        for province_code, district_code, name in cur.fetchall():
            parent_key = province_key_by_code.get(province_code)
            cur.execute(
                "INSERT INTO dim_geography (admin_level, province_code, district_code, district_name_th, "
                "parent_geo_key, source_system) VALUES ('district', %s, %s, %s, %s, 'dopa')",
                (province_code, district_code, name, parent_key),
            )
            district_key_by_code[(province_code, district_code)] = cur.lastrowid
        print(f"[gold_dim_geography] districts: {len(district_key_by_code)}")

        # 4. Subdistricts, from DOPA. One row per
        #    (province_code, district_code, subdistrict_code), same rule.
        cur.execute(
            "SELECT cc_code, rcode_code, ccaatt_code, "
            "SUBSTRING_INDEX(GROUP_CONCAT(TRIM(ccaatt_desc) ORDER BY yymm DESC SEPARATOR '\x01'), '\x01', 1) "
            "FROM silver.population_by_area_month "
            "WHERE admin_level='subdistrict' AND is_rollup_row=0 AND ccaatt_code IS NOT NULL "
            "GROUP BY cc_code, rcode_code, ccaatt_code"
        )
        subdistrict_key_by_code = {}  # (province_code, district_code, subdistrict_code) -> geo_key
        for province_code, district_code, subdistrict_code, name in cur.fetchall():
            parent_key = district_key_by_code.get((province_code, district_code))
            cur.execute(
                "INSERT INTO dim_geography (admin_level, province_code, district_code, subdistrict_code, "
                "subdistrict_name_th, parent_geo_key, source_system) "
                "VALUES ('subdistrict', %s, %s, %s, %s, %s, 'dopa')",
                (province_code, district_code, subdistrict_code, name, parent_key),
            )
            subdistrict_key_by_code[(province_code, district_code, subdistrict_code)] = cur.lastrowid
        print(f"[gold_dim_geography] subdistricts: {len(subdistrict_key_by_code)}")
        # Known gap, verified not a bug: 10 subdistrict codes (out of
        # 10,416) reference a district_code that never appears as its own
        # row in the district-level file -- likely a newer administrative
        # subdivision not yet reflected there. parent_geo_key stays NULL
        # for these rather than fabricating a placeholder parent row.

        # 5. population_by_tambon_national reuses the exact same DOPA code
        #    scheme (confirmed: same source data, different delivery) --
        #    add any codes not already covered (e.g. if its snapshot year
        #    introduced a new administrative code DOPA's own file didn't
        #    have at the same vintage).
        cur.execute(
            "SELECT DISTINCT cc_code, cc_desc, rcode_code, rcode_desc, ccaatt_code, ccaatt_desc "
            "FROM silver.population_by_tambon_national WHERE is_rollup_row=0"
        )
        new_from_tambon = 0
        for cc_code, cc_desc, rcode_code, rcode_desc, ccaatt_code, ccaatt_desc in cur.fetchall():
            if cc_code and cc_code not in province_key_by_code:
                cur.execute(
                    "INSERT INTO dim_geography (admin_level, province_code, province_name_th, "
                    "parent_geo_key, source_system) VALUES ('province', %s, %s, %s, 'other_health')",
                    (cc_code, (cc_desc or "").strip(), country_key),
                )
                province_key_by_code[cc_code] = cur.lastrowid
                new_from_tambon += 1
            if rcode_code and (cc_code, rcode_code) not in district_key_by_code:
                cur.execute(
                    "INSERT INTO dim_geography (admin_level, province_code, district_code, district_name_th, "
                    "parent_geo_key, source_system) VALUES ('district', %s, %s, %s, %s, 'other_health')",
                    (cc_code, rcode_code, (rcode_desc or "").strip(), province_key_by_code.get(cc_code)),
                )
                district_key_by_code[(cc_code, rcode_code)] = cur.lastrowid
                new_from_tambon += 1
            if ccaatt_code and (cc_code, rcode_code, ccaatt_code) not in subdistrict_key_by_code:
                cur.execute(
                    "INSERT INTO dim_geography (admin_level, province_code, district_code, subdistrict_code, "
                    "subdistrict_name_th, parent_geo_key, source_system) "
                    "VALUES ('subdistrict', %s, %s, %s, %s, %s, 'other_health')",
                    (cc_code, rcode_code, ccaatt_code, (ccaatt_desc or "").strip(),
                     district_key_by_code.get((cc_code, rcode_code))),
                )
                subdistrict_key_by_code[(cc_code, rcode_code, ccaatt_code)] = cur.lastrowid
                new_from_tambon += 1
        print(f"[gold_dim_geography] new codes from population_by_tambon_national: {new_from_tambon}")

        # 6. elderly_dependency_by_district: no codes, Samut Prakan (cc_code='11')
        #    only -- matched by exact district_name against DOPA's rcode_desc,
        #    confirmed identical strings ("อำเภอบางบ่อ" etc).
        cur.execute("SELECT DISTINCT district_name FROM silver.elderly_dependency_by_district "
                    "WHERE is_aggregate_row=0")
        unmatched = 0
        for (district_name,) in cur.fetchall():
            match_key = None
            for (prov, dist), key in district_key_by_code.items():
                if prov == "11":
                    cur.execute(
                        "SELECT district_name_th FROM dim_geography WHERE geo_key=%s", (key,)
                    )
                    if cur.fetchone()[0] == district_name:
                        match_key = key
                        break
            if match_key is None:
                cur.execute(
                    "INSERT INTO dim_geography (admin_level, province_code, district_name_th, "
                    "parent_geo_key, source_system) VALUES ('district', '11', %s, %s, 'other_health (unmatched)')",
                    (district_name, province_key_by_code.get("11")),
                )
                unmatched += 1
        print(f"[gold_dim_geography] elderly_dependency district names unmatched (new rows): {unmatched}")

    conn.commit()
    conn.close()
