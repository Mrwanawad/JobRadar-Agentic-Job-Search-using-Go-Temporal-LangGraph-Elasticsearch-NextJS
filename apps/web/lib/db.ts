import "server-only";
import { env } from "./env";

export type DemoRun = { owner: string; profile_id: string; workflow_id: string | null; created_at: string };

export async function findRun(owner: string): Promise<DemoRun | null> {
  return (await env()).DB.prepare("SELECT * FROM demo_runs WHERE owner = ?").bind(owner).first<DemoRun>();
}

// Recorded right after the gateway creates the profile, before the workflow starts.
export async function saveProfile(owner: string, profileID: string) {
  await (await env()).DB.prepare("INSERT INTO demo_runs (owner, profile_id) VALUES (?, ?)")
    .bind(owner, profileID)
    .run();
}

export async function setWorkflow(owner: string, workflowID: string) {
  await (await env()).DB.prepare("UPDATE demo_runs SET workflow_id = ? WHERE owner = ?")
    .bind(workflowID, owner)
    .run();
}
