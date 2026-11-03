# Migration Guide: Full-Load → Incremental Pipeline

This guide walks through deploying the incremental HDC pipeline, verifying it works, and eventually migrating other sources.

---

## **Pre-Deployment Checklist**

- [ ] Current pipeline running successfully (baseline)
- [ ] Metabase dashboards display correct data
- [ ] Database backups current
- [ ] Access to Docker environment
- [ ] Scheduled maintenance window (optional, but safer)

---

## **Phase 1: Prepare Schema (One-Time)**

### Step 1.1: Review Schema Changes

File: `sql/00_incremental_setup.sql`

What it does:
- Creates `gold.pipeline_metadata` table (high-water mark tracking)
- Adds `row_hash` column to `silver.api_hdc_observations`
- Adds `ingestion_batch_id` column to `silver.api_hdc_observations`
- Adds `ingestion_batch_id` column to `gold.fact_hdc_observation`
- Adds unique constraint on Gold business key `(report_code, year_ce, zone, record_index)`

### Step 1.2: Apply Schema Changes

```bash
# Option A: Using Docker
docker compose exec warehouse-db mysql -u root -p$MYSQL_ROOT_PASSWORD < sql/00_incremental_setup.sql

# Option B: Directly
mysql -h localhost -u root -p < sql/00_incremental_setup.sql
```

### Step 1.3: Verify Schema Changes

```sql
-- Check pipeline_metadata table created
USE gold;
DESC pipeline_metadata;
-- Expected: metadata_id, target_table, last_batch_id, last_processed_at

-- Check Silver columns added
USE silver;
DESC api_hdc_observations;
-- Expected: row_hash, ingestion_batch_id columns

-- Check Gold columns added
USE gold;
DESC fact_hdc_observation;
-- Expected: ingestion_batch_id column, ux_hdc_business_key unique index
SHOW INDEXES FROM fact_hdc_observation;
```

---

## **Phase 2: Test Incremental Pipeline (HDC Proof-of-Concept)**

### Step 2.1: Run Unit Tests

```bash
cd pipeline
python test_incremental_pipeline.py
```

Expected output:
```
======================================================================
INCREMENTAL HDC PIPELINE - END-TO-END TESTS
======================================================================

=== TEST 1: Row Hash Determinism ===
✓ Same input produces same hash: a3f7e2b1c4f7e9d2
✓ Different value produces different hash: d7c4a9f2b1e8c5f3
✓ Row hash ignores source metadata (by design)

=== TEST 2: Delta Detection via Row Hash ===
✓ First insert successful: hash=a3f7e2b1c4f7e9d2, count=1
✓ Duplicate detected: same hash=a3f7e2b1c4f7e9d2

... [more tests] ...

======================================================================
✓ ALL TESTS PASSED
======================================================================
```

### Step 2.2: First Full Run (Cold Start)

Before this, make sure Bronze data is fresh (run `ingest_api_hdc.py` and `extract_load_api_hdc.py`).

```bash
# Run incremental Silver transform
python transform_silver_api_hdc_incremental.py

# Expected output:
# [silver_api_hdc_incremental] loaded 0 existing row hashes from Silver
# [silver_api_hdc_incremental] processed 163219 Bronze rows
# [silver_api_hdc_incremental] skipped 0 existing rows (delta detection)
# [silver_api_hdc_incremental] inserted 163219 new/changed rows to Silver
```

```bash
# Run incremental Gold transform
python transform_gold_facts_incremental.py

# Expected output:
# [gold_fact_hdc_incremental] high-water mark: NONE (full load)
# [gold_fact_hdc_incremental] read 163219 delta rows from Silver
# [gold_fact_hdc_incremental] prepared 116 rows for MERGE
# [gold_fact_hdc_incremental] MERGE completed: 116 rows upserted
# [pipeline_metadata] high-water mark set: fact_hdc_observation → api_hdc_load_20261026T145630
```

