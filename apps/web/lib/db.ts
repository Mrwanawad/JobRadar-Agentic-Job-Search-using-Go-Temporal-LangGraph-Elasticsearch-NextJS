import "server-only";
import { env } from "./env";

export type DemoRun = { owner: string; profile_id: string; workflow_id: string; created_at: string };

export async function findRun(owner: string): Promise<DemoRun | null> {
  return (await env()).DB.prepare("SELECT * FROM demo_runs WHERE owner = ?").bind(owner).first<DemoRun>();
}

export async function saveRun(owner: string, profileID: string, workflowID: string) {
  await (await env()).DB.prepare("INSERT INTO demo_runs (owner, profile_id, workflow_id) VALUES (?, ?, ?)")
    .bind(owner, profileID, workflowID)
    .run();
}
