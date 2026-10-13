-- Generates a single UNION ALL query that scans every text column in
-- silver+gold for aggregate-row markers. Written as a file (not a shell
-- string) so the Thai patterns are never mangled by shell quoting -- an
-- earlier loop-based version of this scan silently matched nothing and
-- reported a false clean.
SET SESSION group_concat_max_len = 1000000;

SELECT GROUP_CONCAT(
  CONCAT(
    'SELECT ''', table_schema, '.', table_name, '.', column_name, ''' AS loc, TRIM(`',
    column_name, '`) AS val, COUNT(*) AS n FROM `', table_schema, '`.`', table_name,
    '` WHERE TRIM(`', column_name, '`) REGEXP ''รวมทั้งหมด|ยอดจริง|ทั้งสิ้น|^รวม$|^Total$|^ALL$|^ทั้งหมด$'' GROUP BY TRIM(`',
    column_name, '`)'
  )
  SEPARATOR ' UNION ALL '
) INTO @sql
FROM information_schema.columns
WHERE table_schema IN ('silver','gold') AND data_type IN ('varchar','text','char');

SET @sql = CONCAT(@sql, ' ORDER BY 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
