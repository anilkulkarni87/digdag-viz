-- Consolidate analysis results
-- Target: golden.analysis_results

SELECT
  'trend_analysis' as analysis_type,
  CURRENT_DATE as analysis_date,
  'Analysis completed via Python scripts' as description,
  CURRENT_TIMESTAMP as created_at
