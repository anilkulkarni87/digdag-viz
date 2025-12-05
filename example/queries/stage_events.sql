-- Clean and standardize events
-- Source: src_raw.events
-- Target: staging.events_cleaned

WITH cleaned_events AS (
  SELECT
    event_id,
    user_id,
    LOWER(event_type) as event_type,
    event_timestamp,
    JSON_EXTRACT_SCALAR(properties, '$.page') as page_url,
    JSON_EXTRACT_SCALAR(properties, '$.referrer') as referrer,
    created_at,
    time
  FROM src_raw.events
  WHERE event_id IS NOT NULL
    AND user_id IS NOT NULL
)
SELECT * FROM cleaned_events