### Step 2.3: Verify Data Integrity

```sql
-- Check row counts match
SELECT COUNT(*) FROM bronze.api_hdc_observations;  -- ~163K (all rows)
SELECT COUNT(*) FROM silver.api_hdc_observations;  -- ~163K (unique hashes)
SELECT COUNT(*) FROM gold.fact_hdc_observation;    -- ~116 (pivoted + joined)

-- Check high-water mark was set
SELECT * FROM gold.pipeline_metadata WHERE target_table = 'fact_hdc_observation';

-- Check sample fact row
SELECT * FROM gold.fact_hdc_observation LIMIT 1;
-- Should have: report_code, year_ce, zone, record_index, target, result, f3_rate, ..., ingestion_batch_id
```

### Step 2.4: Verify Metabase Dashboards

1. Open Metabase: http://localhost:3000
2. Check "Public Health Surveillance" dashboard
3. Verify KPI values unchanged from pre-migration baseline
4. No NULL or missing data
5. All health metrics visible

---

## **Phase 3: Test Incremental Behavior (Delta Run)**

### Step 3.1: Simulate Upstream Correction

Modify a Bronze row to simulate HDC publishing corrected data:

```sql
-- Example: Change a target value
USE bronze;
UPDATE api_hdc_observations 
SET raw_field_value = '510' 
WHERE raw_report_code = 'NL9idjvwQKjv6R6' 
  AND raw_field_name = 'target'
  AND raw_zone = 'zone1'
LIMIT 1;
```

### Step 3.2: Run Incremental Pipeline Again

```bash
# Run Silver transform
python transform_silver_api_hdc_incremental.py

# Expected output:
# [silver_api_hdc_incremental] loaded 163219 existing row hashes from Silver
# [silver_api_hdc_incremental] processed 163219 Bronze rows
# [silver_api_hdc_incremental] skipped 163218 existing rows (delta detection) ← Most skipped!
# [silver_api_hdc_incremental] inserted 1 new/changed rows to Silver        ← Only 1 new!
```

```bash
# Run Gold transform
python transform_gold_facts_incremental.py

# Expected output:
# [gold_fact_hdc_incremental] high-water mark: api_hdc_load_20261026T145630
# [gold_fact_hdc_incremental] read 1 delta rows from Silver  ← Only 1 row!
# [gold_fact_hdc_incremental] prepared 1 rows for MERGE
# [gold_fact_hdc_incremental] MERGE completed: 1 rows upserted
# [pipeline_metadata] high-water mark set: fact_hdc_observation → api_hdc_load_20261027T090000
```

### Step 3.3: Verify Upstream Correction Applied

```sql
-- Check that the fact was updated
SELECT target FROM gold.fact_hdc_observation 
WHERE report_code = 'NL9idjvwQKjv6R6' AND zone = 'zone1' AND record_index = 1;
-- Should show: 510 (updated)

-- Check ingestion_batch_id was updated
SELECT ingestion_batch_id FROM gold.fact_hdc_observation 
WHERE report_code = 'NL9idjvwQKjv6R6' AND zone = 'zone1' AND record_index = 1;
-- Should show: api_hdc_load_20261027T090000 (new batch)
```

### Step 3.4: Memory Usage Comparison

Monitor system during pipeline run:

```bash
# Start monitoring (in separate terminal)
watch -n 1 'free -h | grep Mem'

# Old pipeline (full-load):
# Mem: ~8GB used (hypothetical 163K rows in memory)

# New pipeline (incremental):
# Mem: ~100MB used (only 1 delta row)
# ← 98% memory reduction!
```

---

## **Phase 4: Switch Production (HDC Only)**

### Step 4.1: Update Pipeline Scheduler

Update your pipeline orchestrator (cron, Airflow, etc.) to use incremental versions:

**Before (Full-Load)**:
```bash
#!/bin/bash
python transform_silver_api_hdc.py
python transform_gold_facts.py
```

