"""S3-compatible landing zone for the live-API Bronze sources (NSO, BMA, DDS,
HDC, DIW). Raw API responses land here -- versioned, content-hashed, never
overwritten -- before Bronze shreds them into relational tables. The
elt-runner container itself never writes these bytes to its own filesystem.

Adapted from kmch-ml's raw_store.py (Paiiyahh/kmch-ml, private repo) -- same
append-only, content-addressed contract (identical bytes are never stored
twice; a new version is written only when the source's answer actually
changes), just backed by S3 object keys instead of local filenames.

Backend is SeaweedFS (S3-compatible), not MinIO: MinIO's free container
distribution was discontinued across every registry (Docker Hub, quay.io,
and direct binary download all confirmed blocked) as of this build.
landing_store.py only uses the S3 API via boto3, so swapping the backend
again later -- back to MinIO, or to real AWS S3 -- needs no code change here,
only a docker-compose/.env change.
"""

import hashlib
import os
import time
from datetime import date
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{os.environ['LANDING_ENDPOINT']}",
        aws_access_key_id=os.environ["LANDING_ACCESS_KEY"],
        aws_secret_access_key=os.environ["LANDING_SECRET_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",  # SeaweedFS ignores this, boto3 requires it
    )


def _bucket() -> str:
    return os.environ["LANDING_BUCKET"]


def ensure_bucket() -> None:
    """Create the landing bucket if it doesn't exist yet. Safe to call every run."""
    s3 = _client()
    try:
        s3.head_bucket(Bucket=_bucket())
    except ClientError:
        s3.create_bucket(Bucket=_bucket())


def sha8(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:8]


def _list_versions(prefix: str, stem: str, ext: str) -> list[dict[str, Any]]:
    """Objects sorted oldest -> newest by a write-time we stamp ourselves
    (custom metadata `written-ns`), not S3's own LastModified: confirmed by
    direct testing that this SeaweedFS backend's LastModified only has
    second-level precision, so rapid successive writes (e.g. DIW's
    amphoe-by-amphoe crawl loop) can tie and sort unpredictably. The
    date+hash key string alone has the same problem -- hash suffixes are
    content-based, not sequential. Mirrors raw_store.py's reliance on real
    file mtime, just at higher precision than this backend's own clock."""
    s3 = _client()
    resp = s3.list_objects_v2(Bucket=_bucket(), Prefix=f"{prefix}/{stem}__")
    matches = [obj for obj in resp.get("Contents", []) if obj["Key"].endswith(f".{ext}")]
    objs = []
    for obj in matches:
        head = s3.head_object(Bucket=_bucket(), Key=obj["Key"])
        written_ns = int(head.get("Metadata", {}).get("written-ns", "0"))
        objs.append({"key": obj["Key"], "written_ns": written_ns})
    objs.sort(key=lambda o: o["written_ns"])
    return objs


def latest_version(prefix: str, stem: str, ext: str) -> str | None:
    found = _list_versions(prefix, stem, ext)
    return found[-1]["key"] if found else None


def save_version(prefix: str, stem: str, ext: str, content: bytes, *, on: date | None = None) -> tuple[str, bool]:
    """-> (key, is_new). Identical bytes to ANY stored version under this
    prefix/stem are not written again -- mirrors raw_store.py's save_version()."""
    ensure_bucket()  # must exist before list_objects_v2 can be called against it
    digest = sha8(content)
    for existing in _list_versions(prefix, stem, ext):
        if existing["key"].endswith(f"_{digest}.{ext}"):
            return existing["key"], False
    key = f"{prefix}/{stem}__{(on or date.today()).strftime('%Y%m%d')}_{digest}.{ext}"
    _client().put_object(
        Bucket=_bucket(), Key=key, Body=content,
        Metadata={"written-ns": str(time.time_ns())},
    )
    return key, True


def read_bytes(key: str) -> bytes:
    resp = _client().get_object(Bucket=_bucket(), Key=key)
    return resp["Body"].read()


def read_latest(prefix: str, stem: str, ext: str) -> bytes | None:
    key = latest_version(prefix, stem, ext)
    if key is None:
        return None
    return read_bytes(key)


def list_prefix(prefix: str) -> list[str]:
    """All object keys currently under a prefix (e.g. every landed file for one source)."""
    s3 = _client()
    keys: list[str] = []
    continuation: dict[str, Any] = {}
    while True:
        resp = s3.list_objects_v2(Bucket=_bucket(), Prefix=f"{prefix}/", **continuation)
        keys.extend(obj["Key"] for obj in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            break
        continuation = {"ContinuationToken": resp["NextContinuationToken"]}
    return sorted(keys)
