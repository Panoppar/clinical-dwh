# 0007 — `dim_area` grouped from an authoritative crosswalk, not geometry heuristics

## Status
Accepted

## Context
`dim_area` needs to group Thailand's standard TIS-1099 subdistrict
(tambon) codes into kmch-ml's own catchment-unit grain — 312 documented
units. Bangkok's post-2019 khwaeng (subdistrict) splits mean several
original tambon codes merge into one unit. An earlier version of this
table approximated that grouping from the boundary data alone: merging a
tambon into its parent only when that tambon's *own* centroid was `NULL`.

That heuristic was wrong. It silently left 5 of the 7 Bangkok post-2019
split groups' "anchor" tambon standing as its own independent unit instead
of merged with its split sibling — because that sibling happened to *have*
a valid centroid, so the NULL-centroid trigger never fired for it. This
inflated `dim_area` from kmch-ml's documented 312 units to 317, and the gap
was initially (wrongly) attributed to "snapshot-date drift" before the
real cause was found.

## Decision
Group `dim_area` by `bronze.tambon_xwalk`'s own `unit_code` column —
kmch-ml's authoritative, pre-built mapping — rather than inferring the
grouping from geometry data at all. `centroid_lat/lon`, `area_km2`, and
`contains_kmch_point` are then all derived from a single, consistent
method per unit (the pre-2019-split polygon from
`bronze.geo_boundary_polygon`, confirmed to have exactly one polygon per
merged group since that boundary source pre-dates the 2019 splits) —
not a mix of "Silver's stored point for ordinary units" and "something
else" for merged ones.

## Consequences
- `dim_area` now resolves to exactly 312 units, an exact match to
  kmch-ml's own documented total, confirmed directly rather than inferred.
- The crosswalk file (`bronze.tambon_xwalk`) became a hard structural
  dependency for `dim_area` — a file-based source kept deliberately (see
  [0002](0002-live-api-first-sourcing.md)) specifically because this
  grouping can't be reliably derived any other way.
- `gold.dim_tambon_unit_xwalk` and the live DOPA-population source's own
  unit-code resolution both lean on this same crosswalk table directly
  rather than duplicating grouping logic — one source of truth for
  "which tambon belongs to which unit."
