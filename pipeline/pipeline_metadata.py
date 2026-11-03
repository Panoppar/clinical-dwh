"""High-water mark and incremental state management for delta-load architecture.

Tracks the last successfully processed ingestion_batch_id per target table (Silver→Gold).
Enables filtering Silver queries to only process delta rows, avoiding OOM and wasted compute.
"""

import os
from datetime import datetime, timezone

import pymysql


def _connect_gold():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database="gold",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def get_high_water_mark(target_table: str) -> str | None:
    """Retrieve the last successfully processed ingestion_batch_id for a target table.

    Args:
        target_table: Name of the Gold fact table (e.g., 'fact_hdc_observation')

    Returns:
        Last ingestion_batch_id, or None if table has never been processed (first run).
    """
    try:
        conn = _connect_gold()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT last_batch_id FROM pipeline_metadata WHERE target_table = %s",
                (target_table,)
            )
            result = cur.fetchone()
        conn.close()
        return result[0] if result and result[0] else None
    except pymysql.Error as e:
        print(f"[pipeline_metadata] warning: could not fetch high-water mark for {target_table}: {e}")
        return None


def set_high_water_mark(target_table: str, batch_id: str) -> None:
    """Persist the high-water mark after successful processing of a batch.

    Args:
        target_table: Name of the Gold fact table (e.g., 'fact_hdc_observation')
        batch_id: The ingestion_batch_id that was just processed
    """
    try:
        conn = _connect_gold()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_metadata (target_table, last_batch_id, last_processed_at)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    last_batch_id = VALUES(last_batch_id),
                    last_processed_at = NOW()
                """,
                (target_table, batch_id)
            )
        conn.commit()
        conn.close()
        print(f"[pipeline_metadata] high-water mark set: {target_table} → {batch_id}")
    except pymysql.Error as e:
        print(f"[pipeline_metadata] error setting high-water mark: {e}")
        raise


def get_metadata_status() -> dict:
    """Fetch all pipeline metadata for inspection/debugging."""
    try:
        conn = _connect_gold()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT target_table, last_batch_id, last_processed_at FROM pipeline_metadata ORDER BY target_table"
            )
            rows = cur.fetchall()
        conn.close()
        return {row[0]: {"last_batch_id": row[1], "last_processed_at": row[2]} for row in rows}
    except pymysql.Error as e:
        print(f"[pipeline_metadata] error fetching status: {e}")
        return {}


def reset_high_water_mark(target_table: str) -> None:
    """Reset high-water mark for a target table (forces full re-load on next run).

    Use only for debugging/recovery. Normal incremental runs should not call this.
    """
    try:
        conn = _connect_gold()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pipeline_metadata SET last_batch_id = NULL WHERE target_table = %s",
                (target_table,)
            )
        conn.commit()
        conn.close()
        print(f"[pipeline_metadata] high-water mark reset: {target_table}")
    except pymysql.Error as e:
        print(f"[pipeline_metadata] error resetting high-water mark: {e}")
        raise


if __name__ == "__main__":
    print("Pipeline Metadata Status:")
    print(get_metadata_status())
