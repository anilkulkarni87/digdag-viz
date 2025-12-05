-- Sync clickstream data hourly
-- Target: src_raw.clickstream_events

SELECT
  click_id,
  session_id,
  user_id,
  page_url,
  click_element,
  click_timestamp,
  time
FROM source_system.clickstream
WHERE TD_TIME_RANGE(time,
  TD_TIME_ADD(TD_SCHEDULED_TIME(), '-1h'),
  TD_SCHEDULED_TIME()
)
