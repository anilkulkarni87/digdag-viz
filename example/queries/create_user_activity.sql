-- Create golden user activity table
-- Sources: staging.events_cleaned, staging.users_enriched
-- Target: golden.user_activity_daily

WITH daily_activity AS (
  SELECT
    e.user_id,
    DATE(e.event_timestamp) as activity_date,
    COUNT(DISTINCT e.event_id) as total_events,
    COUNT(DISTINCT e.event_type) as unique_event_types,
    COUNT(DISTINCT e.page_url) as pages_visited,
    MIN(e.event_timestamp) as first_event_time,
    MAX(e.event_timestamp) as last_event_time
  FROM staging.events_cleaned e
  GROUP BY 1, 2
)
SELECT
  a.user_id,
  a.activity_date,
  a.total_events,
  a.unique_event_types,
  a.pages_visited,
  a.first_event_time,
  a.last_event_time,
  u.email,
  u.country,
  u.subscription_tier,
  u.user_segment,
  u.days_since_signup,
  CURRENT_TIMESTAMP as created_at
FROM daily_activity a
LEFT JOIN staging.users_enriched u ON a.user_id = u.user_id