**After (Incremental)**:
```bash
#!/bin/bash
# Run incremental HDC transforms
python transform_silver_api_hdc_incremental.py
python transform_gold_facts_incremental.py
```

### Step 4.2: Archive Old Scripts

Keep original scripts for reference, but don't run them:

```bash
mkdir pipeline/deprecated
mv pipeline/transform_silver_api_hdc.py pipeline/deprecated/
mv pipeline/transform_gold_facts.py pipeline/deprecated/
```

### Step 4.3: Monitor First Production Run

```bash
# Run manually with logging
python transform_silver_api_hdc_incremental.py 2>&1 | tee log_silver_hdc.log
python transform_gold_facts_incremental.py 2>&1 | tee log_gold_hdc.log

# Check logs for errors
grep -i error log_silver_hdc.log log_gold_hdc.log
```

### Step 4.4: Verify Dashboards Post-Migration

- [ ] Metabase dashboards load without errors
- [ ] KPI values stable (no unexpected changes)
- [ ] Drill-down queries work (fact → dimension joins)
- [ ] Historical trend lines smooth (no data loss)

---

## **Phase 5: Migrate Other Sources (Later Phase)**

Once HDC is stable (1-2 weeks of successful incremental runs), extend to other sources.

### NSO Income (Similar Pattern)

```python
# Copy & adapt incremental scripts
cp pipeline/transform_silver_api_hdc_incremental.py \
   pipeline/transform_silver_api_nso_incremental.py

# Edit:
# - Change table names: api_hdc_observations → api_nso_income
# - Change row_hash columns: (report_code, year_ce, ...) → (province, year_ce, ...)
# - Update EAV pivot logic (NSO doesn't use EAV, simpler)
```

### BMA Community (Similar Pattern)

```python
cp pipeline/transform_silver_api_hdc_incremental.py \
   pipeline/transform_silver_api_bma_incremental.py

# Edit:
# - Table names: api_hdc_observations → api_bma_community
# - Row hash: (community_id, fiscal_year, ...) → business key
```

### DIW Factory (Snapshot, No Time Dimension)

```python
# DIW is a single snapshot crawl (no time dimension)
# High-water mark strategy: last_crawl_timestamp
# Simpler than HDC (no historical time series)
```

### DDS Disease Ranking (Once Backend Recovers)

```python
# DDS is currently blocked (backend error)
# Once backend recovers, same pattern:
# - Row hash: (province, disease, year, ...)
# - High-water mark: last_batch_id
# - MERGE: (province, disease, year) unique key
```

---

## **Rollback Plan**

If incremental pipeline fails in production:

### Quick Rollback (< 1 hour)

1. Stop incremental pipeline
2. Switch back to old full-load scripts:
   ```bash
   python deprecated/transform_silver_api_hdc.py
   python deprecated/transform_gold_facts.py
   ```
3. Verify Metabase dashboards recover

### Full Rollback (Database Restore)

If data corruption detected:

```bash
# Restore from backup
mysql < backup_20261026.sql

# Reset high-water mark
python -c "from pipeline_metadata import reset_high_water_mark; reset_high_water_mark('fact_hdc_observation')"

# Rerun full-load pipeline
python deprecated/transform_silver_api_hdc.py
python deprecated/transform_gold_facts.py
```

---

## **Monitoring & Alerting**

### Key Metrics to Monitor

1. **High-Water Mark Advancement**
   ```sql
   SELECT last_batch_id, last_processed_at FROM gold.pipeline_metadata
   WHERE target_table = 'fact_hdc_observation';
   ```
   - Should update with each run
   - Alert if `last_processed_at` > 24 hours old (stalled pipeline)

2. **Row Count Growth**
   ```sql
   SELECT COUNT(*) FROM gold.fact_hdc_observation;
   ```
   - Should remain stable (no duplicates)
   - Alert if count grows unexpectedly after each run

