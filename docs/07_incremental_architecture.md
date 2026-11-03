# Incremental Delta Load Architecture

## Overview

This document describes the transition from a **full-load, drop-and-recreate** Medallion pipeline to a **highly efficient incremental (delta) architecture**, using the HDC (Health Data Center) source as the proof-of-concept.

### Pain Points in Full-Load Model

1. **Bronze→Silver Duplication**: Every run re-inserted all rows, even if only metadata changed
   - File `nso_20261025_abc123.csv` landed again as `nso_20261025_abc456.csv` (different hash)
   - Bronze to Silver re-processed all rows, creating duplicates in Silver
   
2. **Silver→Gold Memory Explosion**: Python `defaultdict` loaded ALL historical data into RAM
   - HDC with 163K EAV rows → 50K+ rows in memory for pivot
   - OOM crashes on larger sources
   - Full drop-and-recreate discarded aggregation state between runs

3. **Compute Waste**: Every run re-computed aggregates for unchanged data
   - Economic KPIs recalculated from all factories (no delta tracking)
   - No reuse of prior-run intermediate state

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ STAGING: SeaweedFS (Content-hashed, immutable)                      │
│ File: nso/SFD_SPB0802_66__20261025_abc123.csv                       │
│ Hash: abc123... (unchanged) → landing_store skips re-store ✓        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ BRONZE: Raw immutable audit trail (no changes to this layer)        │
│ - Extract landing CSV → shred into rows                            │
│ - Lineage metadata: source_file_name, file_hash, ingestion_batch_id│
│ - ALL rows inserted (for audit trail)                              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ SILVER: Cleaned, typed, deduplicated (NEW: Delta detection)        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ transform_silver_api_hdc_incremental.py                         │ │
│ │                                                                 │ │
│ │ 1. For each Bronze row:                                         │ │
│ │    - Compute row_hash = SHA256(report_code|year_ce|zone|...)   │ │
│ │    - Query Silver: hash in existing_hashes?                     │ │
│ │      YES → Skip (seen before, no change)                        │ │
│ │      NO  → INSERT new row                                       │ │
│ │                                                                 │ │
│ │ 2. Track ingestion_batch_id (from Bronze lineage)               │ │
│ │    → Used by Gold for high-water mark filtering                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│ Result: Only NEW/CHANGED rows in Silver, no duplicates              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ GOLD: Facts, dimensions, aggregates (NEW: High-water mark + MERGE)│
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ transform_gold_facts_incremental.py                             │ │
│ │                                                                 │ │
│ │ 1. Query pipeline_metadata: last_batch_id for this table?       │ │
│ │    YES → Use as WHERE filter: ingestion_batch_id > last_batch_id│
│ │    NO  → Full load (first run)                                  │ │
│ │                                                                 │ │
│ │ 2. Read Silver delta rows only                                  │ │
│ │    Memory bound: only new/changed rows, not all history         │ │
│ │                                                                 │ │
│ │ 3. Pivot EAV fields in Python (same logic as before)            │ │
│ │                                                                 │ │
│ │ 4. Execute SQL MERGE (not drop-and-recreate):                   │ │
│ │    INSERT ... ON DUPLICATE KEY UPDATE                           │ │
│ │    - New (report_code, year_ce, zone, record_index) → INSERT    │ │
│ │    - Existing key → UPDATE (handles upstream corrections)       │ │
│ │    - Duplicates in batch → Latest (batch_id DESC) wins          │ │
│ │                                                                 │ │
│ │ 5. Update high-water mark in pipeline_metadata                  │ │
│ │    → Enables next run to fetch only delta                       │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│ Result: Gold fact tables updated (not recreated), bounded memory    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ METABASE: Queries Gold fact tables (no change to consumers)         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Row-Level Hashing (Bronze→Silver)

**File**: `transform_silver_api_hdc_incremental.py`

**Algorithm**:
```python
row_hash = SHA256(f"{report_code}|{year_ce}|{zone}|{record_index}|{field_name}|{field_value}")[:16]
```

**Key Decision**: Hash includes ONLY business columns, ignoring source metadata
- Same data from re-transmitted Bronze file → same hash → skipped
- Different field_value (upstream correction) → different hash → inserted (update via MERGE)

