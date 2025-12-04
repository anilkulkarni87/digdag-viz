-- Extract raw data from source tables
SELECT 
  user_id,
  event_name,
  event_timestamp,
  properties
FROM source_events
WHERE TD_TIME_RANGE(event_timestamp, 
  TD_TIME_ADD(TD_SCHEDULED_TIME(), '-1d'),
  TD_SCHEDULED_TIME())
