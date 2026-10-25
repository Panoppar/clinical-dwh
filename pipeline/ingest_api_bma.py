"""Fetches BMA's community-registry CKAN package (one CSV resource per
fiscal year) and lands each resource's raw CSV bytes in the landing zone,
keyed by the resource's own stable CKAN id. Does not parse -- that's
extract_load_api_bma.py's job.

Adapted from kmch-ml's fetch_bma() (Paiiyahh/kmch-ml, private repo). The
package currently publishes one resource per fiscal year (2565/2566/2567)
but the CKAN package_show call is re-walked on every ingest run so a new
fiscal year BMA adds later is picked up automatically, without a code change.
"""

import requests

import landing_store

BMA_CKAN_BASE = "https://data.bangkok.go.th/api/3/action"
BMA_DATASET_ID = "soc_626755a649135"


def run() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 kmch-phase3-bma/1.0"})

    resp = session.get(f"{BMA_CKAN_BASE}/package_show", params={"id": BMA_DATASET_ID}, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(f"BMA CKAN package_show failed: {payload}")

    for resource in payload["result"]["resources"]:
        resource_id = resource["id"]
        r2 = session.get(resource["url"], timeout=60)
        r2.raise_for_status()
        key, is_new = landing_store.save_version("bma", resource_id, "csv", r2.content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_bma] {resource.get('name')!r} ({resource_id}): {status}: {key}")


if __name__ == "__main__":
    run()