**Example**:
```
Bronze Row 1: report='NL9idjvw', year_be=2568, zone='zone1', record=1, field='target', value='500'
  → hash = 'a3f7e2b1c4f7...'
  → query Silver: hash exists? NO → INSERT with row_hash='a3f7e2b1c4f7'

Bronze Row 2: report='NL9idjvw', year_be=2568, zone='zone1', record=1, field='target', value='500' 
  (identical from re-transmission)
  → hash = 'a3f7e2b1c4f7...' (same)
  → query Silver: hash exists? YES → SKIP (delta detection)

Bronze Row 3: report='NL9idjvw', year_be=2568, zone='zone1', record=1, field='target', value='510'
  (upstream correction: value changed from 500 to 510)
  → hash = 'd7c4a9f2b1e8...' (different)
  → query Silver: hash exists? NO → INSERT with row_hash='d7c4a9f2b1e8'
  → Gold MERGE: key (NL9idjvw, 2025, zone1, 1) exists → UPDATE target=510
```

### 2. High-Water Mark Tracking (Silver→Gold)

**File**: `pipeline_metadata.py`

**Data**: `gold.pipeline_metadata` table
```sql
CREATE TABLE pipeline_metadata (
    metadata_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    target_table VARCHAR(100) NOT NULL,  -- 'fact_hdc_observation', 'fact_income', etc.
    last_batch_id VARCHAR(100),           -- e.g., 'api_hdc_load_20261026T145630'
    last_processed_at TIMESTAMP,
    UNIQUE KEY ux_target_table (target_table)
);
```

**Usage**:
```python
# Before Silver→Gold read:
last_batch_id = pipeline_metadata.get_high_water_mark("fact_hdc_observation")
# Returns: "api_hdc_load_20261025T145630" (or None if first run)

# Silver filter:
if last_batch_id:
    where_clause = f"WHERE ingestion_batch_id > '{last_batch_id}'"
else:
    where_clause = ""  # First run: all rows

# After successful Gold MERGE:
pipeline_metadata.set_high_water_mark("fact_hdc_observation", "api_hdc_load_20261026T150045")
```

**State Persistence**:
- Stored in database, not in code or config files
- Automatically updated after each successful run
- Can be reset manually for recovery: `pipeline_metadata.reset_high_water_mark("fact_hdc_observation")`

### 3. SQL MERGE for Upsert (Gold)

**File**: `transform_gold_facts_incremental.py`

**MySQL Syntax** (MySQL 5.7+):
```sql
INSERT INTO fact_hdc_observation
(report_code, year_ce, zone, record_index, target, result, ..., ingestion_batch_id)
VALUES (%s,%s,%s,%s,%s,%s,%s,...,%s)
ON DUPLICATE KEY UPDATE
    target = COALESCE(VALUES(target), target),
    result = COALESCE(VALUES(result), result),
    ...
    ingestion_batch_id = VALUES(ingestion_batch_id)
```

**Business Key**: Unique constraint on `(report_code, year_ce, zone, record_index)`

**Semantics**:
- **Insert**: New (report_code, year_ce, zone, record_index) → added to fact table
- **Update**: Existing key → measure columns updated (handles upstream corrections)
- **Coalesce Logic**: `COALESCE(new_value, old_value)` prevents overwriting with NULL

**Example**:
```
Run 1: INSERT (report='NL9idjvw', year_ce=2025, zone='zone1', record_index=1)
  → target=500, result=450, male=250

Run 2 (next day, same data): 
  → Row hash same → not re-inserted to Silver → not in delta for Gold
  → Gold unchanged

Run 3 (upstream correction: value changed):
  → Row hash different → inserted to Silver with ingestion_batch_id='api_hdc_load_20261027...'
  → Gold delta includes this row
  → MERGE: (NL9idjvw, 2025, zone1, 1) matches → UPDATE target=510, result=460
  → Old fact values replaced with latest
```

---

## Schema Changes (One-Time Setup)

**File**: `sql/00_incremental_setup.sql`

Run once before switching to incremental pipeline:

