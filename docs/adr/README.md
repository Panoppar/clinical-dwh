# Architecture Decision Records

Significant, hard-to-reverse structural decisions made on this project, and
why — written for whoever next asks "why is it built this way?" Each record
follows the standard format: Context (the problem/forces), Decision (what
was chosen), Consequences (what that costs or enables).

Numbered in the order the decision was made, not necessarily the order a
reader would most want to encounter them — start with
[0001](0001-medallion-architecture.md) for the overall shape, then read
whichever else is relevant to what you're touching.

| # | Title | Status |
|---|---|---|
| [0001](0001-medallion-architecture.md) | Medallion architecture (Bronze/Silver/Gold) | Accepted |
| [0002](0002-live-api-first-sourcing.md) | Live-API-first sourcing, file-based as a scoped exception | Accepted |
| [0003](0003-seaweedfs-landing-zone.md) | SeaweedFS as the S3-compatible landing zone | Accepted |
| [0004](0004-content-addressed-landing-versioning.md) | Content-addressed versioning for landed raw data | Accepted |
| [0005](0005-eav-grain-for-volatile-schemas.md) | EAV grain for sources with volatile category schemas | Accepted |
| [0006](0006-metabase-gold-only-access.md) | Metabase restricted to gold-schema-only via a dedicated account | Accepted |
| [0007](0007-dim-area-from-crosswalk-not-geometry.md) | `dim_area` grouped from an authoritative crosswalk, not geometry heuristics | Accepted |
| [0008](0008-per-service-scoped-db-accounts.md) | Per-service MySQL accounts with schema-scoped grants | Accepted |
| [0009](0009-full-refresh-pipeline.md) | Full-refresh pipeline (drop + recreate every run) | Accepted |
| [0010](0010-loopback-only-port-bindings.md) | Docker port bindings default to loopback-only | Accepted |
