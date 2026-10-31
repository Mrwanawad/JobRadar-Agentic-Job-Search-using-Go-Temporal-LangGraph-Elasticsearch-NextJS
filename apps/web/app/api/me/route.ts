import { getUser } from "@/lib/session";
import { findRun } from "@/lib/db";
import { env } from "@/lib/env";

export async function GET() {
  const [user, e] = await Promise.all([getUser(), env()]);
  const run = user && (await findRun(user.id));
  return Response.json({
    user,
    run: run ? { workflow_id: run.workflow_id, created_at: run.created_at } : null,
    turnstile_site_key: e.TURNSTILE_SITE_KEY,
  });
}
