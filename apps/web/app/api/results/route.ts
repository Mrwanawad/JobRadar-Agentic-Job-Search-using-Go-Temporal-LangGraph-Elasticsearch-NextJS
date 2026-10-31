import { getUser } from "@/lib/session";
import { findRun } from "@/lib/db";
import { gatewayJSON } from "@/lib/gateway";

export async function GET() {
  const user = await getUser();
  const run = user && (await findRun(user.id));
  if (!run?.workflow_id) return Response.json({ error: "no run yet" }, { status: 404 });
  const { status, data } = await gatewayJSON(`/v1/profiles/${encodeURIComponent(run.profile_id)}/results?limit=25`);
  return Response.json(data, { status });
}
