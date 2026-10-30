# 0005 — EAV grain for sources with volatile category schemas

## Status
Accepted

## Context
Two sources' own category columns are tied to things that change on a
schedule outside this project's control:

- HDC's weekly health observation reports — which indicators/report types
  exist varies by report.
- DOE's monthly migrant-worker-permit PDF — several of its permit
  categories are tied to dated cabinet resolutions ("มาตรา 63/2 ต่ออายุมติ
  ครม. 2 ธ.ค. 68") that get superseded and replaced with a *different*
  dated category the following month, confirmed live by comparing two
  months' reports.

A Bronze table with one fixed column per category (the natural choice for a
single month's shape) would need a schema migration every time a category
was added, renamed, or superseded — which, for the DOE source, is
effectively every month.

## Decision
Land these sources as EAV (entity-attribute-value) rows instead: one row
per `(table, zone, category/group label, sex)` combination, with the
category's *name* itself as data in a column (`raw_table_title`,
`raw_group_label`), not as a column name. Bronze's own schema then never
needs to change when a source's category set changes — only the *values*
in `raw_group_label` differ month to month.

Category vs. nationality *interpretation* of a table's group column is
decided generically at Silver-transform time from structural signals (a
fixed title-boilerplate prefix, whether a row's label matches the known
"all nationalities" sentinel) — never from a hardcoded table-number map,
since table numbers and exact category text both shift between reports.

## Consequences
- A future month's DOE report with entirely new cabinet-resolution
  categories loads without any code change — the EAV shape already
  accommodates it.
- Silver's pivot-back-to-named-columns step (e.g.
  `transform_silver_doe_migrant_worker.py`) carries real logic that a fixed
  wide Bronze schema wouldn't have needed — resolving which EAV rows
  represent a "total" vs a breakdown, handling multi-page continuation
  quirks, is now Silver's job instead of being implicit in a column list.
- Every other source in this project (NSO, BMA, DIW, DOPA population) uses
  fixed-column Bronze tables instead, since their own schemas are stable —
  EAV is applied narrowly to the two sources that actually need it, not as
  a universal default, to avoid the extra pivot-logic cost where it isn't
  earning its keep.
