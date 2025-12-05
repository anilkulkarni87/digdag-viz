-- Extract user data from source
-- Target: src_raw.users

SELECT
  user_id,
  email,
  signup_date,
  country,
  subscription_tier,
  time
FROM source_system.users
WHERE TD_TIME_RANGE(time,
  TD_TIME_ADD(TD_SCHEDULED_TIME(), '-1d'),
  TD_SCHEDULED_TIME()
)