```sql
-- 1. Create pipeline metadata table (Gold)
USE gold;
CREATE TABLE pipeline_metadata (
    metadata_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    target_table VARCHAR(100) NOT NULL,
    last_batch_id VARCHAR(100),
    last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_target_table (target_table)
);

-- 2. Add columns to Silver for row hash & batch tracking
USE silver;
ALTER TABLE api_hdc_observations
ADD COLUMN row_hash VARCHAR(16) AFTER field_value,
ADD COLUMN ingestion_batch_id VARCHAR(100) AFTER row_hash,
ADD KEY ix_row_hash (row_hash),
ADD KEY ix_ingestion_batch_id (ingestion_batch_id);

-- 3. Update Gold schema for MERGE support
USE gold;
ALTER TABLE fact_hdc_observation
ADD COLUMN ingestion_batch_id VARCHAR(100) AFTER fact_id,
ADD UNIQUE KEY ux_hdc_business_key (report_code, year_ce, zone, record_index);
```

---

## Migration Path

### Step 1: Prepare Schema
```bash
# Run one-time setup
docker compose exec warehouse-db mysql -p$MYSQL_ROOT_PASSWORD < sql/00_incremental_setup.sql
```

### Step 2: Run Incremental Pipeline for HDC
```bash
# Import the new modules and run
python -c "from transform_silver_api_hdc_incremental import run; run()"
python -c "from transform_gold_facts_incremental import run; run()"
```

### Step 3: Verify State
```python
from pipeline_metadata import get_metadata_status
print(get_metadata_status())
# Output: {'fact_hdc_observation': {'last_batch_id': 'api_hdc_load_20261026T145630', ...}}
```

### Step 4: Migrate Other Sources (Later)
Follow same pattern for NSO, BMA, DIW, DDS:
1. Create incremental versions: `transform_silver_api_{source}_incremental.py`
2. Add to gold fact builders: `transform_gold_facts_incremental.py`
3. Extend `pipeline_metadata.py` for multi-table tracking

---

## Performance & Memory Impact

### Memory Before (Full-Load)
```
Bronze→Silver:
  - Processes ALL Bronze rows every run
  - Python list: ~163K EAV rows (HDC) = ~30 MB

Silver→Gold:
  - Loads ALL Silver rows into defaultdict
  - Pivots all historical records
  - Peak memory: ~100 MB (HDC)
  - OOM risk on larger runs
```

### Memory After (Incremental)
```
Run 1 (cold start):
  - Bronze→Silver: Process all rows (unavoidable first run)
  - Silver→Gold: Load all Silver rows (unavoidable first run)
  - Peak: ~100 MB (same as before)

Run 2 (next day, typical):
  - Bronze→Silver: Process 50K Bronze rows, skip ~113K duplicates via row_hash
  - Silver→Gold: Load only 500 new rows (delta), skip 162.5K via high-water mark
  - Peak: ~5 MB
  - 95% reduction in memory footprint
```

### CPU/Disk Impact
- **Bronze→Silver**: Row hash computation ~1ms per row (negligible)
- **Silver→Gold**: High-water mark filter eliminates 90%+ of I/O on steady-state runs
- **Gold MERGE**: Slightly slower than INSERT (unique key conflict check), but only for delta rows

---

## Handling Edge Cases

### Upstream Corrections (Same Key, Different Value)
**Scenario**: HDC re-publishes previous month's data with corrected values

**Flow**:
```
Old: field_value='500' → row_hash='a3f7e2b1'
New: field_value='510' → row_hash='d7c4a9f2' (different hash)

Run N:
  1. Bronze: both rows present (old + new from re-transmission)
  2. Silver: insert new row with hash='d7c4a9f2'
  3. Gold MERGE: (report_code, year_ce, zone, record_index) matches → UPDATE target=510
  4. Old fact value (500) replaced with corrected (510)
```

**No manual reconciliation needed**: MERGE handle this automatically.

### Duplicate Rows in Current Batch
**Scenario**: High-water mark read happens mid-batch, source publishes same record twice

