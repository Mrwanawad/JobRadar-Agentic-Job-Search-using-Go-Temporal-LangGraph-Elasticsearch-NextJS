-- A run can fail to start after its profile was created (the gateway has then used up the
-- account's demo). Keep the profile with workflow_id NULL so the visitor can retry the start.
CREATE TABLE demo_runs_new (
  owner       TEXT PRIMARY KEY,
  profile_id  TEXT NOT NULL,
  workflow_id TEXT,                      -- NULL until the workflow has started
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO demo_runs_new SELECT owner, profile_id, workflow_id, created_at FROM demo_runs;
DROP TABLE demo_runs;
ALTER TABLE demo_runs_new RENAME TO demo_runs;
CREATE UNIQUE INDEX demo_runs_workflow ON demo_runs (workflow_id);