3. **Memory Usage**
   ```bash
   top -p $(pgrep python)
   ```
   - Should stay < 200MB (delta rows only)
   - Alert if > 1GB (indicates full-load fallback?)

4. **Pipeline Duration**
   ```bash
   # Log timestamps
   echo "Start: $(date)" >> pipeline.log
   python transform_silver_api_hdc_incremental.py
   echo "End: $(date)" >> pipeline.log
   ```
   - Incremental runs should complete in < 5 minutes
   - Alert if > 10 minutes (indicates large delta or query issue)

### Sample Alert Query (Database)

```sql
-- Alert if high-water mark not updated in 24 hours
SELECT 'STALLED_PIPELINE' as alert, target_table, last_processed_at
FROM gold.pipeline_metadata
WHERE target_table = 'fact_hdc_observation'
  AND TIMESTAMPDIFF(HOUR, last_processed_at, NOW()) > 24;
```

---

## **FAQ**

### Q: Can I revert to the old pipeline if needed?

**A**: Yes. Keep the old scripts in `pipeline/deprecated/`. To rollback:
```bash
python deprecated/transform_silver_api_hdc.py
python deprecated/transform_gold_facts.py
```
Then manually update Metabase if it cached old data.

### Q: What if there's a data quality issue in the incremental pipeline?

**A**: Use `pipeline_metadata.reset_high_water_mark()` to force a full re-load:
```python
from pipeline_metadata import reset_high_water_mark
reset_high_water_mark("fact_hdc_observation")
# Next run will process all Silver rows (cold start)
```

### Q: How do I handle schema changes to Bronze or Silver?

**A**: 
1. Update SQL DDL (Bronze or Silver table structure)
2. Run a full re-load:
   ```python
   reset_high_water_mark("fact_hdc_observation")
   python transform_silver_api_hdc_incremental.py
   python transform_gold_facts_incremental.py
   ```

### Q: Can I run the old and new pipeline in parallel?

**A**: Not recommended. The old pipeline truncates facts; the new MERGE updates them. They'll conflict. Choose one.

### Q: What happens if a row lands in both old and new runs?

**A**: 
- Old pipeline: Truncates table, re-inserts all rows
- New pipeline: MERGE upserts (should be idempotent)
- **Recommendation**: Migrate cleanly, don't overlap.

---

## **Success Criteria**

You can declare incremental HDC pipeline successful when:

- [ ] Unit tests pass (`test_incremental_pipeline.py`)
- [ ] Cold start run completes (all 163K rows inserted to Silver)
- [ ] First Gold run completes (116 facts pivoted, high-water mark set)
- [ ] Incremental run completes (1 delta row processed, batch time < 1 min)
- [ ] MERGE updates existing facts on upstream correction
- [ ] Metabase dashboards show identical data to pre-migration
- [ ] Memory usage < 200MB (vs. previous ~1GB)
- [ ] Pipeline duration < 5 minutes for typical delta run
- [ ] High-water mark persists and advances with each run
- [ ] No manual reconciliation needed between runs

---

## **Timeline**

| Phase | Duration | Effort | Owner |
|-------|----------|--------|-------|
| Schema setup | 15 min | Low | DBA |
| Unit tests | 30 min | Low | Engineer |
| Cold start run | 10 min | Low | Engineer |
| Incremental testing | 2 hours | Medium | Engineer + QA |
| Production switch (HDC) | 30 min | Low | Engineer |
| Other sources | 2-3 weeks | Medium | Engineer |

---

## **Related Files**

- Schema: `sql/00_incremental_setup.sql`
- Tests: `pipeline/test_incremental_pipeline.py`
- Metadata: `pipeline/pipeline_metadata.py`
- Silver: `pipeline/transform_silver_api_hdc_incremental.py`
- Gold: `pipeline/transform_gold_facts_incremental.py`
- Architecture: `docs/07_incremental_architecture.md`

---