**Flow**:
```
Silver query results (ordered by ingestion_batch_id DESC):
  (report='NL9idjvw', ..., record=1, field='target', value='510', batch_id='api_hdc_load_20261026')
  (report='NL9idjvw', ..., record=1, field='target', value='510', batch_id='api_hdc_load_20261026')

Python pivot (tie-breaking):
  key = (report_code, year_ce, zone, record_index)
  if key not in hdc_pivots:
      create dict
  if field_name already in dict (from newer batch_id):
      skip
  else:
      store value

Result: First occurrence (highest batch_id) wins
```

**Tie-breaking**: `ORDER BY ingestion_batch_id DESC` ensures latest batch wins on conflict within a single run.

### First Run (No High-Water Mark)
**Scenario**: Fresh deployment, pipeline_metadata empty

**Flow**:
```
pipeline_metadata.get_high_water_mark("fact_hdc_observation")
  → Returns None

where_clause = ""  (no filter)

Read ALL Silver rows (cold start unavoidable)

After MERGE completes:
  → set_high_water_mark(..., last_batch_id)
  → Next run will filter

Result: First run is full-load (expected), subsequent runs are delta
```

---

## Monitoring & Debugging

### Check High-Water Mark State
```python
from pipeline_metadata import get_metadata_status
status = get_metadata_status()
# Output:
# {
#   'fact_hdc_observation': {
#     'last_batch_id': 'api_hdc_load_20261026T150045',
#     'last_processed_at': datetime.datetime(2026, 10, 26, 15, 0, 45)
#   }
# }
```

### Reset High-Water Mark (Force Full Re-load)
```python
from pipeline_metadata import reset_high_water_mark
reset_high_water_mark("fact_hdc_observation")
# Next run will process all Silver rows (expensive)
```

### Inspect Row Hashes in Silver
```sql
-- Check how many hashes are in Silver
SELECT COUNT(DISTINCT row_hash) FROM silver.api_hdc_observations;

-- Find rows with specific hash
SELECT * FROM silver.api_hdc_observations 
WHERE row_hash = 'a3f7e2b1';
```

### Verify MERGE Logic
```sql
-- Check fact_hdc_observation for latest ingestion_batch_id per business key
SELECT report_code, year_ce, zone, record_index, MAX(ingestion_batch_id) as latest_batch
FROM gold.fact_hdc_observation
GROUP BY report_code, year_ce, zone, record_index
ORDER BY latest_batch DESC;
```

---

## Backward Compatibility

**Q**: Can I still run the old full-load pipeline alongside the incremental version?

**A**: Not recommended. Key differences:
- Old: drops `fact_hdc_observation` every run
- New: upserts using MERGE (preserves prior data)

If both run on same database:
- Old truncates table → New MERGE fails to update prior rows
- New inserts new rows → Old truncate wipes them

**Migration strategy**:
1. Verify incremental pipeline works end-to-end
2. Archive old scripts (backup)
3. Switch completely to incremental

---

## Next Steps

### Immediate (HDC Proof-of-Concept)
- [ ] Run `sql/00_incremental_setup.sql` (schema one-time)
- [ ] Test `transform_silver_api_hdc_incremental.py` with sample data
- [ ] Test `transform_gold_facts_incremental.py` (high-water mark filtering)
- [ ] Verify Metabase dashboards still work (Gold unchanged for consumers)

### Phase 2 (Other Sources)
- [ ] Extend for NSO income (same pattern)
- [ ] Extend for BMA community (same pattern)
- [ ] Extend for DIW factories (snapshot, no time dimension)
- [ ] Extend for DDS disease ranking (once backend recovers)

### Phase 3 (Advanced)
- [ ] Aggregate tables (Gold agg_* tables) as separate incremental jobs
- [ ] Composite index (Level-3 KPIs) incremental refresh
- [ ] Idempotency guarantees: exactly-once semantics via batch deduplication
- [ ] Monitoring: alert if high-water mark not advancing (stalled pipeline)

---

## Related Files

- **Schema**: `sql/00_incremental_setup.sql`
- **Metadata**: `pipeline/pipeline_metadata.py`
- **Bronze→Silver**: `pipeline/transform_silver_api_hdc_incremental.py`
- **Silver→Gold**: `pipeline/transform_gold_facts_incremental.py`
- **Original (deprecated)**: `pipeline/transform_silver_api_hdc.py`, `pipeline/transform_gold_facts.py`

