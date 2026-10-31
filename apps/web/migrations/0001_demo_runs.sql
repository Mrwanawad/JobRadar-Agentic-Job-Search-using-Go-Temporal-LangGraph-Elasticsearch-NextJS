-- One demo run per signed-in account. The gateway enforces the same rule; this table maps
-- the account to its run so a returning visitor lands on their results.
CREATE TABLE demo_runs (
  owner       TEXT PRIMARY KEY,          -- "github:<id>" | "google:<sub>"
  profile_id  TEXT NOT NULL,
  workflow_id TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX demo_runs_workflow ON demo_runs (workflow_id);
