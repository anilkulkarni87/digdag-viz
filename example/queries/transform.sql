-- Transform and aggregate data
SELECT 
  user_id,
  COUNT(*) as event_count,
  MIN(event_timestamp) as first_event,
  MAX(event_timestamp) as last_event
FROM raw_data
GROUP BY user_id
HAVING COUNT(*) > 5
