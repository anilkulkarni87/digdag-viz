-- Extract raw events from source system
-- Target: src_raw.events

SELECT 
  event_id,
  user_id,
  event_type,
  event_timestamp,
  properties,
  TD_TIME_FORMAT(time, 'yyyy-MM-dd HH:mm:ss', 'UTC') as created_at
FROM source_system.raw_events
WHERE TD_TIME_RANGE(time, 
  TD_TIME_ADD(TD_SCHEDULED_TIME(), '-1d'),
  TD_SCHEDULED_TIME()
)
