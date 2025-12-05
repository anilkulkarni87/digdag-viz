-- Enrich user data with additional attributes
-- Source: src_raw.users
-- Target: staging.users_enriched

WITH user_enrichment AS (
  SELECT
    u.user_id,
    u.email,
    u.signup_date,
    u.country,
    u.subscription_tier,
    CASE 
      WHEN u.subscription_tier = 'premium' THEN 'high_value'
      WHEN u.subscription_tier = 'standard' THEN 'medium_value'
      ELSE 'low_value'
    END as user_segment,
    DATE_DIFF('day', CAST(u.signup_date AS DATE), CURRENT_DATE) as days_since_signup,
    u.time
  FROM src_raw.users u
)
SELECT * FROM user_enrichment
