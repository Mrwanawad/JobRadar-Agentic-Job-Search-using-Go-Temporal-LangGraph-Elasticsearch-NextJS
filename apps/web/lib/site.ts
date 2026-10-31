export const REPO_URL =
  "https://github.com/Mrwanawad/JobRadar-Agentic-Job-Search-using-Go-Temporal-LangGraph-Elasticsearch-NextJS";

export type Me = {
  user: { id: string; name: string; avatar?: string } | null;
  run: { workflow_id: string; created_at: string } | null;
  turnstile_site_key: string;
};

export async function fetchMe(): Promise<Me> {
  const res = await fetch("/api/me", { cache: "no-store" });
  if (!res.ok) throw new Error(`/api/me ${res.status}`);
  return res.json();
}
