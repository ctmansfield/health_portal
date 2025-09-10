-- services/healthdb-pg-0001/init/045_events_unique_key.sql
ALTER TABLE analytics.data_events
  ADD CONSTRAINT uq_events_person_metric_time
  UNIQUE (person_id, code_system, code, effective_time);
