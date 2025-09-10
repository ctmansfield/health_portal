CREATE TABLE IF NOT EXISTS analytics.ai_findings (
  id BIGSERIAL PRIMARY KEY,
  person_id     text        NOT NULL,
  finding_time  timestamptz NOT NULL,
  metric        text        NOT NULL,
  method        text        NOT NULL,
  score         double precision NOT NULL,
  level         text        NOT NULL,
  "window"      jsonb       NOT NULL,  -- {start,end,mean,std,n,...}
  context       jsonb       NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_findings_person_metric_day
  ON analytics.ai_findings(person_id, finding_time, metric);

CREATE INDEX IF NOT EXISTS idx_ai_findings_person_time
  ON analytics.ai_findings(person_id, finding_time);
