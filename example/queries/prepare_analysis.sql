-- Prepare data for ad-hoc analysis
-- Source: golden.user_activity_daily
-- Target: staging.analysis_prep

SELECT
  user_id,
  activity_date,
  total_events,
  pages_visited,
  subscription_tier,
  user_segment,
  days_since_signup
FROM golden.user_activity_daily
WHERE activity_date >= DATE_ADD('day', -30, CURRENT_DATE)
  AND total_events > 0
