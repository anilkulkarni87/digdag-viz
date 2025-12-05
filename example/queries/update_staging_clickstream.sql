-- Aggregate clickstream data
-- Source: src_raw.clickstream_events
-- Target: staging.clickstream_aggregated (INSERT INTO)

SELECT
  user_id,
  DATE(click_timestamp) as click_date,
  HOUR(click_timestamp) as click_hour,
  COUNT(*) as total_clicks,
  COUNT(DISTINCT page_url) as unique_pages,
  COUNT(DISTINCT session_id) as sessions
FROM src_raw.clickstream_events
GROUP BY 1, 2, 3
